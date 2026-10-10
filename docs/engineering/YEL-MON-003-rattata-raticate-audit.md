# YEL-MON-003: Rattata and Raticate audit

Status: audit documented; no species or engine data changed. Branch: feature/yel-mon-003-rattata-audit.

## Confirmed approval
- Rattata and Raticate must both be pure DARK, not Normal/Dark.
- The currently inherited type constants do NOT define DARK; changing species to DARK immediately would fail assembly. Dark engine integration is a prerequisite.

## Inspected existing values (not newly approved balance changes)
| Species | HP | Atk | Def | SpA | SpD | Speed | BST |
|---|---:|---:|---:|---:|---:|---:|---:|
| Rattata | 30 | 56 | 35 | 25 | 35 | 72 | 253 |
| Raticate | 55 | 81 | 60 | 50 | 70 | 97 | 363 |

In base_stats, legacy five values HP/Atk/Def/Speed/Spc remain 30/56/35/72/25 and 55/81/60/97/50, and six-stat supplemental rows are 25/35 and 50/70.
Evolution: Rattata at level 20 to Raticate; currently implemented.
Starting moves: Rattata Tackle/Tail Whip; Raticate Tackle/Tail Whip/Quick Attack.
Level-up:
- Rattata Quick Attack 7, Hyper Fang 14, Focus Energy 23, Super Fang 34.
- Raticate Quick Attack 7, Hyper Fang 14, Focus Energy 27, Super Fang 41.

## Implementation prerequisites
1. Add DARK type ID while preserving stable existing numeric type values and checking unused slots, type-string pointer table length, type name display, and battle code assumptions.
2. Update type matchups using approved Gen 2 Dark chart: Dark attacks strong against Psychic/Ghost, resisted by Fighting/Dark/Steel (Steel only if present); Dark defenders weak to Fighting/Bug, resist Ghost/Dark, immune to Psychic. Ensure compatibility with currently implemented type roster and corrected Gen 1 Ghost/Psychic behavior. Preserve all other chart choices.
3. Verify battle-type effectiveness, STAB, UI typing, Pokémon storage, and interactions with dual-type duplicates (DARK/DARK).
4. Assign DARK/DARK to Rattata and Raticate only after DARK constant and lookup tables work.
5. Review Dark move availability and any proposed family learnset or TM updates; no replacement learnset or stats are currently authorized.
6. Validate via rgbds build and emulator tests: dark immunity/resistances/weaknesses, STAB, evolution, party/box saving.
7. Six-stat runtime integration remains prerequisite, inherited from YEL-BAL-002.

No build, emulator run, or merge performed. No unrelated Pokémon modified.
