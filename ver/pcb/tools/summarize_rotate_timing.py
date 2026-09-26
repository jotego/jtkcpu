#!/usr/bin/env python3
"""Check the complete controlled byte-rotate timing matrix."""
import hashlib,json
from rotate_operand_timing import cases,timing
root=timing.ROOT/'artifacts/instruction-timing/rotate-operands'
expected=cases();rows=[]
for batch in range(16):
    folder=root/f'batch-{batch:02d}'
    data=json.loads((folder/'results.json').read_text())
    for filename,key in [('timing.asm','source_sha256'),('timing-128k.bin','image_sha256')]:
        assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==data['manifest'][key]
    baseline,target=data['results']
    assert baseline['measurement_role']=='baseline' and target['measurement_role']=='paired'
    assert baseline['input_clocks']==target['baseline_input_clocks']==30
    for key in ('opcode','input_D','cc','carry_in'):
        assert target[key]==expected[2*batch+1][key]
    assert min(s['samples'] for r in data['results'] for s in r['statistics'].values())>=4
    assert abs(target['input_clocks']-target['fitted_input_clocks'])<.15
    assert target['max_fit_residual_us']<=2
    rows.append(target)
summary=dict(cases=rows,scope='A/B operands 00/FF, each with carry 0/1; other operands remain unmeasured here.')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Controlled byte-rotate timings','',summary['scope'],'','Measured setup-only slope (30 CLK) is subtracted. Units reload D and CC50/51 before each rotation; result guards run after timing. Complete capture, hash, sample and fit gates pass. Counts use the user-confirmed 12 MHz reference and RP2040 timestamps, not direct clock-pin capture.','','| Instruction | Operand | Carry in | CLK | Fitted CLK |','|---|---|---:|---:|---:|']
for r in rows:lines.append(f"| {r['mnemonic']} | {r['value']:02X} | {r['carry_in']} | {r['input_clocks']} | {r['fitted_input_clocks']:.4f} |")
(root/'README.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
