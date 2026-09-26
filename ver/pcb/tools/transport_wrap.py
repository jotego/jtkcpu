#!/usr/bin/env python3
"""Verify full firmware input-sequence wrap in a bounded frame capture."""
import argparse,hashlib,json,subprocess
import framed_probe as framed
from pico_link import Pico
ROOT=framed.timing.ROOT/'artifacts/framed-transport/input-wrap'
RUN_ID=0x7b03
SEED=0xfffffff0
class SeededPico(Pico):
    final_sequence=None
    def start(self,base=0x1dc00):
        assert self.get('rom_enable')=='0'
        super().start(base)
        self.write(base+12,SEED.to_bytes(4,'little'))
        assert int.from_bytes(self.read(base+12,4),'little')==SEED
        self.seeded=True
    def end(self):
        if getattr(self,'seeded',False):
            SeededPico.final_sequence=int.from_bytes(self.read(0x1dc0c,4),'little')
            self.seeded=False
        super().end()

def build():
    framed.ROOT=ROOT;framed.generate()
    source=(ROOT/'probe.asm').read_text().replace('LDD #$7B01','LDD #$7B03')
    old='        CLRA\n        STA $2E44\nNEXT_FRAME:'
    assert old in source;source=source.replace(old,'        LDA #$F0\n        STA $2E44\nNEXT_FRAME:')
    (ROOT/'probe.asm').write_text(source)
    m=json.loads((ROOT/'manifest.json').read_text());m.update(run_id=RUN_ID,input_sequence_seed=SEED,source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (ROOT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    with (ROOT/'assembly.log').open('w') as f:
        subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
    framed.package()
    assert bytes.fromhex('10f03a072e44') in (ROOT/'fixed.bin').read_bytes()

def collect():
    framed.ROOT=ROOT;framed.Pico=SeededPico;original=framed.check_frame
    framed.check_frame=lambda data,seq:original(data,seq,True,RUN_ID)
    framed.collect(argparse.Namespace(name='capture',host_delay=0,reconnect=False))
    assert SeededPico.final_sequence==(SEED+96)&0xffffffff
    summary=dict(seed=SEED,final_sequence=SeededPico.final_sequence,acknowledgements=96,validated=True,
       scope='Counter seeded while ROM disabled; exact low-byte CPU receiver crosses FF->00, and firmware uint32 counter crosses FFFFFFFF->00000000 within 96 ACKs. This does not test four billion uninterrupted exchanges.')
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(summary)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect']);a=p.parse_args();globals()[a.action]()
