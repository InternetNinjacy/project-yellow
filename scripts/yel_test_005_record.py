#!/usr/bin/env python3
"""Record normal gameplay via controller commands and produce a replayable trace.

No save-state loads, RAM writes, debug shortcuts or cheats. Run on a machine
with PyBoy and Pillow. For each command a screenshot is saved for inspection.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pyboy import PyBoy

BUTTONS = {"a", "b", "start", "select", "up", "down", "left", "right"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    trace = []
    emu = PyBoy(a.rom, window="null", cgb=False, sound_emulated=False)
    emu.set_emulation_speed(0)
    total = 0
    try:
        while True:
            name = out / f"frame-{total:09d}.png"
            emu.screen.image.save(name)
            print(f"Frame {total}; screenshot {name}")
            print("Enter 'a 1 30' (button hold frames, release/wait frames), "
                  "'wait 60', 'done', or 'help'.")
            cmd = input("> ").strip().lower().split()
            if not cmd or cmd[0] == "help":
                continue
            if cmd[0] == "done":
                break
            if cmd[0] == "wait" and len(cmd) == 2:
                frames = int(cmd[1])
                after = 0
                button = None
            elif cmd[0] in BUTTONS and len(cmd) in (2, 3):
                button = cmd[0]
                frames = int(cmd[1])
                after = int(cmd[2]) if len(cmd) == 3 else 0
            else:
                print("Invalid command")
                continue
            if frames < 0 or frames > 100000 or after < 0 or after > 100000 or (button and not frames):
                print("Invalid frame count")
                continue
            step = {"button": button, "frames": frames, "after": after} if button else {"frames": frames}
            if button:
                emu.button_press(button)
            try:
                if frames:
                    emu.tick(frames)
            finally:
                if button:
                    emu.button_release(button)
            if after:
                emu.tick(after)
            total += frames + after
            trace.append(step)
            (out / "trace.json").write_text(json.dumps(trace, indent=2) + "\n")
        if not trace:
            raise ValueError("Cannot record an empty gameplay route")
        state = out / "checkpoint.state"
        with state.open("wb") as target:
            emu.save_state(target)
        report = {
            "schema": "YEL-TEST-005/1",
            "state_provenance": "clean_boot_controller_only",
            "status": "RECORDED_UNVERIFIED",
            "frames": total,
            "steps": len(trace),
            "rom_sha256": hashlib.sha256(Path(a.rom).read_bytes()).hexdigest(),
            "trace_sha256": hashlib.sha256((out / "trace.json").read_bytes()).hexdigest(),
            "checkpoint_sha256": hashlib.sha256(state.read_bytes()).hexdigest(),
        }
        (out / "recording.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        emu.stop(save=False)


if __name__ == "__main__":
    main()
