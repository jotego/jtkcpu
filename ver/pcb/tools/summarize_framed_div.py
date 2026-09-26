#!/usr/bin/env python3
"""Audit the complete DIV operand/CC matrix against raw CRC frames."""
import hashlib
import json
from framed_div import ROOT,PAIRS
from framed_probe import check_frame

observations={pair:{} for pair in PAIRS}
image_ids=set()
for page in range(32):
    folder=ROOT/f'batch-{page:02d}'
    capture=json.loads((folder/'capture.json').read_text())
    assert capture.get('validated') and capture['complete']
    manifest=capture['manifest']
    assert manifest['run_id']==0xd100+page and manifest['run_id'] not in image_ids
    image_ids.add(manifest['run_id'])
    for filename,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
        assert hashlib.sha256((folder/filename).read_bytes()).hexdigest()==manifest[key]
    assert len(capture['frames'])==len(manifest['cases'])==96
    for index,(record,case) in enumerate(zip(capture['frames'],manifest['cases'])):
        frame=bytes.fromhex(record['hex'])
        check_frame(frame,0xf0+index,False,manifest['run_id'])
        payload=frame[9:25]
        x,b,cc=case['x'],case['b'],case['cc']
        assert payload[:5]==x.to_bytes(2,'big')+b.to_bytes(2,'big')+bytes([cc])
        q,r=divmod(x,b) if b else (65535,x&255)
        outcc=(cc&~12)|(8 if q&0x8000 else 0)|(4 if q==0 else 0)
        expected=(0x1200|r).to_bytes(2,'big')+q.to_bytes(2,'big')+bytes.fromhex('2f102f20')+bytes([outcc])+bytes.fromhex('beef')
        assert payload[5:]==expected,(page,index,payload.hex(),expected.hex())
        assert cc not in observations[(x,b)]
        observations[(x,b)][cc]=dict(quotient=q,remainder=r,cc=outcc)
for pair,ccs in observations.items():assert sorted(ccs)==list(range(256)),pair
summary=dict(records=3072,operand_pairs=PAIRS,initial_cc_values=list(range(256)),
             model='X receives unsigned quotient, B remainder; N/Z reflect quotient; all other CC bits preserved.',
             zero_divisor='For recorded zero-divisor dividends 0000,8000,FFFF: X=FFFF, B=original X low byte.',
             scope='All initial CC values for these 12 operand pairs; other operands remain unmeasured.',
             unique_image_ids=sorted(image_ids))
(ROOT/'all-cc-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
lines=['# Physical DIV X,B flags and results','',summary['model'],'',summary['zero_divisor'],'',
       'All 3072 records pass: 12 dividend/divisor pairs × all 256 initial CC values. A=12, Y=2F10 and U=2F20 remain unchanged. CC is captured immediately after DIV.',
       'Each 96-record batch passes CRC-16, exact sequence, USB/event-ring equality, source/image hashes and no-drop/no-reboot gates. Every image has a distinct packet ID D100..D11F.',
       '',summary['scope'],'',
       'The current FPGA ALU excludes DIVXB from updating N; the PCB updates N in these tests. Local MAME preserves N, derives C from quotient bit 7 and returns zero quotient/remainder for divisor zero; those behaviors differ from these observations. No production HDL or MAME changes were made.',
       '', '| Dividend X | Divisor B | Quotient X | Remainder B |', '|---|---|---|---|']
for x,b in PAIRS:
    q,r=divmod(x,b) if b else (65535,x&255)
    lines.append(f'| {x:04X} | {b:02X} | {q:04X} | {r:02X} |')
(ROOT/'README.md').write_text('\n'.join(lines)+'\n')
print('PASS: all 3072 DIV operand/CC combinations; only N/Z change.')
