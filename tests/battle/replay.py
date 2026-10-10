#!/usr/bin/env python3
"""Replay Project Yellow battle fixtures in PyBoy; never equate boot with mechanics QA.

Usage: python3 tests/battle/replay.py --rom pokeyellow_debug.gbc \
    --symbols pokeyellow_debug.sym --manifest tests/battle/fixtures.json
The manifest references real, independently prepared PyBoy save-states and includes
explicit expected RAM values at checkpoints. Missing fixtures fail closed.
"""
import argparse
import json
from pathlib import Path

REQUIRED_CASES = {
    "amnesia_player", "amnesia_enemy",
    "growth_player", "growth_enemy",
    "growth_spa_cap", "growth_spd_cap",
    "psychic_player", "psychic_enemy",
    "psychic_spd_floor", "damage_special_before_after",
}
ALLOWED_KEYS = {
    "wPlayerMonSpecialMod", "wEnemyMonSpecialMod",
    "wPlayerSpecialDefenseMod", "wEnemySpecialDefenseMod",
    "wBattleMonSpecial", "wEnemyMonSpecial",
    "wPlayerSpecialDefense", "wEnemySpecialDefense",
    "wDamage", "wBattleMonHP", "wEnemyMonHP",
}
WORD_KEYS = {
    "wBattleMonSpecial", "wEnemyMonSpecial",
    "wPlayerSpecialDefense", "wEnemySpecialDefense",
    "wDamage", "wBattleMonHP", "wEnemyMonHP",
}


def symbols(path):
    result = {}
    for line in path.read_text().splitlines():
        parts = line.split(";")[0].split()
        if len(parts) < 2 or ":" not in parts[0]:
            continue
        bank, addr = parts[0].split(":", 1)
        label = parts[1]
        if label in ALLOWED_KEYS:
            result[label] = (int(bank, 16), int(addr, 16))
    missing = ALLOWED_KEYS - result.keys()
    if missing:
        raise AssertionError("Missing RAM symbols: " + ", ".join(sorted(missing)))
    for label, (bank, addr) in result.items():
        if not 0xC000 <= addr <= 0xDFFF:
            raise AssertionError(f"{label} is not a WRAM address: {bank:02x}:{addr:04x}")
    return result


def read_ram(pyboy, sym, name):
    _, addr = sym[name]
    high = pyboy.memory[addr]
    if name in WORD_KEYS:
        return (high << 8) | pyboy.memory[addr + 1]
    return high


def check(pyboy, sym, expected, case, checkpoint):
    if not expected:
        raise AssertionError(f"{case}: empty {checkpoint} oracle")
    for key, want in expected.items():
        if key not in ALLOWED_KEYS:
            raise AssertionError(f"Unrecognized metric {key}")
        actual = read_ram(pyboy, sym, key)
        if actual != want:
            raise AssertionError(
                f"{case}/{checkpoint}: {key}= {actual}, expected {want}"
            )


def replay(pyboy, sym, item, root):
    state_path = root / item["state"]
    if not state_path.is_file():
        raise FileNotFoundError(f"Required real battle save-state missing: {state_path}")
    with state_path.open("rb") as fh:
        pyboy.load_state(fh)
    check(pyboy, sym, item["before"], item["name"], "before")
    # Input is deterministic, frame-explicit; button releases are required in
    # the manifest rather than synthesizing game interaction.
    for step in item["steps"]:
        if "button" in step:
            pyboy.button(step["button"])
        if "release" in step:
            pyboy.button_release(step["release"])
        frames = step.get("frames", 1)
        if not isinstance(frames, int) or not 1 <= frames <= 6000:
            raise ValueError("Frame step must be 1..6000")
        for _ in range(frames):
            pyboy.tick()
    check(pyboy, sym, item["after"], item["name"], "after")
    before = item["before"]
    after = item["after"]
    if item["name"] == "damage_special_before_after":
        # A real battle event must change an HP value and the manifest must
        # assert its exact value; a modified stat cache alone is insufficient.
        hp_names = ("wBattleMonHP", "wEnemyMonHP")
        if not any(k in before and k in after and before[k] != after[k] for k in hp_names):
            raise AssertionError("Damage fixture must assert a changed actual battler HP")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", type=Path, required=True)
    ap.add_argument("--symbols", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    data = json.loads(args.manifest.read_text())
    items = data["cases"]
    present = {item["name"] for item in items}
    missing = REQUIRED_CASES - present
    if missing:
        raise AssertionError("Required replay cases absent: " + ", ".join(sorted(missing)))
    if len(present) != len(items):
        raise AssertionError("Duplicate case names")
    sym = symbols(args.symbols)
    try:
        from pyboy import PyBoy
    except ImportError as exc:
        raise SystemExit("Install PyBoy to perform real emulator replay") from exc
    pyboy = PyBoy(str(args.rom), window="null")
    try:
        for item in items:
            replay(pyboy, sym, item, args.manifest.parent)
            print(f"PASS (actual PyBoy replay): {item['name']}")
    finally:
        pyboy.stop()


if __name__ == "__main__":
    main()
