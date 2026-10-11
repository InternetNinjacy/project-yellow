#!/usr/bin/env python3
"""Discover controller-only path to Red's room/PC from verified DEBUG boot."""
import argparse,io,json
from pathlib import Path
from collections import deque
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play

def snap(em):
    b=io.BytesIO();em.save_state(b);return b.getvalue()
def main():
    p=argparse.ArgumentParser()
    for field in ("rom","sym","boot","out"):p.add_argument("--"+field,required=True)
    a=p.parse_args()
    syms=symbol_table(a.sym)
    spec=json.loads(Path(a.boot).read_text())
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    em=PyBoy(a.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    def loc():
        return tuple(em.memory[syms[k][1]] for k in ("wCurMap","wXCoord","wYCoord"))
    def move(button):
        play(em,[{"button":button,"frames":8},{"frames":24}])
    report={"status":"NOT_VERIFIED","target":"REDS_HOUSE_2F","map_id":38}
    try:
        play(em,spec["prepare"])
        assert em.memory[syms["wPartyCount"][1]]==6
        play(em,[{"frames":600}])
        start=loc()
        todo=deque([(start,snap(em),[])])
        seen={start};found=None
        while todo and len(seen)<450:
            position,state,path=todo.popleft()
            for direction in ("up","right","down","left"):
                em.load_state(io.BytesIO(state))
                move(direction)
                nxt=loc()
                if nxt==position or nxt in seen:continue
                if nxt[0] not in (0,37,38):continue
                candidate=path+[direction]
                if nxt[0]==38:
                    found=(nxt,candidate)
                    break
                seen.add(nxt)
                todo.append((nxt,snap(em),candidate))
            if found:break
        report.update({"start":start,"explored":len(seen),
                       "maps":sorted(set(p[0] for p in seen)),"found":bool(found)})
        if found:
            report.update({"status":"PASS_CONTROLLER_PATH_TO_REDS_ROOM",
                           "destination":found[0],"inputs":found[1]})
        else:report["status"]="NO_PATH_FOUND"
    except Exception as e:
        report["error"]=repr(e)
        raise
    finally:
        out.write_text(json.dumps(report,indent=2)+"\n")
        em.stop(save=False)
if __name__=="__main__":main()
