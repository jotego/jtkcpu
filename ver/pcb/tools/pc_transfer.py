"""Distinct fallthrough and destination markers for transfer selector7."""
import json,hashlib,subprocess,re
import register_probe as base
CASES={f'{op:02x}-{post:02x}-{mode}':(op,post,mode) for op in (0x3e,0x3f) for post in (0x27,0x72) for mode in ('ram','rom')}
base.CASES.update({k:bytes([v[0],v[1]]) for k,v in CASES.items()})

def configure(case):
 root=base.ROOT/'artifacts/pc-transfer'/case;base.framed.ROOT=root
 return root,0x4000+list(CASES).index(case)

def build(case):
 base.configure=configure;base.build(case)
 root,run=configure(case);op,post,mode=CASES[case];s=(root/'probe.asm').read_text()
 old='''        LDD #$A807
        STD $2F80
        LDY #CAPTURE
        STY $2F82
'''
 new='''        LDX #$2F80
        LDA #$AE
FILL_CODE:
        STA ,X+
        CMPX #$2F90
        BNE FILL_CODE
        LDD #$A807
        STD $2F90
        LDY #RAM_TARGET
        STY $2F92
'''
 assert old in s;s=s.replace(old,new)
 if mode=='rom':
  s=s.replace('        LDX #$2F80\n        LDY #$2FA0','        LDX #ROM_TARGET\n        LDY #$2FA0').replace('        LDX #CAPTURE\n        LDY #$2FA0','        LDX #ROM_TARGET\n        LDY #$2FA0')
  assert '        LDX #ROM_TARGET\n        LDY #$2FA0' in s
 pad='        FCB '+','.join(['$AE']*16)+'\n'
 s=s.replace('CAPTURE:\n',pad+'''        LDA #$11
        JMP CAPTURE
ROM_TARGET:
'''+pad+'''RAM_TARGET:
        LDA #$22
CAPTURE:
''')
 (root/'probe.asm').write_text(s)
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 lst=(root/'probe.lst').read_text();label=lambda name:int(re.search(r'\d+/([0-9A-F]+) :\s+'+name+':',lst)[1],16)
 m=json.loads((root/'manifest.json').read_text());m.update(source_sha256=hashlib.sha256(s.encode()).hexdigest(),target_mode=mode,target_address=label('ROM_TARGET') if mode=='rom' else 0x2f80,opcode_address=label('TARGET'),fallthrough_marker=0x11,destination_marker=0x22)
 m['seed']['X']=m['target_address']
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');base.framed.package()

def analyze(case):
 base.configure=configure;return base.analyze(case)
