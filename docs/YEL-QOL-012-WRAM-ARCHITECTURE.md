# YEL-QOL-012 — WRAM0 capacity decision

## Actual layout evidence

The original linker layout places `Current Box Data` after persistent
`Party Data` and `Main Data`, before `CGB Palette Data` and the
hard-anchored stack at $DF15. Its 30-mon version begins at $DA7F.
The enlarged `wBoxDataStart..wBoxDataEnd` region is 1682 bytes, ending
at $E107 if placed contiguously. Thus the box region alone is **273 bytes
past $E000**, and it also collides with the palette section and protected
stack. The original 20-mon region occupies 1122 bytes: +550 bytes total.

The WRAM file contains many `UNION` and `NEXTU` aliases, but aliases
show that different functions *reuse the same live address*, not that
physical memory is unused. In particular `Tilemap`, `Overworld Map`,
`WRAM`, `Party Data` and `Main Data` are not blanket reclaimable
space. Reusing them requires proof of mutually exclusive lifetimes for
every reader/writer in both battles and PC menus, plus save/reload,
DMG and CGB compatibility.

**Decision**: Do not attempt to recover 550 bytes from incidental
WRAM aliases or relocate the stack/palette and declare success.
Choose an SRAM-backed paged working-box architecture after clean compile
proves baseline, because it makes lifetime and persistence boundaries
explicit and does not depend on CGB-only banked WRAM.

## Proposed implementation architecture (NOT YET INSTALLED)

- Preserve the existing 20-mon `wBoxDataStart..wBoxDataEnd` working
  block's 1122-byte footprint for Gen-I UI operations; rename the
  assumption "window", not "30-slot box".
- Keep **30 complete records per box in physical SRAM** in 3 banks of
  four boxes each, as already assigned in `ram/sram.asm`.
- Introduce a controlled 20-record staging window and record indices
  0..29. Under a PC menu operation, page physical records into the
  staging buffer; commit changes transactionally to the proper SRAM box.
  Both Pokémon data and corresponding OT/nickname bytes must move as
  a unit. Preserve the order on native capture prepend.
- Perform full-box and auto-switch checks against the authoritative
  per-box SRAM count, not a possibly partial WRAM page count.
- Keep all unsaved changes durable within the *running game* across
  SRAM bank switches, and commit game SAVE to all required SRAM banks.
  The old 20-slot `sCurBoxData` format in save bank 1 cannot be used
  as if it were a 30-slot box; introduce a versioned saved record format
  with checksum and safe legacy handling.
- Every box command, SendNewMonToBox, party/box transfers, box-view
  navigation, save, continue, and checksum routines must be audited and
  refactored to use the new abstraction before removing the temporary
  linker failure.

## Acceptance constraints

1. DMG-compatible WRAM0 linker build and correct 64 KiB SRAM header.
2. No out-of-bounds box insertions or stale SRAM bank pointers.
3. All 12 boxes of 30, seven storage fixtures and byte-for-byte
   Pokémon/OT/nickname retention after bank crossings.
4. Reboot emulator using real in-game SAVE and CONTINUE, verify records,
   checksums, current selection and item consumption/rejection.
5. Explicit legacy-save conversion policy and adversarial corrupted-save
   tests; no reinterpretation of old 20-mon SRAM as 30-mon records.
6. Keep the known-good 20-slot YEL-QOL-011 branch unchanged.

**Status:** investigation complete; banked-window engine refactor and
native persistence tests remain unimplemented. Draft PR #12 must not merge.

## 2026-10-10 assembly window integration checkpoint
The WRAM `Current Box Data` section now allocates only 20 records using `YEL012_WORKING_SLOTS`, independent of `MONS_PER_BOX=30` in SRAM. The first linker attempt progressed beyond the old WRAM collision and found an unrelated out-of-range JR in the new assembly accessor; changed to JP. The 30-slot SRAM primitive is compiled from `main.asm`, but callers still rely on legacy whole-box copies (`wBoxDataEnd - wBoxDataStart`, now 1122 bytes) when physical SRAM boxes are 1682 bytes. Therefore this branch must be treated as functionally unsafe until page transactions, header/sentinel/count management, PC navigation, capture prepend, deposit/withdraw, checksums and native SAVE/CONTINUE are all migrated. A build PASS is not a playable storage PASS. Do not merge.

## 2026-10-10 occupied-slot transaction primitive
The assembly Yel012TransferBoxRecord routine now rejects physical indexes outside 0..29 and occupied-slot indexes at or beyond the stored count; verifies nonempty species header; rejects incoming writes whose species differs from the indexed species; then transfers exactly 33+11+11 bytes with no writes to unrelated slot offsets. After successful writes it recomputes the physical SRAM bank aggregate checksum and four complete 1682-byte individual box checksums. This is specifically an IN-PLACE occupied-record transaction; captures/insertions, count/sentinel updates, page staging and PC operations are NOT wired yet. Build/emulator/real SAVE acceptance pending CI evidence. No merging.
