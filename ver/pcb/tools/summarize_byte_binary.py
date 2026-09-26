#!/usr/bin/env python3
"""Require both byte-binary addressing sweeps and compare their raw results."""
import json
import byte_binary as probe
summary={'modes':{},'records':0,'scope':'20 immediate plus20 extended-RAM primary opcodes; each12 operand pairs x8 CC presets (00,01,20,21,DE,DF,FE,FF). Other operands, CC states and addressing forms pending.'}
by_mode={}
for mode in ('memory','immediate'):
 probe.MODE=mode;allrows=[];instructions=[]
 for batch,(_,name,reg) in enumerate(probe.OPS):
  probe.analyze(batch);root,expected,run_id=probe.configure(batch)
  data=json.loads((root/'results.json').read_text());assert not data['candidate_data_mismatches'] and not data['candidate_flag_mismatches']
  assert len(data['records'])==96;allrows.extend(data['records'])
  instructions.append(dict(opcode=data['records'][0]['opcode'],mnemonic=name,records=96))
 assert len(allrows)==1920;summary['modes'][mode]=instructions;summary['records']+=len(allrows);by_mode[mode]=allrows
for left,right in zip(by_mode['memory'],by_mode['immediate']):
 for key in ('mnemonic','reg','lhs','rhs','cc','input_D','output_D','output_CC'):assert left[key]==right[key],(key,left,right)
summary['memory_immediate_records_compared']=1920
root=probe.BASE
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'README.md').write_text('# Byte arithmetic, logic, comparison and load flags\n\n'+summary['scope']+'\n\nAll3840 records match the sampled data/flag models. Every memory result exactly matches its immediate counterpart. ADD/ADC update H/N/Z/V/C, with ordinary carry and signed overflow; SUB/SBC/CMP preserve H and update N/Z/V/C, with borrow in C. Logic/BIT/load update N/Z, clear V, preserve H/C. E/F/I are preserved throughout. CMP/BIT preserve the tested accumulator; the other D byte and X/Y/U remain unchanged.\n\nThe CPU checks source RAM and both adjacent sentinels. Host checks echoed inputs, full register results, image/source hashes, CPU CRC, IDs, complete TX/ACK traces and no-reset/no-drop completion. Immediate operand selection is dispatched before restoring CC; fixed ROM leaves contain the literal operand and immediate PSHS CC capture.\n')
print('3840 verified records;1920 identical memory/immediate pairs')
