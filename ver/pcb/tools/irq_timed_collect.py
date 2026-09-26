"""Collect one framed result or preserve a non-returning exact-sequence outcome."""
import hashlib,json,time
import framed_probe as framed
from pico_link import Pico

def collect(root,run):
 assert not (root/'capture.json').exists(), 'Use a fresh output directory'
 manifest=json.loads((root/'manifest.json').read_text());image=(root/'probe-128k.bin').read_bytes()
 for name,key in [('probe.asm','source_sha256'),('probe-128k.bin','image_sha256')]:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==manifest[key]
 result=dict(manifest=manifest,frames=[],snapshots=[],complete=False,validated=False)
 wire=bytearray();p=Pico();status='unresolved'
 try:
  result['device']={k:p.get(k) for k in ('build_config','diag_version','addr_mask')}
  assert result['device']['build_config']=='POG_27C020_70ns'
  assert p.set('rom_enable','0')=='0';paused=time.monotonic();p.end();p.set('addr_mask','0x1ffff')
  p.write(0,image);assert p.read(0,len(image))==image
  p.start(0x1dc00);time.sleep(max(0,3-(time.monotonic()-paused)));assert p.set('rom_enable','1')=='1'
  start=time.monotonic();count=manifest['count'];cursor=3;expected=[0x1a0,0x1a2,0x1a3]
  while time.monotonic()-start<max(6,count*2):
   wire.extend(p.poll());snapshot=p.events();snapshot['host_elapsed']=time.monotonic()-start;result['snapshots'].append(snapshot)
   if snapshot['dropped_bytes'] or snapshot['capture_stopped']:status='capture loss';break
   if len(wire)>=3 and wire[:3]==b'\xa0'*3:status='reentered boot marker before result';break
   if wire==b'\xa0\xf1':status='shared failure/vector handler reached before result';break
   if wire and wire[0]!=0xa0:status='unexpected first byte';break
   if len(result['frames'])<count and len(wire)>=cursor+27:
    seq=240+len(result['frames'])
    frame=bytes(wire[cursor:cursor+27]);framed.check_frame(frame,seq,False,run)
    result['frames'].append(dict(sequence=seq,hex=frame.hex()));cursor+=27
    expected.extend([0x100+b for b in frame]+[0])
    p.send(82,bytes([seq&255]));p.get('status')
   if len(result['frames'])==count and len(wire)>cursor:
    assert len(wire)==cursor+1 and wire[-1]==0xfe
    events={}
    for snap in result['snapshots']:
     for e in snap['events']:
      n=e['sequence'];assert n not in events or events[n]==e;events[n]=e
    expected.append(0x1fe)
    assert sorted(events)==list(range(len(expected)))
    assert [int(events[i]['address'],16) for i in sorted(events)]==expected
    result['complete']=result['validated']=True;status='returned';break
   time.sleep(.002)
  else:status='observation timeout'
 except Exception as error:
  status='collector failure';result['error']=str(error)
 finally:
  result.update(status=status,wire_hex=wire.hex())
  (root/'capture.json').write_text(json.dumps(result,indent=2)+'\n')
  try:p.end()
  finally:p.close()
 print(f'{root.parent.name}/{root.name}: {status}; {len(wire)} bytes',flush=True)
 return result
