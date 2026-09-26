#!/usr/bin/env python3
"""Require all branch outcomes and every initial CC state before reporting."""
import json
from branch_flags import BASE,OPS,analyze,cases
rows=[];changed=[]
for batch in range(43):
    analyze(batch)
    data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
    changed.extend(batch*192+i for i in data['changed_CC_indices']);rows.extend(data['records'])
assert len(rows)==8256
expected=cases()
assert [{k:r[k] for k in expected[0]} for r in rows]==expected
counts=[]
for op in OPS:
    observed=[r for r in rows[:8192] if r['opcode']==op['opcode']]
    assert [r['cc'] for r in observed]==list(range(256))
    counts.append(dict(opcode=op['opcode'],mnemonic=op['mnemonic'],taken=sum(r['observed_taken'] for r in observed),untaken=sum(not r['observed_taken'] for r in observed)))
summary=dict(records=len(rows),primary_records=8192,extra_DFFFF_records=64,CC_changes=changed,instructions=counts,
    scope='32 short/long branch opcodes x all256 CC states with D1234, plus each opcode at CC00/FF with DFFFF. Forward displacement +6; other displacements and boundary placements pending.',
    observed='Each condition matches the independently evaluated flag predicate; all captured CC bits preserved; D/X/Y/U preserved.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');assert not changed,changed[:10]
lines=['# Physical branch outcomes and flags','',summary['scope'],'',summary['observed'],'','Every branch has two separate paths: immediate PSHS CC after the tested branch on either outcome, then D/CC capture and an E6/E7 outcome marker. Both paths preserve the original D until stored. Dispatch occurs before PULS CC. Every image checks exact assembled displacement and PSHS landing, mapper/vector/table/hash invariants, full readback, CPU CRC, packet image/sequence, complete TX/ACK trace and no-reset/no-drop completion.','','| Opcode | Instruction | Taken states | Untaken states |','|---|---|---:|---:|']
for r in counts:lines.append(f"| {r['opcode']:02X} | {r['mnemonic']} | {r['taken']} | {r['untaken']} |")
(BASE/'README.md').write_text('\n'.join(lines)+'\n');print('8256 records; 32 full CC matrices; no CC changes')
