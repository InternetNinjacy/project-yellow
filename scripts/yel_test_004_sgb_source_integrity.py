#!/usr/bin/env python3
"""YEL-TEST-004: independently audit approved 2bpp overworld tile assets.

This gate proves immutable source structure and species isolation only.
It does NOT claim SameBoy VRAM/OAM or visual animation verification.
"""
import argparse
import hashlib
import json
from pathlib import Path


def inspect(path):
    raw = path.read_bytes()
    if len(raw) != 192:
        raise AssertionError(f"{path}: expected 12 2bpp tiles (192 bytes), got {len(raw)}")
    tiles = []
    for offset in range(0, len(raw), 16):
        tile = raw[offset:offset + 16]
        pixels = []
        for row in range(8):
            low, high = tile[2 * row], tile[2 * row + 1]
            pixels.extend(((low >> bit) & 1) | (((high >> bit) & 1) << 1)
                          for bit in range(7, -1, -1))
        tiles.append(pixels)
    histogram = [sum(p == idx for tile in tiles for p in tile) for idx in range(4)]
    if not histogram[0] or not sum(histogram[1:]):
        raise AssertionError(f"{path}: no transparent/background index or no visible ink")
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_length": len(raw), "tiles": len(tiles),
            "pixel_index_histogram": histogram,
            "unique_tile_count": len({tuple(t) for t in tiles})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bulbasaur", type=Path, required=True)
    parser.add_argument("--ivysaur", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = {"Bulbasaur": inspect(args.bulbasaur),
            "Ivysaur": inspect(args.ivysaur)}
    if data["Bulbasaur"]["sha256"] == data["Ivysaur"]["sha256"]:
        raise AssertionError("Distinct approved species must not share identical artwork bytes")
    report = {"status": "SGB_2BPP_SOURCE_INTEGRITY_PASS",
              "scope": "static approved source bytes, not live SGB render",
              "species": data,
              "sgb_vram_oam_animation_compositing": "PENDING",
              "physical_hardware": "PENDING"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
