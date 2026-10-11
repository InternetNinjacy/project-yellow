#!/usr/bin/env python3
"""Controller-only route discovery from the verified DEBUG overworld save.

Uses PyBoy savestate rewind for searching possible *controller traces*, never
memory writes or direct RNG/party manipulation. Fails closed without a real
map transition and saves visual, WRAM and controller-input evidence.
"""
import argparse
from collections import deque
import io
import json
from pathlib import Path

FIELDS=("wCurMap","wXCoord","wYCoord","wPartyCount","wIsInBattle",
        "wBattleMonSpecies","wEnemyMonSpecies","wJoyIgnore",
        "wWalkCounter","wMovementFlags","wCurrentMapScriptFlags",
        "wPalletTownCurScript","wPlayerMovingDirection")

def labels(path):
    out={}
    for ln in path.read_text().splitlines():
        p=ln.split(";")[0].split()
        if len(p)>1 and p[1] in FIELDS and ":" in p[0]:
            address=int(p[0].split(":")[1],16)
            if 0xC000 <= address <= 0xDFFF:
                out[p[1]]=address
    if set(out)!=set(FIELDS):
        raise AssertionError("Missing WRAM labels "+repr(set(FIELDS)-set(out)))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",type=Path,required=True)
    ap.add_argument("--symbols",type=Path,required=True)
    ap.add_argument("--initial-state",type=Path,required=True)
    ap.add_argument("--initial-trace",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--max-states",type=int,default=450)
    args=ap.parse_args()
    from pyboy import PyBoy
    w=labels(args.symbols)
    p=PyBoy(str(args.rom),window="null")
    args.output.mkdir(parents=True,exist_ok=True)
    records=[]
    def get():
        return {key:int(p.memory[value]) for key,value in w.items()}
    def tick(n):
        for _ in range(n):p.tick()
    def snapshot():
        fh=io.BytesIO();p.save_state(fh);return fh.getvalue()
    def restore(data):
        p.load_state(io.BytesIO(data))
    def step(button):
        p.button(button);tick(72);p.button_release(button);tick(24)
        return [{"button":button,"frames":72},{"release":button,"frames":24}]
    try:
        with args.initial_state.open("rb") as fh:p.load_state(fh)
        first=get()
        if first["wPartyCount"]!=5 or first["wIsInBattle"]:
            raise AssertionError("Not verified five-Pokémon overworld state")
        p.screen.image.save(args.output/"overworld_start.png")
        original_trace=json.loads(args.initial_trace.read_text())
        # Diagnose whether an action changes the real overworld position
        # before launching graph traversal.
        origin=snapshot()
        trials=[]
        for direction in ("up","right","left","down","start","b","a"):
            for hold in ((24,72,180) if direction in ("up","right","left","down") else (24,)):
                restore(origin)
                p.button(direction);tick(hold);p.button_release(direction);tick(30)
                trial={"button":direction,"frames":hold,"after":get()}
                trials.append(trial)
                if hold==180 or direction in ("start","b","a"):p.screen.image.save(args.output/f"move_{direction}.png")
        (args.output/"movement_trials.json").write_text(json.dumps(trials,indent=2)+"\n")
        q=deque([(origin,[])])
        seen={(first["wCurMap"],first["wXCoord"],first["wYCoord"])}
        found=None
        for _ in range(args.max_states):
            if not q:break
            state,inputs=q.popleft()
            restore(state)
            before=get()
            if before["wCurMap"]!=first["wCurMap"]:
                found=(state,inputs,before)
                break
            for button in ("up","right","left","down"):
                restore(state)
                added=step(button)
                after=get()
                key=(after["wCurMap"],after["wXCoord"],after["wYCoord"])
                if after["wIsInBattle"]:
                    found=(snapshot(),inputs+added,after)
                    break
                if key in seen:continue
                seen.add(key)
                if len(records)<300:
                    records.append({"button":button,"x":after["wXCoord"],"y":after["wYCoord"],"map":after["wCurMap"]})
                q.append((snapshot(),inputs+added))
            if found:break
        (args.output/"route_search.json").write_text(json.dumps({
            "initial":first,"seen_positions":len(seen),"steps":records,
            "found":None if found is None else found[2]
        },indent=2)+"\n")
        if found:
            state,inputs,last=found
            restore(state)
            p.screen.image.save(args.output/"overworld_route_found.png")
            with (args.output/"overworld_route_found.state").open("wb") as h:p.save_state(h)
            (args.output/"overworld_route_trace.json").write_text(json.dumps(original_trace+inputs,indent=2)+"\n")
        if not found:
            raise AssertionError("Controller search did not reach another map or a battle; see route_search.json")
        print("Real controller-only overworld route discovered:",first,last)
    finally:p.stop()

if __name__=="__main__":main()
