#!/usr/bin/env python3
"""Compare native SameBoy SGB OBJ-enabled and OBJ-disabled lab frames.

This is direct compositing evidence, not a claim about an exact SGB palette
packet or physical SNES/GB color calibration.
"""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageChops
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--species",choices=["Bulbasaur","Ivysaur"],required=True)
    p.add_argument("--enabled",type=Path,required=True)
    p.add_argument("--disabled",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    x=Image.open(a.enabled).convert("RGB")
    y=Image.open(a.disabled).convert("RGB")
    if x.size!=(512,448) or y.size!=x.size:
        raise AssertionError("Native SGB framebuffer sizes mismatch")
    # Exclude SGB border, which must remain stable across an OBJ toggle.
    border_coords=[(px,py) for py in range(0,448,8) for px in range(0,512,8)
                   if px<96 or px>=416 or py<80 or py>=368]
    border_changed=sum(x.getpixel(q)!=y.getpixel(q) for q in border_coords)
    if border_changed:
        raise AssertionError("SGB border changed during OBJ-only comparison")
    a0=x.crop((96,80,416,368)).resize((160,144))
    b0=y.crop((96,80,416,368)).resize((160,144))
    diff=ImageChops.difference(a0,b0)
    changed=sum(rgb!=(0,0,0) for rgb in diff.getdata())
    if changed<8:
        raise AssertionError("OBJ disable caused no substantial central-screen sprite change")
    # The changed pixels may include protagonist/follower; sprite identity
    # still requires source-linked OAM plus a location-specific comparison.
    a.out.parent.mkdir(parents=True,exist_ok=True)
    report={"status":"SGB_OBJ_LAYER_COMPOSITING_DIAGNOSTIC_PASS",
            "species":a.species,"game_pixels_changed":changed,
            "border_sample_changed":border_changed,
            "individual_species_alpha_occlusion":"PENDING_OAM_LOCALIZATION",
            "sgb_palette_packet_correctness":"PENDING",
            "physical_hardware":"NOT_TESTED"}
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    diff.save(a.out.with_name(a.out.stem+"_difference.png"))
    print(json.dumps(report))
if __name__=="__main__":
    main()
