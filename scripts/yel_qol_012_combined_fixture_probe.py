#!/usr/bin/env python3
"""Prove combined independent six-party + 29-of-30 physical storage precondition.

This DOES NOT simulate or claim a catch, battle, SAVE or CONTINUE.
"""
import argparse,json
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,box_bytes,record
from yel_qol_012_party_seed import seed_six_party
from yel_qol_012_fixture import seed_scenario

def main():
    p=argparse.ArgumentParser()
    for field in ("rom","sym","out"):p.add_argument("--"+field,required=True)
    args=p.parse_args()
    sym=symbol_table(args.sym)
    em=PyBoy(args.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    out=Path(args.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    report={"status":"FAIL","scope":"COMBINED_PRE_BATTLE_FIXTURE_ONLY"}
    try:
        em.tick(400,render=False,sound=False)
        party=seed_six_party(em.memory,sym)
        storage=seed_scenario(em.memory,sym,0,29,False)
        occupancy=[box_bytes(em,sym,i)[0] for i in range(12)]
        occupied=[record(box_bytes(em,sym,0),i) for i in range(29)]
        assert em.memory[sym["wPartyCount"][1]]==6
        assert occupancy==[29]+[0]*11
        assert all(len(rec)==55 and rec[0] not in (0,255) for rec in occupied)
        assert len(occupied)==29
        report.update({"status":"PASS_COMBINED_PRE_BATTLE_FIXTURE",
                       "party_count":6,"box_occupancies":occupancy,
                       "validated_box_records":len(occupied),
                       "party_fixture":party,"storage_fixture":storage})
    except Exception as exc:
        report["error"]=repr(exc)
        raise
    finally:
        out.write_text(json.dumps(report,indent=2)+"\n")
        em.stop(save=False)
if __name__=="__main__":main()
