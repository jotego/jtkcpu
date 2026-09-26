"""Operand-controlled timings with a measured setup-only reference for each case."""

def cases():
    rows=[]
    def add(code,name,loads,operand,instruction=None,displacement=False):
        enc=bytearray();asm=[]
        for reg,value in loads:
            opcode,width={'A':(0x10,1),'B':(0x11,1),'D':(0x40,2),'X':(0x42,2),'Y':(0x44,2),'U':(0x46,2)}[reg]
            enc+=bytes([opcode])+value.to_bytes(width,'big')
            asm.append(f'        LD{reg} #${value:0{width*2}X}\n')
        enc+=bytes.fromhex('3c503d50');asm+=['        ANDCC #$50\n        ORCC #$50\n']
        tested=bytes([code]+([0] if displacement else []))
        first=len(rows)+1
        common=dict(opcode=code,mnemonic=name,mode='CONTROLLED',encoding=tested.hex(),operand=operand,
                    unit_setup_encoding=enc.hex(),unit_setup_asm=''.join(asm),instruction_asm=instruction or name,
                    coverage='fixed operands and CC50 before every tested instruction; measured setup-only slope subtracted; other operand classes pending')
        rows.append(dict(**common,id=first,measurement_role='baseline',unit_encoding=enc.hex()))
        rows.append(dict(**common,id=first+1,measurement_role='paired',baseline_case_id=first,unit_encoding=(enc+tested).hex()))
        target=rows[-1]
        if displacement:
            taken=loads[0][1]!=1
            prefix=f'CHECK{first}'
            pre=''.join(asm)+f'        FCB ${code:02X}\n        FCB {prefix}_TAKEN-*-1\n'
            pre+=f'        JMP {"RAM_FAIL" if taken else prefix+"_OK"}\n{prefix}_TAKEN:\n'
            if not taken:pre+='        JMP RAM_FAIL\n'
            target['preflight']=pre+prefix+'_OK:\n'
            target['taken']=taken
        if code in (0xb6,0xb7,0xcf,0xd0):
            values=dict(loads);count=values['U']
            written=1 if code==0xb7 else count*(2 if code==0xd0 else 1)
            prefix=f'FILL{first}'
            target['preflight']=f'''        LDX #$2800
        LDA #$5A
{prefix}_SRC:
        STA ,X+
        CMPX #$2A00
        BNE {prefix}_SRC
        LDX #$2FFF
        LDA #$A5
{prefix}_DST:
        STA ,X+
        CMPX #$3402
        BNE {prefix}_DST
'''
            guard=f'        CMPX #${0x3000+written:04X}\n        LBNE RAM_FAIL\n        CMPU #${count-1 if code==0xb7 else 0:04X}\n        LBNE RAM_FAIL\n'
            if code in (0xb6,0xb7):guard+=f'        CMPY #${0x2800+written:04X}\n        LBNE RAM_FAIL\n'
            if code==0xd0:
                for address in (0x3000,0x3000+written-2):
                    guard+=f'        LDD ${address:04X}\n        CMPD #$1234\n        LBNE RAM_FAIL\n'
            else:
                for address in (0x3000,0x3000+written-1):
                    guard+=f'        LDA ${address:04X}\n        CMPA #${0x55 if code==0xcf else 0x5a:02X}\n        LBNE RAM_FAIL\n'
            for address in (0x2fff,0x3000+written):
                guard+=f'        LDA ${address:04X}\n        CMPA #$A5\n        LBNE RAM_FAIL\n'
            target['postflight']=guard
            target['written_bytes']=written
            target['coverage']+='; final pointers, first/last data and adjacent sentinels checked'
    for a,b in ((0,0),(1,1),(255,255),(128,2),(85,170),(18,52)):
        add(0xb3,'MUL',[('D',a<<8|b)],f'A={a:02X},B={b:02X}')
    for x,y in ((0,0),(1,1),(65535,65535),(32768,2),(0x55aa,0xaa55),(0x1234,0x5678)):
        add(0xb4,'LMUL',[('X',x),('Y',y)],f'X={x:04X},Y={y:04X}')
    for x,b in ((0,1),(1,1),(65535,1),(65535,255),(0x8000,2),(0x1234,0x56),(0,0),(65535,0)):
        add(0xb5,'DIV X,B',[('X',x),('B',b)],f'X={x:04X},B={b:02X}')
    for code,name,reg in ((0xac,'DECB,JNZ','B'),(0xad,'DECX,JNZ','X')):
        for value in (1,2,0):
            add(code,name,[(reg,value)],f'{reg}={value}; '+('untaken' if value==1 else 'taken'),displacement=True)
    for count in (1,2,8,16,128,512):
        add(0xb6,'BMOVE Y,X,U',[('X',0x3000),('Y',0x2800),('U',count)],f'U={count},src=2800,dst=3000')
    for count in (1,512):
        add(0xb7,'MOVE Y,X,U',[('X',0x3000),('Y',0x2800),('U',count)],f'U={count},src=2800,dst=3000')
    for count in (1,2,8,16,128,512):
        add(0xcf,'BSET A,X,U',[('X',0x3000),('U',count),('A',0x55)],f'U={count},A=55,dst=3000','BSETA X,U')
        add(0xd0,'BSET D,X,U',[('X',0x3000),('U',count),('D',0x1234)],f'U={count},D=1234,dst=3000','BSETD X,U')
    # Block count zero is deliberately absent until its wrap/write behavior is established.
    # A 65536-element wrap could reach PCB I/O, including EEPROM outputs.
    return rows
