#!/usr/bin/env python3
"""YEL-TEST-002: deterministic ROM boot smoke test, NOT artwork verification."""
import argparse
import hashlib
import json
from pathlib import Path

from pyboy import PyBoy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", default="pokeyellow.gbc")
    parser.add_argument("--out", default="test-results/emulator")
    args = parser.parse_args()
    rom = Path(args.rom)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = {
        "test": "YEL-TEST-002 baseline emulator boot smoke",
        "rom": rom.name,
        "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        "mode": "DMG emulation (requested cgb=False)",
        "sprite_validation": "NOT_TESTED",
        "palette_validation": "NOT_TESTED",
    }
    emu = None
    try:
        emu = PyBoy(str(rom), window="null", cgb=False, sound_emulated=False)
        emu.set_emulation_speed(0)
        # Boot startup and capture a stable pre-input screenshot.
        emu.tick(360)
        first = emu.screen.image.copy().convert("RGB")
        first.save(out / "boot_360.png")
        emu.button_press("start")
        emu.tick(2)
        emu.button_release("start")
        emu.tick(180)
        second = emu.screen.image.copy().convert("RGB")
        second.save(out / "after_start_542.png")
        distinct = len(set(second.getdata()))
        result.update(
            cartridge_title=str(emu.cartridge_title),
            frames=542,
            native_image_size=list(second.size),
            final_unique_rgb_colors=distinct,
            boot_screenshot_sha256=hashlib.sha256((out / "boot_360.png").read_bytes()).hexdigest(),
            start_screenshot_sha256=hashlib.sha256((out / "after_start_542.png").read_bytes()).hexdigest(),
        )
        if second.size != (160, 144):
            raise AssertionError(f"Expected 160x144 screen, got {second.size}")
        if distinct < 2:
            raise AssertionError("Final emulated screen appears uniform/blank")
        result["status"] = "BOOT_SMOKE_PASS"
    except Exception as exc:
        result["status"] = "BOOT_SMOKE_FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if emu is not None:
            emu.stop(save=False)
        (out / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
