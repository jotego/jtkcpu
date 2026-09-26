#!/usr/bin/env python3
"""Timestamp entry through the reset vector; compare with a deliberate watchdog wait."""
import argparse,hashlib,json,re,subprocess,sys
import operand_probe as base
ROOT=base.ROOT
VARIANT='nop'
base.SUFFIXES['watchdog']=bytes.fromhex('fe')

def configure(op):
 root=ROOT/'artifacts/reset-screen'/VARIANT/f'{op:02x}'
 base.framed.ROOT=root
 return root,0x7000+list(base.SUFFIXES).index(VARIANT)*256+op

def build(op):
 base.VARIANT=VARIANT;base.configure=configure
 root,run=configure(op);base.build(op)
 s=(root/'probe.asm').read_text()
 s=s.replace('        LDD #$1234\n        LDX #$2F00','        LDA #$A7\n        STA $2E45\n        LDA $DFE0\n        LDD #$1234\n        LDX #$2F00')
 assert s.count('        LDA $DFE0')==1
 s=s.replace('        PSHS CC\n        STD $2E0C','        LDA $DFE2\n        CLR $2E45\n        JMP IDLE\n        PSHS CC\n        STD $2E0C')
 s=s.replace('        ORG $FFF6','''RESET_DISPATCH:
        LDA $2E45
        CMPA #$A7
        BEQ RESET_OBSERVED
        JMP RESET
RESET_OBSERVED:
        LDA $DFE1
        CLR $2E45
        JMP IDLE
        ORG $FFF6''')
 s=s.replace('FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET','FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET_DISPATCH')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 fixed=(root/'fixed.bin').read_bytes();lst=(root/'probe.lst').read_text()
 dispatch=int(re.search(r'\d+/([0-9A-F]+) :\s+RESET_DISPATCH:',lst)[1],16)
 assert len(fixed)==32768 and fixed[0x5c00:0x6000]==b'\xff'*1024
 assert fixed[:26].hex()=='4280000824ff63fb92075fea10113a077c0010fb3a075d003dd0'
 assert int.from_bytes(fixed[-2:],'big')==dispatch
 image=bytes(0x18000)+fixed;(root/'probe-128k.bin').write_bytes(image)
 m=json.loads((root/'manifest.json').read_text());m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),image_sha256=hashlib.sha256(image).hexdigest(),reset_vector=dispatch,protocol='A0 boot, E0 before seed/target, E1 reset entry or E2 fallthrough; no result frame',ram_magic_address=0x2e45,ram_magic=0xa7)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')

def analyze(op):
 root,run=configure(op);m=json.loads((root/'manifest.json').read_text())
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==m[key]
 context=json.loads((root/'probe-128k.device.json').read_text());assert context['image_sha256']==m['image_sha256'] and context['build_config']=='POG_27C020_70ns'
 snaps=json.loads((root/'probe-128k.events.json').read_text());events={}
 for snap in snaps:
  assert not snap['capture_stopped'] and snap['dropped_bytes']==0
  for e in snap['events']:
   n=e['sequence'];assert n not in events or events[n]==e;events[n]=e
 assert sorted(events)==list(range(snaps[-1]['count']))
 addresses=[int(events[i]['address'],16) for i in sorted(events)]
 assert len(addresses)==3 and addresses[:2]==[0x1a0,0x1e0] and addresses[-1] in (0x1e1,0x1e2),addresses
 delta=(events[2]['time_us']-events[1]['time_us'])&0xffffffff
 r=dict(opcode=op,variant=VARIANT,event_addresses=addresses,marker_interval_us=delta,reset_entry=addresses[-1]==0x1e1,scope='Includes fixed register-seed and reset-dispatch overhead; not a per-instruction cycle count')
 (root/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
 return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('opcode',type=lambda s:int(s,16));p.add_argument('--variant',choices=['nop','extended','watchdog'],default='nop');a=p.parse_args();VARIANT=a.variant
 if a.action=='build':build(a.opcode)
 elif a.action=='analyze':analyze(a.opcode)
 else:
  root,run=configure(a.opcode)
  subprocess.run([sys.executable,str(base.TOOLS/'load_probe.py'),str(root/'probe-128k.bin'),'--seconds','3','--poll-interval','.005'],check=True)
