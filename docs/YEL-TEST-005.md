# YEL-TEST-005 — shared emulator infrastructure (initial interface)

Owner: YEL-TEST-005. Primary project area: testing/QA. Consumers: YEL-QOL-011,
battle mechanics, Brock Gym. This branch introduces infrastructure only and does
not alter capture rules, battles, maps, or the release ROM.

## Common replay interface

```bash
python scripts/yel_test_005_replay.py \
  --rom pokeyellow.gbc --sym pokeyellow.sym \
  --trace path/to/controller-trace.json \
  --out test-results/emulator/shared/qol011-route --checkpoint
```

Trace v1 is a JSON array of ordered steps, e.g.
```json
[
  {"frames": 120},
  {"button": "start", "frames": 1, "after": 30},
  {"button": "down", "frames": 8, "after": 8}
]
```

A step with `button` holds that button for `frames` frames, releases it, then
waits `after` frames. Wait-only steps use `frames`. Button names are lowercase.
This JSON is directly compatible with the existing YEL-QOL-011 capture replay
step schema. All replay timing uses emulated frames, not wall-clock sleep.

By default, start at clean ROM boot. `--state-in` explicitly labels a loaded
checkpoint and is **not** proof of clean-boot gameplay navigation. `--checkpoint`
produces a local/private state and hashes it; neither state nor ROM belongs in
the Git repository or public CI artifacts.

Report fields include ROM SHA256, symbol SHA256, input trace SHA256, optional
incoming and output checkpoint hashes, PyBoy version, Python version, DMG mode,
step count, frame count, and final 160x144 screenshot hash. The report's status
is deliberately `REPLAY_COMPLETED_TARGET_STATE_UNVERIFIED`, not feature PASS.
Build commit, RGBDS version, full build log, and CI run URL must be supplied
by invoking CI or a parent build manifest, not guessed by this script.

## YEL-QOL-011 integration sequence

1. Build the exact PR #6 revision with a pinned RGBDS version; save ROM hash,
   source SHA, symbol hash, build log, linker map, and environment version.
2. Record an **actual clean-boot controller trace** that creates/recruits a party
   of six through legitimate game mechanics, obtains Poké Balls, reaches a
   catchable wild Pokémon, and stops at a stable pre-throw menu.
3. Replay that route using this script and `--checkpoint`. A screenshot alone
   is insufficient: check the party count, six usable Pokémon, item quantity,
   active battle state, chosen wild species, game position/event provenance,
   and deterministic RNG/result using real game symbols or equivalent
   independently observed state. Only then label it a genuine pre-capture base.
4. Seed the 12 box contents from the approved `yel_qol_011_make_fixture.py`
   into a **copy** of that private genuine base state. Label each result
   `CONTROLLED_SEEDED_FROM_GENUINE_BASE`; never relabel its synthetic box
   contents as naturally obtained.
5. Run `yel_qol_011_storage.py --assert-all-boxes` using the SAME capture
   input JSON schema and matrix in `docs/yel-qol-011-fixture-matrix.md`.
   Inspect all 12 complete physical boxes with active WRAM substituted for
   its SRAM copy; existing (box, slot, 33-byte record, 11-byte OT, 11-byte
   nickname) must remain identical and in order. A successful capture adds
   exactly one record in the expected destination; all-full adds none.
6. Exercise the game-native SAVE menu, stop PyBoy, relaunch the ROM, select
   CONTINUE, and compare all 12 boxes again. A PyBoy `save_state` /
   `load_state` pair does NOT establish native SRAM persistence.
7. Run regular deposit/withdraw, first-switch initialization, box wrap,
   all-full, and repeated-capture regressions independently.

## Important current blockers

No clean-boot trace reaching the six-member pre-capture battle has yet been
produced. This runner cannot manufacture that route and does not implement
automatic gameplay planning. The feature PR currently checks per-record
preservation in memory but does **not** implement ordinary in-game
save/restart/continue verification. Neither feature nor full gameplay route is
emulator verified merely by this infrastructure commit.

Do not publicly upload ROMs, SRM/SAV files, or PyBoy states. Only controller
traces, safe reports, hashes, screenshots without private data, and CI links.

## Acceptance

Shared interface: code review + syntax check + replay with actual project ROM.
Gameplay route: observed six-member party, Poké Balls, wild battle, reproducible
throw result. Storage: all seven matrix cases with complete 12-box equality
checks. Persistence: native SAVE/restart/CONTINUE and identical original slot
records. Until all targeted conditions pass, PR #6 stays draft.

## Controller-only authoring and checkpoint inspection (new)

```bash
python scripts/yel_test_005_record.py --rom pokeyellow.gbc --out local/qol011-natural
python scripts/yel_test_005_replay.py --rom pokeyellow.gbc --sym pokeyellow.sym \
  --trace local/qol011-natural/trace.json --checkpoint \
  --out local/qol011-replayed
python scripts/yel_test_005_capture_audit.py --rom pokeyellow.gbc \
  --sym pokeyellow.sym --state local/qol011-replayed/checkpoint.state \
  --out local/qol011-audit.json
```

Recorder commands are `a 1 30`, `down 8 8`, `wait 60`, and
`done`. The recorder starts from a fresh ROM boot, writes one screenshot
per command, and continually updates a replayable `trace.json`. The final
private PyBoy checkpoint may be recreated by a separate clean-boot replay.
It must be compared by state hashes and the actual final RAM values. These
scripts do not currently include an automatically generated complete six-
Pokémon playthrough; they provide the repeatable instrumentation needed to
record one. Manual controller entry is legitimate input but requires an
independent deterministic replay and read-only audit before acceptance.

The audit validates six party species entries, at least one normal Poké Ball
(item ID $04), `wIsInBattle == 1` (wild encounter), and
`wEnemyMonSpecies2` nonzero. The checkpoint must additionally be confirmed
to be at the correct battle bag/throw prompt, rather than any wild battle
turn, and the ball's deterministic capture outcome must be demonstrated.
These read-only checks cannot independently establish original game save
persistence or a guaranteed catch. They use symbol addresses from the
exact compiled ROM and intentionally reject missing symbols.

An important distinction: an interactive clean-boot trace can establish a
genuine history, while a fixture seeded afterward is synthetic in its PC
contents. Keep separate manifests for natural replay, seeded storage
matrix, and native save/restart/continue. Until all are executed, do not
report YEL-QOL-011 as emulator-verified.

## 2026-10-10: GitHub Actions input trace diagnostics

First real instrumented per-step Actions run:
https://github.com/InternetNinjacy/project-yellow/actions/runs/38052396716

Infrastructure workflow completed PASS. Startup step probe at frames 0, 360,
542, 724, 906, 1088 observed wPartyCount=0, wNumBagItems=0,
wIsInBattle=0, and wCurMap=0 throughout. Therefore this trace did NOT
reach a playable full-party state. Inspect per-step screenshots in evidence
rather than inferring progress from changing screen hashes. SHA changes
indicate visual changes only, not advancement to the overworld.

An extended startup probe with repeated A confirmations is now being
evaluated; these input presses are exploratory and do not qualify as a
genuine complete six-Pokémon capture route or a passing game scenario.
Keep the currently exercised ROM branch separate from YEL-QOL-011 PR #6:
PR #6 behavior requires building its exact source revision before feature tests.

## 2026-10-10 input-driven progress update

Extended 60-A introductory trace, Actions run
https://github.com/InternetNinjacy/project-yellow/actions/runs/38052482785 :
map changed from 0 to 38 (hex $26 = REDS_HOUSE_2F), player position
(3,6) at frame 1184. This is a real clean-boot/controller-input
transition into the upstairs starting map. Party zero, bag zero, no battle.

Subsequent exploratory B/right/up commands, Actions run
https://github.com/InternetNinjacy/project-yellow/actions/runs/38052586833 :
through frame 6584, map remains 38 and coordinates (3,6), party zero.
Thus controller steps did NOT move the player or reach the stairs.
Inspect the archived screenshots to determine the blocking intro/menu
state; do not assume the player is freely controllable because map
coordinates are populated. The future route must take inputs according to
observed menu state rather than brute-force repeating A.
No pre-capture checkpoint or storage scenario passed.
