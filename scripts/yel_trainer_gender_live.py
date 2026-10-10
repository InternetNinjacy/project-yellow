#!/usr/bin/env python3
"""Real-controller DEBUG-to-Viridian-Forest battle probe; no RAM teleport.

Explores by PyBoy savestate replay, recording actual button presses. A failed
route is a test failure, never represented as a verified encounter.
"""
import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from pyboy import PyBoy
from yel_dev_lab_verify import (
    parse_sym, mem8, mem_bytes, tick, tap, screenshot, save_state_bytes,
    load_state_bytes, enter_debug_menu, choose_debug_new_game,
    move_one_step, DIRECTIONS,
)

FOREST = 0x33
TARGET_CLASS = 2   # BUG_CATCHER
TARGET_PARTY = 1
TARGET_YX = (33, 30)  # existing object_event coordinate (x=30,y=33)
MAX_VISITS = 2600


def explore(emu, sym, out):
    map_addr, y_addr, x_addr = (sym[k] for k in ("wCurMap", "wYCoord", "wXCoord"))
    start = (mem8(emu,map_addr), mem8(emu,y_addr), mem8(emu,x_addr))
    states = deque([(start,save_state_bytes(emu),[])])
    seen = {start}
    accepted = {0, 1, 0x0c, 0x0d, 0x25, 0x26, 0x32, FOREST}
    trace = []
    while states and len(seen) < MAX_VISITS:
        (m,y,x), state, path = states.popleft()
        if m == FOREST and abs(y-TARGET_YX[0])+abs(x-TARGET_YX[1]) <= 2:
            load_state_bytes(emu,state)
            return path, trace
        for direction in DIRECTIONS:
            load_state_bytes(emu,state)
            next_m, ny, nx = move_one_step(emu,direction,map_addr,y_addr,x_addr)
            loc = (next_m,ny,nx)
            if next_m not in accepted or loc == (m,y,x) or loc in seen:
                continue
            seen.add(loc)
            new_path = path + [direction]
            trace.append({"from":[m,y,x],"button":direction,"to":list(loc)})
            states.append((loc,save_state_bytes(emu),new_path))
    (out/"navigation_trace.json").write_text(json.dumps(trace,indent=2)+"\n")
    raise AssertionError(f"Controller navigation did not reach the forest fixture; explored {len(seen)} positions")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--rom",default="pokeyellow_debug.gbc")
    ap.add_argument("--sym",default="pokeyellow_debug.sym")
    ap.add_argument("--out",default="test-results/trainer-gender-live")
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    symbols=parse_sym(Path(args.sym))
    required=["wCurMap","wYCoord","wXCoord","wTrainerClass","wTrainerNo",
              "wTrainerGenderVariant","wTrainerName","wTrainerPicPointer",
              "wEnemyPartyCount","wEnemyPartySpecies","wTopMenuItemY",
              "wMaxMenuItem","wCurrentMenuItem"]
    missing=[x for x in required if x not in symbols]
    if missing: raise AssertionError(f"Missing symbols: {missing}")
    result={"status":"INCOMPLETE","rom_sha256":hashlib.sha256(Path(args.rom).read_bytes()).hexdigest()}
    emu=None
    try:
        emu=PyBoy(args.rom,window="null",cgb=False,sound_emulated=False,symbols=args.sym)
        emu.set_emulation_speed(0)
        enter_debug_menu(emu,symbols,out)
        choose_debug_new_game(emu,symbols,out)
        tick(emu,30)
        path, trace=explore(emu,symbols,out)
        result["controller_navigation"]=path
        (out/"controller_inputs.json").write_text(json.dumps(path,indent=2)+"\n")
        (out/"navigation_trace.json").write_text(json.dumps(trace,indent=2)+"\n")
        screenshot(emu,out/"forest_approach.png")
        # Battle activation must occur through controller movement, not WRAM writes.
        battle=[]; triggered=False
        for direction in DIRECTIONS:
            saved=save_state_bytes(emu)
            for _ in range(5):
                tap(emu,direction,hold=5,settle=40)
                tick(emu,80)
                cls=mem8(emu,symbols["wTrainerClass"])
                var=mem8(emu,symbols["wTrainerGenderVariant"])
                if cls==TARGET_CLASS and var==1:
                    triggered=True
                    battle.append(direction)
                    break
            if triggered:break
            load_state_bytes(emu,saved)
        if not triggered:
            screenshot(emu,out/"battle_not_triggered.png")
            raise AssertionError("Natural inputs did not trigger female Bug Catcher battle")
        result["encounter_controller_inputs"]=battle
        if mem8(emu,symbols["wTrainerNo"])!=TARGET_PARTY:
            raise AssertionError("Wrong trainer party number")
        name=mem_bytes(emu,symbols["wTrainerName"],13)
        result["name_raw_hex"]=name.hex()
        # Fetch expected 13-byte name directly from the built ROM's symbol.
        name_bank=int(next(line[:2] for line in Path(args.sym).read_text().splitlines()
                           if line.strip().endswith(" TrainerVariantNames")),16)
        name_addr=symbols["TrainerVariantNames"] + 13  # Bug Catcher is entry 2
        expected_name=bytes(int(emu.memory[name_bank,name_addr+i]) for i in range(13))
        result["expected_name_raw_hex"]=expected_name.hex()
        if name!=expected_name:
            raise AssertionError("Battle name bytes do not match BUG CATCHR female lookup entry")
        # The rendered screenshot is retained, and byte exact name is compared
        # to the encoded table by the game; verify chosen variant and display.
        result["trainer_class"]=mem8(emu,symbols["wTrainerClass"])
        result["variant"]=mem8(emu,symbols["wTrainerGenderVariant"])
        result["trainer_party_no"]=mem8(emu,symbols["wTrainerNo"])
        result["enemy_party_count"]=mem8(emu,symbols["wEnemyPartyCount"])
        result["enemy_species_bytes"]=list(mem_bytes(emu,symbols["wEnemyPartySpecies"],3))
        result["portrait_pointer"]=list(mem_bytes(emu,symbols["wTrainerPicPointer"],2))
        screenshot(emu,out/"bug_catcher_f_battle.png")
        if result["enemy_party_count"]!=2:
            raise AssertionError("Expected two Caterpie in original Bug Catcher #1 party")
        portrait=symbols["BugCatcherPic"]
        actual=int.from_bytes(bytes(result["portrait_pointer"]),"little")
        if actual!=portrait:
            raise AssertionError(f"Wrong portrait pointer: {actual:#06x} != {portrait:#06x}")
        result["portrait_symbol_address"]=portrait
        result["screenshot_sha256"]=hashlib.sha256((out/"bug_catcher_f_battle.png").read_bytes()).hexdigest()
        result["status"]="BATTLE_WRAM_AND_PORTRAIT_POINTER_PASS"
        # A separate graphics-level comparison is needed to prove rendered tiles.
    except Exception as e:
        result["error"]=f"{type(e).__name__}: {e}"
        raise
    finally:
        if emu: emu.stop(save=False)
        (out/"report.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":main()
