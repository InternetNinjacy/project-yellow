# YEL-TEST-003 — Developer Graphics Lab

## What is implemented

Phase 1 reuses the engine's existing Red's House 1F as a DEBUG-only graphics lab rather than creating a new production map. In `_DEBUG` builds, the original Mom object is represented by the authentic Yellow Bulbasaur graphics with `WALK / ANY_DIR`. Normal `pokeyellow.gbc` preserves Mom and the original map. No canonical story alteration is implied. This deliberately exercises the normal indoor dynamic sprite loader, separate from the older Pallet Town outdoor fixture in PR #2.

## Access

Run `pokeyellow_debug.gbc`. At the title screen, press **Select** to enter Yellow's existing debug menu, select **DEBUG**, and begin the debug new game. The normal debug start enters the protagonist's house upstairs; the lab station is downstairs in Red's House 1F.

## Deterministic emulator verification

`scripts/yel_dev_lab_verify.py` is the YEL-TEST-003 visual verifier. It does not teleport or patch the active map. After selecting the existing DEBUG new-game path, it reads RGBDS WRAM symbols and uses PyBoy savestates to explore the small upstairs room until an actual player movement crosses the real warp into Red's House 1F.

Inside the lab it checks:

- current map is Red's House 1F;
- object 1 is really `SPRITE_BULBASAUR` in both sprite-state structures;
- the exact compiled 192-byte Bulbasaur 2bpp stream exists in live VRAM;
- live shadow OAM references Bulbasaur's loaded tiles;
- disabling OBJ rendering reveals both changed sprite pixels and unchanged background pixels inside the Bulbasaur OAM bounds, validating visible sprite/background transparency behavior;
- `WALK` movement status and at least two object positions are observed;
- all four documented engine facings (down, up, left, right) occur naturally and are captured as native 160×144 screenshots.

The CI still builds both release and DEBUG ROMs. Release isolation remains a required gate. The visual verifier's result is not considered a pass until its GitHub Actions run and archived report/screenshots are inspected.

## Still outstanding after the Bulbasaur visual gate

- verify graphics state after opening/closing actual NPC text;
- add a DEBUG-only on-demand species selector instead of loading every species at once;
- integrate DEX-002 Ivysaur as a distinct sprite ID and graphics pointer using its approved indexed source package;
- repeat the same engine verification for Ivysaur;
- test supported SGB/GBC compatibility palette behavior separately;
- archive verified reports/screenshots into permanent DEX folders and synchronize Drive authorities.

## Permanent rules

- Every species retains one permanent Drive asset folder and status record.
- Never load 151 sprites simultaneously; load only the selected species needed by the test station/map.
- Runtime palette tests for DMG, SGB and GBC compatibility modes are separate gates.
- Artwork approval, format validation, ROM integration, successful compilation, emulator verification and physical-hardware verification remain separate statuses.
- Normal builds must exclude DEV LAB behavior.
