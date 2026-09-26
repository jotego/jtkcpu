#!/usr/bin/env python3
"""Require complete ANDCC/ORCC initial-state matrices at twelve masks."""
import json
from cc_logic import BASE,MASKS,analyze
rows=[]
for batch in range(32):
 analyze(batch)
 data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['candidate_flag_mismatches']
 rows.extend(data['records'])
assert len(rows)==6144
for opcode in (0x3c,0x3d):
 for mask in MASKS:
  selected=[r for r in rows if r['opcode']==opcode and r['mask']==mask]
  assert len(selected)==256 and [r['cc'] for r in selected]==list(range(256))
  for r in selected:
   expected=r['cc']&mask if opcode==0x3c else r['cc']|mask
   assert r['output_CC']==expected and r['output_D']==r['input_D']
summary=dict(records=len(rows),opcodes=[0x3c,0x3d],masks=list(MASKS),initial_CC='All 256 states for each mask and opcode',observed='ANDCC computes CC & mask; ORCC computes CC | mask, independently for all eight bits. D/X/Y/U unchanged.',scope='Twelve masks, including all single-bit masks, 00/FF/55/AA. Remaining mask values unmeasured; not the full mask-by-CC product.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# ANDCC and ORCC\n\n6144 physical records. '+summary['initial_CC']+'.\n\n'+summary['observed']+'\n\n'+summary['scope']+'\n\nMask selection precedes PULS CC; the tested immediate opcode is followed immediately by PSHS CC. Two complete input/output records share each CPU-CRC frame. D contains the mask in A and A5 in B, is echoed, and remains unchanged; CPU checks X/Y/U after CC capture. Exact bytes, tables, mapper/vector, hashes, full image readback, unique IDs B600..B61F, ordered TX/ACK traces and no-reset/no-drop completion pass.\n')
print('6144 complete CC-mask records; all models and guards pass')
