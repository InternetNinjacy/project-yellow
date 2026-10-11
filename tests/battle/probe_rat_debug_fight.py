#!/usr/bin/env python3
"""Controller-only DEBUG Fight menu route: Rattaking versus Rhydon.

Outputs a real live-battle state only after validating active battle + species.
No emulator RAM mutation. The fight menu is accessible by SELECT at title.
"""
import argparse, hashlib, json
from pathlib import Path

LABELS = ("wIsInBattle", "wBattleMonSpecies", "wEnemyMonSpecies",
          "wPartyCount", "wCurMap", "wPlayerMoveNum", "wEnemyMonStatus",
          "wEnemyBattleStatus3", "wEnemyMonStatMods", "wPartySpecies", "wBattleMonMoves")

def resolve(path):
    found = {}
    for line in path.read_text().splitlines():
        p = line.split(";")[0].split()
        if len(p) >= 2 and ":" in p[0] and p[1] in LABELS:
            addr = int(p[0].split(":")[1], 16)
            if not 0xC000 <= addr <= 0xDFFF:
                raise AssertionError(p[1] + " is not in WRAM")
            found[p[1]] = addr
    if set(found) != set(LABELS):
        raise AssertionError("Missing symbols: " + str(set(LABELS)-set(found)))
    return found

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--rom", required=True, type=Path)
    p.add_argument("--symbols", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    from pyboy import PyBoy
    symbols = resolve(a.symbols)
    pyboy = PyBoy(str(a.rom), window="null")
    total = 0
    trace, checkpoints = [], []
    def tick(n):
        nonlocal total
        for _ in range(n):
            pyboy.tick()
            total += 1
    def check(name):
        rec = {"name":name,"frame":total}
        for label,addr in symbols.items():
            rec[label] = int(pyboy.memory[addr])
        rec["battle_moves"] = [int(pyboy.memory[symbols["wBattleMonMoves"] + i]) for i in range(4)]
        checkpoints.append(rec)
        try:
            a.output.mkdir(parents=True, exist_ok=True)
            pyboy.screen.image.save(a.output / (name + ".png"))
        except Exception as exc:
            rec["screen_capture_error"] = repr(exc)
    def press(button, settle=32):
        pyboy.button(button)
        trace.append({"button":button,"frames":2})
        tick(2)
        pyboy.button_release(button)
        trace.append({"release":button,"frames":settle})
        tick(settle)
    try:
        tick(2200)
        trace.append({"frames":2200})
        check("title")
        # SELECT from title enters DEBUG menu; A enters FIGHT menu.
        # Hold SELECT through title startup rather than tapping before it is ready.
        # DEBUG title handler recognizes held SELECT and enters DebugMenu.
        pyboy.button("select")
        trace.append({"button":"select","frames":1200})
        tick(1200)
        pyboy.button_release("select")
        trace.append({"release":"select","frames":80})
        tick(80)
        check("debug_menu")
        press("a", 350)
        check("fight_menu")
        # First player slot, species zero -> decrement wraps to last index
        # (Rattaking $BF on this branch).
        press("b", 50)
        press("right", 50)
        # Level 50 from zero
        for _ in range(50):
            press("a", 24)
        check("player_selected")
        press("start", 350)  # add Rattaking to DEBUG party
        press("b", 350)      # decline AddPartyMon nickname prompt
        check("enemy_type")
        press("down", 50)    # enemy species row
        press("a", 50)       # species 1 = Rhydon
        press("right", 50)   # enemy level field
        for _ in range(45):
            press("a", 24)
        check("enemy_selected")
        press("start", 600)  # enter actual battle
        for _ in range(25):
            if pyboy.memory[symbols["wIsInBattle"]] and pyboy.memory[symbols["wBattleMonSpecies"]] and pyboy.memory[symbols["wEnemyMonSpecies"]]:
                break
            press("a", 100)
        check("battle_candidate")
        out = a.output
        out.mkdir(parents=True, exist_ok=True)
        (out/"debug_fight_trace.json").write_text(json.dumps(trace,indent=2)+"\n")
        (out/"debug_fight_checkpoints.json").write_text(json.dumps({
            "rom_sha256":hashlib.sha256(a.rom.read_bytes()).hexdigest(),
            "checkpoints":checkpoints,
        },indent=2)+"\n")
        with (out/"debug_fight_final.state").open("wb") as f:
            pyboy.save_state(f)
        status=checkpoints[-1]
        if not status["wIsInBattle"] or not status["wBattleMonSpecies"] or not status["wEnemyMonSpecies"]:
            raise AssertionError("Not a live battle. Inspect uploaded checkpoints and controller trace.")
        if status["wBattleMonSpecies"] != 0xBF:
            raise AssertionError("Live battle player species is not Rattaking $BF")
        print("Real DEBUG Fight menu battle reached using controller inputs only")
    finally:
        pyboy.stop()

if __name__=="__main__":
    main()
