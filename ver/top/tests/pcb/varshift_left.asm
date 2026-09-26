; Selected 053248 variable left-shift and rotate results/flags.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800

        LDD #$8001
        ANDCC #0
        ORCC #$53
        ASLD #0
        STD $0200
        PSHS CC
        PULS A
        STA $0202
        LDD $0200
        CMPD #$8001
        LBNE BAD
        LDA $0202
        CMPA #$58
        LBNE BAD

        LDD #$8001
        ANDCC #0
        ORCC #$53
        ROLD #1
        STD $0200
        PSHS CC
        PULS A
        STA $0202
        LDD $0200
        CMPD #$0003
        LBNE BAD
        LDA $0202
        CMPA #$50
        LBNE BAD

        LDD #$8001
        ANDCC #0
        ORCC #$53
        ROLD #15
        STD $0200
        PSHS CC
        PULS A
        STA $0202
        LDD $0200
        CMPD #$C000
        LBNE BAD
        LDA $0202
        CMPA #$58
        LBNE BAD

        LDD #$8001
        STD $0300
        LDA #0
        ANDCC #0
        ORCC #$53
        FCB $BF,$07,$03,$00
        PSHS CC
        PULS A
        STA $0202
        LDD $0300
        CMPD #$8001
        LBNE BAD
        LDA $0202
        CMPA #$58
        LBNE BAD

        LDD #$8001
        STD $0300
        LDA #15
        ANDCC #0
        ORCC #$53
        FCB $C1,$07,$03,$00
        PSHS CC
        PULS A
        STA $0202
        LDD $0300
        CMPD #$C000
        LBNE BAD
        LDA $0202
        CMPA #$58
        LBNE BAD

        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
