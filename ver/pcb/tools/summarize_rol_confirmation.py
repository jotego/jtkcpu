#!/usr/bin/env python3
"""Require both independent ROL confirmation matrices before publishing."""
import json
from argparse import Namespace
from rol_confirmation import BASE,analyze
rows=[]
for reg in ('A','B'):
    subset=[]
    for dataset,count in [('boundary',1),('allbytes',6)]:
        for batch in range(count):
            args=Namespace(reg=reg,dataset=dataset,batch=batch)
            analyze(args)
            result=json.loads((BASE/reg/dataset/f'batch-{batch:02d}'/'results.json').read_text())
            records=result['records'];rows.extend(records)
            if dataset=='allbytes':subset.extend(records)
    assert len(subset)==576
    for cc in (0,5):
        assert {r['value'] for r in subset if r['cc']==cc}==set(range(256))
assert len(rows)==1344
summary=dict(records=len(rows),scope='For each ROLA/ROLB: 12 operands x 8 CC presets, all 256 byte values at CC00/05, and 32 additional byte values at CC0E/FF.',
             observed='ROL rotates through carry; N/V/E/F/H/I preserved, C=old bit7, Z preserved if incoming C=1, otherwise result-zero.',
             limitations='All byte operands covered at two CC values; initial-CC exhaustiveness remains limited to the earlier four-operand matrix.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# Direct ROL confirmation\n\n'+summary['observed']+'\n\n'+summary['scope']+'\n\n'+summary['limitations']+'\n\nAll 1,344 records match this model. These ROMs execute a fixed ROLA or ROLB with no opcode dispatch, using the earlier single-record full-register payload. X/Y/U are checked on the host. CPU CRC, full trace/ACK, image/source hashes, input echoes, data, no-reset/no-drop and completion gates pass. Failed result-N/Z candidate mismatches remain in each results.json.\n')
print(summary)
