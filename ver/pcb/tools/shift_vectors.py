#!/usr/bin/env python3
"""Capture single-operation shift results and CC, with baseline capture checks."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json
from pathlib import Path
import instruction_timing as timing
ROOT=timing.ROOT/'artifacts/shift-vectors'
DATASET='initial'

def cases():
    if DATASET=='boundary':
        timing.FAMILY='shift';rows=[]
        for r in timing.cases():
            if r['shift_count'] not in (0,1,2,7,15,16):continue
            for value in (0,0x8001,0xffff):
                for cc in (0x50,0x7f):
                    rows.append(dict(id=len(rows),kind='shift',cc=cc,input_d=value,
                        **{k:r[k] for k in ('opcode','encoding','mode','shift_count','mnemonic')}))
        return rows
    rows=[dict(id=i,kind='baseline',cc=i,encoding='',input_d=0x1234) for i in range(256)]
    timing.FAMILY='shift'
    for r in timing.cases():
        rows.append(dict(id=len(rows),kind='shift',cc=0x50,input_d=0x1234,**{k:r[k] for k in ('opcode','encoding','mode','shift_count','mnemonic')}))
    return rows

def generate(batch):
    rows=cases()[batch*64:(batch+1)*64]
    assert rows
    p=ROOT/f'batch-{batch:02d}';p.mkdir(parents=True,exist_ok=True)
    prefix=(TEMPLATES / 'bootstrap.asm').read_text().split('        LDA $DF10')[0]
    parts=[prefix,timing.RAM]
    for r in rows:
        i=r['id']
        parts.append(f'        LDX #$FFFF\nD{i}:\n        LEAX -1,X\n        BNE D{i}\n        TST $5FEA\n        LDS #$3FF0\n        LDD #${r["input_d"]:04X}\n')
        if r.get('mode')=='EXT':
            parts.append(f"        STD $2F00\n        LDA #${r['shift_count']:02X}\n")
        parts.append(f"        ANDCC #0\n        ORCC #${r['cc']:02X}\n")
        if r['encoding']:parts.append('        FCB '+','.join('$'+r['encoding'][n:n+2] for n in range(0,len(r['encoding']),2))+'\n')
        # Capture CC first. No data store or flag-changing instruction intervenes.
        parts.append('        PSHS CC\n')
        if r.get('mode')=='EXT':parts.append('        LDD $2F00\n')
        parts.append(f'        STD $2F02\n        PULS A\n        STA $2F04\n        LDA $DFA1\n        LDA ${0xdf00+(i>>8):04X}\n        LDA ${0xdf00+(i&255):04X}\n')
        for address in (0x2f02,0x2f03,0x2f04):
            parts.append(f'        LDX #$DF00\n        LDB ${address:04X}\n        ABX\n        LDA ,X\n')
    parts.append('''        LDA $DFFE
IDLE:
        LDX #$FFFF
IDLE_DELAY:
        LEAX -1,X
        BNE IDLE_DELAY
        TST $5FEA
        BRA IDLE
RAM_FAIL:
        LDA $DFF1
        BRA IDLE
        ORG $FFF6
        FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET
''')
    asm=''.join(parts);(p/'vectors.asm').write_text(asm)
    (p/'manifest.json').write_text(json.dumps(dict(cases=rows,source_sha256=hashlib.sha256(asm.encode()).hexdigest()),indent=2)+'\n')

def package(p):
    b=(p/'fixed.bin').read_bytes();assert len(b)==32768
    assert b[0x5c00:0x6000]==b'\xff'*1024
    image=bytes(0x18000)+b
    assert image[0x18000:0x1801a].hex()=='4280000824ff63fb92075fea10113a077c0010fb3a075d003dd0'
    m=json.loads((p/'manifest.json').read_text());m['image_sha256']=hashlib.sha256(image).hexdigest()
    (p/'vectors-128k.bin').write_bytes(image);(p/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')

def analyze(p):
    m=json.loads((p/'manifest.json').read_text())
    assert hashlib.sha256((p/'vectors-128k.bin').read_bytes()).hexdigest()==m['image_sha256']
    assert hashlib.sha256((p/'vectors.asm').read_bytes()).hexdigest()==m['source_sha256']
    context=json.loads((p/'vectors-128k.device.json').read_text())
    assert context['image_sha256']==m['image_sha256'] and context['build_config']=='POG_27C020_70ns'
    snaps=json.loads((p/'vectors-128k.events.json').read_text());events={}
    for s in snaps:
        assert not s['dropped_bytes'] and not s['capture_stopped']
        for e in s['events']:
            n=e['sequence'];assert n not in events or events[n]==e
            events[n]=e
    assert sorted(events)==list(range(snaps[-1]['count']))
    values=bytes(int(events[n]['address'],16)-0x100 for n in sorted(events))
    usb=bytes.fromhex(''.join(s['received_hex'] for s in snaps))
    assert values==usb, 'USB/event data mismatch'
    assert len(values)==2+6*len(m['cases']) and values[0]==0xa0 and values[-1]==0xfe, 'Incomplete run or unexpected boot/trap'
    rows=[]
    for i,c in enumerate(m['cases']):
        marker,hi,lo,a,b,cc=values[1+i*6:7+i*6]
        assert marker==0xa1 and (hi<<8|lo)==c['id']
        r=dict(**c,output_value=a<<8|b,output_cc=cc)
        if c['kind']=='baseline':assert r['output_value']==0x1234 and cc==c['cc'],r
        rows.append(r)
    (p/'results.json').write_text(json.dumps(dict(manifest=m,results=rows),indent=2)+'\n')
    print(f'{p.name}: {len(rows)} complete records; {sum(r['kind']=='baseline' for r in rows)} baseline checks pass; USB and timestamp ring agree')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['generate','package','analyze']);a.add_argument('batch',type=int)
    a.add_argument('--dataset',choices=['initial','boundary'],default='initial');args=a.parse_args()
    DATASET=args.dataset
    if DATASET!='initial':ROOT=ROOT/DATASET
    p=ROOT/f'batch-{args.batch:02d}'
    if args.action=='generate':generate(args.batch)
    elif args.action=='package':package(p)
    else:analyze(p)
