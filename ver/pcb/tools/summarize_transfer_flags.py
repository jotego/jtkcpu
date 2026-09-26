#!/usr/bin/env python3
"""Validate all known EXG/TFR pairs and full register readback."""
import json
from transfer_flags import BASE,CC,REGS,SEEDS,analyze,predicted
rows=[]
for batch in range(6):
 analyze(batch)
 data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['changed_CC_indices']
 assert not data['candidate_data_mismatches']
 rows.extend(data['records'])
assert len(rows)==576
for op in (0x3e,0x3f):
 for src in range(6):
  for dst in range(6):
   group=[r for r in rows if r['opcode']==op and r['src']==src and r['dst']==dst]
   assert [r['cc'] for r in group]==list(CC)
   assert all((r['output_registers'],r['output_DP'])==predicted(r) and r['output_CC']==r['cc'] for r in group)
summary=dict(records=576,assembler_registers=REGS,physical_selectors=['A low / B high','B low / A high','X','Y','DP word','U'],seeds=SEEDS,selector4_seed=0xa67b,cc_presets=list(CC),scope='All36 assembler-defined pairs for each opcode at eightCC presets and one fixed register-seed set. Other operands, CC values and selectors6/7 remain unmeasured. Assembler/disassembler selector4 label S disagrees with these observations.',observed='Both primary bytes3E/3F exchange the selected values for postbytes built from selectors0..5. Selector0 reads B:A; selector1 reads A:B. Writes to0/1 update only A/B respectively. Selector4 reads the seeded16-bit value and writes expose its high byte through DP stack capture; S stays unchanged. X/Y/U exchange full words. AllCC preserved.',capture='All cases use S-stack capture after physical observations established that selectors0..5 leave S unchanged. U may receive arbitrary words and is not used for capture. D is captured before popping CC into A; U/S readback occurs after the capture stack is restored.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# EXG and TFR\n\n'+summary['scope']+'\n\n'+summary['observed']+'\n\n'+summary['capture']+'\n\nSeeds A3C/B96/X2193/Y32C4/S3FF0/U3FE0 and selector4 wordA67B. Every leaf explicitly initializes selector4 using raw3E42 before loading the target seeds. Payload echoes opcode/postbyte/inputCC and returns A/B/X/Y/U/S, the DP stack byte and outputCC. All literal register-pair encodings, immediate restore/target/capture bytes, tables/hashes/mapper/vector, full readback, CPU CRC, IDs BD00..BD05, complete TX/ACK traces and no-drop/no-reset completion pass.\n')
print('576 records; 36 pairs per opcode; all data, flags and guards pass')
