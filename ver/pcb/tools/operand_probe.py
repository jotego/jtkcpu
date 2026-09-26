#!/usr/bin/env python3
"""Single raw-opcode continuation screen; failures remain unresolved."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from pcb_paths import ROOT
TOOLS=Path(__file__).resolve().parent
sys.path.insert(0,str(TOOLS))
import framed_probe as framed

VARIANT='nop'
SUFFIXES={'nop':b'', 'regoff':bytes.fromhex('a0'), 'direct':bytes.fromhex('c4ae'), 'extended':bytes.fromhex('072f80')}
SUFFIXES.update({'zero':bytes.fromhex('070000'), 'extended-setz':bytes.fromhex('072f80'), 'zero-setz':bytes.fromhex('070000')})
SUFFIXES['extended-alt']=bytes.fromhex('072f80')
SUFFIXES.update({'regoff-marker':bytes.fromhex('a0a0'), 'direct-marker':bytes.fromhex('c4aea0'), 'extended-marker':bytes.fromhex('072f80a0'), 'x-postinc':bytes.fromhex('20'), 'x-indirect':bytes.fromhex('2e')})
SUFFIXES.update({'extended-cc00':bytes.fromhex('072f80'), 'extended-ccff':bytes.fromhex('072f80')})
# Reserve the historical reset-control index before adding further variants.
SUFFIXES['watchdog']=bytes.fromhex('fe')
SUFFIXES.update({f'extended-fill{x:02x}':bytes.fromhex('072f80') for x in (0,255,128,1)})

def configure(op):
 framed.ROOT=ROOT/'artifacts/operand-screen'/VARIANT/f'{op:02x}'
 return framed.ROOT,0xc100+list(SUFFIXES).index(VARIANT)*256+op

def build(op):
 root,run=configure(op);framed.COUNT=1;framed.generate()
 fill=int(VARIANT[-2:],16) if '-fill' in VARIANT else 0x5a
 cc=0x5f if VARIANT.endswith('-setz') else 0x50
 if VARIANT.endswith('-cc00'):cc=0
 if VARIANT.endswith('-ccff'):cc=0xff
 seed=dict(D=0x1234,X=0x2f00,Y=0x2f10,U=8,S=0x3ff0,CC=cc,DP=0x2f)
 dpword=0x2f00
 if VARIANT=='extended-alt':
  seed.update(D=0xa1b2,X=0x2f23,Y=0x2f45,U=3,S=0x3fe8,CC=0xff)
  cc=seed['CC'];dpword=0x2fa5
 s=(root/'probe.asm').read_text().replace('LDD #$7B01',f'LDD #${run:04X}')
 s=s.replace('CMPD #$0150','CMPD #$00F1')
 first=s.index('        LDX #$2E09');last=s.index('; CRC-16/CCITT-FALSE',first)
 suffix=''.join(f'        FCB ${b:02X}\n' for b in SUFFIXES[VARIANT])
 body=f'''        LDX #$2F00
        LDA #${fill:02X}
FILL_SCRATCH:
        STA ,X+
        CMPX #$3000
        BNE FILL_SCRATCH
        LDD #$2F80
        STD $2F00
        LDD #$2F90
        STD $2F10
        LDS #${seed['S']:04X}
        LDX #${dpword:04X}
        FCB $3E,$42 ; initialize full physical DP-related word
        LDD #${seed['D']:04X}
        LDX #${seed['X']:04X}
        LDY #${seed['Y']:04X}
        LDU #${seed['U']:04X}
        ANDCC #0
        ORCC #${cc:02X}
TARGET:
        FCB ${op:02X}
{suffix}        FCB $AE,$AE,$AE,$AE,$AE,$AE,$AE,$AE
        FCB $AE,$AE,$AE,$AE,$AE,$AE,$AE,$AE
        PSHS CC
        STD $2E0C
        STX $2E0E
        STY $2E10
        PULS A
        STA $2E16
        STU $2E12
        STS $2E14
        PSHS DP
        PULS A
        STA $2E17
        LDS #$3FF0
        LDA #${op:02X}
        STA $2E09
        LDA #${cc:02X}
        STA $2E0A
        LDA #$F9
        STA $2E0B
        LDA #$FC
        STA $2E18
'''
 s=s[:first]+body+s[last:];(root/'probe.asm').write_text(s)
 manifest=dict(first=240,count=1,frame_size=27,run_id=run,opcode=op,
  seed=seed,scratch_fill=fill,
  initial_selector4_word=dpword,variant=VARIANT,trailing_hex=SUFFIXES[VARIANT].hex()+'ae'*16,source_sha256=hashlib.sha256(s.encode()).hexdigest())
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 fixed=(root/'fixed.bin').read_bytes();assert fixed.count(bytes([op])+SUFFIXES[VARIANT]+bytes([0xae])*16+bytes([12,1]))==1
 framed.package()

def analyze(op):
 root,run=configure(op);c=json.loads((root/'capture.json').read_text());assert c['validated'] and c['complete']
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['manifest'][key]
 records=[]
 for i,f in enumerate(c['frames']):
  raw=bytes.fromhex(f['hex']);framed.check_frame(raw,240+i,False,run);b=raw[9:25]
  assert b[:3]==bytes([op,c['manifest']['seed']['CC'],0xf9]) and b[15]==0xfc
  records.append(dict(D=int.from_bytes(b[3:5],'big'),X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'),CC=b[13],DP=b[14]))
 assert len(records)==1
 summary=dict(opcode=op,records=records,distinct_outputs=list({json.dumps(r,sort_keys=True):r for r in records}.values()),status='returned through NOP padding; length and memory effects unresolved')
 (root/'results.json').write_text(json.dumps(summary,indent=2)+'\n');print(f'{op:02X}:',summary['distinct_outputs'])
 if op==0xae and VARIANT=='nop':assert all(r==c['manifest']['seed'] for r in records)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('opcode',type=lambda s:int(s,16));p.add_argument('--variant',choices=SUFFIXES,default='nop');a=p.parse_args();VARIANT=a.variant;assert 0<=a.opcode<=255
 if a.action=='build':build(a.opcode)
 elif a.action=='analyze':analyze(a.opcode)
 else:
  from screen_collect import collect
  root,run=configure(a.opcode)
  collect(root,run)
