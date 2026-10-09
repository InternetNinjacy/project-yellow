# YEL-BAL-002: Six-stat battle-engine migration (implementation branch)

Status: dependency audit in progress; NO executable battle-code change yet.
Baseline: Project Yellow master, inspected 2026-10-09.

## Verified entry points

- `constants/pokemon_data_constants.asm`: `BASE_STATS` uses `NUM_STATS`; `BASE_SPC`, `MON_SPC_EXP`, `MON_SPC`; boxed mon $21 bytes, party mon $2c bytes.
- `constants/battle_constants.asm`: `STAT_SPECIAL` and `NUM_STATS`.
- `data/pokemon/base_stats/*.asm`: currently HP/Atk/Def/Spd/Spc, e.g. Bulbasaur 45/49/49/45/65.
- `macros/ram.asm`: `box_struct` SpecialExp, `party_struct` Special, `battle_struct` Special.
- `engine/battle/core.asm`:
  - `GetDamageVarsForPlayerAttack` ~4201; `GetDamageVarsForEnemyAttack` ~4314 choose offense/defense by type threshold (`cp SPECIAL`), currently double defensive stats for screens, and double effective level on crits.
  - `CalculateDamage` ~4470 uses b=Attack, c=Defense, d=Power, e=Level.
  - `CriticalHitTest` ~4649.
  - NUM_STATS/record-length consumers include ~837, 1697, 1741, 1746, 6291, 6322, 6556; entire repository sweep still required.

## Nonnegotiable requirements

1. Independent Special Attack/Defense in base data, calculated stats, and battle calculations.
2. Per-move Physical/Special/Status categories override old type threshold. Approved Lick category is Special. Fixed-damage/effect paths bypass normal categories where specified.
3. Retain legacy SpecialExp and Special DV until a separate training-data design is approved. Both new Special stats derive their individual bases from the same legacy training fields.
4. Critical damage uses approved 1.5x multiplier with floor rounding; ignore negative offensive and positive defensive stages; bypass Reflect/Light Screen. No doubled critical level.
5. Screen multipliers are late in damage formula, with approved floor rounding; do not double defensive stats.
6. Preserve existing saves and boxed Pokémon if feasible; do not change structure sizes before finding every serialization/link/daycare/hall-of-fame user.
7. Preserve Yellow's approved 217/255 through 255/255 variation and original base formula where not contradicted.

## Migration gate

Before editing `NUM_STATS`, `MON_STATS`, `PARTYMON_STRUCT_LENGTH`, `box_struct`, or `battle_struct`, trace all offset/length assumptions in the repo. A naive additional 16-bit stat shifts party and battle structures and breaks data copying. Consider a legacy persistent record plus derived supplemental Special Defense battle/party cache; verify memory budget and all reads/writes before choosing.

## Validation required before merge

- Build with rgbds; check WRAM/ROM allocation.
- Six-stat species load, party, PC deposit/withdraw, daycare, evolution, save/load, link/trade.
- Physical vs Special mapping, modern crit stat stages, screens, integer boundaries, immunities, fixed damage, Substitute, double battle integration.
- Real Game Boy compatibility/emulator regression.

No changes to `master`; no ROM build or emulator test claimed.

## BAL-01: additional verified persistence dependency findings (2026-10-09)

1. `ram/sram.asm` defines `sPartyData` as `wPartyDataEnd - wPartyDataStart` and `sCurBoxData` as `wBoxDataEnd - wBoxDataStart`; all 12 saved boxes similarly use `wBoxDataEnd - wBoxDataStart`. Consequently any party/box record-size change also changes save layout and bank sizing. Existing saves CANNOT be assumed compatible.
2. `ram/wram.asm:1899-1925` allocates seven `party_struct` records (six plus extra); `:2485-2509` allocates 21 `box_struct` records; `:2480` daycare stores `box_struct`. Current `party_struct` is 0x2c and boxed record 0x21 bytes (confirmed constants).
3. `ram/wram.asm:1377-1384` allocates two `battle_struct` instances. Both currently contain one Special 16-bit word, so a separate derived Special Defense cache could be held outside the persistent party/box representation, but RAM budget and all stat-stage modification paths need inspection.
4. `ram/wram.asm:720-749` has a single Special stage modifier per side and one unmodified Special stat. Modern independent Special Attack and Special Defense require separate stage handling; reusing a single modifier would be mechanically incorrect.
5. `constants/battle_constants.asm:10-17` has five stat identifiers (HP, Attack, Defense, Speed, Special); `:19-28` has a single special modifier. Increasing `NUM_STATS` changes loops that previously assume 5, even if saved structures stay unchanged.
6. `engine/battle/core.asm` contains many `PARTYMON_STRUCT_LENGTH` and `NUM_STATS` users, including loops/copies near 1697, 1741, 1746, 6291, 6322, 6556; these need individual review, not blind global substitution.
7. `constants/battle_constants.asm:30-38` defines 6-byte per-move records without a category field. Prefer separate move category lookup table indexed by move ID to avoid shifting every move record.

### Design conclusion (provisional)

Maintain legacy 0x21-byte boxed records and 0x2c-byte party records, including SpecialExp and one Special DV, for save continuity. Derive independent Sp. Atk and Sp. Def from species-specific base stats and shared SpecialExp/DV upon party/battle load. Store additional *battle-only* stat and stage data outside persistent structs, subject to WRAM size verification. Separately define how newly calculated Special Attack maps to the existing party 'Special' field and where supplemental Special Defense is materialized. That is a candidate design, not an implemented or validated solution.

### Still outstanding

Repository-wide symbol-reference sweep (including stat stage routines, UI, link serialization, evolution, PC/deposit/withdraw), available WRAM budgeting, migration tests against existing saves, and actual assembly patches.

## BAL-02: Save/load and PC transfer boundary audit (2026-10-09)

Verified directly on `master` (source audit, not execution):

- `engine/pokemon/load_mon_data.asm` selects the source record based on party versus box and copies `PARTYMON_STRUCT_LENGTH` into `wLoadedMon`; preserving legacy party/box layouts also preserves this consumer's current stride. A derived extra Special Defense must be initialized by the caller or an explicit auxiliary calculation rather than blindly copied from saved bytes.
- `engine/pokemon/bills_pc.asm` uses both `PARTYMON_STRUCT_LENGTH` and `BOXMON_STRUCT_LENGTH` when selecting records. Deposit and withdraw paths need round-trip tests, including the existing Special field, species, DVs and stat experience.
- `engine/menus/save.asm` saves and loads `sGameData` with `sGameDataEnd - sGameData`, and copies main, party and current-box data through the SRAM layout. Existing checksums and box switching are therefore implicated by *any* persistent record expansion. Preserve original record sizes until an independently tested save migration exists.
- `macros/ram.asm` confirms exactly one Special stat in `party_struct` and `battle_struct`, one legacy SpecialExp in `box_struct`. This motivates a *derived* Special Defense battle cache, with the existing Special field tentatively serving as Special Attack, rather than modifying persistent records.
- `constants/battle_constants.asm` shows the status flags and stat modifier indices are distinct systems. The new defensive stat stage needs explicit reset, update, copy/Transform, Haze, and screen-interaction handling; simply adding a value to `NUM_STATS` will not do that safely.

### Gate and implementation order

1. Audit every stat producer and consumer, not just `CalcStats`: load, evolution, party menu, status screen, trainer creation, wild creation, Transform, link serialization and move effects.
2. Confirm WRAM headroom and choose stable locations for player/enemy Special Defense and each side's independent Sp. Def modifier. Preserve existing party/box bytes and offsets.
3. Introduce the separate move-category lookup by ID without altering existing six-byte move records; verify all 165 original entries against the locked authority before integration.
4. Patch the stat calculations and battle damage selection together with paired player/enemy tests; migrate stat-stage effects and critical/screen handling in the same bounded integration.
5. Run clean rgbds build, save/load and PC round-trips, then emulator tests before considering merge. Include the original-Pokémon-Yellow save fixture if available.

**Current branch remains unimplemented at the engine level.** No source change, build, emulator run or save migration is claimed by this audit.
