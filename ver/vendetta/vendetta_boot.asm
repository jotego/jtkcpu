; SPDX-FileCopyrightText: 2026 Jose Tejada Gomez
; SPDX-License-Identifier: GPL-3.0-or-later
;
; Vendetta bootstrap for JTKCPU issue 1. ASL -cpu 052001.
; Board map: jtsimson_main.v, Vendetta PAL U21/U22 and U25 decode.
; Only the program ROM is replaced; font tiles come from the game ROMs.

WATCHDOG EQU $5FEA
OUTPUT   EQU $5FE0
CONTROL  EQU $5FE2
PCU      EQU $5FA0
RAMSTART EQU $2000
RAMEND   EQU $4000
STACKTOP EQU $3FF0
IRQCOUNT EQU $2000             ; big endian word
STATUS   EQU $2010             ; A5 = ready, E1 = RAM fault, E2 = interrupt fault
COUNTROW EQU $6000+12*64+26

        ORG $8000
RESET:
        ORCC #$50             ; mask IRQ and FIRQ before touching peripherals
        LDA WATCHDOG
        CLRA
        STA CONTROL           ; IRQ off, EEPROM deselected, video RAM selected
        SETLINES #0           ; reserve bank-0 $1C00..1FFF for future PicoROM comms
        LDA #$10
        STA OUTPUT            ; INIT on, RMRD and OBJCHA off

; No stack, subroutine calls, or variables until ALL work RAM passes.
; Ascending read/replace sweeps also expose aliased RAM addresses.
        LDX #RAMSTART
        LDA #$55
RAM_FILL:
        STA ,X+
        LDB WATCHDOG
        CMPX #RAMEND
        BNE RAM_FILL
        LDX #RAMSTART
RAM_55:
        LDA ,X
        CMPA #$55
        LBNE RAM_FAIL
        LDA #$AA
        STA ,X+
        LDB WATCHDOG
        CMPX #RAMEND
        BNE RAM_55
        LDX #RAMSTART
RAM_AA:
        LDA ,X
        CMPA #$AA
        LBNE RAM_FAIL
        CLRA
        STA ,X+
        LDB WATCHDOG
        CMPX #RAMEND
        BNE RAM_AA
        LDX #RAMSTART
RAM_ZERO:
        LDA ,X+
        LBNE RAM_FAIL
        LDB WATCHDOG
        CMPX #RAMEND
        BNE RAM_ZERO
        LDS #STACKTOP
        LDA #$11
        STA STATUS            ; RAM verified

; At reset K052109 attributes/registers are in $6000..7FFF. Mode 1
; moves attributes to $4000..5FFF and codes to $6000..7FFF.
        LDA #$11
        STA $7C00
        STA $5C00
        CLRA
        STA $5C80             ; no row/column scroll
        STA $5D00             ; no tile-chip interrupts (Vendetta uses LVBL)
        STA $5D80             ; tile banks 0
        STA $5E00
        STA $5E80             ; no flip
        STA $5F00
        LDX #$4000
CLEAR_ATTR:
        STA ,X+
        LDB WATCHDOG
        CMPX #$5C00           ; three tilemaps and scroll tables, not registers
        BNE CLEAR_ATTR
        LDA #$10              ; blank glyph
        LDX #$6000
CLEAR_CODE:
        STA ,X+
        LDB WATCHDOG
        CMPX #$7800
        BNE CLEAR_CODE
; Unscrolled layer A/B: K052109 subtracts six from horizontal scroll.
        CLRA
        STA $580C
        STA $580D
        STA $580E
        STA $580F
        LDA #6
        STA $5A00
        STA $5A01
        STA $5A02
        STA $5A03
        CLRA
        STA $5A04
        STA $5A05
        STA $5A06
        STA $5A07

; Palette and sprite RAM overlay. Keep EEPROM/IRQ bits zero.
        LDA #1
        STA CONTROL
        CLRA
        LDX #$4000
CLEAR_OBJ:
        STA ,X+
        LDB WATCHDOG
        CMPX #$5000
        BNE CLEAR_OBJ
        LDX #$6000
CLEAR_PAL:
        STA ,X+
        LDB WATCHDOG
        CMPX #$7000
        BNE CLEAR_PAL
; Vendetta's font uses foreground pen 8 and shadow pen A in the core's
; plane order. Leave the shadow black. CI2 has four font color groups.
        LDX #$6010
        LDD #$7FFF             ; white, palette 0
        JSR PALETTE
        LDX #$6030
        LDD #$001F             ; red, palette 1
        JSR PALETTE
        LDX #$6050
        LDD #$03E0             ; green, palette 2
        JSR PALETTE
        LDX #$6070
        LDD #$7C00             ; blue, palette 3
        JSR PALETTE
        LDX #$6210
        LDD #$4210             ; gray, layer A palette 16
        JSR PALETTE
        CLRA
        STA CONTROL
; Disable sprite DMA and ROM reads; all sprites are also cleared above.
        STA $5FB5
; Priority/color mixer: fixed text first, then A, with black backdrop.
        LDX #PCU
        LDY #PCU_VALUES
        LDB #13
PCU_INIT:
        LDA ,Y+
        STA ,X+
        DECB
        BNE PCU_INIT

        LDX #TITLE
        LDY #$6000+6*64+16
        JSR PRINT
        LDX #RAM_OK
        LDY #$6000+8*64+16
        JSR PRINT
        LDX #WD_OK
        LDY #$6000+10*64+16
        JSR PRINT
        LDX #IRQ_TEXT
        LDY #$6000+12*64+16
        JSR PRINT
        LDX #RED_TEXT
        LDY #$6000+16*64+16
        JSR PRINT
        LDX #GREEN_TEXT
        LDY #$6000+16*64+20
        JSR PRINT
        LDX #BLUE_TEXT
        LDY #$6000+16*64+26
        JSR PRINT
        LDX #WHITE_TEXT
        LDY #$6000+16*64+31
        JSR PRINT
; Put GRAY on layer A so it has an independent palette bank.
        LDX #GRAY_TEXT
        LDY #$6800+16*64+37
        JSR PRINT
        LDX #$4000+16*64+16
        LDA #$40
        STA ,X+
        STA ,X+
        STA ,X
        LDX #$4000+16*64+20
        LDA #$80
        LDB #5
GREEN_ATTR:
        STA ,X+
        DECB
        BNE GREEN_ATTR
        LDX #$4000+16*64+26
        LDA #$C0
        LDB #4
BLUE_ATTR:
        STA ,X+
        DECB
        BNE BLUE_ATTR
        LDX #FOOTER
        LDY #$6000+20*64+16
        JSR PRINT
        LDA #$A5
        STA STATUS
        LDA WATCHDOG
        LDA #$40
        STA CONTROL           ; enable LVBL IRQ, retain video RAM mapping
        ANDCC #$EF            ; unmask IRQ, keep FIRQ masked
IDLE:
        LDA WATCHDOG          ; servicing does not depend on interrupt delivery
        BRA IDLE

; X = palette foreground pen, D = xBGR555. Other pens remain black.
PALETTE:
        STD ,X
        LDA WATCHDOG
        RTS

; X = zero-terminated ASCII (uppercase/digits/spaces), Y = tile-code RAM.
; Installed Vendetta font: 0..9 at $00..09, A..Z at $11..2A, space $10.
PRINT:
        LDA ,X+
        BEQ PRINT_DONE
        CMPA #$20
        BEQ PRINT_SPACE
        SUBA #$30             ; maps both digits and uppercase letters
        BRA PRINT_TILE
PRINT_SPACE:
        LDA #$10
PRINT_TILE:
        STA ,Y+
        LDB WATCHDOG
        BRA PRINT
PRINT_DONE:
        RTS

; Called only during vertical blank. IRQ auto-stacks the interrupted state.
IRQ:
        CLRA
        STA CONTROL           ; clear irqen to acknowledge the latched LVBL IRQ
        INC IRQCOUNT+1
        BNE IRQ_NO_CARRY
        INC IRQCOUNT
IRQ_NO_CARRY:
        LDY #COUNTROW
        LDA IRQCOUNT
        JSR HEX_BYTE
        LDA IRQCOUNT+1
        JSR HEX_BYTE
        LDA WATCHDOG
        LDA #$40
        STA CONTROL
        RTI
HEX_BYTE:
        PSHS A
        LSRA
        LSRA
        LSRA
        LSRA
        JSR HEX_NIBBLE
        PULS A
        ANDA #$0F
HEX_NIBBLE:
        CMPA #10
        BCS HEX_STORE
        ADDA #7
HEX_STORE:
        STA ,Y+
        RTS

UNEXPECTED:
        ORCC #$50
        LDA #$E2
        BRA FAIL_MARK
RAM_FAIL:
        LDA #$E1
FAIL_MARK:
        STA STATUS            ; best effort diagnostic marker; RAM may be faulty
        ORCC #$50
        LDA #1
        STA CONTROL           ; IRQ off, palette selected
; Stackless solid red fallback. Never return through potentially bad RAM.
        LDX #$6000
FAIL_PALETTE:
        LDD #$001F
        STD ,X++
        LDA WATCHDOG
        CMPX #$7000
        BEQ FAIL_IDLE
        BRA FAIL_PALETTE
FAIL_IDLE:
        LDA WATCHDOG
        BRA FAIL_IDLE

PCU_VALUES:
        FCB 63,63,0,1,63,0,0,0,0,0,1,0,7
TITLE:  FCC "JTKCPU VENDETTA TEST"
        FCB 0
RAM_OK: FCC "RAM PASS"
        FCB 0
WD_OK:  FCC "WATCHDOG ACTIVE"
        FCB 0
IRQ_TEXT: FCC "IRQ COUNT 0000"
        FCB 0
RED_TEXT: FCC "RED"
        FCB 0
GREEN_TEXT: FCC "GREEN"
        FCB 0
BLUE_TEXT: FCC "BLUE"
        FCB 0
WHITE_TEXT: FCC "WHITE"
        FCB 0
GRAY_TEXT: FCC "GRAY"
        FCB 0
FOOTER: FCC "BOOTSTRAP 01"
        FCB 0

        FCB [$FFF6-*]$FF
        FDB UNEXPECTED,IRQ,UNEXPECTED,UNEXPECTED,RESET
