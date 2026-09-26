        ORG $8000
RESET:
        LDX #$8000
BOOT_DELAY:
        LEAX -1,X
        BNE BOOT_DELAY
        TST $5FEA
        LDA #$11
        STA $7C00
        LDA #$FB
        STA $5D00
        ORCC #$D0
        ORCC #$50
        CLRA
        STA $5FE2
        STA $5D00
        LDA #$10
        STA $5FE0
        SETLINES #0
        TST $5FEA
        LDA $DF10
        LDA $DC00
        CMPA #$50
        BNE BAD
        LDA $DC01
        CMPA #$49
        BNE BAD
        LDA $DC02
        CMPA #$43
        BNE BAD
        LDA $DC03
        CMPA #$4F
        BNE BAD
        LDA $DF20
        LDA $DF20
        LDA $DF21
HEARTBEAT:
        LDA $DF30
        LDX #$FFFF
DELAY:
        TST $5FEA
        LEAX -1,X
        BNE DELAY
        BRA HEARTBEAT
BAD:
        LDA $DFEE
BAD_IDLE:
        TST $5FEA
        BRA BAD_IDLE
        ORG $9000
FIRQ_TRAP:
        LDA $DFE0
FIRQ_IDLE:
        TST $5FEA
        BRA FIRQ_IDLE
        ORG $9010
IRQ_TRAP:
        LDA $DFE1
IRQ_IDLE:
        TST $5FEA
        BRA IRQ_IDLE
        ORG $9020
SWI_TRAP:
        LDA $DFE2
SWI_IDLE:
        TST $5FEA
        BRA SWI_IDLE
        ORG $9030
NMI_TRAP:
        LDA $DFE3
NMI_IDLE:
        TST $5FEA
        BRA NMI_IDLE
        ORG $FFF6
        FDB FIRQ_TRAP,IRQ_TRAP,SWI_TRAP,NMI_TRAP,RESET
