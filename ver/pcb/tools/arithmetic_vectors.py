#!/usr/bin/env python3
"""Capture D/X/Y/CC for controlled MUL, LMUL and DIV operand cases."""
from pcb_paths import TEMPLATES
import argparse,hashlib,json,re
from pathlib import Path
import instruction_timing as timing
from paired_timing_cases import cases as paired_cases
ROOT=timing.ROOT/'artifacts/arithmetic-vectors'
DATASET='arithmetic'

def cases():
    rows=[]
    opcodes=(0xb3,0xb4,0xb5) if DATASET=='arithmetic' else (0xb6,0xb7,0xcf,0xd0)
    targets=[r for r in paired_cases() if r['measurement_role']=='paired' and r['opcode'] in opcodes]
    for r in targets:
        for cc in (0x50,0x7f):
            loads=r['unit_setup_asm'].split('        ANDCC')[0]
            rows.append(dict(id=len(rows),opcode=r['opcode'],mnemonic=r['mnemonic'],operand=r['operand'],
                encoding=r['encoding'],load_asm=loads,cc=cc,
                preflight=re.sub(r'\bFILL(\d+)',fr'FV{len(rows)}_\1',r.get('preflight',''))))
    if DATASET=='blocks':return rows
    for value in (1,2,0x8000):
        for cc in (0x50,0x7f):
            rows.append(dict(id=len(rows),opcode=0xb5,mnemonic='DIV X,B',operand=f'X={value:04X},B=00',
                encoding='b5',load_asm=f'        LDX #${value:04X}\n        LDB #0\n',cc=cc))
    return rows

def generate():
    ROOT.mkdir(parents=True,exist_ok=True)
    rows=cases();prefix=(TEMPLATES / 'bootstrap.asm').read_text().split('        LDA $DF10')[0]
    parts=[prefix,timing.RAM]
    for r in rows:
        i=r['id']
        parts.append(f'        LDX #$FFFF\nD{i}:\n        LEAX -1,X\n        BNE D{i}\n        TST $5FEA\n')
        parts.append(r.get('preflight',''))
        parts.append(timing.SETUP+r['load_asm']+f"        ANDCC #0\n        ORCC #${r['cc']:02X}\n        FCB ${r['opcode']:02X}\n")
        parts.append(f'''        PSHS CC
        STD $2F02
        STX $2F04
        STY $2F06
        STU $2F08
        PULS A
        STA $2F0A
        LDA $DFA1
        LDA ${0xdf00+(i>>8):04X}
        LDA ${0xdf00+(i&255):04X}
''')
        for address in range(0x2f02,0x2f0b):
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
    asm=''.join(parts);(ROOT/'vectors.asm').write_text(asm)
    (ROOT/'manifest.json').write_text(json.dumps(dict(cases=rows,source_sha256=hashlib.sha256(asm.encode()).hexdigest()),indent=2)+'\n')

def package():
    b=(ROOT/'fixed.bin').read_bytes();assert len(b)==32768 and b[0x5c00:0x6000]==b'\xff'*1024
    image=bytes(0x18000)+b
    assert image[0x18000:0x1801a].hex()=='4280000824ff63fb92075fea10113a077c0010fb3a075d003dd0'
    m=json.loads((ROOT/'manifest.json').read_text());m['image_sha256']=hashlib.sha256(image).hexdigest()
    (ROOT/'vectors-128k.bin').write_bytes(image);(ROOT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')

def analyze():
    m=json.loads((ROOT/'manifest.json').read_text())
    for name,key in (('vectors-128k.bin','image_sha256'),('vectors.asm','source_sha256')):
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==m[key]
    context=json.loads((ROOT/'vectors-128k.device.json').read_text())
    assert context['image_sha256']==m['image_sha256'] and context['build_config']=='POG_27C020_70ns'
    snaps=json.loads((ROOT/'vectors-128k.events.json').read_text());events={}
    for s in snaps:
        assert not s['dropped_bytes'] and not s['capture_stopped']
        for e in s['events']:
            n=e['sequence'];assert n not in events or events[n]==e
            events[n]=e
    assert sorted(events)==list(range(snaps[-1]['count']))
    values=bytes(int(events[n]['address'],16)-0x100 for n in sorted(events))
    assert values==bytes.fromhex(''.join(s['received_hex'] for s in snaps))
    assert len(values)==2+12*len(m['cases']) and values[0]==0xa0 and values[-1]==0xfe
    rows=[]
    for i,r in enumerate(m['cases']):
        record=values[1+12*i:13+12*i]
        assert record[0]==0xa1 and int.from_bytes(record[1:3],'big')==r['id']
        result=dict(**r,output_D=int.from_bytes(record[3:5],'big'),output_X=int.from_bytes(record[5:7],'big'),
            output_Y=int.from_bytes(record[7:9],'big'),output_U=int.from_bytes(record[9:11],'big'),output_CC=record[11])
        rows.append(result)
        print(f"{r['mnemonic']} {r['operand']} CC={r['cc']:02X}: D={result['output_D']:04X} X={result['output_X']:04X} Y={result['output_Y']:04X} U={result['output_U']:04X} CC={result['output_CC']:02X}")
    (ROOT/'results.json').write_text(json.dumps(dict(manifest=m,results=rows),indent=2)+'\n')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['generate','package','analyze'])
    a.add_argument('--dataset',choices=['arithmetic','blocks'],default='arithmetic');args=a.parse_args()
    DATASET=args.dataset
    if DATASET=='blocks':ROOT=ROOT/'blocks'
    globals()[args.action]()
