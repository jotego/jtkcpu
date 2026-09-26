#!/usr/bin/env python3
"""Fixed raw transfer probes with varied register seeds and no opcode dispatcher."""
import argparse
import hashlib
import json
import subprocess

import framed_probe as framed

BASE = framed.timing.ROOT / 'artifacts/transfer-confirmation'
ENCODINGS = [(op, post) for post in (0x23, 0x42, 0x20, 0x41) for op in (0x3e, 0x3f)]
WORDS = (0, 1, 2, 0x3fff, 0x4000, 0x5555, 0x7fff, 0x8000, 0x8001, 0xaaaa, 0xfffe, 0xffff)
CC = (0, 1, 4, 5, 8, 9, 0x72, 255)


def configure(batch):
    framed.ROOT = BASE / f'batch-{batch:02d}'
    op, post = ENCODINGS[batch]
    rows = [dict(opcode=op, postbyte=post, cc=cc, D=0x3c96 ^ (i * 0x1111),
                 X=word, Y=word ^ 0xa55a, DPword=word ^ 0x5ac3)
            for i, word in enumerate(WORDS) for cc in CC]
    return framed.ROOT, rows, 0xbf00 + batch


def build(batch):
    root, rows, run_id = configure(batch)
    framed.generate()
    source = (root / 'probe.asm').read_text().replace('LDD #$7B01', f'LDD #${run_id:04X}')
    first = source.index('        LDX #$2E09')
    last = source.index('; CRC-16/CCITT-FALSE', first)
    op, post = ENCODINGS[batch]
    body = f'''        LDS #$3FF0
        LDD $2E42
        SUBD #$00F0
        LDA #9
        MUL
        LDY #OPERANDS
        LEAY D,Y
        LDD ,Y
        STD $2E60
        LDD 2,Y
        STD $2E62
        LDD 4,Y
        STD $2E64
        LDX 6,Y
        FCB $3E,$42 ; seed full physical selector4 before loading target registers
        LDA 8,Y
        STA $2E0B
        PSHS A
        LDD #${op:02X}{post:02X}
        STD $2E09
        LDD $2E60
        LDX $2E62
        LDY $2E64
        LDU #$3FE0
        PULS CC
        FCB ${op:02X},${post:02X}
        PSHS CC
        STD $2E0C
        STX $2E0E
        STY $2E10
        PULS A
        STA $2E16
        STU $2E12
        STS $2E14
        PSHS DP
        PULS A
        STA $2E17
        LDA #$EF
        STA $2E18
'''
    source = source[:first] + body + source[last:]
    first = source.index('        ORG $FFF6')
    table = '        ORG $9000\nOPERANDS:\n' + ''.join(
        f"        FDB ${r['D']:04X},${r['X']:04X},${r['Y']:04X},${r['DPword']:04X}\n        FCB ${r['cc']:02X}\n" for r in rows)
    source = source[:first] + table + source[first:]
    (root / 'probe.asm').write_text(source)
    manifest = dict(first=240, count=96, frame_size=27, run_id=run_id, cases=rows,
                    source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    with (root / 'assembly.log').open('w') as log:
        subprocess.run(['asl', '-cpu', '052001', 'probe.asm', '-L'], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['p2bin', 'probe.p', 'fixed.bin', '-r', '0x8000-0xffff', '-l', '255'], cwd=root, stdout=log, stderr=subprocess.STDOUT, check=True)
    fixed = (root / 'fixed.bin').read_bytes()
    assert fixed.count(bytes([0x0e, 1, op, post, 0x0c, 1])) == 1
    expected = b''.join(b''.join(r[k].to_bytes(2, 'big') for k in ('D', 'X', 'Y', 'DPword')) + bytes([r['cc']]) for r in rows)
    assert fixed[0x1000:0x1000+len(expected)] == expected
    framed.package()


def predicted(row):
    a, b = row['D'] >> 8, row['D'] & 255
    values = [b << 8 | a, a << 8 | b, row['X'], row['Y'], row['DPword'], 0x3fe0]
    src, dst = row['postbyte'] & 15, row['postbyte'] >> 4
    result = values.copy()
    result[src], result[dst] = values[dst], values[src]
    return dict(A=result[0] & 255, B=result[1] & 255, X=result[2], Y=result[3],
                U=result[5], S=0x3ff0, DP=result[4] >> 8, CC=row['cc'])


def analyze(batch):
    root, rows, run_id = configure(batch)
    capture = json.loads((root / 'capture.json').read_text())
    assert capture['validated'] and capture['complete'] and len(capture['frames']) == 96
    assert capture['manifest']['cases'] == rows
    for filename, key in [('probe.asm', 'source_sha256'), ('probe-128k.bin', 'image_sha256')]:
        assert hashlib.sha256((root / filename).read_bytes()).hexdigest() == capture['manifest'][key]
    records, mismatches = [], []
    for i, (frame, row) in enumerate(zip(capture['frames'], rows)):
        packet = bytes.fromhex(frame['hex'])
        framed.check_frame(packet, 240+i, False, run_id)
        payload = packet[9:25]
        assert payload[:3] == bytes([row['opcode'], row['postbyte'], row['cc']]) and payload[15] == 0xef
        result = dict(A=payload[3], B=payload[4], X=int.from_bytes(payload[5:7], 'big'),
                      Y=int.from_bytes(payload[7:9], 'big'), U=int.from_bytes(payload[9:11], 'big'),
                      S=int.from_bytes(payload[11:13], 'big'), CC=payload[13], DP=payload[14])
        records.append(dict(input=row, output=result))
        if result != predicted(row):
            mismatches.append(i)
    summary = dict(records=records, candidate_mismatch_indices=mismatches)
    (root / 'results.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(f'batch {batch}: {len(records)} records; {len(mismatches)} model mismatches', flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'collect', 'analyze'))
    parser.add_argument('batch', type=int, choices=range(len(ENCODINGS)))
    args = parser.parse_args()
    if args.action == 'build':
        build(args.batch)
    elif args.action == 'analyze':
        analyze(args.batch)
    else:
        root, rows, run_id = configure(args.batch)
        original = framed.check_frame
        framed.check_frame = lambda data, seq: original(data, seq, False, run_id)
        args.name, args.host_delay, args.reconnect = 'capture', 0, False
        framed.collect(args)


if __name__ == '__main__':
    main()
