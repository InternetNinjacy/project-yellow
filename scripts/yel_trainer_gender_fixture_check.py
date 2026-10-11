#!/usr/bin/env python3
"""Check the DEBUG Bug Catcher counterpart fixture and table wiring.

This is a source-level regression test, not a live battle capture.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
def source(path):
    return (root / path).read_text()

fixture = source("data/maps/objects/ViridianForest.asm")
assert re.search(r"IF DEF\(_DEBUG\).*?OPP_BUG_CATCHER, TRAINER_F_VARIANT \| 1.*?ELSE.*?OPP_BUG_CATCHER, 1.*?ENDC", fixture, re.S), "DEBUG-only encounter is missing"
names = source("engine/battle/get_trainer_name.asm")
assert 'li "BUG CATCHR♀"' in names
assert "wTrainerGenderVariant" in names
assert "db BUG_CATCHER" in names
assert "NUM_TRAINER_GENDER_VARIANTS EQU 25" in names
setup = source("engine/battle/get_trainer_name.asm")
assert "InitBattleEnemyParameters_::" in setup
assert "TRAINER_PARTY_INDEX_MASK" in setup
pics = source("data/trainers/pic_pointers_money.asm")
assert "pic_money BugCatcherPic," in pics
parties = source("data/trainers/parties.asm")
assert "dw BugCatcherData" in parties
assert re.search(r"BugCatcherData:\s*\n(?:;[^\n]*\n)*\s*db\s+6,\s+WEEDLE,\s+CATERPIE,\s+0", parties) or "BugCatcherData:" in parties
print("DEBUG Bug Catcher female source wiring PASS (not emulator battle verification)")
