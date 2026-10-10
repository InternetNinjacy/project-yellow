#!/usr/bin/env python3
"""Probe a real battle menu from the clean-boot DEBUG capture checkpoint.

This probes controller sequences, saving screenshots and per-probe summaries.
No mutation or fake capture. The existing DEBUG Master Ball is first in bag
and is preferable to an RNG-dependent ordinary Poké Ball for this harness.
"""
import argparse, json, hashlib
from pathlib import Path
from pyboy import PyBoy
from yel_test_005_capture_audit import symbols

def main():
    p=argparse.ArgumentParser()
    for arg in ("rom","sym","state","out"):
        p.add_argument("--"+arg,required=True)
    a=p.parse_args()
    syms=symbols(a.sym)
    out=Path(a.out)
    out.mkdir(parents=True,exist_ok=True)
    for name in ("wIsInBattle","wEnemyMonSpecies2","wPartyCount","wNumBagItems","wCurrentBoxNum","wBoxCount"):
        if name not in syms: raise ValueError("Missing "+name)
    # Each candidate is an independent load of the same clean-boot state.
    candidates={
      "menu_down_item_first":[("a",2,160),("a",2,100),("down",2,20),("a",2,90),("a",2,80),("a",2,550),("a",2,420)],
      "menu_item_first":[("a",2,160),("down",2,20),("a",2,90),("a",2,80),("a",2,550),("a",2,420)],
      "intro_long_then_item":[(None,0,800),("down",2,40),("a",2,120),("a",2,150),("a",2,700),("a",2,500)],
      "item_two_steps":[(None,0,450),("down",2,30),("a",2,100),("a",2,100),("a",2,150),("a",2,700),("a",2,700)],
    }
    output=[]
    for label,sequence in candidates.items():
        emu=PyBoy(a.rom,window="null",cgb=False,sound_emulated=False)
        emu.set_emulation_speed(0)
        frames=[]
        try:
            with open(a.state,"rb") as state: emu.load_state(state)
            for i,(button,held,after) in enumerate([(None,0,0)]+sequence):
                if button: emu.button_press(button)
                try:
                    if held: emu.tick(held)
                finally:
                    if button: emu.button_release(button)
                if after: emu.tick(after)
                shot=out/f"{label}-{i:02d}.png"
                emu.screen.image.save(shot)
                data={k:int(emu.memory[syms[k][1]]) for k in ("wIsInBattle","wEnemyMonSpecies2","wPartyCount","wNumBagItems","wCurrentBoxNum","wBoxCount")}
                frames.append({"step":i,"button":button,"hold":held,"after":after,"memory":data,"screenshot":shot.name,"sha256":hashlib.sha256(shot.read_bytes()).hexdigest()})
            output.append({"candidate":label,"sequence":sequence,"frames":frames,"verified_success":False})
        finally:
            emu.stop(save=False)
    (out/"probe.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps([{ "candidate":x["candidate"],"end":x["frames"][-1]["memory"]} for x in output],indent=2))
    print("NOTE: no captures are marked successful until storage-delta assertions verify them.")

if __name__=="__main__":
    main()
