#!/usr/bin/env python3
"""Audit all packed CLR/COM/SEX and INC/DEC initial-CC truth tables."""
import argparse
import hashlib
import json
from packed_unary import BASE,decode,operands

parser=argparse.ArgumentParser()
parser.add_argument('--family',choices=['clearcom','incdec'],required=True)
args=parser.parse_args()
root=BASE/args.family
observations={};ids=set()
for dataset in ('boundary','ordinary'):
    for page in range(16):
        folder=root/dataset/f'batch-{page:02d}'
        capture=json.loads((folder/'capture.json').read_text())
        manifest=capture['manifest']
        assert manifest['run_id'] not in ids
        ids.add(manifest['run_id'])
        for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
            assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==manifest[key]
        expected=[dict(**r,cc=cc) for r in operands(args.family,dataset) for cc in range(page*16,page*16+16)]
        assert manifest['cases']==expected
        for row in decode(capture):
            key=(row['opcode'],row['value'])
            observations.setdefault(key,{})
            assert row['cc'] not in observations[key]
            observations[key][row['cc']]=row
assert len(observations)==24 and len(ids)==32
tables=[];mismatches=[]
for key,states in sorted(observations.items()):
    assert sorted(states)==list(range(256))
    case=states[0];name=case['mnemonic'];width=case['width'];sign=1<<(width-1)
    result=case['output_D'] if case['reg']=='D' or name=='SEX' else (case['output_D']>>8 if case['reg']=='A' else case['output_D']&255)
    result_sign=0x8000 if name=='SEX' else sign
    nz=(8 if result&result_sign else 0)|(4 if result==0 else 0)
    rules={}
    for bit,label in enumerate(('C','V','Z','N','I','H','F','E')):
        actual=[(states[cc]['output_CC']>>bit)&1 for cc in range(256)]
        original=[(cc>>bit)&1 for cc in range(256)]
        rules[label]='0' if not any(actual) else '1' if all(actual) else 'preserved' if actual==original else 'other CC dependency'
    for cc,row in states.items():
        if name.startswith('CLR'):predicted=(cc&0xf0)|4
        elif name.startswith('COM'):predicted=(cc&0xf0)|nz|1
        elif name=='SEX':predicted=(cc&0xf1)|nz
        elif name.startswith('INC'):predicted=(cc&0xf1)|nz|(2 if case['value']==sign-1 else 0)
        elif name.startswith('DEC'):predicted=(cc&0xf1)|nz|(2 if case['value']==sign else 0)
        else:raise ValueError(name)
        if predicted!=row['output_CC']:mismatches.append(dict(opcode=case['opcode'],value=case['value'],cc=cc,predicted=predicted,observed=row['output_CC']))
    tables.append(dict(opcode=case['opcode'],mnemonic=name,width=width,value=case['value'],result=result,flag_rules=rules))
sex_alternative=[]
for (opcode,value),states in observations.items():
    if opcode!=0xb2:continue
    for cc,row in states.items():
        d=row['output_D']
        predicted=(cc&0xf1)|(8 if d&0x8000 else 0)|(4 if d>>8==0 else 0)
        if row['output_CC']!=predicted:sex_alternative.append(dict(value=value,cc=cc))
summary=dict(records=6144,operand_cases=tables,candidate_model_mismatches=mismatches,
             sex_generated_A_model_mismatches=sex_alternative,
             scope='Four recorded operand values per primary opcode, all 256 initial CC values. Other operands remain pending.')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=[f'# Physical {args.family} flag matrices','',
       '6144 records: six primary opcodes × four recorded operands × all 256 initial CC values. Two complete input/output records fit each CPU-generated CRC frame. Every input D/opcode/CC is echoed; output D/CC and an E7 guard are checked. The CPU checks unchanged X/Y/U after immediately capturing D/CC.',
       'Every capture passes CRC, image ID, ordered frame/trace/ACK agreement, no-drop/no-reboot and completion gates. Source/image hashes, full operand tables and the initial-CC matrices are verified.',
       '',summary['scope'], '',f'Candidate flag-model mismatches: {len(mismatches)}. The initial SEX candidate derives N/Z from full D. For SEX, the alternative deriving N/Z from the generated A byte has {len(sex_alternative)} mismatches; see ../../sex-confirm/README.md for independent confirmation and the full B sweep.', '',
       '| Instruction | Input | Result | C | V | Z | N | E/F/H/I |','|---|---|---|---|---|---|---|---|']
for r in tables:
    f=r['flag_rules'];upper='/'.join(f[k] for k in ('E','F','H','I'))
    lines.append(f"| {r['mnemonic']} | {r['value']:0{r['width']//4}X} | {r['result']:0{(16 if r['mnemonic']=='SEX' else r['width'])//4}X} | {f['C']} | {f['V']} | {f['Z']} | {f['N']} | {upper} |")
(root/'README.md').write_text('\n'.join(lines)+'\n')
print(f'{args.family}: 6144 verified records; candidate flag-model mismatches: {len(mismatches)}')
