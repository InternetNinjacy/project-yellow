#!/usr/bin/env python3
"""Inspect controller-only Raticate switch into a real Route 1 wild battle.

Diagnostic gate, not success claim: records battle-menu screenshots and WRAM,
and requires Raticate to become active without emulator memory mutation.
"""
import argparse, hashlib, json
from pathlib import Path

KEYS=("wIsInBattle","wCurMap","wPartyCount","wPartySpecies",
      "wBattleMonSpecies","wBattleMonLevel","wEnemyMonSpecies",
      "wPartyMon5Level","wPartyMon5Exp","wPartyMon5Moves",
      "wEnemyMonHP","wPlayerSelectedMove","wCurrentMenuItem","wMenuJoypadPollCount")
RATICATE=0xA6

def parse(path):
    out={}
    for line in path.read_text().splitlines():
        a=line.split(";")[0].split()
        if len(a)<2 or a[1] not in KEYS or ":" not in a[0]:continue
        addr=int(a[0].split(":",1)[1],16)
        if 0xC000<=addr<=0xDFFF:out[a[1]]=addr
    required=set(KEYS)-{"wCurrentMenuItem","wMenuJoypadPollCount"}
    if not required.issubset(out):raise AssertionError("Missing WRAM symbols "+repr(required-set(out)))
    return out

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--rom",required=True,type=Path)
    pa.add_argument("--symbols",required=True,type=Path)
    pa.add_argument("--initial-state",required=True,type=Path)
    pa.add_argument("--initial-trace",required=True,type=Path)
    pa.add_argument("--output",required=True,type=Path)
    args=pa.parse_args()
    from pyboy import PyBoy
    w=parse(args.symbols)
    args.output.mkdir(parents=True,exist_ok=True)
    pb=PyBoy(str(args.rom),window="null")
    trace=json.loads(args.initial_trace.read_text())
    observations=[]
    def frames(n):
        for _ in range(n):pb.tick()
    def sample(label):
        r={"label":label}
        for name,addr in w.items():r[name]=int(pb.memory[addr])
        r["fifth_species"]=int(pb.memory[w["wPartySpecies"]+4])
        r["fifth_moves"]=[int(pb.memory[w["wPartyMon5Moves"]+i]) for i in range(4)]
        r["fifth_exp"]=[int(pb.memory[w["wPartyMon5Exp"]+i]) for i in range(3)]
        observations.append(r)
        pb.screen.image.save(args.output/(label+".png"))
        with (args.output/(label+".state")).open("wb") as h:pb.save_state(h)
    def preserve_diagnostics():
        (args.output/"evolution_battle_diagnostics.json").write_text(json.dumps({
            "rom_sha256":hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "observations":observations,
            "steps":len(trace)
        },indent=2)+"\\n")
        (args.output/"evolution_battle_trace.json").write_text(json.dumps(trace,indent=2)+"\\n")
    def press(button,settle=120):
        pb.button_press(button)
        trace.append({"button":button,"frames":2})
        frames(2)
        pb.button_release(button)
        trace.append({"release":button,"frames":settle})
        frames(settle)
    try:
        with args.initial_state.open("rb") as h:pb.load_state(h)
        sample("battle_entering")
        if observations[-1]["wCurMap"]!=12 or observations[-1]["wIsInBattle"]!=1 or observations[-1]["fifth_species"]!=RATICATE:
            raise AssertionError("Not verified Route1 wild battle with party Raticate")
        # Diagnostic: advance opening text progressively, capturing each menu.
        for i in range(5):
            press("a",150)
            sample("opening_a"+str(i))
        press("right",70)
        sample("battle_command_right")
        press("a",140)
        sample("battle_command_confirm")
        for i in range(4):
            press("down",65)
            sample("party_down"+str(i+1))
        press("a",160)
        sample("party_select_fifth")
        press("a",160)
        sample("party_switch_confirm")
        if observations[-1]["wBattleMonSpecies"]!=RATICATE:
            raise AssertionError("Real wild battle did not switch to Raticate")
        # Continue only with genuine button A presses. Raticate should use
        # its first (Rage) move to defeat the low-level Route 1 encounter,
        # earn the remaining EXP and evolve through the normal animation.
        for index in range(32):
            press("a",160)
            sample("post_switch_a"+str(index))
            if observations[-1]["fifth_species"]==0xBF and observations[-1]["wPartyMon5Level"]==36:
                break
        (args.output/"evolution_battle_diagnostics.json").write_text(json.dumps({
            "rom_sha256":hashlib.sha256(args.rom.read_bytes()).hexdigest(),
            "observations":observations,
            "steps":len(trace)
        },indent=2)+"\n")
        (args.output/"evolution_battle_trace.json").write_text(json.dumps(trace,indent=2)+"\n")
        if not any(x["wBattleMonSpecies"]==RATICATE for x in observations):
            raise AssertionError("Raticate not switched into actual battle")
        if observations[-1]["fifth_species"]!=0xBF or observations[-1]["wPartyMon5Level"]!=36:
            raise AssertionError("Raticate has not evolved into level-36 Rattaking; inspect post-switch screenshots")
        with (args.output/"rattaking_evolved.state").open("wb") as h:pb.save_state(h)
        print("PASS genuine battle EXP and evolution into level-36 Rattaking",flush=True)
    finally:
        preserve_diagnostics()
        pb.stop()

if __name__=="__main__":main()
