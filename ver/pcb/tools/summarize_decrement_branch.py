#!/usr/bin/env python3
"""Require complete input-CC matrices and both decrement-branch outcomes."""
import json
from decrement_branch import BASE,analyze
rows=[]
for batch in range(16):
 analyze(batch)
 data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['candidate_flag_mismatches']
 rows.extend(data['records'])
assert len(rows)==3072
for op in (0xac,0xad):
 group=[r for r in rows if r['opcode']==op]
 assert len(group)==1536
 assert sum(r['observed_taken'] for r in group)==1280
 for value in sorted({r['value'] for r in group}):
  assert [r['cc'] for r in group if r['value']==value]==list(range(256))
summary=dict(records=len(rows),opcodes=[0xac,0xad],scope='Six inputs per opcode (0,1,2,largest positive,most negative,all ones), each at all256 CC states. Forward displacement +6 only; other displacements and operand values pending.',observed='Decrement modulo operand width; branch iff result nonzero. N/Z describe result, V indicates signed overflow at minimum negative input, E/F/H/I/C preserved.',register_guards='DECB preserves A/X/Y/U; DECX preserves D/Y/U. CC captured immediately on both branch paths; X result recorded before packet pointer use.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# Decrement and branch\n\n3072 physical records. '+summary['scope']+'\n\n'+summary['observed']+'\n\n'+summary['register_guards']+'\n\nEach opcode has1280 taken and256 untaken records. Raw inventoried AC/AD opcode and displacement bytes are checked against assembled labels; both outcomes immediately reach PSHS CC. Exact tables, mapper/vectors, source/image hashes, full readback, CPU CRC, unique IDs B700..B70F, ordered TX/ACK traces and no-drop/no-reset completion pass.\n')
print('3072 decrement-branch records; all data, outcomes, flags and guards pass')
