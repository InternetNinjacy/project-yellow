#!/usr/bin/env python3
"""YEL-TEST-005: read-only gameplay state audit for genuine capture checkpoints.

Does not create Pokémon, modify memory, or claim a completed throw.
"""
import argparse
import hashlib
import json
from pathlib import Path


def symbols(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        fields = line.split(";", 1)[0].split()
        if len(fields) < 2 or ":" not in fields[0]:
            continue
        bank, addr = fields[0].split(":", 1)
        try:
            result[fields[1]] = (int(bank, 16), int(addr, 16))
        except ValueError:
            continue
    return result


def inspect(memory, syms):
    required = ("wPartyCount", "wPartySpecies", "wNumBagItems", "wBagItems",
                "wIsInBattle", "wEnemyMonSpecies2")
    missing = [s for s in required if s not in syms]
    if missing:
        raise ValueError("Missing required symbols: " + ", ".join(missing))
    def read(s):
        bank, address = syms[s]
        if not 0xC000 <= address <= 0xDFFF:
            raise ValueError(f"Expected WRAM symbol {s}; got {bank:02x}:{address:04x}")
        return memory[address]
    party_count = read("wPartyCount")
    if party_count > 6:
        raise ValueError("Invalid party count " + str(party_count))
    party_base = syms["wPartySpecies"][1]
    species = [memory[party_base + i] for i in range(party_count)]
    item_count = read("wNumBagItems")
    if item_count > 20:
        raise ValueError("Invalid bag count " + str(item_count))
    bag_start = syms["wBagItems"][1]
    items = [[memory[bag_start + i*2], memory[bag_start + i*2 + 1]]
             for i in range(item_count)]
    ball_quantity = sum(qty for item, qty in items if item == 0x04)
    wild = read("wIsInBattle") == 1
    enemy = read("wEnemyMonSpecies2")
    checks = {
        "six_party_members": party_count == 6 and all(s not in (0, 0xFF) for s in species),
        "has_poke_ball": ball_quantity > 0,
        "wild_battle": wild,
        "enemy_species_present": enemy not in (0, 0xFF),
    }
    return {
        "party_count": party_count, "party_species_ids": species,
        "poke_ball_quantity": ball_quantity, "battle_flag": read("wIsInBattle"),
        "enemy_species_id": enemy, "checks": checks,
        "capture_preconditions_pass": all(checks.values()),
        "warning": "RAM preconditions alone do not prove capture-menu position, RNG success, or in-game save integrity",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", required=True)
    ap.add_argument("--sym", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    from pyboy import PyBoy
    emu = PyBoy(a.rom, window="null", cgb=False, sound_emulated=False)
    try:
        with open(a.state, "rb") as f:
            emu.load_state(f)
        report = inspect(emu.memory, symbols(a.sym))
        for name, path in (("rom", a.rom), ("symbols", a.sym), ("state", a.state)):
            report[name + "_sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        report["provenance"] = "UNVERIFIED_UNLESS_PAIRED_WITH_CLEAN_BOOT_REPLAY_MANIFEST"
        report["status"] = "PRECONDITIONS_PASS_ROUTE_UNVERIFIED" if report["capture_preconditions_pass"] else "FAIL"
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        if not report["capture_preconditions_pass"]:
            raise SystemExit(1)
    finally:
        emu.stop(save=False)


if __name__ == "__main__":
    main()
