"""Stable source locations and an independently selectable result directory."""
import os
from pathlib import Path
MODULE = Path(__file__).resolve().parents[3]
TEMPLATES = Path(__file__).resolve().parent.parent / 'templates'
ROOT = Path(os.environ.get('JTKCPU_PCB_OUT', 'pcb-output')).resolve()
