#!/usr/bin/env python3
"""Discover and record real DEBUG new-game controller input, fail closed.

No RAM mutation. Evidence only if the running game actually reports six
party members and the new storage-version marker after controller events.
This does not claim a battle/capture or save/continue pass.
"""
import argparse
import json
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table, play

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--rom",required=True)
    p.add_argument("--sym",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    sym=symbol_table(a.sym)
    needed=("wPartyCount","sYel012StorageVersion","sYel012StorageVersionCheck")
    for name in needed:
        if name not in sym:
            raise RuntimeError("missing symbol "+name)
    out=Path(a.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    events=[]
    em=PyBoy(a.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    status="NOT_VERIFIED"
    try:
        def step(button=None,frames=1):
            event={"frames":frames}
            if button is not None:event["button"]=button
            events.append(event)
            play(em,[event])
        def check():
            n=em.memory[sym["wPartyCount"][1]]
            v=em.memory[5,sym["sYel012StorageVersion"][1]]
            c=em.memory[5,sym["sYel012StorageVersionCheck"][1]]
            return n==6 and (v,c)==(1,0xfe)
        # Title accepts SELECT, opens DEBUG menu. Its second choice is DEBUG.
        step(frames=1100)
        step("select",frames=40)
        step(frames=80)
        step("down",frames=12)
        step(frames=25)
        step("a",frames=12)
        for _ in range(240):
            if check():
                status="PASS_DEBUG_NEW_GAME_CONTROLLER_BOOT"
                break
            step("a",frames=2)
            step(frames=25)
        result={"status":status,"prepare":events,"wPartyCount":em.memory[sym["wPartyCount"][1]],
                "storage_version":em.memory[5,sym["sYel012StorageVersion"][1]],
                "version_check":em.memory[5,sym["sYel012StorageVersionCheck"][1]],
                "cpu_pc":em.register_file.PC,
                "frames_recorded":sum(e["frames"] for e in events)}
        out.write_text(json.dumps(result,indent=2)+"\n")
        if status!="PASS_DEBUG_NEW_GAME_CONTROLLER_BOOT":
            raise AssertionError("real controller events did not establish DEBUG party/storage; see evidence JSON")
        print("Verified six-party DEBUG new game with controller-input trace:",out)
    finally:
        em.stop(save=False)

if __name__=="__main__":
    main()
