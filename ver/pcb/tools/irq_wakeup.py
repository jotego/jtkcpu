"""Observe IRQ entry after exact unknown byte sequences, preserving failures."""
import irq_probe as p
import json,hashlib,subprocess,re
from pathlib import Path
BASE=p.ROOT
def build(op):
 p.ROOT=BASE/'artifacts/wakeup'/f'{op:02x}'
 root,run=p.build('enabled');assert not (root/'capture.json').exists()
 s=(root/'probe.asm').read_text()
 # Enable the source only immediately before the test sequence.
 s=s.replace('        LDA #$40\n        STA $5FE2\n','')
 s=s.replace('IRQ_WAIT:\n',f'''        LDA #$40
        STA $5FE2
WAKE_OPCODE:
        FCB ${op:02X}
        FCB $AE,$AE,$AE,$AE,$AE,$AE,$AE,$AE
        FCB $AE,$AE,$AE,$AE,$AE,$AE,$AE,$AE
IRQ_WAIT:
''')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 m=json.loads((root/'manifest.json').read_text());lst=(root/'probe.lst').read_text()
 m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),exact_sequence=bytes([op]+[0xae]*16).hex(),opcode_address=int(re.search(r'\d+/([0-9A-F]+) :\s+WAKE_OPCODE:',lst)[1],16))
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');p.f.package()
 return root,run

if __name__=='__main__':
 for op in (0x01,0xd2,0xff):
  root,run=build(op);c=p.collect(root,run)
  if c['validated']:p.analyze(root,run)
