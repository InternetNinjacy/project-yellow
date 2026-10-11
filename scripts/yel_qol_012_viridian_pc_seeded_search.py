#!/usr/bin/env python3
"""Find Viridian Pokémon Center PC through real overworld A interaction using PyBoy snapshots for search."""
import argparse,io,json
from pathlib import Path
from collections import deque
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play
from yel_qol_012_fixture import seed_scenario

def snapshot(em):
    b=io.BytesIO();em.save_state(b);return b.getvalue()
def main():
    p=argparse.ArgumentParser()
    for name in ("rom","sym","boot","route","out"):p.add_argument("--"+name,required=True)
    a=p.parse_args()
    sym=symbol_table(a.sym)
    boot=json.loads(Path(a.boot).read_text())
    stairs=json.loads(Path(a.route).read_text())
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    em=PyBoy(a.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    count=[0]
    bank,pc=sym["ActivatePC"]
    details=[]
    def hooked(ctx):
        count[0]+=1
        details.append({"location":where(),"facing":em.memory[sym["wSpritePlayerStateData1FacingDirection"][1]],"pc":em.register_file.PC})
    em.hook_register(bank,pc,hooked,None)
    def where():
        return tuple(em.memory[sym[n][1]] for n in ("wCurMap","wXCoord","wYCoord"))
    def move(button):
        old=where()
        play(em,[{"button":button,"frames":8},{"frames":24}])
        if where()[0]!=old[0]:play(em,[{"frames":300}])
    result={"status":"NOT_VERIFIED","scope":"CONTROLLER_ACTIVATE_PC_DISCOVERY"}
    try:
        play(em,boot["prepare"])
        assert em.memory[sym["wPartyCount"][1]]==6
        play(em,[{"frames":600}])
        seed_scenario(em.memory,sym,0,30,False)
        for direction in stairs["directions"]:move(direction)
        assert where()[0]==41,("failed Viridian Pokémon Center path",where())
        start=where()
        q=deque([(start,snapshot(em),[])])
        seen={start};found=None
        while q and len(seen)<70:
            pos,blob,path=q.popleft()
            for direction in ("up","right","down","left"):
                em.load_state(io.BytesIO(blob))
                move(direction)
                if where()[0]!=41:continue
                after_move=snapshot(em)
                play(em,[{"button":"a","frames":4},{"frames":120}])
                if count[0]:
                    found={"position":pos,"facing":direction,"directions":path,
                           "last_move":direction,"hits":count[0]}
                    break
                em.load_state(io.BytesIO(after_move))
                nxt=where()
                if nxt!=pos and nxt not in seen:
                    seen.add(nxt)
                    q.append((nxt,snapshot(em),path+[direction]))
            if found:break
        result.update({"start":start,"visited":len(seen),"found":found is not None,"cpu_hook_details":details})
        if found:
            result.update({"status":"PASS_CONTROLLER_ACTIVATE_PC_FOUND","interaction":found})
        else:result["status"]="PC_INTERACTION_NOT_FOUND"
    except Exception as error:
        result["error"]=repr(error)
        raise
    finally:
        out.write_text(json.dumps(result,indent=2)+"\n")
        em.stop(save=False)
if __name__=="__main__":main()
