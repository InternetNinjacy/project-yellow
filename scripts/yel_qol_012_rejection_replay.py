#!/usr/bin/env python3
"""Negative real-controller capture checks: fail closed and preserve all physical records."""
import argparse,json
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play,box_bytes
from yel_qol_012_fixture import seed_scenario,fill_box,fix_bank_checksums

CASES=("all_full","bad_version","bad_sentinel","interrupted_stage","interrupted_commit")
def main():
    p=argparse.ArgumentParser()
    for key in ("rom","sym","boot","route","out"):p.add_argument("--"+key,required=True)
    p.add_argument("--case",choices=CASES,required=True)
    args=p.parse_args()
    symbols=symbol_table(args.sym)
    em=PyBoy(args.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    report={"case":args.case,"status":"NOT_VERIFIED","hooks":{}}
    hooks={name:0 for name in ("DisplayBattleMenu","ItemUseBall","Yel012PreflightCaptureTarget","Yel012CaptureToAvailableBox","Yel012CommitTransaction")}
    def visited(name):hooks[name]+=1
    for name in hooks:
        if name not in symbols:raise ValueError("missing symbol "+name)
        bank,pc=symbols[name]
        em.hook_register(bank,pc,visited,name)
    def step(button=None,held=4,idle=100):
        actions=[{"frames":held,"button":button} if button else {"frames":held}]
        if idle:actions.append({"frames":idle})
        play(em,actions)
    try:
        boot=json.loads(Path(args.boot).read_text())
        route=json.loads(Path(args.route).read_text())
        play(em,boot["prepare"])
        assert em.memory[symbols["wPartyCount"][1]]==6
        play(em,route["settle"])
        seed_scenario(em.memory,symbols,0,30,True)
        em.memory[symbols["wCurrentBoxNum"][1]]=0x80
        em.memory[symbols["wBoxCount"][1]]=30
        if args.case!="all_full":
            fill_box(em.memory,symbols,1,29)
            fix_bank_checksums(em.memory,symbols,2)
        if args.case=="bad_version":
            em.memory[5,symbols["sYel012StorageVersionCheck"][1]]=0
        if args.case=="bad_sentinel":
            box1=symbols["sBox1"][1]
            # Corrupt the 29-record target's terminator in box 2.
            em.memory[2,box1+1682+30]=0
            # Leave checksum as-is: corruption must never be silently repaired.
        if args.case.startswith("interrupted_"):
            em.memory[5,symbols["sYel012TransactionStatus"][1]]=1 if args.case=="interrupted_stage" else 2
        prior=[box_bytes(em,symbols,i) for i in range(12)]
        marker=bytes(em.memory[5,symbols[k][1]] for k in
                     ("sYel012StorageVersion","sYel012StorageVersionCheck","sYel012TransactionStatus"))
        bag_start=symbols["wNumBagItems"][1]
        bag_before=bytes(em.memory[bag_start+i] for i in range(50))
        selected_before=em.memory[symbols["wCurrentBoxNum"][1]]
        play(em,route["movements"])
        assert em.memory[symbols["wIsInBattle"][1]]==1,"wild battle missing"
        step(None,1400,0)
        for _ in range(25):
            if hooks["DisplayBattleMenu"]:break
            step("a",3,90)
        assert hooks["DisplayBattleMenu"]>0,"battle menu missing"
        step(None,90,0)
        for button in ("down","a","a"):step(button,4,125)
        for _ in range(12):step("a",4,180)
        report["hooks"]=dict(hooks)
        report["battle"]=em.memory[symbols["wIsInBattle"][1]]
        assert hooks["ItemUseBall"]>0,"ROM ball action not entered"
        assert hooks["Yel012PreflightCaptureTarget"]>0,"physical preflight not reached"
        assert hooks["Yel012CaptureToAvailableBox"]==0,"unsafe transaction entered"
        assert hooks["Yel012CommitTransaction"]==0,"unsafe commit entered"
        assert [box_bytes(em,symbols,i) for i in range(12)]==prior,"box data changed on rejected capture"
        assert bytes(em.memory[bag_start+i] for i in range(50))==bag_before,"ball inventory changed"
        assert em.memory[symbols["wCurrentBoxNum"][1]]==selected_before,"selected box changed"
        assert bytes(em.memory[5,symbols[k][1]] for k in
                     ("sYel012StorageVersion","sYel012StorageVersionCheck","sYel012TransactionStatus"))==marker,"storage status mutated"
        report["status"]="PASS_REJECTED_WITHOUT_CONSUMPTION_OR_STORAGE_CHANGE"
    except Exception as error:
        report["error"]=repr(error)
        raise
    finally:
        out.write_text(json.dumps(report,indent=2)+"\n")
        em.stop(save=False)
if __name__=="__main__":main()
