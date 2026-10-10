#!/usr/bin/env python3
"""Fail-closed SameBoy debugger proof: two live map/x/y samples."""
import argparse
import json
import re
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--log",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args()
    raw=a.log.read_text(errors="replace")
    readings=[int(x,16) for x in re.findall(r"^>\s*=\s*\$([0-9a-fA-F]+)\s*$",raw,re.M)]
    if len(readings)<6:
        raise AssertionError(f"Expected 6 live debugger readings, got {len(readings)}: {readings}")
    values=[{"map_id":readings[i],"x":readings[i+1],"y":readings[i+2]} for i in (0,3)]
    for value in values:
        if not 0<=value["x"]<256 or not 0<=value["y"]<256:
            raise AssertionError(f"Invalid live coordinate sample: {value}")
    # Map changes are valid movement, and the warp should be recorded rather than rejected.
    # A true no-op (all three fields equal) is the actual failure case.
    if values[0] == values[1]:
        raise AssertionError(f"SameBoy debug samples did not show movement or warp: {values}")
    # ROM map constants: REDS_HOUSE_1F=$25 and REDS_HOUSE_2F=$26.
    # Confirm the two samples are the actual lab map and upstairs map.
    # The second sample follows the old GUI navigation routine, which walks
    # out of the lab. This establishes the mapping, not visual sprite QA.
    if values[0]["map_id"] != 0x25 or values[1]["map_id"] != 0x26:
        raise AssertionError(f"Unexpected map sequence, expected Red House 1F -> 2F: {values}")
    a.out.write_text(json.dumps({"status":"SGB_LIVE_MAP_XY_READ_PASS","samples":values,"map_changed":values[0]["map_id"] != values[1]["map_id"],"source":"SameBoy debugger FIFO, symbol-resolved WRAM","sgb_species_visual_status":"PENDING"},indent=2)+"\n")
    print(f"LIVE_MAP_XY_PASS samples={values}")

if __name__=="__main__":
    main()
