#!/usr/bin/env python3
"""Observe DEBUG new-game startup using real PyBoy controller inputs only.

Never writes emulated memory. Produces a controller trace + frame-by-frame
diagnostic checkpoints, for repairing the real six-mon DEBUG startup path.
Do NOT treat this as proof of a battle fixture.
"""
import argparse
import hashlib
import json
from pathlib import Path

SYMBOLS = ("wPartyCount", "wIsInBattle", "wStatusFlags6",
           "wCurMap", "wBattleMonSpecies", "wEnemyMonSpecies")
# A conservative, replayable scripted sweep of menu/text advancement.
# No claimed success: the probe fails if no initialized party is observed.
STEPS = [
    ("start", 1, 1200),
    *[("a", 1, 180) for _ in range(45)],
]

def parse_symbols(path):
    found = {}
    for line in path.read_text().splitlines():
        parts = line.split(";")[0].split()
        if len(parts) < 2 or ":" not in parts[0] or parts[1] not in SYMBOLS:
            continue
        addr = int(parts[0].split(":")[1], 16)
        if not 0xC000 <= addr <= 0xDFFF:
            raise AssertionError(f"{parts[1]} is not WRAM")
        found[parts[1]] = addr
    missing = set(SYMBOLS) - set(found)
    if missing:
        raise AssertionError("Missing WRAM symbols: " + repr(sorted(missing)))
    return found

def run(rom, symbols, output):
    from pyboy import PyBoy
    pb = PyBoy(str(rom), window="null")
    trace, checkpoints = [{"frames": 240}], []
    try:
        total_frames = 0
        def record(phase):
            values = {k: int(pb.memory[a]) for k, a in symbols.items()}
            checkpoints.append({"phase": phase, "frame": total_frames, **values})
        def frames(n):
            nonlocal total_frames
            for _ in range(n):
                pb.tick()
                total_frames += 1
        frames(240)
        record("initial")
        for idx, (button, held, release_frames) in enumerate(STEPS):
            pb.button(button)
            trace.append({"button": button, "frames": held})
            frames(held)
            pb.button_release(button)
            trace.append({"release": button, "frames": release_frames})
            frames(release_frames)
            record(f"step_{idx:02d}_{button}")
        output.mkdir(parents=True, exist_ok=True)
        (output / "debug_startup_inputs.json").write_text(json.dumps(trace, indent=2) + "\n")
        (output / "debug_startup_checkpoints.json").write_text(json.dumps({
            "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
            "checkpoints": checkpoints,
        }, indent=2) + "\n")
        with (output / "debug_startup_final.state").open("wb") as f:
            pb.save_state(f)
        if not any(row["wPartyCount"] > 0 for row in checkpoints):
            raise AssertionError("No initialized DEBUG party observed. See startup trace, checkpoints and state artifact.")
        print("DEBUG startup party observed; verify count and battle access separately.")
    finally:
        pb.stop()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rom", type=Path, required=True)
    p.add_argument("--symbols", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run(args.rom, parse_symbols(args.symbols), args.output)
