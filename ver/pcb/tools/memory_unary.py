#!/usr/bin/env python3
"""Guarded extended-RAM unary flag probes, one fixed opcode per ROM."""
import argparse,hashlib,json,subprocess
import framed_probe as framed
from packed_unary import expected_d
BASE=framed.timing.ROOT/'artifacts/memory-unary'
OPS=[(0x82,'CLR',8),(0x85,'COM',8),(0x88,'NEG',8),(0x8b,'INC',8),(0x8e,'DEC',8),(0x92,'TST',8),
     (0x95,'LSR',8),(0x98,'ROR',8),(0x9b,'ASR',8),(0x9e,'ASL',8),(0xa2,'ROL',8),
     (0xa3,'LSRW',16),(0xa4,'RORW',16),(0xa5,'ASRW',16),(0xa6,'ASLW',16),(0xa7,'ROLW',16),
     (0xc3,'CLRW',16),(0xc5,'NEGW',16),(0xc7,'INCW',16),(0xc9,'DECW',16),(0xcb,'TSTW',16)]
CC=[0,1,4,5,8,9,0x72,0xff]
def cases(batch):
    op,name,width=OPS[batch];mask=(1<<width)-1;sign=1<<(width-1)
    values=[0,1,2,sign//2-1,sign//2,mask//3,sign-1,sign,sign+1,2*(mask//3),mask-1,mask]
    return [dict(opcode=op,mnemonic=name,width=width,reg='D',value=v,cc=c,mode='EXT',address=0x2f40) for v in values for c in CC]
def configure(batch):
    framed.ROOT=BASE/f'batch-{batch:02d}'
    return framed.ROOT,cases(batch),0xaa00+batch

def build(batch):
    root,rows,run_id=configure(batch);framed.generate();source=(root/'probe.asm').read_text()
    source=source.replace('LDD #$7B01',f'LDD #${run_id:04X}')
    first=source.index('        LDX #$2E09');last=source.index('; CRC-16/CCITT-FALSE',first)
    width=rows[0]['width'];op=rows[0]['opcode'];name=rows[0]['mnemonic']
    store='STD' if width==16 else 'STB'
    load='        LDD $2F40\n' if width==16 else '        CLRA\n        LDB $2F40\n'
    after=0x2f40+width//8
    instruction=f'        {name} $2F40\n' if name!='DEC' else '        FCB $8E,$07,$2F,$40\n'
    body='''        LDS #$3FF0
        LDD $2E42
        SUBD #$00F0
        LDA #5
        MUL
        LDY #OPERANDS
        LEAY D,Y
        LDD ,Y
        STD $2E09
        LDD 2,Y
        STD $2E0B
        LDA 4,Y
        STA $2E0D
        PSHS A
        LDA #$A5
        STA $2F3F
        LDA #$5A
'''+f'        STA ${after:04X}\n'+'''        LDD ,Y
'''+f'        {store} $2F40\n'+'''        LDX #$2F00
        LDY #$2F10
        LDU #$2F20
        LDD #$1234
        PULS CC
'''+instruction+'''        PSHS CC
        STD $2E0E
        STX $2E10
        STY $2E12
        STU $2E14
        PULS A
        STA $2E16
'''+load+'''        STD $2E17
        LDA $2F3F
        CMPA #$A5
        LBNE RAM_FAIL
'''+f'        LDA ${after:04X}\n'+'''        CMPA #$5A
        LBNE RAM_FAIL
'''
    source=source[:first]+body+source[last:]
    table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['value']:04X},$0000\n        FCB ${r['cc']:02X}\n" for r in rows)
    source=source.replace('        ORG $FFF6',table+'        ORG $FFF6')
    (root/'probe.asm').write_text(source)
    m=json.loads((root/'manifest.json').read_text());m.update(cases=rows,run_id=run_id,source_sha256=hashlib.sha256(source.encode()).hexdigest(),encoding=f'{op:02x}072f40',encoding_exception='DEC mnemonic collides with assembler directive; raw bytes from known inventory' if name=='DEC' else None)
    (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    with (root/'assembly.log').open('w') as f:
        subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    framed.package();fixed=(root/'fixed.bin').read_bytes()
    expected=b''.join(r['value'].to_bytes(2,'big')+b'\0\0'+bytes([r['cc']]) for r in rows)
    assert fixed[0x1000:0x1000+len(expected)]==expected
    assert fixed.count(bytes([0x0e,1,op,7,0x2f,0x40,0x0c,1]))==1
    assert bytes.fromhex('0a54ff500000') in fixed

def analyze(batch):
    root,cases_expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text())
    assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
    m=capture['manifest'];assert m['cases']==cases_expected
    for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==m[key]
    rows=[]
    for i,(frame,r) in enumerate(zip(capture['frames'],cases_expected)):
        packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id)
        b=packet[9:25];assert b[:5]==r['value'].to_bytes(2,'big')+b'\0\0'+bytes([r['cc']])
        assert b[5:13]==bytes.fromhex('12342f002f102f20'),'D/X/Y/U changed'
        result=int.from_bytes(b[14:16],'big');assert result==expected_d(r),(r,result)
        rows.append(dict(**r,output_value=result,output_CC=b[13]))
    result=dict(records=rows,scope='12 selected operands x 8 CC presets, extended work RAM 2F40; adjacent byte guards checked by CPU, D/X/Y/U checked on host.')
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS',OPS[batch][1],len(rows),'data/register/guard records; flags retained without prediction',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(len(OPS)));a=p.parse_args()
    if a.action=='build':build(a.batch)
    elif a.action=='analyze':analyze(a.batch)
    else:
        root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
        a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
