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
