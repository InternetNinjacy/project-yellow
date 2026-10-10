#!/usr/bin/env python3
"""Emulator SRAM bank-isolation probe (not a battle-routine execution test).

Exercises the cartridge RAM mapper using an isolated temporary save directory.
Fails if the new workspace bank aliases any of the original four save banks.
Do not claim existing user's save integrity without a real legacy-save fixture.
"""
import argparse
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path, required=True)
    args = parser.parse_args()
    header = args.rom.read_bytes()
    assert header[0x149] == 0x04, "128KiB SRAM header required"
    assert header[0x147] in (0x1B,), "expected MBC5+RAM+BATTERY cart"
    from pyboy import PyBoy
    with tempfile.TemporaryDirectory() as tmp:
        rom = Path(tmp) / args.rom.name
        rom.write_bytes(header)
        pyboy = PyBoy(str(rom), window="null")
        try:
            pyboy.memory[0x0000] = 0x0A
            # Snapshot every byte, not just sentinel bytes, in the existing
            # save banks before writing a test pattern to isolated bank 4.
            originals = []
            for bank in range(4):
                pyboy.memory[0x4000] = bank
                originals.append(bytes(pyboy.memory[0xA000:0xC000]))
            # Explicit bank-context round trip: select a legacy bank,
            # access bank 4, then restore the selected bank before reading.
            # This tests mapper behavior, not assembly register preservation.
            previous_bank = 2
            pyboy.memory[0x4000] = previous_bank
            legacy_sentinel = pyboy.memory[0xA000 + 4095]
            pyboy.memory[0x4000] = 4
            pyboy.memory[0xA000 + 4095] = legacy_sentinel ^ 0xFF
            pyboy.memory[0x4000] = previous_bank
            assert pyboy.memory[0xA000 + 4095] == legacy_sentinel, (
                "bank selection restoration did not recover legacy bank contents"
            )
            pyboy.memory[0x4000] = 4
            before = bytes(pyboy.memory[0xA000:0xC000])
            offsets = (0, 31, 255, 511, 1023, 2047)
            for i, pos in enumerate(offsets):
                pyboy.memory[0xA000 + pos] = (0x51 + i * 17) & 0xFF
            for i, pos in enumerate(offsets):
                assert pyboy.memory[0xA000 + pos] == (0x51 + i * 17) & 0xFF
            for bank in range(4):
                pyboy.memory[0x4000] = bank
                assert bytes(pyboy.memory[0xA000:0xC000]) == originals[bank], (
                    f"saved bank {bank} was altered by bank-4 writes"
                )
            pyboy.memory[0x4000] = 4
            for pos in offsets:
                pyboy.memory[0xA000 + pos] = before[pos]
            pyboy.memory[0xA000 + 4095] = before[4095] ^ 0xFF
            pyboy.memory[0x4000] = 0
            pyboy.memory[0x0000] = 0
            print("PASS: emulator mapper bank-4 writes did not modify banks 0..3")
            print("NOT TESTED: assembly routine execution, legacy save migration, Pokémon serialization")
        finally:
            pyboy.stop(save=False)


if __name__ == "__main__":
    main()
