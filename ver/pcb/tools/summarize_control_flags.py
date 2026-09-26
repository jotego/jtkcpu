#!/usr/bin/env python3
"""Validate all-CC transfer and RTI matrices from raw hashed captures."""
import json
import control_flags as control
import rti_flags as rti
all_rows=[]
for probe,count in [(control,20),(rti,4)]:
 rows=[]
 for batch in range(count):
  probe.analyze(batch)
  data=json.loads((probe.BASE/f'batch-{batch:02d}'/'results.json').read_text())
  assert not data['changed_CC_indices']
  rows.extend(data['records'])
 for opcode in sorted({r['opcode'] for r in rows}):
  group=[r for r in rows if r['opcode']==opcode]
  assert len(group)==768
  for d in (0,0x1234,0xffff):
   selected=[r for r in group if r['input_D']==d]
   assert [r['cc'] for r in selected]==list(range(256))
   assert all(r['output_D']==d and r['output_CC']==r['cc'] for r in selected)
 if probe is rti:
  assert sum(r['full_frame'] for r in rows)==384
  assert all(r['pre_CC']==r['cc']^255 for r in rows)
 summary=dict(records=len(rows),opcodes=sorted({r['opcode'] for r in rows}),initial_CC='All256 states at D0000/1234/FFFF',scope='Recorded forward ROM destinations, call return addresses and RAM stack layout. Other targets, addressing modes and stack locations remain pending.')
 if probe is rti:
  summary['observed']='RTI restores all frame CC bits; frame E selects3-byte(short)/12-byte(full) consumption despite opposite incoming E. Full frames restore D/X/Y/U from deliberately different seeds; short frames preserve them. DP frame byte is00 but DP restoration is not independently measured.'
 else:summary['observed']='JMP/JSR/BSR/LBSR/RTS preserve allCC and D/X/Y/U; calls push the exact next-opcode return address; S displacement is checked on every case.'
 (probe.BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 (probe.BASE/'README.md').write_text('# Control-transfer flags\n\n'+str(len(rows))+' physical records. '+summary['initial_CC']+'.\n\n'+summary['observed']+'\n\n'+summary['scope']+'\n\nCC is captured immediately at the executed destination. Source/image hashes, emitted target/return addresses, exact restore/target and destination-capture bytes, operand tables, mapper/vector, full readback, CPU CRC, image identity, complete TX/ACK trace, data/register/stack guards and no-drop/no-reset completion pass.\n')
 all_rows.extend(rows)
assert len(all_rows)==4608
print('4608 records across6 control primaries; full matrices and guards pass')
