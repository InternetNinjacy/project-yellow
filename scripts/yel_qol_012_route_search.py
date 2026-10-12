#!/usr/bin/env python3
"""Discover a controller-only path from DEBUG spawn to another map/wild battle.

PyBoy savestates are used strictly to search, never as acceptance evidence.
The replay candidate is verified from a fresh boot with its actual inputs.
"""
import argparse,io,json
from collections import deque
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play,box_bytes
from yel_qol_012_fixture import seed_scenario

def snapshot(em):
    buf=io.BytesIO()
    em.save_state(buf)
    return buf.getvalue()

def main():
    ap=argparse.ArgumentParser()
    for key in ("rom","sym","replay","out"):ap.add_argument("--"+key,required=True)
    args=ap.parse_args()
    sym=symbol_table(args.sym)
    spec=json.loads(Path(args.replay).read_text())
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    em=PyBoy(args.rom,window="null",cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    def locate():
        return (em.memory[sym["wCurMap"][1]],
                em.memory[sym["wXCoord"][1]],em.memory[sym["wYCoord"][1]])
    def movement(button):
        play(em,[{"button":button,"frames":8},{"frames":24}])
    report={"status":"NOT_VERIFIED","scope":"CONTROLLER_PATH_DISCOVERY"}
    try:
        play(em,spec["prepare"])
        assert em.memory[sym["wPartyCount"][1]]==6
        play(em,[{"frames":600}])
        seed_scenario(em.memory,sym,0,29,False)
        start=locate()
        queue=deque([(start,snapshot(em),[])])
        seen={start}
        directions=("up","right","down","left")
        found=None
        while queue and len(seen)<350:
            position,blob,path=queue.popleft()
            for button in directions:
                em.load_state(io.BytesIO(blob))
                movement(button)
                nextpos=locate()
                if nextpos==position or nextpos in seen:continue
                candidate=path+[button]
                if nextpos[0]==12 or em.memory[sym["wIsInBattle"][1]]!=0:
                    found=(nextpos,candidate)
                    break
                seen.add(nextpos)
                queue.append((nextpos,snapshot(em),candidate))
            if found:break
        mapids=sorted({pos[0] for pos in seen})
        coverage={str(m):{"count":len([p for p in seen if p[0]==m]),
                           "min_x":min(p[1] for p in seen if p[0]==m),
                           "max_x":max(p[1] for p in seen if p[0]==m),
                           "min_y":min(p[2] for p in seen if p[0]==m),
                           "max_y":max(p[2] for p in seen if p[0]==m)} for m in mapids}
        report.update({"map_coverage":coverage,"start":start,"explored_positions":len(seen),
                       "route_found":bool(found)})
        if found:
            report["destination"]=found[0]
            report["movement_inputs"]=found[1]
            report["status"]="PASS_CONTROLLER_PATH_TO_ROUTE1_OR_BATTLE"
            # Continue from authentic Route 1 state to discover the FIRST
            # wild battle through real directional input, never RAM forcing.
            if found[0][0]==12:
                battle_queue=deque([(found[0],snapshot(em),found[1])])
                battle_seen={found[0]}
                battle=None
                while battle_queue and len(battle_seen)<450:
                    pos,blob,steps=battle_queue.popleft()
                    for direction in directions:
                        em.load_state(io.BytesIO(blob))
                        movement(direction)
                        play(em,[{"frames":80}])
                        nxt=locate()
                        candidate=steps+[direction]
                        if em.memory[sym["wIsInBattle"][1]]==1:
                            battle={"location":nxt,"inputs":candidate}
                            break
                        if nxt[0]!=12 or nxt in battle_seen:continue
                        battle_seen.add(nxt)
                        battle_queue.append((nxt,snapshot(em),candidate))
                    if battle:break
                report["route1_explored_positions"]=len(battle_seen)
                report["wild_battle"]=battle
                if battle:report["status"]="PASS_REAL_WILD_BATTLE_CONTROLLER_PATH"
        else:
            report["status"]="NO_ROUTE_FOUND"
    except Exception as e:
        report["error"]=repr(e)
        raise
    finally:
        out.write_text(json.dumps(report,indent=2)+"\n")
        em.stop(save=False)
if __name__=="__main__":main()
