#!/usr/bin/env python3
"""Explore real post-DEBUG overworld from saved controller replay.

Stages synthetic 29-slot physical storage only AFTER genuine six-party
DEBUG new-game startup. Reports map/movement, never claims battle/capture.
"""
import argparse,json
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play,box_bytes
from yel_qol_012_fixture import seed_scenario

def main():
    ap=argparse.ArgumentParser()
    for key in ("rom","sym","replay","out"): ap.add_argument("--"+key,required=True)
    a=ap.parse_args()
    sym=symbol_table(a.sym)
    spec=json.loads(Path(a.replay).read_text())
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    em=PyBoy(a.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    events=[]
    def state(tag):
        row={"stage":tag,"party_count":em.memory[sym["wPartyCount"][1]],
             "box1_count":box_bytes(em,sym,0)[0],
             "pc":em.register_file.PC}
        for key in ("wCurMap","wXCoord","wYCoord","wIsInBattle","wCurrentBoxNum"):
            if key in sym:row[key]=em.memory[sym[key][1]]
        events.append(row)
    try:
        play(em,spec["prepare"])
        assert em.memory[sym["wPartyCount"][1]]==6,"verified boot replay regressed"
        state("verified_debug_boot")
        play(em,[{"frames":600}])
        state("overworld_settled")
        seed_scenario(em.memory,sym,0,29,False)
        assert box_bytes(em,sym,0)[0]==29
        state("combined_staging")
        # Explore real controller movement from spawn; never force map/coords.
        for button in ["down"]*8+["left"]*3+["right"]*3+["down"]*8:
            play(em,[{"button":button,"frames":18},{"frames":30}])
            state("move_"+button)
        report={"status":"PASS_OVERWORLD_REPLAY_AND_COMBINED_STAGING",
                "scope":"NO_BATTLE_OR_CAPTURE_YET","states":events}
        out.write_text(json.dumps(report,indent=2)+"\n")
    finally:
        em.stop(save=False)
if __name__=="__main__":main()
