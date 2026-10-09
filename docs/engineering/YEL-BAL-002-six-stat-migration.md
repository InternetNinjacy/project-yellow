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

## BAL-03: transient battle cache reservation (2026-10-09)

**First executable-source edit committed to PR #5:** `ram/wram.asm` now declares a separate `SECTION "Six Stat Battle Cache", WRAM0`, allocating ten bytes: two 16-bit current Special Defense values, two 16-bit unmodified Special Defense values, and two independent 8-bit Special Defense stage modifiers (one set for each side). These are *separate from serialized party and box structs*. The existing `Special` fields and persistent record lengths have not changed.

- Added names: `wPlayerSpecialDefense`, `wEnemySpecialDefense`, `wPlayerUnmodifiedSpecialDefense`, `wEnemyUnmodifiedSpecialDefense`, `wPlayerSpecialDefenseMod`, `wEnemySpecialDefenseMod`.
- This is a **storage reservation only**, not functional six-stat damage support. Values are not initialized, derived, copied, or read by battle code yet. Special Attack remains at the legacy Special address pending later integration.
- **Validation status:** Re-fetched the branch file and confirmed declarations exist. No rgbds/linker build or emulator verification performed; WRAM0 allocation success and section link placement must be verified by CI before merging.
- Next: wire derived stat values on wild/trainer/party load; reset/copy both stages on switch, Transform and Haze; then integrate category-driven stat selection with matching tests.

## BAL-04: initialise transient stat cache on battler loads (2026-10-09)

Committed a bounded assembly edit to `engine/battle/core.asm`:

- `LoadBattleMonFromParty` now calls `InitPlayerSpecialDefenseCache` after its existing stage reset.
- `LoadEnemyMonFromParty` now calls `InitEnemySpecialDefenseCache` after its existing stage reset.
- The wild/trainer non-link path in `LoadEnemyMonData` now calls `InitEnemySpecialDefenseCache` after its existing stage reset.
- Each helper copies the current 16-bit legacy Special value to both its current and unmodified supplemental Special Defense cache, and resets its new Sp. Def stage to neutral (`BASE_STAT_LEVEL`). No persistent party or box layout is changed.

**Strict scope warning:** This is a transitional *initialisation* step only. The cache initially equals legacy Special, not a separately derived species Sp. Def. Stat-exp/DV-based independent calculation, new species Sp. Atk/Sp. Def bases, per-move category routing, switch/Transform/Haze update paths, and six-stat battle math are still required. Branch source was re-fetched to confirm both helpers and three call sites; no ROM build or emulator validation has yet occurred. Do not merge until all users and WRAM allocation are tested.

## BAL-05: separate species stat source verification (2026-10-09)

Inspected Project Yellow `data/pokemon/base_stats.asm`: 151 included per-species files in National Dex order. Confirmed the approved Gen-II-derived starting point: `pret/pokecrystal/data/pokemon/base_stats/bulbasaur.asm` defines six base stats `45,49,49,45,65,65` (HP/Atk/Def/Spd/SpA/SpD). This is a reference, not imported game data.

Integration rules: maintain legacy five-stat ROM species layout and existing boxed/party save layouts until stat/header consumers are migrated; a separate 151-entry Sp. Def (and Sp. Atk if different from old Special) table must be fully populated and audited by dex index, with explicit handling for added species. The battle cache must be **computed** from the new species base Sp. Def plus shared Special DV and Special stat experience using the existing non-HP stat formula at its level. No shortcuts copying legacy Special can be treated as final behavior. Wire both player and enemy through a single calculation helper and regression-test species with unequal SpA/SpD, including after box retrieval and level-up.

**Not yet complete:** all-species import, safe header lookup, actual stat computation code, assembler build and emulator tests. The attempted bulk reference import was interrupted; no partial species table is used in game. Preserve current functional fallback until a full, verified table and helper can be committed atomically.

## BAL-06: full 151-species split table and derived Sp. Def calculation (2026-10-09)

**Committed to draft PR #5:**

- Added `data/pokemon/base_special_stats.asm`, a **151-entry**, National Dex-ordered two-byte table of historical Special Attack and Special Defense species bases, from PokeAPI modern stat CSV with pre-Gen VI historical overrides from `pokemon_stats_past.csv`. 111 species have unequal split base values. Not an authoritative override for separately approved Project Yellow species redesigns or new species.
- Included the table at the end of `data/pokemon/base_stats.asm`, outside the existing per-species five-stat record layout.
- Replaced battle-only fallback initialization helpers in `engine/battle/core.asm`: the player, enemy-party and nonlink wild-enemy switch-in paths now retrieve a species' Special Defense base using internal-ID -> National Dex translation; temporarily substitute it into the legacy stat calculator's Special base; call `CalcStat` with the same Special DV and corresponding existing Special stat experience (wild opponents use zero stat experience), and store both current/unmodified 16-bit Special Defense into the new WRAM cache. Restore the original header base and level afterwards; reset derived stage to neutral. Unsupported IDs retain the old legacy Special fallback.
- Verified by re-fetch: 151 source rows, table INCLUDE, helper label and all three caller paths.

**Validation restrictions / remaining work:** Assembly has NOT been compiled or run, so build linkage/bank placement, register side effects, and compatibility across switching, Transform, stat-stage effects, original saves and linked battles remain unverified. This change ONLY derives Sp. Def on battler load: damage calculation still uses legacy Special, and Sp. Atk has not been migrated to its split species base. Do not merge until RGBDS build plus battle/save tests and category-driven damage wiring pass.

## BAL-07: Special Attack calculation and move-category damage routing (2026-10-09)

On draft PR #5:
- Added a 165-row `MoveCategories` registry in `data/moves/moves.asm` from modern damage categories, preserving the existing six-byte move records. Locked exceptions applied: Razor Leaf Physical, Lick Special. Constants `MOVE_CATEGORY_PHYSICAL/SPECIAL/STATUS` defined in `constants/battle_constants.asm`.
- Added `GetBattleMoveCategory` in `engine/battle/core.asm` and replaced both player and opponent ordinary damage type-threshold selection with per-move category lookups.
- Added `InitPlayerSpecialAttack` and `InitEnemySpecialAttack`: on battler load, derive 16-bit Sp. Atk using the split species base and existing Special DV/experience via Yellow `CalcStat`; update active Special and unmodified Special snapshot without expanding saved party or boxed records.
- Ordinary Special damage defense pointer now loads new `wEnemySpecialDefense`/`wPlayerSpecialDefense` caches rather than legacy combined Special.

**Not ready to merge:** GitHub CI is queued; builds and game testing not yet verified. Legacy critical-hit handling still temporarily substitutes legacy Special and doubles level, and screen handling still doubles defense, both contrary to approved modernized mechanics. Status categories are available but the full effects engine and unusual moves are not yet migrated. Stat stages, Transform/Haze, link battle consistency and temporary cache refresh on moves need further work. Do not report full correct split battle behavior until these are addressed and emulator tested.

## BAL-08: critical multiplier and late screen initial integration (2026-10-09)

- Read PR #5 CI failures: `FATAL: Unable to place "Six Stat Battle Cache" (WRAM0 section) anywhere`. Fixed source `ram/wram.asm` by allocating the 10 bytes from the existing 13-byte unused span following `wPlayerMonMinimized`, leaving a 3-byte pad. This preserves the offsets of subsequent battle RAM data; separate WRAM0 section removed. One CI workflow for commit ca790a9c completed successfully; other workflows still pending at that observation.
- Integrated `ApplyProjectYellowCriticalDamage` immediately after base `CalculateDamage` for ordinary player/enemy attacks, before type and random; computes floor(3 * damage / 2) using 16-bit arithmetic, replacing the original double-level critical damage adjustment in the respective stat preparation routines.
- Removed legacy Reflect/Light Screen doubling of defense from both ordinary player/enemy damage preparation paths. Added `ApplyProjectYellowScreens` after `RandomizeDamage` for singles, reducing Physical damage through Reflect or Special through Light Screen by floor(damage/2), and bypassed on critical hits. Ordinary Physical/Special selection uses the per-move category registry, rather than elemental type.

**Known incomplete conditions, explicitly NOT closed:** Modern critical handling for positive attacking/negative defending stat stages is not yet correct in legacy critical-stat branches. Full critical stage probability engine and Focus Energy handling remain legacy. Screen duration and 2/3 double-battle damage fraction not implemented. Multi-hit/fixed-damage/edge move effects and pre-existing damage arithmetic still require audit. Builds for the latest commits must be checked, as must in-game tests and memory allocation. PR must stay draft and unmerged.
