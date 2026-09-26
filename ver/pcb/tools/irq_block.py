"""Synchronize block execution to one vblank, inspect state at the next IRQ."""
import irq_probe as p
import json,hashlib,subprocess,re
from pathlib import Path
BASE=p.ROOT
TIMED=False

def build(op,delay):
 p.ROOT=BASE/('artifacts/irq-block-timed' if TIMED else 'artifacts/irq-block')/f'{op:02x}-{delay:04x}'
 root,run=p.build('enabled');assert not (root/'capture.json').exists()
 s=(root/'probe.asm').read_text().replace('        LDA #$40\n        STA $5FE2','        CLR $2E49\n        LDA #$40\n        STA $5FE2',1)
 s=s.replace('IRQ_WAIT:\n', 'IRQ_WAIT:\n')
 s=s.replace('        STA $2E0A\n','''        STA $2E0A
        INC $2E49
        LDA $2E49
        CMPA #1
        LBEQ FIRST_IRQ
''')
 helper=f'''FIRST_IRQ:
        CLR $5FE2
        LDD #START_BLOCK
        STD 10,S
        LDA #$40
        STA $5FE2
        RTI
START_BLOCK:
        LDX #${delay:04X}
BLOCK_DELAY:
        LEAX -1,X
        BNE BLOCK_DELAY
        LDX #$8000
        LDY #$8000
        LDU #${0x2800 if op==0xd0 else 0x5000:04X}
        LDD #0
BLOCK_OPCODE:
        FCB ${op:02X}
AFTER_BLOCK:
        BRA AFTER_BLOCK
'''
 s=s.replace('        ORG $FFF6',helper+'        ORG $FFF6')
 if TIMED:
  s=s.replace('FIRST_IRQ:\n        CLR $5FE2','FIRST_IRQ:\n        LDA $DFA2\n        CLR $5FE2')
  s=s.replace('        LBEQ FIRST_IRQ\n','        LBEQ FIRST_IRQ\n        LDA $DFA3\n')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 m=json.loads((root/'manifest.json').read_text());lst=(root/'probe.lst').read_text();label=lambda name:int(re.search(r'\d+/([0-9A-F]+) :\s+'+name+':',lst)[1],16)
 m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),block_opcode=op,delay_iterations=delay,opcode_address=label('BLOCK_OPCODE'),after_address=label('AFTER_BLOCK'),block_X=0x8000,block_Y=0x8000,block_U=0x2800 if op==0xd0 else 0x5000)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');p.f.package();return root,run

if __name__=='__main__':
 for op in (0xcf,0xd0,0xb6):
  for delay in (0x0800,0x1000,0x1800):
   root,run=build(op,delay);c=p.collect(root,run)
   if c['validated']:p.analyze(root,run)
