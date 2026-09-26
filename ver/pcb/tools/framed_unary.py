#!/usr/bin/env python3
"""Physical NEG/ABS records, with CC restored inside each fixed-opcode leaf."""
import argparse
import hashlib
import json
import framed_lmul as template
import framed_probe as framed

BASE=framed.timing.ROOT/'artifacts/framed-unary'
ROOT=BASE
OPS=[(0x86,'NEGA','A'),(0x87,'NEGB','B'),(0xc4,'NEGD','D'),
     (0xcc,'ABSA','A'),(0xcd,'ABSB','B'),(0xce,'ABSD','D')]


def cases(dataset):
    rows=[]
    for opcode,name,reg in OPS:
        width=16 if reg=='D' else 8
        values=(0,1<<(width-1)) if dataset=='boundary' else (1,(1<<width)-1)
        for value in values:
            d=value if reg=='D' else ((value<<8)|0xa5 if reg=='A' else 0x5a00|value)
            rows.append(dict(opcode=opcode,mnemonic=name,reg=reg,width=width,value=value,input_D=d))
    return rows


def generate(page,dataset):
    operands=cases(dataset)
    template.ROOT=ROOT
    template.PAIRS=[(r['input_D'],r['opcode']) for r in operands]
    template.CC=list(range(page*8,page*8+8))
    template.generate()
    source=(ROOT/'probe.asm').read_text()
    start=source.index('        LDX ,Y\n')
    end=source.index('        STD $2E0E\n',start)
    dispatch='        LDB 3,Y\n'
    for opcode,name,reg in OPS:
        dispatch+=f'        CMPB #${opcode:02X}\n        LBEQ TEST_{opcode:02X}\n'
    dispatch+='        JMP RAM_FAIL\n'
    for opcode,name,reg in OPS:
        dispatch+=f'''TEST_{opcode:02X}:
        LDX #$2F00
        LDY #$2F10
        LDU #$2F20
        LDD $2E09
        PULS CC
        {name}
        PSHS CC
        JMP CAPTURE
'''
    dispatch+='CAPTURE:\n'
    source=source[:start]+dispatch+source[end:]
    image_id=(0xe100 if dataset=='boundary' else 0xe200)+page
    source=source.replace('LDD #$7B01',f'LDD #${image_id:04X}')
    (ROOT/'probe.asm').write_text(source)
    manifest=json.loads((ROOT/'manifest.json').read_text())
    manifest['cases']=[dict(**r,cc=cc) for r in operands for cc in template.CC]
    manifest.update(dataset='NEG/ABS '+dataset,run_id=image_id,
                    source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def analyze(name):
    capture=json.loads((ROOT/(name+'.json')).read_text())
    assert capture.get('validated') and capture['complete']
    manifest=capture['manifest'];rows=[]
    for frame,case in zip(capture['frames'],manifest['cases']):
        packet=bytes.fromhex(frame['hex'])
        framed.check_frame(packet,frame['sequence'],False,manifest['run_id'])
        b=packet[9:25]
        assert b[:5]==case['input_D'].to_bytes(2,'big')+case['opcode'].to_bytes(2,'big')+bytes([case['cc']])
        assert b[14:]==b'\xbe\xef'
        output={reg:int.from_bytes(b[pos:pos+2],'big') for reg,pos in [('D',5),('X',7),('Y',9),('U',11)]}
        output['CC']=b[13]
        width,value=case['width'],case['value']
        result=(-value if case['mnemonic'].startswith('NEG') or value&(1<<(width-1)) else value)&((1<<width)-1)
        expected_d=result if case['reg']=='D' else ((result<<8)|0xa5 if case['reg']=='A' else 0x5a00|result)
        assert output['D']==expected_d,(case,output)
        assert (output['X'],output['Y'],output['U'])==(0x2f00,0x2f10,0x2f20)
        rows.append(dict(**case,output=output))
    assert len(rows)==96
    (ROOT/'results.json').write_text(json.dumps(dict(records=rows,capture=name+'.json',
                    coverage='Six unary primaries, two operands each, eight initial CC values per batch'),indent=2)+'\n')
    print('PASS: 96 NEG/ABS records; data and untouched-register checks pass.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','collect','analyze'])
    parser.add_argument('--dataset',choices=['boundary','ordinary'],default='boundary')
    parser.add_argument('--cc-page',type=int,choices=range(32),required=True)
    parser.add_argument('--name',default='capture')
    args=parser.parse_args()
    ROOT=BASE/args.dataset/f'batch-{args.cc_page:02d}'
    framed.ROOT=ROOT
    if args.action=='generate':generate(args.cc_page,args.dataset)
    elif args.action=='package':framed.package()
    elif args.action=='analyze':analyze(args.name)
    else:
        image_id=json.loads((ROOT/'manifest.json').read_text())['run_id']
        original_check=framed.check_frame
        framed.check_frame=lambda data,seq:original_check(data,seq,False,image_id)
        args.host_delay=0
        args.reconnect=False
        framed.collect(args)
