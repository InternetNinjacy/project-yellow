# YEL-QOL-011 — reproducible capture fixture matrix

No copyrighted ROMs, SRAM saves, or PyBoy states are committed here.

Generate a genuine pre-capture PyBoy state by normal gameplay, with six living
party Pokémon, a Poké Ball selected, and a catchable wild encounter. Supply
that state to `scripts/yel_qol_011_make_fixture.py` for each scenario.

| ID | Active (0-indexed) | Counts in boxes 1–12 | Expected active after a successful capture |
| --- | ---: | --- | ---: |
| current-space | 0 | 19,0,0,0,0,0,0,0,0,0,0,0 | 0 |
| next-box | 0 | 20,0,0,0,0,0,0,0,0,0,0,0 | 1 |
| skip-full | 0 | 20,20,20,0,0,0,0,0,0,0,0,0 | 3 |
| wrap | 11 | 0,0,0,0,0,0,0,0,0,0,0,20 | 0 |
| wrap-skip | 10 | 20,0,0,0,0,0,0,0,0,0,20,20 | 1 |
| all-full | 0 | 20,20,20,20,20,20,20,20,20,20,20,20 | 0 |
| only-current-free | 3 | 20,20,20,19,20,20,20,20,20,20,20,20 | 3 |

Full party, caught-mon species, pre-capture HP, bag contents, random state and
input replay must be verified and logged per fixture. All-full must be tested
with attempted throw rejected, not a successfully caught wild Pokémon.

Capture integrity criteria:
1. Compare complete box records across all 12 boxes (WRAM active box + SRAM others).
2. Assert every preexisting record survives byte-identically once each.
3. Assert only one new record appears for a successful capture, none for a rejected throw.
4. Check selected box and counts against the matrix.
5. Repeat tests with failed throws and multiple successive captures.
6. Save from the game's normal UI, restart emulator, load via game UI, and
   compare all records and active selection again.
7. Confirm box deposit/withdraw remain functional and preserve records.

This file is a test plan, not evidence of executing tests. Do NOT promote to
EMULATOR VERIFIED or merge PR #6 until reports from actual emulator execution exist.
