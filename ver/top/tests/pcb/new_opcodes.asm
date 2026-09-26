; 053248 opcodes 05-07 and D1, using measured postbyte 26 (,X).
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        LDX #0
        ANDCC #0
        ORCC #1
        FCB $05,$26     ; LEAX05 ,X: X=0, Z=1, C preserved
        BNE BAD
        BCC BAD
        ANDCC #$FB
        FCB $06,$26     ; LEAX06 ,X
        BNE BAD
        FCB $07,$26     ; LEAX07 ,X
        BNE BAD
        LDA #$A5
        STA ,X
        ANDCC #0
        ORCC #$5F
        FCB $D1,$26     ; CLR.NF ,X: memory cleared, CC unchanged
        PSHS CC
        PULS A
        CMPA #$5F
        BNE BAD
        LDA ,X
        BNE BAD
        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
