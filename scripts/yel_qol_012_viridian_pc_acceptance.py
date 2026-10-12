#!/usr/bin/env python3
"""Controller-driven Viridian Bill PC 20+10 viewer/switch acceptance.

All physical record setup is test-only. PC input, assembly menu/view,
transaction staging and box selection must execute on the actual ROM.
"""
import argparse,json
from pathlib import Path
from pyboy import PyBoy
from yel_qol_012_gameplay_replay import symbol_table,play,box_bytes
from yel_qol_012_fixture import seed_scenario

def main():
 p=argparse.ArgumentParser()
 for key in ("rom","sym","boot","route","out"):p.add_argument("--"+key,required=True)
 args=p.parse_args()
 syms=symbol_table(args.sym)
 boot=json.loads(Path(args.boot).read_text())
 route=json.loads(Path(args.route).read_text())
 em=PyBoy(args.rom,window="null",cgb=False,sound_emulated=False)
 em.set_emulation_speed(0)
 out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
 result={"status":"NOT_VERIFIED","scope":"REAL_VIRIDIAN_BILLS_PC","hooks":[],"pages":[],"actions":[]}
 visited={key:0 for key in ("OpenPokemonCenterPC","ActivatePC","BillsPC_","Yel012SafePCView","Yel012SafePCDisplayPage","Yel012SafePCNextBox","Yel012AbortTransaction","CheckForHiddenEventOrBookshelfOrCardKeyDoor","CheckForHiddenEvent")}
 def callback(ctx,name):
  visited[name]+=1
  if len(result["hooks"])<90:result["hooks"].append(name)
  if name=="Yel012SafePCDisplayPage":
   count=em.memory[syms["wBoxCount"][1]]
   box=box_bytes(em,syms,0)
   page=20 if len(result["pages"]) else 0
   records=[]
   for i in range(min(count,20)):
    species=em.memory[syms["wBoxSpecies"][1]+i]
    mon=bytes(em.memory[syms["wBoxMons"][1]+i*33+j] for j in range(33))
    ot=bytes(em.memory[syms["wBoxMonOT"][1]+i*11+j] for j in range(11))
    nick=bytes(em.memory[syms["wBoxMonNicks"][1]+i*11+j] for j in range(11))
    expect=box[32+(i+page)*33:32+(i+page+1)*33]+box[1022+(i+page)*11:1022+(i+page+1)*11]+box[1352+(i+page)*11:1352+(i+page+1)*11]
    records.append(species==box[1+i+page] and mon+ot+nick==expect)
   result["pages"].append({"offset":page,"count":count,"records_matched":sum(records),"all_records_match":all(records)})
 for name in visited:
  if name not in syms:raise AssertionError("missing exported PC symbol "+name)
  bank,pc=syms[name]
  em.hook_register(bank,pc,callback,name)
 def press(key=None,held=4,idle=130):
  seq=[{"button":key,"frames":held} if key else {"frames":held}]
  if idle:seq.append({"frames":idle})
  play(em,seq)
  result["actions"]+=seq
 def loc():
  return tuple(em.memory[syms[k][1]] for k in ("wCurMap","wXCoord","wYCoord"))
 def walk(key):
  before=loc()
  press(key,8,24)
  if loc()[0]!=before[0]:press(None,300,0)
 try:
  play(em,boot["prepare"])
  assert em.memory[syms["wPartyCount"][1]]==6
  play(em,[{"frames":600}])
  seed_scenario(em.memory,syms,0,30,False)
  before=[box_bytes(em,syms,i) for i in range(12)]
  for direction in route["directions"]:walk(direction)
  assert loc()[0]==41,("failed to reach Viridian Center",loc())
  result["center_entry_position"]=loc()
  for direction in ("up","up")+("right",)*10:walk(direction)
  result["before_pc_action"]=loc()
  assert loc()==(41,13,5),("PC interaction base position differs",loc())
  # Test both grounded interaction tiles with separate A key edges.
  # The exploratory savestate search reached ActivatePC at (13,4);
  # acceptance MUST verify from this uninterrupted real-input boot.
  result["attempts"]=[]
  for tile in ("below","standing"):
   if tile=="standing":walk("up")
   else:press("up",1,300)
   press(None,300,0)
   for i in range(12):
    press("a",30,170)
    result["attempts"].append({"tile":tile,"index":i,"location":loc(),
      "facing":em.memory[syms["wSpritePlayerStateData1FacingDirection"][1]],
      "pc_hits":visited["ActivatePC"],
      "hidden_event_hits":visited["OpenPokemonCenterPC"],
      "cpu_pc":em.register_file.PC,
      "rom_bank":em.memory[syms["hLoadedROMBank"][1]],
      "joy_ignore":em.memory[syms["wJoyIgnore"][1]] if "wJoyIgnore" in syms else None,
      "status_flags5":em.memory[syms["wStatusFlags5"][1]],
      "joy_held":em.memory[syms["hJoyHeld"][1]],
      "joy_pressed":em.memory[syms["hJoyPressed"][1]],
      "hidden_dispatch_hits":visited["CheckForHiddenEventOrBookshelfOrCardKeyDoor"],
      "hidden_lookup_hits":visited["CheckForHiddenEvent"]})
    if visited["ActivatePC"]:break
   if visited["ActivatePC"]:break
  result["after_pc_action"]=loc()
  assert visited["ActivatePC"]>0,"PC interaction never ran"
  for i in range(18):
   if visited["BillsPC_"]:break
   press("a",4,150)
  assert visited["BillsPC_"],"Bill PC menu not reached"
  for i in range(12):
   if result["pages"]:break
   press("a",4,150)
  assert result["pages"],"physical viewer did not execute"
  for i in range(12):
   if len(result["pages"])>=2:break
   press("b",4,130)
   press("a",4,130)
  result["selected_before_switch"]=em.memory[syms["wCurrentBoxNum"][1]]&0x7f
  for i in range(16):
   if visited["Yel012SafePCNextBox"]:break
   press("b",4,140)
   press("down",4,50)
   press("a",4,140)
  result["selected_after_switch"]=em.memory[syms["wCurrentBoxNum"][1]]&0x7f
  result["counters"]=visited
  assert len(result["pages"])>=2,("second PC page absent",result["pages"])
  assert result["pages"][0]["count"]==20 and result["pages"][1]["count"]==10
  assert all(x["all_records_match"] for x in result["pages"][:2])
  assert visited["Yel012SafePCNextBox"]>0,"non-copying box selector did not run"
  assert result["selected_after_switch"]==1
  assert [box_bytes(em,syms,i) for i in range(12)]==before,"PC viewing/switch mutated physical records"
  result["status"]="PASS_REAL_PC_20_PLUS_10_AND_SELECT_NON_MUTATING"
 except Exception as e:
  result["counters"]=visited
  result["error"]=repr(e)
  raise
 finally:
  out.write_text(json.dumps(result,indent=2)+"\n")
  em.stop(save=False)
if __name__=="__main__":main()
