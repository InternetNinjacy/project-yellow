#!/usr/bin/env python3
"""Replay recorded gameplay inputs and save only after the real Pewter Gym warp.

The JSON route must start at a genuine gameplay state (or at power-on). No
WRAM writes, teleport calls, scripted warp injection, or artificial map IDs.
Route format: {"actions":[{"button":"up","frames":16}, ...]}
Use {"button":null,"frames":N} for no input. All inputs are replayable.
"""
import argparse
import hashlib
import json
from pathlib import Path

PEWTER_CITY = 0x02
PEWTER_GYM = 0x36
BUTTONS = {"up", "down", "left", "right", "a", "b", "start", "select"}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", type=Path, required=True)
    p.add_argument("--symbols", type=Path, required=True)
    p.add_argument("--route", type=Path, required=True)
    p.add_argument("--initial-state", type=Path,
                   help="Authentic gameplay-created state; omit to boot from power-on")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-frames", type=int, default=180000)
    args = p.parse_args()
    for path in (args.rom, args.symbols, args.route):
        if not path.is_file():
            p.error(f"Missing file: {path}")
    if args.initial_state is not None and not args.initial_state.is_file():
        p.error(f"Missing state: {args.initial_state}")
    actions = json.loads(args.route.read_text(encoding="utf-8"))["actions"]
    if not isinstance(actions, list) or not actions:
        p.error("Route must contain nonempty actions")
    from pyboy import PyBoy
    pyboy = PyBoy(str(args.rom), window="null", symbols=str(args.symbols), cgb=False)
    previous = None
    saw_city = False
    elapsed = 0
    try:
        if args.initial_state:
            with args.initial_state.open("rb") as state:
                pyboy.load_state(state)
        pyboy.set_emulation_speed(0)
        _, address = pyboy.symbol_lookup("wCurMap")
        def map_id():
            return int(pyboy.memory[address])
        previous = map_id()
        saw_city = previous == PEWTER_CITY
        for index, action in enumerate(actions):
            button = action.get("button")
            frames = action.get("frames")
            if button is not None and button not in BUTTONS:
                raise ValueError(f"Invalid button in action {index}: {button}")
            if not isinstance(frames, int) or frames < 1 or frames > 3600:
                raise ValueError(f"Invalid frames in action {index}: {frames}")
            if elapsed + frames > args.max_frames:
                raise RuntimeError("Route exceeded maximum frame budget")
            if button:
                pyboy.button_press(button)
            for _ in range(frames):
                pyboy.tick(1)
                elapsed += 1
                current = map_id()
                if current == PEWTER_CITY:
                    saw_city = True
                if current == PEWTER_GYM:
                    if not saw_city or previous != PEWTER_CITY:
                        raise RuntimeError(
                            "Reached gym without observing direct Pewter City -> Gym transition"
                        )
                    # The map script and tileset must be loaded before snapshot.
                    if button:
                        pyboy.button_release(button)
                    pyboy.tick(60)
                    if map_id() != PEWTER_GYM:
                        raise RuntimeError("Gym not stable after warp")
                    args.output.mkdir(parents=True, exist_ok=True)
                    state_path = args.output / "pewter_gym_gameplay.state"
                    screen_path = args.output / "pewter_gym_entry_actual.png"
                    with state_path.open("wb") as file:
                        pyboy.save_state(file)
                    pyboy.screen.image.copy().save(screen_path)
                    evidence = {
                        "source": "PyBoy input replay through live Pewter City Gym warp",
                        "rom_sha256": sha(args.rom),
                        "route_sha256": sha(args.route),
                        "initial_state_sha256": sha(args.initial_state) if args.initial_state else None,
                        "state_sha256": sha(state_path),
                        "screenshot_sha256": sha(screen_path),
                        "map_transition": ["0x02", "0x36"],
                        "frames_to_entry": elapsed,
                        "human_visual_review": "PENDING",
                    }
                    (args.output / "entry_evidence.json").write_text(
                        json.dumps(evidence, indent=2) + "\n", encoding="utf-8"
                    )
                    print(f"Verified real city-to-gym transition after {elapsed} frames")
                    print(f"Gameplay fixture: {state_path}")
                    return
                previous = current
            if button:
                pyboy.button_release(button)
            pyboy.tick(1)
            elapsed += 1
            previous = map_id()
        raise RuntimeError("Replay completed without entering Pewter Gym through its city warp")
    finally:
        pyboy.stop()

if __name__ == "__main__":
    main()
