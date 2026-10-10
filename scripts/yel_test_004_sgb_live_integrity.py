#!/usr/bin/env python3
"""Fail-closed SameBoy memory dump verifier for the isolated SGB species lab.

Only the emulator's live examine output counts. A static source match alone
cannot certify VRAM/OAM loading, animation, or actual display.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def symbols(path):
    out = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) > 1 and ":" in parts[0]:
            if parts[1] in ("wShadowOAM", "wSprite01StateData1"):
                out[parts[1]] = int(parts[0].split(":")[-1], 16)
    if set(out) != {"wShadowOAM", "wSprite01StateData1"}:
        raise AssertionError(f"Required RGBDS symbols absent: {out}")
    return out


def parse_dump(transcript, start, size):
    # SameBoy examine emits address-labelled rows. Never accept values from
    # unrelated debugger commands or silently fill missing bytes with zero.
    found = {}
    for raw in transcript.splitlines():
        match = re.match(r"^\s*(?:>\s*)?([0-9a-fA-F]{4}):\s*((?:[0-9a-fA-F]{2}(?:\s+|$))+)", raw)
        if not match:
            continue
        addr = int(match.group(1), 16)
        for i, token in enumerate(match.group(2).split()):
            loc = addr + i
            if start <= loc < start + size:
                found[loc] = int(token, 16)
    missing = [hex(x) for x in range(start, start + size) if x not in found]
    if missing:
        raise AssertionError(f"Incomplete live SameBoy memory dump at {start:#06x}: {len(missing)} missing; first={missing[:5]}")
    return bytes(found[x] for x in range(start, start + size))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--species", required=True, choices=["Bulbasaur", "Ivysaur"])
    p.add_argument("--sym", required=True, type=Path)
    p.add_argument("--sprite-2bpp", required=True, type=Path)
    p.add_argument("--transcript", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    sym = symbols(a.sym)
    raw = a.transcript.read_text(errors="replace")
    source = a.sprite_2bpp.read_bytes()
    if len(source) != 192:
        raise AssertionError("Species source must contain exactly 192 bytes")
    vram = parse_dump(raw, 0x8000, 0x1800)
    shadow = parse_dump(raw, sym["wShadowOAM"], 160)
    hardware = parse_dump(raw, 0xFE00, 160)
    offsets = [i for i in range(0, len(vram) - 191, 16) if vram[i:i + 192] == source]
    if not offsets:
        raise AssertionError(f"{a.species}: approved full 192-byte sprite absent from live SameBoy VRAM")
    first = offsets[0] // 16
    eligible = set(range(first, first + 12))
    def entries(data):
        return [{"slot": i, "y": data[i * 4], "x": data[i * 4 + 1],
                 "tile": data[i * 4 + 2], "flags": data[i * 4 + 3]}
                for i in range(40) if data[i * 4] and data[i * 4 + 1]
                and data[i * 4 + 2] in eligible]
    # Group live hardware and shadow OAM by the same stopped-CPU snapshot.
    # A wandering object may be clipped at one instant, so require at least
    # one independently paired snapshot with four displayed species tiles.
    starts = list(re.finditer(r"(?im)^>\\s*fe00:", raw))
    observations = []
    for n, mark in enumerate(starts):
        section = raw[mark.start():starts[n+1].start() if n+1 < len(starts) else len(raw)]
        try:
            live_hardware = parse_dump(section, 0xFE00, 160)
            live_shadow = parse_dump(section, sym["wShadowOAM"], 160)
        except AssertionError:
            continue
        observations.append((entries(live_shadow), entries(live_hardware)))
    passing = [(s,h) for s,h in observations if len(s)>=4 and len(h)>=4]
    if not passing:
        raise AssertionError(
            f"{a.species}: no simultaneous four-tile OAM match across "
            f"{len(observations)} paired native SGB snapshots")
    shadow_matches, hardware_matches = passing[0]
    report = {"status": "SGB_LIVE_VRAM_OAM_PASS", "species": a.species,
              "model": "SameBoy sgb-ntsc", "source_sha256": hashlib.sha256(source).hexdigest(),
              "vram_matched_address": hex(0x8000 + offsets[0]),
              "matching_vram_offsets": [hex(0x8000 + x) for x in offsets],
              "shadow_oam_matches": shadow_matches, "hardware_oam_matches": hardware_matches,\n              "paired_oam_snapshots_inspected": len(observations),
              "facing_walking_transparency_palette": "PENDING",
              "physical_hardware": "PENDING"}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
