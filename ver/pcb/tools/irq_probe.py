"""Bounded board-vblank IRQ entry, masking and pending recognition probes."""
import sys,json,hashlib,subprocess
from pathlib import Path
from pcb_paths import ROOT
import framed_probe as f
from screen_collect import collect

def build(case):
 root=ROOT/'artifacts/irq-v2'/case;assert not (root/'capture.json').exists();f.ROOT=root;f.COUNT=1;f.generate();run=0x6100+['enabled','masked','pending'].index(case)
 s=(root/'probe.asm').read_text().replace('LDD #$7B01',f'LDD #${run:04X}').replace('CMPD #$0150','CMPD #$00F1')
 a=s.index('        LDX #$2E09');b=s.index('; CRC-16/CCITT-FALSE',a)
 pending='''        ANDCC #$EF
        LDX #$FFFF
PENDING_WAIT:
        LEAX -1,X
        BNE PENDING_WAIT
''' if case=='pending' else ''
 s=s[:a]+f'''        LDX #$2E09
        CLRA
ZERO_RESULT:
        STA ,X+
        CMPX #$2E19
        BNE ZERO_RESULT
        LDS #$3FF0
        LDX #$2FA5
        FCB $3E,$42
        LDA #$40
        STA $5FE2
        LDD #$1234
        LDY #$2FA0
        LDU #$3FE0
        LDX #$FFFF
        ANDCC #0
        ORCC #${0x4f if case=='enabled' else 0x5f:02X}
IRQ_WAIT:
        LEAX -1,X
        BNE IRQ_WAIT
{pending}        ORCC #$50
        CLR $5FE2
        LDA #$EE
        STA $2E09
        JMP REPORT
IRQ_HANDLER:
        PSHS CC
        PULS A
        STA $2E0A
        STS $2E0B
        LDA #$F8
        STA $2E09
        CLR $5FE2
        FCB $3E,$A6 ; copy actual S selector6 into X
        LDY #$2E0D
COPY_FRAME:
        LDA ,X+
        STA ,Y+
        CMPY #$2E19
        BNE COPY_FRAME
        LDS #$3FF0
REPORT:
''' +s[b:]
 s=s.replace('FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET','FDB RAM_FAIL,IRQ_HANDLER,RAM_FAIL,RAM_FAIL,RESET')
 (root/'probe.asm').write_text(s)
 m=dict(first=240,count=1,frame_size=27,run_id=run,case=case,source_sha256=hashlib.sha256(s.encode()).hexdigest(),initial_s=0x3ff0,seed_D=0x1234,seed_Y=0x2fa0,seed_U=0x3fe0,seed_DPword=0x2fa5)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 f.package();return root,run

def analyze(root,run):
 c=json.loads((root/'capture.json').read_text());assert c['validated'] and c['complete'] and len(c['frames'])==1
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['manifest'][key]
 frame=bytes.fromhex(c['frames'][0]['hex']);f.check_frame(frame,240,False,run);b=frame[9:25]
 r=dict(status=b[0],live_cc=b[1],entry_s=int.from_bytes(b[2:4],'big'),frame=b[4:].hex());(root/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(root.name,r,flush=True);return r

if __name__=='__main__':
 for case in ('masked','enabled','pending'):
  root=ROOT/'artifacts/irq-v2'/case;assert not (root/'capture.json').exists()
  root,run=build(case);r=collect(root,run);assert r['validated'],r['status'];analyze(root,run)
