#!/usr/bin/env python3
"""Real saved game, then version-marker-invalidated legacy-format refusal.

Acceptance: old-layout marker is never silently initialized or rewritten,
no CONTINUE loads the party, all existing physical Pokémon data preserved.
"""
import argparse,json,shutil,tempfile
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play,box_bytes

def main():
    p=argparse.ArgumentParser()
    for n in ("rom","sym","boot","out"):p.add_argument("--"+n,required=True)
    a=p.parse_args()
    symbols=symbol_table(a.sym)
    spec=json.loads(Path(a.boot).read_text())
    output=Path(a.out);output.parent.mkdir(parents=True,exist_ok=True)
    result={"status":"NOT_VERIFIED","scope":"NONDESTRUCTIVE_LEGACY_VERSION_REFUSAL"}
    with tempfile.TemporaryDirectory() as td:
        rom=Path(td)/"yellow.gbc"
        shutil.copyfile(a.rom,rom)
        def emu():
            game=PyBoy(str(rom),window="null",cgb=False,sound_emulated=False)
            game.set_emulation_speed(0)
            return game
        em=emu()
        counts={"SaveGameData":0}
        def saved(ctx):counts["SaveGameData"]+=1
        bank,pc=symbols["SaveGameData"]
        em.hook_register(bank,pc,saved,None)
        try:
            play(em,spec["prepare"])
            assert em.memory[symbols["wPartyCount"][1]]==6
            play(em,[{"frames":600},{"button":"start","frames":4},{"frames":100}])
            for _ in range(4):
                play(em,[{"button":"down","frames":4},{"frames":35}])
            play(em,[{"button":"a","frames":4},{"frames":110}])
            for _ in range(30):
                if counts["SaveGameData"]:break
                play(em,[{"button":"a","frames":4},{"frames":160}])
            assert counts["SaveGameData"],"in-game SaveGameData wasn't executed"
            play(em,[{"frames":300}])
            before=[box_bytes(em,symbols,i) for i in range(12)]
            em.stop(save=True)
            em=emu()
            assert em.memory[5,symbols["sYel012StorageVersionCheck"][1]]==254
            em.memory[5,symbols["sYel012StorageVersionCheck"][1]]=0
            loader_hits=[0]
            if "TryLoadSaveFile" not in symbols:raise ValueError("missing TryLoadSaveFile")
            bank,pc=symbols["TryLoadSaveFile"]
            def loaded(context):loader_hits[0]+=1
            em.hook_register(bank,pc,loaded,None)
            play(em,[{"frames":1100}])
            for _ in range(24):
                if loader_hits[0]>0 and em.memory[symbols["wSaveFileStatus"][1]]!=0:break
                play(em,[{"button":"a","frames":4},{"frames":145}])
            result["loader_hits"]=loader_hits[0]
            assert loader_hits[0]>0,"game never entered TryLoadSaveFile"
            result["status_code"]=em.memory[symbols["wSaveFileStatus"][1]]
            result["party_count"]=em.memory[symbols["wPartyCount"][1]]
            assert result["status_code"]==1,"legacy marker did not reject old format"
            assert [box_bytes(em,symbols,i) for i in range(12)]==before,"legacy refusal changed physical boxes"
            assert em.memory[5,symbols["sYel012StorageVersionCheck"][1]]==0,"legacy marker was overwritten"
            result["status"]="PASS_INCOMPATIBLE_SAVE_REFUSED_WITHOUT_BOX_WRITES"
        except Exception as error:
            result["error"]=repr(error)
            raise
        finally:
            output.write_text(json.dumps(result,indent=2)+"\n")
            em.stop(save=False)
if __name__=="__main__":main()
