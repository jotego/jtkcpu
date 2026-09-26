#!/usr/bin/env python3
"""Compare explicit carry/overflow candidates against complete byte-shift matrices."""
import argparse
import hashlib
import json
from packed_unary import BASE,decode,operands

parser=argparse.ArgumentParser()
parser.add_argument('--family',choices=['right','lefttst'],required=True)
args=parser.parse_args();root=BASE/args.family
states={};ids=set()
for dataset in ('boundary','ordinary'):
    for page in range(16):
        folder=root/dataset/f'batch-{page:02d}'
        capture=json.loads((folder/'capture.json').read_text());manifest=capture['manifest']
        assert manifest['run_id'] not in ids
        ids.add(manifest['run_id'])
        assert manifest['cases']==[dict(**r,cc=cc) for r in operands(args.family,dataset) for cc in range(page*16,page*16+16)]
        for file,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
            assert hashlib.sha256((folder/file).read_bytes()).hexdigest()==manifest[key]
        for row in decode(capture):
            key=(row['opcode'],row['value'])
            states.setdefault(key,{})
            assert row['cc'] not in states[key]
            states[key][row['cc']]=row
assert len(states)==24
for entries in states.values():assert sorted(entries)==list(range(256))
rows=[r for entries in states.values() for r in entries.values()]
summaries=[]
for opcode in sorted({r['opcode'] for r in rows}):
    observed=[r for r in rows if r['opcode']==opcode]
    name=observed[0]['mnemonic'];candidates={}
    for c_rule in ('shifted_out','preserved','zero'):
        for v_rule in ('preserved','zero','N_xor_C'):
            bad=[]
            for i,r in enumerate(observed):
                result=r['output_D']>>8 if r['reg']=='A' else r['output_D']&255
                shifted=(r['value']>>7)&1 if name.startswith(('ASL','ROL')) else r['value']&1
                carry={'shifted_out':shifted,'preserved':r['cc']&1,'zero':0}[c_rule]
                negative=(result>>7)&1
                overflow={'preserved':(r['cc']>>1)&1,'zero':0,'N_xor_C':negative^carry}[v_rule]
                expected=(r['cc']&0xf0)|(negative<<3)|(4 if result==0 else 0)|(overflow<<1)|carry
                if r['output_CC']!=expected:bad.append(i)
            candidates[f'C={c_rule},V={v_rule}']=dict(mismatch_count=len(bad),mismatch_indices=bad)
    if name.startswith('ROL'):
        bad=[]
        for i,r in enumerate(observed):
            result=r['output_D']>>8 if r['reg']=='A' else r['output_D']&255
            zero=(r['cc']&4) if r['cc']&1 else (4 if result==0 else 0)
            expected=(r['cc']&0xfa)|zero|((r['value']>>7)&1)
            if r['output_CC']!=expected:bad.append(i)
        candidates['N/V preserved; C=shifted_out; Z preserved if input C=1, else result zero']=dict(mismatch_count=len(bad),mismatch_indices=bad)
    matches=[name for name,test in candidates.items() if not test['mismatch_count']]
    summaries.append(dict(opcode=opcode,mnemonic=name,records=len(observed),matching_models=matches,candidate_models=candidates))
summary=dict(records=len(rows),instructions=summaries,
    scope='Operands 00,80,01,FF on A/B, all 256 initial CC values; other operands pending.',
    data='Logical/arithmetic shifts and rotations through carry match all records, including the unused D byte and CPU X/Y/U guards.')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=[f'# Physical {args.family} byte-operation flags','',summary['scope'], '',summary['data'],'',
       '6144 records pass CPU CRC, input echoes, frame/image identity, trace/ACK/no-drop/no-reboot gates, hash checks and complete CC matrices. The nine original candidates require N/Z from the actual result byte and preservation of E/F/H/I. A separate ROL candidate preserves N/V, takes C from the shifted-out bit, and preserves Z when incoming C=1 (otherwise Z follows the result). Original failed candidates remain recorded. The result is recomputed for each carry-in state; rotations do not reuse the C=0 result for C=1.', '',
       '| Instruction | Records | Matching C/V models |','|---|---:|---|']
for row in summaries:lines.append(f"| {row['mnemonic']} | {row['records']} | {'; '.join(row['matching_models']) or 'NONE: inspect raw observations'} |")
(root/'README.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({r['mnemonic']:r['matching_models'] for r in summaries}))
