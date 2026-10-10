# YEL-TEST-004 — Compatible Hardware Palette Verification

Goal: retroactively verify authentic color-capable hardware presentation of DEX-001 Bulbasaur and DEX-002 Ivysaur. Their prior DMG art approval and master merges remain locked.

## Hardware
Pokemon Yellow handles CGB palettes through home/cgb_palettes.asm and hOnCGB, and SGB palettes separately through engine/gfx/palettes.asm. Overworld palette selection is map/tileset-related; do not assume per-species individual overworld palettes from battle species color tables.

## Status
- DEX-001 Bulbasaur: DMG QA approved and merged PR #4. GBC PASS (PyBoy CGB, run 38004880489); SGB PENDING; physical hardware PENDING.
- DEX-002 Ivysaur: DMG QA approved and merged PR #7. GBC PASS (PyBoy CGB, run 38004880489); SGB PENDING; physical hardware PENDING.

## Current CI gate
scripts/yel_test_004_gbc_ivysaur.py runs PyBoy cgb=True, verifies the engine hOnCGB flag, captures a native 160x144 screenshot, counts actual non-grayscale screen pixels, and checks the preexisting Ivysaur VRAM/OAM/movement and dialogue reload contract.
Non-grayscale image pixels prove a GBC-mode rendering path, not unique colors assigned to Ivysaur or exact real LCD colors. Keep sprite-art approval separate from hardware confirmation.
The DEBUG lab currently shows Ivysaur only. DEX-001 needs its own independent GBC capture; do not label Ivysaur evidence as Bulbasaur.
Super Game Boy screenshots require an SGB-capable emulator/hardware; not provided by the present PyBoy CI workflow. Static SGB palette packets are not display evidence.

## Exit criteria
Independent DMG, GBC, and SGB screenshot/report evidence for each species; GBC palette data source verified; unchanged normal release behavior and clean build; ROM SHA and test commit recorded; archive to corresponding Drive folders; records synchronized. Hardware verification is separately tracked.

## Verified GBC emulator evidence — 2026-10-09

- GitHub Actions run: https://github.com/InternetNinjacy/project-yellow/actions/runs/38004880489 ; all four associated workflows SUCCESS at commit 9aa959d11cb5489458507352ccc155e7474f2605.
- Separate real DEBUG ROM fixtures: Ivysaur `41518d25cd042c0ed2c198c98148e1f88ad6f72974a5cb557c6efb8d6073d115` and Bulbasaur `88f1e7a1e370b65c0bde53bd234aa9faa4af200ff804ad2017a4201cfc7d1105` (SHA-256). Bulbasaur-only DEBUG lab substitution occurs in CI workspace after original release and Ivysaur verification; source repository `master` and normal release map remain unchanged.
- Both: `ENGINE_VISUAL_PASS` in GBC-mode PyBoy, `hOnCGB` TRUE, exact 192-byte VRAM sprite match, four facing states with OAM, walking, transparency, and actual TV text-close sprite reloading.
- Ivysaur: 4 unique RGB screen colors and 4,390 non-gray pixels in post-dialogue screenshot.
- Bulbasaur: 4 unique RGB screen colors and 4,389 non-gray pixels in post-dialogue screenshot.
- Three distinct full-frame facing PNGs for each run (four facing states verified). The pair of duplicate full screenshots do not independently disprove the directional sprite state; the sprite shape was previously user-approved in DMG. Full-frame comparison does not isolate sprite from background or position.
- Evidence copied to both permanent Drive species folders: Bulbasaur https://drive.google.com/file/d/1VYalNpqHaOJpNXGLRG4kZFL35YRJrQ1m/view and Ivysaur https://drive.google.com/file/d/1KZWVkyazgA_QpZECTUNxCkbK0krUcF_D/view .
- This verifies game-specific GBC compatibility-mode rendering. It does NOT prove individually assigned species colors (overworld remains map palette dependent), calibrated original LCD colors, SGB appearance or physical hardware behavior.

## Remaining gate

Obtain separate authentic SGB-renderer screenshot/packet behavior proof for both species. Keep PR draft and milestone partial until SGB coverage and final review, or explicitly split out a GBC-only verified PR.

## Planned SGB test implementation

Use an actual SGB-capable renderer, rather than PyBoy's CGB mode, for the remaining gate. SameBoy is an appropriate candidate because it explicitly supports `sgb-ntsc`, `sgb-pal`, and `sgb2` hardware models (https://sameboy.github.io/features/). A test must confirm the ROM's SGB handshake/packet path, real overworld palette assignment, and each species' native in-game screenshot under SGB emulation. Select a reproducible model/version, archive screenshots and emulator settings, then compare map palette behavior to the DMG/GBC baselines. Do not count untested source packet analysis as an SGB PASS.

## Actual SameBoy Super Game Boy renderer: boot smoke (2026-10-09)

- A reproducible GitHub Actions SGB smoke job was implemented as .github/workflows/yel-test-004-sgb.yml, building pinned SameBoy v1.0.3 from source because the Ubuntu Actions environment does not provide its apt package, and launching its actual `--model sgb-ntsc` under Xvfb.
- Run 38006042395 passed SameBoy initialization, SGB model startup, and an authentic Pikachu SGB border screenshot. Run 38006382886 passed staged console-input navigation/screenshots. Run 38006611551 passed staged shots with later entry timing; visible screenshots still show startup/Pikachu intro and not in-map species.
- SGB archive https://drive.google.com/file/d/13ZBI9ZtTOwCp2gPacSc404jj2SYMrhQb/view is stored under QA & Integration Reports, not misrepresented as evidence for Bulbasaur or Ivysaur sprite colors.
- Next engineering step is a deterministic method of getting into the DEBUG lab on this actual SGB emulator, then capture the on-screen Bulbasaur and Ivysaur frames separately, verify palette behavior and SGB data packets. This gate is NOT completed by the boot smoke; do not mark either species SGB-verified or merge PR #8 on this basis alone.

## SGB DEBUG navigation checkpoint (2026-10-09)

- Actual SameBoy SGB-NTSC screenshot from GitHub Actions run 38010740129 proves the existing DEBUG menu progression reached Red's House upstairs (the player, Pikachu and second-floor layout are on screen). Earlier startup-only checks had not reached the gameplay map.
- The current unresolved navigation is the upstairs stairs/warp into Red's House 1F where the DEBUG Ivysaur station is installed. We added arrow-key steps and additional before/after screenshots in the SGB CI job. The newest run must be inspected before recording this warp as successful.
- The SGB species palette gate stays pending until the real in-map Ivysaur and independently isolated Bulbasaur have visible, archived screenshots. Startup-border or house-upstairs evidence is not species color verification.
