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

## SGB navigation checkpoint (continued 2026-10-09)

- Real SameBoy `sgb-ntsc` CI run https://github.com/InternetNinjacy/project-yellow/actions/runs/38011210886: successful emulator startup, DEBUG menu row selection, DEBUG new-game intro dismissal and overworld screenshot capture. Screenshots `sgb_lab_attempt.png`, `sgb_upper_right.png`, `sgb_downstairs_attempt.png` archive the navigation attempt.
- This demonstrates progress past the title/menu into the in-game environment, but **not yet a positively identified Red's House 1F lab or Bulbasaur/Ivysaur**. The unattended GUI key holds are insufficient for a source-confirmed map-position assertion. Do not label this as SGB species rendering QA.
- The existing PyBoy DMG/GBC fixture reaches the lab by real overworld movement from initial map 0 `(y=6,x=5)` with a single `up` transition into Red's House 1F `(y=7,x=2)`; SameBoy GUI navigation presently differs in timing and requires independently validated in-map position or screenshot recognition.
- Next: make SameBoy control deterministic (game-frame-aware input or stable savestate injection), assert a lab marker or player/map coordinates before screenshot capture, then stage separate Bulbasaur/Ivysaur SGB sprite fixtures. Current DMG/GBC approvals remain unchanged.

## SGB deterministic location gate attempt (2026-10-09)

- Branch changes introduce scripts/yel_test_004_sgb_navigate.py and update .github/workflows/yel-test-004-sgb.yml to produce an independent native GBC Red's House 1F reference, then screen-capture real SameBoy SGB-NTSC at every player input and compare edge geometry against the reference. The test requires threshold 0.45 and must FAIL without matching lab image. It does not edit gameplay memory or pretend time-based screenshots prove a warp.
- Run https://github.com/InternetNinjacy/project-yellow/actions/runs/38014043151 completed with **SGB location gate failure**, which is the correct fail-closed result: none of 23 screens reached the lab; best image edge-overlap score 0.29591 (threshold 0.45). Navigational input remains a bounded sequence of short held keys; image check makes success evidence-grounded but input path is NOT YET proven deterministic.
- Artifact ID 11655548395, archive `YEL-TEST-004_SGB_deterministic_navigation_diagnostics.zip`, includes screenshots for positions 00–22 and `navigation.json` with per-step scores. Investigate actual upstairs warp/player position and SameBoy key mapping before altering threshold. Do not lower threshold solely to force green. SGB Bulbasaur/Ivysaur still PENDING. PR #8 stays draft/unmerged.

## Source-coordinate correction — 2026-10-09

Source of truth: `constants/map_constants.asm` assigns PALLET_TOWN map `$00`; the existing PyBoy deterministic verifier reports DEBUG starting coordinates `[y=6,x=5]`, and its verified route `['up']` transitions into REDS_HOUSE_1F with player `[y=7,x=2]`. The earlier assumption that SGB begins inside REDS_HOUSE_2F was wrong. The staircase at (x=7,y=1) belongs to an unrelated upstairs map. The SGB navigation script was updated to attempt the grounded one-step northward entrance first. Existing visual-reference threshold 0.45 stays unchanged; passing the threshold, rather than completing a timed key sequence, is required. SameBoy outcome still needs verification.

## Corrected interpretation of SGB start and staircase screenshots (2026-10-09)

The earlier assumption that the SGB GUI remained in PALLET_TOWN after the DEBUG menu was contradicted by native SGB screenshots. Screenshot `sgb-smoke/navigation/position_00.png` from run 38015929838 actually shows Red's House 2F (upstairs table, chairs, stair at upper-right); this should override the earlier inference from a PyBoy map value sampled at an intermediate program stage. In map source `data/maps/objects/RedsHouse2F.asm`, the stair at `(x=7,y=1)` warps to REDS_HOUSE_1F (warp #3). SGB screen sequence from run 38016203846 shows the player progressing right and upward, with the stair east of the player after reaching the upper side of the room. Attempted route adjusted to go east toward visible stair and then north; the room matcher remains unchanged (threshold 0.45). Two test cycles exposed script serialization of literal `\\n` in comments, accidentally commenting out the movement variable; corrected and added Python compile smoke gate to prevent further late-stage failures. Latest run (head 6fc7b9884ed7553faccec03eabc47ee9c3a0f7b9) pending. Do not label SGB lab entry or species palette PASS until independent screenshot gate succeeds. Exact SGB in-game player coordinates have NOT been read from emulator memory; screenshots alone only ground relative position. Follow-up should add a SameBoy state/memory coordinate check or a DEBUG-only in-game coordinate readout for exact location.

## SGB post-warp capture checkpoint (2026-10-09)

- Added post-transition screenshot sampling and native 160x144 viewport PNGs in `scripts/yel_test_004_sgb_navigate.py` (commit 197cb17bf29ac7e7d4eb9d72c75e8b11ddfc4a63) while holding room-match threshold 0.45.
- CI https://github.com/InternetNinjacy/project-yellow/actions/runs/38018980393 **FAIL**, correctly, because Red's House 1F was not identified. Its evidence artifact ID 11657117960 includes eight postwarp screenshots and `navigation.json`; postwarp edge similarity stays 0.02574. Examination of cropped game frames shows the player still upstairs, standing near the upper-right wall/warp area; earlier black frame was a transient display state, NOT proof of map transition.
- Remaining dependency: verify exact SGB player x/y and walkable staircase tile using SameBoy state/memory debugging or use more precise input increments and visual feedback. Do not reduce threshold or count black transition as a pass; PR #8 remains draft.

## Live SameBoy debugger readout achieved (2026-10-10)

**Milestone achieved:** GitHub Actions run 38059271748 succeeded with an SDL SameBoy v1.0.3 process wired to a FIFO debugger command stream. Sent SIGINT to interrupt normal emulation, then symbol-resolved `print [wCurMap]`, `print [wXCoord]`, `print [wYCoord]`, and `continue` twice. Authentic `sameboy.log` values: first map=$25, x=$02, y=$07; second map=$25, x=$07, y=$05. This is reliable direct live WRAM readback, **not screenshot inference**. Evidence: https://github.com/InternetNinjacy/project-yellow/actions/runs/38059271748 (artifact 11673005263). Reproducible parser `scripts/yel_test_004_sgb_live_xy.py` added to enforce two map/coordinate reads and observable movement, with GitHub workflow integration on branch.

This resolves the previously missing live map/X/Y introspection capability. It does **not** yet prove the stair warp: player ends at (7,5), while Red's House 2F's downstairs warp is (7,1). Next engineering task: move from (7,5) north, inspect live coordinates after each step, and require map switch to REDS_HOUSE_1F before enabling independent sprite screenshot QA. The 0.45 room image gate remains unchanged; PR #8 remains DRAFT.

## Native SameBoy debugger live RAM probe — 2026-10-10

- SameBoy official SDL debugger supports SIGINT interruption and `examine/1 $ADDR`. Implemented PTY-based debugger probing in `scripts/yel_test_004_sgb_debug_probe.py` and invoked it before the GUI screenshot test from `.github/workflows/yel-test-004-sgb.yml`.
- Run https://github.com/InternetNinjacy/project-yellow/actions/runs/38064762399 successfully completed the **debugger-probe step** and archived `sgb-debugger/debugger_transcript.txt` and `sgb-debugger/symbols.json` in artifact ID 11675171491, but the subsequent existing GUI navigation step failed.
- Actual native debugger transcript: `d35d: 00` = `wCurMap`, `d360: 06` = `wYCoord`, and `d361: 05` = `wXCoord`. This is a genuine SameBoy emulator memory inspection, not a screenshot estimate. It does not yet establish whether the sample was taken after final DEBUG map initialization; the SGB screenshots still show a room resembling Red's House 2F. Do not infer resolved navigation solely from these bytes.
- Follow-up commit 771403116b1aeb694935e3e3ba1fc6495150d1eb parses bytes into `live_coordinates.json` rather than accepting echoed commands, not yet verified in CI at time of note. Next must sample before/after controlled movement or break on the map-transition routine to reconcile screen with RAM, then use coordinates as the navigation acceptance gate. SGB species graphics remain pending and PR stays draft.

## Confirmed native SGB map transition — 2026-10-10

SameBoy debugger-backed GitHub CI run 38065420666 revealed actual `wCurMap/wXCoord/wYCoord` transitions: `(37 / $25, x=2, y=7)` followed by `(38 / $26, x=7, y=1)`. ROM constants identify $25 as `REDS_HOUSE_1F` (the graphics lab) and $26 as `REDS_HOUSE_2F` (upstairs). Thus the SGB gameplay did reach the lab; subsequent navigation left it and our former parser rejected any map change as unexpected. Parser repaired in commits 079998bf8e31a12e4b4cab687a497fffae9fd98f and d6d8d50f2c9009c438ad559d37629ba73321bf79: allow movement/warps and assert the exact 1F -> 2F transition. The test run confirming latest parser implementation may still be pending. Remaining objective is to capture actual Ivysaur and Bulbasaur screens while map $25 is active and verify colors/graphics; do NOT assert species SGB verification merely on coordinates. Retain original 0.45 visual threshold until a verified corresponding reference proves any comparator problem. PR #8 remains draft.

## First real SGB Ivysaur room capture — 2026-10-10

- CI run https://github.com/InternetNinjacy/project-yellow/actions/runs/38067160552 PASSED all its SGB smoke/capture gates. Artifact 11675650819 archives `sgb-smoke/ivysaur_map25_candidate.png`, the 160x144 cropped `ivysaur_map25_viewport.png`, and `ivysaur_capture_report.json`.
- SameBoy native debugger confirmed map `$25` / REDS_HOUSE_1F at x=2,y=7 adjacent to the captured frame. Actual SGB framebuffer (512x448) shows the lab with the species sprite occupying the upper-right room position. Capture diagnostics: 772 distinct RGB colors in extracted viewport, RGB standard deviations 106.94, 106.29, 107.75. These are frame diagnostics, not a standalone species pixel-identity verification.
- Status: **IVYSAUR SGB MAP-GATED CAPTURE COMPLETE**; detailed sprite integrity/palette/facing verification still PENDING. **BULBASAUR SGB CAPTURE PENDING**, must use its own isolated species fixture (do not mislabel the Ivysaur image). The gate's visual-reference threshold remains 0.45 for the independent lab comparison; this map-gated capture test validates coordinates/frame, not sprite equality. PR #8 DRAFT/UNMERGED.
