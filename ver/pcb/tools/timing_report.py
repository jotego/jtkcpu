#!/usr/bin/env python3
"""Merge measured cases without treating one operand/addressing case as full coverage."""
from pcb_paths import MODULE
import csv,json,re
from pathlib import Path
from instruction_timing import OUT,inventory
inv=inventory()
rtl=(MODULE / 'hdl/jtkcpu.inc').read_text().split('localparam [7:0]')[1].split(';')[0]
rtl_codes={int(s,16) for s in re.findall(r"=\s*8'h([0-9a-fA-F]+)",rtl)}
# F0 BSWI is explicitly labelled JT-specific in jtkcpu.inc, not a known PCB opcode.
assert rtl_codes-{0xf0}=={r['opcode'] for r in inv}, 'RTL/disassembler opcode inventory mismatch'
results=[]
for p in sorted(OUT.rglob('batch-*/results.json')):
 data=json.loads(p.read_text())
 for row in data['results']:
  if row.get('measurement_role')=='baseline':continue
  results.append(dict(**row,batch=str(p.parent.relative_to(OUT)),image_sha256=data['manifest']['image_sha256']))
for row in inv:
 measured=[r for r in results if r['opcode']==row['opcode']]
 row['measured_timing_cases']=[dict(encoding=r['encoding'],input_clocks=r['input_clocks'],batch=r['batch'],taken=r.get('taken'),shift_count=r.get('shift_count'),operand=r.get('operand'),stack_mask=r.get('stack_mask'),dynamic_target=r.get('dynamic_target',False),dynamic_pc_target=r.get('dynamic_pc_target')) for r in measured]
 if measured:row['timing_status']='measured subset; full operand/addressing coverage pending'
vector_root=OUT.parent/'shift-vectors'
vectors=[]
for p in sorted(vector_root.rglob('batch-*/results.json')):
 for r in json.loads(p.read_text())['results']:
  if r['kind']=='shift':vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'arithmetic-vectors').rglob('results.json')):
 for r in json.loads(p.read_text())['results']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'framed-lmul').rglob('results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,opcode=0xb4,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'framed-div').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,opcode=0xb5,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'framed-unary').glob('*/batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for family in ('clearcom','incdec','sexall','right','lefttst'):
 for p in sorted((OUT.parent/'packed-unary'/family).glob('*/batch-*/results.json')):
  for r in json.loads(p.read_text())['records']:
   vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
sex_confirmation=OUT.parent/'sex-confirm/single/results.json'
if sex_confirmation.exists():
 for r in json.loads(sex_confirmation.read_text())['records']:
  vectors.append(dict(**r,evidence=str(sex_confirmation.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'rol-confirm').glob('*/*/batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'memory-unary').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'daa-tstd').glob('*/batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'daa-allcc').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'branch-flags').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'byte-binary').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'byte-binary-immediate').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for family in ('word-d','word-d-immediate','word-register','word-register-immediate'):
 for p in sorted((OUT.parent/family).glob('batch-*/results.json')):
  for r in json.loads(p.read_text())['records']:
   vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for family in ('word-stack-pointer','word-stack-pointer-immediate','u-stack-control'):
 for p in sorted((OUT.parent/family).glob('batch-*/results.json')):
  for r in json.loads(p.read_text())['records']:
   vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'store-flags').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'lea-flags').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'abx-flags').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'cc-logic').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'decrement-branch').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for family in ('control-flags','rti-flags'):
 for p in sorted((OUT.parent/family).glob('batch-*/results.json')):
  for r in json.loads(p.read_text())['records']:
   vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'setlines-flags').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'transfer-flags').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'stack-flags').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r,evidence=str(p.relative_to(OUT.parent))))
for p in sorted((OUT.parent/'transfer-confirmation').glob('batch-*/results.json')):
 for r in json.loads(p.read_text())['records']:
  vectors.append(dict(**r['input'],output=r['output'],evidence=str(p.relative_to(OUT.parent))))
for row in inv:
 observed=[r for r in vectors if r['opcode']==row['opcode']]
 row['observed_flag_cases']=len(observed)
 if observed:
  row['flags_status']='measured subset; general flag rules and full operand/CC coverage pending'
  row['flag_evidence']=sorted({r['evidence'] for r in observed})
for row in inv:
 if row['opcode'] in (0x3e,0x3f):
  row['encoding_caveat']='Physical postbytes from selectors0..5: both3E/3F exchange, selector4 accesses a DP-related word rather than S. Historical timing operand names follow the assembler; exact bytes remain authoritative. See transfer-flags/summary.json.'
(OUT/'inventory.json').write_text(json.dumps(inv,indent=2)+'\n')
with (OUT/'timings.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['opcode','mnemonic','mode','encoding','encoding_kind','branch_taken','shift_count','operand','stack_mask','input_CLK_periods','fitted_CLK_periods','max_fit_residual_us','batch','coverage'])
 for r in results:w.writerow([f"{r['opcode']:02X}",r['mnemonic'],r['mode'],r['encoding'],'prefix plus varying displacement16' if 'dynamic_pc_target' in r else 'prefix plus varying target16' if r.get('dynamic_target') else 'complete',r.get('taken',''),r.get('shift_count',''),r.get('operand',''),r.get('stack_mask',''),r['input_clocks'],r['fitted_input_clocks'],r['max_fit_residual_us'],r['batch'],r['coverage']])
covered=len({r['opcode'] for r in results})
lines=['# Physical 053248 timing measurements','',
       'Reference: user-confirmed 12 MHz CLK input. Counts are input-clock periods; no M6809 E/Q signal is assumed.', '',
       f'{len(results)} measured cases spanning {covered}/197 known primary opcodes. This is partial coverage: additional operands, addressing modes, control flow, variable-length operations and flags remain pending.','',
       'Method: fit repeated blocks against RP2040 marker timestamps: normally 0/128/256/512 repetitions; operand-controlled paired, indexed and PC-addressing cases use 0/64/128/256. Paired cases subtract a separately measured setup-only slope from the setup-plus-instruction slope. Return-frame preparation is outside timing windows; its stack pointer setup is constant inside each window. Each block size requires at least four samples. Captures reject restarts, missing events, drops, nonlinear fits and ambiguous integer counts. Raw binary hashes, captures and per-size statistics accompany each batch.','',
       'Coverage details: memory cases currently use extended work-RAM address 2F00. Branch timing cases use zero displacement and separately check a nonzero branch outcome. Counts may depend on conditions, operands, addressing and displacement; do not generalize a row beyond its recorded case.', '',
       'Uncertainty: fitted CLK values and residuals are in timings.csv and per-batch results.json. Integer counts use the user-confirmed 12 MHz reference and RP2040 timestamps, without direct input-clock capture. The 0.15 CLK rounding gate is an analysis criterion, not a bound on clock-reference accuracy.', '',
       'Inventory audit: RTL also defines F0 BSWI, explicitly labelled JT-specific. It is excluded from the known physical-opcode sweep.', '',
       'The timing harness performs a stackless work-RAM check before emitting its ready marker. Watchdog accesses are spaced between blocks; the external reset output is unused.','',
       '| Opcode | Instruction | Encoding | Case detail | CLK periods |','|---|---|---|---|---:|']
lines.insert(4, 'Transfer encoding caveat: historical EXG/TFR timing names follow the assembler. Physical tests of selectors0..5 show both primary bytes3E/3F exchange values and selector4 accesses a DP-related word rather than S. Timing rows measure the recorded bytes; see transfer-flags/summary.json and the module research notes for data/flag observations.')
for r in results:lines.append(f"| {r['opcode']:02X} | {r['mnemonic']} ({r['mode']}) | {r['encoding']}{'xxxx' if r.get('dynamic_target') or 'dynamic_pc_target' in r else ''} | {('taken' if r['taken'] else 'untaken') if 'taken' in r else r.get('operand',r.get('shift_count',('mask %02X'%r['stack_mask']) if 'stack_mask' in r else ''))} | {r['input_clocks']} |")
(OUT/'README.md').write_text('\n'.join(lines)+'\n')
print(f'{len(results)} measured cases; {covered}/197 primary opcodes have samples; inventory matches RTL and disassembler')
