#!/usr/bin/env python3
"""Physical validation of bounded CRC records and host acknowledgements."""
from pcb_paths import TEMPLATES
import argparse
import binascii
import hashlib
import json
import time
from pathlib import Path

import instruction_timing as timing
from pico_link import Pico

ROOT = timing.ROOT / 'artifacts/framed-transport'
FIRST = 0x00f0
COUNT = 96
RUN_ID = 0x7b01
FRAME_SIZE = 27


def generate():
    ROOT.mkdir(parents=True, exist_ok=True)
    prefix = (TEMPLATES / 'bootstrap.asm').read_text().split('        LDA $DF10')[0]
    source = prefix + timing.RAM + '''; Packet 2E00..2E1A; sequence 2E42; received sequence 2E44.
        LDD #$00F0
        STD $2E42
        CLRA
        STA $2E44
NEXT_FRAME:
; Space watchdog reads independently of host speed.
        LDX #$0FFF
FRAME_DELAY:
        LEAX -1,X
        BNE FRAME_DELAY
        TST $5FEA
        LDD #$A55A
        STD $2E00
        LDA #1
        STA $2E02
        LDD #$7B01
        STD $2E03
        LDD $2E42
        STD $2E05
        LDA #16
        STA $2E07
        CLRA
        STA $2E08
        LDX #$2E09
; Payload: consecutive byte values, starting with the sequence low byte.
        LDB $2E43
FILL_PAYLOAD:
        STB ,X+
        INCB
        CMPX #$2E19
        BNE FILL_PAYLOAD
; CRC-16/CCITT-FALSE, polynomial 1021, initial FFFF, no final XOR.
; Includes the complete header and payload, excluding CRC itself.
        LDD #$FFFF
        LDX #$2E00
CRC_BYTE:
        EORA ,X+
        LDY #8
CRC_BIT:
        ASLB
        ROLA
        BCC CRC_NO_XOR
        EORA #$10
        EORB #$21
CRC_NO_XOR:
        LEAY -1,Y
        BNE CRC_BIT
        CMPX #$2E19
        BNE CRC_BYTE
        STD $2E19
; One complete frame fits the 32-byte FIFO. No next frame until host ACK.
        LDU #$2E00
SEND_BYTE:
        LDB ,U+
        LDX #$DF00
        ABX
        LDA ,X
        CMPU #$2E1B
        BNE SEND_BYTE
; Require the exact next in_seq, instead of accepting any changed value.
; pending is published before the byte, so it is not the readiness gate.
        INC $2E44
        LDU #$0800
WAIT_BLOCK:
        LDY #$0FFF
WAIT_ACK:
        LDA $DC0C
        CMPA $2E44
        BEQ GOT_ACK
        LEAY -1,Y
        BNE WAIT_ACK
        TST $5FEA
        LEAU -1,U
        CMPU #0
        BNE WAIT_BLOCK
        LDA $DFF2
        BRA IDLE
GOT_ACK:
        LDA $DE00
        CMPA $2E43
        BNE RAM_FAIL
        LDD $2E42
        ADDD #1
        STD $2E42
        CMPD #$0150
        LBNE NEXT_FRAME
        LDA $DFFE
IDLE:
        LDX #$FFFF
IDLE_DELAY:
        LEAX -1,X
        BNE IDLE_DELAY
        TST $5FEA
        BRA IDLE
RAM_FAIL:
        LDA $DFF1
        BRA IDLE
        ORG $FFF6
        FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET
'''
    (ROOT / 'probe.asm').write_text(source)
    (ROOT / 'manifest.json').write_text(json.dumps(dict(first=FIRST, count=COUNT,
        run_id=RUN_ID, frame_size=FRAME_SIZE, source_sha256=hashlib.sha256(source.encode()).hexdigest()), indent=2)+'\n')


def package():
    fixed = (ROOT / 'fixed.bin').read_bytes()
    assert len(fixed) == 32768 and fixed[0x5c00:0x6000] == b'\xff'*1024
    assert fixed[:26].hex() == '4280000824ff63fb92075fea10113a077c0010fb3a075d003dd0'
    assert fixed[-2:] == b'\x80\x00'
    image = bytes(0x18000)+fixed
    (ROOT / 'probe-128k.bin').write_bytes(image)
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    manifest['image_sha256'] = hashlib.sha256(image).hexdigest()
    (ROOT / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


def check_frame(frame, seq, check_payload=True, run_id=RUN_ID):
    assert len(frame) == FRAME_SIZE, 'frame length'
    assert frame[:5] == bytes.fromhex('a55a01')+run_id.to_bytes(2,'big'), 'frame header/run ID'
    assert int.from_bytes(frame[5:7], 'big') == seq, 'frame sequence'
    assert frame[7:9] == bytes([16, 0]), 'payload length/flags'
    assert binascii.crc_hqx(frame[:-2], 0xffff) == int.from_bytes(frame[-2:], 'big'), 'CRC mismatch'
    if check_payload:
        assert frame[9:25] == bytes((seq+i)&255 for i in range(16)), 'payload mismatch'


def collect(args):
    image = (ROOT / 'probe-128k.bin').read_bytes()
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    assert hashlib.sha256(image).hexdigest() == manifest['image_sha256']
    assert hashlib.sha256((ROOT/'probe.asm').read_bytes()).hexdigest() == manifest['source_sha256']
    result = dict(manifest=manifest, host_delay=args.host_delay, reconnect=args.reconnect,
                  frames=[], snapshots=[], wire_hex='', acknowledgements=[], complete=False)
    result['collector_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    wire = bytearray()
    pending = bytearray()
    p = Pico()
    try:
        result['device'] = {k:p.get(k) for k in ('build_config','diag_version','addr_mask')}
        assert result['device']['build_config'] == 'POG_27C020_70ns'
        assert p.set('rom_enable','0') == '0'
        paused = time.monotonic()
        p.end()
        p.set('addr_mask','0x1ffff')
        p.write(0,image)
        assert p.read(0,len(image)) == image
        p.start(0x1dc00)
        time.sleep(max(0,3-(time.monotonic()-paused)))
        assert p.set('rom_enable','1') == '1'
        start = time.monotonic()
        if args.host_delay:
            time.sleep(args.host_delay)
            held = p.events(0x1dc00)
            result['held_snapshot'] = held
            assert held['count'] == 1+FRAME_SIZE and held['dropped_bytes'] == 0
        boot = False
        while time.monotonic()-start < 25+args.host_delay:
            chunk = p.poll()
            wire.extend(chunk)
            pending.extend(chunk)
            snapshot = p.events(0x1dc00)
            snapshot['host_elapsed'] = time.monotonic()-start
            result['snapshots'].append(snapshot)
            assert snapshot['dropped_bytes'] == 0 and not snapshot['capture_stopped']
            if not boot and pending:
                assert pending.pop(0) == 0xa0, 'missing boot marker'
                boot = True
            if len(result['frames']) == COUNT and pending:
                assert pending == b'\xfe', 'missing completion marker'
                pending.clear()
                result['complete'] = True
                break
            if boot and pending and pending[0] in (0xf1,0xf2):
                raise RuntimeError(f'CPU reported transport failure {pending[0]:02X}')
            if len(pending) >= FRAME_SIZE:
                frame = bytes(pending[:FRAME_SIZE]); del pending[:FRAME_SIZE]
                assert not pending, 'CPU transmitted without acknowledgement'
                seq = FIRST+len(result['frames'])
                check_frame(frame,seq)
                result['frames'].append(dict(sequence=seq,hex=frame.hex(),host_elapsed=time.monotonic()-start))
                if args.reconnect and len(result['frames']) == 10:
                    # CPU waits for this frame's ACK while the interface is released.
                    p.close(); p = None
                    time.sleep(2)
                    p = Pico()
                    after = p.events(0x1dc00)
                    assert after['count'] == snapshot['count'], 'CPU advanced without ACK'
                    result['reconnect_snapshot'] = after
                p.send(82,bytes([seq&255]))
                p.get('status')  # Fence ACK enqueue; CPU advances independently.
                result['acknowledgements'].append(seq&255)
            time.sleep(.002)
        assert result['complete'], 'timeout before completion'
        # The event stream independently contains each sent byte and one RX read per ACK.
        events = {}
        for snapshot in result['snapshots']:
            for event in snapshot['events']:
                seq = event['sequence']
                assert seq not in events or events[seq] == event
                events[seq] = event
        assert sorted(events) == list(range(result['snapshots'][-1]['count'])), 'missing trace records'
        expected = [0x1a0]
        for frame in result['frames']:
            expected.extend(0x100+b for b in bytes.fromhex(frame['hex']))
            expected.append(0)
        expected.append(0x1fe)
        assert [int(events[i]['address'],16) for i in sorted(events)] == expected
        assert wire == b'\xa0'+b''.join(bytes.fromhex(f['hex']) for f in result['frames'])+b'\xfe'
        result['validated'] = True
        print(f'PASS: {COUNT} CRC frames, {len(wire)} USB bytes, {len(events)} events; no drops or reset.')
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        result['wire_hex'] = wire.hex()
        (ROOT / (args.name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        if p is not None:
            try:
                p.end()
            finally:
                p.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','collect'])
    parser.add_argument('--host-delay',type=float,default=0)
    parser.add_argument('--reconnect',action='store_true')
    parser.add_argument('--name',default='capture')
    args = parser.parse_args()
    if args.action == 'collect': collect(args)
    else: globals()[args.action]()
