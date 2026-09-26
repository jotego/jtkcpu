#!/usr/bin/env python3
"""ANDCC/ORCC masks with all initial CC states, two records per frame."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/cc-logic'
MASKS=(0,0xff,0x55,0xaa,1,2,4,8,0x10,0x20,0x40,0x80)
def cases(batch):
 op=0x3c+batch//16;name='ANDCC' if op==0x3c else 'ORCC';page=batch%16
 return [dict(opcode=op,mnemonic=name,mask=mask,input_D=mask<<8|0xa5,cc=cc)
         for mask in MASKS for cc in range(page*16,page*16+16)]
def configure(batch):
 assert 0<=batch<32
 framed.ROOT=BASE/f'batch-{batch:02d}'
 return framed.ROOT,cases(batch),0xb600+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 source=(TEMPLATES / 'packed_records.asm').read_text()
 source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK').replace('LDD #$A200',f'LDD #${run_id:04X}')
 first=source.index('        LDB $2E62');last=source.index('CAPTURE:\n',first)
 body='        LDA $2E60\n'
 for mask in MASKS:body+=f'        CMPA #${mask:02X}\n        LBEQ MASK_{mask:02X}\n'
 body+='        JMP RAM_FAIL\n'
 for mask in MASKS:
  body+=f'''MASK_{mask:02X}:
        LDX #$2F00
        LDY #$2F10
        LDU #$2F20
        LDD $2E60
        PULS CC
        {rows[0]['mnemonic']} #${mask:02X}
        PSHS CC
        JMP CAPTURE
'''
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
 for mask in MASKS:assert fixed.count(bytes([14,1,rows[0]['opcode'],mask,12,1]))==1
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
   assert b[4:6]==r['input_D'].to_bytes(2,'big') and b[7]==0xe7
   flags=r['cc']&r['mask'] if r['opcode']==0x3c else r['cc']|r['mask']
   if flags!=b[6]:bad.append(2*i+slot)
   records.append(dict(**r,output_D=int.from_bytes(b[4:6],'big'),output_CC=b[6]))
 (root/'results.json').write_text(json.dumps(dict(records=records,candidate_flag_mismatches=bad),indent=2)+'\n')
 print(batch,expected[0]['mnemonic'],'192 records; candidate flag mismatches',len(bad),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(32));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
