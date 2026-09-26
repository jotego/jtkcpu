#!/usr/bin/env python3
"""Cross-check SEX's Z behavior with a different record layout and all B values."""
import hashlib
import json
from pathlib import Path
from packed_unary import BASE,decode,sex_cases
from framed_probe import check_frame

root=BASE.parent/'sex-confirm'
single=json.loads((root/'single/capture.json').read_text())
assert single.get('validated') and single['complete']
manifest=single['manifest'];rows=[]
for file,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
    assert hashlib.sha256((root/'single'/file).read_bytes()).hexdigest()==manifest[key]
for i,(frame,case) in enumerate(zip(single['frames'],manifest['cases'])):
    packet=bytes.fromhex(frame['hex'])
    check_frame(packet,0xf0+i,False,0xa500)
    b=packet[9:25];input_d=case['x'];value=input_d&255
    assert b[:5]==input_d.to_bytes(2,'big')+b'\0\0'+bytes([case['cc']])
    expected=value|0xff00 if value&0x80 else value
    assert b[5:7]==expected.to_bytes(2,'big') and b[7:13]==bytes.fromhex('2f002f102f20') and b[14:]==b'\xbe\xef'
    rows.append(dict(opcode=0xb2,mnemonic='SEX',value=value,input_D=input_d,cc=case['cc'],output_D=expected,output_CC=b[13]))
assert len(rows)==96
(root/'single/results.json').write_text(json.dumps(dict(records=rows),indent=2)+'\n')
packed=[]
for batch in range(3):
    folder=BASE/'sexall'/'boundary'/f'batch-{batch:02d}'
    capture=json.loads((folder/'capture.json').read_text())
    assert capture['manifest']['cases']==sex_cases()[batch*192:(batch+1)*192]
    for file,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:
        assert hashlib.sha256((folder/file).read_bytes()).hexdigest()==capture['manifest'][key]
    packed.extend(decode(capture))
assert len(packed)==576
for cc in (0,255):
    assert {r['value'] for r in packed[:512] if r['cc']==cc}==set(range(256))
all_rows=rows+packed
models={'NZ_from_full_D':[],'NZ_from_generated_A':[]}
for i,r in enumerate(all_rows):
    d,cc=r['output_D'],r['cc']
    full=(cc&0xf1)|(8 if d&0x8000 else 0)|(4 if d==0 else 0)
    a_only=(cc&0xf1)|(8 if d&0x8000 else 0)|(4 if d>>8==0 else 0)
    if full!=r['output_CC']:models['NZ_from_full_D'].append(i)
    if a_only!=r['output_CC']:models['NZ_from_generated_A'].append(i)
assert not models['NZ_from_generated_A']
summary=dict(records=len(all_rows),single_records=96,packed_records=576,model_mismatch_indices=models,
    observed='SEX sign-extends B into D; N=B7, Z=not B7, V=0; E/F/H/I/C preserved in recorded cases.',
    scope='All 256 B values at CC00/FF with initial A5A; 64 additional A-boundary cases; 96 independently formatted records at CC00..07. Earlier four B values cover all 256 initial CC states.')
(root/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(root/'README.md').write_text('\n'.join(['# Physical SEX zero-flag behavior','',summary['observed'],'',summary['scope'],'',
    'Positive nonzero B produces a nonzero D but sets Z: B=01 gives D=0001 with Z=1. This is consistent with flags describing the generated A byte (00 or FF), rather than the entire D result. It does not establish the internal implementation.',
    '',f"Full-D N/Z model mismatches: {len(models['NZ_from_full_D'])}/{len(all_rows)}; generated-A N/Z model mismatches: 0.",'',
    'The single-record confirmation uses no opcode dispatch and the earlier full-register payload format. It checks X/Y/U externally. The packed sweep echoes both input records and checks X/Y/U on the CPU. Both restore CC immediately before SEX and capture it immediately afterward. All CRC, image/hash, trace, reset/drop and completion gates pass.',''])+'\n')
print('SEX confirmation: 672 complete records; generated-A flag model fits all; full-D model mismatches:',len(models['NZ_from_full_D']))
