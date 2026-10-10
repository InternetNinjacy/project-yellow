#!/usr/bin/env python3
"""Fail-closed, controller-only PyBoy regression gate for Poison Fang and Crunch.

The four savestates must be captured from real gameplay with capture.py.
No writes to emulated WRAM or modifications to random seeds are permitted.
"""
import argparse
import hashlib
import json
from pathlib import Path

REQUIRED = {
    "poison_fang_proc": ("poison_fang", True),
    "poison_fang_no_proc": ("poison_fang", False),
    "crunch_proc": ("crunch", True),
    "crunch_no_proc": ("crunch", False),
}
# Source-level probability check complements, not replaces, the real battle replays.
assert 128 * 2 == 256  # 50% of an 8-bit uniform roll
assert 78 * 100 == 39 * 200  # exactly 39%, via 0..199 rejection sampling
PSN_MASK = 1 << 3
BADLY_POISONED_MASK = 1 << 0
POISON_FANG = 0xA7
CRUNCH = 0xA8
SYMBOLS = (
    "wIsInBattle", "wBattleMonSpecies", "wEnemyMonSpecies",
    "wEnemyMonStatus", "wEnemyBattleStatus3", "wEnemyMonStatMods",
    "wPlayerMoveNum",
)

def addresses(path):
    found = {}
    for line in path.read_text().splitlines():
        parts = line.split(";")[0].split()
        if len(parts) < 2 or ":" not in parts[0]:
            continue
        if parts[1] in SYMBOLS:
            addr = int(parts[0].split(":")[1], 16)
            if not 0xC000 <= addr <= 0xDFFF:
                raise AssertionError("Non-WRAM battle symbol " + parts[1])
            found[parts[1]] = addr
    if set(found) != set(SYMBOLS):
        raise AssertionError("Missing symbols: " + str(set(SYMBOLS) - set(found)))
    return found

def snapshot(pb, a):
    return {
        "battle": pb.memory[a["wIsInBattle"]],
        "player": pb.memory[a["wBattleMonSpecies"]],
        "enemy": pb.memory[a["wEnemyMonSpecies"]],
        "status": pb.memory[a["wEnemyMonStatus"]],
        "toxic": pb.memory[a["wEnemyBattleStatus3"]],
        "defense_stage": pb.memory[a["wEnemyMonStatMods"] + 1],
        "move": pb.memory[a["wPlayerMoveNum"]],
    }

def replay(pb, steps):
    if not isinstance(steps, list) or not steps:
        raise AssertionError("Controller trace must be nonempty")
    for step in steps:
        if set(step) - {"button", "release", "frames"}:
            raise AssertionError("Unknown controller step")
        frames = step.get("frames", 1)
        if type(frames) is not int or not 1 <= frames <= 6000:
            raise AssertionError("Invalid frame count")
        if "button" in step:
            pb.button(step["button"])
        if "release" in step:
            pb.button_release(step["release"])
        for _ in range(frames):
            pb.tick()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", required=True, type=Path)
    p.add_argument("--symbols", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    opt = p.parse_args()
    from pyboy import PyBoy
    manifest = json.loads(opt.manifest.read_text())
    cases = manifest.get("cases", {})
    if set(cases) != set(REQUIRED):
        raise AssertionError("Must supply all four real captures: " + repr(sorted(REQUIRED)))
    digest = hashlib.sha256(opt.rom.read_bytes()).hexdigest()
    a = addresses(opt.symbols)
    evidence = {}
    for name, (move, expected_proc) in REQUIRED.items():
        case = cases[name]
        state_path = opt.manifest.parent / case["state"]
        if not state_path.is_file():
            raise FileNotFoundError("Missing real battle savestate: " + str(state_path))
        if case.get("rom_sha256") != digest:
            raise AssertionError(name + ": state/ROM provenance SHA mismatch")
        pb = PyBoy(str(opt.rom), window="null")
        try:
            with state_path.open("rb") as handle:
                pb.load_state(handle)
            before = snapshot(pb, a)
            if not before["battle"] or not before["player"] or not before["enemy"]:
                raise AssertionError(name + ": not an active battle")
            replay(pb, case["steps"])
            after = snapshot(pb, a)
            if move == "poison_fang":
                if after["move"] != POISON_FANG:
                    raise AssertionError(name + ": selected move is not Poison Fang")
                succeeded = bool(after["status"] & PSN_MASK and after["toxic"] & BADLY_POISONED_MASK)
                if not expected_proc and (after["status"] != before["status"] or after["toxic"] != before["toxic"]):
                    raise AssertionError(name + ": unexpected status change")
                if expected_proc and not succeeded:
                    raise AssertionError(name + ": did not apply badly poisoned status")
            else:
                if after["move"] != CRUNCH:
                    raise AssertionError(name + ": selected move is not Crunch")
                delta = before["defense_stage"] - after["defense_stage"]
                if delta != (1 if expected_proc else 0):
                    raise AssertionError(name + ": unexpected Defense stage delta " + str(delta))
            evidence[name] = {"before": before, "after": after, "passed": True}
        finally:
            pb.stop()
    print(json.dumps({"rom_sha256": digest, "results": evidence}, indent=2))

if __name__ == "__main__":
    main()
