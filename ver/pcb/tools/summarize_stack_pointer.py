#!/usr/bin/env python3
"""Validate S operations and full-CC U-stack capture controls."""
import json
import word_stack_pointer as s
root=s.BASE;allrows=[];modes={}
for mode in ('memory','immediate'):
 s.MODE=mode;rows=[]
 for batch in range(2):
  s.analyze(batch);folder,expected,run_id=s.configure(batch);data=json.loads((folder/'results.json').read_text())
  assert not data['candidate_data_mismatches'] and not data['candidate_flag_mismatches'];rows.extend(data['records'])
 modes[mode]=rows;allrows.extend(rows)
for a,b in zip(modes['memory'],modes['immediate']):assert {k:v for k,v in a.items() if k!='opcode'}=={k:v for k,v in b.items() if k!='opcode'}
assert len(allrows)==384
import u_stack_control as control
controls=[]
for batch in range(8):
 control.probe.analyze(batch);data=json.loads((control.BASE/f'batch-{batch:02d}'/'results.json').read_text())
 assert not data['candidate_data_mismatches'] and not data['candidate_flag_mismatches'];controls.extend(data['records'])
assert len(controls)==768
for value in (0,0x8000,0xffff):assert [r['cc'] for r in controls if r['input_value']==value]==list(range(256))
summary=dict(S_operation_records=384,NOP_control_records=768,total=1152,scope='LDS/CMPS immediate and extended:12 word pairs x8 CC presets each; NOP with S0000/8000/FFFF xall256 CC states.',observed='LDS sets word N/Z, clears V, preserves E/F/H/I/C. CMPS preserves S, sets subtraction N/Z/V and borrow C, preserves E/F/H/I. NOP preserves all CC and D/X/Y/S; U returns to3FE0.')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'README.md').write_text('# S-register flags and U-stack control\n\n'+summary['scope']+'\n\n'+summary['observed']+'\n\nNo S-stack push/pull instruction appears in these probes. CC is pushed, restored and captured through U at3FE0. S is read back before resetting it to3FF0; D/X/Y are captured and U is checked after the CC pop. Source RAM and adjacent sentinels are checked unchanged. All literal/table/capture/hash, full-readback, CPU-CRC, identity, TX/ACK, no-drop/no-reset and completion gates pass. All192 corresponding LDS/CMPS immediate/RAM results agree.\n')
print(summary)
