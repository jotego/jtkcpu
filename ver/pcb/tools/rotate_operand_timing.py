#!/usr/bin/env python3
"""Controlled byte-rotate timing with both carry-in states."""
import argparse
import instruction_timing as timing
from packed_unary import expected_d

OPS=[(0x96,'RORA','A'),(0x97,'RORB','B'),(0xa0,'ROLA','A'),(0xa1,'ROLB','B')]


def cases():
    rows=[]
    for opcode,name,reg in OPS:
        for value in (0,255):
            for carry in (0,1):
                cc=0x50|carry
                d=value<<8|0xa5 if reg=='A' else 0x5a00|value
                setup=bytes([0x40])+d.to_bytes(2,'big')+bytes([0x3c,0x50,0x3d,cc])
                first=len(rows)+1
                descriptor=dict(opcode=opcode,mnemonic=name,reg=reg,width=8,value=value,input_D=d,cc=cc)
                common=dict(**descriptor,mode='CONTROLLED',encoding=f'{opcode:02x}',carry_in=carry,
                    operand=f'{reg}={value:02X},C={carry}',unit_setup_encoding=setup.hex(),
                    unit_setup_asm=f'        LDD #${d:04X}\n        ANDCC #$50\n        ORCC #${cc:02X}\n',
                    instruction_asm=name,coverage='Recorded byte operand and CC50/51 reloaded before every rotate; measured setup-only slope subtracted')
                rows.append(dict(**common,id=first,measurement_role='baseline',unit_encoding=setup.hex()))
                result=expected_d(descriptor)
                guard=f'        LDD $3F00\n        CMPD #${result:04X}\n        LBNE RAM_FAIL\n'
                rows.append(dict(**common,id=first+1,measurement_role='paired',baseline_case_id=first,
                    unit_encoding=(setup+bytes([opcode])).hex(),capture_asm='        STD $3F00\n',postflight=guard))
    return rows


def configure():
    timing.OUT=timing.ROOT/'artifacts/instruction-timing/rotate-operands'
    timing.BATCH_SIZE=2
    timing.COUNTS=[0,64,128,256]
    timing.BLOCK_DELAY=0x3fff
    timing.cases=cases


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','analyze'])
    parser.add_argument('batch',type=int,choices=range(16))
    args=parser.parse_args();configure()
    if args.action=='generate':timing.generate(args.batch)
    else:getattr(timing,args.action)(timing.OUT/f'batch-{args.batch:02d}')
