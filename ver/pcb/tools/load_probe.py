#!/usr/bin/env python3
"""Pause ROM outputs, verify an image, arm read markers, and resume without reset wiring."""
import argparse,hashlib,json,time
from pathlib import Path
from pico_link import Pico

def main():
    a=argparse.ArgumentParser()
    a.add_argument('image',type=Path)
    a.add_argument('--seconds',type=float,default=6)
    a.add_argument('--pause',type=float,default=3)
    a.add_argument('--host-delay',type=float,default=0)
    a.add_argument('--poll-interval',type=float,default=.005)
    a.add_argument('--base',type=lambda s:int(s,0),default=0x1dc00)
    args=a.parse_args()
    if not 0 < args.poll_interval <= 1:
        a.error('--poll-interval must be greater than zero and at most one second')
    if args.pause < 3:
        a.error('--pause must be at least three seconds for watchdog recovery')
    if args.seconds <= 0:
        a.error('--seconds must be positive')
    b=args.image.read_bytes()
    if len(b)!=131072: raise ValueError('Expected 128 KiB program image')
    p=Pico()
    records=[]
    try:
        context={k:p.get(k) for k in ('name','build_config','diag_version')}
        assert context['build_config'] == 'POG_27C020_70ns', 'This probe is validated only with POG firmware'
        context.update(image_sha256=hashlib.sha256(b).hexdigest(),comms_base=args.base,
                       pause_seconds=args.pause,host_delay_seconds=args.host_delay,
                       observation_seconds=args.seconds,poll_interval_seconds=args.poll_interval)
        args.image.with_suffix('.device.json').write_text(json.dumps(context,indent=2)+'\n')
        assert p.set('rom_enable','0')=='0'
        paused=time.monotonic()
        p.end()
        p.set('addr_mask','0x1ffff')
        p.write(0,b)
        assert p.read(0,len(b))==b, 'Image readback mismatch; outputs remain disabled'
        p.start(args.base)
        assert p.read(args.base,4)==b'PICO'
        time.sleep(max(0,args.pause-(time.monotonic()-paused)))
        print(f'Verified {len(b)} bytes; paused for {time.monotonic()-paused:.3f}s',flush=True)
        assert p.set('rom_enable','1')=='1'
        if args.host_delay:
            time.sleep(args.host_delay)
            print('Before host polling:',json.dumps(p.events(args.base)),flush=True)
        start=time.monotonic()
        while time.monotonic()-start<args.seconds:
            time.sleep(args.poll_interval)
            received=p.poll()
            s=p.events(args.base)
            s['received_hex']=received.hex()
            s['host_elapsed']=time.monotonic()-start
            records.append(s)
        args.image.with_suffix('.events.json').write_text(json.dumps(records,indent=2)+'\n')
        print(f"Captured {len(records)} snapshots, {len(p.received)} USB bytes, "
              f"{records[-1]['count']} events, {records[-1]['dropped_bytes']} dropped bytes")
    finally:
        try:
            p.end()
        finally:
            p.close()

if __name__=='__main__': main()
