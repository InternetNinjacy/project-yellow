#!/usr/bin/env python3
"""Interactive, auditable Pewter City -> Gym route capture using real button input.

Start from a gameplay-created PyBoy state in Pewter City. Enter commands such
as 'up 8', 'right 16', 'a 1', 'wait 30', 'shot', or 'quit'. Every command is
played on the emulator and recorded as a reusable replay JSON. No memory is
modified. Only a witnessed city-to-gym map transition counts as success.
"""
import argparse
import hashlib
import json
from pathlib import Path

CITY, GYM = 0x02, 0x36
BUTTONS = {"up", "down", "left", "right", "a", "b", "start", "select"}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--initial-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for item in (args.rom, args.symbols, args.initial_state):
        if not item.is_file():
            parser.error(f"Missing file: {item}")
    from pyboy import PyBoy
    args.output.mkdir(parents=True, exist_ok=True)
    boy = PyBoy(str(args.rom), window="null", symbols=str(args.symbols), cgb=False)
    actions = []
    try:
        with args.initial_state.open("rb") as handle:
            boy.load_state(handle)
        boy.set_emulation_speed(0)
        _, address = boy.symbol_lookup("wCurMap")
        def current_map():
            return int(boy.memory[address])
        if current_map() != CITY:
            raise RuntimeError(f"Initial gameplay state is not Pewter City: {current_map():#04x}")
        print("Pewter City confirmed. Commands: 'up 16', 'wait 30', 'shot', 'quit'.")
        print("Frames are exact; each command is saved to an auditable input route.")
        while True:
            command = input("gym-route> ").strip().lower().split()
            if not command:
                continue
            if command == ["quit"]:
                print("Aborted; no fixture accepted.")
                return
            if command == ["shot"]:
                path = args.output / "route_preview.png"
                boy.screen.image.copy().save(path)
                print(path)
                continue
            if len(command) != 2:
                print("Expected <button|wait> <frames>")
                continue
            key, raw = command
            if key not in BUTTONS | {"wait"}:
                print("Unknown button")
                continue
            try:
                frames = int(raw)
            except ValueError:
                print("Frames must be an integer")
                continue
            if not 1 <= frames <= 3600:
                print("Frames must be between 1 and 3600")
                continue
            button = None if key == "wait" else key
            if button:
                boy.button_press(button)
            entered = False
            executed = 0
            for _ in range(frames):
                before = current_map()
                boy.tick(1)
                executed += 1
                after = current_map()
                if before == CITY and after == GYM:
                    entered = True
                    break
                if after not in (CITY, GYM):
                    raise RuntimeError(f"Unexpected warp away from city: {after:#04x}")
            if button:
                boy.button_release(button)
            actions.append({"button": button, "frames": executed})
            if entered:
                boy.tick(60)
                if current_map() != GYM:
                    raise RuntimeError("Gym map did not remain loaded")
                state = args.output / "pewter_gym_gameplay.state"
                screenshot = args.output / "pewter_gym_entry_actual.png"
                route = args.output / "pewter_city_to_gym.json"
                route.write_text(json.dumps({"actions": actions}, indent=2) + "\n")
                with state.open("wb") as handle:
                    boy.save_state(handle)
                boy.screen.image.copy().save(screenshot)
                evidence = {
                    "method": "Real PyBoy input, observed CITY 0x02 -> GYM 0x36 transition",
                    "rom_sha256": digest(args.rom),
                    "initial_state_sha256": digest(args.initial_state),
                    "route_sha256": digest(route),
                    "fixture_sha256": digest(state),
                    "screenshot_sha256": digest(screenshot),
                    "visual_approval": "PENDING",
                }
                (args.output / "entry_evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
                print("Success: authentic warp observed. Replay the saved route to verify.")
                return
            if current_map() != CITY:
                raise RuntimeError("Unexpected map ID")
            print(f"Map {current_map():#04x}; actions {len(actions)}")
    finally:
        boy.stop()

if __name__ == "__main__":
    main()
