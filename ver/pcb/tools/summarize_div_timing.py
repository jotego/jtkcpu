#!/usr/bin/env python3
"""Summarize measured DIV timing without extrapolating candidate formulas."""
import hashlib
import json
from div_operand_timing import PAIRS,timing

root=timing.ROOT/'artifacts/instruction-timing/div-operands'
rows=[]
for batch,pair in enumerate(PAIRS):
    folder=root/f'batch-{batch:02d}'
    data=json.loads((folder/'results.json').read_text())
    meta=data['manifest']
    for filename,key in [('timing.asm','source_sha256'),('timing-128k.bin','image_sha256')]:
        assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==meta[key]
    baseline,target=data['results']
    assert baseline['measurement_role']=='baseline' and target['measurement_role']=='paired'
    assert (target['dividend'],target['divisor'])==pair
    assert baseline['input_clocks']==target['baseline_input_clocks']==39
    assert min(s['samples'] for r in data['results'] for s in r['statistics'].values())>=4
    assert abs(target['input_clocks']-target['fitted_input_clocks'])<.15
    rows.append(target)
models={
    'nonzero_25_plus_quotient_bit0':dict(tested=0,mismatches=[]),
    'zero_26_minus_dividend_bit15':dict(tested=0,mismatches=[]),
}
for r in rows:
    x,b=r['dividend'],r['divisor']
    key='nonzero_25_plus_quotient_bit0' if b else 'zero_26_minus_dividend_bit15'
    predicted=25+((x//b)&1) if b else 26-(x>>15)
    models[key]['tested']+=1
    if predicted!=r['input_clocks']:models[key]['mismatches'].append(dict(dividend=x,divisor=b,predicted=predicted,observed=r['input_clocks']))
previous={}
for file in (timing.ROOT/'artifacts/instruction-timing/paired').glob('batch-*/results.json'):
    for r in json.loads(file.read_text())['results']:
        if r['opcode']==0xb5 and r['measurement_role']=='paired':previous[r['operand']]=r['input_clocks']
overlaps=[r for r in rows if r['operand'] in previous]
assert overlaps and all(r['input_clocks']==previous[r['operand']] for r in overlaps)
summary=dict(cases=rows,candidate_models=models,previous_matching_cases=len(overlaps),
             scope='Recorded operands at initial CC50; candidate formulas are not exhaustive.',
             units='User-confirmed 12 MHz input CLK periods, inferred from repeated-block fits')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Operand-dependent DIV timing','',summary['units']+'.','',
       '32 target cases with a separately measured setup-only reference for every case. Each repeated unit reloads X, B and CC50. Baseline setup costs 39 CLK. Nonempty blocks check final quotient and remainder after the end marker.',
       'Fits use 0/64/128/256 repetitions. The first four cases have ~10.6 ms watchdog spacing; later cases use ~42.3 ms. A rejected 10.6 ms capture lost two trace entries during an 88 ms host snapshot gap, with zero FIFO drops. Its source/image/raw capture is retained under attempts/.',
       '',f'All {len(overlaps)} overlapping cases agree with the earlier slower timing captures.','',summary['scope'],'']
for name,result in models.items():lines.append(f"Candidate `{name}`: {len(result['mismatches'])} mismatches in {result['tested']} cases.")
lines+=['','| Dividend X | Divisor B | CLK | Fitted CLK |','|---|---|---:|---:|']
for r in rows:lines.append(f"| {r['dividend']:04X} | {r['divisor']:02X} | {r['input_clocks']} | {r['fitted_input_clocks']:.4f} |")
(root/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({key:{'tested':v['tested'],'mismatches':len(v['mismatches'])} for key,v in models.items()}))
