#!/usr/bin/env python3
"""Verify full DAA input classes and preserve alternative flag hypotheses."""
import json
from daa_tstd_probe import BASE,DAACC,cases,analyze,model
allrows=[];summaries={}
for name,count in [('DAA',22),('TSTD',1)]:
    rows=[];old_bad=[];new_bad=[];incoming_c_nz_bad=[];outgoing_c_nz_bad=[]
    for batch in range(count):
        analyze(name,batch)
        rows.extend(json.loads((BASE/name/f'batch-{batch:02d}'/'results.json').read_text())['records'])
    assert [{k:r[k] for k in ('opcode','mnemonic','input_D','cc')} for r in rows]==cases(name)
    for i,r in enumerate(rows):
        d,cc=model(r);assert r['output_D']==d
        if cc!=r['output_CC']:old_bad.append(i)
        if name=='DAA':
            a=r['input_D']>>8;cin=r['cc'];lo=a&15
            low_correction=6 if cin&32 or lo>9 else 0
            high_correction=96 if cin&1 or a>0x99 else 0
            total=a+low_correction+high_correction
            half=lo+low_correction>15
            carry=(cin&1)^int(total>255)
            result_nz=(8 if d&0x8000 else 0)|(4 if d>>8==0 else 0)
            fixed=(cin&0xd0)|(32 if half else 0)|carry
            if (fixed|((cin&12) if cin&1 else result_nz))!=r['output_CC']:incoming_c_nz_bad.append(i)
            if (fixed|((cin&12) if carry else result_nz))!=r['output_CC']:outgoing_c_nz_bad.append(i)
            cc=fixed|((cin&12) if high_correction else result_nz)
        if cc!=r['output_CC']:new_bad.append(i)
    assert not new_bad,(name,new_bad[:10])
    if name=='DAA':
        for cc in DAACC:
            assert {r['input_D']>>8 for r in rows[:2048] if r['cc']==cc}==set(range(256))
    summaries[name]=dict(records=len(rows),original_candidate_mismatches=old_bad,observed_model_mismatches=new_bad,incoming_C_NZ_hypothesis_mismatches=incoming_c_nz_bad,outgoing_C_NZ_hypothesis_mismatches=outgoing_c_nz_bad)
    allrows.extend(rows)
summary=dict(instructions=summaries,records=len(allrows),scope='DAA: all 256 A values x CC00/01/20/21/DE/DF/FE/FF with B=A5, plus64 B-variation cases. TSTD:12 word values x8 CC presets.',
 observed='DAA data follows conditional +06/+60 correction; C is input C XOR correction carry-out, H is low-nibble correction carry-out, V=0, N/Z preserved if the +60 correction applies (input C=1 or original A>99), otherwise adjusted-result N/Z; E/F/I preserved. TSTD N/Z full D, V=0, E/F/H/I/C preserved.')
(BASE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(BASE/'README.md').write_text('# DAA and TSTD physical observations\n\n'+summary['scope']+'\n\n'+summary['observed']+'\n\nAll 2,208 records pass data/register guards, source/image hashes, CPU CRC, image identity, full TX/ACK traces, completion and no-reset/no-drop gates. The initial DAA model preserved H and always updated N/Z; its mismatch indices remain in summary.json. All initial CC values and operand-dependent timing are separate coverage dimensions.\n')
print({name:{k:len(v) if isinstance(v,list) else v for k,v in r.items()} for name,r in summaries.items()})
