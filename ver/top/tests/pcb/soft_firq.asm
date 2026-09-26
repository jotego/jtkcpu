; 053248 FIRQ opcode: short frame retries opcode PC, FFF6 vector.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        ANDCC #0
        ORCC #1
TARGET: FIRQ
AFTER:  LBRA BAD
        ORG $F100
HANDLER:
        TFR S,X
        CMPX #$07FD
        BNE BAD
        LDD 1,S
        CMPD #TARGET
        BNE BAD
        LDA ,S
        CMPA #$01
        BNE BAD
        include ../finish.inc
        DC.B [$FFF6-*]0
        FDB HANDLER,$FFFF,$FFFF,$FFFF,RESET
