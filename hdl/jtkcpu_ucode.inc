localparam UCODE_DW = 61;
localparam OPCAT_AW = 7;
localparam UCODE_AW = OPCAT_AW+5;

reg [UCODE_DW-1:0] mem[0:(1<<UCODE_AW)-1], ucode;
reg [UCODE_AW-1:0] addr; // current ucode position read
reg [OPCAT_AW-1:0] opcat, post_idx, nx_cat, idx_cat;

localparam [OPCAT_AW-1:0] 
        RESET              = 'o0,
        FIRQ               = 'o1,
        IRQ                = 'o2,
        NMI                = 'o3,
        BRSWI              = 'o4,
        BUSERROR           = 'o5,
        PARSE_IDX          = 'o6,
        IDX_R              = 'o7,
        IDX_RINC           = 'o10,
        IDX_RINC2          = 'o11,
        IDX_RDEC           = 'o12,
        IDX_RDEC2          = 'o13,
        IDX_OFFSET8        = 'o14,
        IDX_OFFSET16       = 'o15,
        IDX_IND            = 'o16,
        IDX_EXT            = 'o17,
        IDX_DP             = 'o20,
        IDX_ACC            = 'o21,
        IDX_UNK            = 'o22,
        SINGLE_ALU         = 'o23,
        CMP8               = 'o24,
        CMP8_IDX           = 'o25,
        SINGLE_ALU_16      = 'o26,
        SINGLE_ALUD        = 'o27,
        SINGLE_ALUD_IDX    = 'o30,
        CMP16              = 'o31,
        CMP16_IDX          = 'o32,
        SINGLE_A_INH       = 'o33,
        DAA_TIMED          = 'o34,
        SINGLE_A5          = 'o35,
        SINGLE_B_INH       = 'o36,
        SINGLE_B5          = 'o37,
        SINGLE_ALU_INH16   = 'o40,
        SINGLE_D5          = 'o41,
        SINGLE_D6          = 'o42,
        SINGLE_D7          = 'o43,
        SINGLE_D8          = 'o44,
        SINGLE_ABX         = 'o45,
        SINGLE_ALU_IDX     = 'o46,
        SINGLE_ALU_IDX16   = 'o47,
        SHIFTD             = 'o50,
        SHIFTD_R           = 'o51,
        SHIFTD_AR          = 'o52,
        SHIFTD_IDX         = 'o53,
        SHIFTD_IDX_R       = 'o54,
        SHIFTD_IDX_AR      = 'o55,
        NOPE               = 'o56,
        MEM_ALU_IDX        = 'o57,
        DIVIDE             = 'o60,
        WMEM_ALU           = 'o61,
        WMEM_TST           = 'o62,
        WMEM_CLR           = 'o63,
        WMEM_ASL           = 'o64,
        WMEM_RIGHT         = 'o65,
        MULTIPLY           = 'o66,
        LMULTIPLY          = 'o67,
        LOOPX              = 'o70,
        LOOPB              = 'o71,
        MOVE               = 'o72,
        BMOVE_START        = 'o73,
        BMOVE              = 'o74,
        BSETA_START        = 'o75,
        BSETA              = 'o76,
        BSETD_START        = 'o77,
        BSETD              = 'o100,
        STORE8             = 'o101,
        STORE16            = 'o102,
        LEA                = 'o103,
        SETLNS             = 'o104,
        SETLNS_IDX         = 'o105,
        EXCHANGE           = 'o106,
        TRANSFER           = 'o107,
        SBRANCH            = 'o110,
        BRA11              = 'o111,
        BRN6               = 'o112,
        SBSR               = 'o113,
        BSRL               = 'o114,
        LBRANCH            = 'o115,
        LBRA13             = 'o116,
        LBRN7              = 'o117,
        JUMP               = 'o120,
        JMSR               = 'o121,
        RTIT               = 'o122,
        RTSR               = 'o123,
        PSH                = 'o124,
        PUL                = 'o125,
        MEM_ALU_NF         = 'o126,
        SINGLE_ALU9        = 'o127,
        CMP8_9             = 'o130,
        CMPD13             = 'o131,
        IDX_ACCD           = 'o132,
        MEM_ALU_CLR        = 'o133,
        MEM_ALU_OTHER      = 'o134,
        MEM_ALU_ROL        = 'o135,
        LEA05              = 'o136,
        LEA06              = 'o137,
        LEA07              = 'o140,
        SINGLE_ALU_IDX_LOG = 'o141,
        BIT8_IDX           = 'o142;

assign { 
        we,
        up_tfr,
        up_move,
        up_lmul,
        up_lines,
        up_lea,
        up_ldb,
        up_lda,
        up_ld8,
        up_ld16,
        up_exg,
        up_div,
        up_cc,
        up_abx,
        up_ab,
        uc_loop,
        shd_en,
        rti_other,
        rti_cc,
        pul_go,
        psh_pc,
        psh_go,
        psh_cc,
        psh_all,
        pc_jmp,
        set_pc_branch8,
        set_pc_branch16,
        set_opn0_mem,
        opd,
        niuz,
        ni_raw,
        memhi,
        int_en,
        incx,
        idx_ret,
        idx_pre,
        set_idx_post,
        idx_jmp,
        idx_ind,
        idx_en,
        idx_dp,
        idx_adv,
        set_idx_acc,
        idx_8,
        idx_16,
        set_idxw,
        set_i,
        set_fake_irq,
        set_f,
        set_e,
        clr_e,
        dynwait,
        div_en,
        decx,
        decu,
        decb,
        data2addr,
        buserror,
        branch_bnz,
        addry,
        addrx
    } = (niuzl || block_flush!=0) ? {UCODE_DW{1'b0}} : ucode;


always @(posedge clk,posedge rst) begin
	if(rst) begin
		ucode <= 0;
	end else if(cen) begin
	    case( addr )	        12'o000: ucode <= 61'h10005000;    // RESET
	        12'o004: ucode <= 61'h40000000;
	        12'o040: ucode <= 61'hC000000400;    // FIRQ
	        12'o041: ucode <= 61'h5000;
	        12'o043: ucode <= 61'h10005400;
	        12'o045: ucode <= 61'h200;
	        12'o046: ucode <= 61'h40000000;
	        12'o100: ucode <= 61'hA000000800;    // IRQ
	        12'o101: ucode <= 61'h4000;
	        12'o103: ucode <= 61'h10004800;
	        12'o105: ucode <= 61'h200;
	        12'o106: ucode <= 61'h40000000;
	        12'o140: ucode <= 61'hA000000800;    // NMI
	        12'o141: ucode <= 61'h5000;
	        12'o143: ucode <= 61'h10005800;
	        12'o145: ucode <= 61'h200;
	        12'o146: ucode <= 61'h40000000;
	        12'o200: ucode <= 61'h100000000;    // BRSWI
	        12'o201: ucode <= 61'h800000000;
	        12'o203: ucode <= 61'h2000;
	        12'o205: ucode <= 61'h40000000;
	        12'o240: ucode <= 61'h008;    // BUSERROR
	        12'o300: ucode <= 61'h100000000;    // PARSE_IDX
	        12'o301: ucode <= 61'h800000;
	        12'o341: ucode <= 61'h400000;
	        12'o400: ucode <= 61'h1000000;    // IDX_RINC
	        12'o401: ucode <= 61'h400000;
	        12'o440: ucode <= 61'h1008000;    // IDX_RINC2
	        12'o442: ucode <= 61'h400000;
	        12'o500: ucode <= 61'h2000000;    // IDX_RDEC
	        12'o501: ucode <= 61'h400000;
	        12'o540: ucode <= 61'h8000;    // IDX_RDEC2
	        12'o541: ucode <= 61'h2000000;
	        12'o542: ucode <= 61'h400000;
	        12'o600: ucode <= 61'h100000000;    // IDX_OFFSET8
	        12'o606: ucode <= 61'h420000;
	        12'o640: ucode <= 61'h120000000;    // IDX_OFFSET16
	        12'o641: ucode <= 61'h100000000;
	        12'o647: ucode <= 61'h410000;
	        12'o700: ucode <= 61'h20200000;    // IDX_IND
	        12'o701: ucode <= 61'h280000;
	        12'o705: ucode <= 61'h4000010;
	        12'o740: ucode <= 61'h120000000;    // IDX_EXT
	        12'o741: ucode <= 61'h100000000;
	        12'o746: ucode <= 61'h400010;
	        12'o1000: ucode <= 61'h100000000;    // IDX_DP
	        12'o1004: ucode <= 61'h500000;
	        12'o1043: ucode <= 61'h440000;
	        12'o1100: ucode <= 61'h400000;    // IDX_UNK
	        12'o1140: ucode <= 61'h100000000;    // SINGLE_ALU
	        12'o1144: ucode <= 61'h11000000000000;
	        12'o1145: ucode <= 61'h40000000;
	        12'o1200: ucode <= 61'h100000000;    // CMP8
	        12'o1204: ucode <= 61'h1000000000000;
	        12'o1205: ucode <= 61'h40000000;
	        12'o1240: ucode <= 61'h200000;    // CMP8_IDX
	        12'o1246: ucode <= 61'h1000000000000;
	        12'o1247: ucode <= 61'h40000000;
	        12'o1300: ucode <= 61'h120000000;    // SINGLE_ALU_16
	        12'o1301: ucode <= 61'h100000000;
	        12'o1310: ucode <= 61'h9000000000000;
	        12'o1311: ucode <= 61'h40000000;
	        12'o1340: ucode <= 61'h120000000;    // SINGLE_ALUD
	        12'o1341: ucode <= 61'h100000000;
	        12'o1351: ucode <= 61'h1400000000000;
	        12'o1352: ucode <= 61'h40000000;
	        12'o1400: ucode <= 61'h20200000;    // SINGLE_ALUD_IDX
	        12'o1401: ucode <= 61'h280000;
	        12'o1412: ucode <= 61'h1400000000000;
	        12'o1413: ucode <= 61'h40000000;
	        12'o1440: ucode <= 61'h120000000;    // CMP16
	        12'o1441: ucode <= 61'h100000000;
	        12'o1450: ucode <= 61'h1000000000000;
	        12'o1451: ucode <= 61'h40000000;
	        12'o1500: ucode <= 61'h20200000;    // CMP16_IDX
	        12'o1501: ucode <= 61'h280000;
	        12'o1512: ucode <= 61'h1000000000000;
	        12'o1513: ucode <= 61'h40000000;
	        12'o1540: ucode <= 61'h21000000000000;    // SINGLE_A_INH
	        12'o1541: ucode <= 61'h40000000;
	        12'o1600: ucode <= 61'h21000000000000;    // DAA_TIMED
	        12'o1601: ucode <= 61'h200;
	        12'o1602: ucode <= 61'h40000000;
	        12'o1641: ucode <= 61'h21000000000000;
	        12'o1642: ucode <= 61'h40000000;
	        12'o1700: ucode <= 61'h41000000000000;    // SINGLE_B_INH
	        12'o1701: ucode <= 61'h40000000;
	        12'o1741: ucode <= 61'h41000000000000;
	        12'o1742: ucode <= 61'h40000000;
	        12'o2000: ucode <= 61'h1400000000000;    // SINGLE_ALU_INH16
	        12'o2001: ucode <= 61'h40000000;
	        12'o2041: ucode <= 61'h1400000000000;
	        12'o2042: ucode <= 61'h40000000;
	        12'o2102: ucode <= 61'h1400000000000;
	        12'o2103: ucode <= 61'h40000000;
	        12'o2143: ucode <= 61'h1400000000000;
	        12'o2144: ucode <= 61'h40000000;
	        12'o2204: ucode <= 61'h1400000000000;
	        12'o2205: ucode <= 61'h40000000;
	        12'o2240: ucode <= 61'h800000000000;    // SINGLE_ABX
	        12'o2241: ucode <= 61'h40000000;
	        12'o2300: ucode <= 61'h200000;    // SINGLE_ALU_IDX
	        12'o2306: ucode <= 61'h11000000000000;
	        12'o2307: ucode <= 61'h40000000;
	        12'o2340: ucode <= 61'h20200000;    // SINGLE_ALU_IDX16
	        12'o2341: ucode <= 61'h280000;
	        12'o2352: ucode <= 61'h9000000000000;
	        12'o2353: ucode <= 61'h40000000;
	        12'o2400: ucode <= 61'h100000000;    // SHIFTD
	        12'o2401: ucode <= 61'h100000000000;
	        12'o2403: ucode <= 61'h1400000000000;
	        12'o2412: ucode <= 61'h40000000;
	        12'o2440: ucode <= 61'h100000000;    // SHIFTD_R
	        12'o2441: ucode <= 61'h100000000000;
	        12'o2443: ucode <= 61'h1400000000000;
	        12'o2453: ucode <= 61'h40000000;
	        12'o2500: ucode <= 61'h100000000;    // SHIFTD_AR
	        12'o2501: ucode <= 61'h100000000000;
	        12'o2503: ucode <= 61'h1400000000000;
	        12'o2515: ucode <= 61'h40000000;
	        12'o2540: ucode <= 61'h20200000;    // SHIFTD_IDX
	        12'o2541: ucode <= 61'h280000;
	        12'o2542: ucode <= 61'h100000280000;
	        12'o2544: ucode <= 61'h1000200000000;
	        12'o2545: ucode <= 61'h1000000020200000;
	        12'o2546: ucode <= 61'h1000000000280000;
	        12'o2570: ucode <= 61'h40000000;
	        12'o2600: ucode <= 61'h20200000;    // SHIFTD_IDX_R
	        12'o2601: ucode <= 61'h280000;
	        12'o2602: ucode <= 61'h100000280000;
	        12'o2604: ucode <= 61'h1000200000000;
	        12'o2605: ucode <= 61'h1000000020200000;
	        12'o2606: ucode <= 61'h1000000000280000;
	        12'o2631: ucode <= 61'h40000000;
	        12'o2640: ucode <= 61'h20200000;    // SHIFTD_IDX_AR
	        12'o2641: ucode <= 61'h280000;
	        12'o2642: ucode <= 61'h100000280000;
	        12'o2644: ucode <= 61'h1000200000000;
	        12'o2645: ucode <= 61'h1000000020200000;
	        12'o2646: ucode <= 61'h1000000000280000;
	        12'o2673: ucode <= 61'h40000000;
	        12'o2701: ucode <= 61'h40000000;
	        12'o2740: ucode <= 61'h200000;    // MEM_ALU_IDX
	        12'o2746: ucode <= 61'h1001000200200000;
	        12'o2747: ucode <= 61'h40000000;
	        12'o3000: ucode <= 61'h100;    // DIVIDE
	        12'o3003: ucode <= 61'h3000000000000;
	        12'o3004: ucode <= 61'h200;
	        12'o3005: ucode <= 61'h40000000;
	        12'o3040: ucode <= 61'h20200000;    // WMEM_ALU
	        12'o3041: ucode <= 61'h280000;
	        12'o3061: ucode <= 61'h1000000220200000;
	        12'o3062: ucode <= 61'h1001000200280000;
	        12'o3063: ucode <= 61'h40000000;
	        12'o3100: ucode <= 61'h20200000;    // WMEM_TST
	        12'o3101: ucode <= 61'h280000;
	        12'o3111: ucode <= 61'h1000000220200000;
	        12'o3112: ucode <= 61'h1001000200280000;
	        12'o3113: ucode <= 61'h40000000;
	        12'o3140: ucode <= 61'h20200000;    // WMEM_CLR
	        12'o3141: ucode <= 61'h280000;
	        12'o3152: ucode <= 61'h1000000220200000;
	        12'o3153: ucode <= 61'h1001000200280000;
	        12'o3154: ucode <= 61'h40000000;
	        12'o3200: ucode <= 61'h20200000;    // WMEM_ASL
	        12'o3201: ucode <= 61'h280000;
	        12'o3222: ucode <= 61'h1000000220200000;
	        12'o3223: ucode <= 61'h1001000200280000;
	        12'o3224: ucode <= 61'h40000000;
	        12'o3240: ucode <= 61'h20200000;    // WMEM_RIGHT
	        12'o3241: ucode <= 61'h280000;
	        12'o3263: ucode <= 61'h1000000220200000;
	        12'o3264: ucode <= 61'h1001000200280000;
	        12'o3265: ucode <= 61'h40000000;
	        12'o3314: ucode <= 61'h1400000000000;
	        12'o3315: ucode <= 61'h40000000;
	        12'o3363: ucode <= 61'h201000000000000;
	        12'o3364: ucode <= 61'h40000000;
	        12'o3400: ucode <= 61'h100000000;    // LOOPX
	        12'o3401: ucode <= 61'h1000000000080;
	        12'o3402: ucode <= 61'h004;
	        12'o3403: ucode <= 61'h40000000;
	        12'o3440: ucode <= 61'h100000000;    // LOOPB
	        12'o3441: ucode <= 61'h1000000000020;
	        12'o3442: ucode <= 61'h004;
	        12'o3443: ucode <= 61'h40000000;
	        12'o3500: ucode <= 61'h002;    // MOVE
	        12'o3501: ucode <= 61'h1400000000000001;
	        12'o3513: ucode <= 61'h40000000;
	        12'o3544: ucode <= 61'h002;
	        12'o3545: ucode <= 61'h1400000000000001;
	        12'o3551: ucode <= 61'h200000000000;
	        12'o3600: ucode <= 61'h80000000;    // BMOVE
	        12'o3602: ucode <= 61'h002;
	        12'o3603: ucode <= 61'h1400000000000001;
	        12'o3606: ucode <= 61'h200000000000;
	        12'o3643: ucode <= 61'h1000000008000041;
	        12'o3645: ucode <= 61'h200000000000;
	        12'o3700: ucode <= 61'h80000000;    // BSETA
	        12'o3701: ucode <= 61'h1000000008000041;
	        12'o3702: ucode <= 61'h200000000000;
	        12'o3744: ucode <= 61'h1000000008000041;
	        12'o3745: ucode <= 61'h1000000008000001;
	        12'o3751: ucode <= 61'h200000000000;
	        12'o4000: ucode <= 61'h80000000;    // BSETD
	        12'o4002: ucode <= 61'h1000000008000041;
	        12'o4003: ucode <= 61'h1000000008000001;
	        12'o4006: ucode <= 61'h200000000000;
	        12'o4040: ucode <= 61'h1001000000200000;    // STORE8
	        12'o4050: ucode <= 61'h40000000;
	        12'o4100: ucode <= 61'h1000000020200000;    // STORE16
	        12'o4101: ucode <= 61'h1001000000280000;
	        12'o4114: ucode <= 61'h40000000;
	        12'o4140: ucode <= 61'h81000000000000;    // LEA
	        12'o4146: ucode <= 61'h40000000;
	        12'o4200: ucode <= 61'h100000000;    // SETLNS
	        12'o4206: ucode <= 61'h100000040000000;
	        12'o4240: ucode <= 61'h200000;    // SETLNS_IDX
	        12'o4250: ucode <= 61'h100000040000000;
	        12'o4300: ucode <= 61'h100000000;    // EXCHANGE
	        12'o4304: ucode <= 61'h4000000000000;
	        12'o4305: ucode <= 61'h40000000;
	        12'o4340: ucode <= 61'h100000000;    // TRANSFER
	        12'o4344: ucode <= 61'h800000000000000;
	        12'o4345: ucode <= 61'h40000000;
	        12'o4400: ucode <= 61'h100000000;    // SBRANCH
	        12'o4401: ucode <= 61'h800000000;
	        12'o4402: ucode <= 61'h200;
	        12'o4403: ucode <= 61'h40000000;
	        12'o4440: ucode <= 61'h100000000;    // BRA11
	        12'o4441: ucode <= 61'h800000000;
	        12'o4450: ucode <= 61'h40000000;
	        12'o4500: ucode <= 61'h100000000;    // BRN6
	        12'o4501: ucode <= 61'h800000000;
	        12'o4503: ucode <= 61'h40000000;
	        12'o4540: ucode <= 61'h100000000;    // SBSR
	        12'o4541: ucode <= 61'h18000000000;
	        12'o4543: ucode <= 61'h800000000;
	        12'o4556: ucode <= 61'h40000000;
	        12'o4600: ucode <= 61'h120000000;    // BSRL
	        12'o4601: ucode <= 61'h100000000;
	        12'o4602: ucode <= 61'h18000000000;
	        12'o4604: ucode <= 61'h400000000;
	        12'o4620: ucode <= 61'h40000000;
	        12'o4640: ucode <= 61'h120000000;    // LBRANCH
	        12'o4641: ucode <= 61'h100000000;
	        12'o4642: ucode <= 61'h400000000;
	        12'o4643: ucode <= 61'h200;
	        12'o4644: ucode <= 61'h40000000;
	        12'o4700: ucode <= 61'h120000000;    // LBRA13
	        12'o4701: ucode <= 61'h100000000;
	        12'o4702: ucode <= 61'h400000000;
	        12'o4712: ucode <= 61'h40000000;
	        12'o4740: ucode <= 61'h120000000;    // LBRN7
	        12'o4741: ucode <= 61'h100000000;
	        12'o4742: ucode <= 61'h400000000;
	        12'o4744: ucode <= 61'h40000000;
	        12'o5000: ucode <= 61'h1000000000;    // JUMP
	        12'o5003: ucode <= 61'h40000000;
	        12'o5040: ucode <= 61'h18000000000;    // JMSR
	        12'o5042: ucode <= 61'h1000000000;
	        12'o5053: ucode <= 61'h40000000;
	        12'o5100: ucode <= 61'h60000000000;    // RTIT
	        12'o5102: ucode <= 61'hA0000000000;
	        12'o5104: ucode <= 61'h200;
	        12'o5105: ucode <= 61'h40000000;
	        12'o5140: ucode <= 61'h30000000000;    // RTSR
	        12'o5151: ucode <= 61'h40000000;
	        12'o5200: ucode <= 61'h100000000;    // PSH
	        12'o5201: ucode <= 61'h8000000000;
	        12'o5204: ucode <= 61'h200;
	        12'o5205: ucode <= 61'h40000000;
	        12'o5240: ucode <= 61'h100000000;    // PUL
	        12'o5241: ucode <= 61'h20000000000;
	        12'o5244: ucode <= 61'h200;
	        12'o5245: ucode <= 61'h40000000;
	        12'o5300: ucode <= 61'h200000;    // MEM_ALU_NF
	        12'o5307: ucode <= 61'h1000000200200000;
	        12'o5310: ucode <= 61'h40000000;
	        12'o5340: ucode <= 61'h100000000;    // SINGLE_ALU9
	        12'o5345: ucode <= 61'h11000000000000;
	        12'o5346: ucode <= 61'h40000000;
	        12'o5400: ucode <= 61'h100000000;    // CMP8_9
	        12'o5405: ucode <= 61'h1000000000000;
	        12'o5406: ucode <= 61'h40000000;
	        12'o5440: ucode <= 61'h120000000;    // CMPD13
	        12'o5441: ucode <= 61'h100000000;
	        12'o5451: ucode <= 61'h1000000000000;
	        12'o5452: ucode <= 61'h40000000;
	        12'o5505: ucode <= 61'h440000;
	        12'o5540: ucode <= 61'h200000;    // MEM_ALU_CLR
	        12'o5547: ucode <= 61'h1001000200200000;
	        12'o5550: ucode <= 61'h40000000;
	        12'o5600: ucode <= 61'h200000;    // MEM_ALU_OTHER
	        12'o5612: ucode <= 61'h1001000200200000;
	        12'o5613: ucode <= 61'h40000000;
	        12'o5640: ucode <= 61'h200000;    // MEM_ALU_ROL
	        12'o5653: ucode <= 61'h1001000200200000;
	        12'o5654: ucode <= 61'h40000000;
	        12'o5700: ucode <= 61'h81000000000000;    // LEA05
	        12'o5714: ucode <= 61'h40000000;
	        12'o5740: ucode <= 61'h81000000000000;    // LEA06
	        12'o5752: ucode <= 61'h40000000;
	        12'o6000: ucode <= 61'h81000000000000;    // LEA07
	        12'o6010: ucode <= 61'h40000000;
	        12'o6040: ucode <= 61'h200000;    // SINGLE_ALU_IDX_LOG
	        12'o6047: ucode <= 61'h11000000000000;
	        12'o6050: ucode <= 61'h40000000;
	        12'o6100: ucode <= 61'h200000;    // BIT8_IDX
	        12'o6107: ucode <= 61'h1000000000000;
	        12'o6110: ucode <= 61'h40000000;
	        default: ucode <= 0;
	    endcase
	end
end

