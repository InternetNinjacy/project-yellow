#!/usr/bin/env python3
"""Strict Project Yellow end-to-end capture/SAVE/CONTINUE PyBoy replay.

Input JSON supplies *real controller events*, not synthesized SRAM records.
This script does not claim gameplay success until a full-party catch and a
persisted exact 55-byte Pokémon record have been observed in cartridge SRAM.
No savestate or direct write to emulator memory is used.
"""
import argparse
import json
import shutil
import tempfile
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_fixture import seed_scenario

BOX_SIZE = 1682
MON_BYTES = 33
NAME_BYTES = 11
PHYSICAL_MON_OFFSET = 32
PHYSICAL_OT_OFFSET = 1022
PHYSICAL_NICK_OFFSET = 1352
ALLOWED = {"a", "b", "start", "select", "up", "down", "left", "right"}

def symbol_table(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        parts = line.split(";")[0].split()
        if len(parts) >= 2 and ":" in parts[0]:
            try:
                bank, address = parts[0].split(":", 1)
                result[parts[1]] = (int(bank, 16), int(address, 16))
            except ValueError:
                pass
    return result

def play(em, sequence):
    for action in sequence:
        button = action.get("button")
        frames = action.get("frames", 1)
        if not isinstance(frames, int) or not 1 <= frames <= 12000:
            raise ValueError("invalid frame count")
        if button is not None:
            if button not in ALLOWED:
                raise ValueError("unsupported button: " + str(button))
            em.button_press(button)
        em.tick(frames, render=False, sound=False)
        if button is not None:
            em.button_release(button)
            em.tick(2, render=False, sound=False)

def box_bytes(em, syms, index):
    if not isinstance(index, int) or not 0 <= index < 12:
        raise ValueError("box must be 0..11")
    start = syms["sBox1"][1] + (index % 4) * BOX_SIZE
    bank = 2 + index // 4
    return bytes(em.memory[bank, start + offset] for offset in range(BOX_SIZE))

def record(box, index):
    return (box[PHYSICAL_MON_OFFSET + index * MON_BYTES:PHYSICAL_MON_OFFSET + (index + 1) * MON_BYTES] +
            box[PHYSICAL_OT_OFFSET + index * NAME_BYTES:PHYSICAL_OT_OFFSET + (index + 1) * NAME_BYTES] +
            box[PHYSICAL_NICK_OFFSET + index * NAME_BYTES:PHYSICAL_NICK_OFFSET + (index + 1) * NAME_BYTES])

def assert_storage(em, syms, destination, count):
    box = box_bytes(em, syms, destination)
    if box[0] != count or box[count + 1] != 255:
        raise AssertionError(f"box occupancy/terminator mismatch: expected {count}, saw {box[0]}")
    return box

def stage_party_from_rom(em, syms):
    """Fixture only: invoke actual ROM roster builder on CPU, restore CPU state."""
    regs = em.register_file
    registers = ("PC","SP","A","F","B","C","D","E","HL")
    saved = {key:getattr(regs,key) for key in registers}
    bank, address = syms["SetDebugNewGameParty"]
    old_bank = em.memory[syms["hLoadedROMBank"][1]]
    saved_bytes = {i:em.memory[i] for i in (0xc000,0xc001,0xcfee,0xcfef,0xffff,0xff0f)}
    old_location = em.memory[syms["wMonDataLocation"][1]]
    try:
        em.memory[0xc000]=0x18
        em.memory[0xc001]=0xfe
        em.memory[0xcfee]=0x00
        em.memory[0xcfef]=0xc0
        em.memory[0xffff]=0
        em.memory[0xff0f]=0
        em.memory[0x2000]=bank
        em.memory[syms["hLoadedROMBank"][1]]=bank
        em.memory[syms["wMonDataLocation"][1]]=0
        regs.SP=0xcfee
        regs.PC=address
        for _ in range(2400):
            em.tick(1,render=False,sound=False)
            if regs.PC in (0xc000,0xc001):
                break
        else:
            raise AssertionError("ROM roster builder did not return")
        if em.memory[syms["wPartyCount"][1]] != 6:
            raise AssertionError("ROM roster builder did not create six Pokémon")
    finally:
        em.memory[0x2000]=old_bank
        em.memory[syms["hLoadedROMBank"][1]]=old_bank
        em.memory[syms["wMonDataLocation"][1]]=old_location
        for location,value in saved_bytes.items():
            em.memory[location]=value
        for key,value in saved.items():
            setattr(regs,key,value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", required=True)
    parser.add_argument("--sym", required=True)
    parser.add_argument("--replay", required=True, help="Recorded gameplay input JSON")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    spec = json.loads(Path(args.replay).read_text())
    for key in ("prepare", "capture", "save", "continue"):
        if not isinstance(spec.get(key), list) or not spec[key]:
            raise ValueError(f"replay must include real {key} controller actions")
    destination = spec["destination_box"]
    if type(destination) is not int or not 0 <= destination < 12:
        raise ValueError("destination_box must be integer 0..11")
    starting_count = spec.get("starting_count", 29)
    if type(starting_count) is not int or starting_count != 29:
        raise ValueError("acceptance replay must exercise 29 -> 30")
    syms = symbol_table(args.sym)
    for symbol in ("sBox1", "wPartyCount", "sYel012StorageVersion", "sYel012StorageVersionCheck"):
        if symbol not in syms:
            raise ValueError("missing symbol " + symbol)
    with tempfile.TemporaryDirectory(prefix="yel012_replay_") as temp:
        rom = Path(temp) / "yellow.gbc"
        shutil.copyfile(args.rom, rom)
        def boot():
            emulator = PyBoy(str(rom), window="null", cgb=False, sound_emulated=False)
            emulator.set_emulation_speed(0)
            return emulator
        em = boot()
        try:
            play(em, spec["prepare"])
            if spec.get("party_fixture") == "rom-debug-cpu":
                for name in ("SetDebugNewGameParty","hLoadedROMBank","wMonDataLocation"):
                    if name not in syms:
                        raise ValueError("missing party fixture symbol " + name)
                stage_party_from_rom(em,syms)
            elif "party_fixture" in spec:
                raise ValueError("unsupported party_fixture")
            if em.memory[syms["wPartyCount"][1]] != 6:
                raise AssertionError("replay did not prepare a six-Pokémon party")
            # Opt-in synthetic SRAM staging after a real debug new-game.
            # The actual battle, ball, SAVE and CONTINUE phases must still
            # run using controller input, never direct memory writes.
            if spec.get("fixture_mode") == "synthetic-physical-29":
                for name in ("sBank2AllBoxesChecksum", "sBank2IndividualBoxChecksums"):
                    if name not in syms:
                        raise ValueError("missing fixture checksum symbol " + name)
                seed_scenario(em.memory, syms, destination, 29,
                              bool(spec.get("other_boxes_full", False)))
            elif "fixture_mode" in spec:
                raise ValueError("unsupported fixture_mode")
            before = assert_storage(em, syms, destination, starting_count)
            prior_boxes = [box_bytes(em, syms, i) for i in range(12)]
            play(em, spec["capture"])
            after = assert_storage(em, syms, destination, 30)
            if record(after, 0) == record(before, 0):
                raise AssertionError("captured record not prepended")
            for index in range(29):
                if record(after, index + 1) != record(before, index):
                    raise AssertionError(f"existing record {index} changed during capture")
            for idx in range(12):
                if idx != destination and box_bytes(em, syms, idx) != prior_boxes[idx]:
                    raise AssertionError(f"capture unexpectedly modified box {idx + 1}")
            captured = record(after, 0)
            if len(captured) != 55 or captured[0] in (0, 255):
                raise AssertionError("invalid captured species/record")
            play(em, spec["save"])
            em.stop(save=True)
            em = boot()  # New emulator instance, battery SRAM loaded from disk
            play(em, spec["continue"])
            if em.memory[syms["wPartyCount"][1]] != 6:
                raise AssertionError("CONTINUE did not restore the six-Pokémon party")
            restored = assert_storage(em, syms, destination, 30)
            if restored != after or record(restored, 0) != captured:
                raise AssertionError("SAVE/CONTINUE failed to retain exact physical box data")
            for idx in range(12):
                if idx != destination and box_bytes(em, syms, idx) != prior_boxes[idx]:
                    raise AssertionError(f"reboot changed unrelated box {idx + 1}")
            report = {"party_fixture":spec.get("party_fixture","controller-only"), "fixture_mode": spec.get("fixture_mode", "controller-only"), "contract": "YEL-QOL-012-REAL-GAMEPLAY/1", "status": "PASS",
                      "destination_box": destination + 1, "before": 29, "after": 30,
                      "captured_record_hex": captured.hex(),
                      "reboot": "new PyBoy instance; actual battery SRAM"}
            output = Path(args.out)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({k: v for k, v in report.items() if k != "captured_record_hex"}))
        finally:
            em.stop(save=False)

if __name__ == "__main__":
    main()
