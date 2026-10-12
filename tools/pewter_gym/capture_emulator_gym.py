#!/usr/bin/env python3
"""Capture real PyBoy frames from a proven Pewter Gym gameplay state.

Requires a genuine gameplay-created PyBoy state; this script does NOT synthesize
a map or treat a tileset preview as emulator evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

PEWTER_GYM_MAP_ID = 0x36  # constants/map_constants.asm

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--symbols", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True,
                        help="PyBoy state saved from gameplay while inside Pewter Gym")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=60)
    args = parser.parse_args()
    for path in (args.rom, args.symbols, args.state):
        if not path.is_file():
            parser.error(f"Missing required input: {path}")
    if args.frames < 1:
        parser.error("--frames must be positive")
    from pyboy import PyBoy
    args.output.mkdir(parents=True, exist_ok=True)
    emulator = PyBoy(str(args.rom), window="null", symbols=str(args.symbols), cgb=False)
    try:
        with args.state.open("rb") as handle:
            emulator.load_state(handle)
        emulator.set_emulation_speed(0)
        emulator.tick(args.frames)
        _, map_address = emulator.symbol_lookup("wCurMap")
        actual_map = int(emulator.memory[map_address])
        if actual_map != PEWTER_GYM_MAP_ID:
            raise RuntimeError(
                f"Fixture did not enter actual Pewter Gym: map {actual_map:#04x}, "
                f"expected {PEWTER_GYM_MAP_ID:#04x}"
            )
        screenshot = args.output / "pewter_gym_dmg_actual.png"
        emulator.screen.image.copy().save(screenshot)
        metadata = {
            "source": "PyBoy emulation, loaded authentic gameplay state",
            "rom_sha256": hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "state_sha256": hashlib.sha256(args.state.read_bytes()).hexdigest(),
            "map_id": actual_map,
            "frames_after_state": args.frames,
            "screenshot_sha256": hashlib.sha256(screenshot.read_bytes()).hexdigest(),
            "visual_review": "PENDING HUMAN REVIEW",
        }
        (args.output / "evidence.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Captured actual Pewter Gym frame: {screenshot}")
    finally:
        emulator.stop()

if __name__ == "__main__":
    main()
