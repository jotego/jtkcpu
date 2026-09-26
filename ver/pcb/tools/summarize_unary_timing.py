#!/usr/bin/env python3
"""Require every controlled NEG/ABS operand timing before reporting a table."""
import hashlib
import json
from unary_operand_timing import OPERANDS,timing

root=timing.ROOT/'artifacts/instruction-timing/unary-operands'
rows=[]
for batch,operand in enumerate(OPERANDS):
    folder=root/f'batch-{batch:02d}'
    data=json.loads((folder/'results.json').read_text())
    manifest=data['manifest']
    for filename,key in [('timing.asm','source_sha256'),('timing-128k.bin','image_sha256')]:
        assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==manifest[key]
    baseline,target=data['results']
    assert baseline['measurement_role']=='baseline' and target['measurement_role']=='paired'
    assert baseline['input_clocks']==target['baseline_input_clocks']==30
    assert target['opcode']==operand['opcode'] and target['input_D']==operand['input_D']
    assert min(s['samples'] for r in data['results'] for s in r['statistics'].values())>=4
    assert abs(target['input_clocks']-target['fitted_input_clocks'])<.15
    rows.append(target)
assert len(rows)==24
groups={}
for row in rows:groups.setdefault(row['mnemonic'],[]).append(row)
summary=dict(cases=rows,by_instruction={name:dict(operands=[r['value'] for r in rs],
    measured_counts=[r['input_clocks'] for r in rs],constant_in_sample=len({r['input_clocks'] for r in rs})==1)
    for name,rs in groups.items()},scope='Four recorded operands per instruction with CC50 restored before every execution; other operands/CC timing pending')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Controlled NEG/ABS operand timing','',
       '24 paired timing cases use 0/64/128/256 repetitions and a separately measured setup-only reference. Each repeated unit reloads D and CC50. Setup costs 30 input CLK periods. The target block stores D before its end marker, then checks the result afterward; that store contributes constant overhead, not per-instruction time.',
       'Every batch uses ~42.3 ms watchdog spacing, 5 ms requested polling and three-second observation. All existing hash, complete-trace, boot/drop, sample-count, residual and integer-fit gates pass.',
       '',summary['scope']+'.','',
       '| Instruction | Operand | CLK | Fitted CLK |','|---|---|---:|---:|']
for row in rows:lines.append(f"| {row['mnemonic']} | {row['value']:0{row['width']//4}X} | {row['input_clocks']} | {row['fitted_input_clocks']:.4f} |")
(root/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(summary['by_instruction']))
