#!/usr/bin/env python3
"""YEL-QOL-011: deterministic PyBoy storage regression harness.

A prepared, legally sourced PyBoy state and a reproducible scripted capture
sequence are required. This is NOT a boot smoke test. It fails closed when a
fixture is absent; no synthetic Pokémon are counted as emulator evidence.

Usage:
 python scripts/yel_qol_011_storage.py --rom pokeyellow.gbc \
   --sym pokeyellow.sym --state tests/fixtures/qol011/full_box.state \
   --sequence tests/fixtures/qol011/capture.json \
   --expected-active-box 1 --expected-count-delta 1

The JSON sequence is a list of {"button": "a", "frames": 1, "after": 30}
events, or {"frames": N} waits. State must be positioned immediately before
a deterministic capture; run once for each approved edge case.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pyboy import PyBoy

def symbols(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        tokens = line.split(';', 1)[0].split()
        if len(tokens) >= 2 and ':' in tokens[0]:
            bank, address = tokens[0].split(':', 1)
            try:
                result[tokens[1]] = (int(bank, 16), int(address, 16))
            except ValueError:
                pass
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rom', required=True)
    p.add_argument('--sym', required=True)
    p.add_argument('--state', required=True)
    p.add_argument('--sequence', required=True)
    p.add_argument('--expected-active-box', type=int, required=True,
                   help='zero-based active box after capture')
    p.add_argument('--expected-count-delta', type=int, choices=[0, 1], required=True)
    p.add_argument('--out', default='test-results/emulator/qol011')
    args = p.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    sym = symbols(args.sym)
    required = ('wCurrentBoxNum', 'wBoxDataStart', 'wBoxCount', 'wBoxDataEnd')
    missing = [name for name in required if name not in sym]
    if missing:
        raise RuntimeError(f'Missing ROM symbols: {missing}')
    steps = json.loads(Path(args.sequence).read_text())
    if not isinstance(steps, list) or not steps:
        raise ValueError('Capture sequence must be a nonempty JSON list')
    emu = PyBoy(args.rom, window='null', cgb=False, sound_emulated=False)
    report = {'work_id': 'YEL-QOL-011',
              'rom_sha256': hashlib.sha256(Path(args.rom).read_bytes()).hexdigest(),
              'state_sha256': hashlib.sha256(Path(args.state).read_bytes()).hexdigest(),
              'sequence_sha256': hashlib.sha256(Path(args.sequence).read_bytes()).hexdigest(),
              'status': 'FAIL'}
    try:
        emu.set_emulation_speed(0)
        with open(args.state, 'rb') as state:
            emu.load_state(state)
        def read(name):
            return emu.memory[sym[name][1]]
        def snapshot():
            a = sym['wBoxDataStart'][1]
            b = sym['wBoxDataEnd'][1]
            return {'active_box': read('wCurrentBoxNum') & 0x7f,
                    'count': read('wBoxCount'),
                    'working_box_sha256': hashlib.sha256(bytes(emu.memory[a:b])).hexdigest(),
                    'working_box_hex': bytes(emu.memory[a:b]).hex()}
        before = snapshot()
        for step in steps:
            frames = int(step.get('frames', 0))
            if frames < 0 or frames > 100000:
                raise ValueError('Invalid frame count')
            button = step.get('button')
            if button:
                emu.button_press(button)
            emu.tick(frames)
            if button:
                emu.button_release(button)
            emu.tick(int(step.get('after', 0)))
        after = snapshot()
        # Preserve complete working-box bytes for offline per-Pokémon field audits.
        # This is not equivalent to reading all twelve SRAM boxes.
        (out / 'before_working_box.bin').write_bytes(bytes.fromhex(before['working_box_hex']))
        (out / 'after_working_box.bin').write_bytes(bytes.fromhex(after['working_box_hex']))
        report.update(before={k:v for k,v in before.items() if k!='working_box_hex'},
                      after={k:v for k,v in after.items() if k!='working_box_hex'})
        assert after['active_box'] == args.expected_active_box, 'Unexpected selected box'
        if before['active_box'] == after['active_box']:
            assert after['count'] - before['count'] == args.expected_count_delta, 'Wrong box count delta'
            if args.expected_count_delta == 0:
                assert before['working_box_hex'] == after['working_box_hex'], ('Failed capture altered working box data')
        else:
            assert args.expected_count_delta == 1, 'Selection changed without a successful capture'
            assert after['count'] > 0, 'Switched to empty box but new capture was not stored'
        report['status'] = 'PARTIAL_PASS_ACTIVE_BOX_ONLY'
        report['warning'] = ('Active WRAM box assertions passed, but SRAM boxes, per-Pokémon '
                             'fields, full-box preservation, and save/reload are NOT yet '
                             'asserted. Do not mark storage integrity verified.')
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        emu.stop(save=False)
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
