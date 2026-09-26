#!/usr/bin/env python3
"""Physical transfer-selector and hidden-DP probes with a safe RAM PC trampoline."""
import sys,json,hashlib,subprocess,argparse,re
from pathlib import Path
from pcb_paths import ROOT
import framed_probe as framed
from screen_collect import collect
CASES={'control':b'\xae'}
for opcode in (0x3e,0x3f):
 for post in (0x22,0x24,0x26,0x27,0x62,0x72):CASES[f'{opcode:02x}-{post:02x}']=bytes([opcode,post])
CASES.update({'dp-pull':b'\x0e\x08','dp-rti':b'\x9f'})
CASES.update({'control-recovery':b'\xae','ram-jump':bytes.fromhex('a8072f80'),'3e-27-rom':bytes.fromhex('3e27'),'3f-27-rom':bytes.fromhex('3f27'),'control-final':b'\xae'})

def configure(case):
 root=ROOT/'artifacts/registers'/case;framed.ROOT=root
 return root,0x3100+list(CASES).index(case)

def build(case):
 root,run=configure(case);assert not (root/'capture.json').exists();framed.COUNT=1;framed.generate()
 s=(root/'probe.asm').read_text().replace('LDD #$7B01',f'LDD #${run:04X}').replace('CMPD #$0150','CMPD #$00F1')
 first=s.index('        LDX #$2E09');last=s.index('; CRC-16/CCITT-FALSE',first)
 prep=''
 if case=='dp-pull':prep='''        PSHS DP
        LDX #$9C18
        FCB $3E,$42
        LDX #$2F80
'''
 elif case=='dp-rti':prep='''        LDD #$D012
        STD $3FE4
        LDD #$342F
        STD $3FE6
        LDD #$2F80
        STD $3FE8
        LDD #$2FA0
        STD $3FEA
        LDD #$3FE0
        STD $3FEC
        LDD #CAPTURE
        STD $3FEE
        LDX #$9C18
        FCB $3E,$42
        LDS #$3FE4
        LDD #$1234
        LDX #$2F80
'''
 raw=','.join(f'${b:02X}' for b in CASES[case])
 body=f'''        LDD #$A807
        STD $2F80
        LDY #CAPTURE
        STY $2F82
        LDS #$3FF0
        LDX #$2FA5
        FCB $3E,$42
        LDD #$1234
        LDX #$2F80
        LDY #$2FA0
        LDU #$3FE0
{prep}        ANDCC #0
        ORCC #$5F
TARGET:
        FCB {raw}
CAPTURE:
        PSHS CC
        STD $2E0C
        STX $2E0E
        STY $2E10
        PULS A
        STA $2E16
        STU $2E12
        STS $2E14
        LDS #$3FF0
        LDX #0
        FCB $3E,$42
        STX $2E17
        LDA #${CASES[case][0]:02X}
        STA $2E09
        LDA #${CASES[case][-1]:02X}
        STA $2E0A
        LDA #$F9
        STA $2E0B
'''
 if case.endswith('-rom'):
  body=body.replace('LDX #$2F80','LDX #CAPTURE').replace('PSHS CC','PSHU CC').replace('PULS A','PULU A')
 s=s[:first]+body+s[last:];(root/'probe.asm').write_text(s)
 m=dict(first=240,count=1,frame_size=27,run_id=run,case=case,encoding=CASES[case].hex(),seed=dict(D=0x1234,X=0x2f80,Y=0x2fa0,U=0x3fe0,S=0x3ff0,CC=0x5f,DPword=0x2fa5),source_sha256=hashlib.sha256(s.encode()).hexdigest(),safe_pc_target=0x2f80)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 if case.endswith('-rom'):
  listing=(root/'probe.lst').read_text()
  m['seed']['X']=int(re.search(r'\d+/([0-9A-F]+) :\s+CAPTURE:',listing)[1],16)
  (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 framed.package()

def analyze(case):
 root,run=configure(case);c=json.loads((root/'capture.json').read_text());assert c['validated'] and c['complete'] and len(c['frames'])==1
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['manifest'][key]
 frame=bytes.fromhex(c['frames'][0]['hex']);framed.check_frame(frame,240,False,run);b=frame[9:25];assert b[:3]==bytes([CASES[case][0],CASES[case][-1],0xf9])
 r=dict(D=int.from_bytes(b[3:5],'big'),X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'),CC=b[13],DPword=int.from_bytes(b[14:16],'big'))
 (root/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(case,r,flush=True)
 if case.startswith('control'):assert r==c['manifest']['seed']
 return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('case',choices=CASES);a=p.parse_args()
 if a.action=='build':build(a.case)
 elif a.action=='collect':root,run=configure(a.case);collect(root,run)
 else:analyze(a.case)
