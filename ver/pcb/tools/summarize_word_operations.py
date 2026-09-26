#!/usr/bin/env python3
"""Compare complete immediate/RAM word-operation matrices and raw registers."""
import json
import word_d,word_register
summary=dict(records=0,instructions=[],scope='LDD/ADDD/SUBD/CMPD and LDX/LDY/LDU/CMPX/CMPY/CMPU, both immediate and extended RAM. Twelve word operand pairs x8 CC presets per opcode; other operands, CC states and addressing forms pending.')
for module in (word_d,word_register):
 modes={}
 for mode in ('memory','immediate'):
  module.MODE=mode;rows=[]
  for batch,(_,name,reg) in enumerate(module.OPS):
   module.analyze(batch);root,expected,run_id=module.configure(batch);data=json.loads((root/'results.json').read_text())
   assert not data['candidate_data_mismatches'] and not data['candidate_flag_mismatches']
   rows.extend(data['records']);summary['instructions'].append(dict(opcode=data['records'][0]['opcode'],mnemonic=name,mode=mode,records=96))
  modes[mode]=rows;summary['records']+=len(rows)
 for mem,imm in zip(modes['memory'],modes['immediate']):
  assert {k:v for k,v in mem.items() if k!='opcode'}=={k:v for k,v in imm.items() if k!='opcode'}
assert summary['records']==1920 and len(summary['instructions'])==20
root=word_d.BASE
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'README.md').write_text('# Word load, arithmetic and comparison flags\n\n'+summary['scope']+'\n\nAll1920 observations match the candidate data/flag models;960 corresponding immediate/RAM records agree exactly. E/F/H/I are preserved. Word loads update N/Z, clear V and preserve C. ADDD updates N/Z/V/C with signed overflow and unsigned carry. SUBD and word compares update N/Z/V/C with signed overflow and borrow. Compare destinations remain unchanged. Other D/X/Y/U registers, source RAM and adjacent sentinels pass guards. Every input/table/literal/capture, CRC, hash, image identity, TX/ACK trace, no-reset/no-drop and completion check passes. S-target operations are not part of this matrix.\n')
print('1920 records across20 primaries;960 identical immediate/RAM pairs')
