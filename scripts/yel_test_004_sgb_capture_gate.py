#!/usr/bin/env python3
"""Fail-closed native SGB capture: RAM map $25 and archived screenshot.

A correct location is not itself proof that Ivysaur rendered correctly.
The RGB/edge measurements are diagnostics; independent sprite verification
remains a separate acceptance gate.
"""
import argparse
import json
import re
from pathlib import Path
from PIL import Image, ImageStat

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--species",choices=["Ivysaur","Bulbasaur"],default="Ivysaur")
    p.add_argument("--log",required=True,type=Path)
    p.add_argument("--frame",required=True,type=Path)
    p.add_argument("--reference",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    raw=a.log.read_text(errors="replace")
    readings=[int(v,16) for v in re.findall(r"^>\s*=\s*\$([0-9a-fA-F]+)\s*$",raw,re.M)]
    if len(readings) < 3:
        raise AssertionError(f"No complete SameBoy RAM location snapshot: {readings}")
    loc={"map_id":readings[0],"x":readings[1],"y":readings[2]}
    if loc["map_id"] != 0x25:
        raise AssertionError(f"Refusing SGB species frame: not on REDS_HOUSE_1F $25: {loc}")
    image=Image.open(a.frame).convert("RGB")
    if image.size != (512,448):
        raise AssertionError(f"Unexpected SGB framebuffer: {image.size}")
    game=image.crop((96,80,416,368)).resize((160,144))
    out_image=a.out.with_name(a.species.lower()+"_map25_viewport.png")
    game.save(out_image)
    colors=len(game.getcolors(160*144) or [])
    std=[round(x,2) for x in ImageStat.Stat(game).stddev]
    report={
        "status":"SGB_MAP25_FRAME_CAPTURED",
        "species_candidate":a.species,
        "map_ram":loc,
        "source":"SameBoy sgb-ntsc native debugger; immediate preceding frame",
        "emulator_frame":str(a.frame),
        "cropped_viewport":str(out_image),
        "distinct_rgb_colors":colors,
        "rgb_channel_stddev":std,
        "reference_available":a.reference.is_file(),
        "sprite_visual_verification":"PENDING",
        "bulbasaur_sgb_verification":"PENDING"
    }
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report),flush=True)

if __name__=="__main__":
    main()
