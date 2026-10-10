#!/usr/bin/env python3
"""Create a *legitimate* Project Yellow PyBoy battle savestate by gameplay replay.

Never writes to emulator memory. A trace starts at power-on or a previously
recorded legitimate PyBoy state and uses only controller events and frame ticks.
The resulting state is accepted only while wIsInBattle is nonzero.
"""
import argparse
import hashlib
import json
from pathlib import Path


def address(symbol_file, label):
    for line in symbol_file.read_text().splitlines():
        parts = line.split(";")[0].split()
        if len(parts) >= 2 and parts[1] == label and ":" in parts[0]:
            address = int(parts[0].split(":")[1], 16)
            if 0xC000 <= address <= 0xDFFF:
                return address
    raise ValueError(f"Missing WRAM symbol: {label}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True, type=Path)
    ap.add_argument("--symbols", required=True, type=Path)
    ap.add_argument("--trace", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--starting-state", type=Path)
    args = ap.parse_args()
    from pyboy import PyBoy

    trace = json.loads(args.trace.read_text())
    if not isinstance(trace, list) or not trace:
        raise ValueError("Trace must be a nonempty list of input/frame steps")
    pyboy = PyBoy(str(args.rom), window="null")
    try:
        if args.starting_state:
            with args.starting_state.open("rb") as f:
                pyboy.load_state(f)
        for i, step in enumerate(trace):
            if "button" in step:
                pyboy.button(step["button"])
            if "release" in step:
                pyboy.button_release(step["release"])
            frames = step.get("frames", 1)
            if type(frames) is not int or not 1 <= frames <= 6000:
                raise ValueError(f"Invalid frame count at trace step {i}")
            for _ in range(frames):
                pyboy.tick()
        state = pyboy.memory[address(args.symbols, "wIsInBattle")]
        player = pyboy.memory[address(args.symbols, "wBattleMonSpecies")]
        enemy = pyboy.memory[address(args.symbols, "wEnemyMonSpecies")]
        if not state or not player or not enemy:
            raise AssertionError(
                f"Not a valid active battle: state={state}, player={player}, enemy={enemy}"
            )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("wb") as f:
            pyboy.save_state(f)
        provenance = {
            "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "trace_sha256": hashlib.sha256(args.trace.read_bytes()).hexdigest(),
            "starting_state_sha256": hashlib.sha256(args.starting_state.read_bytes()).hexdigest() if args.starting_state else None,
            "saved_state": str(args.output),
            "battle_flag": state,
            "player_species_internal_id": player,
            "enemy_species_internal_id": enemy,
        }
        (args.output.parent / (args.output.name + ".json")).write_text(
            json.dumps(provenance, indent=2) + "\n"
        )
        print(json.dumps(provenance, indent=2))
    finally:
        pyboy.stop()


if __name__ == "__main__":
    main()
