; Both 3E/3F use postbyte bit 7 for copy versus exchange.
; Selector 4 holds the full DP-related word, with only its high byte
; exposed by PSHS DP.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        LDX #$A67B
        LDY #$1234
        TFR3E X,DP       ; copy with primary 3E
        EXG3F DP,Y       ; exchange with primary 3F
        CMPY #$A67B
        BNE BAD
        TFR DP,X
        CMPX #$1234
        BNE BAD
        PSHS DP
        PULS A
        CMPA #$12
        BNE BAD
        LDX #$2FA5
        TFR3E X,DP
        LDA #$12
        PSHS A
        PULS DP
        TFR3E DP,Y
        CMPY #$12A5
        BNE BAD
        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
