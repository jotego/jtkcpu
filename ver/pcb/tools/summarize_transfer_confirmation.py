#!/usr/bin/env python3
"""Recheck fixed transfer captures and compare matching 3E/3F observations."""
import json
import transfer_confirmation as probe


def main():
    results = [probe.analyze(batch) for batch in range(len(probe.ENCODINGS))]
    assert all(not result['candidate_mismatch_indices'] for result in results)
    compared = 0
    for index in range(0, len(results), 2):
        for left, right in zip(results[index]['records'], results[index+1]['records']):
            assert {k: v for k, v in left['input'].items() if k != 'opcode'} == {
                k: v for k, v in right['input'].items() if k != 'opcode'}
            assert left['output'] == right['output']
            compared += 1
    summary = dict(records=sum(len(r['records']) for r in results),
                   matching_3e_3f_pairs=compared, candidate_mismatches=0,
                   encodings=[f'{op:02x}{post:02x}' for op, post in probe.ENCODINGS],
                   limitations='Four postbytes, twelve seed patterns, eight CC presets; selectors6/7 and other postbyte bits untested.')
    (probe.BASE / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
