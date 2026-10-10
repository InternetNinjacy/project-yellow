#!/usr/bin/env python3
"""Reusable manifest-based sprite QA orchestration for Project Yellow.

A manifest defines species, approved source, test map, hardware, and gates.
This tool never marks a gate passed without the actual emulator evidence.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT = Path("tests/sprite_lab/cases.json")
MODES = {"dmg", "cgb", "sgb-ntsc"}
FACINGS = {"up", "down", "left", "right"}


def case_for(manifest, ident):
    document = json.loads(manifest.read_text())
    if document.get("schema_version") != 1:
        raise ValueError("Unsupported sprite lab schema")
    cases = document.get("cases", [])
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate sprite case IDs")
    for c in cases:
        if not re.fullmatch(r"[a-z0-9-]+", c["id"]):
            raise ValueError("Unsafe case ID")
        if not re.fullmatch(r"[A-Za-z0-9]+", c["species"]):
            raise ValueError("Unsafe species")
        if not re.fullmatch(r"SPRITE_[A-Z0-9_]+", c["sprite_symbol"]):
            raise ValueError("Unsafe sprite constant")
        if c["hardware_mode"] not in MODES:
            raise ValueError("Unsupported hardware mode")
        source = Path(c["sprite_source"])
        if source.is_absolute() or ".." in source.parts or not str(source).startswith("gfx/sprites/"):
            raise ValueError("Sprite source must live in gfx/sprites/")
        if source.is_file() and len(source.read_bytes()) != 192:
            raise ValueError(f"{c['id']}: expected 192-byte 12-tile sprite source")
        location = c["test_location"]
        if not 0 <= location["map_id"] <= 255:
            raise ValueError("Invalid map")
        if not re.fullmatch(r"SPRITE_[A-Z0-9_]+", location["placeholder"]):
            raise ValueError("Unsafe fixture placeholder")
        if set(c["expected_behavior"].get("facings", [])) != FACINGS:
            raise ValueError("Walking sprite tests must request all four directions")
        if c["expected_behavior"].get("palette_packets") not in ("pending", "required"):
            raise ValueError("Palette packet acceptance must be explicitly declared")
    return next((c for c in cases if c["id"] == ident), None)


def prepare(c, out):
    source = Path(c["test_location"]["object_source"])
    data = source.read_text()
    placeholder = c["test_location"]["placeholder"]
    if data.count(placeholder) != 1:
        raise AssertionError(f"Ambiguous DEBUG sprite fixture: {source} has {data.count(placeholder)} placeholders")
    if c["sprite_symbol"] != placeholder:
        source.write_text(data.replace(placeholder, c["sprite_symbol"], 1))
    out.mkdir(parents=True, exist_ok=True)
    payload = {"case":c, "sprite_sha256":hashlib.sha256(Path(c["sprite_source"]).read_bytes()).hexdigest() if Path(c["sprite_source"]).is_file() else None,
               "source_modified_only_for_ci":True, "verification":"NOT_RUN"}
    (out/"case_metadata.json").write_text(json.dumps(payload,indent=2)+"\n")


def validate(c, out, evidence):
    # Explicit list of independent checks. Never infer a pass from a photo.
    mode=c["hardware_mode"]
    if mode != "sgb-ntsc":
        raise AssertionError(f"{mode}: separate emulator adapter not implemented; no false PASS")
    if not Path(c["sprite_source"]).is_file():
        raise AssertionError("Generated 2bpp source missing after ROM compilation")
    prefix=c["species"].lower()
    required={
        "capture":(evidence/f"{prefix}_capture_report.json","SGB_MAP25_FRAME_CAPTURED"),
        "vram_oam":(evidence/f"{prefix}_live_integrity.json","SGB_LIVE_VRAM_OAM_PASS"),
        "direction_walk":(evidence/f"{prefix}_direction_report.json","SGB_DIRECTION_AND_WALK_CAPTURE_PASS"),
        "border":(evidence/f"{prefix}_border_report.json","SGB_BORDER_VIEWPORT_RENDER_PASS"),
        "obj_layer":(evidence/f"{prefix}_compositing.json","SGB_OBJ_LAYER_COMPOSITING_DIAGNOSTIC_PASS"),
    }
    results={}
    for name,(file,status) in required.items():
        if not file.is_file():
            raise AssertionError(f"{c['id']}: missing {name} evidence {file}")
        report=json.loads(file.read_text())
        if report.get("status") != status:
            raise AssertionError(f"{name} did not pass: {report.get('status')}")
        if name != "capture" and report.get("species") != c["species"]:
            raise AssertionError(f"{name} species mismatch")
        if name == "capture" and report.get("species_candidate") != c["species"]:
            raise AssertionError("Capture species mismatch")
        if name == "capture" and report.get("map_ram",{}).get("map_id") != c["test_location"]["map_id"]:
            raise AssertionError("Unexpected map")
        if name == "vram_oam" and report.get("source_sha256") != hashlib.sha256(Path(c["sprite_source"]).read_bytes()).hexdigest():
            raise AssertionError("Source art changed since VRAM verification")
        if name == "direction_walk" and set(report.get("facing_frames",{})) != set(c["expected_behavior"]["facings"]):
            raise AssertionError("Facing evidence incomplete")
        results[name]="PASS"
    # A visible SGB border is not an assertion that packet transfer occurred.
    if c["expected_behavior"]["palette_packets"] == "required":
        raise AssertionError("SGB palette-packet probe not yet implemented; cannot sign off")
    output={"id":c["id"],"species":c["species"],"hardware":mode,
            "verified_gates":results,"palette_packet_verification":"PENDING",
            "species_specific_transparency":"PENDING","hardware_device":"NOT_TESTED",
            "status":"PARTIAL_EMULATOR_QA_ONLY"}
    out.mkdir(parents=True,exist_ok=True)
    (out/"acceptance.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,indent=2))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=["list","prepare","validate"])
    p.add_argument("--manifest",type=Path,default=DEFAULT)
    p.add_argument("--case")
    p.add_argument("--out",type=Path,default=Path("test-results/sprite-lab"))
    p.add_argument("--evidence",type=Path,default=Path("test-results/sgb-smoke"))
    a=p.parse_args()
    if a.command=="list":
        data=json.loads(a.manifest.read_text())
        for item in data["cases"]:
            case_for(a.manifest,item["id"])
        print(json.dumps([{"id":c["id"],"species":c["species"],"hardware":c["hardware_mode"]} for c in data["cases"]],indent=2))
        return
    if not a.case:
        p.error("--case is required")
    c=case_for(a.manifest,a.case)
    if c is None:
        raise ValueError("Unknown sprite lab case")
    if a.command=="prepare":prepare(c,a.out)
    else:validate(c,a.out,a.evidence)


if __name__=="__main__":
    main()
