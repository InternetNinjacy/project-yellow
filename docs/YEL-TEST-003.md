# YEL-TEST-003 — Developer Graphics Lab (first implemented station)

## What is implemented

This is **phase 1**, a test-only room using the engine's already existing Red's House 1F, not yet a newly mapped laboratory. In `_DEBUG` builds, the original Mom object is temporarily represented by the native Yellow Bulbasaur graphics with WALK/ANY_DIR. It retains its original dialogue for now. Normal `pokeyellow.gbc` preserves Mom and the original map. No canonical Pokémon content or story alteration is approved. The object deliberately exercises **indoor dynamic sprite registration**, unlike the separate test-only Pallet Town outdoor prototype in PR #2.

## Access

Run `pokeyellow_debug.gbc`. At the title screen, activate the existing Yellow debug menu with **Select** and choose **DEBUG**. Existing debug new-game setup allows bypassing the full normal introduction and starts in the protagonist's house, allowing you to find the Bulbasaur object on the ground floor without obtaining Bulbasaur in the story. Controls and launch sequence should be confirmed against emulator captures, not assumed proven.

## Tests still to build

The CI currently validates that both ROM modes compile and that the debug ROM boots in PyBoy DMG emulation. A title-screen smoke pass alone does **not** verify that the debug menu was used, that the player entered the test room, that the Bulbasaur object rendered, or that it changed direction. Add a scripted or savestate-based reliable lab-entry path and actual screenshot/OAM/VRAM checks. Then add a dev-only species selector and optionally a dedicated new map. Do not mark either Pokémon ENGINE VERIFIED until actual on-screen evidence exists.

## Permanent rules

- Every species retains one permanent Drive asset folder and status record.
- Never load 151 sprites at once. Select one species and load only its native graphics for the intended map/object context.
- Runtime palette tests for SGB and GBC compatibility modes are separate gates.
- Ivysaur requires a controlled integration of its actual 16×48 asset, distinct sprite ID, pointer/bank registration and emulator screenshots before a pass.
- Normal build excludes all DEV LAB object changes by preprocessor flag; CI compiles both build modes to prevent accidental leakage.
