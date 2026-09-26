#!/usr/bin/env python3
"""Identify vector entry and retain registers plus the complete stack page."""
import argparse,hashlib,json,subprocess
import memory_probe as memory
from pathlib import Path
ROOT=memory.ROOT
VARIANT='extended'

def configure(op):
 root=ROOT/'artifacts/vector-screen'/VARIANT/f'{op:02x}'
 memory.base.framed.ROOT=root
 return root,0x9000+list(memory.base.SUFFIXES).index(VARIANT)*256+op

def build(op):
 memory.VARIANT=VARIANT;memory.configure=configure
 root,run=configure(op);memory.build(op)
 s=(root/'probe.asm').read_text()
 s=s.replace('        LDS #$3FF0\n        LDX #$2F00\n        FCB $3E,$42','        CLR $2E45\n        LDS #$3FF0\n        LDX #$2F00\n        FCB $3E,$42')
 assert s.count('        CLR $2E45')==1
 s=s.replace('        PSHS CC\n        STD $2E0C','CAPTURE_ENTRY:\n        PSHS CC\n        STD $2E0C')
 s=s.replace('        LDA #$F9\n        STA $2E0B','        LDA $2E45\n        STA $2E0B')
 s=s.replace('        LDX #$2F00\n        ABX\n        LDY #$2E09','        LDX #$3F00\n        ABX\n        LDY #$2E09')
 handlers=''
 for vector in (0xf6,0xf8,0xfa,0xfc):
  handlers+=f'''VECTOR_{vector:02X}:
        PSHS CC,A
        LDA #${vector:02X}
        STA $2E45
        PULS CC,A
        JMP CAPTURE_ENTRY
'''
 s=s.replace('        ORG $FFF6',handlers+'        ORG $FFF6')
 s=s.replace('FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET','FDB VECTOR_F6,VECTOR_F8,VECTOR_FA,VECTOR_FC,RESET')
 (root/'probe.asm').write_text(s)
 m=json.loads((root/'manifest.json').read_text());m.update(memory_start=0x3f00,source_sha256=hashlib.sha256(s.encode()).hexdigest(),vector_ids=[0xf6,0xf8,0xfa,0xfc],handler_stack_scratch_bytes=2)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 memory.base.framed.package()

def analyze(op):
 root,run=configure(op);c=json.loads((root/'capture.json').read_text())
 assert c['validated'] and c['complete'] and len(c['frames'])==17
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['manifest'][key]
 payload=[]
 for i,f in enumerate(c['frames']):
  b=bytes.fromhex(f['hex']);memory.base.framed.check_frame(b,240+i,False,run);payload.append(b[9:25])
 b=payload[0];assert b[:2]==bytes([op,c['manifest']['seed']['CC']]) and b[15]==0xfc and b[2] in (0,0xf6,0xf8,0xfa,0xfc)
 r=dict(D=int.from_bytes(b[3:5],'big'),X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'),CC=b[13],DP=b[14])
 page=b''.join(payload[1:]);start=r['S']-0x3f00;end=c['manifest']['seed']['S']-0x3f00
 assert 0<=start<=end<=256
 frame=page[start:end]
 result=dict(opcode=op,vector=b[2],registers=r,stack_frame_hex=frame.hex(),stack_page_hex=page.hex(),stack_bytes=len(frame),scope='Stack page includes transient handler pushes below entry S; original frame is S..initial S-1')
 (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
 print(f'{VARIANT}/{op:02X}: vector {b[2]:02X}, {r}, frame {frame.hex()}',flush=True)
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('opcode',type=lambda x:int(x,16));p.add_argument('--variant',choices=['nop','extended','direct','regoff','extended-cc00','extended-ccff'],default='extended');a=p.parse_args();VARIANT=a.variant
 if a.action=='build':build(a.opcode)
 elif a.action=='analyze':analyze(a.opcode)
 else:
  from screen_collect import collect
  root,run=configure(a.opcode);collect(root,run)
