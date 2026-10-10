#!/usr/bin/env python3
"""Run seven approved PC box layouts against the feature branch ROM.

Required: a confirmed, deterministic *capture* sequence. This orchestrator
does not construct gameplay provenance or infer successful captures.
All scenario state files are private and must never be uploaded.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

SCENARIOS = {
 "current-space":(0,[19]+[0]*11,0,1),
 "next-box":(0,[20]+[0]*11,1,1),
 "skip-full":(0,[20,20,20]+[0]*9,3,1),
 "wrap":(11,[0]*11+[20],0,1),
 "wrap-skip":(10,[20,0,0,0,0,0,0,0,0,0,20,20],1,1),
 "all-full":(0,[20]*12,0,0),
 "only-current-free":(3,[20,20,20,19]+[20]*8,3,1),
}
def main():
 p=argparse.ArgumentParser()
 for arg in ("rom","sym","base-state","sequence","fixture-builder","storage-harness","out"):
  p.add_argument("--"+arg,required=True)
 a=p.parse_args()
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 steps=json.loads(Path(a.sequence).read_text())
 if not isinstance(steps,list) or not steps or not any(x.get("button") in ("a","b","start") for x in steps):
  raise ValueError("Deterministic verified capture inputs required")
 report={"schema":"YEL-QOL-011-MATRIX/1","status":"FAIL",
         "rom_sha256":hashlib.sha256(Path(a.rom).read_bytes()).hexdigest(),
         "base_state_sha256":hashlib.sha256(Path(a.base_state).read_bytes()).hexdigest(),
         "sequence_sha256":hashlib.sha256(Path(a.sequence).read_bytes()).hexdigest(),
         "cases":[]}
 try:
  for name,(active,counts,expected,delta) in SCENARIOS.items():
   dest=out/name;dest.mkdir(exist_ok=True)
   state=dest/"seeded.state"
   subprocess.run([sys.executable,a.fixture_builder,"--rom",a.rom,"--sym",a.sym,
      "--base-state",a.base_state,"--counts",",".join(map(str,counts)),
      "--active",str(active),"--out",str(state)],check=True)
   cmd=[sys.executable,a.storage_harness,"--rom",a.rom,"--sym",a.sym,
       "--state",str(state),"--sequence",a.sequence,
       "--expected-active-box",str(expected),"--expected-count-delta",str(delta),
       "--assert-all-boxes","--out",str(dest/"result")]
   result=subprocess.run(cmd,check=False)
   try:
    details=json.loads((dest/"result"/"report.json").read_text())
   except FileNotFoundError:
    details={"status":"FAIL","error":"No storage report created"}
   status="PASS_UNSAVED_MEMORY_ONLY" if result.returncode==0 and details.get("status")=="EMULATOR_RECORDS_PRESERVED_NOT_SAVE_VERIFIED" else "FAIL"
   record={"id":name,"active_before":active,"expected_after":expected,
           "expected_added":delta,"status":status,"test_report":details.get("status"),
           "returncode":result.returncode,"error":details.get("error")}
   report["cases"].append(record)
   (out/"matrix.json").write_text(json.dumps(report,indent=2)+"\n")
  if len(report["cases"])==7 and all(c["status"]=="PASS_UNSAVED_MEMORY_ONLY" for c in report["cases"]):
   report["status"]="ALL_SEVEN_EMULATOR_MEMORY_PASSES_NATIVE_SAVE_UNVERIFIED"
  (out/"matrix.json").write_text(json.dumps(report,indent=2)+"\n")
  print(json.dumps(report,indent=2))
  if report["status"]=="FAIL":raise SystemExit(1)
 finally:
  (out/"matrix.json").write_text(json.dumps(report,indent=2)+"\n")

if __name__=="__main__":
 main()
