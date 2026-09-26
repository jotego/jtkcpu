#!/usr/bin/env python3
"""LMUL operand/flag records using the physically validated CRC transport."""
import argparse
import hashlib
import json
from pathlib import Path
import framed_probe as framed

ROOT = framed.timing.ROOT/'artifacts/framed-lmul'
PAIRS = [(0,0),(1,1),(0xffff,0xffff),(0x8000,2),(0x55aa,0xaa55),(0x1234,0x5678),
         (0x8000,1),(1,0x8000),(0xffff,1),(0x100,0x100),(0xffff,0x8000),(0x8001,0xffff)]
CC = [0,1,2,4,8,0x20,0x50,0xff]


def generate():
    framed.ROOT=ROOT
    framed.generate()
    source=(ROOT/'probe.asm').read_text()
    first=source.index('        LDX #$2E09')
    last=source.index('; CRC-16/CCITT-FALSE',first)
    source=source[:first]+'''        LDS #$3FF0
        LDD $2E42
        SUBD #$00F0
        LDA #5
        MUL
        LDY #OPERANDS
        LEAY D,Y
        LDD ,Y
        STD $2E09
        LDD 2,Y
        STD $2E0B
        LDA 4,Y
        STA $2E0D
        PSHS A
        LDX ,Y
        LDY 2,Y
        LDU #$2F20
        LDD #$1234
        PULS CC
        LMUL
        PSHS CC
        STD $2E0E
        STX $2E10
        STY $2E12
        STU $2E14
        PULS A
        STA $2E16
        LDD #$BEEF
        STD $2E17
'''+source[last:]
    cases=[dict(x=x,y=y,cc=cc) for x,y in PAIRS for cc in CC]
    assert len(cases)==framed.COUNT
    table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['x']:04X},${r['y']:04X}\n        FCB ${r['cc']:02X}\n" for r in cases)
    source=source.replace('        ORG $FFF6',table+'        ORG $FFF6')
    (ROOT/'probe.asm').write_text(source)
    m=json.loads((ROOT/'manifest.json').read_text())
    m.update(cases=cases,source_sha256=hashlib.sha256(source.encode()).hexdigest(),dataset='LMUL boundary flags')
    (ROOT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')


def analyze(name):
    capture=json.loads((ROOT/(name+'.json')).read_text())
    assert capture.get('validated') and capture['complete']
    cases=capture['manifest']['cases']
    rows=[]
    for frame,case in zip(capture['frames'],cases):
        b=bytes.fromhex(frame['hex'])[9:25]
        assert int.from_bytes(b[0:2],'big')==case['x'] and int.from_bytes(b[2:4],'big')==case['y']
        assert b[4]==case['cc'] and b[14:]==b'\xbe\xef'
        output={reg:int.from_bytes(b[pos:pos+2],'big') for reg,pos in [('D',5),('X',7),('Y',9),('U',11)]}
        output['CC']=b[13]
        assert output['D']==0x1234 and output['U']==0x2f20
        product=case['x']*case['y']
        assert output['X']*65536+output['Y']==product
        rows.append(dict(**case,product=product,output=output))
    assert len(rows)==96
    models={
        'Z_only':lambda r:(r['cc']&~4)|(4 if r['product']==0 else 0),
        'Z_and_C_bit15':lambda r:(r['cc']&~5)|(4 if r['product']==0 else 0)|(1 if r['product']&0x8000 else 0),
        'Z_and_C_bit31':lambda r:(r['cc']&~5)|(4 if r['product']==0 else 0)|(1 if r['product']&0x80000000 else 0),
    }
    mismatches={name:[i for i,r in enumerate(rows) if fn(r)!=r['output']['CC']] for name,fn in models.items()}
    result=dict(records=rows,flag_model_mismatch_indices=mismatches,
                coverage='12 operand pairs x 8 initial CC values; partial coverage',capture=name+'.json')
    (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('96 complete LMUL records; flag model mismatches:',{k:len(v) for k,v in mismatches.items()})


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','collect','analyze'])
    parser.add_argument('--name',default='capture')
    parser.add_argument('--cc-page',type=int,choices=range(32))
    args=parser.parse_args()
    if args.cc_page is not None:
        ROOT=ROOT/f'batch-{args.cc_page:02d}'
        CC=list(range(args.cc_page*8,args.cc_page*8+8))
    framed.ROOT=ROOT
    if args.action=='generate':generate()
    elif args.action=='package':framed.package()
    elif args.action=='analyze':analyze(args.name)
    else:
        original_check=framed.check_frame
        framed.check_frame=lambda data,seq:original_check(data,seq,False)
        args.host_delay=0
        args.reconnect=False
        framed.collect(args)
