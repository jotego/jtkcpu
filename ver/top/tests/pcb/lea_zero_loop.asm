TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        LDX #5
LOOP:   LEAX -1,X
        BNE LOOP
        CMPX #0
        BNE BAD
        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
