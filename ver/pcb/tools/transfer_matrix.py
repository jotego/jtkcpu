"""All transfer postbytes with initialized RAM destinations for PC/S/U values."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
from pcb_paths import ROOT
TOOLS=Path(__file__).resolve().parent
import framed_probe as framed
from screen_collect import collect
SEED=dict(D=0x3333,X=0x2f80,Y=0x2fa0,DPword=0x2fc0,U=0x3800,S=0x3900,CC=0x5f)

def configure(op,half):
 root=ROOT/'artifacts/transfer-matrix'/f'{op:02x}-{half}';framed.ROOT=root
 return root,0x5000+(op-0x3e)*256+half*128

def build(op,half):
 root,run=configure(op,half);assert not (root/'capture.json').exists();framed.COUNT=128;framed.generate()
 s=(root/'probe.asm').read_text().replace('LDD #$7B01',f'LDD #${run:04X}').replace('CMPD #$0150','CMPD #$0170')
 first=s.index('        LDX #$2E09');last=s.index('; CRC-16/CCITT-FALSE',first)
 code=''
 for i,address in enumerate((0x3333,0x2f80,0x2fa0,0x2fc0,0x3800,0x3900,0x3c02)):
  code+=f'''        LDX #${address:04X}
        LDY #16
        LDA #$AE
STUB_{i}:
        STA ,X+
        LEAY -1,Y
        BNE STUB_{i}
        LDD #$A807
        STD ,X++
        LDD #CAPTURE
        STD ,X
'''
 code+=f'''        LDA #${op:02X}
        STA $3C00
        LDB $2E43
        SUBB #$F0
        ADDB #${half*128:02X}
        STB $3C01
        LDS #$3900
        LDX #$2FC0
        FCB $3E,$42
        LDD #$3333
        LDX #$2F80
        LDY #$2FA0
        LDU #$3800
        ANDCC #0
        ORCC #$5F
        JMP $3C00
CAPTURE:
        PSHS CC
        STD $2E0C
        STX $2E0E
        STY $2E10
        PULS A
        STA $2E16
        STU $2E12
        STS $2E14
        LDS #$3FF0
        LDX #0
        FCB $3E,$42
        STX $2E17
        LDA #${op:02X}
        STA $2E09
        LDB $2E43
        SUBB #$F0
        ADDB #${half*128:02X}
        STB $2E0A
        LDA #$F9
        STA $2E0B
'''
 s=s[:first]+code+s[last:];(root/'probe.asm').write_text(s)
 m=dict(first=240,count=128,frame_size=27,run_id=run,opcode=op,half=half,seed=SEED,source_sha256=hashlib.sha256(s.encode()).hexdigest(),ram_instruction_address=0x3c00,pc_value=0x3c02,padding_bytes=16)
 (root/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (root/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','probe.asm','-L'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','probe.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 framed.package()

def prediction(post, transfer_bit=True):
 r=SEED.copy();values=[0x3333,0x3333,r['X'],r['Y'],r['DPword'],r['U'],r['S'],0x3c02]
 src=post&7;dst=(post>>4)&7
 def write(sel,value):
  if sel==0:r['D']=(r['D']&255)|((value&255)<<8)
  elif sel==1:r['D']=(r['D']&0xff00)|(value&255)
  elif sel!=7:r[{2:'X',3:'Y',4:'DPword',5:'U',6:'S'}[sel]]=value
 write(dst,values[src])
 if not transfer_bit or not post&0x80:write(src,values[dst])
 return r

def analyze(op,half):
 root,run=configure(op,half);c=json.loads((root/'capture.json').read_text());assert c['validated'] and c['complete'] and len(c['frames'])==128
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==c['manifest'][key]
 rows=[];mismatches=[]
 for i,f in enumerate(c['frames']):
  frame=bytes.fromhex(f['hex']);framed.check_frame(frame,240+i,False,run);b=frame[9:25];post=half*128+i
  assert b[:3]==bytes([op,post,0xf9])
  r=dict(D=int.from_bytes(b[3:5],'big'),X=int.from_bytes(b[5:7],'big'),Y=int.from_bytes(b[7:9],'big'),U=int.from_bytes(b[9:11],'big'),S=int.from_bytes(b[11:13],'big'),CC=b[13],DPword=int.from_bytes(b[14:16],'big'))
  row=dict(postbyte=post,registers=r);rows.append(row)
  if r!=prediction(post):mismatches.append(dict(**row,expected=prediction(post)))
 result=dict(opcode=op,half=half,records=rows,bit7_transfer_model_mismatches=mismatches)
 (root/'results.json').write_text(json.dumps(result,indent=2)+'\n');print(f'{op:02x}-{half}: {len(rows)} records, {len(mismatches)} model mismatches',flush=True)
 for row in mismatches[:8]:print(row,flush=True)
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['build','collect','analyze']);p.add_argument('opcode',type=lambda x:int(x,16));p.add_argument('half',type=int,choices=(0,1));a=p.parse_args();assert a.opcode in (0x3e,0x3f)
 if a.action=='build':build(a.opcode,a.half)
 elif a.action=='analyze':analyze(a.opcode,a.half)
 else:root,run=configure(a.opcode,a.half);collect(root,run)
