#!/usr/bin/env python3
"""RTI short/full frame flags and register restoration with guarded stacks."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,re,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/rti-flags'
def cases(batch):
 full=batch>=2
 rows=[dict(opcode=0x9f,mnemonic='RTI',full_frame=full,input_D=d,cc=cc,pre_CC=cc^255) for d in (0,0x1234,0xffff) for cc in range(128 if full else 0,256 if full else 128)]
 return rows[(batch%2)*192:(batch%2+1)*192]
def configure(batch):
 assert 0<=batch<4
 framed.ROOT=BASE/f'batch-{batch:02d}'
 return framed.ROOT,cases(batch),0xb840+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 full=rows[0]['full_frame']
 source=(TEMPLATES / 'packed_records.asm').read_text()
 source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK').replace('LDD #$A200',f'LDD #${run_id:04X}')
 first=source.index('        PSHS A\n');last=source.index('; CC and D are already captured',first)
 body='        LDA $2E63\n        STA $3F80\n'
 if full:
  body+='        LDD $2E60\n        STD $3F81\n        LDA #0\n        STA $3F83\n'
  for reg,offset,value in [('X',0x84,0x2f00),('Y',0x86,0x2f10),('U',0x88,0x2f20)]:
   body+=f'        LD{reg} #${value:04X}\n        ST{reg} $3F{offset:02X}\n'
 body+=f'        LDX #DESTINATION\n        STX ${0x3f8a if full else 0x3f81:04X}\n'
 body+='        LDS #$3F80\n        LDA $2E63\n        EORA #$FF\n        PSHS A\n        LDD $2E60\n'
 if full:body+='        COMA\n        COMB\n'
 for reg,value in [('X',0x2f50 if full else 0x2f00),('Y',0x2f60 if full else 0x2f10),('U',0x2f70 if full else 0x2f20)]:body+=f'        LD{reg} #${value:04X}\n'
 body+=f"""        PULS CC
TARGET:
        RTI
        JMP RAM_FAIL
DESTINATION:
        PSHS CC
        STD $2E64
        PULS A
        STA $2E66
        CMPS #${0x3f8c if full else 0x3f83:04X}
        LBNE RAM_FAIL
        LDS #$3FF0
"""
 source=source[:first]+body+source[last:]
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
 labels={n:int(a,16) for a,n in re.findall(r'^\s*\d+/([0-9A-F]{4}) :\s+(TARGET|DESTINATION):',(root/'probe.lst').read_text(),re.M)}
 assert len(labels)==2
 pos=labels['TARGET']-0x8000;dest=labels['DESTINATION']
 assert fixed[pos-2:pos+1]==bytes([14,1,0x9f])
 assert fixed[dest-0x8000:dest-0x8000+2]==bytes([12,1])
 assert bytes([0x42])+dest.to_bytes(2,'big')+bytes([0x59,7])+(0x3f8a if full else 0x3f81).to_bytes(2,'big') in fixed
 assert bytes([0x52])+(0x3f8c if full else 0x3f83).to_bytes(2,'big') in fixed
 assert bytes.fromhex('0a54ff500000') in fixed
 manifest=json.loads((root/'manifest.json').read_text());manifest['control_labels']=labels
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

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
   assert b[4:6]==r['input_D'].to_bytes(2,'big') and b[7]==0xe7
   if r['cc']!=b[6]:bad.append(2*i+slot)
   records.append(dict(**r,output_D=int.from_bytes(b[4:6],'big'),output_CC=b[6]))
 (root/'results.json').write_text(json.dumps(dict(records=records,changed_CC_indices=bad),indent=2)+'\n')
 print(batch,expected[0]['mnemonic'],'192 guarded records; CC changes',len(bad),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(4));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
