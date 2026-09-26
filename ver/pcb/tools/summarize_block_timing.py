#!/usr/bin/env python3
"""Derive block-operation timing models only where all recorded points agree."""
from pcb_paths import ROOT
import json,re
from pathlib import Path
root=ROOT / 'artifacts/instruction-timing/paired'
rows=[r for f in root.glob('batch-*/results.json') for r in json.loads(f.read_text())['results'] if r.get('measurement_role')=='paired']
summary=[]
for opcode in (0xb6,0xb7,0xcf,0xd0):
    group=[r for r in rows if r['opcode']==opcode]
    expected={1,512} if opcode==0xb7 else {1,2,8,16,128,512}
    by_n={int(re.search(r'U=(\d+)',r['operand'])[1]):r for r in group}
    assert set(by_n)==expected,f'{opcode:02X}: incomplete count sweep'
    assert all(r.get('postflight') for r in group),'Missing pointer/data/sentinel guards'
    points=sorted(by_n)
    slope=(by_n[points[1]]['input_clocks']-by_n[points[0]]['input_clocks'])/(points[1]-points[0])
    base=by_n[points[0]]['input_clocks']-points[0]*slope
    affine=all(r['input_clocks']==base+slope*n for n,r in by_n.items())
    formula=f'{base:g} + {slope:g} * U' if affine else None
    summary.append(dict(opcode=f'{opcode:02X}',mnemonic=group[0]['mnemonic'],tested_U=points,
        formula_CLK=formula,affine_on_tested_counts=affine,count_unit='words' if opcode==0xd0 else 'bytes',
        zero_count_status='not measured',records=[dict(U=n,input_CLK=r['input_clocks'],written_bytes=r['written_bytes']) for n,r in sorted(by_n.items())]))
    print(f'{opcode:02X}',formula or 'non-affine on measured counts')
(root/'block-formulas.json').write_text(json.dumps(summary,indent=2)+'\n')
