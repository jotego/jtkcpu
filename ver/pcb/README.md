# Physical 053248 characterization on Vendetta

These sources reproduce the POG PicoROM transport, timing and flag probes used
for [JTKCPU issue1](http://gitea.jotego.es/jotego/jtkcpu/issues/1) and the
[unknown-opcode investigation](http://gitea.jotego.es/jotego/jtkcpu/issues/2).
[Measurements and limitations](../../doc/pcb-053248.md) describe the observed
053248 behavior, including differences from assembler/MAME/RTL interpretations.
No game ROM assets are required by these program-ROM probes.

## Board and firmware

The validated device is original **POG**, firmware build `POG_27C020_70ns`,
diagnostic version `jtkcpu-1.6`, USB name `VENDETTA`. The experimental PicoROM
firmware supplies `rom_enable`, a128KiB address mask and bounded timestamped
communication events. Stock firmware and P32 firmware do not satisfy this
configuration. The matching PicoROM checkout's `firmware/README-jtkcpu.md`
documents the build, install and host protocol. On the development computer it
is under `/nobackup/jtmisc/reverse/PicoROM`, branch `jtkcpu-1`. Use the matching
diagnostic firmware sources from that branch. A clean firmware rebuild matches the previous
POG binary apart from its firmware timestamp and SDK build-date strings.

Keep the reset output disconnected. The uploader disables ROM outputs for at
least three seconds, writes and verifies the complete128KiB image, arms capture,
then resumes ROM service. The PCB watchdog supplies recovery. USB power alone
does not establish PCB power; keep the PCB powered for collection.

Physical image mask is`0x1ffff`. CPU fixed ROM8000..FFFF maps to physical
18000..1FFFF. Communications use physical1DC00, CPU DC00..DFFF; transmit reads
DF00+byte and receive reads DE00. The validated original mapper initialization
is retained, followed by source-level interrupt isolation and a stackless RAM
test. Watchdog reads are spaced; rapid repeated reads caused resets on this PCB.

Only one USB client may run at a time. Build and analysis commands do not access
hardware. Commands named `run` or `collect` upload and execute a probe; successful
collection leaves it idling with spaced watchdog service and ends capture.

## Setup and outputs

Requires Python3, libusb, PyUSB, `asl` with052001 support, and `p2bin` on PATH.
Use the normal JTCORES environment if it supplies those binaries. From JTCORES:

```sh
source setprj.sh
python3 -m venv tasks/jtkcpu-1/tools/venv
. tasks/jtkcpu-1/tools/venv/bin/activate
pip install -r modules/jtkcpu/ver/pcb/requirements.txt
export JTKCPU_PCB_OUT="$PWD/tasks/jtkcpu-1/artifacts/reproduction"
export PCB_TOOLS="$PWD/modules/jtkcpu/ver/pcb/tools"
```

`JTKCPU_PCB_OUT` is independent of the source checkout and may be any output
directory. Its default is`pcb-output` in the current directory. Each builder
creates an`artifacts/` subtree there; generated ROMs, listings, manifests,
captures and summaries are never source files to commit. To analyze historical
results, point it to their task root instead; avoid rebuilding into that root
because builds replace matching generated files.

The module can also be used outside JTCORES: source, opcode inventory and
assembly template locations are resolved relative to this checkout.

## Transport and timing

```sh
python "$PCB_TOOLS/pcb.py" transport build
python "$PCB_TOOLS/pcb.py" transport run
python "$PCB_TOOLS/pcb.py" timing build --family scalar --batch 0
python "$PCB_TOOLS/pcb.py" timing run --family scalar --batch 0
```

Transport exchanges96 CPU-CRC frames with exact ACK sequence checks. Timing
uses repeated blocks and RP2040 marker timestamps, with a user-confirmed12MHz
CPU input. Results are **input-clock periods**, with fitted values and residuals;
they are not direct clock-pin captures. The analyzer rejects dropped/missing
trace entries, resets, insufficient samples and ambiguous integer fits.

Timing families: `scalar`, `memory`, `branch`, `shift`, `transfer_stack`,
`control`, `paired`, `indexed`, `pc`, `div-operands`, `unary-operands`,
`rotate-operands`, `daa-operands`. `run` defaults to30 seconds to collect enough
samples for multi-case batches; `--seconds` can adjust it. `analyze` reuses a
saved capture without touching hardware. Build one batch at a time; the family
inventory and generator cases define valid batch ranges.

## Flag matrices and reports

The family tools retain their tested command interfaces. For example:

```sh
python "$PCB_TOOLS/stack_flags.py" build 0
python "$PCB_TOOLS/stack_flags.py" collect 0
python "$PCB_TOOLS/stack_flags.py" analyze 0
```

`--help` lists each tool's batch/mode arguments. Builders with a`build` action
assemble and package their own image. Earlier tools using`generate`/`package`
require assembly between those steps; `pcb.py` handles that for transport and
timing. Collection saves raw packets, independent event snapshots, image/source
hashes and device configuration. Summarizers require their complete matrices;
missing batches are failures. `timing_report.py` merges available results and
keeps coverage explicitly partial, even when all primary opcode bytes appear.
It does not substitute model predictions for missing physical observations.

Sources cover the measured unary/binary/word, branch, control, stack, transfer,
bank, multiply/divide and variable-shift families. Transfer mnemonics and
selector labels must be interpreted using the research notes: the physical
3E/3F behavior differs from the current assembler/RTL convention.

## Additional opcode probes

These tools use the same dependencies, output root and single-client USB rules.
For a new run, choose a fresh `JTKCPU_PCB_OUT`; building a matching case replaces
its generated files. Opcode arguments are hexadecimal.

```sh
python "$PCB_TOOLS/operand_probe.py" build 05 --variant extended
python "$PCB_TOOLS/operand_probe.py" collect 05 --variant extended
python "$PCB_TOOLS/operand_probe.py" analyze 05 --variant extended
python "$PCB_TOOLS/memory_probe.py" build d1 --variant extended
python "$PCB_TOOLS/memory_probe.py" collect d1 --variant extended
python "$PCB_TOOLS/memory_probe.py" analyze d1 --variant extended
```

`operand_probe.py` returns registers and flags. Its manifest records the full
suffix and initial register state. `memory_probe.py` adds a complete 256-byte
scratch-page readback in 16 further CPU-CRC frames. `vector_probe.py` identifies
the vector handler and reads the stack page; transient handler pushes lie below
the entry stack pointer and do not overwrite the original frame. It accepts
the same `build`, `collect`, `analyze` actions; use opcode 02/03/04/5d and
variants `extended`, `extended-cc00` or `extended-ccff` for the measured cases.

`unknown_timing.py` batches 0..2 compare 05/06/07/d1 with 08 in extended,
direct-page and plain-X forms. `entry_timing.py` batches 0..3 compare raw
02/03/04/5d entry with PSHS+JMP baselines and matched return handlers. Both use
`build 0`, `collect 0`, `analyze 0` to operate on batch 0.

`reset_probe.py` timestamps reset-vector entry using a RAM sentinel, with
`build`, `collect`, `analyze` actions. Run a verified NOP recovery first to
clear the sentinel. Measured controls are `ae --variant nop` (fallthrough) and
`60 --variant watchdog` (deliberate wait). Opcode `00 --variant nop` tests
immediate reset entry. Its marker interval includes setup/dispatch overhead;
it is not an instruction cycle count or a register/flag characterization.

Non-returning sequences remain unresolved: operands/postbytes may change their
meaning. Inspect collection status before analysis; a failed/timeout capture is
saved for investigation, not promoted to a valid result. To recover, build and
collect `ae --variant nop` with `operand_probe.py`; verify its analysis passes.
See [the datasheet](../../doc/053248.md) for measured semantics and coverage.

## Host verification

```sh
PYTHONPATH="$PCB_TOOLS" python -m unittest \
  test_framed_probe test_packed_unary test_branch_flags
```

The tests use small embedded physical packet vectors and require no historical
capture directory or attached board. They check CRC, identity, input echoes,
results/outcomes and preservation of unexpected flag observations.

The five assembly files in`templates/` are maintained builder inputs extracted
from the validated development probes. Their table/body regions are replaced
by family builders; they are not standalone board images. Keep their generated
encoding and image checks when changing them. No production RTL changes are
implied by these measurement tools.

## Register, IRQ and stream follow-up (issue 3)

The following tools use `JTKCPU_PCB_OUT` and the same POG setup. Use a fresh
output directory for each campaign. Builders refuse to replace a captured
case; collectors must run one at a time. Imports do not contact USB.

| Tool                      | Probe / invocation                                                   |
| ------------------------- | -------------------------------------------------------------------- |
| `register_probe.py`       | `build`, `collect`, `analyze` followed by `control` or a named case  |
| `transfer_matrix.py`      | `build`, `collect`, `analyze` followed by `3e`/`3f` and half `0`/`1` |
| `pc_continuation.py`      | Run all twelve old-stream opcode / RAM destination cases             |
| `dp_restore.py`           | Run eight PULS DP / full RTI hidden-byte cases                       |
| `irq_probe.py`            | Run masked, enabled and pending board-IRQ cases                      |
| `irq_wakeup.py`           | Run exact 01/D2/FF plus sixteen AE-byte sequences                    |
| `irq_return.py`           | Compare unchanged versus redirected saved PC at RTI                  |
| `irq_block.py`            | Run nine vblank-synchronized positive-count block cases              |
| `block_zero.py`           | Run CF/D0/B6 with U=1 and U=0, CC5F                                  |
| `stream_timing.py`        | Run ten batches: ROM/RAM, offsets 0/1, ten stream units              |
| `audit_probe_capture.py`  | Offline: one or more `capture.json` paths                            |

**The tools described as “Run” upload ROMs when executed directly.** For a
build-only operation, import the module and call its `build` function; this
assembles and packages files without opening USB. The helpers `pc_transfer`,
`deferred_collect` and `irq_timed_collect` support those campaigns.

Examples (after setting `PCB_TOOLS`, the Python environment and a fresh output
root as above):

```sh
python "$PCB_TOOLS/transfer_matrix.py" build 3e 0
python "$PCB_TOOLS/transfer_matrix.py" collect 3e 0
python "$PCB_TOOLS/transfer_matrix.py" analyze 3e 0
python "$PCB_TOOLS/audit_probe_capture.py" \
  "$JTKCPU_PCB_OUT/artifacts/transfer-matrix/3e-0/capture.json"
```

Timestamped block-IRQ cases use `irq_block.TIMED=True` and
`irq_timed_collect.collect(root, run)`, followed by `irq_probe.analyze`.
Their trace starts with A0/A2/A3 before the ordinary result frame. The A2→A3
interval includes the handlers and setup; it is not an instruction cycle count.
For additional zero-count flags, set `block_zero.CC` to 50 or FF and set
`block_zero.OUTPUT` to a fresh campaign name before `build(opcode, 0)`.

Zero-count blocks can traverse the communication window. `deferred_collect`
keeps capture disabled during execution, waits two seconds after ROM resume,
then arms a fresh session and sends A5. The CPU reconstructs mapper/report
state, consumes that request, emits A0 and reports. Its expected event trace
includes the initial RX before A0. This establishes effects and flags but
provides no duration for the block itself. The active-capture and early-arm
attempts that overflowed are not valid timing measurements.

The actual register encodings matter: assembler `TFR S,X` emits `3F 24`,
which accesses the observed DP word, not S. The IRQ frame reader uses raw
`3E A6`. Early development captures with that assembler mismatch retain an
erratum and are excluded from frame-semantics claims. Early ROM-target probes
also retain seed-metadata errata; use the corrected builders here.

Physical evidence in `tasks/jtkcpu-3/artifacts/` is kept outside git. Seventy-seven
images from these maintained builders reproduced the accepted campaign images
byte for byte. The offline audit checks image/source hashes, CPU CRC and frame
identity, complete event ordering, and loss/reset indicators. It does not turn
a transport-valid capture with a documented probe error into valid semantic
evidence. The research notes and datasheet identify each observation's scope.

Vendetta's core ties NMI inactive and leaves FIRQ disabled; the user deferred
those inputs' masking/priority measurements to a suitable later PCB. The real
IRQ measurements here are independent of the earlier software-entry opcode
measurements. Keep the PicoROM reset lead disconnected.
