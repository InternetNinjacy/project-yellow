#!/usr/bin/env python3
"""Verify a short map path using genuine PyBoy controller inputs.

Each command drives one attempted tile and checks observed map/coordinates.
No memory modifications. A blocked step is reported rather than silently
repeated. Starting state MUST have provenance documented by caller.
"""
import argparse
import json
from pathlib import Path
from pyboy import PyBoy
from yel_test_005_capture_audit import symbols
from yel_test_005_navigation import verify_step


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", required=True)
    p.add_argument("--sym", required=True)
    p.add_argument("--state", required=True,
                   help="Private emulator checkpoint with independently documented provenance")
    p.add_argument("--directions", required=True, help="JSON list of directional buttons")
    p.add_argument("--out", required=True)
    p.add_argument("--hold", type=int, default=8)
    p.add_argument("--settle", type=int, default=18)
    a = p.parse_args()
    moves = json.loads(Path(a.directions).read_text())
    if not isinstance(moves, list) or not moves:
        raise ValueError("Directions must be nonempty JSON list")
    if not 1 <= a.hold <= 8 or not 1 <= a.settle <= 120:
        raise ValueError("Unsafe input timing")
    syms = symbols(a.sym)
    for name in ("wCurMap", "wXCoord", "wYCoord"):
        if name not in syms:
            raise ValueError("Missing symbol " + name)
    emu = PyBoy(a.rom, window="null", cgb=False, sound_emulated=False)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        with open(a.state, "rb") as source:
            emu.load_state(source)
        emu.set_emulation_speed(0)
        def coordinates():
            return {"map": emu.memory[syms["wCurMap"][1]],
                    "x": emu.memory[syms["wXCoord"][1]],
                    "y": emu.memory[syms["wYCoord"][1]]}
        for i, direction in enumerate(moves):
            before = coordinates()
            emu.button_press(direction)
            try:
                emu.tick(a.hold)
            finally:
                emu.button_release(direction)
            emu.tick(a.settle)
            after = coordinates()
            shot = out / f"tile-{i:03d}.png"
            emu.screen.image.save(shot)
            record = {"index": i, "button": direction,
                      "before": before, "after": after}
            try:
                record["result"] = verify_step(before, after, direction)
            except AssertionError as error:
                record["result"] = "BLOCKED_OR_UNVERIFIED"
                record["error"] = str(error)
                results.append(record)
                break
            results.append(record)
        passed = len(results) == len(moves) and all(x["result"] == "verified_tile" for x in results)
        report = {"status": "PASS_TILE_NAVIGATION_ONLY" if passed else "FAIL_TILE_NAVIGATION",
                  "steps": results, "state_provenance": "UNVERIFIED_BY_THIS_RUNNER"}
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        if not passed:
            raise SystemExit(1)
    finally:
        emu.stop(save=False)


if __name__ == "__main__":
    main()
