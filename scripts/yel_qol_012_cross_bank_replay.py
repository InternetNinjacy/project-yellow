#!/usr/bin/env python3
"""Live capture -> in-game SAVE -> fresh emulator CONTINUE proof (fail closed).

Only the initial 29 physical records are synthetic. All menu interactions,
ball use, SaveGameData, and Continue are ROM CPU/controller events.
"""
import argparse,json,shutil,tempfile
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play,box_bytes,record
from yel_qol_012_fixture import seed_scenario

def main():
    ap=argparse.ArgumentParser()
    for n in ("rom","sym","boot","route","out"):ap.add_argument("--"+n,required=True)
    ap.add_argument("--source-box",type=int,required=True)
    ap.add_argument("--target-box",type=int,required=True)
    a=ap.parse_args()
    sym=symbol_table(a.sym)
    boot=json.loads(Path(a.boot).read_text())
    route=json.loads(Path(a.route).read_text())
    assert (a.source_box,a.target_box) in ((3,4),(7,8),(11,0))
    result={"status":"NOT_VERIFIED","scope":"REAL_CROSS_BANK_CAPTURE_SAVE_CONTINUE","source_box":a.source_box+1,"target_box":a.target_box+1,"events":[],"hooks":{}}
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        rom=Path(tmp)/"yellow.gbc"
        shutil.copyfile(a.rom,rom)
        def start_emulator():
            boy=PyBoy(str(rom),window="null",cgb=False,sound_emulated=False)
            boy.set_emulation_speed(0)
            return boy
        em=start_emulator()
        counts={"DisplayBattleMenu":0,"ItemUseBall":0,"Yel012CaptureToAvailableBox":0,"SaveGameData":0}
        def hook(context):
            counts[context]+=1
        for name in counts:
            if name not in sym:raise AssertionError("missing symbol "+name)
            bank,address=sym[name]
            em.hook_register(bank,address,hook,name)
        def action(button=None,held=4,idle=135):
            events=[{"frames":held,"button":button} if button else {"frames":held}]
            if idle:events.append({"frames":idle})
            play(em,events)
            result["events"].extend(events)
        try:
            play(em,boot["prepare"])
            assert em.memory[sym["wPartyCount"][1]]==6,"DEBUG boot failed"
            play(em,route["settle"])
            seed_scenario(em.memory,sym,a.target_box,29,True)
            selected=box_bytes(em,sym,a.source_box)
            before=box_bytes(em,sym,a.target_box)
            prior=[box_bytes(em,sym,i) for i in range(12)]
            em.memory[sym["wCurrentBoxNum"][1]]=a.source_box | 0x80
            # The legacy WRAM box window is smaller than physical 30 slots.
            # Never memcpy the physical SRAM record over unrelated WRAM.
            em.memory[sym["wBoxCount"][1]]=30
            assert em.memory[sym["wBoxCount"][1]]==30
            assert all(box_bytes(em,sym,i)[0]==(29 if i==a.target_box else 30) for i in range(12))
            play(em,route["movements"])
            assert em.memory[sym["wIsInBattle"][1]]==1,"wild battle missing"
            action(None,1400,0)
            # Observed real battle-menu appearance after three A prompts.
            for attempt in range(25):
                if counts["DisplayBattleMenu"]>0:
                    result["menu_after_prompts"]=attempt
                    break
                action("a",3,90)
            assert counts["DisplayBattleMenu"]>0,"battle menu never appeared"
            action(None,90,0)
            for key in ("down","a","a"):action(key,4,125)
            for _ in range(28):
                if box_bytes(em,sym,a.target_box)[0]==30:break
                action("a",4,180)
            result["hooks"]=dict(counts)
            assert counts["ItemUseBall"]>0,"ROM ItemUseBall not run"
            assert counts["Yel012CaptureToAvailableBox"]>0,"capture transaction not run"
            after=box_bytes(em,sym,a.target_box)
            result["selected_after_capture"]=em.memory[sym["wCurrentBoxNum"][1]] & 0x7f
            assert result["selected_after_capture"]==a.source_box, "temporary capture routing changed selected box"
            assert after[0]==30,"real capture did not insert record"
            captured=record(after,0)
            assert len(captured)==55 and captured[0] not in (0,255)
            for i in range(29):
                assert record(after,i+1)==record(before,i),"existing record shifted incorrectly"
            for idx in range(12):
                if idx!=a.target_box:
                    assert box_bytes(em,sym,idx)==prior[idx],f"unrelated box {idx+1} changed before SAVE"
            result.update({"capture":"PASS","captured_record_hex":captured.hex(),
                           "captured_species":captured[0]})
            # Finish caught/tranferred text and wait for return to overworld.
            for _ in range(45):
                if em.memory[sym["wIsInBattle"][1]]==0:break
                action("a",3,145)
            result["after_battle"]={"battle":em.memory[sym["wIsInBattle"][1]],
                                   "pc":em.register_file.PC}
            assert em.memory[sym["wIsInBattle"][1]]==0,"capture dialogue did not exit battle"
            action(None,120,0)
            action("start",4,120)
            # With the Pokédex, SAVE is the fifth menu item (index 4).
            for _ in range(4):action("down",4,35)
            action("a",4,110)
            for _ in range(30):
                if counts["SaveGameData"]:break
                action("a",4,160)
            result["hooks"]=dict(counts)
            assert counts["SaveGameData"]>0,"controller SAVE did not call SaveGameData"
            # Let SRAM save finish and flush the cartridge battery.
            action(None,300,0)
            em.stop(save=True)
            em=start_emulator()
            # Power on fresh. CONTINUE is first menu entry when save exists.
            action(None,1100,0)
            for _ in range(28):
                if em.memory[sym["wPartyCount"][1]]==6:break
                action("a",4,180)
            restored=box_bytes(em,sym,a.target_box)
            result["after_continue"]={
                "party":em.memory[sym["wPartyCount"][1]],
                "box_count":restored[0],
                "record_hex":record(restored,0).hex(),
                "pc":em.register_file.PC}
            assert em.memory[sym["wPartyCount"][1]]==6,"CONTINUE failed to load party"
            assert restored[0]==30,"CONTINUE lost box count"
            assert restored==after,"CONTINUE changed physical box records"
            for idx in range(12):
                if idx!=a.target_box:
                    assert box_bytes(em,sym,idx)==prior[idx],f"CONTINUE changed unrelated box {idx+1}"
            assert (em.memory[sym["wCurrentBoxNum"][1]] & 0x7f)==a.source_box,"CONTINUE changed player-selected box"
            result["status"]="PASS_REAL_CROSS_BANK_CAPTURE_SAVE_CONTINUE"
        except Exception as e:
            result["error"]=repr(e)
            raise
        finally:
            out.write_text(json.dumps(result,indent=2)+"\n")
            em.stop(save=False)
if __name__=="__main__":main()
