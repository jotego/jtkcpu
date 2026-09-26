; 053248 RESET opcode reaches the FFFE vector without waiting for watchdog.
TESTCTRL EQU $1000
        ORG $F000
RESET:  LDS #$0800
        RESET
        LBRA BAD
        ORG $F100
HANDLER:
        include ../finish.inc
        DC.B [$FFFE-*]0
        FDB HANDLER
