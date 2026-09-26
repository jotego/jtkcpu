#!/usr/bin/env python3
"""Pair interrupt-entry blocks with known PSHS+JMP and equal-cost return handlers."""
import argparse,json,re,subprocess,sys
from pathlib import Path
from pcb_paths import ROOT
TOOLS=Path(__file__).resolve().parent
sys.path.insert(0,str(TOOLS))
import instruction_timing as t

def cases():
 rows=[]
 for op in (2,3,4,0x5d):
  short=op==3
  for baseline in (True,False):
   rows.append(dict(id=len(rows)+1,opcode=0x0c if baseline else op,mnemonic='PSHS+JMP baseline' if baseline else f'Entry {op:02X}',mode='entry',encoding=('0c81a8070000' if short else '0cffa8070000') if baseline else f'{op:02x}',
    role='baseline' if baseline else 'target',target_opcode=op,baseline_cost=48 if short else 78,
    setup_extra='        ORCC #$50\n' if short else '        ORCC #$D0\n',
    capture_asm='        STD $3F00\n',saved_d=0x1234,
    post_registers=dict(S=(0x3ff0,0),X=(0x2f00,0),Y=(0x2f10,0),U=(0x2f20,0)),
    coverage='Matched handler instruction paths; PSHS+JMP baseline cost from measured issue1 formulas; adjusted saved PC then RTI'))
 return rows

t.OUT=ROOT/'artifacts/entry-timing';t.BATCH_SIZE=2;t.cases=cases

def build(batch):
 t.generate(batch);folder=t.OUT/f'batch-{batch:02d}'
 s=(folder/'timing.asm').read_text()
 s=s.replace('        FCB $0C,$FF,$A8,$07,$00,$00','        FCB $0C,$FF,$A8,$07\n        FDB FULL_BASE')
 s=s.replace('        FCB $0C,$81,$A8,$07,$00,$00','        FCB $0C,$81,$A8,$07\n        FDB SHORT_BASE')
 handlers=''
 for label,offset,advance in [('FULL_BASE',12,4),('SHORT_BASE',3,4),('FULL_RETRY',12,1),('SHORT_RETRY',3,1),('FULL_NEXT',12,0)]:
  handlers+=f'''{label}:
        PSHS D
        LDD {offset},S
        ADDD #{advance}
        STD {offset},S
        PULS D
        RTI
'''
 s=s.replace('        ORG $FFF6',handlers+'        ORG $FFF6').replace('FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET','FDB SHORT_RETRY,FULL_RETRY,FULL_NEXT,FULL_RETRY,RESET')
 (folder/'timing.asm').write_text(s)
 with (folder/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','timing.asm','-L'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','timing.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
 import hashlib
 m=json.loads((folder/'manifest.json').read_text());m['source_sha256']=hashlib.sha256(s.encode()).hexdigest()
 lst=(folder/'timing.lst').read_text()
 for row in m['cases']:
  if row['role']=='baseline':
   label='SHORT_BASE' if row['target_opcode']==3 else 'FULL_BASE'
   address=int(re.search(r'\d+/([0-9A-F]+) :\s+'+label+':',lst)[1],16)
   row['encoding']=row['encoding'][:-4]+f'{address:04x}'
 (folder/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');t.package(folder)

def analyze(batch):
 folder=t.OUT/f'batch-{batch:02d}';t.analyze(folder)
 data=json.loads((folder/'results.json').read_text());base,target=data['results'];assert base['role']=='baseline' and target['role']=='target'
 fitted=target['fitted_input_clocks']-base['fitted_input_clocks']+base['baseline_cost']
 clocks=round(fitted);assert clocks>0 and abs(fitted-clocks)<.15
 result=dict(opcode=target['target_opcode'],input_clocks=clocks,fitted_input_clocks=fitted,baseline_instruction_clocks=base['baseline_cost'],baseline_block_clocks=base['input_clocks'],target_block_clocks=target['input_clocks'],scope='Entry clock count excludes matched handler/RTI cost; inferred from 12 MHz input')
 (folder/'entry-results.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int);a=p.parse_args();folder=t.OUT/f'batch-{a.batch:02d}'
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':analyze(a.batch)
 else:subprocess.run([sys.executable,str(TOOLS/'load_probe.py'),str(folder/'timing-128k.bin'),'--seconds','20','--poll-interval','.005'],check=True)
