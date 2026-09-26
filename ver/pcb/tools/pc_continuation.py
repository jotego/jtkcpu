"""Distinguish old-stream opcode/operand execution after a PC exchange."""
import sys,json,hashlib,subprocess
from pathlib import Path
import pc_transfer as p
from pcb_paths import ROOT

def build(op,post,variant):
 case=f'{op:02x}-{post:02x}-ram'
 p.base.ROOT=ROOT/'artifacts/continuation'/variant
 p.build(case)
 root,run=p.configure(case)
 assert not (root/'capture.json').exists()
 s=(root/'probe.asm').read_text()
 pad='        FCB '+','.join(['$AE']*16)+'\n'
 old={'nop':'        FCB $AE\n','clra':'        CLRA\n','lda':'        LDA #$99\n'}[variant]
 # Only the first old-stream instruction is changed; both landing pads remain.
 target=f'        FCB ${op:02X},${post:02X}\n'
 assert s.count(target)==1
 s=s.replace(target+pad,target+old+pad)
 s=s.replace('RAM_TARGET:\n        LDA #$22','RAM_TARGET:\n        LDB #$66')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 m=json.loads((root/'manifest.json').read_text());m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),continuation_variant=variant,destination_B=0x66)
 # Changed layout invalidates previous label metadata; RAM entry remains fixed.
 m.pop('opcode_address',None);m.pop('fallthrough_marker',None);m.pop('destination_marker',None)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');p.base.framed.package()
 return case,root,run

if __name__=='__main__':
 for op in (0x3e,0x3f):
  for post in (0x27,0x72):
   for variant in ('nop','clra','lda'):
    case,root,run=build(op,post,variant)
    r=p.base.collect(root,run)
    assert r['validated'],r['status']
    p.analyze(case)
