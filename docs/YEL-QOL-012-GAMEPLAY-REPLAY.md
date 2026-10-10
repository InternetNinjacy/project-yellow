# YEL-QOL-012 real-gameplay PyBoy acceptance replay

The file `scripts/yel_qol_012_gameplay_replay.py` is a **strict replay runner**, not a recorded replay or a successful gameplay test. It only touches SRAM through normal gameplay. Its controller script is supplied in JSON; unlike the lower-level CPU probe, no SRAM is pre-seeded.

The input must contain nonempty `prepare`, `capture`, `save`, and `continue` arrays, and an integer `destination_box` from 0 through 11. Each action is `{"button":"a","frames":2}` or a no-button wait `{"frames":60}`. The `prepare` trace must arrive at a natural in-game state with six party Pokémon and exactly 29 records in the destination physical box. The `capture` trace must actually throw a ball and add a Pokémon at slot 0. The `save` trace must execute the game's SAVE UI, and `continue` must navigate the rebooted emulator's CONTINUE menu. **No such proven controller trace has yet been recorded or committed.**

Invocation, after producing a ROM and symbols in the existing build workflow:

```sh
python3 scripts/yel_qol_012_gameplay_replay.py \
  --rom pokeyellow_debug.gbc --sym pokeyellow_debug.sym \
  --replay path/to/recorded-live-replay.json \
  --out test-results/yel-qol-012/live-gameplay.json
```

The runner fails closed on missing phases, missing six-member party, wrong occupancy/sentinel, no new record, changed prior 29 records, invalid record species, and any mismatch after a fresh PyBoy instance reloads battery SRAM from disk.

## Important test gaps

- No verified deterministic input trace can yet reach the precondition through the actual game. Do not invent input events or mark this test PASS.
- A 29→30 fixture in one box does not demonstrate selecting the next box or switching SRAM banks. Create separate recordings for box 3→4, 7→8 and 11→0, full and corrupt boxes.
- A battery SRAM reboot equality check must be coupled with observed game SAVE and CONTINUE actions. The script cannot identify text/menu state on its own and should not be treated as a UI assertion.
- The game's legacy save and PC menu routines continue to use 20-slot assumptions. A passing low-level CPU or generic emulator smoke test does not establish persistence, normal player PC usage or migration.
- Do not run this as a required CI job until the recorded trace exists and has been independently executed. PR #12 remains draft.

## 2026-10-10 deterministic setup, fixture-vs-gameplay boundary

The DEBUG-only new-game party now has six species (commit 9dc83b7).
`scripts/yel_qol_012_fixture.py` seeds a complete 29-record physical
destination box and bank checksums **only from the emulator harness**, after
real debug new-game controls have established six party members. Other boxes
can optionally be full to force bank crossings. This is not naturally earned
game progress and must never be represented as such.

The replay runner accepts `"fixture_mode":"synthetic-physical-29"`
and optionally `"other_boxes_full":true`. The fixture preparation is
synthetic, but all `capture`, `save`, and `continue` actions are still
real controller events, not scripted SRAM writes. The runner checks entire
physical boxes before and after reload.

There is STILL NO recorded, verified replay JSON in the repository.
The `tests/replays/yel_qol_012_full_party_29_to_30.json` CI gate remains
skipped until a real controlled trace is discovered. No captured-mon
gameplay success or save persistence is asserted by these commits.
