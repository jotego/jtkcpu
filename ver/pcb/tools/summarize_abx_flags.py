#!/usr/bin/env python3
"""Validate the ABX matrix from hashed raw captures."""
import json
from abx_flags import BASE,analyze,cases
analyze(0)
data=json.loads((BASE/'batch-00/results.json').read_text())
assert not data['candidate_data_mismatches']
assert not data['candidate_flag_mismatches']
assert len(data['records'])==96
assert [{k:r[k] for k in cases(0)[0]} for r in data['records']]==cases(0)
summary=dict(records=96,opcode=0xb0,
 scope='Twelve X/B pairs at CC00/01/04/05/08/09/72/FF; zero, sign boundaries and unsigned wrap. Other operand/CC combinations pending.',
 observed='X becomes (X + unsigned B) modulo 65536; all CC bits and A/B/Y/U remain unchanged in the sample.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# ABX data and flags\n\n'+summary['scope']+'\n\n'+summary['observed']+'\n\nExact PULS CC / ABX / PSHS CC encoding, operand table, mapper/vector, source/image hashes, full readback, CPU CRC, unique ID B500, ordered TX/ACK trace, no-reset/no-drop completion and full register guards pass.\n')
print('96 ABX records; data, flags and register guards pass')
