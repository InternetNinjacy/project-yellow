# YEL-BAL-002: deterministic battle fixture gate

Status: **replay runner committed, battle fixtures NOT captured and NOT executed**.

`tests/battle/replay.py` is a fail-closed PyBoy runner. It loads a legitimate
emulator state immediately preceding an action, verifies the live battle WRAM
snapshot, replays explicit input/frame steps, and checks the final WRAM values
using the actual ROM's `.sym` map. It does not inject synthetic battle stages
or treat ROM startup as mechanics verification.

## Prerequisites

1. Build the **same branch revision** ROM and its matching symbol file:
   `make pokeyellow_debug.gbc` (or a verified equivalent).
2. Install PyBoy in the test environment.
3. Capture actual PyBoy savestates after reaching a reproducible **active
   battle**, with the chosen move available and an unambiguous selected target.
   Use the same ROM revision for capture and replay.
4. Populate `tests/battle/fixtures.json` with all required scenarios and
   exact expected values; do not commit copyrighted ROMs or private save data.
5. Run:
   `python3 tests/battle/replay.py --rom pokeyellow_debug.gbc --symbols pokeyellow_debug.sym --manifest tests/battle/fixtures.json`

## Manifest example (illustrative schema, NOT test evidence)

```json
{
  "cases": [
    {
      "name": "amnesia_player",
      "state": "states/amnesia_player.state",
      "before": {
        "wPlayerMonSpecialMod": 7,
        "wPlayerSpecialDefenseMod": 7
      },
      "steps": [
        {"button": "a", "frames": 1},
        {"release": "a", "frames": 150}
      ],
      "after": {
        "wPlayerMonSpecialMod": 7,
        "wPlayerSpecialDefenseMod": 9
      }
    }
  ]
}
```

The example is deliberately incomplete: the runner REQUIRES all ten named
scenarios in its `REQUIRED_CASES` set and real savestates. Accurate frame
counts, target HP, and calculated values must be recorded from controlled
emulator execution, not invented. Cases must assert **both** Special modifiers
to detect cross-stat interference, and include 16-bit current Special Attack
and Special Defense readings wherever damage claims depend on them.

Required cases: Amnesia on both sides; Growth on both sides; Growth with either
individual Special stat at +6; Psychic triggered on both sides; Psychic against
-6 Special Defense; and at least one damaging Special move with asserted
actual HP change. For the Psychic probability gate, capture the RNG state in
the legitimate savestate and preserve deterministic inputs. Repeat against
a second RNG state in which the secondary effect does not occur.

## QA requirements beyond the initial runner

This runner establishes an explicit *replay mechanism*, not complete evidence:
- Record paired before/after enemy and player HP and 16-bit stats for damage.
- Capture ordinary and critical hit controls with identical relevant setup.
- Capture switch/re-entry, Haze, Transform, screens and residual state separately.
- Verify the exact ROM hash and PyBoy version as fixture provenance.
- Run fixture replays in CI once genuine fixture states exist.

No deterministic emulator battle tests have passed until the runner prints
PASS for each case **on actual savestates**. PR #5 stays draft.

## Capturing the first legitimate active-battle state

`tests/battle/capture.py` is a deterministic **controller-only** recorder for
already-known traces. It can replay from emulator power-on or a previously
captured legitimate starting state. Unlike directly modifying WRAM, it cannot
silently manufacture a battle or bypass a broken entry event.

Create `tests/battle/routes/first_battle.json` containing actual observed
PyBoy button/frame steps, for example objects of the form
`{"button":"a","frames":1}` and `{"release":"a","frames":30}`.
These are **schema illustrations, not an asserted playable route**.

Run:
```
python3 tests/battle/capture.py \
  --rom pokeyellow_debug.gbc \
  --symbols pokeyellow_debug.sym \
  --trace tests/battle/routes/first_battle.json \
  --output tests/battle/states/first_battle.state
```

The capture command refuses to save unless `wIsInBattle`,
`wBattleMonSpecies`, and `wEnemyMonSpecies` are nonzero. It also records the
ROM and trace SHA-256 hashes and battler IDs. No memory patch is performed.

**Unresolved prerequisite:** A genuinely recorded power-on-to-battle input
trace, or a legitimate earlier starting savestate, is not currently in this
branch. A starter encounter with Oak or a battle with a wild Pokémon would
qualify only if the game is in an actual active battle with usable moves.
For Amnesia, Growth and Psychic testing, follow-on controlled battles must
include Pokémon that actually know those moves. The first basic wild battle
does not alone verify those effects.

This capture script is not self-validating proof of the user's requested
battle: it must be executed and produce a state plus evidence in the emulator.
