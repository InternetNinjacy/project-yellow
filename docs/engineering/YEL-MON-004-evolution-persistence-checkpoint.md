# YEL-MON-004 — Raticate → Rattaking evolution and SAVE/CONTINUE checkpoint

## Verified
- Four Poison Fang / Crunch controller-driven PyBoy proc/no-proc fixtures passed on run [38104385666](https://github.com/InternetNinjacy/project-yellow/actions/runs/38104385666). They were verified prior to the DEBUG New Game fixture additions.
- A DEBUG-only fifth party slot creates an actual Raticate (internal species $A6 = 166) at level 35 with **AddPartyMon**, without PyBoy WRAM writes.
- The test-only Raticate experience is set by DEBUG ROM code to `$00B63F` = 46,655, one point before medium-fast level 36 (46,656). An actual battle must still award XP and trigger evolution.
- DEBUG initial party duplicate-registration bug discovered: `PrepareNewGameDebug` is entered twice. Fixed `SetDebugNewGameParty` table pointer preservation across AddPartyMon and made party setup idempotent. Controller startup now sees exactly five entries, Raticate in slot 5 with level 35.
- Source evolution contract verifies Rattata → Raticate at level 18 and Raticate → Rattaking at level 36, species and dex ID, plus Dark base stats.
- The latest DEBUG ROM assembles successfully; startup and evolution source contract checks pass. No observed wild encounter or post-battle evolution yet.

## Reproducible blocker
- Legitimate DEBUG New Game state saved after the controller intro sequence is on Pallet Town map ID 0, coordinates (5,6), directly outside the player's house according to map warp data.
- PyBoy directional holds of 24, 72, and 180 frames, plus START/A/B trials, do not change coordinates or open menu. The overworld route search finds only one position.
- During held button events, read-only HRAM values `hJoyPressed`, `hJoyHeld`, `hJoy5`, and `hJoy7` remain zero. `wJoyIgnore`, `wWalkCounter`, and `wMovementFlags` remain zero; `wCurrentMapScriptFlags` is $60 (both map-loaded bits).
- CPU PC sampled at 0x4A0E at PyBoy frame boundaries resolves to ROM bank 1 OAM preparation, a normal frame-boundary routine. **Do not interpret this PC sample as proof of an infinite CPU loop.**
- The bug is currently an input polling / post-special-warp transition problem, not a confirmed collision or controller-duration problem. Avoid emulator memory modification as a shortcut.

## Required gameplay gate, NOT YET PASSED
1. Instrument joypad polling and post-DEBUG-init transition to identify why held controller buttons never reach hJoyHeld.
2. Repair start-of-overworld input processing and reproduce a controller-only walk into Route 1 and an actual wild battle.
3. Make level-35 Raticate participate and earn one or more EXP, verify level 36 Rattaking evolution, party species, six stats, four moves and Pokédex seen/owned bit. Reconcile DebugSetPokedexEntries pre-populating the new dex bit so newly acquired evidence is meaningful.
4. Perform in-game SAVE using controller inputs; quit PyBoy and start fresh with the cartridge SRAM; CONTINUE and compare party raw record, trainer ownership, level, EXP, stats, moves, and box storage.
5. Preserve all controller traces, savestates, ROM SHA, WRAM snapshots, and source test outputs. Do not merge before all pass.

## CI
See [current draft PR #13](https://github.com/InternetNinjacy/project-yellow/pull/13).
- `tests/battle/probe_debug_controller_startup.py`: startup fixture and evidence.
- `tests/battle/probe_rattaking_overworld_route.py`: exploratory route search, currently **expected to fail** until input issue fixed.
- `tests/battle/test_rat_move_replay.py`: four-case move battle proof, previously passed.
- `tests/battle/check_rattaking_evolution_contract.py`: source-only gate, does not prove gameplay evolution.

**Current status: blocked on real overworld controls, NOT verified as evolution or persistence complete.**

## 2026-10-11 input-path investigation — verified new evidence
- A power-on replay of the actual startup controller trace, followed by a continuous 18-step UP hold sequence (60 frames held, 20 released) **never changed** Pallet Town map/coordinates from (0,5,6). This also occurs without loading the saved .state, so savestate restoration alone is not the cause.
- DEBUG-party startup is valid: five members including level-35 Raticate internal ID $A6; level-35 EXP fixture $00B63F; no battle/evolution observed.
- Read-only PyBoy CPU hooks while trial buttons are held recorded 1626 calls to `ReadJoypad_`, 813 calls to `_Joypad`, and 813 calls to `JoypadOverworld`. The map logic is actively polling; it is **not a nonexecuting game loop**.
- At the polling hooks, the JOYP hardware register read $CF. Held UP / START trials show `hJoyInput`, `hJoyLast`, `hJoyHeld`, and `hJoyPressed` all zero. `hDisableJoypadPolling`, `wStatusFlags5`, and `wJoyIgnore` are zero, ruling out the standard joypad-disable paths.
- CPU register snapshots at PC $4A0E (bank 1 `PrepareOAMData.loop`) show C=3 and changing HL values, so the CPU **is progressing** through sprite drawing. Do not call it an infinite loop.
- Latest unsuccessful route probe: [run #38129216504](https://github.com/InternetNinjacy/project-yellow/actions/runs/38129216504). Latest JOYP polling hook trace: [run #38129094784](https://github.com/InternetNinjacy/project-yellow/actions/runs/38129094784). No successful route, encounter, evolution, or SRAM replay yet.
- Suggested next diagnostic: compare JOYP input sampling in an actual working DEBUG Fight menu (same PyBoy process and ROM) against `JoypadOverworld` to find why the hardware button state is not delivered in overworld mode. Do not write WRAM or fabricate savestates.

## 2026-10-11 verification closure — all required gameplay gates PASSED

- [GitHub Actions #38134106846](https://github.com/InternetNinjacy/project-yellow/actions/runs/38134106846) completed the entire DEBUG controller fixture workflow, including the fail-closed final evolution/SAVE-CONTINUE gate, with SUCCESS.
- Verified power-on DEBUG party setup: fifth slot Raticate (internal $A6), level 35, one EXP below level 36. A game-controller trace reached Route 1 ($0C) and a wild battle.
- Verified Raticate participates, gains real battle EXP, reaches level 36, and evolves to Rattaking (internal $BF / decimal 191).
- In the verified evolved save state, Rattaking is level 36 with EXP 46663, moves [99,166,162,167], and the expected party structure. Pokédex owned/seen includes its registered entry; note DEBUG startup pre-populates the Pokédex so independent acquisition-bit toggling is not shown by this fixture.
- In-game SAVE used controller inputs. A separately initialized PyBoy loaded the real cartridge .ram and used CONTINUE. The full compared before/after record matches exactly: party species, Pokémon raw struct, OT, nickname, stats, moves, EXP, Pokédex seen/owned, current box number/count and box data SHA-256. Marker `artifacts/rat-persistence/persistence_gate_passed.json` reports `passed: true`; ROM SHA-256 `7ebf1af6403c7f14e2403bc3e3b35c8b643c6febb35898dfc783be6607787d7b`, SRAM SHA-256 `5ee793cc5179bede3f23695e051c999209822b3b2ee4ee0aa0bed777c8b1fe61`.
- Poison Fang and Crunch each have genuine proc and no-proc PyBoy replays, all four passed again in the same workflow.
- Critical repairs: overworld test must use PyBoy `button_press()` / `button_release()` for continuous direction holds; DEBUG New Game sets `EVENT_FOLLOWED_OAK_INTO_LAB` so Oak's normal story gate does not interrupt the fixture. Both are test-only behavior.
- Persistence test must not compare `wBoxMonCounts` because that symbol is a volatile `NEXTU` alias; it now verifies persistent `wBoxCount`, `wCurrentBoxNum`, and the full `wBoxDataStart..wBoxDataEnd` digest.
- **Status: gameplay evolution and fresh SAVE/CONTINUE persistence validated.** PR remains draft; merge only after final code review, checking all approved TM34 world-item placement and other Project Yellow integration issues outside the verified family tests.

## 2026-10-11 THREAD RETIREMENT — CURRENT AUTHORITATIVE HANDOFF

**Conversation status:** This Project Yellow rat-family engineering thread is RETIRED at user request. Work continues in a NEW thread only on user instruction. **Do not resume coding, CI runs, or merge action as part of thread retirement.** Draft PR #13 remains the implementation handoff.

**Supersession:** Earlier sections of this cumulative file describe real, previously observed blockers. They are historical. The later 2026-10-11 verification closure above supersedes the old "overworld input blocked" and "no evolution/SRAM evidence" statements. Do not mistake these historical findings for the current state.

**Verified engineering outcome:** GitHub Actions [run #38134106846](https://github.com/InternetNinjacy/project-yellow/actions/runs/38134106846) passed the genuine level-35 Raticate → level-36 Rattaking controller-played evolution, Pokédex checks (with DEBUG pre-population caveat), in-game SAVE, fresh PyBoy SRAM-backed CONTINUE, full party Pokémon/OT/nickname/stat/move/EXP and box integrity comparison, and Poison Fang/Crunch proc and no-proc (four cases). ROM SHA-256 `7ebf1af6403c7f14e2403bc3e3b35c8b643c6febb35898dfc783be6607787d7b`; SRAM SHA-256 `5ee793cc5179bede3f23695e051c999209822b3b2ee4ee0aa0bed777c8b1fe61`. Do not imply probability distribution is empirically established by four examples; source RNG logic is separate evidence.

**Implementation scope still requiring human review / resolution before merge:** final Rattaking sprite art, cry/dex flavor placeholders, any incomplete per-family learnset/TM compatibility reconciliation, real TM34 Poison Fang world-item placement in Safari Zone (exact tile unresolved), world encounter integration and all other changed-table references. These are not established complete by the successful narrow battle/persistence gate. Audit the latest branch HEAD and CI, because it may differ from the archived verified ROM SHA. Do not merge merely because tests passed.

**Framework/reporting policy for next thread:** Begin from this handoff, the Work Registry, Project Charter and CORE-003/004; use status badges, a progress bar and concise explanations for every multipart engineering task/progress request. Always end each progress report with **Next Step**, stated concretely. Separate source-implemented, compiled, controller/emulator verified, visual/user-approved, and merged statuses. Don't run background/asynchronous jobs without an actual scheduling mechanism, and do not imply a CI run succeeded unless checked. No need to repeat previously passed battle/evolution/SRAM work unless source changes warrant regression.

**Immediate next engineering milestone (for the new thread, not this one):** Inspect PR #13's current HEAD and required CI, perform a gap audit against the approved YEL-DEX-001 rat-family contract, inventory placeholder artwork and Pokédex content, locate/implement the approved Safari Zone TM34 item without fabricating tile placement, verify all five Dark move retypes and TM/HM eligibility, run focused regressions, and prepare a documented merge-readiness decision while retaining draft status until approved.


## THREAD RETIREMENT HANDOFF — 2026-10-11
Thread retired at user request. Do not execute further implementation until a new user-directed thread.
Latest verified milestone: legitimate controller-driven Route 1 (map $0C = 12) wild encounter at (7,29), with fifth-party level-35 Raticate $A6 and opponent wild Rattata $A5. Evidence GitHub Actions run 38131270007.
PyBoy overworld input fix: button() auto-released after a single frame; use button_press() and button_release() for held movement. DEBUG-only startup also sets EVENT_FOLLOWED_OAK_INTO_LAB so Oak's script no longer blocks Route 1.
Earlier Poison Fang and Crunch four-case tests passed in run 38104385666. Subsequent combined workflow runs included failed move-fixture collectors: historical success is not proof of passing current HEAD.
Latest new unverified test: tests/battle/probe_rattaking_evolution_battle.py, drafted to switch the fifth-party Raticate into the real Route 1 wild battle. Its own CI run, success, and integration have NOT been verified.
NOT DONE: Raticate battle switch, real level-36 EXP gain, Rattaking evolution, six stats/moves/Pokédex proof, actual SAVE, fresh CONTINUE, exact record/SRAM/box comparison.
Keep PR #13 draft and feature branch active. No merge approval.
Resume in new thread: inspect latest GitHub HEAD/CI; validate new evolution-battle probe, integrate and run controller replay; only then develop post-evolution and persistence checks.
