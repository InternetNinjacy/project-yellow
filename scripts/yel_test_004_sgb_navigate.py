#!/usr/bin/env python3
"""Screen-grounded SameBoy SGB navigation gate.

Unlike elapsed-time screenshot checks, this fails closed unless the native SGB
screen resembles an independently captured in-game Red's House 1F reference.
No RAM pokes or synthetic map warps. Key presses are ordinary emulator input.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path
from PIL import Image, ImageFilter, ImageChops


def command(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def tap(wid, key, hold=0.13):
    command("xdotool", "keydown", "--window", wid, key)
    time.sleep(hold)
    command("xdotool", "keyup", "--window", wid, key)
    time.sleep(0.22)


def screenshot(wid, path):
    command("import", "-window", wid, str(path))
    image = Image.open(path).convert("RGB")
    # SameBoy SGB-NTSC fixed-size 512x448 window; 160x144 game area
    # is rendered at 2x within the 256x224 SNES display.
    if image.size != (512, 448):
        raise AssertionError(f"Unexpected SGB framebuffer {image.size}")
    return image.crop((96, 80, 416, 368)).resize((160, 144))


def fingerprint(im):
    # Edges are substantially more palette-invariant than RGB.
    gray = im.convert("L")
    return gray.filter(ImageFilter.FIND_EDGES)


def likeness(actual, expected):
    a, b = fingerprint(actual), fingerprint(expected)
    # Keep the comparison to fixed room tile geometry, excluding moving NPC
    # and protagonist locations. Compare top and left-hand wall/furniture only.
    rectangles = ((0, 0, 64, 62), (90, 0, 160, 58), (0, 72, 50, 144))
    shared = 0
    union = 0
    reference_edges = 0
    for rect in rectangles:
        x, y = a.crop(rect), b.crop(rect)
        a_edges = [v > 48 for v in x.getdata()]
        b_edges = [v > 48 for v in y.getdata()]
        shared += sum(a and b for a, b in zip(a_edges, b_edges))
        union += sum(a or b for a, b in zip(a_edges, b_edges))
        reference_edges += sum(b_edges)
    if reference_edges < 30 or union == 0:
        raise AssertionError("Invalid room visual template: too few edges")
    return shared / union


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.45)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    reference = Image.open(args.reference).convert("RGB")
    if reference.size != (160, 144):
        raise ValueError("Reference must be native 160x144 game pixels")
    # This is a bounded image-feedback walk, not a 'wait N seconds then PASS'.
    # Live SameBoy SGB screenshot (CI run 38015929838) shows the player
    # upstairs in REDS_HOUSE_2F, south-west of the staircase at (x=7,y=1).
    # The reported PyBoy map $00 belongs to an earlier transition stage,
    # not proof of the post-intro SGB position. Route east AROUND the table,
    # north along the right wall, then west onto the top-right stair.
    # Sprite input is edge-triggered; the visual room gate below remains
    # authoritative and refuses to claim entry without matching room art.
    # 2026-10-09 SGB screenshot sequence at step 9-13 shows the top-right\n    # stairs east of the player; travel along the top row toward it.\n    steps = ["Right"] * 4 + ["Up"] * 5 + ["Right"] * 4 + ["Up", "Right", "Up"]
    evidence = []
    for i, direction in enumerate(["initial"] + steps):
        if direction != "initial":
            tap(args.window_id, direction, hold=0.17)
        time.sleep(0.65)
        path = args.out / f"position_{i:02d}.png"
        view = screenshot(args.window_id, path)
        score = likeness(view, reference)
        evidence.append({"step": i, "input": direction, "room_likeness": round(score, 5), "screenshot": path.name})
        if score >= args.threshold:
            view.save(args.out / "lab_confirmed_160x144.png")
            (args.out / "navigation.json").write_text(json.dumps({"status":"LAB_SCREEN_CONFIRMED","threshold":args.threshold,"steps":evidence},indent=2)+"\n")
            print(f"VERIFIED SGB Red's House 1F visual reference: {score:.5f}", flush=True)
            return
    (args.out / "navigation.json").write_text(json.dumps({"status":"LAB_NOT_CONFIRMED","threshold":args.threshold,"steps":evidence},indent=2)+"\n")
    raise AssertionError("SGB lab image was not independently identified; screenshots are diagnostic, not proof")


if __name__ == "__main__":
    main()
