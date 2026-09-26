#!/usr/bin/env python3
"""Generate bounded ROM timing batches and analyze physical PicoROM captures."""
from pcb_paths import MODULE, ROOT, TEMPLATES
import argparse, hashlib, json, re, statistics
from pathlib import Path
OUT=ROOT/'artifacts/instruction-timing'
SOURCE=MODULE / 'doc/mame/6x09dasm.cpp'
COUNTS=[0,128,256,512]
FAMILY="scalar"
BATCH_SIZE=6
BLOCK_DELAY=0xffff

def inventory():
    s=SOURCE.read_text().split('konami_disassembler::konami_opcodes[] =')[1].split('\n};')[0]
    rows=[]
    for op,length,name,mode in re.findall(r'\{\s*(0x[0-9A-Fa-f]+),\s*(\d+),\s*"([^"]+)",\s*(\w+)',s):
        rows.append(dict(opcode=int(op,16),mnemonic=name,base_length=int(length),mode=mode,timing_status='pending',flags_status='pending'))
    assert len(rows)==197 and len({x['opcode'] for x in rows})==197
    return rows

def branch_taken(code, cc):
    c,v,z,n=[bool(cc&(1<<bit)) for bit in range(4)]
    answer=[True,not c and not z,not c,not z,not v,not n,n==v,not z and n==v][code&7]
    return not answer if code&0x10 else answer

def cases():
    if FAMILY=='pc':
        from pc_timing_cases import cases as pc_cases
        return pc_cases()
    if FAMILY=='indexed':
        from indexed_timing_cases import cases as indexed_cases
        return indexed_cases()
    if FAMILY=='paired':
        from paired_timing_cases import cases as paired_cases
        return paired_cases()
    if FAMILY=='control':
        rows=[]
        for code,name in ((0xa8,'JMP'),(0xa9,'JSR')):
            rows.append(dict(id=len(rows)+1,opcode=code,mnemonic=name,mode='EXT',
                encoding=f'{code:02x}07',dynamic_target=True,operand='next opcode address',
                coverage='extended target is next opcode; actual address operands are in ROM image; other targets/modes pending'))
        for code,name,frame,stack,full,encoding in (
                (0x8f,'RTS',2,'S',False,'8f'),
                (0x9f,'RTI',3,'S',False,'9f'),
                (0x9f,'RTI',12,'S',True,'9f'),
                (0x0e,'PULLS',2,'S',False,'0e80'),
                (0x0f,'PULLU',2,'U',False,'0f80'),
                (0x0e,'PULLS',12,'S',False,'0eff'),
                (0x0f,'PULLU',12,'U',False,'0fff')):
            rows.append(dict(id=len(rows)+1,opcode=code,mnemonic=name,mode='STACK',encoding=encoding,
                frame_bytes=frame,frame_full=full,stack=stack,
                operand=f'{frame}-byte frame on {stack}',setup_extra=f'        LD{stack} #$2000\n',
                coverage='preloaded return chain in verified RAM, frames initialized outside timing window; other frame data/addresses pending'))
        return rows
    if FAMILY=='transfer_stack':
        rows=[]
        regs=['A','B','X','Y','S','U']
        for code,name in ((0x3e,'EXG'),(0x3f,'TFR')):
            for src in range(6):
                for dst in range(6):
                    rows.append(dict(id=len(rows)+1,opcode=code,mnemonic=name,mode='IMM_RR',
                        encoding=bytes([code,(dst<<4)|src]).hex(),operand=f'{regs[src]},{regs[dst]}',
                        coverage='known register pair; fixed initial registers; other operand values and aliases pending'))
        for code,name in ((0x0c,'PUSHS'),(0x0d,'PUSHU'),(0x0e,'PULLS'),(0x0f,'PULLU')):
            pull=code>=0x0e
            masks=[0,1,2,4,8,16,32,64]+([127] if pull else [128,255])
            for mask in masks:
                ident=len(rows)+1
                preflight=''
                if pull:
                    preflight=f'        LDX #$2000\n        LDA #$50\nFILL{ident}:\n        STA ,X+\n        CMPX #$4000\n        BNE FILL{ident}\n'
                stack='S' if code in (0x0c,0x0e) else 'U'
                rows.append(dict(id=ident,opcode=code,mnemonic=name,mode='STACK',
                    encoding=bytes([code,mask]).hex(),stack_mask=mask,
                    setup_extra=f'        LD{stack} #${0x2000 if pull else 0x3ff0:04X}\n',
                    preflight=preflight,coverage='selected stack mask; RAM contents 50 for pulls; PC pulls and other masks pending'))
        for code,name in ((0xaa,'BSR'),(0xab,'LBSR')):
            rows.append(dict(id=len(rows)+1,opcode=code,mnemonic=name,mode='REL' if code==0xaa else 'LREL',
                encoding=bytes([code]+[0]*(1 if code==0xaa else 2)).hex(),
                coverage='zero displacement call to following opcode, return addresses retained in verified RAM; other displacements pending'))
        return rows
    rows=[]
    excluded={0x8f,0x9f,0xb3,0xb4,0xb5,0xb6,0xb7,0xcf,0xd0}
    for op in inventory():
        code=op['opcode']; mode=op['mode']
        if FAMILY=='shift':
            if not 0xb8<=code<=0xc1: continue
            for count in (0,1,2,7,8,15,16,17,31,32,255):
                memory=bool(code&1)
                encoding=bytes([code,0x07,0x2f,0x00] if memory else [code,count])
                setup=''
                if memory:
                    setup=f'        LDD #$1234\n        STD $2F00\n        LDA #${count:02X}\n        ANDCC #$50\n        ORCC #$50\n'
                rows.append(dict(id=len(rows)+1,opcode=code,mnemonic=op['mnemonic'],
                    mode='EXT' if memory else mode,encoding=encoding.hex(),shift_count=count,
                    setup_extra=setup,coverage='fixed shift count; evolving operand from 1234; other operand/addressing variants pending'))
            continue
        if FAMILY=='branch':
            if not 0x60<=code<=0x7f: continue
            for outcome in (False,True):
                choices=[cc for cc in range(16) if branch_taken(code,cc)==outcome]
                if not choices: continue
                cc=choices[0]; ident=len(rows)+1
                name=op['mnemonic']
                pre=f'        ANDCC #$50\n        ORCC #${0x50|cc:02X}\n        {name} CK{ident}_TAKEN\n'
                pre += f'        JMP {"RAM_FAIL" if outcome else "CK"+str(ident)+"_OK"}\n'
                pre += f'CK{ident}_TAKEN:\n'
                if not outcome: pre += '        JMP RAM_FAIL\n'
                pre += f'CK{ident}_OK:\n'
                rows.append(dict(id=ident,opcode=code,mnemonic=name,mode=mode,
                    encoding=bytes([code]+[0]*(op['base_length']-1)).hex(),
                    coverage='zero displacement; nonzero functional outcome check; other displacements pending',
                    taken=outcome,cc_low=cc,setup_extra=f'        ORCC #${0x50|cc:02X}\n',preflight=pre))
            continue
        if FAMILY=='memory':
            if mode!='IND' or code in {0xa8,0xa9,0xb9,0xbb,0xbd,0xbf,0xc1}: continue
            operand=[0x07,0x2f,0x00]
            mode='EXT'
        elif mode=='INH' and code not in excluded:
            operand=[]
        elif mode=='IMM' and code<0x60:
            value={0x38:0,0x3c:0x50,0x3d:0x50}.get(code,0x55 if op['base_length']==2 else 0x2f00)
            operand=list(value.to_bytes(op['base_length']-1,'big'))
        else: continue
        rows.append(dict(id=len(rows)+1,opcode=code,mnemonic=op['mnemonic'],mode=mode,
                         encoding=bytes([code]+operand).hex(),coverage='repeated encoding from fixed seed; operand variants pending'))
    return rows

# Stackless RAM validation; service the physical watchdog once per sweep, never per byte.
RAM='''        LDX #$2000
        LDA #$55
RAM_FILL:
        STA ,X+
        CMPX #$4000
        BNE RAM_FILL
        TST $5FEA
        LDX #$2000
RAM_55:
        LDA ,X
        CMPA #$55
        LBNE RAM_FAIL
        LDA #$AA
        STA ,X+
        CMPX #$4000
        BNE RAM_55
        TST $5FEA
        LDX #$2000
RAM_AA:
        LDA ,X
        CMPA #$AA
        LBNE RAM_FAIL
        CLRA
        STA ,X+
        CMPX #$4000
        BNE RAM_AA
        TST $5FEA
        LDX #$2000
RAM_ZERO:
        LDA ,X+
        LBNE RAM_FAIL
        CMPX #$4000
        BNE RAM_ZERO
        TST $5FEA
        LDA $DFA0
'''
SETUP='''        LDS #$3FF0
        LDU #$2F20
        LDY #$2F10
        LDX #$2F00
        LDD #$1234
        ANDCC #$50
        ORCC #$50
'''

def prepare_frames(case,label):
    size=case.get('frame_bytes')
    if not size:return ''
    step=len(bytes.fromhex(case['encoding']))
    text=f'        LDX #$2000\n        LDY #{label}_BODY+{step}\n{label}_FRAME:\n'
    if size==3:text+='        LDA #$50\n        STA ,X+\n'
    elif size==12:
        for word in ((0xd012 if case['frame_full'] else 0x5012),0x3400,0x2f00,0x2f10,0x2f20):
            text+=f'        LDD #${word:04X}\n        STD ,X++\n'
    text+=f'        STY ,X++\n        LEAY {step},Y\n        CMPX #${0x2000+512*size:04X}\n        BNE {label}_FRAME\n'
    return text

def generate(batch):
    rows=cases()[batch*BATCH_SIZE:(batch+1)*BATCH_SIZE]
    if not rows: raise ValueError('No such batch')
    folder=OUT/f'batch-{batch:02d}'; folder.mkdir(parents=True,exist_ok=True)
    prefix=(TEMPLATES / 'bootstrap.asm').read_text().split('        LDA $DF10')[0]
    pieces=[prefix,RAM,'LOOP_BEGIN:\n']
    for case in rows:
        pieces.append(case.get('preflight',''))
        for size,n in enumerate(COUNTS):
            label=f'C{case["id"]}_N{n}'
            pieces.append(f'''{label}:
        LDX #${BLOCK_DELAY:04X}
{label}_DELAY:
        LEAX -1,X
        BNE {label}_DELAY
        TST $5FEA
''')
            pieces.append(prepare_frames(case,label))
            pieces.append(case.get('pre_window','').format(label=label))
            pieces.append(f'''
        LDA $DF{case['id']:02X}
        LDA $DF{0xd0+size:02X}
        LDA $DFE1
''')
            pieces.append(SETUP+case.get("setup_extra",""))
            encoding=bytes.fromhex(case.get('unit_encoding',case['encoding']))
            line='        FCB '+','.join(f'${b:02X}' for b in encoding)+'\n'
            if case.get('dynamic_target'):line+='        FDB *+2\n'
            if 'dynamic_pc_target' in case:line+=f"        FDB (${case['dynamic_pc_target']:04X}-*)&$FFFF\n"
            if case.get('frame_bytes'):pieces.append(f'{label}_BODY:\n')
            pieces.extend([line]*n)
            pieces.append(case.get('capture_asm',''))
            pieces.append('        LDA $DFE2\n')
            if n:pieces.append(case.get('postflight',''))
            if n and 'cc_check' in case:
                mask,value=case['cc_check']
                pieces.append(f'        ANDB #${mask:02X}\n        CMPB #${value:02X}\n        LBNE RAM_FAIL\n')
            if n:
                for reg,(initial,delta) in case.get('post_registers',{}).items():
                    pieces.append(f'        CMP{reg} #${(initial+n*delta)&0xffff:04X}\n        LBNE RAM_FAIL\n')
                if 'saved_d' in case:
                    pieces.append(f"        LDD $3F00\n        CMPD #${case['saved_d']:04X}\n        LBNE RAM_FAIL\n")
            if case.get('frame_bytes'):
                pieces.append(f"        CMP{case['stack']} #${0x2000+n*case['frame_bytes']:04X}\n        LBNE RAM_FAIL\n")
            elif case.get('dynamic_target') and case['opcode']==0xa9:
                pieces.append(f'        CMPS #${0x3ff0-2*n:04X}\n        LBNE RAM_FAIL\n')
    pieces.append(f'''        JMP LOOP_BEGIN
RAM_FAIL:
        LDA $DFF1
FAULT_IDLE:
        LDX #$FFFF
FAULT_DELAY:
        LEAX -1,X
        BNE FAULT_DELAY
        TST $5FEA
        BRA FAULT_IDLE
        ORG $FFF6
        FDB RAM_FAIL,RAM_FAIL,RAM_FAIL,RAM_FAIL,RESET
''')
    text=''.join(pieces)
    (folder/'timing.asm').write_text(text)
    meta=dict(cases=rows,counts=COUNTS,clock_hz=12000000,clock_source='User-confirmed 053248 CLK input',watchdog_delay_loop=BLOCK_DELAY,
              source_sha256=hashlib.sha256(text.encode()).hexdigest(),setup=SETUP)
    (folder/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(folder)

def package(folder):
    b=(folder/'fixed.bin').read_bytes()
    assert len(b)==32768
    assert b[0x5c00:0x6000]==b'\xff'*1024, 'Program overlaps communications window'
    meta=json.loads((folder/'manifest.json').read_text())
    for case in meta['cases']:
        prefix=bytes.fromhex(case.get('unit_encoding',case['encoding']))
        if 'dynamic_pc_target' in case:
            repeats=max(meta['counts']);matches=[]
            for pos in range(len(b)-4*repeats):
                if b[pos:pos+2]!=prefix:continue
                if all(b[pos+4*i:pos+4*i+2]==prefix and (0x8000+pos+4*i+2+int.from_bytes(b[pos+4*i+2:pos+4*i+4],'big'))&0xffff==case['dynamic_pc_target'] for i in range(repeats)):
                    matches.append(pos)
            assert matches,'No valid repeated PC-relative target chain'
        elif case.get('dynamic_target'):
            matches=[]
            for pos in range(len(b)-2048):
                if b[pos:pos+2]!=prefix:continue
                if all(b[pos+4*i:pos+4*i+2]==prefix and int.from_bytes(b[pos+4*i+2:pos+4*i+4],'big')==0x8000+pos+4*i+4 for i in range(512)):
                    matches.append(pos)
            assert matches, 'No valid 512-instruction forward target chain'
        else:assert prefix*max(meta['counts']) in b
    image=bytes(0x18000)+b
    (folder/'timing-128k.bin').write_bytes(image)
    meta['image_sha256']=hashlib.sha256(image).hexdigest()
    (folder/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')

def analyze(folder):
    meta=json.loads((folder/'manifest.json').read_text())
    counts=meta['counts']
    image=folder/'timing-128k.bin'
    assert hashlib.sha256(image.read_bytes()).hexdigest()==meta['image_sha256'], 'Image hash mismatch'
    assert hashlib.sha256((folder/'timing.asm').read_bytes()).hexdigest()==meta['source_sha256'], 'Source hash mismatch'
    context_path=image.with_suffix('.device.json')
    if context_path.exists():
        context=json.loads(context_path.read_text())
        assert context['image_sha256']==meta['image_sha256'], 'Capture/image mismatch'
        assert context['build_config']=='POG_27C020_70ns', 'Wrong physical board variant'
        assert context['comms_base']==0x1dc00
    snapshots=json.loads(image.with_suffix('.events.json').read_text())
    events={}
    for snapshot in snapshots:
        for event in snapshot['events']:
            seq=event['sequence']
            assert seq not in events or events[seq]==event, 'Conflicting event snapshots'
            events[seq]=event
    assert sorted(events)==list(range(snapshots[-1]['count'])), 'Missing capture records'
    assert all(r['dropped_bytes']==0 and not r['capture_stopped'] for r in snapshots)
    lookup={c['id']:c for c in meta['cases']}
    samples={i:{n:[] for n in counts} for i in lookup}
    state='case'; case=size=start=None; boots=0
    for _,e in sorted(events.items()):
        value=int(e['address'],16)-0x100
        if value==0xa0:
            boots+=1; assert boots==1, 'Unexpected restart'; continue
        assert value!=0xf1, 'RAM test or interrupt failure'
        if state=='case':
            assert value in lookup,e
            case=value; state='size'
        elif state=='size':
            assert 0xd0<=value<=0xd3,e
            size=counts[value-0xd0]; state='start'
        elif state=='start':
            assert value==0xe1,e
            start=e['time_us']; state='end'
        else:
            assert value==0xe2,e
            samples[case][size].append((e['time_us']-start)&0xffffffff); state='case'
    assert boots==1
    results=[]
    for i,by_n in samples.items():
        assert min(map(len,by_n.values()))>=4,(i,{n:len(s) for n,s in by_n.items()})
        stats={n:dict(samples=len(s),min_us=min(s),median_us=statistics.median(s),max_us=max(s)) for n,s in by_n.items()}
        ys=[stats[n]['median_us'] for n in counts]
        xm=statistics.mean(counts); ym=statistics.mean(ys)
        slope=sum((n-xm)*(y-ym) for n,y in zip(counts,ys))/sum((n-xm)**2 for n in counts)
        clocks=slope*12; nearest=round(clocks)
        residual=max(abs(y-(ym+slope*(n-xm))) for n,y in zip(counts,ys))
        assert abs(clocks-nearest)<0.15 and residual<=2.0,(i,clocks,residual)
        result=dict(**lookup[i],input_clocks=nearest,fitted_input_clocks=clocks,max_fit_residual_us=residual,statistics=stats)
        results.append(result)
    indexed={r['id']:r for r in results}
    for r in results:
        if r.get('measurement_role')=='paired':
            base=indexed[r['baseline_case_id']]
            assert base['measurement_role']=='baseline'
            r['unit_input_clocks']=r['input_clocks']
            r['unit_fitted_input_clocks']=r['fitted_input_clocks']
            r['input_clocks']-=base['input_clocks']
            r['fitted_input_clocks']-=base['fitted_input_clocks']
            r['baseline_input_clocks']=base['input_clocks']
            r['unit_max_fit_residual_us']=r['max_fit_residual_us']
            ys=[r['statistics'][n]['median_us']-base['statistics'][n]['median_us'] for n in counts]
            xm=statistics.mean(counts);ym=statistics.mean(ys)
            r['max_fit_residual_us']=max(abs(y-(ym+r['fitted_input_clocks']/12*(n-xm))) for n,y in zip(counts,ys))
            assert r['max_fit_residual_us']<=2.0
            assert r['input_clocks']>0 and abs(r['fitted_input_clocks']-r['input_clocks'])<0.15
        suffix=f" [{r['measurement_role']}]" if 'measurement_role' in r else ''
        print(f"{r['opcode']:02X} {r['mnemonic']:12s} {r['encoding']:8s}: {r['input_clocks']:4d} CLK ({r['fitted_input_clocks']:.4f} fitted){suffix}")
    (folder/'results.json').write_text(json.dumps(dict(manifest=meta,results=results),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['inventory','generate','package','analyze']);p.add_argument('batch',type=int,nargs='?',default=0)
    p.add_argument('--family',choices=['scalar','memory','branch','shift','transfer_stack','control','paired','indexed','pc'],default='scalar');a=p.parse_args()
    FAMILY=a.family
    if FAMILY!='scalar': OUT=OUT/FAMILY
    if FAMILY=='paired':BATCH_SIZE=2;COUNTS=[0,64,128,256]
    if FAMILY in ('indexed','pc'):COUNTS=[0,64,128,256]
    if FAMILY=='memory':
        SETUP='        LDD #$1234\n        STD $2F00\n'+SETUP
    OUT.mkdir(parents=True,exist_ok=True)
    if a.action=='inventory':
        (OUT/'inventory.json').write_text(json.dumps(inventory(),indent=2)+'\n')
        (OUT/'initial-cases.json').write_text(json.dumps(cases(),indent=2)+'\n')
        print(f'{len(inventory())} known primary opcodes; {len(cases())} initial timing cases')
    elif a.action=='generate':generate(a.batch)
    elif a.action=='package':package(OUT/f'batch-{a.batch:02d}')
    else:analyze(OUT/f'batch-{a.batch:02d}')
