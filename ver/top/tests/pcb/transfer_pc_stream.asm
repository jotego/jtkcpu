; 3E 27 executes one opcode from the old stream after PC exchange.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        LDA #$AE
        STA $0200
        LDA #$11
        STA $0201
        LDA #$66
        STA $0202
        LDA #$8F
        STA $0203
        LDX #CHECK
        PSHS X
        LDD #$1200
        LDX #$0200
        FCB $3E,$27
        CLRA
CHECK:  CMPD #$0066
        LBNE BAD
        LDA #$AE
        STA $0210
        LDA #$11
        STA $0211
        LDA #$66
        STA $0212
        LDA #$8F
        STA $0213
        LDX #CHECK2
        PSHS X
        LDD #$1200
        LDX #$0210
        FCB $3E,$27
        LDA #$99
CHECK2: CMPD #$AE66
        LBNE BAD
        LDX #CHECK3
        PSHS X
        LDD #$1200
        LDX #$0200
        FCB $3F,$27
        CLRA
CHECK3: CMPD #$0066
        LBNE BAD
        LDX #CHECK4
        PSHS X
        LDD #$1200
        LDX #$0200
        FCB $3E,$72
        CLRA
CHECK4: CMPD #$0066
        LBNE BAD
        LDX #CHECK5
        PSHS X
        LDD #$1200
        LDX #$0200
        FCB $3F,$72
        CLRA
CHECK5: CMPD #$0066
        LBNE BAD
        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB RESET
