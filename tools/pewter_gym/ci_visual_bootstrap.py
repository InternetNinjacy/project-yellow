#!/usr/bin/env python3
"""CI-only Pewter Gym visual test, starting from an explicitly flagged test ROM.

NO RAM editing, forced map transitions or fabricated save-state. The CI-only
assembler define places the newly initialized player immediately south of the
normal Pewter Gym entrance. The emulator must reach the city via its ordinary
new-game startup and enter the Gym using a directional controller input.
"""
import argparse
import hashlib
import json
from pathlib import Path

CITY, GYM = 0x02, 0x36

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--rom", required=True, type=Path)
    cli.add_argument("--symbols", required=True, type=Path)
    cli.add_argument("--output", required=True, type=Path)
    args = cli.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    from pyboy import PyBoy
    emulator = PyBoy(str(args.rom), symbols=str(args.symbols), window="null", cgb=False)
    frames = 0
    trace = []
    def tick(n):
        nonlocal frames
        emulator.tick(n)
        frames += n
    def press(key, n=8, settle=45):
        emulator.button_press(key)
        tick(n)
        emulator.button_release(key)
        tick(settle)
        trace.append({"button": key, "frames": n, "settle": settle})
    def shot(name):
        emulator.screen.image.copy().save(args.output / name)
    try:
        emulator.set_emulation_speed(0)
        _, address = emulator.symbol_lookup("wCurMap")
        def location():
            return int(emulator.memory[address])
        tick(600)
        # New Game/Oak speech may contain text, menu and naming prompts.
        # A timeout is a FAILED test, never interpreted as a screenshot pass.
        for index in range(1200):
            if location() == CITY:
                break
            press("start" if index % 11 == 0 else "a")
            if index % 16 == 0:
                shot("bootstrap_latest.png")
        else:
            shot("bootstrap_failed.png")
            raise RuntimeError(f"Test build never reached Pewter City; map={location():#04x}")
        shot("pewter_city_before_entry.png")
        # Startup coordinate is (16,18), directly south of the real warp.
        # Directional input must perform the original game warp.
        for _ in range(8):
            press("up", n=10, settle=20)
            if location() == GYM:
                break
        if location() != GYM:
            shot("entry_failed.png")
            raise RuntimeError(f"Gym warp did not activate, map={location():#04x}")
        tick(90)
        if location() != GYM:
            raise RuntimeError("Entered Gym but could not remain in it")
        screenshot = args.output / "pewter_gym_actual_test_build.png"
        shot(screenshot.name)
        fixture = args.output / "pewter_gym_test_build.state"
        with fixture.open("wb") as handle:
            emulator.save_state(handle)
        evidence = {
            "test_build_only": True,
            "source": "normal new-game setup with CI-only spawn; directional door entry",
            "rom_sha256": sha(args.rom),
            "screenshot_sha256": sha(screenshot),
            "state_sha256": sha(fixture),
            "map_id": location(),
            "frames": frames,
            "visual_review": "PENDING HUMAN REVIEW",
            "production_progression_verified": False,
            "trace": trace,
        }
        (args.output / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(f"Actual frozen Gym test-build screen: {screenshot}")
    finally:
        emulator.stop()

if __name__ == "__main__":
    main()
