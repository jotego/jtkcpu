#!/usr/bin/env python3
"""Direct DAA/TSTD data and flag captures; preserve failed hypotheses."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/daa-tstd'
DAACC=[0,1,0x20,0x21,0xde,0xdf,0xfe,0xff]

def cases(name):
    if name=='DAA':
        pairs=[(a<<8|0xa5,cc) for a in range(256) for cc in DAACC]
        pairs += [(a<<8|b,cc) for a in (0,9,10,0x7f,0x80,0x99,0x9a,0xff) for b in (0,1,0x80,0xff) for cc in (0,0xff)]
    else:
        pairs=[(v,cc) for v in (0,1,0xff,0x100,0x3fff,0x4000,0x5555,0x7fff,0x8000,0x8001,0xff00,0xffff) for cc in (0,1,4,5,8,9,0x72,0xff)]
    return [dict(opcode=0xb1 if name=='DAA' else 0xca,mnemonic=name,input_D=d,cc=cc) for d,cc in pairs]

def configure(name,batch):
    framed.ROOT=BASE/name/f'batch-{batch:02d}'
    rows=cases(name)[batch*96:(batch+1)*96];assert len(rows)==96
    return framed.ROOT,rows,0xab00+(0x40 if name=='TSTD' else 0)+batch

def build(name,batch):
    root,rows,run_id=configure(name,batch);root.mkdir(parents=True,exist_ok=True)
    template=TEMPLATES / 'single_record.asm'
    source=template.read_text().replace('        LEAU -1,U\n        BNE WAIT_BLOCK','        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK')
    source=source.replace('        LDD #$A500',f'        LDD #${run_id:04X}').replace('        SEX\n',f'        {name}\n')
    first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
    table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['input_D']:04X},$0000\n        FCB ${r['cc']:02X}\n" for r in rows)
    source=source[:first]+table+source[last:];(root/'probe.asm').write_text(source)
    m=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest(),template_sha256=hashlib.sha256(template.read_bytes()).hexdigest())
    (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    with (root/'assembly.log').open('w') as f:
        subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    framed.package();fixed=(root/'fixed.bin').read_bytes()
    expected=b''.join(r['input_D'].to_bytes(2,'big')+b'\0\0'+bytes([r['cc']]) for r in rows)
    assert fixed[0x1000:0x1000+len(expected)]==expected
    assert fixed.count(bytes([0x0e,1,rows[0]['opcode'],0x0c,1]))==1
    assert bytes.fromhex('0a54ff500000') in fixed

def model(r):
    cc=r['cc'];d=r['input_D']
    if r['mnemonic']=='TSTD':return d,(cc&0xf1)|(8 if d&0x8000 else 0)|(4 if d==0 else 0)
    a=d>>8;lo=a&15;hi=a>>4
    correction=(6 if (cc&0x20 or lo>9) else 0)+(0x60 if (cc&1 or hi>9 or (hi>8 and lo>9)) else 0)
    adjusted=a+correction;value=adjusted&255
    return (value<<8)|(d&255),(cc&0xf0)|(8 if value&128 else 0)|(4 if value==0 else 0)|(1 if cc&1 or adjusted>255 else 0)

def analyze(name,batch):
    root,cases_expected,run_id=configure(name,batch);capture=json.loads((root/'capture.json').read_text())
    assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
    m=capture['manifest'];assert m['cases']==cases_expected
    for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==m[key]
    rows=[];data_bad=[];flag_bad=[]
    for i,(frame,r) in enumerate(zip(capture['frames'],cases_expected)):
        packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id)
        b=packet[9:25];assert b[:5]==r['input_D'].to_bytes(2,'big')+b'\0\0'+bytes([r['cc']])
        assert b[7:13]==bytes.fromhex('2f002f102f20') and b[14:]==b'\xbe\xef'
        actual=int.from_bytes(b[5:7],'big');assert actual&255==r['input_D']&255
        expected_d,expected_cc=model(r)
        if actual!=expected_d:data_bad.append(i)
        if b[13]!=expected_cc:flag_bad.append(i)
        rows.append(dict(**r,output_D=actual,output_CC=b[13]))
    result=dict(records=rows,candidate_data_mismatches=data_bad,candidate_flag_mismatches=flag_bad)
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(name,batch,'96 records; candidate data/flag mismatches',len(data_bad),len(flag_bad),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('name',choices=['DAA','TSTD']);p.add_argument('batch',type=int);a=p.parse_args()
    if a.action=='build':build(a.name,a.batch)
    elif a.action=='analyze':analyze(a.name,a.batch)
    else:
        root,rows,run_id=configure(a.name,a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
        a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
