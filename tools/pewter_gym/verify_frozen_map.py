#!/usr/bin/env python3
"""Static acceptance checks for the dedicated Pewter Gym geometry."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
original_map = (ROOT / "maps/PewterGym.blk").read_bytes()
new_blocks = (ROOT / "gfx/blocksets/pewter_gym.bst").read_bytes()
old_blocks = (ROOT / "gfx/blocksets/gym.bst").read_bytes()
new_tileset = (ROOT / "gfx/tilesets/pewter_gym.png").read_bytes()
old_tileset = (ROOT / "gfx/tilesets/gym.png").read_bytes()

assert len(original_map) == 35, "Original 5x7 block-map footprint changed"
assert len(old_blocks) % 16 == len(new_blocks) % 16 == 0
assert len(new_blocks) // 16 <= 256, "Block ID limit"
assert max(original_map) < len(new_blocks) // 16
assert new_tileset.startswith(b"\x89PNG\r\n\x1a\n")
assert new_tileset[16:24] == old_tileset[16:24] == bytes.fromhex("0000008000000030"), "Tileset dimensions must be 128x48"

# Compare the changed map block-by-block with the corresponding original tile positions.
baseline_map = bytes.fromhex(
    "08 0a 0a 0a 09 "
    "0c 0b 05 0b 0d "
    "0e 12 13 0b 0f "
    "0e 12 13 0b 0f "
    "0c 07 05 06 0d "
    "05 11 05 10 05 "
    "05 05 04 05 05"
)
ice_count = snow_count = 0
for pos, (old_id, new_id) in enumerate(zip(baseline_map, original_map)):
    before = old_blocks[16*old_id:16*(old_id+1)]
    after = new_blocks[16*new_id:16*(new_id+1)]
    assert len(before) == len(after) == 16
    bx, by = pos % 5, pos // 5
    for t, (a, b) in enumerate(zip(before, after)):
        tx, ty = bx*4+t%4, by*4+t//4
        expected = a
        if a == 0x11:
            if 8 <= tx <= 11 and 5 <= ty <= 23:
                expected = 0x5f
                ice_count += 1
            elif 2 <= ty <= 23:
                expected = 0x5e
                snow_count += 1
        assert b == expected, f"Unexpected tile at block {pos} tile {t}: {a:02x}->{b:02x}"
assert (snow_count, ice_count) == (212,68), (snow_count,ice_count)
print("Pewter Gym static geometry verified: 35 blocks, 212 snowy tiles, 68 ice tiles, all other tiles unchanged.")
