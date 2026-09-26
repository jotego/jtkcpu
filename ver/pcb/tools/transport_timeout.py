#!/usr/bin/env python3
"""Exercise the production probe's full ACK timeout and recovery on the PCB."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
import framed_probe as framed
from pico_link import Pico
ROOT=framed.timing.ROOT/'artifacts/framed-transport/timeout'
RUN_ID=0x7b02

def build():
    framed.ROOT=ROOT;framed.generate()
    source=(ROOT/'probe.asm').read_text().replace('LDD #$7B01','LDD #$7B02')
    assert '        LDU #$0800\nWAIT_BLOCK:' in source
    (ROOT/'probe.asm').write_text(source)
    m=json.loads((ROOT/'manifest.json').read_text());m.update(run_id=RUN_ID,source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (ROOT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    with (ROOT/'assembly.log').open('w') as f:
        subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    framed.package()

def collect():
    image=(ROOT/'probe-128k.bin').read_bytes();manifest=json.loads((ROOT/'manifest.json').read_text())
    assert hashlib.sha256(image).hexdigest()==manifest['image_sha256']
    assert hashlib.sha256((ROOT/'probe.asm').read_bytes()).hexdigest()==manifest['source_sha256']
    result=dict(manifest=manifest,snapshots=[],wire_hex='',validated=False,acknowledgements_sent=0)
    p=Pico();wire=bytearray()
    try:
        result['device']={k:p.get(k) for k in ('build_config','diag_version','addr_mask')}
        assert result['device']['build_config']=='POG_27C020_70ns'
        assert p.set('rom_enable','0')=='0';paused=time.monotonic();p.end()
        p.set('addr_mask','0x1ffff');p.write(0,image);assert p.read(0,len(image))==image
        p.start(0x1dc00);time.sleep(max(0,3-(time.monotonic()-paused)));p.set('rom_enable','1')
        start=time.monotonic();timeout_seen=None;first_frame=None
        while time.monotonic()-start<180:
            wire.extend(p.poll());snap=p.events(0x1dc00);snap['host_elapsed']=time.monotonic()-start;result['snapshots'].append(snap)
            assert snap['dropped_bytes']==0 and not snap['capture_stopped']
            assert len(wire)<=29
            if len(wire)>=28:
                assert wire[0]==0xa0
                framed.check_frame(bytes(wire[1:28]),240,True,RUN_ID)
                if first_frame is None:first_frame=time.monotonic()-start;print('First CRC frame received; withholding ACK',flush=True)
            if len(wire)==29:
                assert wire[-1]==0xf2,'expected timeout marker F2'
                if timeout_seen is None:timeout_seen=time.monotonic()-start;print('Timeout reported after',timeout_seen-first_frame,'seconds',flush=True)
                if time.monotonic()-start-timeout_seen>=3:break
            time.sleep(.01)
        assert timeout_seen is not None and time.monotonic()-start-timeout_seen>=3
        events={}
        for snap in result['snapshots']:
            for event in snap['events']:
                i=event['sequence'];assert i not in events or events[i]==event;events[i]=event
        assert sorted(events)==list(range(29))
        assert [int(events[i]['address'],16) for i in range(29)]==[0x100+b for b in wire]
        result.update(validated=True,timeout_after_frame_seconds=timeout_seen-first_frame,stable_after_timeout_seconds=time.monotonic()-start-timeout_seen)
        print('PASS: frame, F2 timeout, no RX, no reboot/drop, three-second stable idle',flush=True)
    except Exception as e:result['error']=str(e);raise
    finally:
        result['wire_hex']=wire.hex();(ROOT/'timeout.json').write_text(json.dumps(result,indent=2)+'\n');p.end();p.close()

def recover():
    framed.ROOT=ROOT;original=framed.check_frame
    framed.check_frame=lambda data,seq:original(data,seq,True,RUN_ID)
    framed.collect(argparse.Namespace(name='recovery',host_delay=0,reconnect=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','recover']);a=p.parse_args();globals()[a.action]()
