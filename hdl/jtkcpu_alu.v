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
    Date: 14-02-2023 */

module jtkcpu_alu(
    input             rst,
    input             clk,
    input             cen /* synthesis direct_enable */,

    input      [ 7:0] op,
    input      [15:0] opnd0,
    input      [15:0] opnd1, // data from memory
    input      [ 7:0] cc_in,
    output     [ 7:0] cc_out,

    // Special OPs
    input             dec8,
    input             dec16,
    input             div_en,
    input             shd_en,
    input             idx_en,

    output            busy,
    output            div_extra,

    output reg [15:0] rslt,
    output reg [15:0] rslt_hi // used only in lmul
);

`include "jtkcpu.inc"

wire [3:0] msb;
wire       div_busy;
reg        shd_busy, shd_zero, alu16, up_z, up_n;
reg        c_out, v_out, z_out, n_out, h_out, e_out, i_out, f_out;

// Multi-bit shift
reg  [15:0] shd_data;
reg  [ 4:0] shd_cnt;
wire [ 3:0] shd_mux;
wire       shd_left;
wire [15:0] shd_input, shd_lresult;
// Divider
wire [15:0] div_quot;
wire [ 7:0] div_rem;
wire        div_v;
reg         div_sign = 0;

assign cc_out   = { e_out, f_out, h_out, i_out, n_out, z_out, v_out, c_out };
assign msb      = alu16 ? 4'd15 : 4'd7;
assign busy     = div_busy | shd_busy;
assign div_extra = opnd1[7:0]==0 ? !opnd0[15] : div_quot[0];
assign shd_mux  = idx_en ? opnd0[11:8] : opnd1[3:0];
assign shd_left = op==ASLD_IMM || op==ASLD_IDX || op==ROLD_IMM || op==ROLD_IDX;
assign shd_input = idx_en ? opnd1 : opnd0;
assign shd_lresult = op==ROLD_IMM || op==ROLD_IDX ?
    (shd_input << shd_mux) | (shd_input >> (5'd16-{1'b0,shd_mux})) :
    shd_input << shd_mux;

always @(posedge clk) begin
    case( op )
        CMPD_IMM, CMPD_IDX, ASRD_IMM, ASRD_IDX, ASRW, ADDD_IMM, INCD, NEGD, ABSD,
        CMPX_IMM, CMPX_IDX, ASLD_IMM, ASLD_IDX, ASLW, ADDD_IDX, INCW, NEGW,  ABX,
        CMPY_IMM, CMPY_IDX, ROLD_IMM, ROLD_IDX, ROLW, SUBD_IMM, DECD, TSTD,  SEX,
        CMPU_IMM, CMPU_IDX, RORD_IMM, RORD_IDX, LSRW, SUBD_IDX, DECW, TSTW,
        CMPS_IMM, CMPS_IDX, LSRD_IMM, LSRD_IDX, RORW, DIVXB,
        LEAX, LEAX05, LEAX06, LEAX07, LDD_IMM, LDX_IMM, LDY_IMM, STX,
        LEAY,     LDD_IDX,  LDX_IDX,  LDY_IDX,  STY,
        LEAU,     LDU_IMM,  LDS_IMM,  CLRD,     STU,
        LEAS,     LDU_IDX,  LDS_IDX,  CLRW,     STS, STD:
                 alu16 <= 1;
        default: alu16 <= 0;
    endcase
    if( dec16 ) alu16 <= 1;
    up_n  <= op!=LEAX && op!=LEAX05 && op!=LEAX06 && op!=LEAX07 &&
             op!=LEAY && op!=LEAU && op!=LEAS && op!=ABX &&
             op!=MUL  && op!=LMUL  && op!=DIVXB && op!=ANDCC && op!=ORCC;
    up_z  <= op!=LEAU && op!=LEAS  && op!=ABX && op!=ANDCC && op!=ORCC;
end

always @(posedge clk, posedge rst) begin
    if( rst ) begin
        shd_cnt  <= 0;
        shd_data <= 0;
        shd_zero <= 0;
    end else if(cen) begin
        shd_busy <= shd_cnt!=0;
        if( shd_en && shd_left ) begin
            shd_data <= shd_lresult;
            shd_cnt  <= 5'd16-{1'b0,shd_mux};
            shd_zero <= 0;
            shd_busy <= 1;
        end else if( shd_en ) begin
            shd_data <= opnd1;
            shd_cnt  <= {1'b0,shd_mux};
            shd_zero <= shd_mux==0;
            shd_busy <= 1;
        end else if( shd_cnt!=0 ) begin
            shd_cnt  <= shd_cnt-1'd1;
            if( !shd_left ) shd_data <= rslt;
        end
    end
end

jtkcpu_div u_div(
    .rst  ( rst         ),
    .clk  ( clk         ),
    .cen  ( cen         ),
    .op0  ( opnd0       ),
    .op1  ( opnd1[7:0]  ),
    .len  ( 1'b1        ),
    .sign ( div_sign    ),
    .start( div_en      ),
    .quot ( div_quot    ),
    .rem  ( div_rem     ),
    .busy ( div_busy    ),
    .v    ( div_v       )
);

always @* begin
    c_out   = cc_in[CC_C];
    v_out   = cc_in[CC_V];
    z_out   = cc_in[CC_Z];
    n_out   = cc_in[CC_N];
    h_out   = cc_in[CC_H];
    e_out   = cc_in[CC_E];
    i_out   = cc_in[CC_I];
    f_out   = cc_in[CC_F];
    rslt    = opnd0;  // default value
    rslt_hi = 0;

    case (op)
        TSTA, TSTB, TSTD,
        STA,  STB,  STD,
        STX,  STY,  STU,  STS: begin
            rslt  = opnd0;
            v_out = 0;
        end
        LEAX, LEAX05, LEAX06, LEAX07, LEAY, LEAU, LEAS: begin
            rslt  = opnd0;
        end
        LDA_IMM, LDB_IMM, LDA_IDX, LDB_IDX, TST,
        LDD_IMM, LDD_IDX, LDX_IMM, LDX_IDX, LDY_IMM,
        LDY_IDX, LDU_IMM, LDU_IDX, LDS_IMM, LDS_IDX, TSTW: begin  // LD, ST, TST, TSTD, TSTW
            rslt  = opnd1;
            v_out = 0;
        end
        ADDA_IMM,ADDB_IMM,ADDA_IDX,ADDB_IDX: begin  // ADD
            {c_out, rslt[7:0]} = {1'b0, opnd0[7:0]} + {1'b0, opnd1[7:0]};
            v_out = opnd0[7]==opnd1[7] && opnd0[7]!=rslt[7];
            h_out = opnd0[4] ^ opnd1[4] ^ rslt[4];
        end
        ADDD_IMM,ADDD_IDX: begin  // ADD
            {c_out, rslt} = {1'b0, opnd0} + {1'b0, opnd1};
            v_out = opnd0[15]==opnd1[15] && opnd0[15]!=rslt[15];
        end
        ADCA_IMM,ADCB_IMM,ADCA_IDX,ADCB_IDX: begin  // ADC
            {c_out, rslt[7:0]} =  {1'b0, opnd0[7:0]} + {1'b0, opnd1[7:0]} + {8'd0,cc_in[CC_C]};
            v_out = opnd0[7]==opnd1[7] && opnd0[7]!=rslt[7];
            h_out = opnd0[4] ^ opnd1[4] ^ rslt[4];
        end
        SUBA_IMM, SUBB_IMM,
        SUBA_IDX, SUBB_IDX,
        CMPA_IMM, CMPB_IMM,
        CMPA_IDX, CMPB_IDX: begin  // SUB
            {c_out, rslt[7:0]} = {1'b0, opnd0[7:0]} - {1'b0, opnd1[7:0]};
            v_out = opnd0[7]!=opnd1[7] && opnd0[7]!=rslt[7];
        end
        SUBD_IMM, SUBD_IDX,
        CMPD_IMM, CMPD_IDX,
        CMPX_IMM, CMPX_IDX,
        CMPY_IMM, CMPY_IDX,
        CMPU_IMM, CMPU_IDX,
        CMPS_IMM, CMPS_IDX:  begin  // SUB/CMP
            {c_out, rslt} = {1'b0, opnd0} - {1'b0, opnd1};
            v_out = opnd0[15]!=opnd1[15] && opnd0[15]!=rslt[15];
        end
        SBCA_IMM,SBCB_IMM,SBCA_IDX,SBCB_IDX: begin   // SBC
            {c_out, rslt[7:0]} = {1'b0, opnd0[7:0]} - {1'b0, opnd1[7:0]} - {8'd0,cc_in[CC_C]};
            v_out = opnd0[7]!=opnd1[7] && opnd0[7]!=rslt[7];
        end
        ANDA_IMM, ANDB_IMM,
        ANDA_IDX, ANDB_IDX,
        BITA_IMM, BITB_IMM,
        BITA_IDX, BITB_IDX: begin  // AND, BIT
            rslt  = opnd0 & opnd1;
            v_out = 0;
        end
        EORA_IMM, EORB_IMM,
        EORA_IDX, EORB_IDX: begin    // EOR
            rslt  = opnd0 ^ opnd1;
            v_out = 0;
        end
        ORA_IMM, ORB_IMM,
        ORA_IDX, ORB_IDX: begin  // OR
            rslt  = opnd0 | opnd1;
            v_out = 0;
        end
        ANDCC: begin
            { e_out, f_out, h_out, i_out, n_out, z_out, v_out, c_out } = cc_in & opnd1[7:0];
        end
        ORCC: begin
            { e_out, f_out, h_out, i_out, n_out, z_out, v_out, c_out } = cc_in | opnd1[7:0];
        end
        CLRA,CLRB,CLR,CLR_NF,CLRD,CLRW: begin  // CLR, CLRD, CLRW
            rslt  = 0;
            c_out = 0;
            v_out = 0;
        end
        COMA,COMB,COM: begin  // COM
            rslt  = ~opnd0;
            c_out = 1;
            v_out = 0;
        end
        NEGA,NEGB,NEG: begin  // NEG, NEGA , NEGB
            rslt[7:0] = ~opnd0[7:0] + 8'b1;
            c_out = opnd0[7:0]!=0; // done this way to match MAME's result
            v_out = opnd0[7]==rslt[7] && opnd0[7:0]!=0;
        end
        NEGD,NEGW: begin
            rslt  = -opnd0;
            c_out = opnd0!=0;
            v_out = opnd0==16'h8000;
        end
        INCA,INCB,INC,INCD,INCW: begin
            rslt  = opnd0 + 1'b1;
            v_out = ~opnd0[msb] & rslt[msb];
        end
        DECA,DECB,DEC,DECD,DECW: begin  // DEC, DECD, DECW
            rslt  = opnd0 - 1'b1;
            v_out = opnd0[msb] & ~rslt[msb];
        end

        LSRA,LSRB,LSR: begin
            {rslt[7:0], c_out} = {1'b0, opnd0[7:0]};
        end
        LSRW: begin
            {rslt[15:0], c_out} = {1'b0, opnd0[15:0]};
        end
        RORA,RORB,ROR: begin
            {rslt[7:0], c_out} = {cc_in[CC_C], opnd0[7:0]};
        end
        RORW: begin
            {rslt[15:0], c_out} = {cc_in[CC_C], opnd0[15:0]};
        end
        ROLW: begin
            {c_out, rslt[15:0]} = {opnd0[15:0], cc_in[CC_C]};
            v_out         =  opnd0[msb] ^ rslt[msb];
        end
        ASRA,ASRB,ASR,ASRW: begin
            rslt      = opnd0>>1;
            rslt[msb] = opnd0[msb];
            c_out     = opnd0[0];
        end
        ASLA,ASLB,ASL,ASLW: begin
            rslt  = opnd0 << 1;
            c_out = opnd0[msb];
            v_out = opnd0[msb] ^ rslt[msb];
        end
        ROLA,ROLB,ROL: begin
            {c_out, rslt[7:0]} = {opnd0[7:0], cc_in[CC_C]};
        end

        ////////////// multi-shift operations on D register
        ASRD_IMM: if( shd_busy && !shd_zero ) begin
            rslt      = opnd0>>1;
            rslt[msb] = opnd0[msb];
            c_out     = opnd0[0];
        end
        LSRD_IMM: if( shd_busy && !shd_zero ) begin
            {rslt[15:0], c_out} = {1'b0, opnd0[15:0]};
        end
        ASLD_IMM: begin
            rslt  = shd_data;
            c_out = 0;
            v_out = 0;
        end
        RORD_IMM: if( shd_busy && !shd_zero ) begin
            rslt = {opnd0[0], opnd0[15:1]};
        end
        ROLD_IMM: begin
            rslt  = shd_data;
            c_out = 0;
            v_out = 0;
        end

        ////////////// multi-shift operations on 16-bit memory
        ASRD_IDX: if( shd_busy && !shd_zero ) begin
            rslt      = shd_data>>1;
            rslt[msb] = shd_data[msb];
            c_out     = shd_data[0];
        end else begin
            rslt  = shd_data;
        end
        LSRD_IDX: if( shd_busy && !shd_zero ) begin
            {rslt[15:0], c_out} = {1'b0, shd_data[15:0]};
        end else begin
            rslt  = shd_data;
        end
        ASLD_IDX: begin
            rslt  = shd_data;
            c_out = 0;
            v_out = 0;
        end
        RORD_IDX: if( shd_busy && !shd_zero ) begin
            rslt = {shd_data[0], shd_data[15:1]};
        end else begin
            rslt  = shd_data;
        end
        ROLD_IDX: begin
            rslt  = shd_data;
            c_out = 0;
            v_out = 0;
        end

        ABX: rslt =  {8'h0, opnd0[7:0]} + opnd1 ;  // ABX
        DAA: begin  // DAA
            rslt[7:0] = {cc_in[CC_C] || opnd0[7:0] > 8'h99 ? 4'h6 : 4'h0,
                         cc_in[CC_H] || opnd0[3:0] > 4'h9  ? 4'h6 : 4'h0};
            {rslt[8], rslt[7:0]} = {1'b0, opnd0[7:0]} + {1'b0, rslt[7:0]};
            h_out = ({1'b0, opnd0[3:0]} +
                     (cc_in[CC_H] || opnd0[3:0] > 4'h9 ? 5'h06 : 5'h00)) > 5'h0f;
            c_out = cc_in[CC_C] ^ rslt[8];
            v_out = 0;
        end
        SEX: begin  // SEX
            rslt  = {{8{opnd0[7]}}, opnd0[7:0]};
            v_out = 0;
        end
        MUL: begin
            rslt  = opnd0[15:8]*opnd0[7:0];
            c_out = rslt[7];
        end
        LMUL: begin
            { rslt_hi, rslt }  = opnd0*opnd1;
        end
        //
        ABSA, ABSB, ABSD: begin  // ABS
            if (opnd0[msb] )
                rslt = alu16 ? -opnd0 : {opnd0[15:8],-opnd0[7:0]};
            else
                rslt = opnd0;
            c_out = opnd0[msb];
            v_out = opnd0[msb] & rslt[msb];
        end
        DIVXB: begin
            rslt    = div_quot;
            rslt_hi = {8'd0, div_rem};
        end
        default:
            rslt = opnd0;
    endcase

    if( dec8 || dec16 ) begin // this should be moved with the DEC above
        rslt  = opnd0 - 1'b1;
        v_out = opnd0[msb] & ~rslt[msb];
    end

    if( up_z )
        z_out = alu16 ? rslt==0 : rslt[7:0]==0;
    if( up_n )
        n_out = rslt[msb];
    case (op)
        SEX:     z_out = !opnd0[7];
        ROLA, ROLB, ROL: begin
            n_out = cc_in[CC_N];
            if( cc_in[CC_C] ) z_out = cc_in[CC_Z];
        end
        LMUL:    z_out = {rslt_hi, rslt}==0;
        DIVXB:   n_out = rslt[15];
        DAA: if( cc_in[CC_C] || opnd0[7:0]>8'h99 ) begin
            n_out = cc_in[CC_N];
            z_out = cc_in[CC_Z];
        end
        default: ;
    endcase
    case (op)
        ASRD_IMM, ASRD_IDX, LSRD_IMM, LSRD_IDX, RORD_IMM, RORD_IDX:
            begin c_out = 0; v_out = 0; end
        default: ;
    endcase
end

endmodule
