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
from PIL import Image
from pyboy import PyBoy
from yel_dev_lab_verify import (
    parse_sym, mem8, mem_bytes, tick, tap, screenshot, save_state_bytes,
    load_state_bytes, enter_debug_menu, choose_debug_new_game,
    move_one_step, DIRECTIONS,
)

FOREST = 0x33
TARGET_CLASS = 2   # BUG_CATCHER
TARGET_PARTY = 1
TARGET_YX = (33, 30)  # trainer tile (y=33, x=30), facing LEFT, range 4
SIGHT_TILES = {(33,x) for x in range(26,30)}
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
        if m == FOREST and (y,x) in SIGHT_TILES:
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
        result["approach_map_y_x"]=[mem8(emu,symbols[k]) for k in ("wCurMap","wYCoord","wXCoord")]
        (out/"controller_inputs.json").write_text(json.dumps(path,indent=2)+"\n")
        (out/"navigation_trace.json").write_text(json.dumps(trace,indent=2)+"\n")
        screenshot(emu,out/"forest_approach.png")
        # Battle activation must occur through controller movement, not WRAM writes.
        # We have navigated onto the four-tile LEFT sight line, not merely
        # within Manhattan distance of the trainer's south side.
        battle=[]; triggered=False
        # The DEBUG warp places us at (y=33,x=29), immediately left of
        # Bug Catcher #1 at (33,30). A warp arrival does not necessarily run
        # trainer line-of-sight logic; talk to the adjacent trainer instead.
        pos=(mem8(emu,symbols["wYCoord"]),mem8(emu,symbols["wXCoord"]))
        result["interaction_origin_y_x"]=list(pos)
        if pos==(33,29):
            tap(emu,"right",hold=2,settle=18)
            tap(emu,"a",hold=4,settle=30)
            battle=["right","a"]
            for _ in range(40):
                tick(emu,20)
                if (mem8(emu,symbols["wTrainerClass"])==TARGET_CLASS
                    and mem8(emu,symbols["wTrainerGenderVariant"])==1):
                    triggered=True
                    break
                tap(emu,"a",hold=3,settle=15)
                battle.append("a")
        tick(emu,120)
        if mem8(emu,symbols["wTrainerClass"])==TARGET_CLASS and mem8(emu,symbols["wTrainerGenderVariant"])==1:
            triggered=True
        for direction in DIRECTIONS:
            if triggered:break
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
        # Two original Bug Catcher #1 party members must be the same species.
        if result["enemy_species_bytes"][0] != result["enemy_species_bytes"][1]:
            raise AssertionError("Bug Catcher #1 party did not load two identical Caterpie")
        result["portrait_pointer"]=list(mem_bytes(emu,symbols["wTrainerPicPointer"],2))
        # A trainer pointer can be correct while the LCD is still black.
        # Require an actual nonblank battle frame before claiming graphics pass.
        frames=[]
        for frame in range(1500):
            emu.tick(1)
            if frame % 15: continue
            frame_img=emu.screen.image.convert("L")
            colors=len(set(frame_img.getdata()))
            if colors >= 3:
                frames.append((frame,colors,frame_img.copy()))
        if not frames:
            screenshot(emu,out/"battle_still_black.png")
            raise AssertionError("Trainer data loaded but no nonblank battle screenshot appeared")
        selected=max(frames,key=lambda item:item[1])
        selected[2].convert("RGB").save(out/"bug_catcher_f_battle.png")
        result["screenshot_frame_after_trigger"]=selected[0]
        result["screenshot_unique_colors"]=selected[1]
        if result["enemy_party_count"]!=2:
            raise AssertionError("Expected two Caterpie in original Bug Catcher #1 party")
        if result["enemy_species_bytes"][:2] != [0x7B, 0x7B]:
            raise AssertionError("Expected exact original party species CATERPIE ($7B) twice")
        level_symbols = ["wEnemyMon1Level", "wEnemyMon2Level"]
        missing_levels = [name for name in level_symbols if name not in symbols]
        if missing_levels:
            raise AssertionError(f"Cannot assert individual party levels; missing {missing_levels}")
        result["enemy_party_levels"] = [mem8(emu, symbols[k]) for k in level_symbols]
        if result["enemy_party_levels"] != [7, 7]:
            raise AssertionError("Expected two level-7 Caterpie in the original Bug Catcher #1 party")
        portrait=symbols["BugCatcherPic"]
        actual=int.from_bytes(bytes(result["portrait_pointer"]),"little")
        if actual!=portrait:
            raise AssertionError(f"Wrong portrait pointer: {actual:#06x} != {portrait:#06x}")
        result["portrait_symbol_address"]=portrait
        result["screenshot_sha256"]=hashlib.sha256((out/"bug_catcher_f_battle.png").read_bytes()).hexdigest()
        # Match a 56x56 battle portrait against the unmodified original PNG
        # across the actual screen. Reject uniform/blank or wrong sprite data.
        reference=Image.open("gfx/trainers/bugcatcher.png").convert("L")
        if reference.size!=(56,56):
            raise AssertionError(f"Unexpected reference trainer portrait size {reference.size}")
        # Compare categorical grayscale pixel ranks, independently of DMG palette.
        ref_colors=sorted(set(reference.getdata()))
        if len(ref_colors)<2:
            raise AssertionError("Reference sprite has no visual detail")
        ref_pixels=list(reference.getdata())
        ref_rank={c:i for i,c in enumerate(ref_colors)}
        expected=[ref_rank[c] for c in ref_pixels]
        from collections import Counter
        best={"matched":-1,"x":None,"y":None}
        screen=selected[2]
        # Trainer battle sprite appears in the upper half of the LCD.
        for y in range(0,73,4):
            for x in range(0,105,4):
                crop=screen.crop((x,y,x+56,y+56))
                colors=sorted(set(crop.getdata()))
                if len(colors)!=len(ref_colors):continue
                rank={c:i for i,c in enumerate(colors)}
                observed=[rank[c] for c in crop.getdata()]
                matched=sum(a==b for a,b in zip(expected,observed))
                if matched>best["matched"]:best={"matched":matched,"x":x,"y":y}
        result["portrait_pixel_match"]=best
        # The sprite might be transposed in the LCD by a few pixels; require
        # a high exact-match fraction after permitted palette normalization.
        if best["matched"] < 2800:
            raise AssertionError(f"Original Bug Catcher sprite pixels not verified: {best}")
        result["status"]="BATTLE_VISUAL_PASS"
    except Exception as e:
        result["error"]=f"{type(e).__name__}: {e}"
        raise
    finally:
        if emu: emu.stop(save=False)
        (out/"report.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__=="__main__":main()
