# YEL-MON-001: Pidgey and Weedle implementation audit

Status: staged on isolated feature branch; NOT build-tested or emulator-tested.
Base: yel-bal-002-six-stats (six-stat integration work in progress).

## Approved stat targets (HP / Atk / Def / SpA / SpD / Spe)

| Species | HP | Atk | Def | SpA | SpD | Spe | BST |
|---|---:|---:|---:|---:|---:|---:|---:|
| Pidgey | 45 | 55 | 40 | 40 | 45 | 85 | 310 |
| Pidgeotto | 65 | 75 | 55 | 55 | 60 | 105 | 415 |
| Pidgeot | 85 | 105 | 70 | 75 | 80 | 115 | 530 |
| Weedle | 50 | 55 | 45 | 30 | 40 | 80 | 300 |
| Kakuna | 60 | 55 | 85 | 30 | 80 | 35 | 345 |
| Beedrill | 75 | 110 | 80 | 50 | 80 | 105 | 500 |

## Changes staged
- Updated the 5-byte Gen I-style base-stat fields to HP / Atk / Def / Speed / Special Attack for all six species. This preserves the existing base-data layout, but the fifth byte remains the legacy Special field at runtime until the six-stat engine fully replaces it.
- Updated the separate `data/pokemon/base_special_stats.asm` SpA/SpD table for species 13–18. This table's runtime use is a separate YEL-BAL-002 integration dependency.
- Pidgey, Pidgeotto, and Pidgeot type bytes are now FLYING / FLYING, representing monotype Flying without altering the species data layout.
- Pidgey evolves at 18 and Pidgeotto evolves at 36: already matching approved settings; left unchanged.
- Weedle evolves at 16 and Kakuna at 36: updated from 7 and 10.
- Beedrill learns Whirlwind at 44 in place of the existing Agility learnset entry; other unapproved learnset changes were not introduced.

## Open work / gates
1. **Build test:** Run rgbds build and confirm data-size and symbol/link compatibility.
2. **Engine prerequisite:** Complete YEL-BAL-002 six-stat runtime integration; validate battle, PC storage and persistence.
3. **Monotype:** Confirm all type-matchup and UI consumers work with FLYING/FLYING.
4. **Twineedle:** Implement approved two-hit / hit-reliability / +1 Speed mechanic with explicit checks for immunity, protection, accuracy and secondary effects. This commit does not modify the battle-effect engine.
5. **Learnsets and TMs:** Recover and compare full earlier-approved level-up moves and TM lists before making further revisions. Current lists are not claimed to be final.
6. **Emulator:** Test both evolution transitions, six-stat battle values, learnsets, save and continue, and actual battle behavior. None performed here.

Do not merge to master until the six-stat dependency and regression tests pass. Other ROM-hack projects are unrelated.
