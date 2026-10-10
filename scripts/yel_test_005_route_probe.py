#!/usr/bin/env python3
"""Read-only per-step ROM gameplay probe for YEL-TEST-005.

All execution starts at clean boot; snapshots are telemetry, not assertions
that a scenario has been accomplished. No state mutation or debug shortcut.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pyboy import PyBoy
from yel_test_005_capture_audit import symbols, inspect
from yel_test_005_replay import validate

FIELDS = ("wCurMap", "wXCoord", "wYCoord", "wPartyCount",
          "wNumBagItems", "wIsInBattle", "wEnemyMonSpecies2",
          "wCurrentMenuItem")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", required=True)
    p.add_argument("--sym", required=True)
    p.add_argument("--trace", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--require-debug-setup", action="store_true", help="Require six party members and Poké Balls")
    p.add_argument("--require-movement", action="store_true", help="Fail unless an input changes actual player coordinates")
    a = p.parse_args()
    steps = json.loads(Path(a.trace).read_text())
    validate(steps)
    syms = symbols(a.sym)
    absent = [x for x in FIELDS if x not in syms]
    if absent:
        raise ValueError("Missing symbols: " + ", ".join(absent))
    dest = Path(a.out)
    dest.mkdir(parents=True, exist_ok=True)
    emu = PyBoy(a.rom, window="null", cgb=False, sound_emulated=False)
    emu.set_emulation_speed(0)
    rows = []
    try:
        frame = 0
        for i, st in enumerate([{"frames": 0}] + steps):
            button = st.get("button")
            frames, after = st.get("frames", 0), st.get("after", 0)
            buttons = st.get("buttons", [button] if button else [])
            for pressed in buttons:
                emu.button_press(pressed)
            try:
                if frames:
                    emu.tick(frames)
            finally:
                for pressed in buttons:
                    emu.button_release(pressed)
            if after:
                emu.tick(after)
            frame += frames + after
            record = {"step": i, "frame": frame, "input": st}
            for x in FIELDS:
                bank, addr = syms[x]
                if not 0xC000 <= addr <= 0xDFFF:
                    raise AssertionError(f"{x} not WRAM: {bank:02X}:{addr:04X}")
                record[x] = emu.memory[addr]
            filename = dest / f"step-{i:03d}.png"
            emu.screen.image.save(filename)
            record["screenshot_sha256"] = sha(filename)
            rows.append(record)
            print(json.dumps(record), flush=True)
        moved = any((a["wXCoord"], a["wYCoord"]) != (b["wXCoord"], b["wYCoord"]) and a["wCurMap"] == b["wCurMap"] for a,b in zip(rows[1:], rows[:-1]))
        if a.require_movement and not moved:
            raise AssertionError("No actual player movement recorded")
        result = inspect(emu.memory, syms)
        result["actual_coordinate_movement"] = moved
        if a.require_debug_setup and not (result["checks"]["six_party_members"] and result["checks"]["has_poke_ball"]):
            raise AssertionError("DEBUG setup failed: six-member party and Poké Balls not established")
        result["steps"] = rows
        result["rom_sha256"] = sha(a.rom)
        result["symbols_sha256"] = sha(a.sym)
        result["trace_sha256"] = sha(a.trace)
        result["status"] = ("CAPTURE_PRECONDITIONS_PASS_PROMPT_UNVERIFIED" if
                            result["capture_preconditions_pass"] else
                            "CAPTURE_PRECONDITIONS_FAIL")
        (dest / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        print("Final audit:", json.dumps(result["checks"]), flush=True)
    finally:
        emu.stop(save=False)

if __name__ == "__main__":
    main()
