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

## BAL-09: critical-hit stage probability integration (2026-10-09)

Commit `9a070f113bb742f5045e996f88c20a253c50a1b8` replaces the original Speed-based `CriticalHitTest` in `engine/battle/core.asm` with stage-based odds: stage 0 = 1/24, stage 1 = 1/8, stage 2 = 1/2, stage >=3 = guaranteed. High-critical move membership contributes +1 stage and Focus Energy contributes +2; their effects now compound without the original Focus Energy bug. Stage 0 rejection-samples 0..239 for exact 1/24; other stages use thresholds on one 8-bit random draw. No stored Pokémon record layout changes.

**Validation gate:** Source was committed; build workflows were queued when checked and emulator outcomes are not established. The crit stage rates should be checked against the separate Mechanics Authority before merge. **Still required:** correct stat-stage bypass semantics (ignore only offensive penalties and defensive boosts on crit), apply independent Sp. Def stage modifiers consistently, five-turn Reflect/Light Screen tracking and expiration, proper doubles scaling and target ownership, and regression testing. Keep the PR in draft and do not claim a complete critical/screen/doubles migration.

## BAL-10: critical-hit stat-stage selectivity (2026-10-09)

On PR #5, engine/battle/core.asm now selects the current adjusted offense and defense independently, and only substitutes the unmodified stat during a critical hit when the attacking stat stage is **below neutral** or the defending stat stage is **above neutral**. Positive Attack / Sp. Atk stages and negative Defense / Sp. Def stages remain effective on critical hits. Physical and Special paths are symmetric for the player and opponent, using the separate Special Defense cache and its stage index. Legacy critical branches that reset both stats through GetEnemyMonStat/party fields have been removed. The current stat values (including nonstage modifiers such as burn where applied) are not otherwise rewritten in this pass. Persistent party and box record sizes unchanged.

Source update commit `c184fddbb43682f3491014cc9516932836cf095d`; static readback verified both pathways each have one scaling label and no legacy critical stat branch. CI, dev lab build, baseline and emulator smoke were queued, without results when checked. **Not yet validated in ROM**: stage-effect producers must populate the independent Special Defense active stat, no on-cart stage-case test exists yet, and no emulator test has demonstrated outcome. Do not merge until verified. Next: stat-stage effects, screen turn counters and doubles mechanics separately.

## BAL-11: retired conversation handoff (2026-10-09)

Previous conversation retired. Continue engineering from current live PR #5, branch `yel-bal-002-six-stats`, targeting `master`. No merge authorization or green functional battle test is implied.

**Verified before this handoff:** commit `613b472c552701266fa142bee18046a2ca00df1d` had all four GitHub Actions green: CI `38005964943`, clean baseline `38005965107`, dev lab build `38005965084`, DMG emulator smoke `38005964970`. The smoke confirms boot only; none of these is deterministic validation of critical calculations, SpD stages, Reflect/Light Screen timing, two-active-side doubles, PC storage, or backwards save compatibility.

The selective critical-stage selection patch `c184fddbb43682f3491014cc9516932836cf095d` replaces both previous reset-both-stats critical branches. On critical only: if attacker offensive stage < neutral then use unmodified offense; if defender defensive stage > neutral then use unmodified defense. Otherwise preserve the active adjusted value. Covers Physical/Special and player/enemy, with a dedicated SpD stage cache. Prior critical chance stages 0=1/24, 1=1/8, 2=1/2, >=3 guaranteed; Focus Energy +2 and high-crit moves +1. User explicitly approved original Yellow base damage/random 217..255/255, 1.5x crit before STAB/type/random rounded immediately down, singles screens 1/2 late rounded down and critical bypass, doubles screens 2/3 when implemented.

**Next required implementation:** wire independent SpD stage producers/consumers including Amnesia, Growth, Psychic's SpD drop, Haze and Transform, then write emulator fixtures for both positive/negative attacker/defender critical-stage cases. After that, implement team-wide screen counters and five-turn expiry, and integrate true double battles (two active positions, participant state, target choice/recheck, one-usable-Pokemon case, 2/3 screen damage, trainer/AI cases). Maintain original serialized party/box record sizes. Check updated Mechanics Authority and Work Registry before making changes, including concurrent Dark move typing/Poison Fang canon; always reconcile live branch and parallel PRs first.

## BAL-11: Growth independent Sp. Def stage (2026-10-09)

Commit `efaff938367060c79e1211ad65c40d778821766b` adds a bounded Growth hook to `StatModifierUpEffect` in `engine/battle/effects.asm`. When the existing Special Attack increase succeeds, the hook increments the separate player/enemy Special Defense modifier (up to +6) and recalculates the derived current Special Defense using the unmodified supplemental cache and the existing StatModifierRatios multiplication/division path, capped at 999. Party/box record sizes and save data are unchanged.

This is source integration only. It has NOT been proven through a successful new build or in-game emulator assertions. Known gap: when Special Attack is already at +6 but Special Defense is not, legacy effect rejection prevents Growth from increasing Special Defense; the final combined move handler must handle this case. Amnesia still incorrectly affects Special Attack, Psychic still lowers Special Attack, and Haze/Transform/switch propagation remain pending. Do not merge.

## BAL-12: Growth/Amnesia/Psychic independent Special Defense stage routing (2026-10-09)

Branch code commits `9d7fbbf934e2fd757f76965599e43c1aaa6edcf8` and `17bc044561548add1c992c60741791da8ff07094` modify `engine/battle/effects.asm`:
- Amnesia routes exclusively to supplemental Special Defense (+2, capped at +6); original Special Attack remains unchanged.
- Growth independently advances supplemental Special Defense (+1) and the existing Special Attack (+1). Either stage can advance when the other is already +6.
- Psychic's `SPECIAL_DOWN_SIDE_EFFECT` routes to supplemental target Special Defense (-1) rather than old Special Attack after the existing secondary-effect chance/substitute checks.
- The supplemental calculation reuses the original battle stat-stage ratio table, floor division, minimum one, maximum 999 and separate player/enemy derived base caches.
- Existing party and box serialized records are unchanged.

Verification: all four workflows passed at earlier Growth-only commit efaff938, **not** evidence for this new source. New RGBDS/DMG CI is required. Deterministic emulator battle-state fixtures have not been run and cannot be claimed; minimum required fixtures: each move from both player/enemy perspectives, +6/-6 mixed boundaries, independent stage/state reads and output damage, secondary-effect trigger and miss, switching, Haze and Transform. This change does not yet implement Haze, Transform, screens or double-battle architecture. PR stays draft.

## BAL-13: deterministic PyBoy battle replay runner (2026-10-09)

Committed `tests/battle/replay.py` (`11c857c9bfcb4f96e4a2b6cc96de21ed72eecf7a`) and its capture instructions (`c27ee051d22ba5cb48ff3064f9d6957b3cd48bc0`). The script parses the built ROM's symbol map, loads each real battle savestate into PyBoy, checks pre-action player/enemy Special Attack and supplemental Special Defense stage/stat memory, replays frame-explicit button input, and checks post-action state, including HP delta for a damage case. All ten baseline cases are required. Missing save-states and missing cases are hard failures, not skipped tests.

**Evidence level:** test *runner source* committed; not a captured fixture. No valid pre-battle savestate or completed deterministic replay is present, and the runner is not wired into Actions without bona fide fixtures. Previously passing DMG smoke workflows remain startup-only. Next: capture genuine in-battle states, fill manifest with independently checked expected stats and damage, execute PyBoy replay, fix any confirmed code divergences, and only then promote actual mechanic cases to verified. PR #5 stays draft.

## BAL-14: Mechanics Thread 3 return to mechanics (2026-10-09)

Ownership split affirmed: this YEL-BAL-002 thread implements game battle rules; PyBoy/RGBDS installation, controller trace capture, real first battle state, and shared fixture infrastructure are delegated to YEL-TEST shared emulator infrastructure. The battle replay runner, capture and recorder files remain on draft PR #5 for future consumption but must not distract from battle mechanics work.

Latest mechanics source: Amnesia +2 supplemental SpD, Growth independent +1 SpA/+1 SpD with asymmetric stat cap, Psychic secondary-effect minus one supplemental target SpD. No actual in-game damage or stage replay passed. CI success only proves build/startup. Preserve draft PR, save/PC compatibility, and approved user canon.

Resume bounded battle mechanics implementation: (1) Haze resets all active stat stages including supplemental SpD but preserves ordinary status/team-wide Reflect/Light Screen, (2) Transform copies/derives independent Special statistics and stages without modifying persistent records, (3) switch-in stage reset and split-cache integrity, (4) five-turn team-wide screen state and expiry; eventually doubles and verified damage handling. Track emulator replay as external QA dependency, not the active thread's toolchain task.

## BAL-15: Haze stage-only reset (2026-10-10)

Commit `845e6aa5ad67f649f80844cf19d58ccb3392ec30` modifies `engine/battle/move_effects/haze.asm`. The move restores active player and enemy Attack, Defense, Speed and SpA, resets their existing accuracy/evasion and other legacy stat-stage bytes to neutral (7), and additionally restores both battle-only SpD caches from unmodified SpD while setting both independent SpD stages to neutral. It intentionally removes the old Haze side effects which cured target major status and cleared disable/confusion/other volatile flags, bad poison and Reflect/Light Screen. This is a mechanics-source change, not an emulator-proven result.

No persistent Pokémon record sizes changed. Build and in-game checks are required: paired split stages with divergent bases and +6/-6 modifiers, accuracy/evasion, active status unchanged, team screens unchanged, transformed battlers, and switch followup. Keep PR #5 draft. Emulator fixture execution is owned by the separate testing workstream.

## BAL-16: Transform copies independent Special Defense (2026-10-10)

Commit `57ca47222fba26a936804ade3a791114d4dec9ca` extends `engine/battle/move_effects/transform.asm` so Transform copies target's **current** supplemental Special Defense, **unmodified** supplemental Special Defense, and independent Special Defense stage, correctly selecting source/destination for either acting side. The legacy four-stat and stage copy, DVs, species, moves and original transformation flow remain in place. No change to persistent party/box record layout.

This is SOURCE IMPLEMENTATION only. Verify fresh Actions compilation, then assign actual emulator cases to YEL-TEST for player and enemy Transform, opposing divergent SpA/SpD and stage cases, Transform followed by stat changes/Haze, and switch/reversion. Do not claim actual battle verification or merge PR #5 without tests.

## BAL-17: Switching and transformation reversion source audit (2026-10-10)
Source inspection confirms player switch-in through LoadBattleMonFromParty, enemy trainer switch-in through LoadEnemyMonFromParty, and wild entry through LoadEnemyMonData initialize appropriate split Special Attack and independent Special Defense caches and neutral stage. Transform's temporary supplemental caches therefore get replaced at next actual species load; no speculative assembly rewrite needed. Structural guard committed in tests/battle/test_switch_cache_contract.py (3b8b10c), not yet a controlled emulator gameplay test. Next mechanics implementation: five-turn team-wide screen state, expiry, singles/doubles damage reductions. PR #5 remains draft; no claim of in-battle reversion verification.

## BAL-18: Team-wide screen countdown implementation, pending doubles (2026-10-10)

Commits 2922a48 (battle-only timer storage in unused WRAM), db1e30d (screen activation timers), b08360e (new round-completion countdown, battle-start reset, damage reads team timers), and 25299fe (screen recast checks timer, not the per-Pokémon status bit). Reflect and Light Screen each start at five; timers attach to player/enemy side, not current active battler; successful complete rounds decrement them. Noncritical singles damage remains floor(damage/2) through the existing late damage modifier. The new authoritative timer checks persist through normal switching, and expired screens can be recast. Save formats unchanged.

LIMITATIONS / required followup: no real doubles-state designation yet, so approved floor(2*damage/3) for doubles is NOT implemented; do not infer doubles using link-state or trainer-battle flag. Knockout and other early-exit round accounting, stale legacy status flags, shared-team multiple active battlers, and in-game timing must be audited. Builds and emulator damage fixtures required. This checkpoint is source implementation, not a completed screen feature or proof of correctness. Draft PR #5 remains unmerged.

## BAL-19: Screen knockout round accounting and compile fix (2026-10-10)

The prior screen integration failed compilation at head 446e5bb because `engine/battle/move_effects/reflect_light_screen.asm` accidentally defined local `.reflect` and `.playAnim` labels twice; the source build error was confirmed from the Actions development job log. Commit 7717c575 removes the duplicate stale handler fragment. Commit a92c351e adds `TickProjectYellowScreens` at the enemy/player faint-handler entrances so knockout-terminated rounds decrement side screen timers rather than skipping the normal round tail entirely. The two existing normal-completion ticks are unchanged.

Remaining edge cases NOT VERIFIED: escape, forced switching or other interrupted rounds; multi-faint handling; timer semantics on rounds in which screens are first cast; end-of-screen player messaging and stale legacy status flags; doubles team state and floor(2*damage/3) modifier. This incremental fix requires fresh successful compilation and true gameplay assertions before claiming correctness. PR #5 stays draft and unmerged.

## BAL-20: Screen build repair and expiration cleanup (2026-10-10)

At head 32d43b all five Actions failed: linker reported undefined symbols `ReflectLightScreenEffect_.reflect` and `.playAnim`. The previous duplicate-label patch removed required labels, not just redundant code. Commit 46e0c1bd restores the proper Reflect activation arm and one animation handler. Commit 69587dd2 makes `TickProjectYellowScreens` clear each side's legacy screen status bit when its authoritative five-turn timer reaches zero, so expiry no longer leaves those bits set.

Round handling: normal two-action rounds tick once; knockout-ending exits currently tick in faint handlers. Escape and forced switch abort the action path before an ordinary completed-round tick, and must be explicitly reviewed under final battle-turn semantics. No verified true-double-battle state exists on this branch; approved doubles floor(2D/3) screen modifier CANNOT be wired truthfully yet. Do not use wild/trainer/link flags as substitutes. Integration remains BLOCKED on true doubles architecture. Re-run full CI/build and YEL-TEST deterministic fixtures; do not claim success solely on source edits. PR #5 remains draft and unmerged.

## BAL-21: True-double-battle integration contract, cross-PR verification (2026-10-10)

Live GitHub cross-check: PR #11 (YEL-CHALLENGE-001 Viridian Doubles School, head b57e2479) is explicitly documentation-only staging and has no functioning true-double-battle engine. None of the current project-yellow branches inspected expose an established double-format battle-state symbol; do not equate a linked battle, trainer battle, or two sequential enemies with true doubles. The YEL-BAL-002 PR #5 head aa80d40d has five green workflows (CI, clean baseline, dev lab, DMG startup, PyBoy/RGBDS toolchain), establishing successful build/startup only.

Required upstream doubles-engine contract for screens: (a) a single well-defined, publicly referenced runtime battle-format discriminator that distinguishes singles from true 2-v-2; (b) persistent side/team identities shared by both simultaneously active slots and preserved through substitutions; (c) well-defined round boundary exactly once after both sides' permitted actions, including faint/switch/forced replacement; (d) target-side access in damage pipeline to select the right side screen timer; (e) explicit per-target screen application rules for spread moves and critical bypass.

On introduction of that engine contract, modify ApplyProjectYellowScreens to use floor(2 * pre-screen damage / 3) for doubles and floor(damage / 2) for singles, with critical hit bypass in both. Use a 16-bit-safe implementation that does not overflow when doubling damage; do not use an approximated 8-bit multiplier. Validate max/min damage, critical hits, simultaneous moves, expiry and shared-team switching. Until that dependency lands, DOUBLE SCREEN REDUCTION REMAINS NOT IMPLEMENTED. Keep PR #5 draft/unmerged.

## BAL-22 / YEL-DBL-001: First executable doubles-format foundation (2026-10-10)

Cross-repository check: Viridian School draft PR #11 (current head b7bed8c1) is implementation staging, not a functioning two-active-slot engine. True doubles engine does not presently supply battle format / paired slots in the current mainline or BAL implementation.

The first *code* dependency has been introduced on BAL draft PR #5: commit b43c8312 repurposes one byte of existing unused battle WRAM into `wBattleFormat` (0 singles; 1 reserved for correctly initialized true doubles); no WRAM offsets or persistent party/PC save size change. Commit aa7a531d clears `wBattleFormat` to singles at every StartBattle, so existing regular battles do not leak a stale doubles setting. This is the format discriminator, NOT functioning doubles: code never sets it to doubles until the engine actually initializes the second active Pokémon on each team.

Follow-on true doubles work must implement and verify actual simultaneous two-slot player and enemy battle records, target selection/redirection, move ordering across four battlers, faint and replacement dispatch, move effect status per slot, end-of-round semantics, and set `wBattleFormat=1` **only after** valid setup. Integration with YEL-CHALLENGE-001 gates Viridian gift/tutorial behind the real engine. Once established, apply the approved floor(2D/3) screen damage modifier via defending team identity and test it against singles (floor(D/2)) and crit bypass. This checkpoint is source foundation only; build/emulator verification pending and PR #5 remains draft/unmerged.

## BAL-23 / YEL-DBL-001: Second active battler working-record reservation (2026-10-10)

Committed `ae4bfc3d`: `ram/wram.asm` adds `wDoublesPlayer2` and `wDoublesEnemy2` as full `battle_struct` records, with nickname, independent unmodified Attack/Defense/Speed/Special snapshots, independent current and unmodified SpD, stat stages including supplemental SpD, three battle status bytes, party slot and selected move. Both are in the pre-existing 1300-byte overworld/scratch WRAM0 UNION via NEXTU; ASSERT constrains allocation <=1300 bytes. No new party/box/SRAM or serialized fields, and no existing WRAM0 addresses shifted. Working records currently have NO initialization, actual battle activation, target routing, turn scheduler or UI use; do not call doubles implemented.

HIGH-PRIORITY MEMORY LIFETIME BLOCKER: the overlaid union also aliases `wOverworldMap`, temporary pictures and printer scratch. Before connecting these records, audit whether overworld map/tile drawing and picture decompression write to this scratch region during battle; preserve/reload required overworld state on returning to map. Scratch alias is reserved pending memory-lifetime proof, not verified conflict-free. New symbols and macro layout must pass RGBDS compile and linker. Follow-up engine tasks: accessors, initialization from existing party records, explicit active slot identities, faint/replacement transitions, four-mon targeting/priority, render/audio interactions and lifecycle checks. Keep PR #5 draft until real emulator verification.

## BAL-24 / YEL-DBL-001: secondary party-data staging and scratch lifetime audit (2026-10-10)

Previous secondary-record allocation at ae4bfc3d compiled and all five CI/dev/boot/toolchain jobs passed at head 08ac236a. This validates linker layout, not scratch lifetimes. Source memory audit confirms these records overlap `wOverworldMap`, `wTempPic`, printer tile buffers and other image/map scratch via preexisting 1300-byte WRAM0 UNION. Actual nested battle calls can decompress graphics and display sprites, making this overlap a potentially live corruption risk; DO NOT ENABLE `wBattleFormat=1` or call the staging routines from normal gameplay before verifying and replacing the memory allocation with safe, battle-exclusive storage. Overworld return also requires any temporary map state be rebuilt or otherwise preserved.

New source-only staging implementation: `engine/battle/doubles_secondary.asm` commits e55d75e8 and 513a1a18, included from main.asm at 33d82717. Input A is a zero-based party slot for either side, calls the established party-record offset-copy primitives, snapshots legacy unmodified attack/defense/speed/special into separate battle-only fields, stages nickname, initializes stages to neutral 7 and battle status to 0. Current supplemental SpD is copied from the legacy Special as a temporary fallback, NOT calculated from the target species' independent base; this must be replaced before actually enabling a real doubles battle. No persistent save/party/box formats changed. There are deliberately NO call sites from gameplay, and no active doubles yet. Assembly of new staging routines pending CI outcome at write time.

Followups before using these routines: resolve scratch-lifetime conflict (e.g. use truly battle-exclusive reserved space); correctly calculate independent SpD including species bases, DVs, stat XP; register and verify party-index ownership, selected moves and second HP; initialize enemy/player second slots; wire four-target scheduler and screen format; verify via controlled in-game fixtures. PR #5 remains draft/unmerged.

## BAL-25: Storage and ROM bank blocker discovered (2026-10-10)

Actual job logs for staging commit 33d82717 showed RGBDS linker error: Battle Core section exceeded the 0x4000-byte bank by 0x32. Commit 7b127c41 moved inactive doubles secondary routines to bank10 via main.asm; no gameplay call sites currently exist, and any future caller must use a far call / correct bank switch, not an ordinary call. The new build is pending at documentation time.

Crucially, NO SAFE LIVE SECONDARY MEMORY ALLOCATION HAS BEEN ESTABLISHED. The proposed wDoublesPlayer2 and wDoublesEnemy2 symbols currently overlay wOverworldMap / wTempPic and printer/graphics scratch. Source audit proves this overlap; absence of a real conflict has *not* been established. Do not set wBattleFormat to doubles and do not invoke the routines until a storage reservation with provably disjoint lifetime or protected extra cartridge RAM exists. Do not silently overwrite saved boxes or add SRAM writes. Code-level fallback to legacy Special is not independent SpD; independent derivation must use the target's species base, DVs and stat experience before enabling. Current state: structural records + inactive unverified staging ONLY; not a complete four-active battle engine.

## BAL-26: Safe-memory audit result and fail-closed gate (2026-10-10)

All five Actions passed at preceding head d4f41f91, confirming the relocated inactive secondary-stage code builds and boots. The proposed wDoublesPlayer2/wDoublesEnemy2 records live in a NEXTU arm of the same WRAM0 union as wOverworldMap, wTempPic and printer/graphics buffers. This is physical aliasing, **not** independent battle memory; basic build success does not make it lifetime-safe. The SRAM layout also contains persistent Hall of Fame, saved gameplay data and all storage boxes. It is not acceptable to repurpose any of these without explicit, separately verified mapper/save format migration and SRAM bank isolation.

Architectural disposition: the current overlay remains PROTOTYPE ONLY; do not set wBattleFormat=1 or call the staging routines. To enable actual simultaneous four-mon battles, first allocate dedicated, non-aliased live storage. Candidate engineering path is a cartridge mapper and extra-SRAM-bank migration supporting explicit isolated volatile battle banks, but that requires cart capability confirmation and save compatibility/versioning tests. Another path is a rigorously proven RAM-lifetime partition with saved/restored overworld and no other overlapping battle calls; this is not established. Do not label either path implemented.

Commit bb4270bc adds tests/battle/test_doubles_memory_gate.py, a source regression gate documenting the scratch overlay and ensuring core has no call sites to the secondary staging helpers. It does not prove RAM lifetime or gameplay. Independent second-slot SpD derivation and double-battle activation remain BLOCKED pending safe storage. Do not merge PR #5.

## BAL-27: Dedicated fifth MBC5 SRAM bank reservation (2026-10-10)

Audit of Makefile confirmed MBC5+RAM+BATTERY with original RAM header $03 (32 KiB, four 8-KiB banks). Old sram.asm has existing sprite buffers/Hall of Fame, game SAVE and the two boxes sections occupying this existing mapper space. New source commits 169e13c1 and 11d9d0bb reserve a completely separate `SECTION "Doubles Battle Workspace", SRAM, BANK[4]` sized to the secondary-record footprint and set header RAM size $04 (128 KiB) for a target cartridge capable of >=5 SRAM banks. The first four bank addresses and serialized record lengths remain unchanged; however, the *external save-file / hardware RAM-size compatibility is NOT VERIFIED* and some emulators may represent the SRAM file as larger. Need test migrating an old 32 KiB save to new 128 KiB RAM, back up saves, and assess physical-cart availability.

Crucial: Existing `wDoubles*` aliases still overlay WRAM0 temporary graphics/map scratch, and inactive staging helpers still point at those aliases. New `sDoublesSecondaryBattleData` is a reserved safe address, not automatically the live backing store. Must implement correct mapper enable/bank save/restore, copy/staging to dedicated bank4, and safe access/active-slot synchronization before turning on doubles. NEVER assume SRAM is always enabled or selected, or leave bank4 selected on return to ordinary engine. SRAM operations must preserve existing box/save banks and disable RAM as appropriate. Build checks are structural only until actual emulator save migration and data-isolation fixtures pass. Do not merge or enable wBattleFormat=1.

## BAL-28: Controlled bank-4 transfer and emulator isolation test (2026-10-10)

Commit e52b5510 adds CopyDoublesScratchToDedicatedSRAM and CopyDoublesDedicatedSRAMToScratch in engine/battle/doubles_secondary.asm. API inputs B=previous SRAM bank (0..3), C=previous SRAM enabled (nonzero) or disabled (zero). It checks B before enabling SRAM, saves registers, selects MBC5 SRAM bank 4, transfers the workspace data, restores the prior bank, and disables SRAM only if caller indicated it had been disabled. Because MBC5's bank/enable registers cannot be read back, the API **cannot discover** previous state; caller must provide accurate state and exclusive ownership. It has no active gameplay call site. The existing WRAM graphics scratch source/destination remains unsafe to use while a battle is running.

Commit 1c4b3bf9 adds PyBoy test_doubles_sram_isolation.py; commit 3a50629e adds the test to the YEL-BAL-002 toolchain CI. It boots an isolated copy of the 128 KiB-MBC5 ROM, snapshots every byte in original SRAM banks 0..3, writes patterns to bank 4, then verifies original banks are byte-identical. The test exercises mapper bank isolation, **not the new assembly API**, real saved Pokémon, resume/reload, or old 32 KiB .sav compatibility. Check job output before claiming the test passes. Before enabling doubles: provide safe active-record backing and runtime bank-state ownership, invoke the assembly API in a controlled emulator fixture, verify context restored across every failure path, and run legacy-save migration and Pokémon integrity fixtures. Draft PR #5 remains unmerged.

## BAL-29: SRAM isolation evidence and legacy-save acceptance boundary (2026-10-10)

At head ea2dc98521d857f3be40a154a3245b78b6bee1dd, all five GitHub workflows completed successfully. The toolchain job log explicitly reports `PASS: emulator mapper bank-4 writes did not modify banks 0..3`; this is concrete isolated PyBoy mapper evidence, not an assembly-routine execution or saved-Pokémon persistence test. Commit 0b859c03 adds an explicit bank-2 -> bank-4 -> bank-2 selection round-trip assertion to that isolated emulator probe; rerun pending.

Blocking legacy-save matrix: load a known-good 32KiB .sav from original 4-bank build in an isolated copy of the 128KiB build, verify trainer/party/current box and saved boxes and checksums; save in the larger configuration, fully stop/restart emulator, verify all bytes and game-level records remain stable; verify hardware/cart migration as a separate concern. The test must fail closed with missing fixture, not synthesize a fake user save. No authorized legacy save fixture is present in this PR.

The bank-4 read/write helpers still copy via unsafe shared WRAM scratch, and the code has no live battle caller. Bank switching must be coordinated with all other SRAM users. Four-Pokémon activation, assembly routine restoration proofs and old-save interoperability remain unverified; do not merge PR #5.

## BAL-30: Legacy-save test harness and actual assembly execution gate (2026-10-10)

Commit 42f213e6 adds tests/battle/test_legacy_save_compatibility.py, which REQUIRES a real 32768-byte legacy save fixture as a CLI argument. In an isolated temporary emulator directory it loads that save under the MBC5 128KiB ROM, snapshots all 4 old SRAM banks, writes only the isolated bank4 sentinel, then stops and checks the first 32768 bytes of the persisted SRAM image are identical to the original; the real source fixture is never modified. It prints only a bounded raw bank-preservation claim: no Pokémon record parser, gameplay save menu, resumed battle, or real Pokémon checksum assertions yet. NO LEGACY SAVE FILE was available here; thus this migration test has NOT BEEN EXECUTED. Commit ad176afc adds syntax check and fixture guard review to CI, not fake compatibility success.

The controlled `CopyDoublesScratchToDedicatedSRAM` / `CopyDoublesDedicatedSRAMToScratch` assembly is still uncalled. The current PyBoy mapper test demonstrates SRAM bank isolation and bank selection at the emulator MMIO level, not CPU execution of those two routines or previous RAM-enable-state restoration. A proper fixture must arrange controlled CPU execution of each entry point with B=known prior bank and C=known enable state, check exact transferred bytes plus return carry and register contract, verify bank 0-3 unchanged, compare behavior for enabled/disabled initial SRAM and invalid-bank reject, and verify no shared-scratch lifetime conflict. No such fixture has passed. Keep PR #5 draft and live doubles disabled.
