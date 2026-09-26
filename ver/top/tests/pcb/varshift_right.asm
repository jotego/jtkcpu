; Variable right-shift zero count, 16-bit rotation, and CC behavior.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800

        LDD #$8001
        ANDCC #0
        ORCC #$53
        FCB $B8,$00
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
        FCB $BA,$00
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
        FCB $BC,$01
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
        FCB $BB,$07,$03,$00
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
        LDA #1
        ANDCC #0
        ORCC #$53
        FCB $BD,$07,$03,$00
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
