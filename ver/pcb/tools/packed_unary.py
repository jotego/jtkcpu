#!/usr/bin/env python3
"""Two echoed unary-operation records per acknowledged 16-byte payload."""
import argparse
import hashlib
import json
import framed_probe as framed

BASE=framed.timing.ROOT/'artifacts/packed-unary'
ROOT=BASE
FAMILIES={
 'negabs':[(0x86,'NEGA','A'),(0x87,'NEGB','B'),(0xc4,'NEGD','D'),(0xcc,'ABSA','A'),(0xcd,'ABSB','B'),(0xce,'ABSD','D')],
 'clearcom':[(0x80,'CLRA','A'),(0x81,'CLRB','B'),(0xc2,'CLRD','D'),(0x83,'COMA','A'),(0x84,'COMB','B'),(0xb2,'SEX','B')],
 'incdec':[(0x89,'INCA','A'),(0x8a,'INCB','B'),(0xc6,'INCD','D'),(0x8c,'DECA','A'),(0x8d,'DECB','B'),(0xc8,'DECD','D')],
 'sexall':[(0xb2,'SEX','B')],
 'right':[(0x93,'LSRA','A'),(0x94,'LSRB','B'),(0x96,'RORA','A'),(0x97,'RORB','B'),(0x99,'ASRA','A'),(0x9a,'ASRB','B')],
 'lefttst':[(0x9c,'ASLA','A'),(0x9d,'ASLB','B'),(0xa0,'ROLA','A'),(0xa1,'ROLB','B'),(0x90,'TSTA','A'),(0x91,'TSTB','B')],
}


def operands(family,dataset):
    rows=[]
    for opcode,name,reg in FAMILIES[family]:
        width=16 if reg=='D' else 8
        first=(1<<(width-1))-1 if name.startswith('INC') else 1
        values=(0,1<<(width-1)) if dataset=='boundary' else (first,(1<<width)-1)
        for value in values:
            d=value if reg=='D' else (value<<8|0xa5 if reg=='A' else 0x5a00|value)
            rows.append(dict(opcode=opcode,mnemonic=name,reg=reg,width=width,value=value,input_D=d))
    return rows


def expected_d(case):
    value,width,name=case['value'],case['width'],case['mnemonic']
    mask=(1<<width)-1
    if name=='SEX':return value|0xff00 if value&0x80 else value
    if name.startswith('NEG'):result=-value&mask
    elif name.startswith('ABS'):result=(-value if value&(1<<(width-1)) else value)&mask
    elif name.startswith('CLR'):result=0
    elif name.startswith('COM'):result=value^mask
    elif name.startswith('INC'):result=(value+1)&mask
    elif name.startswith('DEC'):result=(value-1)&mask
    elif name.startswith('LSR'):result=value>>1
    elif name.startswith('ASR'):result=(value>>1)|(value&(1<<(width-1)))
    elif name.startswith('ROR'):result=(value>>1)|((case['cc']&1)<<(width-1))
    elif name.startswith('ASL'):result=(value<<1)&mask
    elif name.startswith('ROL'):result=((value<<1)|(case['cc']&1))&mask
    elif name.startswith('TST'):result=value
    else:raise ValueError(name)
    return result if case['reg']=='D' else (result<<8|0xa5 if case['reg']=='A' else 0x5a00|result)


def sex_cases():
    inputs=[(0x5a,b,cc) for b in range(256) for cc in (0,255)]
    inputs += [(a,b,cc) for b in (0,1,2,0x7f,0x80,0x81,0xfe,0xff)
               for a in (0,0x7f,0x80,0xff) for cc in (0,255)]
    return [dict(opcode=0xb2,mnemonic='SEX',reg='B',width=8,value=b,input_D=a<<8|b,cc=cc)
            for a,b,cc in inputs]


def generate(family,dataset,page):
    framed.ROOT=ROOT
    framed.generate()
    source=(ROOT/'probe.asm').read_text()
    first=source.index('        LDX #$2E09')
    last=source.index('; CRC-16/CCITT-FALSE',first)
    body='''        LDS #$3FF0
        LDD $2E42
        SUBD #$00F0
        ASLB
        ROLA
        STD $2E46
        LDA #2
        STA $2E48
        LDX #$2E09
        STX $2E49
NEXT_CASE:
        LDD $2E46
        LDA #5
        MUL
        LDY #OPERANDS
        LEAY D,Y
        LDD ,Y
        STD $2E60
        LDA 3,Y
        STA $2E62
        LDA 4,Y
        STA $2E63
        PSHS A
        LDB $2E62
'''
    for opcode,name,reg in FAMILIES[family]:
        body+=f'        CMPB #${opcode:02X}\n        LBEQ TEST_{opcode:02X}\n'
    body+='        JMP RAM_FAIL\n'
    for opcode,name,reg in FAMILIES[family]:
        body+=f'''TEST_{opcode:02X}:
        LDX #$2F00
        LDY #$2F10
        LDU #$2F20
        LDD $2E60
        PULS CC
        {name}
        PSHS CC
        JMP CAPTURE
'''
    body+='''CAPTURE:
        STD $2E64
        PULS A
        STA $2E66
; CC and D are already captured before checking untouched registers.
        CMPX #$2F00
        LBNE RAM_FAIL
        CMPY #$2F10
        LBNE RAM_FAIL
        CMPU #$2F20
        LBNE RAM_FAIL
; Eight-byte record: input D, opcode, input CC, output D, output CC, E7.
        LDX $2E49
        LDD $2E60
        STD ,X++
        LDA $2E62
        STA ,X+
        LDA $2E63
        STA ,X+
        LDD $2E64
        STD ,X++
        LDA $2E66
        STA ,X+
        LDA #$E7
        STA ,X+
        STX $2E49
        LDD $2E46
        ADDD #1
        STD $2E46
        LDA $2E48
        DECA
        STA $2E48
        LBNE NEXT_CASE
'''
    source=source[:first]+body+source[last:]
    if family=='sexall':
        assert dataset=='boundary' and 0<=page<3
        cases=sex_cases()[page*192:(page+1)*192]
    else:
        cases=[dict(**case,cc=cc) for case in operands(family,dataset) for cc in range(page*16,page*16+16)]
    assert len(cases)==192
    image_id={'negabs':0xa100,'clearcom':0xa200,'incdec':0xa300,'sexall':0xa400,'right':0xa600,'lefttst':0xa700}[family]+(0x40 if dataset=='ordinary' else 0)+page
    source=source.replace('LDD #$7B01',f'LDD #${image_id:04X}')
    table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['input_D']:04X},${r['opcode']:04X}\n        FCB ${r['cc']:02X}\n" for r in cases)
    source=source.replace('        ORG $FFF6',table+'        ORG $FFF6')
    (ROOT/'probe.asm').write_text(source)
    manifest=json.loads((ROOT/'manifest.json').read_text())
    manifest.update(cases=cases,records_per_frame=2,dataset=dataset,family=family,run_id=image_id,
                    source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def decode(capture):
    assert capture.get('validated') and capture['complete']
    manifest=capture['manifest'];rows=[]
    assert len(capture['frames'])==96 and len(manifest['cases'])==192
    for frame_index,frame in enumerate(capture['frames']):
        packet=bytes.fromhex(frame['hex'])
        framed.check_frame(packet,0xf0+frame_index,False,manifest['run_id'])
        for slot in range(2):
            b=packet[9+slot*8:17+slot*8]
            case=manifest['cases'][frame_index*2+slot]
            assert b[:4]==case['input_D'].to_bytes(2,'big')+bytes([case['opcode'],case['cc']])
            assert b[7]==0xe7
            d=int.from_bytes(b[4:6],'big')
            assert d==expected_d(case),(case,d)
            rows.append(dict(**case,output_D=d,output_CC=b[6]))
    return rows


def analyze(name):
    capture=json.loads((ROOT/(name+'.json')).read_text())
    rows=decode(capture)
    if capture['manifest']['family']=='negabs':
        dataset=capture['manifest']['dataset'];old={}
        for file in (framed.timing.ROOT/'artifacts/framed-unary'/dataset).glob('batch-*/results.json'):
            for r in json.loads(file.read_text())['records']:old[(r['opcode'],r['value'],r['cc'])]=r
        for r in rows:
            prev=old[(r['opcode'],r['value'],r['cc'])]
            assert (r['output_D'],r['output_CC'])==(prev['output']['D'],prev['output']['CC'])
    result=dict(records=rows,capture=name+'.json',register_guards='X/Y/U checked by CPU after immediate CC/D capture',
                coverage='Recorded operands and CC states; no timing inference from report throughput')
    (ROOT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"PASS: {len(rows)} packed {capture['manifest']['family']} records; all input echoes and data match.")


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['generate','package','collect','analyze'])
    parser.add_argument('--family',choices=FAMILIES,required=True)
    parser.add_argument('--dataset',choices=['boundary','ordinary'],default='boundary')
    parser.add_argument('--cc-page',type=int,choices=range(16),required=True)
    parser.add_argument('--name',default='capture')
    parser.add_argument('--host-delay',type=float,default=0)
    parser.add_argument('--reconnect',action='store_true')
    args=parser.parse_args()
    ROOT=BASE/args.family/args.dataset/f'batch-{args.cc_page:02d}'
    framed.ROOT=ROOT
    if args.action=='generate':generate(args.family,args.dataset,args.cc_page)
    elif args.action=='package':framed.package()
    elif args.action=='analyze':analyze(args.name)
    else:
        image_id=json.loads((ROOT/'manifest.json').read_text())['run_id']
        original_check=framed.check_frame
        framed.check_frame=lambda data,seq:original_check(data,seq,False,image_id)
        framed.collect(args)
