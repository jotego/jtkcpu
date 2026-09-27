localparam UCODE_DW = 64;
localparam OPCAT_AW = 7;
localparam UCODE_AW = OPCAT_AW+4;

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
        BIT8_IDX           = 'o142,
        WAIT8              = 'o143,
        WAIT16             = 'o144;

assign { 
        we,
        wait_ret,
        wait8_call,
        wait16_call,
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
	    case( addr )	        11'o000: ucode <= 64'h10005000;    // RESET
	        11'o004: ucode <= 64'h40000000;
	        11'o020: ucode <= 64'hC000000400;    // FIRQ
	        11'o021: ucode <= 64'h5000;
	        11'o023: ucode <= 64'h10005400;
	        11'o025: ucode <= 64'h200;
	        11'o026: ucode <= 64'h40000000;
	        11'o040: ucode <= 64'hA000000800;    // IRQ
	        11'o041: ucode <= 64'h4000;
	        11'o043: ucode <= 64'h10004800;
	        11'o045: ucode <= 64'h200;
	        11'o046: ucode <= 64'h40000000;
	        11'o060: ucode <= 64'hA000000800;    // NMI
	        11'o061: ucode <= 64'h5000;
	        11'o063: ucode <= 64'h10005800;
	        11'o065: ucode <= 64'h200;
	        11'o066: ucode <= 64'h40000000;
	        11'o100: ucode <= 64'h100000000;    // BRSWI
	        11'o101: ucode <= 64'h800000000;
	        11'o103: ucode <= 64'h2000;
	        11'o105: ucode <= 64'h40000000;
	        11'o120: ucode <= 64'h008;    // BUSERROR
	        11'o140: ucode <= 64'h100000000;    // PARSE_IDX
	        11'o141: ucode <= 64'h800000;
	        11'o161: ucode <= 64'h400000;
	        11'o200: ucode <= 64'h1000000;    // IDX_RINC
	        11'o201: ucode <= 64'h400000;
	        11'o220: ucode <= 64'h1008000;    // IDX_RINC2
	        11'o222: ucode <= 64'h400000;
	        11'o240: ucode <= 64'h2000000;    // IDX_RDEC
	        11'o241: ucode <= 64'h400000;
	        11'o260: ucode <= 64'h8000;    // IDX_RDEC2
	        11'o261: ucode <= 64'h2000000;
	        11'o262: ucode <= 64'h400000;
	        11'o300: ucode <= 64'h100000000;    // IDX_OFFSET8
	        11'o306: ucode <= 64'h420000;
	        11'o320: ucode <= 64'h120000000;    // IDX_OFFSET16
	        11'o321: ucode <= 64'h100000000;
	        11'o327: ucode <= 64'h410000;
	        11'o340: ucode <= 64'h20200000;    // IDX_IND
	        11'o341: ucode <= 64'h280000;
	        11'o345: ucode <= 64'h4000010;
	        11'o360: ucode <= 64'h120000000;    // IDX_EXT
	        11'o361: ucode <= 64'h100000000;
	        11'o366: ucode <= 64'h400010;
	        11'o400: ucode <= 64'h100000000;    // IDX_DP
	        11'o404: ucode <= 64'h500000;
	        11'o423: ucode <= 64'h440000;
	        11'o440: ucode <= 64'h400000;    // IDX_UNK
	        11'o460: ucode <= 64'h100000000;    // SINGLE_ALU
	        11'o464: ucode <= 64'h11000000000000;
	        11'o465: ucode <= 64'h40000000;
	        11'o500: ucode <= 64'h100000000;    // CMP8
	        11'o504: ucode <= 64'h1000000000000;
	        11'o505: ucode <= 64'h40000000;
	        11'o520: ucode <= 64'h200000;    // CMP8_IDX
	        11'o526: ucode <= 64'h1000000000000;
	        11'o527: ucode <= 64'h40000000;
	        11'o540: ucode <= 64'h120000000;    // SINGLE_ALU_16
	        11'o541: ucode <= 64'h100000000;
	        11'o550: ucode <= 64'h9000000000000;
	        11'o551: ucode <= 64'h40000000;
	        11'o560: ucode <= 64'h120000000;    // SINGLE_ALUD
	        11'o561: ucode <= 64'h100000000;
	        11'o571: ucode <= 64'h1400000000000;
	        11'o572: ucode <= 64'h40000000;
	        11'o600: ucode <= 64'h20200000;    // SINGLE_ALUD_IDX
	        11'o601: ucode <= 64'h280000;
	        11'o602: ucode <= 64'h2000000000000000;
	        11'o604: ucode <= 64'h1400000000000;
	        11'o605: ucode <= 64'h40000000;
	        11'o620: ucode <= 64'h120000000;    // CMP16
	        11'o621: ucode <= 64'h100000000;
	        11'o630: ucode <= 64'h1000000000000;
	        11'o631: ucode <= 64'h40000000;
	        11'o640: ucode <= 64'h20200000;    // CMP16_IDX
	        11'o641: ucode <= 64'h280000;
	        11'o642: ucode <= 64'h2000000000000000;
	        11'o644: ucode <= 64'h1000000000000;
	        11'o645: ucode <= 64'h40000000;
	        11'o660: ucode <= 64'h21000000000000;    // SINGLE_A_INH
	        11'o661: ucode <= 64'h40000000;
	        11'o700: ucode <= 64'h21000000000000;    // DAA_TIMED
	        11'o701: ucode <= 64'h200;
	        11'o702: ucode <= 64'h40000000;
	        11'o721: ucode <= 64'h21000000000000;
	        11'o722: ucode <= 64'h40000000;
	        11'o740: ucode <= 64'h41000000000000;    // SINGLE_B_INH
	        11'o741: ucode <= 64'h40000000;
	        11'o761: ucode <= 64'h41000000000000;
	        11'o762: ucode <= 64'h40000000;
	        11'o1000: ucode <= 64'h1400000000000;    // SINGLE_ALU_INH16
	        11'o1001: ucode <= 64'h40000000;
	        11'o1021: ucode <= 64'h1400000000000;
	        11'o1022: ucode <= 64'h40000000;
	        11'o1042: ucode <= 64'h1400000000000;
	        11'o1043: ucode <= 64'h40000000;
	        11'o1063: ucode <= 64'h1400000000000;
	        11'o1064: ucode <= 64'h40000000;
	        11'o1104: ucode <= 64'h1400000000000;
	        11'o1105: ucode <= 64'h40000000;
	        11'o1120: ucode <= 64'h800000000000;    // SINGLE_ABX
	        11'o1121: ucode <= 64'h40000000;
	        11'o1140: ucode <= 64'h200000;    // SINGLE_ALU_IDX
	        11'o1146: ucode <= 64'h11000000000000;
	        11'o1147: ucode <= 64'h40000000;
	        11'o1160: ucode <= 64'h20200000;    // SINGLE_ALU_IDX16
	        11'o1161: ucode <= 64'h280000;
	        11'o1162: ucode <= 64'h2000000000000000;
	        11'o1164: ucode <= 64'h9000000000000;
	        11'o1165: ucode <= 64'h40000000;
	        11'o1200: ucode <= 64'h100000000;    // SHIFTD
	        11'o1201: ucode <= 64'h100000000000;
	        11'o1203: ucode <= 64'h1400000000000;
	        11'o1212: ucode <= 64'h40000000;
	        11'o1220: ucode <= 64'h100000000;    // SHIFTD_R
	        11'o1221: ucode <= 64'h100000000000;
	        11'o1223: ucode <= 64'h1400000000000;
	        11'o1233: ucode <= 64'h40000000;
	        11'o1240: ucode <= 64'h100000000;    // SHIFTD_AR
	        11'o1241: ucode <= 64'h100000000000;
	        11'o1243: ucode <= 64'h1400000000000;
	        11'o1244: ucode <= 64'h2000000000000000;
	        11'o1247: ucode <= 64'h40000000;
	        11'o1260: ucode <= 64'h20200000;    // SHIFTD_IDX
	        11'o1261: ucode <= 64'h280000;
	        11'o1262: ucode <= 64'h100000280000;
	        11'o1264: ucode <= 64'h1000200000000;
	        11'o1265: ucode <= 64'h8000000020200000;
	        11'o1266: ucode <= 64'h8000000000280000;
	        11'o1267: ucode <= 64'h1000000000000000;
	        11'o1272: ucode <= 64'h40000000;
	        11'o1300: ucode <= 64'h20200000;    // SHIFTD_IDX_R
	        11'o1301: ucode <= 64'h280000;
	        11'o1302: ucode <= 64'h100000280000;
	        11'o1304: ucode <= 64'h1000200000000;
	        11'o1305: ucode <= 64'h8000000020200000;
	        11'o1306: ucode <= 64'h8000000000280000;
	        11'o1307: ucode <= 64'h1000000000000000;
	        11'o1313: ucode <= 64'h40000000;
	        11'o1320: ucode <= 64'h20200000;    // SHIFTD_IDX_AR
	        11'o1321: ucode <= 64'h280000;
	        11'o1322: ucode <= 64'h100000280000;
	        11'o1324: ucode <= 64'h1000200000000;
	        11'o1325: ucode <= 64'h8000000020200000;
	        11'o1326: ucode <= 64'h8000000000280000;
	        11'o1327: ucode <= 64'h1000000000000000;
	        11'o1335: ucode <= 64'h40000000;
	        11'o1341: ucode <= 64'h40000000;
	        11'o1360: ucode <= 64'h200000;    // MEM_ALU_IDX
	        11'o1366: ucode <= 64'h8001000200200000;
	        11'o1367: ucode <= 64'h40000000;
	        11'o1400: ucode <= 64'h100;    // DIVIDE
	        11'o1403: ucode <= 64'h3000000000000;
	        11'o1404: ucode <= 64'h200;
	        11'o1405: ucode <= 64'h40000000;
	        11'o1420: ucode <= 64'h20200000;    // WMEM_ALU
	        11'o1421: ucode <= 64'h280000;
	        11'o1422: ucode <= 64'h2000000000000000;
	        11'o1433: ucode <= 64'h8000000220200000;
	        11'o1434: ucode <= 64'h8001000200280000;
	        11'o1435: ucode <= 64'h40000000;
	        11'o1440: ucode <= 64'h20200000;    // WMEM_TST
	        11'o1441: ucode <= 64'h280000;
	        11'o1451: ucode <= 64'h8000000220200000;
	        11'o1452: ucode <= 64'h8001000200280000;
	        11'o1453: ucode <= 64'h40000000;
	        11'o1460: ucode <= 64'h20200000;    // WMEM_CLR
	        11'o1461: ucode <= 64'h280000;
	        11'o1462: ucode <= 64'h2000000000000000;
	        11'o1464: ucode <= 64'h8000000220200000;
	        11'o1465: ucode <= 64'h8001000200280000;
	        11'o1466: ucode <= 64'h40000000;
	        11'o1500: ucode <= 64'h20200000;    // WMEM_ASL
	        11'o1501: ucode <= 64'h280000;
	        11'o1502: ucode <= 64'h1000000000000000;
	        11'o1504: ucode <= 64'h8000000220200000;
	        11'o1505: ucode <= 64'h8001000200280000;
	        11'o1506: ucode <= 64'h40000000;
	        11'o1520: ucode <= 64'h20200000;    // WMEM_RIGHT
	        11'o1521: ucode <= 64'h280000;
	        11'o1522: ucode <= 64'h1000000000000000;
	        11'o1525: ucode <= 64'h8000000220200000;
	        11'o1526: ucode <= 64'h8001000200280000;
	        11'o1527: ucode <= 64'h40000000;
	        11'o1541: ucode <= 64'h2000000000000000;
	        11'o1546: ucode <= 64'h1400000000000;
	        11'o1547: ucode <= 64'h40000000;
	        11'o1561: ucode <= 64'h1000000000000000;
	        11'o1565: ucode <= 64'h201000000000000;
	        11'o1566: ucode <= 64'h40000000;
	        11'o1600: ucode <= 64'h100000000;    // LOOPX
	        11'o1601: ucode <= 64'h1000000000080;
	        11'o1602: ucode <= 64'h004;
	        11'o1603: ucode <= 64'h40000000;
	        11'o1620: ucode <= 64'h100000000;    // LOOPB
	        11'o1621: ucode <= 64'h1000000000020;
	        11'o1622: ucode <= 64'h004;
	        11'o1623: ucode <= 64'h40000000;
	        11'o1640: ucode <= 64'h002;    // MOVE
	        11'o1641: ucode <= 64'h8400000000000001;
	        11'o1642: ucode <= 64'h2000000000000000;
	        11'o1645: ucode <= 64'h40000000;
	        11'o1664: ucode <= 64'h002;
	        11'o1665: ucode <= 64'h8400000000000001;
	        11'o1671: ucode <= 64'h200000000000;
	        11'o1700: ucode <= 64'h80000000;    // BMOVE
	        11'o1702: ucode <= 64'h002;
	        11'o1703: ucode <= 64'h8400000000000001;
	        11'o1706: ucode <= 64'h200000000000;
	        11'o1723: ucode <= 64'h8000000008000041;
	        11'o1725: ucode <= 64'h200000000000;
	        11'o1740: ucode <= 64'h80000000;    // BSETA
	        11'o1741: ucode <= 64'h8000000008000041;
	        11'o1742: ucode <= 64'h200000000000;
	        11'o1764: ucode <= 64'h8000000008000041;
	        11'o1765: ucode <= 64'h8000000008000001;
	        11'o1771: ucode <= 64'h200000000000;
	        11'o2000: ucode <= 64'h80000000;    // BSETD
	        11'o2002: ucode <= 64'h8000000008000041;
	        11'o2003: ucode <= 64'h8000000008000001;
	        11'o2006: ucode <= 64'h200000000000;
	        11'o2020: ucode <= 64'h8001000000200000;    // STORE8
	        11'o2030: ucode <= 64'h40000000;
	        11'o2040: ucode <= 64'h8000000020200000;    // STORE16
	        11'o2041: ucode <= 64'h8001000000280000;
	        11'o2042: ucode <= 64'h2000000000000000;
	        11'o2046: ucode <= 64'h40000000;
	        11'o2060: ucode <= 64'h81000000000000;    // LEA
	        11'o2066: ucode <= 64'h40000000;
	        11'o2100: ucode <= 64'h100000000;    // SETLNS
	        11'o2106: ucode <= 64'h100000040000000;
	        11'o2120: ucode <= 64'h200000;    // SETLNS_IDX
	        11'o2130: ucode <= 64'h100000040000000;
	        11'o2140: ucode <= 64'h100000000;    // EXCHANGE
	        11'o2144: ucode <= 64'h4000000000000;
	        11'o2145: ucode <= 64'h40000000;
	        11'o2160: ucode <= 64'h100000000;    // TRANSFER
	        11'o2164: ucode <= 64'h800000000000000;
	        11'o2165: ucode <= 64'h40000000;
	        11'o2200: ucode <= 64'h100000000;    // SBRANCH
	        11'o2201: ucode <= 64'h800000000;
	        11'o2202: ucode <= 64'h200;
	        11'o2203: ucode <= 64'h40000000;
	        11'o2220: ucode <= 64'h100000000;    // BRA11
	        11'o2221: ucode <= 64'h800000000;
	        11'o2230: ucode <= 64'h40000000;
	        11'o2240: ucode <= 64'h100000000;    // BRN6
	        11'o2241: ucode <= 64'h800000000;
	        11'o2243: ucode <= 64'h40000000;
	        11'o2260: ucode <= 64'h100000000;    // SBSR
	        11'o2261: ucode <= 64'h18000000000;
	        11'o2263: ucode <= 64'h800000000;
	        11'o2264: ucode <= 64'h2000000000000000;
	        11'o2270: ucode <= 64'h40000000;
	        11'o2300: ucode <= 64'h120000000;    // BSRL
	        11'o2301: ucode <= 64'h100000000;
	        11'o2302: ucode <= 64'h18000000000;
	        11'o2304: ucode <= 64'h400000000;
	        11'o2305: ucode <= 64'h2000000000000000;
	        11'o2312: ucode <= 64'h40000000;
	        11'o2320: ucode <= 64'h120000000;    // LBRANCH
	        11'o2321: ucode <= 64'h100000000;
	        11'o2322: ucode <= 64'h400000000;
	        11'o2323: ucode <= 64'h200;
	        11'o2324: ucode <= 64'h40000000;
	        11'o2340: ucode <= 64'h120000000;    // LBRA13
	        11'o2341: ucode <= 64'h100000000;
	        11'o2342: ucode <= 64'h400000000;
	        11'o2352: ucode <= 64'h40000000;
	        11'o2360: ucode <= 64'h120000000;    // LBRN7
	        11'o2361: ucode <= 64'h100000000;
	        11'o2362: ucode <= 64'h400000000;
	        11'o2364: ucode <= 64'h40000000;
	        11'o2400: ucode <= 64'h1000000000;    // JUMP
	        11'o2403: ucode <= 64'h40000000;
	        11'o2420: ucode <= 64'h18000000000;    // JMSR
	        11'o2422: ucode <= 64'h1000000000;
	        11'o2423: ucode <= 64'h2000000000000000;
	        11'o2425: ucode <= 64'h40000000;
	        11'o2440: ucode <= 64'h60000000000;    // RTIT
	        11'o2442: ucode <= 64'hA0000000000;
	        11'o2444: ucode <= 64'h200;
	        11'o2445: ucode <= 64'h40000000;
	        11'o2460: ucode <= 64'h30000000000;    // RTSR
	        11'o2471: ucode <= 64'h40000000;
	        11'o2500: ucode <= 64'h100000000;    // PSH
	        11'o2501: ucode <= 64'h8000000000;
	        11'o2504: ucode <= 64'h200;
	        11'o2505: ucode <= 64'h40000000;
	        11'o2520: ucode <= 64'h100000000;    // PUL
	        11'o2521: ucode <= 64'h20000000000;
	        11'o2524: ucode <= 64'h200;
	        11'o2525: ucode <= 64'h40000000;
	        11'o2540: ucode <= 64'h200000;    // MEM_ALU_NF
	        11'o2547: ucode <= 64'h8000000200200000;
	        11'o2550: ucode <= 64'h40000000;
	        11'o2560: ucode <= 64'h100000000;    // SINGLE_ALU9
	        11'o2565: ucode <= 64'h11000000000000;
	        11'o2566: ucode <= 64'h40000000;
	        11'o2600: ucode <= 64'h100000000;    // CMP8_9
	        11'o2605: ucode <= 64'h1000000000000;
	        11'o2606: ucode <= 64'h40000000;
	        11'o2620: ucode <= 64'h120000000;    // CMPD13
	        11'o2621: ucode <= 64'h100000000;
	        11'o2631: ucode <= 64'h1000000000000;
	        11'o2632: ucode <= 64'h40000000;
	        11'o2645: ucode <= 64'h440000;
	        11'o2660: ucode <= 64'h200000;    // MEM_ALU_CLR
	        11'o2667: ucode <= 64'h8001000200200000;
	        11'o2670: ucode <= 64'h40000000;
	        11'o2700: ucode <= 64'h200000;    // MEM_ALU_OTHER
	        11'o2701: ucode <= 64'h2000000000000000;
	        11'o2704: ucode <= 64'h8001000200200000;
	        11'o2705: ucode <= 64'h40000000;
	        11'o2720: ucode <= 64'h200000;    // MEM_ALU_ROL
	        11'o2721: ucode <= 64'h2000000000000000;
	        11'o2725: ucode <= 64'h8001000200200000;
	        11'o2726: ucode <= 64'h40000000;
	        11'o2740: ucode <= 64'h81000000000000;    // LEA05
	        11'o2741: ucode <= 64'h2000000000000000;
	        11'o2746: ucode <= 64'h40000000;
	        11'o2760: ucode <= 64'h81000000000000;    // LEA06
	        11'o2761: ucode <= 64'h2000000000000000;
	        11'o2764: ucode <= 64'h40000000;
	        11'o3000: ucode <= 64'h81000000000000;    // LEA07
	        11'o3010: ucode <= 64'h40000000;
	        11'o3020: ucode <= 64'h200000;    // SINGLE_ALU_IDX_LOG
	        11'o3027: ucode <= 64'h11000000000000;
	        11'o3030: ucode <= 64'h40000000;
	        11'o3040: ucode <= 64'h200000;    // BIT8_IDX
	        11'o3047: ucode <= 64'h1000000000000;
	        11'o3050: ucode <= 64'h40000000;
	        11'o3064: ucode <= 64'h4000000000000000;
	        11'o3114: ucode <= 64'h4000000000000000;
	        default: ucode <= 0;
	    endcase
	end
end

