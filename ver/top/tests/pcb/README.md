# Physical 053248 discrepancy regressions

These cases encode observed PCB vectors from
[the physical measurements](../../../../doc/pcb-053248.md). They are outside
the ordinary `tests/*.asm` batch glob. Their expected results are measured PCB
values. Issue #4 implements the six initial flag corrections, the word-NEG
flag correction found during the final audit, and opcode and transfer tests.

From `ver/top`, run any case through the existing harness:

```sh
bash sim.sh --batch pcb/capture_control
bash sim.sh --batch pcb/sex
bash sim.sh --batch pcb/rol
bash sim.sh --batch pcb/lmul
bash sim.sh --batch pcb/div
bash sim.sh --batch pcb/abs
bash sim.sh --batch pcb/neg_word
bash sim.sh --batch pcb/daa
bash sim.sh --batch pcb/new_opcodes
bash sim.sh --batch pcb/transfer_map
bash sim.sh --batch pcb/transfer_pc
bash sim.sh --batch pcb/transfer_pc_stream
bash sim.sh --batch pcb/lea_zero_loop
bash sim.sh --batch pcb/soft_reset
bash sim.sh --batch pcb/soft_nmi
bash sim.sh --batch pcb/soft_firq
bash sim.sh --batch pcb/soft_irq
bash sim.sh --batch pcb/soft_swi
bash sim.sh --batch pcb/varshift_left
bash sim.sh --batch pcb/varshift_right
bash sim.sh --batch pcb/block_flags
```

The test stack is in RAM at0800. Every target is followed immediately by
`PSHS CC`; D/X/Y are then saved, and captured CC is read independently. Data
comparisons run before the CC comparison. The NOP control exercises the same
capture/check path and passes. Existing sex/andcc/orcc/pshs tests also pass.
The source comments identify the physical result file and zero-based row.

At RTL baseline e34eebf (unchanged production RTL from 3dbeda8), the six
flag cases failed as follows. They now pass with the issue #4 corrections:

| Case | Target input | Data result, PCB and RTL agree | PCB CC | RTL CC |
| --- | --- | --- | --- | --- |
| SEX | D5A01, CC00 | D0001 | 04 | 00 |
| ROLA | DFFA5, CC05 | DFFA5 | 05 | 09 |
| LMUL | X8000, Y0001, CC01 | X0000:Y8000 | 01 | 04 |
| DIV X,B | X8000, B01, CC01 | X8000, B00 | 09 | 01 |
| ABSA | D00A5, CC01 | D00A5 | 04 | 00 |
| DAA | D00A5, CC21 | D66A5 | 01 | 21 |

The complete D/X/Y values agree in every case. The LMUL vector exposes both
Z and C differences: a nonzero32-bit product with zero high word must not set Z,
and incoming C persists on the PCB. Host extraction from the existing harness's
RAM-write log verifies these mismatches rather than inferring the failure cause
from a generic FAIL message.

## Implemented flag corrections

The larger physical matrices, not these six vectors alone, support the rules:

- SEX: Z follows the generated sign-extension byte, not the full D result.
- Byte ROL: preserve N/V; preserve Z when incoming C is set, otherwise use
  result-zero. Do not apply this rule to fixed-word or variable-word rotates.
- LMUL: Z covers the complete32-bit product; preserve incoming C.
- DIV: update N from quotient bit15; preserve flags other than N/Z in the
  measured cases. Preserve the separately documented zero-divisor behavior.
- ABS: update Z from the result and C from the original sign; retain the
  measured minimum-negative overflow behavior.
- DAA: H is the low-correction carry; use the measured conditional N/Z and
  C rules in the research document, rather than treating H as preserved.

The new opcode case covers LEAX 05-07 and flag-preserving CLR.NF. The transfer
case covers both primary bytes with bit-7-selected copy/exchange and the full
DP-related word. The PC transfer case checks PC readback and branch to a new
instruction stream. The stream case checks all four measured PC-exchange
encodings: one opcode comes from the old continuation, while an operand for
that opcode comes from the new destination. The LEAX loop case checks Z at a zero result and BNE
fall-through. The software entry cases cover each discovered entry opcode
and the saved return address. Timing measurements are tracked separately.
The variable-shift cases check zero-count data preservation, selected count
boundaries, 16-bit rotation independent of incoming C, and N/Z/V/C against
the physical shift-vector matrix.
The block case checks that Z follows the final U value and that one-element
operations leave bytes beyond the destination untouched.
The word-NEG case checks zero, positive, most-negative and minus-one inputs
against the measured N/Z/V/C rule, including a memory operand.
