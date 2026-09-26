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
