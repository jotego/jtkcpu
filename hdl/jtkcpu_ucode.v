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
    input            cen /* synthesis direct_enable */,

    input     [15:0] mdata,
    input     [ 7:0] cc,
    input     [ 7:0] a,
    input     [ 7:0] op,     // data fetched from memory

    output           buserror,
    output reg       str_busy, // signal a long string operation
    // status inputs
    input            alu_busy,
    input            div_extra,
    input            mem_busy,
    input            stack_busy,
    input            branch,
    input            irq_n,
    input            nmi_n,
    input            firq_n,
    input            uz,

    // indexed addressing
    output reg [2:0] idx_rsel,
    output reg [2:0] idx_asel,
    output reg       idx_post,
    output reg       idx_acc,
    output reg       idx_ld,
    output reg       idxw,
    output           idx_pre,
    output           idx_dp,
    output           idx_en,
    output           idx_16,
    output           idx_8,
    output           data2addr,

    // control outputs from ucode
    output           addrx,
    output           addry,
    output           branch_bnz,
    output           clr_e,
    output           decb,
    output           decu,
    output           decx,
    output           div_en,
    output           idx_adv,
    output           incx,
    output           int_en,
    output           memhi,
    output           ni,
    output           niuz,
    output           opd,
    output           pc_jmp,
    output           psh_all,
    output           psh_cc,
    output           psh_go,
    output           psh_pc,
    output           pul_go,
    output           rti_cc,
    output           rti_other,
    output           set_e,
    output           set_f,
    output           set_i,
    output           set_opn0_mem,
    output           set_pc_branch16,
    output           set_pc_branch8,
    output           shd_en,
    output           up_ab,
    output           up_abx,
    output           up_cc,
    output           up_div,
    output           up_exg,
    output           up_ld16,
    output           up_ld8,
    output           up_lda,
    output           up_ldb,
    output           up_lea,
    output           up_lines,
    output           up_lmul,
    output           up_move,
    output           up_tfr,
    output           we,

    // other outputs
    output    [3:0]  intvec,
    output           intsrv,
    output           soft_retry,
    // debug
    output reg       irq_bsy    // set as output to preven a Quartus warning
);

reg          [3:0] cur_int;
reg          [5:0] br_delay;
reg          [1:0] block_flush;
reg          [3:0] branch_wait_count;
reg                idx_postl, nil, niuzl, idx_ind_rq, br_ni_hold, br_ni_done;
reg                nmin_l, do_nmi;
wire               idx_ret, idx_ind, idx_jmp,
                   set_idx_post, set_idx_acc, set_idxw;
wire               cc_i, cc_f;
wire               uc_loop, set_fake_irq, eff_irqn, dynwait, ni_raw;
wire        [2:0] stack_bytes, stack_words;
wire        [5:0] stack_wait_count;
reg                fake_irq, clr_fake_irq; // fake irq is used on the custom
                    // BSWI instruction, which mixes a branch with a SWI
                    // and is helpful for debugging game problems

`include "jtkcpu.inc"
`include "jtkcpu_ucode.inc"

localparam [UCODE_AW-OPCAT_AW-1:0] OPLEN=0;

assign cc_i = cc[CC_I];
assign cc_f = cc[CC_F];
assign eff_irqn = irq_n & ~fake_irq;
assign ni = ni_raw && br_delay==0 && !(br_ni_hold && br_ni_done);
assign stack_bytes = {2'b0,mdata[0]}+{2'b0,mdata[1]}+{2'b0,mdata[2]}+{2'b0,mdata[3]};
assign stack_words = {2'b0,mdata[4]}+{2'b0,mdata[5]}+{2'b0,mdata[6]}+{2'b0,mdata[7]};
assign stack_wait_count = op==PUSHS || op==PUSHU ?
    6'd14 + {2'b0,stack_bytes,1'b0} + {1'b0,stack_words,2'b0} + {3'b0,stack_words} :
    6'd13 + {2'b0,stack_bytes,1'b0} + {3'b0,stack_bytes} +
    {1'b0,stack_words,2'b0} + {2'b0,stack_words,1'b0} - {5'b0,mdata[7]};

always @* begin
    branch_wait_count = 4'd0;
    case (op)
        BHI:                            branch_wait_count = branch ? 4'd8 : 4'd2;
        BLS:                            branch_wait_count = branch ? 4'd6 : 4'd4;
        BCC, BCS, BNE, BEQ, BVC, BVS,
        BPL, BMI:                       branch_wait_count = branch ? 4'd6  : 4'd2;
        BGE:                            branch_wait_count = branch ? 4'd8  : 4'd4;
        BGT:                            branch_wait_count = branch ? 4'd10 : 4'd6;
        BLT:                            branch_wait_count = branch ? 4'd7  : 4'd4;
        BLE:                            branch_wait_count = branch ? 4'd9  : 4'd6;
        LBHI:                           branch_wait_count = branch ? 4'd9  : 4'd0;
        LBLS:                           branch_wait_count = branch ? 4'd7  : 4'd4;
        LBCC, LBNE, LBVC, LBPL:         branch_wait_count = branch ? 4'd7  : 4'd0;
        LBCS, LBEQ, LBVS, LBMI:         branch_wait_count = branch ? 4'd7  : 4'd2;
        LBGE:                           branch_wait_count = branch ? 4'd9  : 4'd3;
        LBGT:                           branch_wait_count = branch ? 4'd11 : 4'd5;
        LBLT:                           branch_wait_count = branch ? 4'd8  : 4'd4;
        LBLE:                           branch_wait_count = branch ? 4'd10 : 4'd6;
        default:;
    endcase
end

always @* begin
    case( {mdata[7],mdata[2:0]} )
        4'b0_111: idx_cat = IDX_EXT;
        4'b0_000: idx_cat = IDX_RINC;
        4'b0_001: idx_cat = IDX_RINC2;
        4'b0_010: idx_cat = IDX_RDEC;
        4'b0_011: idx_cat = IDX_RDEC2;
        4'b0_100: idx_cat = IDX_OFFSET8;
        4'b0_101: idx_cat = IDX_OFFSET16;
        4'b0_110: idx_cat = IDX_R;
        4'b1_100: idx_cat = IDX_DP;
        4'b1_000,
        4'b1_001,
        4'b1_010,
        4'b1_011,
        4'b1_101,
        4'b1_110: idx_cat = IDX_ACC;
        4'b1_111: idx_cat = IDX_ACCD;
        default:  idx_cat = BUSERROR;
    endcase
end

always @(posedge clk, posedge rst) begin
    if( rst ) begin
        str_busy <= 0;
    end else begin
        if( niuz ) str_busy <= ~uz;
        if( uc_loop && (opcat==BMOVE_START || opcat==BSETA_START ||
                        opcat==BSETD_START)) str_busy <= 1;
    end
end

// Conversion of opcodes to op category
always @* begin
    nx_cat = post_idx;
    case( op )
        OP_RESET:                   opcat = RESET;
        OP_NMI, SOFT_SWI:          opcat = NMI;
        OP_FIRQ:                    opcat = FIRQ;
        OP_IRQ:                     opcat = IRQ;
        ADDA_IMM, SUBA_IMM, ADDB_IMM, SUBB_IMM,
        ADCA_IMM, SBCA_IMM, ADCB_IMM, SBCB_IMM:                        opcat  = SINGLE_ALU;
        ANDA_IMM, LDA_IMM, ANDB_IMM, LDB_IMM,
        EORA_IMM, ORA_IMM, EORB_IMM, ORB_IMM:                          opcat  = SINGLE_ALU9;
        ADDD_IMM, SUBD_IMM:                                           opcat  = SINGLE_ALUD;
        LDD_IMM, LDY_IMM, LDX_IMM, LDU_IMM, LDS_IMM:                  opcat  = SINGLE_ALU_16;
        CMPA_IMM, CMPB_IMM:                                           opcat  = CMP8;
        ANDCC, ORCC, BITA_IMM, BITB_IMM:                              opcat  = CMP8_9;
        CMPD_IMM:                                                     opcat  = CMPD13;
        CMPX_IMM, CMPY_IMM, CMPU_IMM, CMPS_IMM:                       opcat  = CMP16;
        ABSD:                                                         opcat  = SINGLE_D8;
        NEGD:                                                         opcat  = SINGLE_D7;
        INCD, DECD:                                                   opcat  = SINGLE_D6;
        TSTD:                                                         opcat  = SINGLE_D5;
        CLRD, SEX:                                                    opcat  = SINGLE_ALU_INH16;
        NEGB, ABSB, LSRB:                                             opcat  = SINGLE_B5;
        CLRB, INCB, COMB, TSTB, DECB,
        RORB, ASRB, ASLB, ROLB:                                       opcat  = SINGLE_B_INH;
        NEGA, ABSA, LSRA:                                             opcat  = SINGLE_A5;
        DAA:                                                          opcat  = DAA_TIMED;
        CLRA, INCA, COMA, TSTA, DECA,
        RORA, ASRA, ASLA, ROLA:                                       opcat  = SINGLE_A_INH;
        CLR_NF:                                                   begin opcat = PARSE_IDX;
                                                                        nx_cat = MEM_ALU_NF;
                                                                  end
        TST:                                                      begin opcat = PARSE_IDX;
                                                                        nx_cat = MEM_ALU_IDX;
                                                                  end
        CLR:                                                      begin opcat = PARSE_IDX;
                                                                        nx_cat = MEM_ALU_CLR;
                                                                  end
        ROL:                                                    begin opcat = PARSE_IDX;
                                                                        nx_cat = MEM_ALU_ROL;
                                                                end
        INC, NEG, COM, DEC, LSR, ROR, ASR, ASL:                  begin opcat = PARSE_IDX;
                                                                        nx_cat = MEM_ALU_OTHER;
                                                                end
        CMPA_IDX, CMPB_IDX:                                     begin opcat  = PARSE_IDX;
                                                                      nx_cat = CMP8_IDX;
                                                                end
        BITA_IDX, BITB_IDX:                                     begin opcat  = PARSE_IDX;
                                                                      nx_cat = BIT8_IDX;
                                                                end
        CMPX_IDX, CMPY_IDX, CMPD_IDX, CMPU_IDX, CMPS_IDX:       begin opcat  = PARSE_IDX;
                                                                      nx_cat = CMP16_IDX;
                                                                end
        ADDA_IDX, SUBA_IDX, LDA_IDX, ADCA_IDX, SBCA_IDX,
        ADDB_IDX, SUBB_IDX, LDB_IDX, ADCB_IDX, SBCB_IDX:         begin opcat  = PARSE_IDX;
                                                                      nx_cat = SINGLE_ALU_IDX;
                                                                end
        ANDA_IDX, EORA_IDX, ORA_IDX,
        ANDB_IDX, EORB_IDX, ORB_IDX:                            begin opcat  = PARSE_IDX;
                                                                      nx_cat = SINGLE_ALU_IDX_LOG;
                                                                end
        LEAX05:                                                   begin opcat = PARSE_IDX;
                                                                        nx_cat = LEA05;
                                                                  end
        LEAX06:                                                   begin opcat = PARSE_IDX;
                                                                        nx_cat = LEA06;
                                                                  end
        LEAX07:                                                   begin opcat = PARSE_IDX;
                                                                        nx_cat = LEA07;
                                                                  end
        LEAU, LEAX, LEAS, LEAY:                                  begin opcat = PARSE_IDX;
                                                                        nx_cat = LEA;
                                                                end
        ADDD_IDX, SUBD_IDX:                                     begin opcat  = PARSE_IDX;
                                                                      nx_cat = SINGLE_ALUD_IDX;
                                                                end
        LDU_IDX, LDX_IDX, LDD_IDX,
        LDS_IDX, LDY_IDX:                                       begin opcat  = PARSE_IDX;
                                                                      nx_cat = SINGLE_ALU_IDX16;
                                                                end

        LSRD_IMM, RORD_IMM:                                           opcat = SHIFTD_R;
        ASRD_IMM:                                                     opcat = SHIFTD_AR;
        ASLD_IMM, ROLD_IMM:                                           opcat = SHIFTD;
        LSRD_IDX, RORD_IDX:                                     begin opcat = PARSE_IDX;
                                                                      nx_cat = SHIFTD_IDX_R;
                                                                end
        ASRD_IDX:                                               begin opcat = PARSE_IDX;
                                                                      nx_cat = SHIFTD_IDX_AR;
                                                                end
        ASLD_IDX, ROLD_IDX:                                     begin opcat  = PARSE_IDX;
                                                                      nx_cat = SHIFTD_IDX;
                                                                end

        TSTW:                                                   begin opcat = PARSE_IDX; nx_cat = WMEM_TST; end
        CLRW:                                                   begin opcat = PARSE_IDX; nx_cat = WMEM_CLR; end
        ROLW, NEGW, INCW, DECW:                                 begin opcat = PARSE_IDX; nx_cat = WMEM_ALU; end
        ASLW:                                                   begin opcat = PARSE_IDX; nx_cat = WMEM_ASL; end
        LSRW, RORW, ASRW:                                       begin opcat = PARSE_IDX; nx_cat = WMEM_RIGHT; end
        BRA:                                                          opcat = BRA11;
        BRN:                                                          opcat = BRN6;
        LBRA:                                                         opcat = LBRA13;
        LBRN:                                                         opcat = LBRN7;
        BHI, BLS, BCC, BCS, BNE,
        BEQ, BVC, BVS, BPL, BMI, BGE, BLT, BGT, BLE:                  opcat  = SBRANCH;
        LBHI, LBLS, LBCC, LBCS, LBNE, LBLE,
        LBEQ, LBVC, LBVS, LBPL, LBMI, LBGE, LBLT, LBGT:               opcat  = LBRANCH;

        LBSR:                   opcat  = BSRL;
        BSR:                    opcat  = SBSR;
        EXG:                    opcat  = EXCHANGE;
        TFR:                    opcat  = TRANSFER;
        ABX:                    opcat  = SINGLE_ABX;
        MUL:                    opcat  = MULTIPLY;
        LMUL:                   opcat  = LMULTIPLY;
        DIVXB:                  opcat  = DIVIDE;
        DECX_JNZ:               opcat  = LOOPX;
        DECB_JNZ:               opcat  = LOOPB;
        MOVE_Y_X_U:             opcat  = MOVE;
        BMOVE_Y_X_U:            opcat  = str_busy ? BMOVE : BMOVE_START;
        BSETA_X_U:              opcat  = str_busy ? BSETA : BSETA_START;
        BSETD_X_U:              opcat  = str_busy ? BSETD : BSETD_START;
        RTI:                    opcat  = RTIT;
        RTS:                    opcat  = RTSR;
        PUSHU, PUSHS:           opcat  = PSH;
        PULLU, PULLS:           opcat  = PUL;
        NOP:                    opcat  = NOPE;
        BSWI:                   opcat  = BRSWI;
        SETLINES_IMM:           opcat  = SETLNS;
        SETLINES_IDX:   begin   opcat  = PARSE_IDX;
                                nx_cat = SETLNS_IDX;
                        end
        JMP:            begin   opcat  = PARSE_IDX;
                                nx_cat = JUMP;
                        end
        JSR:            begin   opcat  = PARSE_IDX;
                                nx_cat = JMSR;
                        end
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

assign intvec = cur_int & {4{int_en}};
assign intsrv = do_nmi || (!firq_n && !cc_f) || (!eff_irqn && !cc_i);
assign soft_retry = nil && (op==OP_NMI || op==OP_FIRQ || op==OP_IRQ);

`ifdef SIMULATION
integer error_cnt=-1;
always @(posedge clk) if( cen )  begin
    if( buserror && error_cnt<0 ) error_cnt <= 40;
    if( error_cnt > 0 ) error_cnt <= error_cnt - 1;
    if( error_cnt==0 ) begin
        $display("\nJTKCPU Error: simulation finished because of bus error");
        $finish;
    end
end
`endif

always @(posedge clk) begin
    if( rst ) begin
        addr       <= { RESET, OPLEN };  // Reset starts ucode at 0
        cur_int    <= 4'b1000;
        idx_rsel   <= 0;
        idx_asel   <= 0;
        idx_ind_rq <= 0;
        idx_postl  <= 0;
        nil        <= 0;
        post_idx   <= 0;
        idx_post   <= 0;
        idx_ld     <= 0;
        idx_acc    <= 0;
        idxw       <= 0;
        nmin_l     <= 0;
        do_nmi     <= 0;
        niuzl      <= 0;
        irq_bsy    <= 0;
        fake_irq   <= 0;
        clr_fake_irq <= 0;
        br_delay <= 0;
        block_flush <= 0;
        br_ni_hold <= 0;
        br_ni_done <= 0;
    end else if( cen && !buserror ) begin
        nil        <= ni | niuzl;
        niuzl      <= niuz & uz;
        if (niuzl) block_flush <= 2;
        else if (block_flush!=0) block_flush <= block_flush-1'd1;
        post_idx   <= nx_cat;
        idx_post   <= 0;
        idx_ld     <= 0;
        nmin_l     <= nmi_n;

        if( set_fake_irq ) fake_irq <= 1;
        if( !nmi_n && nmin_l ) do_nmi <= 1; // NMI is edge triggered
        if( !mem_busy && !alu_busy && !stack_busy && !(niuz && uz) && !niuzl ) begin
            addr <= addr + 1'd1; // keep processing an opcode routine
        end
        if (set_pc_branch8 || set_pc_branch16) begin
            br_delay <= {2'b0,branch_wait_count};
        end
        if (op==DAA && up_lda) br_delay <= 6'd10 -
            (cc[CC_H] ? 6'd3 : (a[3:0]>4'd9 ? 6'd1 : 6'd0)) -
            (cc[CC_C] ? 6'd3 : (a>8'h99 ? 6'd1 : 6'd0));
        if (up_div) br_delay <= div_extra ? 6'd3 : 6'd2;
        if ((psh_go && (op==PUSHS || op==PUSHU)) ||
            (pul_go && (op==PULLS || op==PULLU))) br_delay <= stack_wait_count;
        if (psh_go && psh_all) br_delay <= 6'd44;
        if (psh_go && psh_cc) br_delay <= 6'd17;
        if (pul_go && rti_other) br_delay <= mdata[{1'b0,CC_E}] ? 6'd44 : 6'd11;
        if (dynwait && br_delay!=0) begin
            addr <= addr;
            br_delay <= br_delay-1'd1;
            br_ni_hold <= 1;
        end
        if (ni_raw && br_delay!=0) begin
            addr <= addr;
            br_delay <= br_delay-1'd1;
        end
        if (!ni_raw && !dynwait) begin
            br_ni_hold <= 0;
            br_ni_done <= 0;
        end else if (ni && br_ni_hold) br_ni_done <= 1;
        if( rti_cc ) irq_bsy <= 1;
        if( int_en || ni ) irq_bsy <= 0;
        if( ni ) begin
            if( clr_fake_irq ) begin
                fake_irq <= 0;
                clr_fake_irq <= 0;
            end
            if( do_nmi ) begin // pending NMI
                do_nmi  <= 0;
                cur_int <= 4'b0100;
                addr    <= { NMI, OPLEN };
                irq_bsy <= 1;
                nil <= 0;
            end else if( !firq_n && !cc_f ) begin  // FIRQ triggered by level
                cur_int <= 4'b0010;
                addr    <= { FIRQ, OPLEN };
                irq_bsy <= 1;
                nil <= 0;
            end else if ( !eff_irqn && !cc_i ) begin  // IRQ triggered by level
                cur_int <= 4'b0001;
                addr    <= { IRQ, OPLEN };
                irq_bsy <= 1;
                clr_fake_irq <= 1;
                nil <= 0;
            end
        end
        if( nil ) begin
            cur_int <= 0;
            addr    <= { opcat, OPLEN }; // when a new opcode is read
            case (op)
                OP_RESET: cur_int <= 4'b1000;
                OP_NMI:   cur_int <= 4'b0100;
                OP_FIRQ:  cur_int <= 4'b0010;
                OP_IRQ:   cur_int <= 4'b0001;
                SOFT_SWI: cur_int <= 4'b1111;
                default:;
            endcase
        end
        if( uc_loop ) addr <= { opcat==BMOVE_START ? BMOVE :
                               opcat==BSETA_START ? BSETA :
                               opcat==BSETD_START ? BSETD : opcat, OPLEN };
        // Indexed addressing parsing
        if( set_idx_post ) idx_postl <= 1;
        if( set_idxw     ) idxw <= 1;
        idx_acc <= set_idx_acc;
        if( idx_jmp ) begin
            addr       <= {idx_cat, OPLEN};
            idx_rsel   <= mdata[6:4];
            idx_asel   <= mdata[2:0];
            idx_ind_rq <= mdata[3];
            idxw       <= 0;
        end
        if( idx_ind ) begin
            idx_ld    <= !data2addr && !idx_dp && !idx_8 && !idx_16;
            addr      <= idx_ind_rq ? {IDX_IND, OPLEN} : {nx_cat, OPLEN};
            idx_post  <= idx_postl;
            idx_postl <= 0;
        end
        if( idx_ret ) begin
            idx_ind_rq <= 0;
            idxw       <= 0;
            addr       <= {nx_cat, OPLEN};
        end
    end
end

endmodule
