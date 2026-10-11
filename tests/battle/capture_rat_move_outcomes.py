#!/usr/bin/env python3
"""Collect four live Project Yellow move-effect fixtures using PyBoy buttons.

Derive a genuine initial DEBUG Fight savestate and trace from
probe_rat_debug_fight.py. This collector NEVER writes emulated memory or
chooses random seeds. It searches legitimate frame-delay variants, captures
the four before-move states by re-running the full controller traces with
capture.py, and fails unless all four expected results can be replayed.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

CASES = (
    ("poison_fang_proc", 0, True, 0x48),
    ("poison_fang_no_proc", 0, False, 0x48),
    ("crunch_proc", 3, True, 0x49),
    ("crunch_no_proc", 3, False, 0x49),
)
NAMES = ("wIsInBattle", "wBattleMonSpecies", "wEnemyMonSpecies",
         "wEnemyMonStatus", "wEnemyBattleStatus3", "wEnemyMonStatMods",
         "wEnemyMonHP", "wPlayerMoveEffect", "wPlayerMoveNum", "wPlayerSelectedMove", "wCurrentMenuItem", "wBattleMonMoves", "wMoveMissed")
PSN = 1 << 3
BAD_POISON = 1

def lookup(path):
    ret = {}
    for ln in path.read_text().splitlines():
        p = ln.split(";")[0].split()
        if len(p) >= 2 and ":" in p[0] and p[1] in NAMES:
            addr = int(p[0].split(":")[1], 16)
            if not 0xC000 <= addr <= 0xDFFF:
                raise AssertionError("Non-WRAM metric " + p[1])
            ret[p[1]] = addr
    if set(ret) != set(NAMES):
        raise AssertionError("Missing symbols " + repr(set(NAMES) - set(ret)))
    return ret

def read(pb, sym):
    def byte(key, offset=0):
        return int(pb.memory[sym[key] + offset])
    return {
        "battle": byte("wIsInBattle"),
        "player": byte("wBattleMonSpecies"),
        "enemy": byte("wEnemyMonSpecies"),
        "status": byte("wEnemyMonStatus"),
        "badly_poisoned": byte("wEnemyBattleStatus3") & BAD_POISON,
        "defense": byte("wEnemyMonStatMods", 1),
        "enemy_hp": byte("wEnemyMonHP") * 256 + byte("wEnemyMonHP", 1),
        "effect": byte("wPlayerMoveEffect"),
        "move_num": byte("wPlayerMoveNum"),
        "selected_move": byte("wPlayerSelectedMove"),
        "menu_index": byte("wCurrentMenuItem"),
        "missed": byte("wMoveMissed"),
        "moves": [byte("wBattleMonMoves", i) for i in range(4)],
    }

def tick(pb, n):
    for _ in range(n):
        pb.tick()

def press(pb, steps, button, settle):
    pb.button(button)
    steps.append({"button": button, "frames": 2})
    tick(pb, 2)
    pb.button_release(button)
    steps.append({"release": button, "frames": settle})
    tick(pb, settle)

def attempt(pb, start, sym, prefix, slot, offset):
    with start.open("rb") as f:
        pb.load_state(f)
    origin = read(pb, sym)
    if not origin["battle"] or origin["player"] != 0xBF or not origin["enemy"]:
        raise AssertionError("Not the verified Rattaking-vs-opponent battle state")
    steps = []
    press(pb, steps, "a", 200)  # Go! text -> battle command menu
    panel = pb.screen.image.crop((98, 96, 160, 144)).tobytes()
    press(pb, steps, "a", 200)  # FIGHT -> move selection
    actual_moves = read(pb, sym)["moves"]
    expected = 0xA7 if slot == 0 else 0xA8
    if actual_moves[slot] != expected:
        raise AssertionError("Wrong move in slot " + str(slot) + ": " + repr(actual_moves))
    for _ in range(slot):
        press(pb, steps, "down", 45)
    if offset:
        steps.append({"frames": offset})
        tick(pb, offset)
    before = read(pb, sym)
    pre_trace = prefix + steps
    attack = []
    press(pb, attack, "a", 200)
    # Advance text only until the original battle-command panel reappears.
    # Never press A again once a second turn is available.
    for _ in range(12):
        if pb.screen.image.crop((98, 96, 160, 144)).tobytes() == panel:
            break
        press(pb, attack, "a", 100)
    after = read(pb, sym)
    # Preserve diagnostics for the first selected attack and every proc/nonproc
    # experiment; no emulator-memory writes or RNG manipulation.
    if offset in (0, 1, 2, 3, 7, 15, 31, 63):
        print("effect-observation", slot, offset, json.dumps({
            "before": before, "after": after, "controller_steps": len(attack),
        }), flush=True)
    if not after["battle"] or after["enemy_hp"] >= before["enemy_hp"]:
        return None
    if after["move_num"] != slot + 1:
        if offset == 0:
            print("REJECT wrong selected slot", slot, "actual", after["move_num"], "before", before["menu_index"], flush=True)
        return None
    if slot == 0:
        proc = bool(after["status"] & PSN and after["badly_poisoned"])
        if after["status"] & PSN and not after["badly_poisoned"]:
            raise AssertionError("Poison Fang gave ordinary instead of badly poisoned status")
    else:
        delta = before["defense"] - after["defense"]
        if delta not in (0, 1):
            raise AssertionError("Crunch incorrectly changed Defense by " + str(delta))
        proc = delta == 1
    return {"proc": proc, "before": before, "after": after,
            "prefix": pre_trace, "attack": attack, "offset": offset}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", required=True, type=Path)
    p.add_argument("--symbols", required=True, type=Path)
    p.add_argument("--starting-state", required=True, type=Path)
    p.add_argument("--starting-trace", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--max-offset", type=int, default=70)
    args = p.parse_args()
    from pyboy import PyBoy
    sym = lookup(args.symbols)
    original_trace = json.loads(args.starting_trace.read_text())
    if not isinstance(original_trace, list) or not original_trace:
        raise AssertionError("Missing legitimate initial controller trace")
    args.output.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(args.rom.read_bytes()).hexdigest()
    pb = PyBoy(str(args.rom), window="null")
    discoveries = {}
    try:
        # Iterate by move, not by expected result; preserve both outcomes.
        for slot in (0, 3):
            for offset in range(args.max_offset):
                result = attempt(pb, args.starting_state, sym, original_trace, slot, offset)
                if result is None:
                    continue
                if offset in (0, 5, 25, 50):
                    print("diagnostic", slot, offset, "move", result["after"]["move_num"], "effect", result["after"]["effect"], "hp", result["after"]["enemy_hp"], "status", result["after"]["status"], "defense", result["after"]["defense"], flush=True)
                for name, desired_slot, expected_proc, _ in CASES:
                    if desired_slot == slot and expected_proc == result["proc"] and name not in discoveries:
                        discoveries[name] = result
                        print(name, "found at controller-only frame delay", offset, "before", result["before"], "after", result["after"], flush=True)
                if all(name in discoveries for name, s, _, _ in CASES if s == slot):
                    break
    finally:
        pb.stop()
    (args.output / "discovery.json").write_text(
        json.dumps({k: {"offset": v["offset"], "before": v["before"], "after": v["after"]}
                    for k, v in discoveries.items()}, indent=2) + "\n")
    missing = set(name for name, _, _, _ in CASES) - set(discoveries)
    if missing:
        raise AssertionError("Missing real controller-driven proc/no-proc cases: " + repr(sorted(missing)))

    cases = {}
    for name, slot, expected_proc, expected_effect in CASES:
        item = discoveries[name]
        trace_name = name + "_capture_trace.json"
        state_name = name + ".state"
        (args.output / trace_name).write_text(json.dumps(item["prefix"], indent=2) + "\n")
        # Reproduce the real state from *power-on*; capture.py writes its
        # standard SHA and actual party/battle provenance sidecar.
        subprocess.run([
            sys.executable, str(Path(__file__).with_name("capture.py")),
            "--rom", str(args.rom), "--symbols", str(args.symbols),
            "--trace", str(args.output / trace_name),
            "--output", str(args.output / state_name),
        ], check=True)
        cases[name] = {
            "state": state_name,
            "rom_sha256": sha,
            "move_slot": slot,
            "steps": item["attack"],
        }
    manifest = args.output / "rat_move_fixtures.json"
    manifest.write_text(json.dumps({"cases": cases}, indent=2) + "\n")
    subprocess.run([
        sys.executable, str(Path(__file__).with_name("test_rat_move_replay.py")),
        "--rom", str(args.rom),
        "--symbols", str(args.symbols),
        "--manifest", str(manifest),
    ], check=True)
    print("All four genuine battle-proc/no-proc replays passed", flush=True)

if __name__ == "__main__":
    main()
