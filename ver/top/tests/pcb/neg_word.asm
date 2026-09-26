; Physical word NEG records: framed-unary/boundary and extended-RAM unary.
; C is set for every nonzero input, including 8000 and FFFF.
TESTCTRL EQU $1000
        CPU 053248
        ORG $F000
RESET:  LDS #$0800
        ANDCC #0
        LDD #$0000
        NEGD
        PSHS CC
        STD $0000
        PULS A
        CMPA #$04
        BNE BAD
        LDD $0000
        CMPD #$0000
        BNE BAD

        ANDCC #0
        LDD #$0001
        NEGD
        PSHS CC
        STD $0000
        PULS A
        CMPA #$09
        BNE BAD
        LDD $0000
        CMPD #$FFFF
        BNE BAD

        ANDCC #0
        LDD #$8000
        NEGD
        PSHS CC
        STD $0000
        PULS A
        CMPA #$0B
        BNE BAD
        LDD $0000
        CMPD #$8000
        BNE BAD

        ANDCC #0
        LDD #$FFFF
        NEGD
        PSHS CC
        STD $0000
        PULS A
        CMPA #$01
        BNE BAD
        LDD $0000
        CMPD #$0001
        BNE BAD

        LDX #$0200
        LDD #$8000
        STD ,X
        ANDCC #0
        NEGW ,X
        PSHS CC
        PULS A
        CMPA #$0B
        BNE BAD
        LDD ,X
        CMPD #$8000
        BNE BAD

        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
