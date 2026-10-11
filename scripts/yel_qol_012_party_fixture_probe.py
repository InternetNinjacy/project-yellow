#!/usr/bin/env python3
"""Actual PyBoy CPU execution of six-party fixture; independent of DEBUG menu."""
import argparse,json
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table
from yel_qol_012_party_seed import seed_six_party

def main():
    ap=argparse.ArgumentParser()
    for field in ("rom","sym","out"): ap.add_argument("--"+field,required=True)
    args=ap.parse_args()
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    syms=symbol_table(args.sym)
    required=("wPartyCount","wPartySpecies","wPartyMon1","wPartyMon1OT","wPartyMon1Nick")
    for name in required:
        if name not in syms:raise ValueError("missing "+name)
    em=PyBoy(args.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    result={"status":"FAIL","type":"TEST_ONLY_SYNTHETIC_WRAM_PARTY_FIXTURE"}
    try:
        em.tick(400,render=False,sound=False)
        try:
            seed_six_party(em.memory,syms)
            count=em.memory[syms["wPartyCount"][1]]
            species=[em.memory[syms["wPartySpecies"][1]+i] for i in range(6)]
            # Distinct species and 44-byte Gen I party records are required.
            offsets=[syms["wPartyMon1"][1]+44*i for i in range(6)]
            records=[bytes(em.memory[at+j] for j in range(44)) for at in offsets]
            assert count==6 and len(set(species))==6 and all(x not in (0,255) for x in species)
            assert all(rec[0]==species[i] for i,rec in enumerate(records))
            result.update({"status":"PASS_SYNTHETIC_SIX_PARTY_RECORDS","count":count,
                           "species":species,"record_hex":[v.hex() for v in records]})
        except Exception as err:
            result["error"]=str(err)
            raise
        finally:
            out.write_text(json.dumps(result,indent=2)+"\n")
    finally:
        em.stop(save=False)
if __name__=="__main__":main()
