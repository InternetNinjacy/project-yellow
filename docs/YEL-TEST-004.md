# YEL-TEST-004 — Compatible Hardware Palette Verification

Goal: retroactively verify authentic color-capable hardware presentation of DEX-001 Bulbasaur and DEX-002 Ivysaur. Their prior DMG art approval and master merges remain locked.

## Hardware
Pokemon Yellow handles CGB palettes through home/cgb_palettes.asm and hOnCGB, and SGB palettes separately through engine/gfx/palettes.asm. Overworld palette selection is map/tileset-related; do not assume per-species individual overworld palettes from battle species color tables.

## Status
- DEX-001 Bulbasaur: DMG QA approved and merged PR #4. GBC PENDING; SGB PENDING; physical hardware PENDING.
- DEX-002 Ivysaur: DMG QA approved and merged PR #7. GBC TEST IN PROGRESS; SGB PENDING; physical hardware PENDING.

## Current CI gate
scripts/yel_test_004_gbc_ivysaur.py runs PyBoy cgb=True, verifies the engine hOnCGB flag, captures a native 160x144 screenshot, counts actual non-grayscale screen pixels, and checks the preexisting Ivysaur VRAM/OAM/movement and dialogue reload contract.
Non-grayscale image pixels prove a GBC-mode rendering path, not unique colors assigned to Ivysaur or exact real LCD colors. Keep sprite-art approval separate from hardware confirmation.
The DEBUG lab currently shows Ivysaur only. DEX-001 needs its own independent GBC capture; do not label Ivysaur evidence as Bulbasaur.
Super Game Boy screenshots require an SGB-capable emulator/hardware; not provided by the present PyBoy CI workflow. Static SGB palette packets are not display evidence.

## Exit criteria
Independent DMG, GBC, and SGB screenshot/report evidence for each species; GBC palette data source verified; unchanged normal release behavior and clean build; ROM SHA and test commit recorded; archive to corresponding Drive folders; records synchronized. Hardware verification is separately tracked.
