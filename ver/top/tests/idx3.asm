; Load test
; 0000-0FFF RAM
; 1000      Simulation control
; 1001		read only, A[23:16]
; F000-FFFF ROM

; Simulation control bits
; 0 -> set to finish the sim
; 1 -> set to mark a bad result
; 5 -> set to trigger IRQ.  Clear manually
; 6 -> set to trigger FIRQ. Clear manually
; 7 -> set to trigger NMI.  Clear manually

TESTCTRL EQU $1000
DATAW    EQU $0100

        ORG $F000
RESET:  LEAU DATAR
        LEAS DATAW
        LDB #15
LOOP:                   ; Copy data in reversed order
        LDA ,U+
        STA B,S
        DECB
        BPL LOOP

        LEAU DATAR
        LEAS DATAW
        LDA #15         ; check that the copy was correct
CHECK:  LDB  A,U
        CMPB ,S+
        BNE BAD
        DECA
        BPL CHECK

END:    LDU #$BABE
        LDA #1
        LDS #TESTCTRL
        STA ,S                  ; Finish test, result ok
        BRA END

BAD:    LDU #$DEAD
        LDA #3
        LDS #TESTCTRL
        STA ,S                  ; Finish test, result bad
        BRA BAD

DATAR:  DB   0,1,2,3,4,5,6,7,8,9,$A,$B,$C,$D,$E,$F

        DC.B  [$FFFE-*]0
        FDB   RESET