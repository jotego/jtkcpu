; 053248 NMI opcode: full frame retries opcode PC, FFFC vector.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        ANDCC #0
        ORCC #1
TARGET: NMI
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
        DC.B [$FFFC-*]0
        FDB HANDLER,RESET
