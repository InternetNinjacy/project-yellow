#!/usr/bin/env python3
"""SGB border/viewport diagnostic, not a per-species color assignment claim."""
import argparse
import json
from pathlib import Path
from PIL import Image

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--species",choices=["Bulbasaur","Ivysaur"],required=True)
    p.add_argument("--frame",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    im=Image.open(a.frame).convert("RGB")
    if im.size!=(512,448):
        raise AssertionError(f"Expected SameBoy SGB 512x448 canvas, got {im.size}")
    border=Image.new("RGB",im.size)
    border.paste(im)
    # The SGB game image occupies the center rectangle at 2x scaling.
    # Evaluate display evidence outside it independently from sprite identity.
    all_pixels=list(im.getdata())
    game=im.crop((96,80,416,368))
    border_samples=[]
    for y in range(im.height):
        for x in range(im.width):
            if x<96 or x>=416 or y<80 or y>=368:
                border_samples.append(all_pixels[y*512+x])
    unique_border=len(set(border_samples))
    unique_game=len(set(game.getdata()))
    non_gray_border=sum(r!=g or g!=b for r,g,b in border_samples)
    if unique_border<4 or non_gray_border==0:
        raise AssertionError("Authentic SGB decorative border/color not visible")
    if unique_game<2:
        raise AssertionError("SGB game viewport does not contain visible graphics")
    report={"status":"SGB_BORDER_VIEWPORT_RENDER_PASS","species":a.species,
            "model":"SameBoy v1.0.3 SGB-NTSC",
            "canvas":[512,448],"game_rectangle":[96,80,416,368],
            "border_unique_colors":unique_border,"game_unique_colors":unique_game,
            "border_non_gray_pixels":non_gray_border,
            "species_specific_overworld_palette":"NOT_ASSUMED",
            "palette_packet_accuracy":"UNVERIFIED",
            "transparency_and_occlusion":"UNVERIFIED",
            "physical_hardware":"NOT_TESTED"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":
    main()
