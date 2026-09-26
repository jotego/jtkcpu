#!/usr/bin/env python3
"""Guarded ABX addition and condition-code probes."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/abx-flags'
MODE='immediate'
OPS=[(0xb1,'ABX','X')]
PAIRS=[(0,0),(0,1),(0,0xff),(0x7fff,1),(0x8000,0x80),(0xffff,0),(0xffff,1),(0xffff,0xff),(0xff80,0x80),(0xff01,0xff),(0x1234,0x55),(0xaaaa,0xaa)]
CC=[0,1,4,5,8,9,0x72,0xff]
def cases(batch):
 op,name,reg=OPS[batch]
 if MODE=='immediate':op-=1
 return [dict(opcode=op,mnemonic=name,reg=reg,lhs=a,rhs=b,input_value=a,cc=cc) for a,b in PAIRS for cc in CC]
def configure(batch):
 root=BASE
 framed.ROOT=root/f'batch-{batch:02d}';return framed.ROOT,cases(batch),0xb500+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 source=(TEMPLATES / 'single_record.asm').read_text()
 source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK').replace('LDD #$A500',f'LDD #${run_id:04X}')
 old='        PSHS A\n        LDX #$2F00';new='''        PSHS A
        LDA #$A5
        STA $2F3F
        LDA #$5A
        STA $2F42
        LDD 2,Y
        STD $2F40
        LDX #$2F00''';assert old in source;source=source.replace(old,new)
 source=source.replace('        SEX\n',f"        {rows[0]['mnemonic']} $2F40\n")
 old='        STD $2E17\n; CRC-16';new='''        STD $2E17
        LDA $2F3F
        CMPA #$A5
        LBNE RAM_FAIL
        LDA $2F42
        CMPA #$5A
        LBNE RAM_FAIL
        LDD $2F40
        CMPD $2E0B
        LBNE RAM_FAIL
; CRC-16''';assert old in source;source=source.replace(old,new)
 if MODE=='immediate':
  first=source.index('        LDX #$2F00',source.index('        STD $2F40'))
  last=source.index('        STD $2E0E',first)
  rhs_values=sorted({r['rhs'] for r in rows})
  body='        LDD $2E0B\n'
  for rhs in rhs_values:body+=f'        CMPD #${rhs:04X}\n        LBEQ OPERAND_{rhs:02X}\n'
  body+='        JMP RAM_FAIL\n'
  for rhs in rhs_values:
   body+=f'OPERAND_{rhs:02X}:\n        LDX #$2F00\n        LDU #$2F20\n        LDD ,Y\n        LDY #$2F10\n        PULS CC\n        {rows[0]["mnemonic"]}\n        PSHS CC\n        JMP CAPTURE\n'
  body+='CAPTURE:\n';source=source[:first]+body+source[last:]
 first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
 table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['input_value']:04X},${r['rhs']:04X}\n        FCB ${r['cc']:02X}\n" for r in rows)
 source=source[:first]+table+source[last:]
 restore=f'        STD $2E60\n        LDD #$1234\n        LD{rows[0]["reg"]} $2E60\n        LDB $2E0C\n        PULS CC\n'
 assert source.count('        PULS CC\n')==(1 if MODE=='memory' else len({r['rhs'] for r in rows}))
 source=source.replace('        PULS CC\n',restore)
 if rows[0]['reg']=='S':
  source=source.replace('        PSHS A\n','        LDU #$3FE0\n        PSHU A\n').replace('        LDU #$2F20\n','')
  source=source.replace('        PULS CC\n','        PULU CC\n').replace('        PSHS CC\n','        PSHU CC\n')
  source=source.replace('        STU $2E14\n','').replace('        PULS A\n        STA $2E16\n','        PULU A\n        STA $2E16\n        STU $2E14\n')
  source=source.replace('        LDD #$BEEF\n        STD $2E17\n','        STS $2E17\n        LDS #$3FF0\n')
  assert 'PSHS' not in source and 'PULS' not in source
 (root/'probe.asm').write_text(source)
 m=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as f:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 framed.package();fixed=(root/'fixed.bin').read_bytes()
 expected=b''.join(r['input_value'].to_bytes(2,'big')+r['rhs'].to_bytes(2,'big')+bytes([r['cc']]) for r in rows)
 assert fixed[0x1000:0x1000+len(expected)]==expected
 assert fixed.count(bytes.fromhex('0e01b00c01'))==len({r['rhs'] for r in rows})
 assert bytes.fromhex('0a54ff500000') in fixed

def model(r):
 return (r['lhs']+r['rhs'])&0xffff,r['cc']

def analyze(batch):
 root,expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text());assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
 assert capture['manifest']['cases']==expected
 for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==capture['manifest'][key]
 rows=[];data_bad=[];flag_bad=[]
 for i,(frame,r) in enumerate(zip(capture['frames'],expected)):
  packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id);b=packet[9:25]
  assert b[:5]==r['input_value'].to_bytes(2,'big')+r['rhs'].to_bytes(2,'big')+bytes([r['cc']])
  assert b[5:7]==bytes([0x12,r['rhs']])
  if r['reg']!='S':assert b[14:]==bytes.fromhex('beef')
  registers={reg:int.from_bytes(b[pos:pos+2],'big') for reg,pos in [('X',7),('Y',9),('U',11)]}
  if r['reg']=='S':registers['S']=int.from_bytes(b[14:16],'big')
  for reg,value in [('X',0x2f00),('Y',0x2f10),('U',0x3fe0 if r['reg']=='S' else 0x2f20)]:
   if reg!=r['reg']:assert registers[reg]==value
  d=int.from_bytes(b[5:7],'big');pred,flags=model(r)
  if registers[r['reg']]!=pred:data_bad.append(i)
  if b[13]!=flags:flag_bad.append(i)
  rows.append(dict(**r,output_D=d,output_registers=registers,output_CC=b[13]))
 (root/'results.json').write_text(json.dumps(dict(records=rows,candidate_data_mismatches=data_bad,candidate_flag_mismatches=flag_bad),indent=2)+'\n')
 print(batch,OPS[batch][1],'96 records; data/flag model mismatches',len(data_bad),len(flag_bad),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(1));p.add_argument('--mode',choices=['immediate'],default='immediate');a=p.parse_args();MODE=a.mode
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
