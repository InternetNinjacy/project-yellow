#!/usr/bin/env python3
"""Fail-closed 32KiB legacy save compatibility test.

Requires a genuine 32768-byte save fixture supplied explicitly. Never rewrites
that source file; verifies original banks after loading and after emulator stop.
This checks raw preservation, not yet all in-game Pokémon save semantics.
"""
import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", required=True, type=Path)
    p.add_argument("--legacy-save", required=True, type=Path)
    args = p.parse_args()
    if not args.legacy_save.is_file():
        p.error("Real 32KiB legacy save fixture is required (none supplied)")
    legacy = args.legacy_save.read_bytes()
    if len(legacy) != 32768:
        p.error("Legacy save must be exactly 32768 bytes")
    image = args.rom.read_bytes()
    if image[0x149] != 4 or image[0x147] != 0x1B:
        p.error("Target ROM must use 128KiB MBC5+RAM+BATTERY")
    from pyboy import PyBoy
    with tempfile.TemporaryDirectory() as tmp:
        rom = Path(tmp) / "compatibility.gbc"
        save = rom.with_suffix(".ram")
        rom.write_bytes(image)
        save.write_bytes(legacy)
        game = PyBoy(str(rom), window="null")
        try:
            game.tick(120, render=False)
            game.memory[0x0000] = 0x0A
            banks = []
            for bank in range(4):
                game.memory[0x4000] = bank
                banks.append(bytes(game.memory[0xA000:0xC000]))
            assert b"".join(banks) == legacy, "Legacy save differs after load"
            game.memory[0x4000] = 4
            game.memory[0xA000] = 0x6A
            game.memory[0x4000] = 0
            game.memory[0x0000] = 0
        finally:
            game.stop(save=True)
        output = save.read_bytes()
        assert len(output) >= 32768, "Migrated SRAM truncated"
        assert output[:32768] == legacy, "Legacy banks changed after save"
        assert args.legacy_save.read_bytes() == legacy, "Fixture unexpectedly modified"
        print("PASS: existing four SRAM banks retained exactly after load and save")
        print("SHA256 legacy banks:", digest(legacy))
        print("LIMIT: game-level Pokémon checksum and party/box interpretation unverified")


if __name__ == "__main__":
    main()
