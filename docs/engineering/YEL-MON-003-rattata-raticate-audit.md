# YEL-MON-003 / YEL-MON-004 — Rat family corrected audit

**Authoritative design:** YEL-DEX-001 Google Drive registry, latest October 9, 2026 locked family update. This document supersedes the former two-stage, level-20 baseline audit. Design approval does not imply complete ROM implementation.

## Locked family
| Species | Type | HP | Atk | Def | SpA | SpD | Spe | BST |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Rattata | Dark | 40 | 65 | 40 | 25 | 40 | 80 | 290 |
| Raticate | Dark | 65 | 85 | 60 | 45 | 65 | 95 | 415 |
| **Rattaking** | Dark | 85 | 115 | 80 | 60 | 85 | 105 | 530 |

Evolution: Rattata to Raticate at **level 18**, Raticate to Rattaking at **level 36**. Third species spelling is exactly **Rattaking**.

Approved Rattaking visual direction: approximately five-foot, black-furred muscular upright/slightly hunched rat with cream accents, red eyes, thick balancing tail, familiar Raticate-like snout, prominent incisors, ears and whiskers. No completed sprite is claimed.

## Locked natural moves
- All three: level 1 Tackle + Tail Whip, 5 Quick Attack, 9 Bite, 13 Focus Energy, 17 Hyper Fang, 21 Rage, 28 Super Fang.
- Raticate and Rattaking additionally: 25 Scary Face and 32 Poison Fang.
- Rattaking additionally: 40 Slash, 44 Thrash, 50 Crunch (not Hyper Beam naturally).
- Crunch: Dark / Physical, power 80, accuracy 100%, PP 30; **exact 39%** Defense -1 chance.
- Poison Fang: Poison / Physical, power 50, accuracy 100%, PP 15; 50% chance to badly poison. Replaces global TM34 Bide; Safari Zone Poké Ball pickup (exact area/tile TBD).
- Globally approved Dark retypes: Bite, Rage, Thrash, Glare, Pay Day. Categories: Bite/Rage/Thrash/Pay Day Physical; Glare Status.

## Locked TM/HM eligibility
| TM/HM | Rattata | Raticate | Rattaking |
|---|---|---|---|
| TM01 Mega Punch | no | yes | yes |
| TM05 Mega Kick | no | yes | yes |
| TM08 Body Slam | yes | yes | yes |
| TM10 Double-Edge | yes | yes | yes |
| TM15 Hyper Beam | yes | yes | yes |
| TM17 Submission | no | no | yes |
| TM20 Rage | yes | yes | yes |
| TM26 Earthquake | no | no | yes |
| TM28 Dig | yes | yes | yes |
| TM34 Poison Fang | yes | yes | yes |
| TM40 Skull Bash | no | yes | yes |
| TM06 Toxic / TM31 Mimic / TM32 Double Team / TM44 Rest / TM50 Substitute | yes | yes | yes |
| HM01 Cut | yes | yes | yes |
| HM04 Strength | no | yes | yes |
| HM02 Fly / HM03 Surf / HM05 Flash | no | no | no |

All other TMs excluded, explicitly including Ice Beam, Blizzard, Thunderbolt, Thunder, Psychic and Fire Blast. Check actual TM numbering against eventual remaps.

## Source changes on feature/yel-mon-004-rat-family-approved
- DARK constant at previously unused type 09, display name and Gen II Dark matchup entries. Ghost vs Psychic changed from Gen I bugged immunity to effectiveness.
- Existing Rattata/Raticate base stat tables and special-stat table aligned to approved six-stat values. Pure DARK encoded DARK/DARK.
- Rattata evolves at level 18. Shared learnable existing level-up attacks staged at approved levels for Rattata and Raticate.
- Available pre-existing TMs/HMs in the approved set staged for Rattata/Raticate, excluding Poison Fang until global TM34 remap.
- Five global Dark move retypes staged.

## NOT YET IMPLEMENTED (hard blockers)
1. Rattaking not yet assigned a collision-free internal species ID. Requires *all* dependent tables: species constant/index, names, National Dex mapping, base stats (six-stat access must accommodate new dex row), evolution pointer, cries, Pokédex entries, graphics, sprites, menus, storage, wild/trainer compatibility. **Do not write unresolved RATT AKING symbols into runnable evolution data.**
2. Raticate L36 evolution not activated until Rattaking has its registered species ID.
3. Scary Face, Poison Fang and Crunch move imports and their effects, move names/IDs, animation/SFX tables, exact custom 39% chance, category table, evolution-stage learnset additions.
4. TM34 Bide-to-Poison Fang replacement, all global TM item/script text/map sources and matching species eligibility.
5. Dark-type engine compatibility, Gen II chart coverage, physical/special category integration and monotype UI checks.
6. Full legacy-special to six-stat runtime migration, save/capture/PC and linking tests.
7. Build, emulator replay, and hardware tests **not performed**; do not merge until all pass.

Source references and unresolved tasks remain here so the approved design is not lost or silently altered.
