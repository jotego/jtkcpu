"""Bounded PC-relative TST probes; inline data uses observable fallback opcodes."""
from indexed_timing_cases import PREP

def cases():
    rows=[]
    def add(encoding,operand,nz,d=0x1234,unit=None,target=None,prep=PREP):
        r=dict(id=len(rows)+1,opcode=0x92,mnemonic='TST',mode='PC',encoding=encoding,operand=operand,
            pre_window=prep,setup_extra=f'        LDD #${d:04X}\n        ANDCC #$50\n        ORCC #$50\n',
            capture_asm='        PSHS CC\n        STD $3F00\n        PULS B\n',saved_d=d,cc_check=[12,nz],
            coverage='bounded PC addressing; final NZ and preserved D checked; predecrement PC and other displacements pending')
        if unit:r['unit_encoding']=unit
        if target is not None:r['dynamic_pc_target']=target
        rows.append(r)
    add('92073838','extended RAM zero-data control',4)
    add('9276',',PC (last read is following PSHS opcode)',0)
    # If these bytes are executed rather than skipped, CLRA/ORA change D and fail its guard.
    add('9270',',PC+; inline 80 skipped',8,unit='927080')
    add('9271',',PC++; inline 3030 skipped',0,unit='92713030')
    add('9278','[,PC+]; inline 80 skipped; last target 800C',0,unit='927880')
    add('9279','[,PC++]; inline 3030 skipped; target RAM 3030',0,unit='92793030')
    for displacement,nz in ((0,4),(-1,0),(-2,8)):
        add(bytes([0x92,0x74,displacement&255]).hex(),f'{displacement},PC (8-bit)',nz)
    direct=PREP.replace('LDA #$38','LDA #$39')+'        CLR $2F00\n'
    indirect=PREP.replace('LDA #$38','LDA #$39')+'''        LDD #$3838
        STD $2F00
        LDA #$38
        STA $3839
        STA $3938
        STA $3939
'''
    add('9275','PC+varying 16-bit displacement to RAM 2F00',4,target=0x2f00,prep=direct)
    add('927d','[PC+varying 16-bit displacement to pointer 2F00]',4,target=0x2f00,prep=indirect)
    for reg,post in (('A',0xf0),('B',0xf1),('D',0xf7)):
        for offset in (0,-1,-2):
            d=((offset&255)<<8) if reg=='A' else (offset&255) if reg=='B' else offset&65535
            add(bytes([0x92,post]).hex(),f'{reg},PC with {reg}={offset}',0 if offset==0 else 8,d=d)
    for reg,post in (('A',0xf8),('B',0xf9),('D',0xff)):
        add(bytes([0x92,post]).hex(),f'[{reg},PC] with {reg}=0; final pointer 0C01 to bank-0 ROM',4,d=0)
    add('927c00','[0,PC] (8-bit); final pointer 000C to bank-0 ROM',4)
    assert len(rows)==24
    return rows
