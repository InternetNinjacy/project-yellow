#!/usr/bin/env python3
"""Generate isolated Pewter Gym assets without editing the shared Gym tileset.

Run from repository root after installing Pillow:
    python tools/pewter_gym/build_frozen_assets.py

Outputs are deliberately uncommitted until validated in a ROM build.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
GFX = ROOT / "gfx/tilesets/gym.png"
BLOCKS = ROOT / "gfx/blocksets/gym.bst"
MAP = ROOT / "maps/PewterGym.blk"
OUT_GFX = ROOT / "gfx/tilesets/pewter_gym.png"
OUT_BLOCKS = ROOT / "gfx/blocksets/pewter_gym.bst"
OUT_MAP = ROOT / "maps/PewterGym.blk"   # Do not run until map integration is planned!
SNOW = ROOT / "art/pewter_gym/snow_floor_8x8.png"
ICE = ROOT / "art/pewter_gym/sliding_ice_8x8.png"
FROST = ROOT / "art/pewter_gym/frost_boulder_16x16.png"
FLOOR_TILE = 0x11
SNOW_TILE = 0x5E
ICE_TILE = 0x5F
WIDTH_BLOCKS = 5
HEIGHT_BLOCKS = 7

def main():
    for file in (GFX, BLOCKS, MAP, SNOW, ICE, FROST):
        if not file.exists():
            raise SystemExit(f"Missing input: {file}")
    image = Image.open(GFX).convert("L")
    if image.size != (128, 48):
        raise SystemExit("Unexpected original Gym image dimensions")
    original = image.copy()
    for path,xy,size in [
        (FROST, (56, 0), (16, 16)),
        (SNOW, (112, 40), (8, 8)),    # $5E within the original 96-tile budget
        (ICE, (120, 40), (8, 8)),     # $5F within the original 96-tile budget
    ]:
        tile = Image.open(path).convert("L")
        if tile.size != size or set(tile.getdata()) - {0,85,170,255}:
            raise SystemExit(f"Unexpected dimensions or grayscale values: {path}")
        image.paste(tile, xy)
    base_blocks = BLOCKS.read_bytes()
    base_map = MAP.read_bytes()
    if len(base_blocks) % 16 or len(base_map) != WIDTH_BLOCKS * HEIGHT_BLOCKS:
        raise SystemExit("Unexpected original block/map size")
    blocks = bytearray(base_blocks)
    remapped = bytearray(base_map)
    cache = {}
    snow_count = ice_count = 0
    for by in range(HEIGHT_BLOCKS):
        for bx in range(WIDTH_BLOCKS):
            pos = by * WIDTH_BLOCKS + bx
            block_id = base_map[pos]
            old = base_blocks[block_id * 16: (block_id + 1) * 16]
            block = bytearray(old)
            for iy in range(4):
                for ix in range(4):
                    index = iy * 4 + ix
                    if old[index] != FLOOR_TILE:
                        continue
                    tx = bx * 4 + ix
                    ty = by * 4 + iy
                    if 8 <= tx <= 11 and 5 <= ty <= 23:
                        block[index] = ICE_TILE
                        ice_count += 1
                    elif 2 <= ty <= 23:
                        block[index] = SNOW_TILE
                        snow_count += 1
            if block == old:
                continue
            key = bytes(block)
            if key not in cache:
                if len(blocks) // 16 >= 256:
                    raise SystemExit("Block ID budget exceeded")
                cache[key] = len(blocks) // 16
                blocks.extend(block)
            remapped[pos] = cache[key]
    # Fail closed: refuse overwriting source-map in the tool itself.
    out_map = ROOT / "build/pewter_gym/PewterGym.blk"
    out_map.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT_GFX)
    OUT_BLOCKS.write_bytes(blocks)
    out_map.write_bytes(remapped)
    if GFX.read_bytes() != GFX.read_bytes():
        raise SystemExit("Unreachable source-preservation guard")
    print(f"Prepared isolated Pewter tileset, {snow_count} snow / {ice_count} ice cells")
    print(f"Map candidate: {out_map} (requires explicit promotion and QA)")

if __name__ == "__main__":
    main()
