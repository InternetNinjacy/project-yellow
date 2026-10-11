#!/usr/bin/env python3
"""Fail-closed YEL-QOL-012 PC/legacy compatibility source audit.

This diagnostic does not replace live PyBoy PC navigation. It inspects
actual ROM inputs and produces actionable facts, not a false PASS.
"""
import argparse,json,re
from pathlib import Path
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=".")
 p.add_argument("--out",required=True)
 a=p.parse_args()
 root=Path(a.root)
 pc=(root/"engine/pokemon/bills_pc.asm").read_text()
 save=(root/"engine/menus/save.asm").read_text()
 txn=(root/"engine/menus/yel_qol_012_transaction.asm").read_text()
 bridge=(root/"engine/menus/yel_qol_012_capture_bridge.asm").read_text()
 checks={
 "pc_deposit_still_calls_legacy_MoveMon":bool(re.search(r"BillsPCDeposit:.*?call MoveMon",pc,re.S)),
 "pc_withdraw_still_calls_legacy_MoveMon":bool(re.search(r"BillsPCWithdraw:.*?call MoveMon",pc,re.S)),
 "pc_withdraw_still_calls_legacy_RemovePokemon":bool(re.search(r"BillsPCWithdraw:.*?call RemovePokemon",pc,re.S)),
 "pc_release_still_calls_legacy_RemovePokemon":bool(re.search(r"BillsPCRelease:.*?call RemovePokemon",pc,re.S)),
 "pc_change_box_still_calls_legacy_ChangeBox":bool(re.search(r"BillsPCChangeBox:.*?farcall ChangeBox",pc,re.S)),
 "pc_display_uses_legacy_wBoxCount": "ld hl, wBoxCount" in pc,
 "pc_physical_transaction_bridge_called":bool(re.search(r"(?:call|farcall)\s+Yel012(?:BeginTransaction|StageWindow|ReadBoxRecord|WriteBoxRecord)",pc)),
 "pc_current_box_has_legacy_working_window": "DEF YEL012_WINDOW_SIZE EQU 1122" in txn,
 "physical_box_is_1682_bytes": "ASSERT YEL012_BOX_SIZE == 1682" in txn,
 "legacy_save_loader_checks_physical_version": "Yel012CheckStorageVersion" in save.split("TryLoadSaveFile:",1)[1].split("LoadMainData:",1)[0],
 "capture_uses_transaction_engine": "call Yel012BeginTransaction" in bridge}
 blockers=[k for k,v in checks.items() if (k in
  ("pc_deposit_still_calls_legacy_MoveMon","pc_withdraw_still_calls_legacy_MoveMon",
   "pc_withdraw_still_calls_legacy_RemovePokemon","pc_release_still_calls_legacy_RemovePokemon",
   "pc_change_box_still_calls_legacy_ChangeBox","pc_display_uses_legacy_wBoxCount") and v)
  or (k in ("pc_physical_transaction_bridge_called","legacy_save_loader_checks_physical_version") and not v)]
 result={"status":"BLOCKED_LEGACY_PC_UNSAFE","source_audit":checks,"blockers":blockers,
         "required_before_approval":[
         "Route PC deposit/withdraw/release through 30-slot bank-5 transactions",
         "Stage paginated physical box records for list and stats views",
         "Implement physical-box selection without legacy 20-slot copy",
         "Reject or explicitly migrate legacy saves before exposing the expanded PC",
         "Run controller-driven 20/21/29/30 boundaries, full record and SAVE/CONTINUE comparisons"]}
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,indent=2)+"\n")
 print("PC audit status:",result["status"],"blockers:",len(blockers))
if __name__=="__main__":main()
