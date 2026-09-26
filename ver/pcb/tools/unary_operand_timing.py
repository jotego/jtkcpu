#!/usr/bin/env python3
"""Reload NEG/ABS operands before every timed instruction, subtract measured setup."""
import argparse
import instruction_timing as timing
from framed_unary import cases as vector_cases

OPERANDS=vector_cases('boundary')+vector_cases('ordinary')


def cases():
    rows=[]
    for operand in OPERANDS:
        opcode=operand['opcode'];d=operand['input_D']
        setup=bytes([0x40])+d.to_bytes(2,'big')+bytes.fromhex('3c503d50')
        first=len(rows)+1
        common=dict(opcode=opcode,mnemonic=operand['mnemonic'],mode='CONTROLLED',encoding=f'{opcode:02x}',
                    operand=f"{operand['reg']}={operand['value']:0{operand['width']//4}X},D={d:04X}",
                    value=operand['value'],input_D=d,reg=operand['reg'],width=operand['width'],
                    unit_setup_encoding=setup.hex(),unit_setup_asm=f'        LDD #${d:04X}\n        ANDCC #$50\n        ORCC #$50\n',
                    instruction_asm=operand['mnemonic'],
                    coverage='Recorded operand and CC50 restored before every instruction; separately measured setup slope subtracted')
        rows.append(dict(**common,id=first,measurement_role='baseline',unit_encoding=setup.hex()))
        value,width=operand['value'],operand['width']
        result=(-value if operand['mnemonic'].startswith('NEG') or value&(1<<(width-1)) else value)&((1<<width)-1)
        expected=result if operand['reg']=='D' else ((result<<8)|0xa5 if operand['reg']=='A' else 0x5a00|result)
        guard=f'        LDD $3F00\n        CMPD #${expected:04X}\n        LBNE RAM_FAIL\n'
        rows.append(dict(**common,id=first+1,measurement_role='paired',baseline_case_id=first,
                         unit_encoding=(setup+bytes([opcode])).hex(),
                         capture_asm='        STD $3F00\n',postflight=guard))
    return rows


def configure():
    timing.OUT=timing.ROOT/'artifacts/instruction-timing/unary-operands'
    timing.BATCH_SIZE=2
    timing.COUNTS=[0,64,128,256]
    timing.BLOCK_DELAY=0x3fff
    timing.cases=cases


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','analyze'])
    parser.add_argument('batch',type=int,choices=range(len(OPERANDS)))
    args=parser.parse_args();configure()
    if args.action=='generate':timing.generate(args.batch)
    else:getattr(timing,args.action)(timing.OUT/f'batch-{args.batch:02d}')
