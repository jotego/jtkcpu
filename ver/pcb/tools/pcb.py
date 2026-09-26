#!/usr/bin/env python3
"""Build and run the validated Vendetta transport and timing probes."""
import argparse
import subprocess
import sys
from pathlib import Path
from pcb_paths import ROOT

TOOLS = Path(__file__).resolve().parent
BASE_FAMILIES = ('scalar', 'memory', 'branch', 'shift', 'transfer_stack', 'control', 'paired', 'indexed', 'pc')
OPERAND_FAMILIES = {
    'div-operands': 'div_operand_timing.py',
    'unary-operands': 'unary_operand_timing.py',
    'rotate-operands': 'rotate_operand_timing.py',
    'daa-operands': 'daa_operand_timing.py',
}


def invoke(script, *args):
    subprocess.run([sys.executable, str(TOOLS / script), *map(str, args)], check=True)


def assemble(folder, stem):
    with (folder / 'assembly.log').open('w') as log:
        subprocess.run(['asl', '-cpu', '052001', stem + '.asm', '-L'], cwd=folder,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run(['p2bin', stem + '.p', 'fixed.bin', '-r', '0x8000-0xffff', '-l', '255'],
                       cwd=folder, stdout=log, stderr=subprocess.STDOUT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='suite', required=True)
    timing = sub.add_parser('timing')
    timing.add_argument('action', choices=('build', 'run', 'analyze'))
    timing.add_argument('--family', choices=BASE_FAMILIES + tuple(OPERAND_FAMILIES), default='scalar')
    timing.add_argument('--batch', type=int, default=0)
    timing.add_argument('--seconds', type=float, default=30)
    transport = sub.add_parser('transport')
    transport.add_argument('action', choices=('build', 'run'))
    args = parser.parse_args()
    if args.suite == 'transport':
        folder = ROOT / 'artifacts/framed-transport'
        if args.action == 'build':
            invoke('framed_probe.py', 'generate')
            assemble(folder, 'probe')
            invoke('framed_probe.py', 'package')
            print(folder / 'probe-128k.bin')
        else:
            invoke('framed_probe.py', 'collect')
        return
    if args.batch < 0:
        parser.error('--batch must be nonnegative')
    folder = ROOT / 'artifacts/instruction-timing'
    if args.family != 'scalar':
        folder /= args.family
    folder /= f'batch-{args.batch:02d}'
    script = OPERAND_FAMILIES.get(args.family, 'instruction_timing.py')
    suffix = ['--family', args.family] if args.family in BASE_FAMILIES else []
    if args.action == 'build':
        invoke(script, 'generate', args.batch, *suffix)
        assemble(folder, 'timing')
        invoke(script, 'package', args.batch, *suffix)
        print(folder / 'timing-128k.bin')
    else:
        if args.action == 'run':
            invoke('load_probe.py', folder / 'timing-128k.bin', '--seconds', args.seconds,
                   '--base', '0x1dc00', '--poll-interval', '.005')
        invoke(script, 'analyze', args.batch, *suffix)


if __name__ == '__main__':
    main()
