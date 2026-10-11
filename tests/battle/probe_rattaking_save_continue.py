#!/usr/bin/env python3
"""Real controller-only Rattaking SAVE/CONTINUE persistence regression.

Uses a fresh copy of the ROM as a separate battery-SRAM namespace; loads
only a legitimate controller-derived post-evolution PyBoy savestate. SAVE
and CONTINUE must both be performed using the actual game menus, never RAM
patches. Tests party record, Pokedex, box view and battery SRAM integrity.
"""
import argparse, hashlib, json, shutil
from pathlib import Path

RATTAKING=0xBF
ROUTE_1=12
NAMES=("wPartyCount","wPartySpecies","wPartyMon5","wPartyMon6",
       "wPartyMon5Species","wPartyMon5Level","wPartyMon5Exp",
       "wPartyMon5Moves","wPartyMon5Attack","wPartyMon5Defense",
       "wPartyMon5Speed","wPartyMon5Special","wPartyMon5MaxHP",
       "wPartyMon5OT","wPartyMon5Nick","wPokedexOwned",
       "wPokedexOwnedEnd","wPokedexSeen","wPokedexSeenEnd",
       "wCurMap","wIsInBattle","wCurrentBoxNum","wBoxDataStart",
       "wBoxDataEnd","wBoxMonCounts")

def parse(path):
    d={}
    for line in path.read_text().splitlines():
        p=line.split(";")[0].split()
        if len(p)<2 or p[1] not in NAMES or ":" not in p[0]:continue
        addr=int(p[0].split(":",1)[1],16)
        if 0xC000<=addr<=0xDFFF:d[p[1]]=addr
    if set(d)!=set(NAMES):raise AssertionError("Missing WRAM symbols "+repr(set(NAMES)-set(d)))
    return d

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--rom",required=True,type=Path)
    p.add_argument("--symbols",required=True,type=Path)
    p.add_argument("--evolved-state",required=True,type=Path)
    p.add_argument("--evolved-trace",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    from pyboy import PyBoy
    sym=parse(args.symbols)
    temp_rom=args.output/"rattaking_persistence_cartridge.gbc"
    shutil.copyfile(args.rom,temp_rom)
    assert sha(args.rom.read_bytes())==sha(temp_rom.read_bytes())
    ram_path=temp_rom.with_suffix(".ram")
    if ram_path.exists():ram_path.unlink()
    def from_mem(pb,key,n=1):
        addr=sym[key]
        return bytes(int(pb.memory[addr+i]) for i in range(n))
    def snapshot(pb):
        party_mon=from_mem(pb,"wPartyMon5",sym["wPartyMon6"]-sym["wPartyMon5"])
        box=from_mem(pb,"wBoxDataStart",sym["wBoxDataEnd"]-sym["wBoxDataStart"])
        owned=from_mem(pb,"wPokedexOwned",sym["wPokedexOwnedEnd"]-sym["wPokedexOwned"])
        seen=from_mem(pb,"wPokedexSeen",sym["wPokedexSeenEnd"]-sym["wPokedexSeen"])
        return {
            "map":int(pb.memory[sym["wCurMap"]]),
            "battle":int(pb.memory[sym["wIsInBattle"]]),
            "party_count":int(pb.memory[sym["wPartyCount"]]),
            "party_species":from_mem(pb,"wPartySpecies",6).hex(),
            "species":int(pb.memory[sym["wPartyMon5Species"]]),
            "level":int(pb.memory[sym["wPartyMon5Level"]]),
            "exp":int.from_bytes(from_mem(pb,"wPartyMon5Exp",3),"big"),
            "moves":list(from_mem(pb,"wPartyMon5Moves",4)),
            "attack":int.from_bytes(from_mem(pb,"wPartyMon5Attack",2),"big"),
            "defense":int.from_bytes(from_mem(pb,"wPartyMon5Defense",2),"big"),
            "speed":int.from_bytes(from_mem(pb,"wPartyMon5Speed",2),"big"),
            "special":int.from_bytes(from_mem(pb,"wPartyMon5Special",2),"big"),
            "maxhp":int.from_bytes(from_mem(pb,"wPartyMon5MaxHP",2),"big"),
            "party_mon_bytes":party_mon.hex(),
            "party_mon_ot":from_mem(pb,"wPartyMon5OT",11).hex(),
            "party_mon_nick":from_mem(pb,"wPartyMon5Nick",11).hex(),
            "pokedex_owned":owned.hex(),
            "pokedex_seen":seen.hex(),
            "rattaking_dex_owned":bool(owned[18] & 0x80),
            "rattaking_dex_seen":bool(seen[18] & 0x80),
            "box_num":int(pb.memory[sym["wCurrentBoxNum"]]),
            "box_counts":from_mem(pb,"wBoxMonCounts",12).hex(),
            "box_view_sha256":sha(box),
        }
    def ticks(pb,n):
        for _ in range(n):pb.tick()
    def press(pb,button,delay=90):
        pb.button_press(button)
        ticks(pb,2)
        pb.button_release(button)
        ticks(pb,delay)
    def photo(pb,label):
        pb.screen.image.save(args.output/(label+".png"))
    evidence={}
    pb=PyBoy(str(temp_rom),window="null")
    try:
        with args.evolved_state.open("rb") as handle:pb.load_state(handle)
        before=snapshot(pb)
        evidence["before_save"]=before
        photo(pb,"evolved_before_save")
        if before["species"]!=RATTAKING or before["level"]!=36 or before["party_count"]!=5 or before["battle"]:
            raise AssertionError("Expected controller-evolved party Rattaking at level 36, outside battle")
        # START opens Gen 1 main menu. Choose SAVE by genuine buttons.
        press(pb,"start",170)
        photo(pb,"start_menu")
        for i in range(4):
            press(pb,"down",75)
            photo(pb,f"start_menu_down_{i+1}")
        press(pb,"a",130)
        photo(pb,"save_selected")
        press(pb,"a",150)
        photo(pb,"save_confirm_1")
        press(pb,"a",500)
        photo(pb,"save_confirm_2")
        evidence["after_save_menu"]=snapshot(pb)
        (args.output/"save_menu_diagnostics.json").write_text(
            json.dumps(evidence,indent=2)+"\n")
    finally:
        pb.stop(save=True)
    if not ram_path.is_file() or ram_path.stat().st_size<8192:
        raise AssertionError("No battery-backed SRAM file written; menu SAVE unverified")
    saved_sram=ram_path.read_bytes()
    evidence["saved_sram_sha256"]=sha(saved_sram)
    evidence["saved_sram_bytes"]=len(saved_sram)
    # The freshly started PyBoy loads ONLY the cartridge's actual SRAM.
    fresh=PyBoy(str(temp_rom),window="null")
    try:
        ticks(fresh,2200)
        photo(fresh,"fresh_title")
        press(fresh,"start",140)
        photo(fresh,"fresh_title_menu")
        press(fresh,"a",1100)
        photo(fresh,"fresh_continue_attempt")
        for i in range(12):
            now=snapshot(fresh)
            if now["party_count"]==before["party_count"] and now["species"]==RATTAKING and now["map"]==before["map"]:
                break
            press(fresh,"a",150)
            photo(fresh,f"fresh_continue_advance_{i}")
        after=snapshot(fresh)
        evidence["after_fresh_continue"]=after
        (args.output/"persistence_comparison.json").write_text(json.dumps(evidence,indent=2)+"\n")
        if after["party_count"]!=before["party_count"] or after["map"]!=before["map"]:
            raise AssertionError("Fresh CONTINUE did not load saved party/map; inspect game menu screenshots")
        for key in ("party_species","species","level","exp","moves","attack","defense",
                    "speed","special","maxhp","party_mon_bytes","party_mon_ot",
                    "party_mon_nick","pokedex_owned","pokedex_seen","box_num",
                    "box_counts","box_view_sha256"):
            if after[key]!=before[key]:
                raise AssertionError("SRAM CONTINUE changed field "+key+" from "+repr(before[key])+" to "+repr(after[key]))
        print("PASS genuine game SAVE/CONTINUE restored Rattaking and all party/Pokedex/box records",flush=True)
    finally:
        fresh.stop(save=True)
    after_sram=ram_path.read_bytes()
    if sha(after_sram)!=sha(saved_sram):
        raise AssertionError("Fresh CONTINUE modified battery SRAM bytes")
    evidence["after_continue_sram_sha256"]=sha(after_sram)
    (args.output/"persistence_comparison.json").write_text(json.dumps(evidence,indent=2)+"\n")
    (args.output/"persistence_gate_passed.json").write_text(json.dumps({"passed":True,"rom_sha256":sha(args.rom.read_bytes()),"sram_sha256":sha(after_sram)},indent=2)+"\n")

if __name__=="__main__":main()
