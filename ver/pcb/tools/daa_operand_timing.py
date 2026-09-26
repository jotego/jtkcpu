#!/usr/bin/env python3
"""Controlled DAA timing spanning decimal-correction and H/C input classes."""
import argparse
import instruction_timing as timing
from daa_tstd_probe import model

def cases():
    rows=[]
    for a in (0,0x0a,0xa0,0xff):
        for bits in (0,1,0x20,0x21):
            cc=0x50|bits;d=a<<8|0xa5
            setup=bytes([0x40])+d.to_bytes(2,'big')+bytes([0x3c,0x50,0x3d,cc]);first=len(rows)+1
            common=dict(opcode=0xb1,mnemonic='DAA',mode='CONTROLLED',encoding='b1',value=a,input_D=d,cc=cc,
                operand=f'A={a:02X},H={int(bool(cc&32))},C={cc&1}',width=8,reg='A',
                unit_setup_encoding=setup.hex(),unit_setup_asm=f'        LDD #${d:04X}\n        ANDCC #$50\n        ORCC #${cc:02X}\n',
                instruction_asm='DAA',coverage='A=00/0A/A0/FF, all four H/C inputs; D and CC reloaded per instruction; measured setup reference subtracted')
            rows.append(dict(**common,id=first,measurement_role='baseline',unit_encoding=setup.hex()))
            result,_=model(common)
            rows.append(dict(**common,id=first+1,measurement_role='paired',baseline_case_id=first,unit_encoding=(setup+b'\xb1').hex(),capture_asm='        STD $3F00\n',postflight=f'        LDD $3F00\n        CMPD #${result:04X}\n        LBNE RAM_FAIL\n'))
    return rows

def configure():
    timing.OUT=timing.ROOT/'artifacts/instruction-timing/daa-operands';timing.BATCH_SIZE=2;timing.COUNTS=[0,64,128,256];timing.BLOCK_DELAY=0x3fff;timing.cases=cases
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['generate','package','analyze']);p.add_argument('batch',type=int,choices=range(16));a=p.parse_args();configure()
    if a.action=='generate':timing.generate(a.batch)
    else:getattr(timing,a.action)(timing.OUT/f'batch-{a.batch:02d}')
