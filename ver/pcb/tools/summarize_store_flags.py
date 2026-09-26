#!/usr/bin/env python3
"""Require the seven guarded store matrices and retain complete raw results."""
import json
from store_flags import BASE,OPS,analyze,cases
rows=[];instructions=[]
for batch,(op,name,reg,width) in enumerate(OPS):
 analyze(batch);data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['candidate_flag_mismatches'];assert len(data['records'])==96
 assert [{k:r[k] for k in cases(batch)[0]} for r in data['records']]==cases(batch)
 rows.extend(data['records']);instructions.append(dict(opcode=op,mnemonic=name,records=96))
assert len(rows)==672
summary=dict(records=672,instructions=instructions,scope='STA/STB/STD/STX/STY/STU/STS at extended address2F40;12 source values xCC00/01/04/05/08/09/72/FF. Other values/CC/address modes pending.',observed='Stored data matches the source; source registers unchanged; N/Z describe stored byte or word, V=0, E/F/H/I/C preserved in sample.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# Store data and flags\n\n'+summary['scope']+'\n\n'+summary['observed']+'\n\nEach destination starts as the bitwise complement of the source. A5/5A guards directly surround the operand. STS uses the validated U-stack capture path and checks S unchanged before restoring it; STU uses S-stack capture. Host verifies full D/X/Y/U and memory data. All table/encoding/hash, readback, CPU CRC, identity, TX/ACK, completion and no-reset/no-drop gates pass.\n')
print('672 records across7 store primaries; all guards and models pass')
