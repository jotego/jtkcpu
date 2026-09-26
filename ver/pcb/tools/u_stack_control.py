#!/usr/bin/env python3
"""Full-CC NOP control for the U-stack capture path with arbitrary S."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import word_stack_pointer as probe
framed=probe.framed
BASE=framed.timing.ROOT/'artifacts/u-stack-control'
def cases():
 return [dict(opcode=0xae,mnemonic='NOP',reg='S',lhs=s,rhs=0,input_value=s,cc=cc) for s in (0,0x8000,0xffff) for cc in range(256)]
def configure(batch):
 framed.ROOT=BASE/f'batch-{batch:02d}';return framed.ROOT,cases()[batch*96:(batch+1)*96],0xb280+batch
probe.configure=configure;probe.model=lambda r:(r['lhs'],r['cc']);probe.OPS=[(0xae,'NOP','S')]*8

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 template=TEMPLATES / 'stack_pointer.asm'
 source=template.read_text();assert source.count('        CMPS $2F40\n')==1
 source=source.replace('        CMPS $2F40\n','        NOP\n').replace('LDD #$B201',f'LDD #${run_id:04X}')
 first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
 table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['lhs']:04X},$0000\n        FCB ${r['cc']:02X}\n" for r in rows)
 source=source[:first]+table+source[last:];assert 'PSHS' not in source and 'PULS' not in source
 (root/'probe.asm').write_text(source)
 m=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest(),template_sha256=hashlib.sha256(template.read_bytes()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as f:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 framed.package();fixed=(root/'fixed.bin').read_bytes()
 assert fixed.count(bytes.fromhex('0f01ae0d01'))==1
 expected=b''.join(r['lhs'].to_bytes(2,'big')+b'\0\0'+bytes([r['cc']]) for r in rows)
 assert fixed[0x1000:0x1000+len(expected)]==expected
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(8));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':probe.analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
