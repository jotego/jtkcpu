TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        TFR3E PC,X
AFTER:  CMPX #AFTER
        BNE BAD
        LDX #LAND
        TFR3E X,PC
        NOP
        BRA BAD
LAND:   NOP
        LDA #$55
        CMPA #$55
        BNE BAD
        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
