#!/usr/bin/env python3
"""Focused operand-dependent DIV timing, with a measured setup-only reference."""
import argparse
import instruction_timing as timing

PAIRS=[(x,0) for x in (0,1,2,0x7f,0x80,0xff,0x100,0x101,0x1ff,0x7fff,0x8000,0x8001,0xff00,0xff7f,0xff80,0xffff)]
PAIRS += [(0,1),(1,1),(1,2),(2,2),(3,2),(4,2),(5,2),(255,2),(256,2),(257,2),
          (0x7fff,255),(0x8000,255),(0x8001,255),(0xffff,128),(0xffff,255),(0x1234,0x56)]


def cases():
    rows=[]
    for x,b in PAIRS:
        setup=bytes([0x42])+x.to_bytes(2,'big')+bytes([0x11,b])+bytes.fromhex('3c503d50')
        first=len(rows)+1
        common=dict(opcode=0xb5,mnemonic='DIV X,B',mode='CONTROLLED',encoding='b5',
                    operand=f'X={x:04X},B={b:02X}',dividend=x,divisor=b,
                    unit_setup_encoding=setup.hex(),
                    unit_setup_asm=f'        LDX #${x:04X}\n        LDB #${b:02X}\n        ANDCC #$50\n        ORCC #$50\n',
                    instruction_asm='DIV X,B',
                    coverage='Recorded X/B operands, CC50 reloaded before each instruction; setup-only slope subtracted')
        rows.append(dict(**common,id=first,measurement_role='baseline',unit_encoding=setup.hex()))
        quotient,remainder=divmod(x,b) if b else (65535,x&255)
        guard=f'        CMPX #${quotient:04X}\n        LBNE RAM_FAIL\n        CMPB #${remainder:02X}\n        LBNE RAM_FAIL\n'
        rows.append(dict(**common,id=first+1,measurement_role='paired',baseline_case_id=first,
                         unit_encoding=(setup+b'\xb5').hex(),postflight=guard))
    return rows


def configure():
    timing.OUT=timing.ROOT/'artifacts/instruction-timing/div-operands'
    timing.BATCH_SIZE=2
    timing.COUNTS=[0,64,128,256]
    timing.BLOCK_DELAY=0x3fff
    timing.cases=cases


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','analyze'])
    parser.add_argument('batch',type=int,choices=range(len(PAIRS)))
    args=parser.parse_args()
    configure()
    if args.action=='generate':timing.generate(args.batch)
    else:getattr(timing,args.action)(timing.OUT/f'batch-{args.batch:02d}')
