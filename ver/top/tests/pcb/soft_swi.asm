; 053248 SWI: full frame, next-byte PC, FFFA vector, CC E/F/I set.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        ANDCC #0
        ORCC #1
        SWI
AFTER:  LBRA BAD
        ORG $F100
HANDLER:
        TFR S,X
        CMPX #$07F4
        BNE BAD
        LDD 10,S
        CMPD #AFTER
        BNE BAD
        LDA ,S
        CMPA #$81
        BNE BAD
        PSHS CC
        PULS A
        ANDA #$D0
        CMPA #$D0
        BNE BAD
        include ../finish.inc
        DC.B [$FFFA-*]0
        FDB HANDLER,$FFFF,RESET
