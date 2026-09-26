#!/usr/bin/env python3
"""Independently audit hashes, CPU frames and complete recorded USB event traces."""
import argparse
import hashlib
import json
from pathlib import Path
from framed_probe import check_frame


def audit(path):
    capture = json.loads(path.read_text())
    assert capture['validated'] and capture['complete'], path
    manifest = capture['manifest']
    for filename, key in [('probe.asm', 'source_sha256'), ('probe-128k.bin', 'image_sha256')]:
        assert hashlib.sha256((path.parent / filename).read_bytes()).hexdigest() == manifest[key]
    assert len(capture['frames']) == manifest['count']
    frames = []
    for index, item in enumerate(capture['frames']):
        frame = bytes.fromhex(item['hex'])
        check_frame(frame, manifest['first'] + index, False, manifest['run_id'])
        frames.append(frame)
    wire = bytes.fromhex(capture['wire_hex'])
    prefix_length = len(wire) - sum(map(len, frames)) - 1
    prefix = wire[:prefix_length]
    assert prefix in (bytes([0xa0]), bytes([0xa0, 0xa2, 0xa3]))
    assert wire == prefix + b''.join(frames) + bytes([0xfe])
    events = {}
    for snapshot in capture['snapshots']:
        assert not snapshot['dropped_bytes'] and not snapshot['capture_stopped']
        for event in snapshot['events']:
            sequence = event['sequence']
            assert sequence not in events or events[sequence] == event
            events[sequence] = event
    expected = [0x100 + byte for byte in prefix]
    for frame in frames:
        expected.extend(0x100 + byte for byte in frame)
        expected.append(0)  # CPU consumes the host ACK.
    expected.append(0x1fe)
    if events[0]['address'] == '0x0':
        assert prefix == bytes([0xa0])
        expected.insert(0, 0)  # Deferred capture's initial A5 request.
    assert sorted(events) == list(range(len(expected)))
    assert [int(events[i]['address'], 16) for i in sorted(events)] == expected
    assert capture['snapshots'][-1]['count'] == len(expected)
    return len(frames)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+', type=Path)
    args = parser.parse_args()
    count = sum(audit(path) for path in args.captures)
    print(f'Validated {len(args.captures)} captures / {count} CPU frames')
