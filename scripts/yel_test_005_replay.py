#!/usr/bin/env python3
"""YEL-TEST-005 shared deterministic controller trace runner.

A trace is data, not proof of gameplay. A checkpoint is gameplay-derived only
when this runner replays all inputs from a clean emulator boot (no load_state,
no direct memory writes) and records its provenance. Never commit resulting
save states, SRAM, or ROMs.
"""
import argparse
import hashlib
import json
import platform
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def validate(steps):
    if not isinstance(steps, list) or not steps:
        raise ValueError("Trace must be a nonempty JSON array")
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i} is not an object")
        if set(step) - {"button", "buttons", "frames", "after"}:
            raise ValueError(f"Step {i} has unknown fields")
        button = step.get("button")
        if button is not None and button not in (
            "a", "b", "start", "select", "up", "down", "left", "right"
        ):
            raise ValueError(f"Unsupported button at step {i}: {button}")
        buttons = step.get("buttons")
        if buttons is not None:
            if button is not None or not isinstance(buttons, list) or not buttons or len(set(buttons)) != len(buttons) or any(b not in ("a", "b", "start", "select", "up", "down", "left", "right") for b in buttons):
                raise ValueError(f"Invalid simultaneous buttons at step {i}")
        for key in ("frames", "after"):
            n = step.get(key, 0)
            if type(n) is not int or n < 0 or n > 100000:
                raise ValueError(f"Step {i}: invalid {key}")
        if (button or buttons) and not step.get("frames"):
            raise ValueError(f"Step {i}: button needs positive frames")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True)
    ap.add_argument("--sym", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--state-in", help="Optional existing checkpoint; NOT clean-boot provenance")
    ap.add_argument("--checkpoint", action="store_true", help="Emit private PyBoy state")
    args = ap.parse_args()

    # Import only after validation so bad inputs fail without loading an emulator.
    steps = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    validate(steps)
    from pyboy import PyBoy
    import pyboy

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "YEL-TEST-005/1",
        "status": "FAIL",
        "rom_sha256": digest(args.rom),
        "symbols_sha256": digest(args.sym),
        "trace_sha256": digest(args.trace),
        "source": "loaded_checkpoint" if args.state_in else "clean_boot_controller_only",
        "state_in_sha256": digest(args.state_in) if args.state_in else None,
        "pyboy_version": getattr(pyboy, "__version__", "unknown"),
        "python_version": platform.python_version(),
        "emulator_mode": "DMG",
        "input_steps": len(steps),
        "frame_count": 0,
    }
    emu = None
    try:
        emu = PyBoy(args.rom, window="null", cgb=False, sound_emulated=False)
        emu.set_emulation_speed(0)
        if args.state_in:
            with open(args.state_in, "rb") as source:
                emu.load_state(source)
        for step in steps:
            button = step.get("button")
            frames = step.get("frames", 0)
            after = step.get("after", 0)
            buttons = step.get("buttons", [button] if button else [])
            for pressed in buttons:
                emu.button_press(pressed)
            try:
                if frames:
                    emu.tick(frames)
            finally:
                for pressed in buttons:
                    emu.button_release(pressed)
            if after:
                emu.tick(after)
            report["frame_count"] += frames + after
        # Captured output is evidence of the end frame, not evidence of location
        # or capture readiness until feature-specific assertions verify it.
        image_path = out / "end.png"
        emu.screen.image.save(image_path)
        report["screenshot_sha256"] = digest(image_path)
        if args.checkpoint:
            state_path = out / "checkpoint.state"
            with open(state_path, "wb") as state:
                emu.save_state(state)
            report["checkpoint_sha256"] = digest(state_path)
        report["status"] = "REPLAY_COMPLETED_TARGET_STATE_UNVERIFIED"
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if emu is not None:
            emu.stop(save=False)
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
