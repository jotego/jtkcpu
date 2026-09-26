#!/usr/bin/env python3
"""Decode all NEG/ABS packets and infer per-bit behavior from all CC states."""
import hashlib
import json
from framed_unary import BASE,OPS,cases
from framed_probe import check_frame

observations={}
image_ids=set()
for dataset in ('boundary','ordinary'):
    for page in range(32):
        folder=BASE/dataset/f'batch-{page:02d}'
        capture=json.loads((folder/'capture.json').read_text())
        assert capture.get('validated') and capture['complete']
        manifest=capture['manifest']
        assert manifest['run_id'] not in image_ids
        image_ids.add(manifest['run_id'])
        for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
            assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==manifest[key]
        expected_cases=[dict(**r,cc=cc) for r in cases(dataset) for cc in range(page*8,page*8+8)]
        assert manifest['cases']==expected_cases and len(capture['frames'])==96
        for i,(record,case) in enumerate(zip(capture['frames'],expected_cases)):
            frame=bytes.fromhex(record['hex'])
            check_frame(frame,0xf0+i,False,manifest['run_id'])
            b=frame[9:25]
            assert b[:5]==case['input_D'].to_bytes(2,'big')+case['opcode'].to_bytes(2,'big')+bytes([case['cc']])
            assert b[14:]==b'\xbe\xef' and b[7:13]==bytes.fromhex('2f002f102f20')
            value,width=case['value'],case['width']
            result=(-value if case['mnemonic'].startswith('NEG') or value&(1<<(width-1)) else value)&((1<<width)-1)
            expected=result if case['reg']=='D' else ((result<<8)|0xa5 if case['reg']=='A' else 0x5a00|result)
            assert int.from_bytes(b[5:7],'big')==expected
            key=(case['opcode'],value)
            observations.setdefault(key,{})
            assert case['cc'] not in observations[key]
            observations[key][case['cc']]=dict(**case,output_D=expected,output_CC=b[13])

rows=[]
flag_names=['C','V','Z','N','I','H','F','E']
model_mismatches=[]
for (opcode,value),states in sorted(observations.items()):
    assert sorted(states)==list(range(256))
    seed=states[0]
    rules={}
    for bit,name in enumerate(flag_names):
        bits=[(states[cc]['output_CC']>>bit)&1 for cc in range(256)]
        inputs=[(cc>>bit)&1 for cc in range(256)]
        if all(v==0 for v in bits):rule='0'
        elif all(v==1 for v in bits):rule='1'
        elif bits==inputs:rule='preserved'
        elif bits==[1-v for v in inputs]:rule='inverted'
        else:rule='depends on other input CC bits'
        rules[name]=rule
    width=seed['width'];sign=1<<(width-1)
    result=(-value if seed['mnemonic'].startswith('NEG') or value&sign else value)&((1<<width)-1)
    carry=bool(value) if seed['mnemonic'].startswith('NEG') else bool(value&sign)
    flags=(8 if result&sign else 0)|(4 if result==0 else 0)|(2 if value==sign else 0)|int(carry)
    for cc,row in states.items():
        predicted=(cc&0xf0)|flags
        if row['output_CC']!=predicted:model_mismatches.append(dict(opcode=opcode,value=value,cc=cc,expected=predicted,observed=row['output_CC']))
    rows.append(dict(opcode=opcode,mnemonic=seed['mnemonic'],value=value,width=width,result=result,
                     flag_rules=rules,initial_cc_values=list(states)))
assert len(rows)==24 and len(image_ids)==64
summary=dict(records=6144,operand_cases=rows,candidate_model_mismatches=model_mismatches,
             scope='Four recorded values per opcode, all 256 initial CC states; additional operands remain unmeasured.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Physical NEG and ABS flags','',
       '6144 CRC-checked records: six primary opcodes × four operands × all 256 initial CC values. Raw frames, sequence/trace gates, image hashes, operand echoes, preserved registers and per-image packet IDs are checked.',
       '',summary['scope'],'',
       f'Candidate rule mismatches: {len(model_mismatches)}. Candidate: N/Z from result, V for the most-negative input; NEG C for nonzero input, ABS C for negative input; E/F/H/I preserved.',
       '', '| Instruction | Input | Result | C | V | Z | N | E/F/H/I |', '|---|---|---|---|---|---|---|---|']
for r in rows:
    f=r['flag_rules'];upper='/'.join(f[k] for k in ('E','F','H','I'))
    lines.append(f"| {r['mnemonic']} | {r['value']:0{r['width']//4}X} | {r['result']:0{r['width']//4}X} | {f['C']} | {f['V']} | {f['Z']} | {f['N']} | {upper} |")
(BASE/'README.md').write_text('\n'.join(lines)+'\n')
print(f'6144 complete NEG/ABS records; candidate flag model mismatches: {len(model_mismatches)}')
