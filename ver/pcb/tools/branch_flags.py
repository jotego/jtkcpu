#!/usr/bin/env python3
"""Branch outcomes and immediate CC capture over all initial flag states."""
import argparse,hashlib,json,subprocess
import packed_unary as packed
from instruction_timing import inventory,branch_taken
framed=packed.framed
BASE=framed.timing.ROOT/'artifacts/branch-flags'
OPS=[r for r in inventory() if 0x60<=r['opcode']<=0x7f]

def cases():
    rows=[dict(opcode=r['opcode'],mnemonic=r['mnemonic'],input_D=0x1234,cc=cc,taken=branch_taken(r['opcode'],cc)) for r in OPS for cc in range(256)]
    rows += [dict(opcode=r['opcode'],mnemonic=r['mnemonic'],input_D=0xffff,cc=cc,taken=branch_taken(r['opcode'],cc)) for r in OPS for cc in (0,255)]
    assert len(rows)==8256
    return rows

def configure(batch):
    root=BASE/f'batch-{batch:02d}';packed.ROOT=root;framed.ROOT=root
    return root,cases()[batch*192:(batch+1)*192],0xad00+batch

def build(batch):
    root,rows,run_id=configure(batch);packed.generate('clearcom','boundary',0)
    source=(root/'probe.asm').read_text().replace('LDD #$A200',f'LDD #${run_id:04X}')
    first=source.index('        LDB $2E62\n');last=source.index('; CC and D are already captured',first)
    body='        LDB $2E62\n'
    for r in OPS:body+=f"        CMPB #${r['opcode']:02X}\n        LBEQ TEST_{r['opcode']:02X}\n"
    body+='        JMP RAM_FAIL\n'
    for r in OPS:
        op=r['opcode'];body+=f'''TEST_{op:02X}:
        LDX #$2F00
        LDY #$2F10
        LDU #$2F20
        LDD $2E60
        PULS CC
        {r['mnemonic']} TAKEN_{op:02X}
        PSHS CC
        JMP CAPTURE_NOT
TAKEN_{op:02X}:
        PSHS CC
        JMP CAPTURE_TAKEN
'''
    for label,marker in [('CAPTURE_NOT',0xe6),('CAPTURE_TAKEN',0xe7)]:
        body+=f'''{label}:
        STD $2E64
        PULS A
        STA $2E66
        LDA #${marker:02X}
        STA $2E67
        JMP CHECK_REGS
'''
    body+='CHECK_REGS:\n';source=source[:first]+body+source[last:]
    assert source.count('        LDA #$E7\n        STA ,X+')==1
    source=source.replace('        LDA #$E7\n        STA ,X+','        LDA $2E67\n        STA ,X+')
    first=source.index('        ORG $9000');last=source.index('        ORG $FFF6',first)
    table='        ORG $9000\nOPERANDS:\n'+''.join(f"        FDB ${r['input_D']:04X},${r['opcode']:04X}\n        FCB ${r['cc']:02X}\n" for r in rows)
    source=source[:first]+table+source[last:];(root/'probe.asm').write_text(source)
    m=json.loads((root/'manifest.json').read_text());m.update(family='branch-flags',run_id=run_id,cases=rows,source_sha256=hashlib.sha256(source.encode()).hexdigest())
    (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    with (root/'assembly.log').open('w') as f:
        subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    framed.package();fixed=(root/'fixed.bin').read_bytes()
    expected=b''.join(r['input_D'].to_bytes(2,'big')+r['opcode'].to_bytes(2,'big')+bytes([r['cc']]) for r in rows)
    assert fixed[0x1000:0x1000+len(expected)]==expected
    for r in OPS:
        op=r['opcode'];offset=b'\x00\x06' if op&8 else b'\x06'
        pattern=b'\x0e\x01'+bytes([op])+offset+b'\x0c\x01'
        assert fixed.count(pattern)==1,(r,pattern.hex())
        pos=fixed.index(pattern)+2
        target=pos+1+len(offset)+6
        assert fixed[target:target+2]==b'\x0c\x01', 'taken path must immediately capture CC'
    assert bytes.fromhex('0a54ff500000') in fixed

def decode_record(b,r):
    assert len(b)==8
    assert b[:4]==r['input_D'].to_bytes(2,'big')+bytes([r['opcode'],r['cc']])
    assert b[4:6]==r['input_D'].to_bytes(2,'big')
    assert b[7]==0xe6+int(r['taken']),(r,b.hex())
    return dict(**r,output_D=int.from_bytes(b[4:6],'big'),output_CC=b[6],observed_taken=bool(b[7]&1))

def analyze(batch):
    root,expected,run_id=configure(batch);capture=json.loads((root/'capture.json').read_text())
    assert capture.get('validated') and capture['complete'] and len(capture['frames'])==96
    m=capture['manifest'];assert m['cases']==expected
    for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==m[key]
    rows=[];changed=[]
    for i,frame in enumerate(capture['frames']):
        packet=bytes.fromhex(frame['hex']);framed.check_frame(packet,240+i,False,run_id)
        for slot in range(2):
            r=expected[2*i+slot];b=packet[9+slot*8:17+slot*8]
            row=decode_record(b,r)
            if b[6]!=r['cc']:changed.append(2*i+slot)
            rows.append(row)
    (root/'results.json').write_text(json.dumps(dict(records=rows,changed_CC_indices=changed),indent=2)+'\n')
    print(batch,'192 outcomes/data records verified; CC changes',len(changed),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('batch',type=int,choices=range(43));a=p.parse_args()
    if a.action=='build':build(a.batch)
    elif a.action=='analyze':analyze(a.batch)
    else:
        root,rows,run_id=configure(a.batch);original=framed.check_frame;framed.check_frame=lambda data,seq:original(data,seq,False,run_id)
        a.name='capture';a.host_delay=0;a.reconnect=False;framed.collect(a)
