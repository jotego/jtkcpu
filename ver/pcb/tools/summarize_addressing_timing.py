#!/usr/bin/env python3
"""Summarize measured TST addressing costs without extending them to other opcodes."""
from pcb_paths import ROOT
import json
from pathlib import Path
root=ROOT / 'artifacts/instruction-timing'
rows=[r for f in (root/'indexed').glob('batch-*/results.json') for r in json.loads(f.read_text())['results']]
pc=[r for f in (root/'pc').glob('batch-*/results.json') for r in json.loads(f.read_text())['results']]
assert len(rows)==124 and len(pc)==24
shapes={6:'plain index',0:'postincrement 1',1:'postincrement 2',2:'predecrement 1',3:'predecrement 2',
        4:'8-bit displacement',5:'16-bit displacement',0x80:'A offset',0x81:'B offset',0x87:'D offset'}
summary=[]
for code,name in shapes.items():
    costs=[]
    for indirect in (False,True):
        group=[r for r in rows if r['mode']=='INDEXED' and r['postbyte']&0x8f==code|(8 if indirect else 0)]
        assert len(group)>=4 and len({r['input_clocks'] for r in group})==1
        costs.append(group[0]['input_clocks'])
    assert costs[1]-costs[0]==7
    summary.append(dict(mode=name,direct_CLK=costs[0],indirect_CLK=costs[1]))
for mode,name in (('EXT','extended'),('DIRECT','direct page')):
    group=[r for r in rows if r['mode']==mode]
    direct=next(r['input_clocks'] for r in group if not r['indirect'])
    indirect=next(r['input_clocks'] for r in group if r['indirect'])
    assert indirect-direct==7
    summary.append(dict(mode=name,direct_CLK=direct,indirect_CLK=indirect))
zero=next(r for r in pc if r['operand']=='extended RAM zero-data control')
assert zero['input_clocks']==21
assert {r['input_clocks'] for r in pc if '(8-bit)' in r['operand'] and not r['operand'].startswith('[')}=={21}
result=dict(instruction='TST',clock_hz=12000000,cases=148,registers=['X','Y','U','S'],costs=summary,
    pc_base_observation='explicit displacement is relative to its first operand byte',
    scope='Canonical tested encodings only. Other opcodes and additional displacements/aliases remain pending. Uniform RAM data checks indirection class; it does not prove every exact effective address.',
    data_controls='Extended RAM zero/nonzero both 21 CLK; tested PC 8-bit zero/positive/negative operands all 21 CLK')
(root/'indexed/addressing-summary.json').write_text(json.dumps(result,indent=2)+'\n')
lines=['# Measured TST addressing costs','',result['scope'],'',
 '| Addressing form | Direct CLK | Indirect CLK |','|---|---:|---:|']
for r in summary:lines.append(f"| {r['mode']} | {r['direct_CLK']} | {r['indirect_CLK']} |")
lines+=['',result['data_controls']+'.', '',
 'PC tests also cover plain, postincrement, accumulator offsets, and explicit displacements. PC-relative displacements use the address of the displacement field, not the end of the instruction. See ../pc/encoding-notes.md for the assembler discrepancy. PC predecrement modes remain pending.', '',
 'All captures passed one-boot/no-drop checks, fitted integer timing, final NZ guards and saved-D checks. X/Y/U/S automatic-address advancement is checked after each nonempty block. Inline PC data contains known instructions that would alter D if executed; the preserved-D guard verifies that those bytes were skipped.']
(root/'indexed/README.md').write_text('\n'.join(lines)+'\n')
print('148 addressing cases summarized; X/Y/U/S agree; all tested indirect increments are 7 CLK')
