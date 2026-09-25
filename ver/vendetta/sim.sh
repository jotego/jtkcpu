#!/bin/bash
# SPDX-FileCopyrightText: 2026 Jose Tejada Gomez
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

main() {
    : "${JTROOT:?Source setprj.sh from your checkout first}"
    : "${ROM:?Source setprj.sh from your checkout first}"
    local action=${1:-build}
    if (($#)); then shift; fi
    local source_dir
    source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
    local output_dir="$JTROOT/tasks/jtkcpu-1/artifacts/bootstrap"
    local sim_dir="$JTROOT/cores/simson/ver/vendetta_boot"
    case "$action" in
        build|sim) ;;
        *) echo "Usage: $0 [build|sim [jtsim options]]" >&2; exit 2 ;;
    esac
    mkdir -p "$output_dir"
    build_rom "$source_dir" "$output_dir"
    if [[ $action == sim ]]; then
        prepare_sim "$source_dir" "$output_dir" "$sim_dir"
        run_sim "$sim_dir" "$@"
    fi
}

build_rom() {
    local source_dir=$1 output_dir=$2
    cp "$source_dir/vendetta_boot.asm" "$output_dir/"
    (
        cd "$output_dir"
        if ! asl -cpu 052001 vendetta_boot.asm -L > assembly.log 2>&1; then
            cat assembly.log >&2
            exit 1
        fi
        p2bin vendetta_boot.p fixed.bin -r '0x8000-0xffff' -l 255
        test "$(stat -c %s fixed.bin)" -eq 32768
        dd if=/dev/zero of=vendetta_boot.bin bs=229376 count=1 status=none
        cat fixed.bin >> vendetta_boot.bin
        test "$(stat -c %s vendetta_boot.bin)" -eq 262144
        sha256sum vendetta_boot.bin > vendetta_boot.sha256
    )
    echo "Program ROM: $output_dir/vendetta_boot.bin (256 KiB)"
}

prepare_sim() {
    local source_dir=$1 output_dir=$2 sim_dir=$3
    if [[ ! -s "$ROM/vendetta.rom" ]]; then jtframe mra simson; fi
    mkdir -p "$sim_dir"
    (
        cd "$sim_dir"
        # Use the existing JTFRAME layout/gfx conversion and retain all game assets.
        jtutil sdram vendetta
        # jtutil links rom.bin to the original. Replace only our local link.
        cp --remove-destination "$ROM/vendetta.rom" rom.bin
        dd if="$output_dir/vendetta_boot.bin" of=rom.bin bs=1 seek=4 conv=notrunc status=none
        dd if="$output_dir/vendetta_boot.bin" of=sdram_bank0.bin conv=swab,notrunc status=none
        cp "$source_dir/vendetta_boot.vlt" game.vlt
    )
}

run_sim() {
    local sim_dir=$1
    shift
    cd "$sim_dir"
    # Keep a dedicated simulation directory: no game-run dumps/preloaded scene RAM.
    # The local ROM already carries Vendetta's header; don't use -setname or -dummyROM.
    jtsim -nosnd -video 100 "$@" 2>&1 | tee boot.log
    grep -q 'BOOT PASS:' boot.log
}

main "$@"
