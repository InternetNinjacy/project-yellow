#!/usr/bin/env python3
"""Source-level guard for split-stat switch/reversion initialization.

This is a structural test, not proof of emulator gameplay.
"""
from pathlib import Path

CORE = Path("engine/battle/core.asm").read_text()


def section(start, end):
    assert start in CORE, f"Missing function: {start}"
    return CORE.split(start, 1)[1].split(end, 1)[0]


def contains_calls(block, *calls):
    for call in calls:
        assert "\tcall " + call in block, f"Missing {call}"


def test_switch_in():
    player = section("LoadBattleMonFromParty:", "LoadEnemyMonFromParty:")
    enemy = section("LoadEnemyMonFromParty:", "InitPlayerSpecialAttack:")
    wild = section("LoadEnemyMonData:", "DoBattleTransitionAndInitBattleVariables:")
    for name, block in (("player", player), ("trainer", enemy), ("wild", wild)):
        if name == "wild":
            contains_calls(block, "InitEnemySpecialAttack", "InitEnemySpecialDefenseCache")
        else:
            contains_calls(block, "InitPlayerSpecialAttack", "InitPlayerSpecialDefenseCache") if name == "player" else contains_calls(block, "InitEnemySpecialAttack", "InitEnemySpecialDefenseCache")
        assert "w" in block
    for name in ("InitPlayerSpecialDefenseCache:", "InitEnemySpecialDefenseCache:"):
        s = section(name, "LoadSpecialDefenseBase:") if name.startswith("InitEnemy") else section(name, "InitEnemySpecialDefenseCache:")
        assert "BASE_STAT_LEVEL" in s, f"{name} must reset SpD stage"
    for name in ("InitPlayerSpecialAttack:", "InitEnemySpecialAttack:"):
        assert name in CORE


if __name__ == "__main__":
    test_switch_in()
    print("PASS: structural switch-in/cache initialization checks (NOT gameplay verification)")
