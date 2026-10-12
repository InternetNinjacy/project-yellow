# YEL-MON-004 Poison Fang / Crunch emulator evidence gate

The contract in `tests/battle/test_rat_move_replay.py` requires **four actual PyBoy in-battle savestates**, one each for Poison Fang proc/no-proc and Crunch proc/no-proc. Nothing here is a captured state or a passing mechanics test.

## Capture rules
- Use the **same DEBUG ROM and symbol file** for capture and replay; preserve SHA-256.
- Start from power-on or a legitimate previously captured state.
- Drive the game **exclusively with controller buttons and frames**.
- Do not write WRAM, RNG seed, party data, species, move effects, or stat stages via PyBoy.
- Use `tests/battle/record.py` to make controller traces and legitimate savestates; inspect battle UI to confirm move and target; use `capture.py` to reproduce each capture from its trace.
- For each case, capture immediately prior to committing to the move, then supply post-capture controller `steps` sufficient to complete the attack.
- The test checks live `wIsInBattle`, party/enemy species, player move ID, enemy PSN bit and BADLY_POISONED bit, or enemy Defense stage modifier.
- The no-proc cases must show unchanged status or Defense modifier while move damage still occurs; preserve independent HP evidence where practical.
- The 39% and 50% *probability implementation* is additionally checked arithmetically (78 accepted values out of 200; 128 out of 256). Four scripted outcomes alone are **not** statistical proof of odds.

Run:
```sh
python3 tests/battle/test_rat_move_replay.py --rom pokeyellow_debug.gbc --symbols pokeyellow_debug.sym --manifest tests/battle/rat_move_fixtures.json
```

Manifest must provide a dictionary of exactly four `cases` named `poison_fang_proc`, `poison_fang_no_proc`, `crunch_proc`, `crunch_no_proc`. Each has `state` (relative path), `rom_sha256` (64-character SHA), and `steps` (record.py controller steps). **No such cases have yet been captured or committed.**

## Gate status 2026-10-10
- RGBDS Linux/macOS, clean build, dev lab and DMG startup smoke passed at commit `073289a`.
- No legitimate controller trace has yet been verified to reach the specified move-selection states; the separate six-Pokémon DEBUG startup probe did not establish a passing baseline.
- No real Poison Fang/Crunch savestates; no deterministic WRAM move replays executed.
- The main source branch contains custom effect implementations; these remain **unverified in live battle**.
- Do not proceed to evolution/SAVE-CONTINUE persistence tests on the assumption that this gate passed.
