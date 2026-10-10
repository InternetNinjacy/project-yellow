#!/usr/bin/env python3
"""Fail closed until double-battle RAM is actually disjoint and verified.

This guard intentionally documents that the current second-slot records are
overlaid with graphic/overworld scratch, not protected game-state memory.
"""
from pathlib import Path

ram = Path("ram/wram.asm").read_text()
core = Path("engine/battle/core.asm").read_text()
stage = Path("engine/battle/doubles_secondary.asm").read_text()

assert "wDoublesSecondaryBattleDataStart::" in ram
assert "wOverworldMap:: ds 1300" in ram
assert "wDoublesSecondaryBattleDataStart::" in ram.split('SECTION "Overworld Map", WRAM0', 1)[1].split('SECTION "WRAM", WRAM0', 1)[0]
assert "ld [wBattleFormat], a" in core
assert "call StageDoublesPlayerSecondFromParty" not in core
assert "call StageDoublesEnemySecondFromParty" not in core
assert "wDoublesPlayer2SpecialDefense" in ram and "wDoublesEnemy2SpecialDefense" in ram
assert "StageDoublesPlayerSecondFromParty:" in stage
assert "StageDoublesEnemySecondFromParty:" in stage
print("PASS (guard only): unsafe overlay remains inactive; no doubles enablement or runtime proof")
