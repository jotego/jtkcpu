#!/usr/bin/env python3
"""Decrement-and-branch results, outcomes and flags with immediate capture."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/decrement-branch'
def cases(batch):
 word=batch>=8;op=0xad if word else 0xac;page=batch%8
 values=(0,1,2,0x7fff,0x8000,0xffff) if word else (0,1,2,0x7f,0x80,0xff)
 return [dict(opcode=op,mnemonic='DECX,JNZ' if word else 'DECB,JNZ',width=16 if word else 8,value=v,input_D=v if word else 0x5a00|v,cc=cc,taken=v!=1)
         for v in values for cc in range(page*32,page*32+32)]
def configure(batch):
 assert 0<=batch<16
 framed.ROOT=BASE/f'batch-{batch:02d}'
 return framed.ROOT,cases(batch),0xb700+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 word=rows[0]['width']==16;op=rows[0]['opcode']
 source=(TEMPLATES / 'packed_records.asm').read_text()
 source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK').replace('LDD #$A200',f'LDD #${run_id:04X}')
 first=source.index('        LDB $2E62');last=source.index('; CC and D are already captured',first)
 setup='        LDX $2E60\n        LDD #$1234\n' if word else '        LDX #$2F00\n        LDD $2E60\n'
 body='        LDY #$2F10\n        LDU #$2F20\n'+setup+f'''        PULS CC
; Inventoried two-byte opcode, relative displacement from following opcode.
        FCB ${op:02X},TAKEN-(*+2)
        PSHS CC
        JMP CAPTURE_NOT
TAKEN:
        PSHS CC
        JMP CAPTURE_TAKEN
'''
 save='        STX $2E64\n        CMPD #$1234\n        LBNE RAM_FAIL\n' if word else '        STD $2E64\n'
 for label,marker in [('CAPTURE_NOT',0xe6),('CAPTURE_TAKEN',0xe7)]:
  body+=label+':\n'+save+f'''        PULS A
        STA $2E66
        LDA #${marker:02X}
        STA $2E67
        JMP CHECK_REGS
'''
 body+='CHECK_REGS:\n';source=source[:first]+body+source[last:]
 if word:source=source.replace('        CMPX #$2F00\n        LBNE RAM_FAIL\n','')
 source=source.replace('        LDA #$E7\n        STA ,X+','        LDA $2E67\n        STA ,X+')
 first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
 source=source[:first]+'        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['input_D']:04X},${r['opcode']:04X}\n        FCB ${r['cc']:02X}\n" for r in rows)+source[last:]
 (root/'probe.asm').write_text(source)
 manifest=dict(first=240,count=96,frame_size=27,records_per_frame=2,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with (root/'assembly.log').open('w') as f:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 framed.package();fixed=(root/'fixed.bin').read_bytes()
 expected=b''.join(r['input_D'].to_bytes(2,'big')+r['opcode'].to_bytes(2,'big')+bytes([r['cc']]) for r in rows)
 assert fixed[0x1000:0x1000+len(expected)]==expected
 pattern=bytes([14,1,op,6,12,1]);assert fixed.count(pattern)==1
 pos=fixed.index(pattern)+2;assert fixed[pos+2+6:pos+2+8]==bytes([12,1])
 assert bytes.fromhex('0a54ff500000') in fixed

def analyze(batch):
 root,expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text())
 assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
 assert capture['manifest']['cases']==expected
 for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
  assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==capture['manifest'][key]
 records=[];bad=[]
 for i,frame in enumerate(capture['frames']):
  packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id)
  for slot in range(2):
   r=expected[2*i+slot];b=packet[9+slot*8:17+slot*8]
   assert b[:4]==r['input_D'].to_bytes(2,'big')+bytes([r['opcode'],r['cc']])
   value=(r['value']-1)&((1<<r['width'])-1)
   encoded=value if r['width']==16 else 0x5a00|value
   assert b[4:6]==encoded.to_bytes(2,'big') and b[7]==0xe6+int(r['taken'])
   flags=(r['cc']&0xf1)|(8 if value&(1<<(r['width']-1)) else 0)|(4 if value==0 else 0)|(2 if r['value']==1<<(r['width']-1) else 0)
   if flags!=b[6]:bad.append(2*i+slot)
   records.append(dict(**r,output_value=value,output_CC=b[6],observed_taken=bool(b[7]&1)))
 (root/'results.json').write_text(json.dumps(dict(records=records,candidate_flag_mismatches=bad),indent=2)+'\n')
 print(batch,expected[0]['mnemonic'],'192 data/outcome records; DEC flag model mismatches',len(bad),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(16));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
