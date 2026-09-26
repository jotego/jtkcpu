#!/usr/bin/env python3
"""Direct ROLA/B probes using the earlier single-record payload."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,subprocess
import framed_probe as framed
BASE=framed.timing.ROOT/'artifacts/rol-confirm'
VALUES=[0,1,2,0x3f,0x40,0x55,0x7f,0x80,0x81,0xaa,0xfe,0xff]
CC=[0,1,4,5,8,9,0x0e,0xff]

def cases(reg,dataset):
    pairs=[(v,c) for v in VALUES for c in CC] if dataset=='boundary' else [(v,c) for v in range(256) for c in (0,5)]+[(v,c) for v in range(32) for c in (0x0e,0xff)]
    return [dict(opcode=0xa0 if reg=='A' else 0xa1,mnemonic='ROL'+reg,reg=reg,value=v,input_D=(v<<8|0xa5) if reg=='A' else (0x5a00|v),cc=c) for v,c in pairs]

def setup(args):
    framed.ROOT=BASE/args.reg/args.dataset/f'batch-{args.batch:02d}'
    rows=cases(args.reg,args.dataset)[args.batch*96:(args.batch+1)*96]
    assert len(rows)==96
    run_id=0xa800+(0x40 if args.reg=='B' else 0)+(0x10 if args.dataset=='allbytes' else 0)+args.batch
    return framed.ROOT,rows,run_id

def build(args):
    root,rows,run_id=setup(args);root.mkdir(parents=True,exist_ok=True)
    template=TEMPLATES / 'single_record.asm'
    source=template.read_text()
    # Historical capture template predates the explicit timeout-counter test.
    source=source.replace('        LEAU -1,U\n        BNE WAIT_BLOCK', '        LEAU -1,U\n        CMPU #0\n        BNE WAIT_BLOCK')
    source=source.replace('        LDD #$A500',f'        LDD #${run_id:04X}')
    assert source.count('        SEX\n')==1
    source=source.replace('        SEX\n',f'        ROL{args.reg}\n')
    first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
    table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['input_D']:04X},$0000\n        FCB ${r['cc']:02X}\n" for r in rows)
    source=source[:first]+table+source[last:]
    (root/'probe.asm').write_text(source)
    manifest=dict(first=240,count=96,frame_size=27,run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest(),template_sha256=hashlib.sha256(template.read_bytes()).hexdigest(),dataset=args.dataset)
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with (root/'assembly.log').open('w') as log:
        subprocess.run(['asl','-cpu','052001','-L','probe.asm'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['p2bin','probe.p','fixed.bin','-r','$8000-$ffff','-k','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    framed.package()
    fixed=(root/'fixed.bin').read_bytes()
    expected=b''.join(r['input_D'].to_bytes(2,'big')+b'\0\0'+bytes([r['cc']]) for r in rows)
    assert fixed[0x1000:0x1000+len(expected)]==expected
    assert fixed.count(bytes([0x0e,1,rows[0]['opcode'],0x0c,1]))==1, 'restore/opcode/capture encoding'

def analyze(args):
    root,cases_expected,run_id=setup(args)
    capture=json.loads((root/'capture.json').read_text())
    assert capture.get('validated') and capture['complete']
    manifest=capture['manifest'];assert manifest['cases']==cases_expected
    for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==manifest[key]
    rows=[];bad=[];ordinary_bad=[]
    assert len(capture['frames'])==96
    for i,(frame,r) in enumerate(zip(capture['frames'],cases_expected)):
        packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id)
        b=packet[9:25];assert b[:5]==r['input_D'].to_bytes(2,'big')+b'\0\0'+bytes([r['cc']])
        value=((r['value']<<1)|(r['cc']&1))&255
        d=(value<<8|0xa5) if args.reg=='A' else (0x5a00|value)
        assert b[5:7]==d.to_bytes(2,'big') and b[7:13]==bytes.fromhex('2f002f102f20') and b[14:]==b'\xbe\xef'
        carry=r['value']>>7;cc=r['cc'];z=(cc&4) if cc&1 else (4 if value==0 else 0)
        model=(cc&0xfa)|z|carry
        ordinary=(cc&0xf2)|(8 if value&128 else 0)|(4 if value==0 else 0)|carry
        if model!=b[13]:bad.append(i)
        if ordinary!=b[13]:ordinary_bad.append(i)
        rows.append(dict(**r,output_D=d,output_CC=b[13]))
    result=dict(records=rows,rol_candidate_mismatches=bad,result_NZ_model_mismatches=ordinary_bad)
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(args.reg,args.dataset,args.batch,'candidate mismatches',len(bad),'ordinary NZ mismatches',len(ordinary_bad),flush=True)
    assert not bad

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('--reg',choices=['A','B'],required=True);p.add_argument('--dataset',choices=['boundary','allbytes'],required=True);p.add_argument('--batch',type=int,default=0)
    args=p.parse_args()
    if args.action=='build':build(args)
    elif args.action=='analyze':analyze(args)
    else:
        root,rows,run_id=setup(args);original=framed.check_frame
        framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
        args.name='capture';args.host_delay=0;args.reconnect=False
        framed.collect(args)
