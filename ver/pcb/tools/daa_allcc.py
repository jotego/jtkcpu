#!/usr/bin/env python3
"""Complete initial-CC confirmation for six DAA boundary operands."""
import argparse,json
import daa_tstd_probe as probe
BASE=probe.framed.timing.ROOT/'artifacts/daa-allcc'
VALUES=(0,0x0a,0x94,0x99,0x9a,0xff)
def cases(name='DAA'):
    assert name=='DAA'
    return [dict(opcode=0xb1,mnemonic='DAA',input_D=a<<8|0xa5,cc=cc) for a in VALUES for cc in range(256)]
def configure(name,batch):
    assert name=='DAA';probe.framed.ROOT=BASE/f'batch-{batch:02d}'
    return probe.framed.ROOT,cases()[batch*96:(batch+1)*96],0xac00+batch
probe.cases=cases;probe.configure=configure

def summary():
    rows=[];original_bad=[];bad=[]
    for batch in range(16):
        probe.analyze('DAA',batch)
        rows.extend(json.loads((BASE/f'batch-{batch:02d}'/'results.json').read_text())['records'])
    assert len(rows)==1536
    for value in VALUES:
        assert [r['cc'] for r in rows if r['input_D']>>8==value]==list(range(256))
    for i,r in enumerate(rows):
        d,oldcc=probe.model(r);assert r['output_D']==d
        if oldcc!=r['output_CC']:original_bad.append(i)
        a=r['input_D']>>8;cc=r['cc'];lo=a&15
        low=6 if cc&32 or lo>9 else 0;high=96 if cc&1 or a>0x99 else 0
        total=a+low+high;carry=(cc&1)^int(total>255)
        nz=(cc&12) if high else (8 if d&0x8000 else 0)|(4 if d>>8==0 else 0)
        observed=(cc&0xd0)|(32 if lo+low>15 else 0)|nz|carry
        if observed!=r['output_CC']:bad.append(i)
    result=dict(records=len(rows),operands=list(VALUES),CC='All256 initial states for each operand',observed_model_mismatches=bad,original_candidate_mismatches=original_bad,
        scope='Independent N/Z/H/C/E/F/I/V initial values at six selected A inputs; combined with earlier all-A/eight-CC sweep, not the full A-by-CC Cartesian product.')
    (BASE/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    assert not bad,bad[:10]
    (BASE/'README.md').write_text('# All-CC DAA confirmation\n\n1536 records: A=00,0A,94,99,9A,FF, each with all256 CC states, B=A5.\n\nThe measured correction/flag model matches every record, including independent N/Z presets. B/X/Y/U remain unchanged. Full source/image hashes, CRC, input echoes, trace/ACK, no-reset/no-drop and completion gates pass. Earlier failed RTL-like flag model mismatches are retained. This is full CC coverage for these six A values, not all256 A values at all256 CC values.\n')
    print('1536 records; observed model mismatches',len(bad),'original candidate',len(original_bad))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze','summary']);p.add_argument('batch',type=int,nargs='?',default=0,choices=range(16));a=p.parse_args()
    if a.action=='summary':summary()
    elif a.action=='build':probe.build('DAA',a.batch)
    elif a.action=='analyze':probe.analyze('DAA',a.batch)
    else:
        root,rows,run_id=configure('DAA',a.batch);original=probe.framed.check_frame;probe.framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
        a.name='capture';a.host_delay=0;a.reconnect=False;probe.framed.collect(a)
