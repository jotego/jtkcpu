; Konami indexed addressing register-offset test
; 0000-0FFF RAM
; 1000      Simulation control
; F000-FFFF ROM

TESTCTRL EQU $1000
DATAW    EQU $0100

        ORG $F000
RESET:
        LEAX DATAW
        DC.B $08,$A2             ; LEAX X,X
        CMPX #(DATAW+DATAW)
        BNE  BAD

        LEAX DATAW
        LEAY $0020
        DC.B $09,$A3             ; LEAY Y,X
        CMPY #(DATAW+$20)
        BNE  BAD

        LEAX DATAW
        LEAU $0003
        DC.B $08,$A5             ; LEAX U,X
        CMPX #(DATAW+3)
        BNE  BAD

        LEAX DATAW
        LEAS $0005
        DC.B $08,$A6             ; LEAX S,X
        CMPX #(DATAW+5)
        BNE  BAD

        LEAX DATAW
        LDD  #$0006
        DC.B $08,$A7             ; LEAX D,X
        CMPX #(DATAW+6)
        BNE  BAD

        LDA  #$5A
        STA  DATAW+1
        LEAX DATAW
        LEAY $0001
        DC.B $12,$A3             ; LDA Y,X
        CMPA #$5A
        BNE  BAD

        LDD  #TARGET
        STD  DATAW+4
        LEAX DATAW
        LEAY $0004
        DC.B $08,$AB             ; LEAX [Y,X]
        CMPX #TARGET
        BNE  BAD

        include finish.inc

TARGET:
        DC.B  $CA,$FE

        DC.B  [$FFFE-*]0
        FDB   RESET
