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
        "wPalletTownCurScript","wPlayerMovingDirection","wStatusFlags5")

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
    joy_names={"hJoyPressed","hJoyHeld","hJoy5","hJoy7","hDisableJoypadPolling","hJoyInput","hJoyLast"}
    joy={}
    for line in args.symbols.read_text().splitlines():
        words=line.split(";")[0].split()
        if len(words)>1 and words[1] in joy_names and ":" in words[0]:
            addr=int(words[0].split(":",1)[1],16)
            if 0xFF80<=addr<=0xFFFE:joy[words[1]]=addr
    def joy_state():
        return {label:int(p.memory[address]) for label,address in joy.items()}
    p=PyBoy(str(args.rom),window="null")
    tracked_labels={"JoypadOverworld","ReadJoypad_","_Joypad","PrepareOAMData",
                    "SpecialEnterMap","CheckForceBikeOrSurf","EnterMap"}
    counters={key:0 for key in tracked_labels}
    poll_samples=[]
    tracing=[False]
    for line in args.symbols.read_text().splitlines():
        parts=line.split(";")[0].split()
        if len(parts)<2 or parts[1] not in tracked_labels or ":" not in parts[0]:
            continue
        bank,addr=(int(v,16) for v in parts[0].split(":",1))
        name=parts[1]
        def seen(_ctx,name=name):
            counters[name]+=1
            if tracing[0] and name in ("ReadJoypad_","_Joypad","JoypadOverworld") and len(poll_samples)<120:
                poll_samples.append({"name":name,"rJOYP":int(p.memory[0xff00]),"pc":int(p.register_file.PC)})
        p.hook_register(bank,addr,seen,None)
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
        # Recreate from power-on using the verified full controller trace.
        # PyBoy restore may retain an inactive JOYP device state even though
        # the in-game WRAM/screenshot appears correct. Do not patch WRAM.
        original_trace=json.loads(args.initial_trace.read_text())
        for instruction in original_trace:
            if "button" in instruction:p.button(instruction["button"])
            if "release" in instruction:p.button_release(instruction["release"])
            tick(instruction["frames"])
        first=get()
        if first["wPartyCount"]!=5 or first["wIsInBattle"]:
            raise AssertionError("Not verified five-Pokémon overworld state")
        p.screen.image.save(args.output/"overworld_start.png")
        original_trace=json.loads(args.initial_trace.read_text())
        # Observe every emulator frame while an input is held, not merely
        # the final frame. Game Boy joypad data is transient and may be
        # cleared before a once-per-press snapshot.
        frame_samples=[]
        p.button("up")
        for frame in range(120):
            p.tick()
            frame_samples.append({"frame":frame,"joy":joy_state(),
                                  "map":int(p.memory[w["wCurMap"]]),
                                  "x":int(p.memory[w["wXCoord"]]),
                                  "y":int(p.memory[w["wYCoord"]])})
        p.button_release("up")
        for _ in range(10):p.tick()
        (args.output/"overworld_held_input_frames.json").write_text(
            json.dumps(frame_samples,indent=2)+"\\n")
        # Diagnose whether an action changes the real overworld position
        # before launching graph traversal.
        origin=snapshot()
        trials=[]
        tracing[0]=True
        for direction in ("up","right","left","down","start","b","a"):
            for hold in ((24,72,180) if direction in ("up","right","left","down") else (24,)):
                if not (direction=="up" and hold==24):
                    restore(origin)
                p.button(direction);tick(hold)
                during={"wram":get(),"joy":joy_state()}
                p.button_release(direction);tick(30)
                trial={"button":direction,"frames":hold,"during":during,"after":get(),
                       "pc":int(p.register_file.PC), "sp":int(p.register_file.SP),
                       "registers":{key:int(getattr(p.register_file,key)) for key in ("A","B","C","D","E","HL")}}
                trials.append(trial)
                if hold==180 or direction in ("start","b","a"):p.screen.image.save(args.output/f"move_{direction}.png")
        # Independently run a continuous controller route without ever
        # loading a savestate; this distinguishes replay from restore bugs.
        fresh=PyBoy(str(args.rom),window="null")
        try:
            for instruction in original_trace:
                if "button" in instruction:fresh.button(instruction["button"])
                if "release" in instruction:fresh.button_release(instruction["release"])
                for _ in range(instruction["frames"]):fresh.tick()
            continuous=[]
            for count in range(18):
                fresh.button("up")
                for _ in range(60):fresh.tick()
                fresh.button_release("up")
                for _ in range(20):fresh.tick()
                continuous.append({"attempt":count,"map":int(fresh.memory[w["wCurMap"]]),
                    "x":int(fresh.memory[w["wXCoord"]]),"y":int(fresh.memory[w["wYCoord"]]),
                    "held":int(fresh.memory[joy["hJoyHeld"]]) if "hJoyHeld" in joy else -1})
            (args.output/"continuous_route.json").write_text(json.dumps(continuous,indent=2)+"\\n")
        finally:fresh.stop()
        (args.output/"movement_trials.json").write_text(json.dumps(trials,indent=2)+"\n")
        (args.output/"input_routine_call_counts.json").write_text(json.dumps(counters,indent=2)+"\n")
        (args.output/"poll_samples.json").write_text(json.dumps(poll_samples,indent=2)+"\n")
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
