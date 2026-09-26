#!/usr/bin/env python3
"""EXG/TFR register-pair results and flags using a safe capture stack."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/transfer-flags'
REGS=['A','B','X','Y','S','U']
SEEDS=dict(A=0x3c,B=0x96,X=0x2193,Y=0x32c4,S=0x3ff0,U=0x3fe0)
CC=(0,1,4,5,8,9,0x72,255)
def cases(batch):
 op=0x3e+batch//3
 rows=[dict(opcode=op,mnemonic='EXG' if op==0x3e else 'TFR',src=src,dst=dst,postbyte=dst<<4|src,cc=cc) for src in range(6) for dst in range(6) for cc in CC]
 return rows[(batch%3)*96:(batch%3+1)*96]
def configure(batch):
 assert 0<=batch<6
 framed.ROOT=BASE/f'batch-{batch:02d}'
 return framed.ROOT,cases(batch),0xbd00+batch

def build(batch):
 root,rows,run_id=configure(batch);root.mkdir(parents=True,exist_ok=True)
 op=rows[0]['opcode'];name=rows[0]['mnemonic']
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
 for src in range(6):
  for dst in range(6):
   post=dst<<4|src
   body+=f'        CMPB #${post:02X}\n        LBEQ PAIR_{post:02X}\n'
 body+='        JMP RAM_FAIL\n'
 stacks={}
 for src in range(6):
  for dst in range(6):
   post=dst<<4|src
   stack='S' # Physical selectors0..5 leave S unchanged; U can receive arbitrary words.
   stacks[str(post)]=stack
   body+=f'''PAIR_{post:02X}:
        LDS #$3FF0
        LDU #$3FE0
        LDX #$A67B
        FCB $3E,$42 ; initialize physical selector4 word, then replace X seed
        LDA $2E0B
        PSH{stack} A
        LDD #$3C96
        LDX #$2193
        LDY #$32C4
        PUL{stack} CC
        {name} {REGS[src]},{REGS[dst]}
        PSH{stack} CC
        STD $2E0C
        STX $2E0E
        STY $2E10
        PUL{stack} A
        STA $2E16
        STU $2E12
        STS $2E14
        PSH{stack} DP
        PUL{stack} A
        STA $2E17
        LDS #$3FF0
        LDU #$3FE0
        JMP CAPTURE_DONE
'''
 body+='CAPTURE_DONE:\n        LDA #$EF\n        STA $2E18\n'
 source=source[:first]+body+source[last:]
 first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
 source=source[:first]+'        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['opcode']:02X}{r['postbyte']:02X},$0000\n        FCB ${r['cc']:02X}\n" for r in rows)+source[last:]
 (root/'probe.asm').write_text(source)
 manifest=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,seeds=SEEDS,initial_selector4=0xa67b,capture_stacks=stacks,source_sha256=hashlib.sha256(source.encode()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with (root/'assembly.log').open('w') as f:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
 framed.package();fixed=(root/'fixed.bin').read_bytes()
 expected=b''.join(bytes([r['opcode'],r['postbyte'],0,0,r['cc']]) for r in rows)
 assert fixed[0x1000:0x1000+len(expected)]==expected
 for post,stack in stacks.items():
  assert fixed.count(bytes([15 if stack=='U' else 14,1,op,int(post),13 if stack=='U' else 12,1]))==1
 assert fixed.count(bytes.fromhex('42a67b3e42'))==36
 for stack in ('S','U'):
  pattern=bytes([13 if stack=='U' else 12,8,15 if stack=='U' else 14,2])
  assert fixed.count(pattern)==list(stacks.values()).count(stack)
 assert bytes.fromhex('0a54ff500000') in fixed

def predicted(r):
 # Measured candidate: both primary bytes exchange; selector4 is a word
 # whose high byte is exposed by the DP stack bit. S is not selector4.
 out=SEEDS.copy();dp=0xa6
 values=[SEEDS['B']<<8|SEEDS['A'],SEEDS['A']<<8|SEEDS['B'],SEEDS['X'],SEEDS['Y'],0xa67b,SEEDS['U']]
 for index,value in [(r['src'],values[r['dst']]),(r['dst'],values[r['src']])]:
  if index==4:dp=value>>8
  else:out[REGS[index]]=value&(255 if index<2 else 65535)
 return out,dp


def analyze(batch):
 root,expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text())
 assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
 assert capture['manifest']['cases']==expected and capture['manifest']['seeds']==SEEDS
 for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
  assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==capture['manifest'][key]
 records=[];bad=[];data_bad=[]
 for i,(frame,r) in enumerate(zip(capture['frames'],expected)):
  packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id);b=packet[9:25]
  assert b[:3]==bytes([r['opcode'],r['postbyte'],r['cc']]) and b[15]==0xef
  registers=dict(A=b[3],B=b[4],X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'))
  if (registers,b[14])!=predicted(r):data_bad.append(i)
  if r['cc']!=b[13]:bad.append(i)
  # Preserve unexpected observations rather than rejecting model differences.
  records.append(dict(**r,output_registers=registers,output_CC=b[13],output_DP=b[14]))
 (root/'results.json').write_text(json.dumps(dict(records=records,candidate_data_mismatches=data_bad,changed_CC_indices=bad),indent=2)+'\n')
 print(batch,expected[0]['mnemonic'],'96 records; data/flag model mismatches',len(data_bad),len(bad),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(6));a=p.parse_args()
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:
  root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
  a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
