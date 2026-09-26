"""Zero-count block probes with reconstructed frame and mapper state."""
import register_probe as p
from deferred_collect import collect
import json,hashlib,subprocess
from pathlib import Path
from pcb_paths import ROOT
CC=0x5f
OUTPUT='block-zero-deferred2'

def build(op,count):
 case=f'block-{op:02x}-{count}'
 p.CASES[case]=bytes([op]);p.ROOT=ROOT/'artifacts'/OUTPUT
 root,run=p.configure(case);assert not (root/'capture.json').exists()
 p.build(case);s=(root/'probe.asm').read_text().replace('ORCC #$5F',f'ORCC #${CC:02X}')
 s=s.replace('        LDD #$1234','        LDD #$0000').replace('        LDU #$3FE0',f'        LDU #{count}')
 s=s.replace('        LDS #$3FF0\n        LDX #$2FA5','''        LDD #$A55A
        STD $2F80
        LDD #$3CC3
        STD $2FA0
        LDS #$3FF0
        LDX #$2FA5''')
 s=s.replace(f'        LDA #${op:02X}\n        STA $2E0A\n        LDA #$F9\n        STA $2E0B','''        LDD $2F80
        STD $2E0A''')
 assert 'LDA #$F9' not in s
 restore=f'''        ORCC #$50
        LDA #$11
        STA $7C00
        LDA #$FB
        STA $5D00
        CLRA
        STA $5D00
        STA $5FE2
        LDA #$10
        STA $5FE0
        SETLINES #0
        LDD #$A55A
        STD $2E00
        LDA #1
        STA $2E02
        LDD #${run:04X}
        STD $2E03
        LDD #$00F0
        STD $2E05
        STD $2E42
        LDD #$1000
        STD $2E07
        LDA #1
        STA $2E44
HOST_WAIT:
        LDX #$0FFF
HOST_DELAY:
        LEAX -1,X
        BNE HOST_DELAY
        TST $5FEA
        LDA $DC0C
        CMPA #1
        BNE HOST_WAIT
        LDA $DE00
        CMPA #$A5
        LBNE RAM_FAIL
        LDA $DFA0
'''
 s=s.replace('; CRC-16/CCITT-FALSE',restore+'; CRC-16/CCITT-FALSE')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 m=json.loads((root/'manifest.json').read_text());m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),block_count=count,guards_before='a55a',source_bytes='3cc3');m['seed'].update(D=0,U=count,CC=CC)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');p.framed.package();return root,run

def analyze(root,run):
 c=json.loads((root/'capture.json').read_text());assert c['validated'] and c['complete'] and len(c['frames'])==1
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['manifest'][key]
 f=bytes.fromhex(c['frames'][0]['hex']);p.framed.check_frame(f,240,False,run);b=f[9:25]
 r=dict(opcode=b[0],memory_2f80=b[1:3].hex(),D=int.from_bytes(b[3:5],'big'),X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'),CC=b[13],DPword=int.from_bytes(b[14:16],'big'))
 (root/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(root.name,r,flush=True);return r

if __name__=='__main__':
 for op in (0xcf,0xd0,0xb6):
  for count in (1,0):
   root,run=build(op,count);c=collect(root,run)
   if c['validated']:analyze(root,run)
