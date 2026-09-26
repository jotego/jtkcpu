#!/usr/bin/env python3
"""Stack masks, byte layout, registers and CC with alternate-stack capture."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,re,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/stack-flags'
MASKS=(0,1,2,4,8,16,32,64,128,0x55,0xaa,0xff)
CC=(0,1,4,5,8,9,0x72,255)
def cases(batch):
 op=0x0c+batch//9;stack='S' if op in (12,14) else 'U';pull=op>=14
 pairs=[(mask,cc) for mask in MASKS for cc in CC]+[(mask,cc) for mask in (0,1,255) for cc in range(256)]
 rows=[dict(opcode=op,mnemonic=('PULL' if pull else 'PUSH')+stack,stack=stack,pull=pull,mask=mask,cc=cc) for mask,cc in pairs]
 return rows[(batch%9)*96:(batch%9+1)*96]
def configure(batch):
 assert 0<=batch<36
 framed.ROOT=BASE/f'batch-{batch:02d}'
 return framed.ROOT,cases(batch),0xbe00+batch

def fields(mask,pull):
 values=[(1,'cc'),(1,0x96 if pull else 0x5a),(1,0x3c if pull else 0xa5),(1,0x69 if pull else 0x37),(2,0x2a51 if pull else 0x2193),(2,0x34b2 if pull else 0x32c4),(2,0x3d00 if pull else 0x3ff0),(2,'pc')]
 return [(width,value) for bit,(width,value) in enumerate(values) if mask&(1<<bit)]
def size(mask):return sum(width for width,_ in fields(mask,False))

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 op=rows[0]['opcode'];stack=rows[0]['stack'];pull=rows[0]['pull'];capture='U' if stack=='S' else 'S'
 source=(TEMPLATES / 'single_record.asm').read_text()
 source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK').replace('LDD #$A500',f'LDD #${run_id:04X}')
 first=source.index('        LDS #$3FF0',source.index('        STA $2E08'));last=source.index('; CRC-16/CCITT-FALSE',first)
 body='''        LDS #$3FF0
        LDD $2E42
        SUBD #$00F0
        LDA #5
        MUL
        LDY #OPERANDS
        LEAY D,Y
        LDD ,Y
        STD $2E09
        LDA 4,Y
        STA $2E0B
        LDB $2E0A
'''
 for mask in MASKS:body+=f'        CMPB #${mask:02X}\n        LBEQ MASK_{mask:02X}\n'
 body+='        JMP RAM_FAIL\n'
 for mask in MASKS:
  n=size(mask);start=0x3e00 if pull else 0x3e00-n;before=start-1;after=start+n
  body+=f'MASK_{mask:02X}:\n        LDS #$3FF0\n        LDA #$37\n        PSHS A\n        PULS DP\n'
  body+=f'        LDA #$A5\n        STA ${before:04X}\n        LDA #$5A\n        STA ${after:04X}\n'
  pos=start
  if pull:
   for width,value in fields(mask,pull):
    if value=='cc':body+=f'        LDA $2E0B\n        EORA #$FF\n        STA ${pos:04X}\n'
    elif value=='pc':body+=f'        LDD #DEST_{mask:02X}\n        STD ${pos:04X}\n'
    else:body+=f'        LD{"A" if width==1 else "D"} #${value:0{width*2}X}\n        ST{"A" if width==1 else "D"} ${pos:04X}\n'
    pos+=width
  else:
   body+='        LDA #$CC\n'
   for pos in range(start,start+n):body+=f'        STA ${pos:04X}\n'
  body+=f'''        LD{stack} #$3E00
        LD{capture} #$3FF0
        LDA $2E0B
        PSH{capture} A
        LDD #$5AA5
        LDX #$2193
        LDY #$32C4
        PUL{capture} CC
TARGET_{mask:02X}:
        FCB ${op:02X},${mask:02X}
'''
  if pull and mask&128:body+='        JMP RAM_FAIL\n'
  body+=f'''DEST_{mask:02X}:
        PSH{capture} CC
        STD $2E0C
        STX $2E0E
        STY $2E10
        PUL{capture} A
        STA $2E16
        STU $2E12
        STS $2E14
        PSH{capture} DP
        PUL{capture} A
        STA $2E17
        LDS #$3FF0
        LDU #$3FE0
        LDA ${before:04X}
        CMPA #$A5
        LBNE RAM_FAIL
        LDA ${after:04X}
        CMPA #$5A
        LBNE RAM_FAIL
'''
  pos=start
  for width,value in fields(mask,pull):
   if value=='cc':
    body+='        LDA $2E0B\n'
    if pull:body+='        EORA #$FF\n'
    body+=f'        CMPA ${pos:04X}\n'
   elif value=='pc':body+=f'        LDD ${pos:04X}\n        CMPD #DEST_{mask:02X}\n'
   else:body+=f'        LD{"A" if width==1 else "D"} ${pos:04X}\n        CMP{"A" if width==1 else "D"} #${value:0{width*2}X}\n'
   body+='        LBNE RAM_FAIL\n';pos+=width
  body+='        JMP CASE_DONE\n'
 body+='CASE_DONE:\n        LDA #$EF\n        STA $2E18\n'
 source=source[:first]+body+source[last:]
 first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
 # Leave room for the guarded mask leaves; table remains outside comms.
 source=source[:first]+'        ORG $B000\nOPERANDS:\n'+''.join(f"        FDB ${op:02X}{r['mask']:02X},$0000\n        FCB ${r['cc']:02X}\n" for r in rows)+source[last:]
 (root/'probe.asm').write_text(source)
 manifest=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with (root/'assembly.log').open('w') as f:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 framed.package();fixed=(root/'fixed.bin').read_bytes()
 expected=b''.join(bytes([op,r['mask'],0,0,r['cc']]) for r in rows)
 assert fixed[0x3000:0x3000+len(expected)]==expected
 labels={name:int(addr,16) for addr,name in re.findall(r'^\s*\d+/([0-9A-F]{4}) :\s+((?:TARGET|DEST)_[0-9A-F]{2}):',(root/'probe.lst').read_text(),re.M)}
 assert len(labels)==24
 for mask in MASKS:
  pos=labels[f'TARGET_{mask:02X}']-0x8000;dest=labels[f'DEST_{mask:02X}'];n=size(mask)
  assert fixed[pos-2:pos+2]==bytes([15 if capture=='U' else 14,1,op,mask])
  assert fixed[dest-0x8000:dest-0x8000+2]==bytes([13 if capture=='U' else 12,1])
  assert dest==pos+0x8000+2+(4 if pull and mask&128 else 0)
  if pull and mask&128:
   assert bytes([0x40])+dest.to_bytes(2,'big')+bytes([0x58,7])+(0x3e00+n-2).to_bytes(2,'big') in fixed
 assert bytes.fromhex('0a54ff500000') in fixed
 manifest=json.loads((root/'manifest.json').read_text());manifest['labels']=labels
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def predicted(r):
 stack=r['stack'];other='U' if stack=='S' else 'S';mask=r['mask'];pull=r['pull']
 out=dict(A=0x5a,B=0xa5,X=0x2193,Y=0x32c4,DP=0x37,CC=r['cc'])
 out[stack]=0x3e00+(size(mask) if pull else -size(mask));out[other]=0x3ff0
 if pull:
  for bit,reg,value in [(0,'CC',r['cc']^255),(1,'A',0x96),(2,'B',0x3c),(3,'DP',0x69),(4,'X',0x2a51),(5,'Y',0x34b2),(6,other,0x3d00)]:
   if mask&(1<<bit):out[reg]=value
 return out

def analyze(batch):
 root,expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text())
 assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
 assert capture['manifest']['cases']==expected
 for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
  assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==capture['manifest'][key]
 records=[];bad=[]
 for i,(frame,r) in enumerate(zip(capture['frames'],expected)):
  packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id);b=packet[9:25]
  assert b[:3]==bytes([r['opcode'],r['mask'],r['cc']]) and b[15]==0xef
  regs=dict(A=b[3],B=b[4],X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'),CC=b[13],DP=b[14])
  if regs!=predicted(r):bad.append(i)
  records.append(dict(**r,output_registers=regs,output_CC=b[13]))
 (root/'results.json').write_text(json.dumps(dict(records=records,candidate_mismatches=bad),indent=2)+'\n')
 print(batch,expected[0]['mnemonic'],'96 guarded stack records; model mismatches',len(bad),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(36));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
