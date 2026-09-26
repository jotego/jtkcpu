"""TST addressing probes with safe RAM pointers and post-window guards."""
PREP='''        LDS #$3FF0
        LDX #$2B00
        LDA #$38
{label}_PTR_FILL:
        STA ,X+
        CMPX #$3302
        BNE {label}_PTR_FILL
        CLR $3838
        LDA #$2F
        PSHS A
        PULS DP
'''

def cases():
    rows=[]
    def add(post,extra,operand,base=None,delta=0,d=5,indirect=False,mode='INDEXED'):
        setup=(f'        LD{base} #$2F00\n' if base else '')+f'        LDD #${d:04X}\n        ANDCC #$50\n        ORCC #$50\n'
        rows.append(dict(id=len(rows)+1,opcode=0x92,mnemonic='TST',mode=mode,
            encoding=bytes([0x92,post]+extra).hex(),postbyte=post,operand=operand+f' (D={d:04X})',
            instruction_asm='TST '+operand,indirect=indirect,pre_window=PREP,setup_extra=setup,
            capture_asm='        PSHS CC\n        STD $3F00\n        PULS B\n',saved_d=d,cc_check=[4,4 if indirect else 0],
            post_registers={base:[0x2f00,delta]} if base else {},
            coverage='TST representative, RAM operands; pointer and final Z checked; other instructions, PC modes and further displacements pending'))
    for base,bits in (('X',0x20),('Y',0x30),('U',0x50),('S',0x60)):
        specs=[(6,[],f',{base}',0),(0,[],f',{base}+',1),(1,[],f',{base}++',2),
               (2,[],f',-{base}',-1),(3,[],f',--{base}',-2),
               (4,[1],f'1,{base}',0),(4,[255],f'-1,{base}',0),
               (5,[1,0],f'256,{base}',0),(5,[255,0],f'-256,{base}',0)]
        for indirect in (False,True):
            for low,extra,operand,delta in specs:
                add(bits|low|(8 if indirect else 0),extra,f'[{operand}]' if indirect else operand,base,delta,indirect=indirect)
            for reg,low in (('A',0),('B',1),('D',7)):
                for offset in (5,-5):
                    seed=((offset&255)<<8) if reg=='A' else (offset&255) if reg=='B' else offset&65535
                    operand=f'{reg},{base}'
                    add(0x80|bits|low|(8 if indirect else 0),[],f'[{operand}]' if indirect else operand,base,d=seed,indirect=indirect)
    for indirect in (False,True):
        add(0x07|(8 if indirect else 0),[0x2f,0], '[$2F00]' if indirect else '$2F00',indirect=indirect,mode='EXT')
        add(0xc4|(8 if indirect else 0),[0], '[<$00]' if indirect else '<$00',indirect=indirect,mode='DIRECT')
    assert len(rows)==124
    return rows
