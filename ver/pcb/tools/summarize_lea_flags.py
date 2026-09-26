#!/usr/bin/env python3
"""Validate all four LEA matrices from hashed raw captures."""
import json
from lea_flags import BASE,OPS,analyze,cases
records=[];instructions=[]
for batch,(_,name,reg) in enumerate(OPS):
 analyze(batch)
 data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['candidate_data_mismatches']
 assert not data['candidate_flag_mismatches']
 assert len(data['records'])==96
 assert [{k:r[k] for k in cases(batch)[0]} for r in data['records']]==cases(batch)
 records.extend(data['records'])
 instructions.append(dict(opcode=cases(batch)[0]['opcode'],mnemonic=name,records=96))
assert len(records)==384
summary=dict(records=384,instructions=instructions,
 scope='LEAX/LEAY/LEAU/LEAS, forced extended effective addresses 0000/0001/0002/3FFF/4000/5555/7FFF/8000/8001/AAAA/FFFE/FFFF, each at CC00/01/04/05/08/09/72/FF. Other addressing forms and initial CC values remain pending.',
 observed='Every destination equals the encoded effective address. LEAX/LEAY update only Z (effective address zero); LEAU/LEAS preserve every CC bit in the sample. D and untouched X/Y/U registers retain their seeds.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# LEA effective addresses and flags\n\n'+summary['scope']+'\n\n'+summary['observed']+'\n\nLEAS uses the validated U-stack capture path, records S before restoring it, and contains no S-stack push/pull. Addresses are not dereferenced by LEA. ASL initially shortened the three lowest addresses to direct-page encodings; forcing extended addressing fixed the local encoding check before upload. Every leaf has exact restore/target/capture bytes checked. All four images passed hash/table/mapper/vector checks, full readback, CPU CRC, unique image ID, complete ordered TX/ACK trace, and no-drop/no-reset completion.\n')
print('384 LEA records; data, flags and register guards pass')
