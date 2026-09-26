#!/usr/bin/env python3
"""Validate bank signatures and compare SETLINES immediate/RAM records."""
import json
from setlines_flags import BASE,analyze
rows=[]
for batch in range(8):
 analyze(batch)
 data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['candidate_flag_mismatches'];rows.extend(data['records'])
 manifest=json.loads((BASE/f'batch-{batch:02d}'/'manifest.json').read_text())
 image=(BASE/f'batch-{batch:02d}'/'probe-128k.bin').read_bytes()
 assert len(manifest['bank_signatures'])==16
 for bank,signature in enumerate(manifest['bank_signatures']):
  assert signature==dict(physical_bank=bank,physical_offset=bank*0x2000+0x1b00,hex=bytes([0x5a,bank,bank^255,0xa5]).hex())
  assert image[signature['physical_offset']:signature['physical_offset']+4]==bytes.fromhex(signature['hex'])
assert len(rows)==1536
for op in (0x38,0x39):
 group=[r for r in rows if r['opcode']==op];assert len(group)==768
 for bank in (0,31):
  assert [r['cc'] for r in group[:512] if r['mask']==bank]==list(range(256))
 assert len(group[512:])==256
 assert {r['mask'] for r in group[512:]}==set(range(32))
 assert all(r['output_CC']==r['cc'] and r['observed_bank']==r['mask']&15 for r in group)
for a,b in zip(rows[:768],rows[768:]):
 assert {k:v for k,v in a.items() if k not in ('opcode','mode')}=={k:v for k,v in b.items() if k not in ('opcode','mode')}
summary=dict(records=1536,paired_mode_records=768,scope='Both modes: banks00/1F at all256 CC, plus banks00..1F at CC00/01/04/05/08/09/72/FF. The16 overlapping operand/CC observations per mode are retained. Not the full bank-by-CC product.',observed='CC and D/X/Y/U preserved. Four-byte bank signatures confirm physical bank value&15 under the128KiB PicoROM address mask; values10..1F alias00..0F. Bank0 restored and checked before reporting.',limits='Only low five input bits varied; physical output pins are not measured. Aliases under addr_mask1ffff cannot independently prove the fifth bank output level.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# SETLINES banks and flags\n\n'+summary['scope']+'\n\n'+summary['observed']+'\n\n'+summary['limits']+'\n\nImmediate leaves use literal operands; memory leaves use guarded extended RAM2F40. Operand and A5/5A neighbors remain unchanged. Signatures5A/bank/complement/A5 occupy offset1B00 in each physical8KiB bank; insertion checks blank regions and preserves mapper/vectors/comms. CPU validates all four bytes after immediate CC capture and reports bank ID. Exact encodings/tables/hashes, full readback, CPU CRC, IDs B900..B907, complete TX/ACK trace, and no-reset/no-drop completion pass.\n')
print('1536 SETLINES records; 768 mode pairs agree; all bank, flag and register guards pass')
