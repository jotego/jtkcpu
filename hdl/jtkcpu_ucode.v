/*  This file is part of JTKCPU.
    JTKCPU program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    JTKCPU program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with JTKCPU.  If not, see <http://www.gnu.org/licenses/>.

    Author: Jose Tejada Gomez. Twitter: @topapate
    Version: 1.0
    Date: 3-03-2023 */

module jtkcpu_ucode(
    input            rst,
    input            clk,
    input            cen,

    input      [7:0] op,     // data fetched from memory
    input      [7:0] mdata,
    // index addressing
    output reg [2:0] idx_rsel,
    output reg       idx_ind_rq,
    output reg       idx_post,
    output           idx_pre,
    output           idxw,
    // status inputs
    input           branch,
    input           alu_busy,
    input           mem_busy,
    input           idx_busy,
    input           irq_n,
    input           nmi_n,
    input           firq_n,
    // control outputs from ucode
    output          adr_data,
    output          adr_idx,
    output          adrx,
    output          adry,
    output          back1_unz,
    output          back2_unz,
    output          buserror,
    output          clr_e,
    output          decb,
    output          decu,
    output          decx,
    output          idx_en,
    output          idx_ld,
    output          idx_ret,
    output          incx,
    output          incy,
    output          int_en,
    output          jmp_idx,
    output          mem16,
    output          memhi,
    output          ni,
    output          opd,
    output          psh_all,
    output          psh_cc,
    output          psh_go,
    output          psh_pc,
    output          pul_go,
    output          pul_pc,
    output          rti_cc,
    output          rti_other,
    output          set_e,
    output          set_f,
    output          set_i,
    output          set_opn0_a,
    output          set_opn0_b,
    output          set_opn0_mem,
    output          set_opn0_regs,
    output          set_pc_bnz_branch,
    output          set_pc_branch16,
    output          set_pc_branch8,
    output          set_pc_jmp,
    output          set_pc_xnz_branch,
    output          up_cc,
    output          skip_noind,
    output          up_data,
    output          up_ld16,
    output          up_ld8,
    output          up_lda,
    output          up_ldb,
    output          up_lea,
    output          up_lines,
    output          up_lmul,
    output          we,

    // other outputs
    output    [3:0] intvec,
);

`include "jtkcpu.inc"

// Op codes = 8 bits, many op-codes will be parsed in the
// same way. Let's assume we only need 64 ucode routines
// 64 = 2^6, Using 2^10 memory rows -> 2^4=16 rows per
// routine
// To do: group op codes in categories that can be parsed
// using the same ucode. 32 categories used for op codes
// another 32 categories reserved for common routines

// localparam UCODE_AW = 10; // 1024 ucode lines

`include "jtkcpu_ucode.inc"

localparam [UCODE_AW-OPCAT_AW-1:0] OPLEN=0;

reg [UCODE_DW-1:0] mem[0:2**(UCODE_AW-1)], ucode;
reg [UCODE_AW-1:0] addr; // current ucode position read
reg [OPCAT_AW-1:0] opcat, post_idx, nx_cat;
reg          [3:0] cur_int;
reg                idxinc, nil, idxwl, idx_pre;

wire wait_stack, waitalu;

assign idx_w = set_idxw | idxwl;

always @* begin
    case( {mdata[7],mdata[2:0]} )
        4'b0_111: idx_cat = IDX_EXT;
        4'b0_000: idx_cat = IDX_RINC;
        4'b0_001: idx_cat = IDX_RINC2;
        4'b0_010: idx_cat = IDX_RDEC;
        4'b0_011: idx_cat = IDX_RDEC2;
        4'b0_100: idx_cat = IDX_OFFSET8;
        4'b0_101: idx_cat = IDX_OFFSET16;
        4'b0_110: idx_cat = IDX_IND;
        4'b1_100: idx_cat = IDX_DP;
        4'b1_000,
        4'b1_001,
        4'b1_111: idx_cat = IDX_ACC;
        default:  idx_cat = BUSERROR;
    endcase
end

// Conversion of opcodes to op category
always @* begin
    nx_cat = post_idx;
    case( op )
        ANDA_IMM, ADDA_IMM, SUBA_IMM, LDA_IMM,
        ANDB_IMM, ADDB_IMM, SUBB_IMM, LDB_IMM,
        EORA_IMM, BITA_IMM, ADCA_IMM, SBCA_IMM, ORA_IMM, ANDCC,
        EORB_IMM, BITB_IMM, ADCB_IMM, SBCB_IMM, ORB_IMM,  ORCC:     opcat = SINGLE_ALU;

        LDD_IMM, LDY_IMM, ADDD_IMM,
        LDX_IMM, LDU_IMM, SUBD_IMM,  LDS_IMM:                       opcat = SINGLE_ALU_16;

        CLRA, INCA, NEGA, COMA, TSTA, DECA, DAA, SEX,
        ABSA, LSRA, RORA, ASRA, ASLA, ROLA:                         opcat = SINGLE_A_INH;
        CLRB, INCB, NEGB, COMB, TSTB, DECB,
        ABSB, LSRB, RORB, ASRB, ASLB, ROLB:                         opcat = SINGLE_B_INH;

        ABX, CLRD, INCD, NEGD, TSTD, DECD, ABSD:               opcat = SINGLE_ALU_INH16;

        CLR,  INC,  NEG,  COM,  TST,  DEC,
        LSR,  ROR,  ASR,  ASL,  ROL:                                opcat = MEM_ALU_IDX;

        CMPA_IMM, CMPB_IMM:                                         opcat = CMP8;
        CMPD_IMM, CMPX_IMM, CMPY_IMM, CMPU_IMM,CMPS_IMM:            opcat = CMP16;

        // Operand in indexed memory
        CMPA_IDX, CMPB_IDX:                                   begin opcat  = PARSE_IDX;
                                                                    nx_cat = CMP8;
                                                              end
        CMPD_IDX, CMPX_IDX, CMPY_IDX, CMPU_IDX, CMPS_IDX:     begin opcat  = PARSE_IDX;
                                                                    nx_cat = CMP16;
                                                              end

        ANDA_IDX, ADDA_IDX, SUBA_IDX, LDA_IDX,
        EORA_IDX, BITA_IDX, ADCA_IDX, SBCA_IDX, ORA_IDX,
        ANDB_IDX, ADDB_IDX, SUBB_IDX, LDB_IDX,
        EORB_IDX, BITB_IDX, ADCB_IDX, SBCB_IDX, ORB_IDX:      begin opcat  = PARSE_IDX;
                                                                    nx_cat = SINGLE_ALU_IDX;
                                                              end

        LDU_IDX, LDD_IDX, LEAU, LEAX, ADDD_IDX,
        LDS_IDX, LDX_IDX, LEAS, LEAY, SUBD_IDX, LDY_IDX:      begin opcat  = PARSE_IDX;
                                                                    nx_cat = SINGLE_ALU_IDX16;
                                                              end

        // FIX MULTI_ALU_INH
        MUL, LMUL:                                                  opcat = MULTIPLY;
        DIV_X_B:                                                    opcat = MULTI_ALU_INH;
        LSRD_IMM, RORD_IMM, ASRD_IMM, ASLD_IMM, ROLD_IMM:           opcat = MULTI_ALU;
        LSRD_IDX, RORD_IDX, ASRD_IDX, ASLD_IDX, ROLD_IDX:           opcat = MULTI_ALU_IDX;

        LSRW, RORW, ASRW, ASLW, ROLW, NEGW, CLRW, INCW, DECW, TSTW: opcat = WMEM_ALU;
        BSR, BRA, BRN, BHI, BLS, BCC, BCS, BNE,
        BEQ, BVC, BVS, BPL, BMI, BGE, BLT, BGT, BLE:                opcat = SBRANCH;
        LBSR, LBRA, LBRN, LBHI, LBLS, LBCC, LBCS, LBNE,
        LBEQ, LBVC, LBVS, LBPL, LBMI, LBGE, LBLT, LBGT, LBLE:       opcat = LBRANCH;

        DECX_JNZ:       opcat = LOOPX;
        DECB_JNZ:       opcat = LOOPB;
        MOVE_Y_X_U:     opcat = MOVE;
        BMOVE_Y_X_U:    opcat = BMOVE;
        BSETA_X_U:      opcat = BSETA;
        BSETD_X_U:      opcat = BSETD;
        RTI:            opcat = RTIT;
        RTS:            opcat = RTSR;
        JMP:            opcat = JUMP;
        JSR:            opcat = JMSR;
        PUSHU, PUSHS:   opcat = PSH;
        PULLU, PULLS:   opcat = PUL;
        NOP:            opcat = NOPE;
        // SETLINES_IDX    opcat = SETLINES

        STA, STB:       begin   opcat  = PARSE_IDX;
                                nx_cat = STORE8;
                        end
        STD, STX, STY,
        STU, STS:       begin   opcat  = PARSE_IDX;
                                nx_cat = STORE16;
                        end
        default:                opcat  = BUSERROR; // stop condition
    endcase
end

// get ucode data from a hex file
// initial begin
//     $readmemh( mem, "jtkcpu_ucode.hex");
// end

assign intvec = cur_int & {4{int_en}};
assign idx_inc = idxinc;

always @(posedge clk) begin
    if( rst ) begin
        addr    <= { RESET, OPLEN };  // Reset starts ucode at 0
        cur_int <= 4'b1000;
    end else if( cen && !buserror ) begin
        nil       <= ni;
        post_idx  <= nx_cat;
        idx_post1 <= 0;
        idx_post2 <= 0;

        if( !mem_busy && !(idx_en && idx_busy)) begin
            addr <= addr + 1; // keep processing an opcode routine
            if( skip_noind && !op[4] ) begin
                addr <= addr + 2;
            end
        end
        if( nil ) begin
            if( !nmi_n ) begin // interrupt enabled irq
                cur_int <= 4'b0100;
                addr    <= { NMI, OPLEN };
            end else if( !firq_n ) begin  // interrupt enabled nmi
                cur_int <= 4'b0010;
                addr    <= { FIRQ, OPLEN };
            end else if ( !irq_n ) begin  // interrupt enabled firq
                cur_int <= 4'b0001;
                addr    <= { IRQ, OPLEN };
            end else begin   // interrupt disabled
                cur_int <= 0;
                addr    <= { opcat, OPLEN }; // when a new opcode is read
            end
        end
        // Indexed addressing parsing
        if( jmp_idx ) begin
            addr       <= {idx_cat, OPLEN};
            idx_rsel    <= mdata[6:4];
            idx_ind_rq <= mdata[3];
            idx_postl  <= set_idx_post;
            idxwl      <= set_idxw;
        end
        if( idx_ind ) begin
            addr <= { IDX_IND, OPLEN}
        end
        if( idx_ret ) begin
            idx_post  <= idx_postl;
            idx_postl <= 0;
            addr <= { nx_cat, OPLEN };
        end
    end
end

endmodule