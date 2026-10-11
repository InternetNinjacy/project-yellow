#!/usr/bin/env python3
"""Controller-only Route 1 wild encounter from verified Pallet -> Route 1 state.

All tests read emulator memory. Traversal uses only held controller buttons,
genuine PyBoy savestates and real wild encounter logic. No RAM mutation or
direct battle instantiation. Fails closed if no legitimate wild battle occurs.
"""
import argparse
from collections import deque
from pathlib import Path
import io, json, hashlib

FIELDS=("wCurMap","wXCoord","wYCoord","wPartyCount","wIsInBattle",
        "wBattleMonSpecies","wEnemyMonSpecies","wPartyMon5Level",
        "wPartySpecies")
ROUTE_1=12
RATICATE=0xA6

def read_symbols(path):
    symbols={}
    for line in path.read_text().splitlines():
        p=line.split(";")[0].split()
        if len(p)<2 or p[1] not in FIELDS or ":" not in p[0]:continue
        address=int(p[0].split(":",1)[1],16)
        if 0xC000 <= address <= 0xDFFF:symbols[p[1]]=address
    if set(symbols)!=set(FIELDS):
        raise AssertionError("Missing battle symbols "+repr(set(FIELDS)-set(symbols)))
    return symbols

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    ap.add_argument("--symbols",type=Path,required=True)
    ap.add_argument("--starting-state",type=Path,required=True)
    ap.add_argument("--starting-trace",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--max-states",type=int,default=650)
    args=ap.parse_args()
    from pyboy import PyBoy
    symbols=read_symbols(args.symbols)
    pyboy=PyBoy(str(args.rom),window="null")
    args.output.mkdir(parents=True,exist_ok=True)
    def info():
        x={key:int(pyboy.memory[addr]) for key,addr in symbols.items()}
        x["party_fifth_species"]=int(pyboy.memory[symbols["wPartySpecies"]+4])
        return x
    def frames(n):
        for _ in range(n):pyboy.tick()
    def capture():
        f=io.BytesIO();pyboy.save_state(f);return f.getvalue()
    def restore(buf):pyboy.load_state(io.BytesIO(buf))
    def advance(button):
        pyboy.button_press(button);frames(56)
        pyboy.button_release(button);frames(20)
        return [{"button":button,"frames":56},{"release":button,"frames":20}]
    try:
        with args.starting_state.open("rb") as h:pyboy.load_state(h)
        initial=info()
        if initial["wCurMap"]!=ROUTE_1 or initial["wIsInBattle"] or initial["wPartyCount"]!=5:
            raise AssertionError("Not a genuine Route 1 overworld with five party members")
        if initial["party_fifth_species"]!=RATICATE or initial["wPartyMon5Level"]!=35:
            raise AssertionError("Missing level-35 Raticate in fifth party slot")
        base_trace=json.loads(args.starting_trace.read_text())
        q=deque([(capture(),[])])
        visited={(initial["wCurMap"],initial["wXCoord"],initial["wYCoord"])}
        encountered=None
        attempts=[]
        for _ in range(args.max_states):
            if not q:break
            state,path=q.popleft()
            for button in ("up","right","left","down"):
                restore(state)
                steps=advance(button)
                current=info()
                if len(attempts)<400:
                    attempts.append({"direction":button,"map":current["wCurMap"],
                                     "x":current["wXCoord"],"y":current["wYCoord"],
                                     "battle":current["wIsInBattle"]})
                if current["wIsInBattle"]==1 and current["wEnemyMonSpecies"] and current["wCurMap"]==ROUTE_1:
                    encountered=(capture(),path+steps,current)
                    break
                if current["wIsInBattle"] or current["wCurMap"]!=ROUTE_1:
                    continue
                key=(current["wCurMap"],current["wXCoord"],current["wYCoord"])
                if key in visited:continue
                visited.add(key)
                q.append((capture(),path+steps))
            if encountered:break
        result={"initial":initial,"visited_positions":len(visited),"attempts":attempts,
                "encounter":None if encountered is None else encountered[2]}
        (args.output/"route1_encounter_search.json").write_text(json.dumps(result,indent=2)+"\n")
        if encountered is None:
            raise AssertionError("No real Route 1 wild encounter from controller-only traversal")
        state,path,final=encountered
        restore(state)
        pyboy.screen.image.save(args.output/"route1_wild_encounter.png")
        with (args.output/"route1_wild_encounter.state").open("wb") as h:pyboy.save_state(h)
        (args.output/"route1_wild_encounter_trace.json").write_text(
            json.dumps(base_trace+path,indent=2)+"\n")
        (args.output/"route1_wild_encounter_provenance.json").write_text(json.dumps({
            "rom_sha256":hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "controller_steps":len(base_trace+path),
            "map_id":final["wCurMap"],"battle_type":final["wIsInBattle"],
            "enemy_species":final["wEnemyMonSpecies"],
            "raticate_level":initial["wPartyMon5Level"],
        },indent=2)+"\n")
        print("PASS legitimate Route 1 wild battle:",final,flush=True)
    finally:
        pyboy.stop()

if __name__=="__main__":main()
