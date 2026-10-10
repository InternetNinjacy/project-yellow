# YEL-QOL-012 — Expand PC box capacity 20 -> 30 (design gate)

**Decision (2026-10-10):** User requests 30 Pokémon per PC box, preserving 12 boxes.
This is a substantial storage-schema migration; not a constant-only edit.
Keep YEL-QOL-011 full-box safety corrections distinct from this redesign.

## Confirmed from source

- Makefile: MBC5+RAM+BATTERY, `-r 03` (32 KiB cartridge SRAM).
- Per-box size: `1 + N + 1 + N*33 + 2*N*11`.
- N=20 -> 1122 bytes; 6 boxes per SRAM bank = 6732 bytes.
- N=30 -> 1672 bytes; six boxes = 10032 bytes, impossible in 8192-byte bank.
- 12 enlarged boxes = 20064 bytes; 4 boxes each across 3 separate 8 KiB
  SRAM banks requires 6688 bytes per bank.
- ROM uses fixed SRAM banking assumptions in save.asm and storage tests;
  size affects active box WRAM, SRAM, saved current box, indexes, menus and
  check sums.
- Existing header `-r 03` provides four SRAM banks (32 KiB). More SRAM
  is appropriate: MBC5 plus `-r 05` means 64 KiB SRAM (8 x 8 KiB banks)
  on compatible emulator/hardware. Verify physical flash cart supports it.

## Safe implementation plan

1. Create exact SRAM / WRAM / save section map from current .map files.
2. Declare new `MONS_PER_BOX=30` and audit all indexes and 20-slot loops.
3. Increase cartridge RAM header to 64 KiB **only after** proving supported
   cartridge type, and assign each group of four boxes to dedicated SRAM banks
   without colliding with core save/player data. Refactor all old
   `sBox1/sBox7`, `bank=2 if idx<6 else 3` assumptions and hard-coded
   1122-byte offsets. Write capacity constants from a single source.
4. Rewrite bank-switch/save/checksum/working-box serialization for 30 slots.
   Test SRAM bank access with explicit bank-boundary assertions.
5. Audit box UI listing, paging, cursor positions, selection, deposit,
   withdraw, release, transfer, names, and empty/full strings.
6. Define migration from legacy 20/box save files. Never silently reinterpret
   a prior save as 30/box. Either implement a verified conversion path and
   version marker with rollback, or explicitly mark incompatible saves only
   with user approval.
7. Replace seven fixture capacities and record offsets with dynamic
   symbol/format knowledge; expand edge cases to 29,30,0 and cross-bank
   captures. Keep seven original scenario intent but update expected counts.
8. Build both DEBUG and release; test storage, all-full rejection, native
   SAVE/reset/CONTINUE and independent gameplay; physical cartridge
   compatibility is a separate final gate.

**Current status:** feasibility established; implementation and migration
NOT COMPLETE. Don't change header/capacity constant alone; such a build
would either fail link or corrupt saves.

## YEL-QOL-011 20-slot fixes under way

- Run 38055588385: four 20-slot scenarios pass; all-full overflow and two
  false-positive record-order checks fail.
- Native Gen I catch insertion prepends a new Pokémon. Update the test to
  preserve byte-exact existing records in the same box and relative order;
  do not demand unchanged absolute slot numbers.
- DEBUG Pallet Town wild station now explicitly sets wBattleType to normal
  wild. Re-run the all-full test to see if the original overflow was a
  stale special-battle flag rather than production box-space logic.
- Do not declare all-full fixed until a real 20/20/.. 20 capacity attempt
  is rejected and all twelve box byte snapshots remain unchanged.
