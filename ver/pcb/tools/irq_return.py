"""Compare RTI to the saved PC with explicit redirection after unknown sequences."""
import irq_probe as p
import json,hashlib,subprocess,re
from pathlib import Path
BASE=p.ROOT

def build(op,mode):
 p.ROOT=BASE/'artifacts/irq-return'/f'{op:02x}-{mode}'
 root,run=p.build('enabled');assert not (root/'capture.json').exists()
 s=(root/'probe.asm').read_text()
 s=s.replace('        LDA #$40\n        STA $5FE2\n','        CLR $2E49\n')
 s=s.replace('IRQ_WAIT:\n',f'''        LDA #$40
        STA $5FE2
RETURN_TEST:
        FCB ${op:02X}
        FCB $AE,$AE,$AE,$AE,$AE,$AE,$AE,$AE
        FCB $AE,$AE,$AE,$AE,$AE,$AE,$AE,$AE
AFTER_TEST:
        ORCC #$50
        CLR $5FE2
        LDA #$A1
        STA $2E09
        JMP REPORT
IRQ_WAIT:
''')
 s=s.replace('        STA $2E0A\n','        STA $2E0A\n        INC $2E49\n')
 redirect='''        LDD #AFTER_TEST
        STD 10,S
''' if mode=='redirect' else '''        LDA #$40
        STA $5FE2
'''
 s=s.replace('        LDS #$3FF0\nREPORT:', '''        LDA $2E49
        CMPA #1
        BNE SECOND_ENTRY
'''+redirect+'''        RTI
SECOND_ENTRY:
        LDS #$3FF0
REPORT:''')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 m=json.loads((root/'manifest.json').read_text());lst=(root/'probe.lst').read_text()
 label=lambda name:int(re.search(r'\d+/([0-9A-F]+) :\s+'+name+':',lst)[1],16)
 m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),exact_sequence=bytes([op]+[0xae]*16).hex(),opcode_address=label('RETURN_TEST'),continuation_address=label('AFTER_TEST'),return_mode=mode)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');p.f.package();return root,run

if __name__=='__main__':
 for op in (0x01,0xd2,0xff):
  for mode in ('unchanged','redirect'):
   root,run=build(op,mode);c=p.collect(root,run)
   if c['validated']:p.analyze(root,run)
