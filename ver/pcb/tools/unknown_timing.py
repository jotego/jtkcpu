#!/usr/bin/env python3
"""Measure newly observed encodings alongside physical known-opcode controls."""
import argparse,subprocess,sys
from pathlib import Path
from pcb_paths import ROOT
TOOLS=Path(__file__).resolve().parent
sys.path.insert(0,str(TOOLS))
import instruction_timing as t

def cases():
 rows=[]
 for post,mode in [('072f80','extended'),('c480','direct'),('26','X')]:
  for op,name in [(8,'LEAX control'),(5,'05 LEAX-like'),(6,'06 LEAX-like'),(7,'07 LEAX-like'),(0xd1,'D1 clear keep CC')]:
   rows.append(dict(id=len(rows)+1,opcode=op,mnemonic=name,mode=mode,encoding=f'{op:02x}'+post,
    setup_extra='        LDX #$2F00\n        FCB $3E,$42\n        LDX #$2F00\n        ANDCC #0\n        ORCC #$50\n',
    coverage='Repeated exact encoding, counts 0/128/256/512; input CLK inferred from 12 MHz input and timestamp slope'))
 return rows

t.OUT=ROOT/'artifacts/unknown-timing';t.cases=cases;t.BATCH_SIZE=5

def build(batch):
 t.generate(batch);folder=t.OUT/f'batch-{batch:02d}'
 with (folder/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','timing.asm','-L'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','timing.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
 t.package(folder)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int);a=p.parse_args();folder=t.OUT/f'batch-{a.batch:02d}'
 if a.action=='build':build(a.batch)
 elif a.action=='analyze':t.analyze(folder)
 else:subprocess.run([sys.executable,str(TOOLS/'load_probe.py'),str(folder/'timing-128k.bin'),'--seconds','20','--poll-interval','.005'],check=True)
