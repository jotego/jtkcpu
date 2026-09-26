"""Repeated ROM/RAM instruction streams at controlled entry alignments."""
import sys,json,hashlib,subprocess
from pathlib import Path
from pcb_paths import ROOT
TOOLS=Path(__file__).resolve().parent
import instruction_timing as t

def cases():
 rows=[]
 units=[('NOP','ae'),('INCA','89'),('LDA80','1080'),('NOP_INCA_LDA','ae891080'),('INCA_LDA_NOP','891080ae'),('COPY_Y_X_3E','3ea3'),('COPY_Y_X_3F','3fa3'),('COPY_S_X','3ea6'),('COPY_PC_X','3ea7'),('EXG_S_X_pair','3e263e26')]
 for mode in ('ROM','RAM'):
  for offset in (0,1):
   for name,enc in units:
    rows.append(dict(id=len(rows)+1,opcode=int(enc[:2],16),mnemonic=name,encoding=enc,mode=mode,offset=offset,coverage='Repeated stream through JSR/RTS; counts0/128/256/512; body entry controlled modulo256'))
 return rows

t.OUT=ROOT/'artifacts/stream-timing';t.cases=cases;t.BATCH_SIZE=4

def build(batch):
 folder=t.OUT/f'batch-{batch:02d}';assert not (folder/'timing-128k.events.json').exists();t.generate(batch)
 s=(folder/'timing.asm').read_text();rows=cases()[batch*4:(batch+1)*4]
 for row in rows:
  unit=bytes.fromhex(row['encoding']);line='        FCB '+','.join(f'${b:02X}' for b in unit)+'\n'
  for n in t.COUNTS:
   label=f'C{row["id"]}_N{n}';start=s.index(label+':\n');end=s.index('        LDA $DFE2\n',start)
   part=s[start:end];assert part.endswith(line*n if n else t.SETUP)
   prefix=part[:len(part)-len(line)*n] if n else part
   target=f'{label}_DATA' if row['mode']=='ROM' else f'${0x2000+row["offset"]:04X}'
   body=f'''        JSR {target}
        JMP {label}_DONE
        ALIGN 256
'''+('        FCB $AE\n'*row['offset'])+f'{label}_DATA:\n'+line*n+f'        RTS\n{label}_DONE:\n'
   if row['mode']=='RAM':
    copy=f'''        LDX #{label}_DATA
        LDY #${0x2000+row['offset']:04X}
        LDU #{len(unit)*n+1}
{label}_COPY:
        LDA ,X+
        STA ,Y+
        LEAU -1,U
        CMPU #0
        BNE {label}_COPY
'''
    prefix=prefix.replace(f'        LDA $DF{row["id"]:02X}\n',copy+f'        LDA $DF{row["id"]:02X}\n')
   s=s[:start]+prefix+body+s[end:]
 (folder/'timing.asm').write_text(s)
 m=json.loads((folder/'manifest.json').read_text());m['source_sha256']=hashlib.sha256(s.encode()).hexdigest();(folder/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with (folder/'assembly.log').open('w') as log:
  subprocess.run(['asl','-cpu','052001','timing.asm','-L'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
  subprocess.run(['p2bin','timing.p','fixed.bin','-r','0x8000-0xffff','-l','255'],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
 t.package(folder);return folder

if __name__=='__main__':
 for batch in range(10):
  folder=build(batch)
  subprocess.run([sys.executable,str(TOOLS/'load_probe.py'),str(folder/'timing-128k.bin'),'--seconds','16','--poll-interval','.002'],check=True)
  t.analyze(folder)
