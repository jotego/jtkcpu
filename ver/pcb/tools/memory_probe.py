#!/usr/bin/env python3
"""Run one candidate, capture registers, then read back the 256-byte scratch page."""
import argparse, hashlib, json, subprocess
import operand_probe as base
from pathlib import Path

ROOT=base.ROOT
VARIANT='extended'

def configure(op):
 root=ROOT/'artifacts/memory-screen'/VARIANT/f'{op:02x}'
 base.framed.ROOT=root
 return root,0xe100+list(base.SUFFIXES).index(VARIANT)*256+op

def build(op):
 base.VARIANT=VARIANT
 base.configure=configure
 root,run=configure(op)
 base.build(op)
 s=(root/'probe.asm').read_text()
 fill=json.loads((root/'manifest.json').read_text()).get('scratch_fill',0x5a)
 needle=f'        LDX #$2F00\n        LDA #${fill:02X}\nFILL_SCRATCH:'
 assert s.count(needle)==1
 s=s.replace(needle,'        LDD $2E42\n        CMPD #$00F0\n        LBNE MEMORY_FRAME\n'+needle)
 marker='; CRC-16/CCITT-FALSE'
 memory='''        JMP ENCODE_FRAME
MEMORY_FRAME:
        LDB $2E43
        SUBB #$F1
        ASLB
        ASLB
        ASLB
        ASLB
        LDX #$2F00
        ABX
        LDY #$2E09
MEMORY_COPY:
        LDA ,X+
        STA ,Y+
        CMPY #$2E19
        BNE MEMORY_COPY
ENCODE_FRAME:
'''
 s=s.replace(marker,memory+marker).replace('CMPD #$00F1','CMPD #$0101')
 (root/'probe.asm').write_text(s)
 m=json.loads((root/'manifest.json').read_text())
 m.update(count=17,source_sha256=hashlib.sha256(s.encode()).hexdigest(),memory_start=0x2f00,memory_size=256)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 base.framed.package()

def analyze(op):
 root,run=configure(op);c=json.loads((root/'capture.json').read_text())
 assert c['validated'] and c['complete'] and len(c['frames'])==17
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['manifest'][key]
 payload=[]
 for i,f in enumerate(c['frames']):
  b=bytes.fromhex(f['hex']);base.framed.check_frame(b,240+i,False,run);payload.append(b[9:25])
 b=payload[0];assert b[:3]==bytes([op,c['manifest']['seed']['CC'],0xf9]) and b[15]==0xfc
 r=dict(D=int.from_bytes(b[3:5],'big'),X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'),CC=b[13],DP=b[14])
 memory=b''.join(payload[1:]);assert len(memory)==256
 initial=bytearray([c['manifest'].get('scratch_fill',0x5a)]*256);initial[0:2]=bytes.fromhex('2f80');initial[16:18]=bytes.fromhex('2f90')
 differences=[dict(address=0x2f00+i,before=a,after=b) for i,(a,b) in enumerate(zip(initial,memory)) if a!=b]
 result=dict(opcode=op,registers=r,memory_hex=memory.hex(),differences=differences,scope='Complete 2F00..2FFF post-execution readback; other memory not captured')
 (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(f'{VARIANT}/{op:02X}: {r}; RAM changes: {differences}',flush=True)
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('opcode',type=lambda x:int(x,16));p.add_argument('--variant',choices=base.SUFFIXES,default='extended');a=p.parse_args();VARIANT=a.variant
 if a.action=='build':build(a.opcode)
 elif a.action=='analyze':analyze(a.opcode)
 else:
  from screen_collect import collect
  root,run=configure(a.opcode);collect(root,run)
