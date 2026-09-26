#!/usr/bin/env python3
"""Classify observed memory-unary flags without assuming register semantics."""
import json
from memory_unary import BASE,OPS,analyze

def standard(r):
    name,v,width,cc,out=r['mnemonic'],r['value'],r['width'],r['cc'],r['output_value']
    sign=1<<(width-1);mask=(1<<width)-1
    n=bool(out&sign);z=out==0;c=cc&1;overflow=bool(cc&2)
    if name.startswith('CLR'):n=False;z=True;c=0;overflow=False
    elif name=='COM':c=1;overflow=False
    elif name.startswith('NEG'):c=v!=0;overflow=v==sign
    elif name.startswith('INC'):overflow=v==sign-1
    elif name.startswith('DEC'):overflow=v==sign
    elif name.startswith('TST'):overflow=False
    elif name.startswith(('LSR','ASR','ROR')):c=v&1
    elif name.startswith(('ASL','ROL')):
        c=bool(v&sign)
        if name.startswith('ASL'):overflow=n^c
    return (cc&0xf0)|(int(n)<<3)|(int(z)<<2)|(int(overflow)<<1)|int(c)

def models(r,bit):
    sign=1<<(r['width']-1);v=r['value'];out=r['output_value'];cc=r['cc']
    return {'preserved':bool(cc&(1<<bit)),'zero':False,'one':True,
     'result_sign':bool(out&sign),'result_zero':out==0,'input_sign':bool(v&sign),
     'input_bit0':bool(v&1),'input_nonzero':v!=0,'input_min_negative':v==sign,
     'input_max_positive':v==sign-1,'sign_changed':bool((v^out)&sign),
     'Z_preserved_if_C1_else_result_zero':bool(cc&4) if cc&1 else out==0}

summaries=[];all_rows=[]
for batch,(op,name,width) in enumerate(OPS):
    analyze(batch)
    data=json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text());rows=data['records'];all_rows.extend(rows)
    assert len({r['value'] for r in rows})==12
    for value in {r['value'] for r in rows}:assert len([r for r in rows if r['value']==value])==8
    matches={}
    for bit,label in enumerate('CVZNIHFE'):
        keys=models(rows[0],bit).keys()
        matches[label]=[key for key in keys if all(models(r,bit)[key]==bool(r['output_CC']&(1<<bit)) for r in rows)]
    bad=[i for i,r in enumerate(rows) if standard(r)!=r['output_CC']]
    alternative_bad=[]
    for i,r in enumerate(rows):
        expected=standard(r)
        if name=='ROL':
            z=(r['cc']&4) if r['cc']&1 else (4 if r['output_value']==0 else 0)
            expected=(r['cc']&0xfa)|z|(r['value']>>7)
        elif name=='ROLW':
            expected=(expected&~2)|(2 if (r['value']^r['output_value'])&0x8000 else 0)
        if expected!=r['output_CC']:alternative_bad.append(i)
    assert not alternative_bad,(name,alternative_bad)

    summaries.append(dict(opcode=op,mnemonic=name,width=width,records=len(rows),flag_candidates=matches,register_like_candidate_mismatches=bad,observed_model_mismatches=alternative_bad))
    print(name,'standard mismatches',len(bad),{k:matches[k] for k in 'NZVC'})
assert len(all_rows)==2016
summary=dict(records=len(all_rows),instructions=summaries,scope='21 opcodes x 12 selected operands x 8 CC presets (00,01,04,05,08,09,72,FF), extended RAM 2F40. Other initial CC states, operands and addressing modes pending.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Extended-RAM unary flag observations','',summary['scope'],'','All data/register/neighbor-guard, CRC, image identity, hash, trace/ACK/no-drop/no-reboot and completion gates pass. Per-bit candidate lists are observational matches over this sample, not exhaustive rules. The register-like candidate assumes result N/Z; failed hypotheses are retained.','','| Operation | Register-like model mismatches | N candidates | Z candidates | V candidates | C candidates |','|---|---:|---|---|---|---|']
for r in summaries:lines.append('| '+r['mnemonic']+' | '+str(len(r['register_like_candidate_mismatches']))+' | '+' | '.join(', '.join(r['flag_candidates'][f]) for f in 'NZVC')+' |')
(BASE/'README.md').write_text('\n'.join(lines)+'\n')
