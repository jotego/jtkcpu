; Physical 053248 regression, expected to fail before the proposed RTL correction.
; Evidence: framed-unary/boundary/batch-00/results.json, zero-based record 49.
; See ver/pcb/README.md and doc/pcb-053248.md for scope and capture validation.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        LDD #$00A5
        LDX #$2F00
        LDY #$2F10
        ANDCC #0
        ORCC #$01
        ABSA
        PSHS CC
        STD $0000
        STX $0002
        STY $0004
        PULS A
        STA $0006
        LDD $0000
        CMPD #$00A5
        BNE BAD
        LDX $0002
        CMPX #$2F00
        BNE BAD
        LDY $0004
        CMPY #$2F10
        BNE BAD
        LDA $0006
        CMPA #$04
        BNE BAD
        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
