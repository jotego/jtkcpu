#!/usr/bin/env python3
"""SETLINES flags with independent bank signatures and RAM operand guards."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/setlines-flags'
MASKS=tuple(range(32))
def cases(batch):
 op=0x38+batch//4
 pairs=[(bank,cc) for bank in (0,31) for cc in range(256)]
 pairs += [(bank,cc) for bank in range(32) for cc in (0,1,4,5,8,9,0x72,0xff)]
 rows=[dict(opcode=op,mnemonic='SETLINES',mode='immediate' if op==0x38 else 'extended RAM',mask=bank,input_D=bank<<8|0xa5,cc=cc) for bank,cc in pairs]
 return rows[(batch%4)*192:(batch%4+1)*192]
def configure(batch):
 assert 0<=batch<8
 framed.ROOT=BASE/f'batch-{batch:02d}'
 return framed.ROOT,cases(batch),0xb900+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 source=(TEMPLATES / 'packed_records.asm').read_text()
 source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK').replace('LDD #$A200',f'LDD #${run_id:04X}')
 first=source.index('        LDB $2E62');last=source.index('CAPTURE:\n',first)
 body='        LDA $2E60\n        STA $2F40\n        LDA #$A5\n        STA $2F3F\n        LDA #$5A\n        STA $2F41\n        LDA $2E60\n'
 for mask in MASKS:body+=f'        CMPA #${mask:02X}\n        LBEQ MASK_{mask:02X}\n'
 body+='        JMP RAM_FAIL\n'
 for mask in MASKS:
  body+=f'''MASK_{mask:02X}:
        LDX #$2F00
        LDY #$2F10
        LDU #$2F20
        LDD $2E60
        PULS CC
        SETLINES {f'#${mask:02X}' if rows[0]['opcode']==0x38 else '>$2F40'}
        PSHS CC
        JMP CAPTURE
'''
 source=source[:first]+body+source[last:]
 guard="""        LDA $2F3F
        CMPA #$A5
        LBNE RAM_FAIL
        LDA $2F41
        CMPA #$5A
        LBNE RAM_FAIL
        LDA $2F40
        CMPA $2E60
        LBNE RAM_FAIL
        LDA $1B00
        CMPA #$5A
        LBNE RAM_FAIL
        LDA $1B03
        CMPA #$A5
        LBNE RAM_FAIL
        LDA $1B01
        STA $2E67
        LDA $2E60
        ANDA #$0F
        CMPA $2E67
        LBNE RAM_FAIL
        EORA #$FF
        CMPA $1B02
        LBNE RAM_FAIL
        SETLINES #0
        LDA $1B01
        CMPA #0
        LBNE RAM_FAIL
"""
 mark='; Eight-byte record:';where=source.index(mark)
 source=source[:where]+guard+source[where:]
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
 if rows[0]['opcode']==0x38:
  for mask in MASKS:assert fixed.count(bytes([14,1,0x38,mask,12,1]))==1
 else:assert fixed.count(bytes.fromhex('0e0139072f400c01'))==32
 assert bytes.fromhex('0a54ff500000') in fixed
 image=bytearray((root/'probe-128k.bin').read_bytes());signatures=[]
 for bank in range(16):
  offset=bank*0x2000+0x1b00;signature=bytes([0x5a,bank,bank^255,0xa5])
  assert image[offset:offset+4]==bytes([0 if bank<12 else 255])*4
  image[offset:offset+4]=signature
  signatures.append(dict(physical_bank=bank,physical_offset=offset,hex=signature.hex()))
 assert image[0x1dc00:0x1e000]==bytes([255])*1024
 assert image[0x18000:0x1801a]==fixed[:26] and image[-2:]==bytes.fromhex('8000')
 (root/'probe-128k.bin').write_bytes(image)
 manifest=json.loads((root/'manifest.json').read_text())
 manifest.update(bank_signatures=signatures,image_sha256=hashlib.sha256(image).hexdigest())
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
   assert b[4:6]==r['input_D'].to_bytes(2,'big') and b[7]==r['mask']&15
   flags=r['cc']
   if flags!=b[6]:bad.append(2*i+slot)
   records.append(dict(**r,output_D=int.from_bytes(b[4:6],'big'),output_CC=b[6],observed_bank=b[7]))
 (root/'results.json').write_text(json.dumps(dict(records=records,candidate_flag_mismatches=bad),indent=2)+'\n')
 print(batch,expected[0]['mnemonic'],'192 records; candidate flag mismatches',len(bad),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(8));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
