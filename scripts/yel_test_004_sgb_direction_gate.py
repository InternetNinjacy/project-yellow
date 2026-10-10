#!/usr/bin/env python3
"""Analyze separate SameBoy SGB direction/step screenshots and debugger samples.

Do not infer facing from a changed RGB frame; accept it only when paired with
symbol-resolved live engine state. Any absent direction fails closed.
"""
import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageChops

FACINGS = {0: "down", 4: "up", 8: "left", 12: "right"}
SNAPSHOT = re.compile(r"^YEL_FRAME_(\\d+)$", re.M)
READING = re.compile(r"(?im)^\\s*[0-9a-f]{4}:\\s*([0-9a-f]{2})\\b")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--species", required=True, choices=["Bulbasaur", "Ivysaur"])
    p.add_argument("--log", required=True, type=Path)
    p.add_argument("--frames", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    text = args.log.read_text(errors="replace")
    matches = list(SNAPSHOT.finditer(text))
    if not matches:
        raise AssertionError("No individually marked SameBoy memory samples")
    frames = {}
    evidence = []
    motion_positions = set()
    moving = False
    for j, mark in enumerate(matches):
        idx = int(mark.group(1))
        fragment = text[mark.end():matches[j+1].start() if j+1 < len(matches) else len(text)]
        values = [int(v, 16) for v in READING.findall(fragment)[:5]]
        if len(values) < 5:
            raise AssertionError(f"SameBoy sample {idx}: fewer than five engine state bytes: {values}")
        map_id, facing_byte, status, x, y = values
        if map_id != 0x25:
            raise AssertionError(f"Sample {idx} is not in Red's House 1F: {map_id:#x}")
        facing = FACINGS.get(facing_byte & 12)
        if facing is None:
            raise AssertionError(f"Unexpected facing byte {facing_byte:#x}")
        png = args.frames / f"direction_{idx:02d}.png"
        if not png.is_file():
            raise AssertionError(f"Missing actual SGB frame {png}")
        image = Image.open(png).convert("RGB")
        if image.size != (512,448):
            raise AssertionError(f"Invalid native SGB frame size: {image.size}")
        if facing not in frames:
            frames[facing] = png
        motion_positions.add((x,y))
        moving |= status == 3
        evidence.append({"index":idx,"frame":png.name,"facing":facing,
                         "status":status,"object_position":[x,y]})
    if set(frames) != set(FACINGS.values()):
        raise AssertionError(f"Four-direction SGB gate incomplete: observed {sorted(frames)}")
    if len(motion_positions) < 2 or not moving:
        raise AssertionError("Walking not proven by both engine movement status and location changes")
    # Color/palette integrity is a separate hardware-accurate check; this
    # records frames for visual review, not fictitious per-species color.
    report={"status":"SGB_DIRECTION_AND_WALK_CAPTURE_PASS","species":args.species,
            "samples":evidence, "facing_frames":{k:v.name for k,v in frames.items()},
            "distinct_positions":len(motion_positions),
            "palette_transparency_compositing":"PENDING",
            "real_hardware":"NOT_TESTED"}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+"\\n")
    print(json.dumps({"status":report["status"],"species":args.species,
                      "facings":list(frames),"samples":len(evidence)}))


if __name__=="__main__":
    main()
