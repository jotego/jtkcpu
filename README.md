# JTKCPU

Verilog core compatible with Konami's 052001 and 052526. The later supports more instructions, but the exact distinction among the two CPUs is not clear.

You can show your appreciation through
* [Patreon](https://patreon.com/jotego), by supporting releases
* [Paypal](https://paypal.me/topapate), with a donation

# Assembler

[Alfred Arnold's assembler](http://john.ccac.rwth-aachen.de:8000/as/index.html) supports the 052001 instruction set. The [top-level simulations](ver/top/sim.sh) expect this assembler in the system to run the unit tests.

# Game Library

The following games used the 052001 CPU as the main or sound processor. The set names and source files refer to the MAME emulator

| Games                                 | Setname  | Source       | Audio                    | CPUs              | Video                  | Sch           |
|:--------------------------------------|:---------|:-------------|:-------------------------|:------------------|:-----------------------|:--------------|
| '88 Games                             | 88games  | 88games.cpp  | YM2151,          uPD7759 | KCPU, Z80         |                        | Yes, original |
| Ajax                                  | ajax     | ajax.cpp     | YM2151, K007232          | 052001,Z80,HD6309 | K051960-52109, K051316 | Yes, original |
| Aliens (World set 1)                  | aliens   | aliens.cpp   | YM2151, K007232          | KCPU, Z80         | K051960-52109          | Yes, pdf      |
| Block Hole / Quarth (Japan)           | blockhl  | blockhl.cpp  | YM2151                   | KCPU, Z80         | K051960-52109          | No            |
| Chequered Flag                        | chqflag  | chqflag.cpp  | YM2151, K007232          | 052001, Z80       | K051316-51960, K051316 | No            |
| Crazy Cop (Japan)                     | crazycop | thunderx.cpp | YM2151, K007232          | 052256, Z80       | K051960-52109          | No            |
| Crime Fighters (World 2 players)      | crimfght | crimfght.cpp | YM2151, K007232          | K52001, Z80       | K051960-52109          | Yes           |
| Escape Kids (Asia, 4 Players)         | esckids  | vendetta.cpp | YM2151,          K053260 | 053248, Z80       | K053247-52109          | No            |
| Gang Busters (set 1)                  | gbusters | thunderx.cpp | YM2151, K007232          | KCPU, Z80         |                        | No            |
| Haunted Castle (version M)            | hcastle  | hcastle.cpp  | YM3812, K007232, K051649 | 052001, Z80       | K007121                | Yes, pdf      |
| Parodius DA! (World, set 1)           | parodius | parodius.cpp | YM2151,          K053260 | KCPU, Z80         | K053245-52109          | No, (pcb)     |
| Rollergames (US)                      | rollerg  | rollerg.cpp  | YM3812,          K053260 | KCPU, Z80         |                        | No            |
| Super Contra (set 1)                  | scontra  | thunderx.cpp | YM2151, K007232          | KCPU, Z80         | K051960-52109          | Yes, pdf      |
| The Simpsons (4 Players World, set 1) | simpsons | simpsons.cpp | YM2151,          K053260 | KCPU, Z80         | K053247-52109          | Yes, pdf      |
| Surprise Attack (World ver. K)        | suratk   | surpratk.cpp | YM2151                   | KCPU              | K051962-52109,K053245  | No            |
| Thunder Cross (set 1)                 | thunderx | thunderx.cpp | YM2151                   | KCPU, Z80         | K051960-52109          | Yes, pdf      |
| Vendetta (World, 4 Players, ver. T)   | vendetta | vendetta.cpp | YM2151,          K053260 | KCPU, Z80         | K053247-52109          | Yes, pdf      |

# Resource Usage
Compiled on a Cyclone III EP3C25 (the FPGA in MiST), resource usage is:

Item            | Usage
----------------|---------
Logic Elements  |  2,290
Memory bits     | 12,800
Multipliers     |      3

Fmax > 70 MHz

# Current Issue

The CPU is not finishing processes during blanking, leading to some gaps in lines (reported in [#787](https://github.com/jotego/jtcores/issues/787))

(29/11/2024)
Using the 96MHz clock, the ALU is not able to finish calculations in time, leading to compilation errors.

To fix this, I tried registering the result obtained in the ALU and delaying other processes adding one clock enable before the result is stored. I tried this through the alu_busy signal, but this does not stop the count of addr in the ucode module.
Important signals like ni (new instruction) are dependent on the addr value, and, for shorter programs, for example, trying to add a cen cycle this ways leads to ni activating before the correct ALU-result can be stored.

Without delaying the rest of the CPU, the slack obtained in the timing report for compiling registering while registering the ALU outputs on a flip flop is -5.382 ns. The report indicated issues with z_out in cc_out, so we tried registering everything else but that bit, solving that issue but letting others show up.

Using another approach to decrease calculation time, I tried simplifying the ALU mux by unifying all op values leading to the same calculations in a single register that enables or disables the processes in continuous assignment. Setup slack obtained was around -6.437, indicating that this registration of op should probably be also done in other modules for this to work.

It would entail several changes for the CPU to work at 96MHz, meanwhile, it is being used in other games without problems with 48 MHz. We will try the other approach (working with cen==1), to check if it might be a better solution


(20/12/2024)   
In the branch `cenwait` in commit [45926b7](https://github.com/jotego/jtkcpu/commit/45926b7e8d73635d0c763741c381e546a738fc6d), we can find another approach to solve the issue. With these small changes, the cpu can also run using a fixed or variable cen input.

The jtframe_gated_cen module usually compensates pauses after a busy state with a faster cen output to keep the average as intended. However, when the intended cen is half of the clock's frequency (as it is the case in mentioned #787), this compensation is not possible, due to it being designed to not send out two cen signals in a row. To test the changes applied in the mentioned commit, a similar approach removing the blockage has been used, so several cen output signals can be active in a row if necessary.

In `cenwait` ([45926b7](https://github.com/jotego/jtkcpu/commit/45926b7e8d73635d0c763741c381e546a738fc6d)), when input cen==1, a wait state is added every time the address is changed. This allows the processes in the ALU to finish before the next cen/cen2 cycle. Nevertheless, always adding a wait state independently from the operation causes only ~10% speed increase for a 48MHz 100% duty cycle clock versus a 48MHz 50% duty cycle (cen=50%) case. The wait states take away most of the gain from doubling the duty cycle. This is not enough to fix the issue reported in #787
