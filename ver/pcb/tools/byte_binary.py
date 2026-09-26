#!/usr/bin/env python3
"""Guarded byte arithmetic/logical/load probes with full register records."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/byte-binary'
MODE='memory'
OPS=[(code+reg,name+('B' if reg else 'A'),'B' if reg else 'A') for code,name in [(0x12,'LD'),(0x16,'ADD'),(0x1a,'ADC'),(0x1e,'SUB'),(0x22,'SBC'),(0x26,'AND'),(0x2a,'BIT'),(0x2e,'EOR'),(0x32,'OR'),(0x36,'CMP')] for reg in (0,1)]
PAIRS=[(0,0),(0,1),(1,255),(255,1),(127,1),(128,1),(128,255),(15,1),(240,16),(85,170),(170,85),(255,255)]
CC=[0,1,32,33,0xde,0xdf,0xfe,0xff]
def cases(batch):
 op,name,reg=OPS[batch]
 if MODE=='immediate':op-=2
 return [dict(opcode=op,mnemonic=name,reg=reg,lhs=a,rhs=b,input_D=(a<<8|0xa5) if reg=='A' else (0x5a00|a),cc=cc) for a,b in PAIRS for cc in CC]
def configure(batch):
 root=BASE if MODE=='memory' else BASE.parent/'byte-binary-immediate'
 framed.ROOT=root/f'batch-{batch:02d}';return framed.ROOT,cases(batch),(0xae00 if MODE=='memory' else 0xaf00)+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 source=(TEMPLATES / 'single_record.asm').read_text()
 source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK').replace('LDD #$A500',f'LDD #${run_id:04X}')
 old='        PSHS A\n        LDX #$2F00';new='''        PSHS A
        LDA #$A5
        STA $2F3F
        LDA #$5A
        STA $2F41
        LDB 3,Y
        STB $2F40
        LDX #$2F00''';assert old in source;source=source.replace(old,new)
 source=source.replace('        SEX\n',f"        {rows[0]['mnemonic']} $2F40\n")
 old='        STD $2E17\n; CRC-16';new='''        STD $2E17
        LDA $2F3F
        CMPA #$A5
        LBNE RAM_FAIL
        LDA $2F41
        CMPA #$5A
        LBNE RAM_FAIL
        LDA $2F40
        CMPA $2E0C
        LBNE RAM_FAIL
; CRC-16''';assert old in source;source=source.replace(old,new)
 if MODE=='immediate':
  first=source.index('        LDX #$2F00',source.index('        STB $2F40'))
  last=source.index('        STD $2E0E',first)
  rhs_values=sorted({r['rhs'] for r in rows})
  body='        LDB $2E0C\n'
  for rhs in rhs_values:body+=f'        CMPB #${rhs:02X}\n        LBEQ OPERAND_{rhs:02X}\n'
  body+='        JMP RAM_FAIL\n'
  for rhs in rhs_values:
   body+=f'OPERAND_{rhs:02X}:\n        LDX #$2F00\n        LDU #$2F20\n        LDD ,Y\n        LDY #$2F10\n        PULS CC\n        {rows[0]["mnemonic"]} #${rhs:02X}\n        PSHS CC\n        JMP CAPTURE\n'
  body+='CAPTURE:\n';source=source[:first]+body+source[last:]
 first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
 table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['input_D']:04X},${r['rhs']:04X}\n        FCB ${r['cc']:02X}\n" for r in rows)
 source=source[:first]+table+source[last:];(root/'probe.asm').write_text(source)
 m=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as f:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 framed.package();fixed=(root/'fixed.bin').read_bytes()
 expected=b''.join(r['input_D'].to_bytes(2,'big')+r['rhs'].to_bytes(2,'big')+bytes([r['cc']]) for r in rows)
 assert fixed[0x1000:0x1000+len(expected)]==expected
 if MODE=='memory':assert fixed.count(bytes([14,1,rows[0]['opcode'],7,0x2f,0x40,12,1]))==1
 else:
  for rhs in {r['rhs'] for r in rows}:assert fixed.count(bytes([14,1,rows[0]['opcode'],rhs,12,1]))==1
 assert bytes.fromhex('0a54ff500000') in fixed

def model(r):
 a,b,cc=r['lhs'],r['rhs'],r['cc'];name=r['mnemonic'][:-1];carry=cc&1;h=bool(cc&32)
 if name in ('ADD','ADC'):
  extra=carry if name=='ADC' else 0;full=a+b+extra;v=full&255;c=full>255;h=((a&15)+(b&15)+extra)>15;overflow=bool((~(a^b)&(a^v))&128)
 elif name in ('SUB','SBC','CMP'):
  extra=carry if name=='SBC' else 0;full=a-b-extra;v=full&255;c=full<0;overflow=bool(((a^b)&(a^v))&128)
 else:
  v={'LD':b,'AND':a&b,'BIT':a&b,'EOR':a^b,'OR':a|b}[name];c=carry;overflow=False
 actual=a if name in ('BIT','CMP') else v
 d=(actual<<8|0xa5) if r['reg']=='A' else 0x5a00|actual
 flags=(cc&0xd0)|(32 if h else 0)|(8 if v&128 else 0)|(4 if v==0 else 0)|(2 if overflow else 0)|int(c)
 return d,flags

def analyze(batch):
 root,expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text());assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
 assert capture['manifest']['cases']==expected
 for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==capture['manifest'][key]
 rows=[];data_bad=[];flag_bad=[]
 for i,(frame,r) in enumerate(zip(capture['frames'],expected)):
  packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id);b=packet[9:25]
  assert b[:5]==r['input_D'].to_bytes(2,'big')+r['rhs'].to_bytes(2,'big')+bytes([r['cc']])
  assert b[7:13]==bytes.fromhex('2f002f102f20') and b[14:]==bytes.fromhex('beef')
  d=int.from_bytes(b[5:7],'big');pred,flags=model(r)
  assert (d&255)==0xa5 if r['reg']=='A' else d>>8==0x5a
  if d!=pred:data_bad.append(i)
  if b[13]!=flags:flag_bad.append(i)
  rows.append(dict(**r,output_D=d,output_CC=b[13]))
 (root/'results.json').write_text(json.dumps(dict(records=rows,candidate_data_mismatches=data_bad,candidate_flag_mismatches=flag_bad),indent=2)+'\n')
 print(batch,OPS[batch][1],'96 records; data/flag model mismatches',len(data_bad),len(flag_bad),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(20));p.add_argument('--mode',choices=['memory','immediate'],default='memory');a=p.parse_args();MODE=a.mode
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
