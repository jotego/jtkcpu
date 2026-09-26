; 053248 IRQ opcode: full frame retries opcode PC, FFF8 vector.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        ANDCC #0
        ORCC #1
TARGET: IRQ
AFTER:  LBRA BAD
        ORG $F100
HANDLER:
        TFR S,X
        CMPX #$07F4
        BNE BAD
        LDD 10,S
        CMPD #TARGET
        BNE BAD
        LDA ,S
        CMPA #$81
        BNE BAD
        include ../finish.inc
        DC.B [$FFF8-*]0
        FDB HANDLER,$FFFF,$FFFF,RESET
