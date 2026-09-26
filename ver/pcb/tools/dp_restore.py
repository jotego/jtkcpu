"""Vary hidden DP bytes through stack pull and full-frame RTI."""
import register_probe as p
import json,hashlib,subprocess
from pathlib import Path
from pcb_paths import ROOT as BASE

def build(case,original,live):
 p.ROOT=BASE/'artifacts/dp-restore'/f'{original:04x}-{live:04x}'
 root,run=p.configure(case);assert not (root/'capture.json').exists();p.build(case)
 s=(root/'probe.asm').read_text().replace('LDX #$2FA5',f'LDX #${original:04X}').replace('LDX #$9C18',f'LDX #${live:04X}')
 if case=='dp-rti':s=s.replace('LDD #$342F',f'LDD #${0x3400|(original>>8):04X}')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 m=json.loads((root/'manifest.json').read_text());m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),original_DPword=original,live_DPword=live,expected_DPword=(original&0xff00)|(live&255));m['seed']['DPword']=original
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');p.framed.package();return root,run

if __name__=='__main__':
 for original,live in [(0x1200,0xabff),(0x34ff,0xcd00),(0xa555,0x5aaa),(0x5aaa,0xa555)]:
  for case in ('dp-pull','dp-rti'):
   root,run=build(case,original,live);c=p.collect(root,run);assert c['validated'];r=p.analyze(case);assert r['DPword']==((original&0xff00)|(live&255))
