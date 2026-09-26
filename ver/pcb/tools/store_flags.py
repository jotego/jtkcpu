#!/usr/bin/env python3
"""Guarded byte/word stores, with U-stack CC capture for arbitrary S."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/store-flags'
OPS=[(0x3a,'STA','A',8),(0x3b,'STB','B',8),(0x58,'STD','D',16),(0x59,'STX','X',16),(0x5a,'STY','Y',16),(0x5b,'STU','U',16),(0x5c,'STS','S',16)]
CC=[0,1,4,5,8,9,0x72,0xff]
def cases(batch):
 op,name,reg,width=OPS[batch];mask=(1<<width)-1;sign=1<<(width-1)
 values=[0,1,2,sign//2-1,sign//2,mask//3,sign-1,sign,sign+1,2*(mask//3),mask-1,mask]
 return [dict(opcode=op,mnemonic=name,reg=reg,width=width,value=v,initial_memory=v^mask,cc=cc) for v in values for cc in CC]
def configure(batch):
 framed.ROOT=BASE/f'batch-{batch:02d}';return framed.ROOT,cases(batch),0xb300+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True);op,name,reg,width=OPS[batch]
 template=TEMPLATES / 'word_register.asm';source=template.read_text().replace('LDD #$B100',f'LDD #${run_id:04X}')
 assert source.count('        LDX $2F40\n')==1
 source=source.replace('        LDX $2F40\n',f'        {name} $2F40\n')
 setup={'A':'        LDA $2E61\n        LDB #$A5\n','B':'        LDA #$5A\n        LDB $2E61\n'}.get(reg,f'        LD{reg} $2E60\n')
 source=source.replace('        LDX $2E60\n',setup)
 guard='        LDD $2F40\n        CMPD $2E0B\n        LBNE RAM_FAIL\n';assert guard in source;source=source.replace(guard,'')
 load='        LDD $2F40\n' if width==16 else '        CLRA\n        LDB $2F40\n'
 source=source.replace('        LDD #$BEEF\n        STD $2E17\n',load+'        STD $2E17\n')
 if width==8:source=source.replace('$2F42','$2F41').replace('        STD $2F40\n','        STB $2F40\n')
 if reg=='S':
  source=source.replace('        PSHS A\n','        LDU #$3FE0\n        PSHU A\n').replace('        LDU #$2F20\n','')
  source=source.replace('        PULS CC\n','        PULU CC\n').replace('        PSHS CC\n','        PSHU CC\n')
  source=source.replace('        STU $2E14\n','').replace('        PULS A\n        STA $2E16\n','        PULU A\n        STA $2E16\n        STU $2E14\n        CMPS $2E60\n        LBNE RAM_FAIL\n        LDS #$3FF0\n')
  assert 'PSHS' not in source and 'PULS' not in source
 first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
 table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['value']:04X},${r['initial_memory']:04X}\n        FCB ${r['cc']:02X}\n" for r in rows)
 source=source[:first]+table+source[last:];(root/'probe.asm').write_text(source)
 m=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest(),template_sha256=hashlib.sha256(template.read_bytes()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as f:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 framed.package();fixed=(root/'fixed.bin').read_bytes()
 assert fixed.count(bytes([15 if reg=='S' else 14,1,op,7,0x2f,0x40,13 if reg=='S' else 12,1]))==1
 expected=b''.join(r['value'].to_bytes(2,'big')+r['initial_memory'].to_bytes(2,'big')+bytes([r['cc']]) for r in rows)
 assert fixed[0x1000:0x1000+len(expected)]==expected
 assert bytes.fromhex('0a54ff500000') in fixed

def analyze(batch):
 root,expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text());assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
 assert capture['manifest']['cases']==expected
 for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==capture['manifest'][key]
 rows=[];bad=[]
 for i,(frame,r) in enumerate(zip(capture['frames'],expected)):
  packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id);b=packet[9:25]
  assert b[:5]==r['value'].to_bytes(2,'big')+r['initial_memory'].to_bytes(2,'big')+bytes([r['cc']])
  regs={key:int.from_bytes(b[pos:pos+2],'big') for key,pos in [('D',5),('X',7),('Y',9),('U',11)]}
  wanted=dict(D=0x1234,X=0x2f00,Y=0x2f10,U=0x3fe0 if r['reg']=='S' else 0x2f20)
  if r['reg']=='A':wanted['D']=r['value']<<8|0xa5
  elif r['reg']=='B':wanted['D']=0x5a00|r['value']
  elif r['reg']!='S':wanted[r['reg']]=r['value']
  assert regs==wanted,(r,regs,wanted)
  memory=int.from_bytes(b[14:16],'big');assert memory==r['value']
  flags=(r['cc']&0xf1)|(8 if memory&(1<<(r['width']-1)) else 0)|(4 if memory==0 else 0)
  if flags!=b[13]:bad.append(i)
  rows.append(dict(**r,output_registers=regs,output_memory=memory,output_CC=b[13]))
 (root/'results.json').write_text(json.dumps(dict(records=rows,candidate_flag_mismatches=bad),indent=2)+'\n')
 print(OPS[batch][1],'96 records; flag-model mismatches',len(bad),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(7));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
