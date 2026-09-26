#!/usr/bin/env python3
"""Validate mask coverage and complete CC matrices for all four stack opcodes."""
import json
from stack_flags import BASE,MASKS,CC,analyze,predicted
rows=[]
for batch in range(36):
 analyze(batch)
 data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['candidate_mismatches']
 rows.extend(data['records'])
assert len(rows)==3456
for op in (12,13,14,15):
 group=[r for r in rows if r['opcode']==op];assert len(group)==864
 for mask in MASKS:assert [r['cc'] for r in group[:96] if r['mask']==mask]==list(CC)
 for mask in (0,1,255):assert [r['cc'] for r in group[96:] if r['mask']==mask]==list(range(256))
 assert all(r['output_registers']==predicted(r) for r in group)
summary=dict(records=3456,opcodes=[12,13,14,15],scope='Each opcode: masks00/01/02/04/08/10/20/40/80/55/AA/FF at eightCC presets, then masks00/01/FF at all256 initialCC.24 overlapping mask/CC cases per opcode retained. Other masks, data patterns and stack addresses remain pending.',observed='Pushes preserveCC and registers apart from stack pointer. Pulls preserveCC unless maskbit0 is selected, then load the prepared complement of incomingCC. Selected registers and PC restore correctly; unselected registers unchanged. Exact stack byte order, every frame byte and adjacent sentinels checked onCPU; both pointers captured after alternate-stack CC readback.',layout='Ascending frame bytes for selected bits: CC,A,B,DP,Xhi,Xlo,Yhi,Ylo,otherSPhi,otherSPlo,PChi,PClo. PushPC is the next opcode address; pullPC reaches a distinct immediate-capture destination.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# Stack masks, data and flags\n\n3456 physical records. '+summary['scope']+'\n\n'+summary['observed']+'\n\n'+summary['layout']+'\n\nTarget stack starts at3E00; capture stack starts3FF0 and may be restored to3D00 by bit6 pulls. All pointers stay in workRAM. Input seeds A5A/BA5/X2193/Y32C4/DP37; pull data A96/B3C/X2A51/Y34B2/DP69. Exact opcodes/masks/return destinations, tables/source/image hashes, mapper/vectors, full readback, CPU CRC, IDs BE00..BE23, complete TX/ACK traces and no-drop/no-reset completion pass.\n')
print('3456 stack records; all frame, pointer, register and flag checks pass')
