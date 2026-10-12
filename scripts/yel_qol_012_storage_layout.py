#!/usr/bin/env python3
"""YEL-QOL-012 physical storage plan and red-line assertions (no emulator state)."""
from dataclasses import dataclass

BOXES = 12
SLOTS = 30
BOX_BYTES = 2 + SLOTS * (1 + 33 + 11 + 11)
BANK_BYTES = 8192
SRAM_BANKS = 8
CORE_BANKS = {0, 1}
BOX_BANKS = (2, 3, 4)
BOXES_PER_BANK = 4

@dataclass(frozen=True)
class Address:
    bank: int
    offset: int

def box_location(index: int) -> Address:
    if index < 0 or index >= BOXES:
        raise ValueError("Invalid PC box")
    return Address(BOX_BANKS[index // BOXES_PER_BANK],
                   (index % BOXES_PER_BANK) * BOX_BYTES)

def check_layout() -> None:
    assert BOX_BYTES == 1682, BOX_BYTES
    assert BOXES_PER_BANK * BOX_BYTES + 5 <= BANK_BYTES
    assert len(set(BOX_BANKS)) == len(BOX_BANKS)
    assert not CORE_BANKS.intersection(BOX_BANKS)
    assert max(BOX_BANKS) < SRAM_BANKS
    addresses = [box_location(i) for i in range(BOXES)]
    assert len(set(addresses)) == BOXES
    for i, address in enumerate(addresses):
        assert address.offset + BOX_BYTES <= BANK_BYTES
        print(f"box {i+1:02d}: SRAM bank {address.bank}, byte offset {address.offset:04x}, "
              f"end {address.offset+BOX_BYTES:04x}")
    print(f"{BOXES*SLOTS} slots, {BOXES*BOX_BYTES} box bytes, "
          f"{len(BOX_BANKS)*BANK_BYTES} bytes dedicated across 3 banks")

if __name__ == "__main__":
    check_layout()
