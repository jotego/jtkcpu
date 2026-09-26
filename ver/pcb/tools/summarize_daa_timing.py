#!/usr/bin/env python3
"""Check the controlled DAA timing matrix and sampled correction-count fit."""
import hashlib,json
from daa_operand_timing import cases,timing
root=timing.ROOT/'artifacts/instruction-timing/daa-operands'
expected=cases();rows=[]
for batch in range(16):
    folder=root/f'batch-{batch:02d}';data=json.loads((folder/'results.json').read_text())
    for filename,key in [('timing.asm','source_sha256'),('timing-128k.bin','image_sha256')]:
        assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==data['manifest'][key]
    baseline,target=data['results'];assert baseline['measurement_role']=='baseline' and target['measurement_role']=='paired'
    assert baseline['input_clocks']==target['baseline_input_clocks']==30
    for key in ('opcode','input_D','cc'):assert target[key]==expected[2*batch+1][key]
    assert min(s['samples'] for r in data['results'] for s in r['statistics'].values())>=4
    assert abs(target['input_clocks']-target['fitted_input_clocks'])<.15 and target['max_fit_residual_us']<=2
    a=target['value'];cc=target['cc'];corrections=int(bool(cc&32) or (a&15)>9)+int(bool(cc&1) or a>0x99)
    target['correction_count_only_clocks']=14-3*corrections
    target['candidate_formula_clocks']=14-(3 if cc&32 else int((a&15)>9))-(3 if cc&1 else int(a>0x99))
    rows.append(target)
bad=[i for i,r in enumerate(rows) if r['candidate_formula_clocks']!=r['input_clocks']]
summary=dict(cases=rows,formula='14 - (H ? 3 : (low_nibble>9 ? 1 : 0)) - (C ? 3 : (A>0x99 ? 1 : 0))',formula_mismatches=bad,correction_count_only_mismatches=[i for i,r in enumerate(rows) if r['correction_count_only_clocks']!=r['input_clocks']],scope='A=00/0A/A0/FF, each with all four H/C inputs; other timing operands pending.')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Controlled DAA timing','',summary['scope'],'','Sampled candidate: '+summary['formula']+'. Mismatch indices: '+str(bad)+'.','',
 'Measured setup-only slope is 30 CLK and is subtracted. Every unit reloads D and CC; data guards run after the window. All hash, complete capture, minimum-sample, residual and integer-fit gates pass. Counts are input periods at user-confirmed 12 MHz, fitted to RP2040 timestamps.','','| A | CC | CLK | Fitted CLK |','|---|---|---:|---:|']
for r in rows:lines.append(f"| {r['value']:02X} | {r['cc']:02X} | {r['input_clocks']} | {r['fitted_input_clocks']:.4f} |")
(root/'README.md').write_text('\n'.join(lines)+'\n')
print('Formula mismatches:',bad);print([(r['value'],r['cc'],r['input_clocks']) for r in rows])
