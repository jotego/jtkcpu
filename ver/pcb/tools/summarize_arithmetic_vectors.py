#!/usr/bin/env python3
"""Check explicit candidate data/flag models against the captured vectors."""
from pcb_paths import ROOT
import json,re
from pathlib import Path
root=ROOT / 'artifacts/arithmetic-vectors'
all_rows=[]
for folder,count in ((root,46),(root/'blocks',40)):
    data=json.loads((folder/'results.json').read_text());rows=data['results'];assert len(rows)==count
    out=[]
    for r in rows:
        code=r['opcode'];cc=r['cc'];text=r['operand']
        expected={'D':0x1234,'X':0x2f00,'Y':0x2f10,'U':0x2f20}
        if code==0xb3:
            a,b=[int(v,16) for v in re.findall(r'[AB]=([0-9A-F]+)',text)]
            value=a*b;expected['D']=value
            flags=(cc&0xfa)|(4 if value==0 else 0)|((value>>7)&1)
            model='Z from product, C from product bit 7; other tested flags preserved'
        elif code==0xb4:
            x,y=[int(v,16) for v in re.findall(r'[XY]=([0-9A-F]+)',text)]
            value=x*y;expected['X']=value>>16;expected['Y']=value&65535
            flags=(cc&0xfb)|(4 if value==0 else 0)
            model='Z from 32-bit product; other tested flags preserved'
        elif code==0xb5:
            x,b=[int(v,16) for v in re.findall(r'[XB]=([0-9A-F]+)',text)]
            q,rem=divmod(x,b) if b else (65535,x&255)
            expected['X']=q;expected['D']=0x1200|rem
            flags=(cc&0xf3)|(8 if q&0x8000 else 0)|(4 if q==0 else 0)
            model='N/Z from quotient; other tested flags preserved; zero divisor output is an observed model'
        else:
            n=int(re.search(r'U=(\d+)',text)[1]);copied=1 if code==0xb7 else n
            expected['U']=n-1 if code==0xb7 else 0
            expected['X']=0x3000+copied*(2 if code==0xd0 else 1)
            if code in (0xb6,0xb7):expected['Y']=0x2800+copied
            if code==0xcf:expected['D']=0x5534
            flags=(cc&0xfb)|(4 if expected['U']==0 else 0)
            model='Z from final U; other tested flags preserved'
        result=dict(**r,expected_registers=expected,expected_CC=flags,
                    data_matches=all(r['output_'+reg]==v for reg,v in expected.items()),
                    flags_match=r['output_CC']==flags,candidate_flag_model=model)
        out.append(result)
    (folder/'summary.json').write_text(json.dumps(dict(results=out,coverage='Recorded operands with initial CC50/7F only; general rules remain to be tested'),indent=2)+'\n')
    lines=['# Arithmetic and block result/CC probes','',
      'Scope: recorded operands, initial CC50/7F. These models fit the observed subset; they are not exhaustive flag specifications. Baseline capture was separately checked over all 256 CC values. Raw captures include complete IDs, completion markers and matching USB/event-ring bytes.', '',
      '| Operation | Inputs | Initial CC | D | X | Y | U | CC | Data/model match |','|---|---|---|---|---|---|---|---|---|']
    for r in out:lines.append(f"| {r['mnemonic']} | {r['operand']} | {r['cc']:02X} | {r['output_D']:04X} | {r['output_X']:04X} | {r['output_Y']:04X} | {r['output_U']:04X} | {r['output_CC']:02X} | {r['data_matches'] and r['flags_match']} |")
    (folder/'README.md').write_text('\n'.join(lines)+'\n')
    all_rows+=out
print('Vectors:',len(all_rows),'data mismatches:',sum(not r['data_matches'] for r in all_rows),'flag model mismatches:',sum(not r['flags_match'] for r in all_rows))
assert all(r['data_matches'] and r['flags_match'] for r in all_rows)
