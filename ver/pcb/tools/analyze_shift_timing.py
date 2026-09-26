#!/usr/bin/env python3
"""Summarize measured shift timing; do not infer functional shift results."""
from pcb_paths import ROOT
import json
from pathlib import Path
root=ROOT / 'artifacts/instruction-timing/shift'
rows=[r for f in sorted(root.glob('batch-*/results.json')) for r in json.loads(f.read_text())['results']]
assert len(rows)==110, f'Incomplete sweep: {len(rows)}/110'
expected={0,1,2,7,8,15,16,17,31,32,255}
summary=[]
for opcode in range(0xb8,0xc2):
    group=[r for r in rows if r['opcode']==opcode]
    by_count={r['shift_count']:r for r in group}
    assert len(group)==11 and set(by_count)==expected
    base=by_count[0]['input_clocks']
    increment=by_count[1]['input_clocks']-base
    mask15=all(r['input_clocks']==base+increment*(c&15) for c,r in by_count.items())
    full_byte=all(r['input_clocks']==base+increment*c for c,r in by_count.items())
    result=dict(opcode=f'{opcode:02X}',mnemonic=group[0]['mnemonic'],mode=group[0]['mode'],
                measured_counts=sorted(expected),base_CLK=base,per_count_CLK=increment,
                low_four_bits_fit=mask15,full_byte_fit=full_byte,
                formula=f'{base} {"+" if increment>=0 else "-"} {abs(increment)} * (count & 15)' if mask15 else None,
                max_fitted_error_CLK=max(abs(r['fitted_input_clocks']-r['input_clocks']) for r in group),
                coverage='Timing only, recorded initial operand and addressing; functional result and flags pending')
    summary.append(result)
    print(result['opcode'],result['mnemonic'],result['mode'],result['formula'] or 'no low-four-bit model')
(root/'timing-formulas.json').write_text(json.dumps(summary,indent=2)+'\n')
