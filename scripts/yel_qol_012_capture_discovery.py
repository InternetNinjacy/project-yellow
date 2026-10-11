#!/usr/bin/env python3
"""Real wild Route 1 battle / Ball menu controller discovery; fail closed.

Loads independently verified DEBUG boot and grass route. The only memory
writes seed 29 initial box records. Catch must invoke actual ROM ItemUseBall.
A failure artifact retains full input trace and entrypoint checkpoints.
"""
import argparse,json
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play,box_bytes,record
from yel_qol_012_fixture import seed_scenario

def main():
    p=argparse.ArgumentParser()
    for name in ("rom","sym","boot","route","out"):p.add_argument("--"+name,required=True)
    args=p.parse_args()
    syms=symbol_table(args.sym)
    boot=json.loads(Path(args.boot).read_text())
    route=json.loads(Path(args.route).read_text())
    em=PyBoy(args.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    output=Path(args.out);output.parent.mkdir(parents=True,exist_ok=True)
    report={"status":"NOT_VERIFIED","scope":"REAL_WILD_BALL_MENU_DISCOVERY",
            "timeline":[],"controller_inputs":[],"hooks":[]}
    try:
        wanted=[n for n in syms if any(token in n for token in
                ("BattleMenu","ItemUseBall","ItemUseItem","DisplayBattleMenu","StartBattle","HandleBattleMenu"))]
        report["available_battle_symbols"]=wanted[:75]
        for name in dict.fromkeys([n for n in ("StartBattle","DisplayBattleMenu","DisplayBattleMenu.handleBattleMenuInput","ItemUseBall","ItemUseBall.captureStorageReady","ItemUseBall.sendToBox") if n in syms]+wanted[:65]):
            bank,address=syms[name]
            def callback(context,label=name):
                if len(report["hooks"])<250:
                    report["hooks"].append({"name":label,"party":em.memory[syms["wPartyCount"][1]],
                     "in_battle":em.memory[syms["wIsInBattle"][1]],
                     "physical_count":box_bytes(em,syms,0)[0]})
            try:em.hook_register(bank,address,callback,None)
            except ValueError:pass
        def snapshot(stage):
            report["timeline"].append({"stage":stage,"pc":em.register_file.PC,
                "in_battle":em.memory[syms["wIsInBattle"][1]],
                "party":em.memory[syms["wPartyCount"][1]],
                "physical_count":box_bytes(em,syms,0)[0]})
        def action(button=None,frames=4,rest=80):
            actions=[({"button":button,"frames":frames} if button else {"frames":frames})]
            if rest:actions.append({"frames":rest})
            play(em,actions)
            report["controller_inputs"].extend(actions)
            snapshot("press_"+str(button))
        play(em,boot["prepare"])
        if em.memory[syms["wPartyCount"][1]]!=6:raise AssertionError("DEBUG party missing")
        play(em,route["settle"])
        seed_scenario(em.memory,syms,0,29,False)
        before=box_bytes(em,syms,0)
        play(em,route["movements"])
        snapshot("after_real_route1_grass")
        if em.memory[syms["wIsInBattle"][1]]!=1:
            raise AssertionError("real wild battle did not start from controller route")
        action(None,frames=1400,rest=0)
        # Advance opening text only until the game's *actual* battle menu.
        # Never mash A after that checkpoint: it selects FIGHT.
        for attempt in range(28):
            if any(e["name"]=="DisplayBattleMenu" for e in report["hooks"]):
                report["battle_menu_reached_after_a"]=attempt
                break
            action("a",3,90)
        else:
            report["battle_menu_unreached"]=True
        if em.memory[syms["wIsInBattle"][1]]==1 and "battle_menu_reached_after_a" in report:
            # Gen I menu is FIGHT/PKMN above ITEM/RUN; DOWN selects ITEM.
            action(None,frames=90,rest=0)
            for button in ("down","a","a"):
                action(button,4,125)
            # In DEBUG inventory Master Ball is the first item; trace
            # ItemUseBall to confirm any Ball use rather than guessing.
            for attempt in range(10):
                if any(e["name"]=="ItemUseBall" for e in report["hooks"]):
                    report["item_use_ball_after_extra_a"]=attempt
                    break
                action("a",4,170)
                if em.memory[syms["wIsInBattle"][1]]!=1:break
        action(None,frames=1200,rest=0)
        report["hook_count"]=len(report["hooks"])
        report["last_cpu_pc"]=em.register_file.PC
        if box_bytes(em,syms,0)[0]==30:
            after=box_bytes(em,syms,0)
            if len(record(after,0))!=55 or record(after,0)==record(before,0):
                raise AssertionError("physical box count changed without a valid inserted record")
            report["status"]="PASS_REAL_BALL_CAUGHT_TO_PHYSICAL_BOX"
            report["captured_record_hex"]=record(after,0).hex()
        else:
            report["status"]="NO_CAPTURE_YET"
    except Exception as error:
        report["error"]=repr(error)
        raise
    finally:
        output.write_text(json.dumps(report,indent=2)+"\n")
        em.stop(save=False)
if __name__=="__main__":main()
