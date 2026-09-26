# Physical 053248 discrepancy regressions

These cases encode individual observed PCB vectors from
[the physical measurements](../../../../doc/pcb-053248.md). They are deliberately
outside the ordinary `tests/*.asm` batch glob: six currently fail against
JTKCPU RTL. Their expected results are the measured PCB values, not an expected
failure inverted into a pass. Keep them failing until the corresponding RTL
change is reviewed and implemented.

From `ver/top`, run any case through the existing harness:

```sh
bash sim.sh --batch pcb/capture_control
bash sim.sh --batch pcb/sex
bash sim.sh --batch pcb/rol
bash sim.sh --batch pcb/lmul
bash sim.sh --batch pcb/div
bash sim.sh --batch pcb/abs
bash sim.sh --batch pcb/daa
```

The test stack is in RAM at0800. Every target is followed immediately by
`PSHS CC`; D/X/Y are then saved, and captured CC is read independently. Data
comparisons run before the CC comparison. The NOP control exercises the same
capture/check path and passes. Existing sex/andcc/orcc/pshs tests also pass.
The source comments identify the physical result file and zero-based row.

At RTL baseline e34eebf (unchanged production RTL from3dbeda8), the observed
outputs are:

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

## Proposed correction scope

Review `hdl/jtkcpu_alu.v` flag update enables and operation cases before applying
these changes. The larger physical matrices, not these six vectors alone,
support the rules:

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

A correction should make its new case pass, retain relevant existing tests,
and add any needed boundary cases from the recorded physical matrices.
Transfer encodings and timing require separate decoder/microcode work; these
flag regressions do not resolve them. No production RTL is changed here.
