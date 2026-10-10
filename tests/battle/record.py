#!/usr/bin/env python3
"""Interactive controller trace recorder for a REAL Project Yellow PyBoy run.

Works from ROM power-on or a legitimate starting PyBoy state. The user supplies
controller actions while watching the PyBoy game window; actions are recorded
exactly and may be replayed using capture.py. No WRAM edits occur.
"""
import argparse
import json
from pathlib import Path

BUTTONS = {"a", "b", "start", "select", "up", "down", "left", "right"}


def symbol(path, name):
    for line in path.read_text().splitlines():
        tokens = line.split(";")[0].split()
        if len(tokens) >= 2 and tokens[1] == name and ":" in tokens[0]:
            address = int(tokens[0].split(":")[-1], 16)
            if 0xC000 <= address <= 0xDFFF:
                return address
    raise RuntimeError("Unable to resolve " + name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True, type=Path)
    parser.add_argument("--symbols", required=True, type=Path)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--starting-state", type=Path)
    a = parser.parse_args()
    from pyboy import PyBoy
    pb = PyBoy(str(a.rom), window="SDL2")
    steps = []
    battle = symbol(a.symbols, "wIsInBattle")
    player = symbol(a.symbols, "wBattleMonSpecies")
    enemy = symbol(a.symbols, "wEnemyMonSpecies")
    try:
        if a.starting_state:
            with a.starting_state.open("rb") as handle:
                pb.load_state(handle)
        print("Commands: a/b/start/select/up/down/left/right [frames];")
        print("wait [frames]; check; save; quit. Buttons release after frames.")
        print("Observe the game window; enter each deliberate action in terminal.")
        while True:
            line = input("battle recorder> ").strip().lower().split()
            if not line:
                continue
            cmd = line[0]
            if cmd == "quit":
                break
            if cmd == "check":
                print(f"battle={pb.memory[battle]} player={pb.memory[player]} enemy={pb.memory[enemy]}")
                continue
            if cmd == "save":
                if not (pb.memory[battle] and pb.memory[player] and pb.memory[enemy]):
                    print("REFUSED: no validated active battle yet")
                    continue
                a.trace.parent.mkdir(parents=True, exist_ok=True)
                a.state.parent.mkdir(parents=True, exist_ok=True)
                a.trace.write_text(json.dumps(steps, indent=2) + "\n")
                with a.state.open("wb") as handle:
                    pb.save_state(handle)
                print(f"Saved legitimate battle: {a.trace} and {a.state}")
                continue
            if cmd not in BUTTONS | {"wait"}:
                print("Unknown command")
                continue
            frames = int(line[1]) if len(line) > 1 else 1
            if not 1 <= frames <= 6000:
                print("Frames must be 1..6000")
                continue
            if cmd != "wait":
                pb.button(cmd)
                steps.append({"button": cmd, "frames": frames})
            else:
                steps.append({"frames": frames})
            for _ in range(frames):
                pb.tick()
            if cmd != "wait":
                pb.button_release(cmd)
                steps.append({"release": cmd, "frames": 1})
                pb.tick()
            print(f"steps={len(steps)} active_battle={bool(pb.memory[battle])}")
    finally:
        pb.stop()


if __name__ == "__main__":
    main()
