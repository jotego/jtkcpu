# Vendetta bootstrap ROM

Minimal board firmware for [JTKCPU issue 1](http://gitea.jotego.es/jotego/jtkcpu/issues/1).
The address map comes from the Vendetta decoder in
`$JTROOT/cores/simson/hdl/jtsimson_main.v`.
This is the bootstrap for later instruction characterization; it does not yet
measure instruction timing/flags or implement PicoROM communications.

## Physical validation status

This original bootstrap has not yet been updated with the successful PCB
bring-up findings. Its 256 KiB image layout and frequent watchdog accesses
differ from the validated 128 KiB POG setup. It is not the ROM used for the
physical instruction measurements. See [053248 PCB measurements](../../doc/pcb-053248.md)
for the mapper initialization, address mask and spaced watchdog requirements.
The simulation instructions and behavior below describe this original bootstrap.

Use this repository as `modules/jtkcpu` in a JTCORES checkout. From the JTCORES
checkout root:

```sh
source setprj.sh
modules/jtkcpu/ver/vendetta/sim.sh build
modules/jtkcpu/ver/vendetta/sim.sh sim
```

Requirements: ASL with `052001` support, p2bin, and the usual JTFRAME simulation
tools. The simulation uses the installed Vendetta graphics ROMs. If
`$ROM/vendetta.rom` is absent, the script runs `jtframe mra simson` using the
configured ROM archive location.

The build creates a **256 KiB program-only image** at:

```
tasks/jtkcpu-1/artifacts/bootstrap/vendetta_boot.bin
```

This legacy image is retained for the original simulation flow. For current
PCB uploads, use the [physical characterization tools](../pcb/README.md).
It has no JTFRAME header. CPU fixed
ROM `$8000–$FFFF` occupies physical `$38000–$3FFFF`, with reset vector `$8000`
at physical `$3FFFE`. The low bank is zero-filled, including the reserved
PicoROM communications page at physical `$01C00–$01FFF`.

The listing, assembly log and SHA-256 are beside the image. No ROM binary or
game assets should be committed.

## Behavior

1. Mask CPU interrupts, disable the board IRQ and EEPROM outputs, select
   bank 0, and service the watchdog with a read from `$5FEA`.
2. Verify all 8 KiB of work RAM **before using a stack or RAM variables**:
   fill `$55`, read/replace with `$AA`, read/replace with zero, then verify zero.
   Each loop services the watchdog. The read/replace sweeps expose aliasing as
   well as data faults; this is a bootstrap check, not an exhaustive RAM test.
3. Initialize tile RAM, palette, priorities and sprite RAM. The font is reused
   from the installed Vendetta graphics ROMs; its foreground uses pen 8.
   Sprite DMA and tile-chip interrupts are disabled. EEPROM lines remain low.
4. Display `JTKCPU VENDETTA TEST`, `RAM PASS`, `WATCHDOG ACTIVE`, `IRQ COUNT`,
   and a color calibration row. GRAY uses layer A's separate palette; the
   other text uses the fixed layer. `WATCHDOG ACTIVE` reports the service loop,
   not a measurement of the physical watchdog timeout.
5. Enable LVBL IRQ, acknowledge it by clearing `$5FE2` bit 6, increment the
   four-digit hexadecimal counter, update its tiles during blanking, and
   re-enable IRQ before RTI. The foreground loop keeps servicing the watchdog
   independently of IRQ delivery.

RAM failure or an unexpected interrupt enters a stackless red-palette loop
that continues watchdog servicing. A RAM failure may prevent the status byte
from being stored; the failure path does not depend on it.

| Work RAM | Meaning |
| --- | --- |
| `$2000–$2001` | Big-endian IRQ count |
| `$2010` | `$11`: RAM verified, `$A5`: ready, `$E1`: RAM fault, `$E2`: unexpected interrupt |
| Below `$3FF0` | Supervisor/IRQ stack, after RAM verification |

## Simulation and checks

`sim` creates a dedicated `cores/simson/ver/vendetta_boot/` directory, calls
`jtutil sdram vendetta`, and overlays only the program image in its local
`rom.bin` and SDRAM bank 0. It preserves the original `$ROM/vendetta.rom` and
the ordinary Vendetta simulation directory. Run this through the script;
`jtsim -setname vendetta` would replace the diagnostic ROM link.

Frames are in `cores/simson/ver/vendetta_boot/frames/`; the log is `boot.log`.
Additional `jtsim` options may follow `sim`, for example `sim -w 14`.

The local `game.vlt` loads a simulation-only monitor through Verilator's bind
mechanism. It does not modify synthesized core behavior. The monitor checks:

- No watchdog-service gap exceeds **10 ms** at the core's 48 MHz clock,
  including RAM/video initialization. This is a conservative simulation
  deadline, not the measured PCB watchdog timeout.
- IRQs update the counter and its tiles only during vertical blank.
- At least 50 IRQ updates and continued watchdog activity occur during one
  second after READY.
- No firmware error marker, EEPROM output activity, or post-READY reset occurs.

The monitor ends a successful run with `BOOT PASS`, reporting IRQ updates,
watchdog reads and the longest service gap. The wrapper requires that marker
and also propagates simulator failure. The 100-frame limit catches incomplete
boots; reducing it below the monitor's observation period fails validation.

Simulation uses `-nosnd`. Real PCB startup, watchdog read qualification,
physical interrupt behavior and PicoROM electrical compatibility still need
board validation. No MAME run has been performed, and PCB display/operation
has not yet been confirmed.

Validation on 2026-09-25: the simson run passed with 59 IRQ updates during the
one-second observation period and a maximum watchdog gap of 2,423 clocks
(about 50 microseconds). Frames 40 and 72 matched the expected ROM-font glyphs
and RGB colors pixel-for-pixel; their counters advanced from `001A` to `003A`.
Separate mutated-image runs confirmed rejection of missing watchdog reads,
masked IRQs, and a forced RAM-check failure. Core lint and ShellCheck passed.
The JTCORES baseline was `0486453041b5685f8d53c406be9d3c4c0ff109c4`.
Logs and the reviewed screen are local artifacts under
`tasks/jtkcpu-1/artifacts/bootstrap/`; regenerate them on a new computer.

## Current PCB workflow

Use the [physical characterization tools](../pcb/README.md) for board uploads,
communication and instruction measurements. They use the validated original
POG variant, a128KiB image, original mapper setup, spaced watchdog service and
watchdog-driven recovery while the reset lead remains disconnected.

The historical September25 upload used P32 firmware and a256KiB image. The
subsequent board work established that the physical device is POG; successful
USB readback of that old image did not establish correct board operation.
The original display bootstrap remains a simulation fixture and has not been
physically validated. Its old reset-pin upload commands have been retired.
