#!/usr/bin/env python3
"""Check assembled return-chain addresses, marker placement and stack guards."""
from pcb_paths import ROOT
from pathlib import Path
import json,re
root=ROOT / 'artifacts/instruction-timing/control'
for f in sorted(root.glob('batch-*')):
    m=json.loads((f/'manifest.json').read_text());b=(f/'fixed.bin').read_bytes();s=(f/'timing.lst').read_text()
    labels={name:int(addr,16) for addr,name in re.findall(r'^\s*\d+/([0-9A-F]{4}) :\s+(C\d+_N\d+_(?:FRAME|BODY)):',s,re.M)}
    for c in m['cases']:
        if not c.get('frame_bytes'):continue
        size=c['frame_bytes'];step=len(bytes.fromhex(c['encoding']))
        assert 0x2000+512*size<=0x4000
        for n in m['counts']:
            prefix=f"C{c['id']}_N{n}"
            frame=labels[prefix+'_FRAME']-0x8000;body=labels[prefix+'_BODY']-0x8000
            assert b[frame-3:frame]==b'\x44'+(0x8000+body+step).to_bytes(2,'big')
            assert b[body:body+n*step]==bytes.fromhex(c['encoding'])*n
            end=body+n*step
            assert b[end:end+4]==bytes.fromhex('1207dfe2')
            assert b[body-3:body]==bytes([0x48 if c['stack']=='S' else 0x46,0x20,0])
            assert b[end+4:end+7]==bytes([0x52 if c['stack']=='S' else 0x50])+(0x2000+n*size).to_bytes(2,'big')
            assert b[end+7]==0x6b # LBNE RAM_FAIL
    print(f.name,'return pointers, bodies, stack guards and RAM bounds validated against assembled bytes')
