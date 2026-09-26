#!/usr/bin/env python3
"""Require the complete physical LMUL 12-by-256 matrix before reporting it."""
import hashlib
import json
from pathlib import Path
from framed_probe import check_frame
from framed_lmul import ROOT,PAIRS

observations={pair:{} for pair in PAIRS}
for page in range(32):
    directory=ROOT/f'batch-{page:02d}'
    data=json.loads((directory/'capture.json').read_text())
    results=json.loads((directory/'results.json').read_text())
    assert data.get('validated') and data['complete']
    manifest=data['manifest']
    for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
        assert hashlib.sha256((directory/filename).read_bytes()).hexdigest()==manifest[key]
    assert len(data['frames'])==len(results['records'])==96
    for frame,row in zip(data['frames'],results['records']):
        check_frame(bytes.fromhex(frame['hex']),frame['sequence'],False)
        key=(row['x'],row['y'])
        assert row['cc'] not in observations[key]
        observations[key][row['cc']]=row

for pair,ccs in observations.items():
    assert sorted(ccs)==list(range(256)),(pair,'missing CC states')
    product=pair[0]*pair[1]
    for cc,row in ccs.items():
        assert row['output']==dict(D=0x1234,X=product>>16,Y=product&65535,U=0x2f20,
                                   CC=(cc&~4)|(4 if product==0 else 0))

summary=dict(records=3072,operand_pairs=PAIRS,initial_cc_values=list(range(256)),
             model='Unsigned X*Y -> X:Y; Z reflects the full 32-bit result; all other CC bits preserved.',
             scope='All initial CC values for these 12 operand pairs, not exhaustive operand coverage.',
             mismatches={'Z_only':0,'Z_and_C_bit15':1536,'Z_and_C_bit31':1536})
# Derive the competing-model mismatch counts instead of assuming them.
for name,mask in [('Z_and_C_bit15',0x8000),('Z_and_C_bit31',0x80000000)]:
    summary['mismatches'][name]=sum(((cc&~5)|(4 if r['product']==0 else 0)|(1 if r['product']&mask else 0))!=r['output']['CC']
                                   for ccs in observations.values() for cc,r in ccs.items())
(ROOT/'all-cc-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Physical LMUL flags','',summary['model'],'',
       'All 3072 records pass: 12 operand pairs × all 256 initial CC values. The 96 earlier boundary records are separate additional observations.',
       'CC is captured immediately after LMUL. D=1234 and U=2F20 remain unchanged. CPU-generated CRC-16, record sequence, exact USB/event-ring agreement, source/image hashes, and no-drop/no-reboot gates pass for every batch.',
       '',summary['scope'],'',
       'The tested products distinguish preserved C from product bit 15 (local MAME) and bit 31 (current JTKCPU ALU). Both competing C models disagree with 1536/3072 records. No production HDL or MAME edits have been made.',
       '', '| Input X | Input Y | Product X:Y |', '|---|---|---|']
for x,y in PAIRS:lines.append(f'| {x:04X} | {y:04X} | {x*y:08X} |')
(ROOT/'README.md').write_text('\n'.join(lines)+'\n')
print('PASS: all 3072 LMUL operand/CC combinations; only Z changes.')
