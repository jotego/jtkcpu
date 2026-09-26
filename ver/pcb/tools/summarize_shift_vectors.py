#!/usr/bin/env python3
"""Compare recorded single-operation outputs with explicit shift hypotheses."""
from pcb_paths import ROOT
import argparse,json
from pathlib import Path
a=argparse.ArgumentParser();a.add_argument('--dataset',choices=['initial','boundary'],default='initial');args=a.parse_args()
root=ROOT / 'artifacts/shift-vectors'
if args.dataset!='initial':root=root/args.dataset
rows=[r for f in sorted(root.glob('batch-*/results.json')) for r in json.loads(f.read_text())['results']]
assert len(rows)==(366 if args.dataset=='initial' else 360), f'Incomplete capture: {len(rows)}'
baseline=[r for r in rows if r['kind']=='baseline']
assert len(baseline)==(256 if args.dataset=='initial' else 0)
assert all(r['output_cc']==r['cc'] and r['output_value']==r['input_d'] for r in baseline)
if args.dataset=='boundary':
    gate=[r for f in root.parent.glob('batch-*/results.json') for r in json.loads(f.read_text())['results'] if r['kind']=='baseline']
    assert len(gate)==256 and {r['cc'] for r in gate}==set(range(256))
    assert all(r['output_cc']==r['cc'] and r['output_value']==0x1234 for r in gate)

def reference(op,value,carry,count):
    for _ in range(count):
        if op=='LSRD': value,carry=value>>1,value&1
        elif op=='ASRD':value,carry=(value>>1)|(value&0x8000),value&1
        elif op=='RORD':value,carry=(carry<<15)|(value>>1),value&1
        elif op=='ASLD':value,carry=(value<<1)&0xffff,value>>15
        elif op=='ROLD':value,carry=((value<<1)|carry)&0xffff,value>>15
        else:raise ValueError(op)
    return value,carry

result=[]
for r in rows:
    if r['kind']!='shift':continue
    n=r['shift_count']&15
    value,carry=reference(r['mnemonic'],r['input_d'],r['cc']&1,n)
    v=r['input_d']
    if r['mnemonic']=='RORD':rotate=((v>>n)|(v<<(16-n)))&0xffff
    elif r['mnemonic']=='ROLD':rotate=((v<<n)|(v>>(16-n)))&0xffff
    else:rotate=value
    result.append(dict(**r,low_four_bit_reference_value=value,low_four_bit_reference_C=carry,
                       data_matches_low_four_bit_model=r['output_value']==value,
                       data_matches_rotate16_model=r['output_value']==rotate,
                       C_preserved=(r['output_cc']&1)==(r['cc']&1),
                       CC_matches_NZ_clear_VC=r['output_cc']==((r['cc']&0xf0)|(8 if r['output_value']&0x8000 else 0)|(4 if r['output_value']==0 else 0)),
                       C_matches_low_four_bit_model=(r['output_cc']&1)==carry))
(root/'summary.json').write_text(json.dumps(dict(baseline_CC_values=len(baseline),results=result),indent=2)+'\n')
lines=['# Single-operation shift data and CC captures','',
 'Capture gate: all 256 initial CC values were recovered exactly through PSHS CC / PULS A, with D=1234 preserved. Each record was received identically through USB and the timestamp ring, with complete sequence and completion markers.', '',
 ('Coverage: initial operand 1234 and CC=50.' if args.dataset=='initial' else 'Coverage: initial operands 0000, 8001, FFFF and CC=50/7F.')+' Selected counts, immediate and extended-memory forms. These observations do not establish general flag rules. The comparison model applies count & 15 and ordinary shift/rotate-through-carry semantics; a separate 16-bit rotation model is recorded in summary.json. Mismatches remain visible.', '',
 '| Opcode | Operation | Count | Input | Initial CC | Result | CC | Model result | Data matches | C matches |','|---|---|---:|---|---|---|---|---|---|---|']
for r in result:
    lines.append(f"| {r['opcode']:02X} | {r['mnemonic']} {r['mode']} | {r['shift_count']} | {r['input_d']:04X} | {r['cc']:02X} | {r['output_value']:04X} | {r['output_cc']:02X} | {r['low_four_bit_reference_value']:04X} | {r['data_matches_low_four_bit_model']} | {r['C_matches_low_four_bit_model']} |")
(root/'README.md').write_text('\n'.join(lines)+'\n')
print('Baseline CC cases in this dataset:',len(baseline))
for op in range(0xb8,0xc2):
    group=[r for r in result if r['opcode']==op]
    print(f'{op:02X}',len(group),'cases; rotate16/shift data mismatches',sum(not r['data_matches_rotate16_model'] for r in group),'CC values',sorted({f"{r['output_cc']:02X}" for r in group}))
print('Data model mismatches:',sum(not r['data_matches_low_four_bit_model'] for r in result))
print('Carry model mismatches:',sum(not r['C_matches_low_four_bit_model'] for r in result))
print('Shift/rotate16 data model mismatches:',sum(not r['data_matches_rotate16_model'] for r in result))
print('Carry not preserved:',sum(not r['C_preserved'] for r in result))

print('NZ result / V,C clear / upper CC preserved model mismatches:',sum(not r['CC_matches_NZ_clear_VC'] for r in result))
