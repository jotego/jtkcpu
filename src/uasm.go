package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"math"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

const (
	MAX_ROUTINE = 32 // Must be power of 2
)

type elements struct {
	labels, mnemonics map[string]int
	lbl_rev           map[int]string
}

func exists(k string, m map[string]int) bool {
	_, b := m[k]
	return b
}

func get_mnemonics(f io.Reader) (all elements, assign string) {
	scanner := bufio.NewScanner(f)
	scanner.Split(bufio.ScanLines)
	re_label := regexp.MustCompile("^[A-Z0-9_]*:")
	found := make(map[string]bool)
	lbl_cnt := 0
	all.labels = make(map[string]int)
	all.lbl_rev = make(map[int]string)

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || line[0] == '#' {
			continue
		}
		halves := strings.Split(line, "#")
		line = halves[0]
		if line == "" {
			continue
		}
		if re_label.MatchString(line) {
			halves = strings.Split(line, ":")
			lbl_name := halves[0]
			if exists(lbl_name, all.labels) {
				log.Fatal("Duplicated label ", lbl_name)
			}
			all.labels[lbl_name] = lbl_cnt
			all.lbl_rev[lbl_cnt] = lbl_name
			lbl_cnt++
			line = halves[1]
		}
		if strings.HasPrefix(strings.ToUpper(strings.TrimSpace(line)), "WAIT ") {
			continue
		}
		for _, each := range strings.Split(line, ",") {
			each = strings.TrimSpace(each)
			if each == "" || each == "NOP" {
				continue
			}
			found[each] = true
		}
	}
	all_nem := make([]string, 0)
	for k, _ := range found {
		all_nem = append(all_nem, k)
	}
	sort.Slice(all_nem, func(i, j int) bool { return all_nem[i] < all_nem[j] })
	assign = make_assign(all_nem)
	sorted := make(map[string]int)
	for k, _ := range all_nem {
		sorted[all_nem[k]] = k
	}
	all.mnemonics = sorted
	return all, assign
}

func asm(f io.Reader, all elements) (rom []uint64) {
	linecnt := 0
	scanner := bufio.NewScanner(f)
	scanner.Split(bufio.ScanLines)
	re_label := regexp.MustCompile("^[A-Z_0-9]*:")
	catBits := int(math.Ceil(math.Log2(float64(len(all.labels)))))
	rom = make([]uint64, (1<<uint(catBits))*MAX_ROUTINE)
	cur_cat := 0
	cur_catname := ""
	subidx := 0

	for scanner.Scan() {
		linecnt++
		line := strings.TrimSpace(scanner.Text())
		if line == "" || line[0] == '#' {
			continue
		}
		comment_split := strings.Split(line, "#")
		line = comment_split[0]
		line = strings.ToUpper(line)
		if re_label.MatchString(line) {
			halves := strings.Split(line, ":")
			cur_catname = halves[0]
			cur_cat = all.labels[cur_catname]
			subidx = 0
			line = halves[1]
		} else {
			subidx++
			if subidx >= (MAX_ROUTINE - 1) {
				fmt.Printf("Subroutine overflow at line %d while parsing %s\n", linecnt, cur_catname)
				os.Exit(1)
			}
		}
		if strings.HasPrefix(strings.TrimSpace(line), "WAIT ") {
			count, err := strconv.Atoi(strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(line), "WAIT ")))
			if err != nil || count < 1 || subidx+count-1 >= (MAX_ROUTINE-1) {
				log.Fatalf("Invalid wait at line %d while parsing %s", linecnt, cur_catname)
			}
			subidx += count - 1
			continue
		}
		val := uint64(0)
		for _, each := range strings.Split(line, ",") {
			each = strings.TrimSpace(each)
			if each == "" || each == "NOP" {
				continue
			}
			val |= uint64(1) << all.mnemonics[each]
		}
		addr := (cur_cat * MAX_ROUTINE) | subidx
		// if val != 0 {
		// 	fmt.Printf("%2X - %X\n",addr,val)
		// }
		rom[addr] = val
	}
	return rom
}

func tr(s string) string {
	x := strings.ToLower(s)
	if x == "ni" {
		return "ni_raw"
	}
	if strings.Index(x, "=") > -1 {
		halves := strings.Split(x, "=")
		if halves[1] == "0" {
			return "clr_" + halves[0]
		}
		if halves[1] == "1" {
			return "set_" + halves[0]
		}
		return "set_" + halves[0] + "_" + halves[1]
	}
	return x
}

func make_assign(all []string) (s string) {
	s += fmt.Sprintf("assign { ")
	first := true
	k2 := 0
	// fmt.Println(all)
	for k := len(all) - 1; k >= 0; k-- {
		if !first {
			s += ","
		}
		s += fmt.Sprintf("\n        ")
		s += fmt.Sprintf("%s", tr(all[k]))
		first = false
		k2++
	}
	s += fmt.Sprintf("\n    } = (niuzl || block_flush!=0) ? {UCODE_DW{1'b0}} : ucode;\n")
	return s
}

func dump_inc(a ...string) {
	path := "../hdl"
	f, err := os.Create(path + "/jtkcpu_ucode.inc")
	if err != nil {
		log.Fatal("Cannot open " + path)
	}
	defer f.Close()
	for _, each := range a {
		fmt.Fprintln(f, each)
	}
}

func make_case(rom []uint64, all elements) (s string) {
	nem_len := len(all.mnemonics)
	addr_len := int(math.Ceil(math.Log2(float64(len(all.labels))))) + int(math.Log2(float64(MAX_ROUTINE)))
	i := "    "
	s += fmt.Sprintf(`
always @(posedge clk,posedge rst) begin
	if(rst) begin
		ucode <= 0;
	end else if(cen) begin
	%scase( addr )`, i)
	for k, each := range rom {
		if each != 0 {
			s += fmt.Sprintf("\t%s%s%d'o%03o: ucode <= %d'h%03X;", i, i, addr_len, k, nem_len, each)
			opcat := k / MAX_ROUTINE
			if all.lbl_rev[opcat] != "" && (k%MAX_ROUTINE == 0) {
				s += fmt.Sprintf("    // %s", all.lbl_rev[opcat])
			}
			s += fmt.Sprintf("\n")
		}
	}
	s += fmt.Sprintf("\t%s%sdefault: ucode <= 0;\n\t%sendcase\n\tend\nend\n", i, i, i)
	return s
}

func make_params(all elements) (s string) {
	s += fmt.Sprintf("localparam UCODE_DW = %d;\n", len(all.mnemonics))
	s += fmt.Sprintf("localparam OPCAT_AW = %d;\n", int(math.Ceil(math.Log2(float64(len(all.labels))))))
	s += fmt.Sprintf("localparam UCODE_AW = OPCAT_AW+%d;\n\n", int(math.Log2(float64(MAX_ROUTINE))))
	s += fmt.Sprintf("reg [UCODE_DW-1:0] mem[0:(1<<UCODE_AW)-1], ucode;\n")
	s += fmt.Sprintf("reg [UCODE_AW-1:0] addr; // current ucode position read\n")
	s += fmt.Sprintf("reg [OPCAT_AW-1:0] opcat, post_idx, nx_cat, idx_cat;\n\n")
	s += fmt.Sprintf("localparam [OPCAT_AW-1:0] ")
	first := true
	sorted := make([]string, len(all.labels))
	maxlen := 0
	for k, v := range all.labels {
		sorted[v] = k
		if len(k) > maxlen {
			maxlen = len(k)
		}
	}
	fmtstr := fmt.Sprintf("\n        %%-%ds = 'o%%o", maxlen)
	for v, k := range sorted {
		if !first {
			s += fmt.Sprintf(",")
		}
		first = false
		s += fmt.Sprintf(fmtstr, k, v)
	}
	s += fmt.Sprintf(";\n")
	return
}

func main() {
	path := "../hdl/ucode"
	f, err := os.Open(path)
	if err != nil {
		log.Fatal("Cannot open " + path)
	}
	all, assign := get_mnemonics(f)
	f.Close()
	// Generate ROM
	f, _ = os.Open(path)
	defer f.Close()
	rom := asm(f, all)
	rom_case := make_case(rom, all)
	localparams := make_params(all)
	dump_inc(localparams, assign, rom_case)
}
