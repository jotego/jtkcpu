#!/usr/bin/env python3
"""Capture DIV X,B over boundary operands and every initial CC value."""
import argparse
import hashlib
import json
import framed_lmul as template
import framed_probe as framed

ROOT=framed.timing.ROOT/'artifacts/framed-div'
PAIRS=[(0,1),(1,1),(0xffff,1),(0xffff,0xff),(0x8000,2),(0x1234,0x56),
       (0,0),(0xffff,0),(1,2),(0x7fff,1),(0x8000,1),(0x8000,0)]


def generate(page):
    template.ROOT=ROOT
    template.PAIRS=PAIRS
    template.CC=list(range(page*8,page*8+8))
    template.generate()
    source=(ROOT/'probe.asm').read_text()
    old='''        LDX ,Y
        LDY 2,Y
        LDU #$2F20
        LDD #$1234
        PULS CC
        LMUL
'''
    new='''        LDX ,Y
        LDB 3,Y
        LDA #$12
        LDY #$2F10
        LDU #$2F20
        PULS CC
        DIV X,B
'''
    assert source.count(old)==1
    source=source.replace(old,new).replace('LDD #$7B01',f'LDD #${0xd100+page:04X}')
    (ROOT/'probe.asm').write_text(source)
    m=json.loads((ROOT/'manifest.json').read_text())
    for case in m['cases']:case['b']=case.pop('y')
    m.update(dataset='DIV X,B boundary flags',run_id=0xd100+page,
             source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (ROOT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')


def analyze(name):
    capture=json.loads((ROOT/(name+'.json')).read_text())
    assert capture.get('validated') and capture['complete']
    cases=capture['manifest']['cases']
    rows=[]
    for frame,case in zip(capture['frames'],cases):
        data=bytes.fromhex(frame['hex'])
        framed.check_frame(data,frame['sequence'],False,capture['manifest']['run_id'])
        b=data[9:25]
        assert int.from_bytes(b[:2],'big')==case['x']
        assert int.from_bytes(b[2:4],'big')==case['b'] and b[4]==case['cc']
        assert b[14:]==b'\xbe\xef'
        output={reg:int.from_bytes(b[pos:pos+2],'big') for reg,pos in [('D',5),('X',7),('Y',9),('U',11)]}
        output['CC']=b[13]
        rows.append(dict(**case,output=output))
    assert len(rows)==96
    mismatches=[]
    for i,r in enumerate(rows):
        x,b,cc=r['x'],r['b'],r['cc']
        quotient,remainder=divmod(x,b) if b else (65535,x&255)
        expected=dict(D=0x1200|remainder,X=quotient,Y=0x2f10,U=0x2f20,
                      CC=(cc&~12)|(8 if quotient&0x8000 else 0)|(4 if quotient==0 else 0))
        if r['output']!=expected:mismatches.append(dict(index=i,expected=expected,observed=r['output']))
    result=dict(records=rows,model_mismatches=mismatches,capture=name+'.json',
                coverage='12 dividend/divisor pairs x 8 initial CC values; partial operands')
    (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'96 complete DIV records; quotient/remainder/NZ-only model mismatches: {len(mismatches)}')
    assert not mismatches,'Physical observations disagree with the candidate model; retained for review'


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','collect','analyze'])
    parser.add_argument('--cc-page',type=int,choices=range(32),required=True)
    parser.add_argument('--name',default='capture')
    args=parser.parse_args()
    ROOT=ROOT/f'batch-{args.cc_page:02d}'
    framed.ROOT=ROOT
    if args.action=='generate':generate(args.cc_page)
    elif args.action=='package':framed.package()
    elif args.action=='analyze':analyze(args.name)
    else:
        run_id=json.loads((ROOT/'manifest.json').read_text())['run_id']
        original_check=framed.check_frame
        framed.check_frame=lambda data,seq:original_check(data,seq,False,run_id)
        args.host_delay=0
        args.reconnect=False
        framed.collect(args)
