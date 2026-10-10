# YEL-QOL-012 live implementation and linker gate

2026-10-10: Branch `yel-qol-012-pc-30` based on the verified YEL-QOL-011 implementation. Code edits attempted in `constants/pokemon_data_constants.asm`, `Makefile`, `ram/sram.asm`, `layout.link`, and `engine/menus/save.asm`: 30 slots, MBC5 64 KiB SRAM header, boxes 1-4/5-8/9-12 in banks 2/3/4, and four-box bank counts/checksums/selection.

## Build outcome: FAIL (important)

GitHub CI run [38063911479](https://github.com/InternetNinjacy/project-yellow/actions/runs/38063911479) reports:

- `Current Box Data` at $DA7F overflows WRAM0 by **273 bytes**.
- `CGB Palette Data` would overflow WRAM0 by 52 bytes.
- Linker cannot decrease address from $E000 to $DF15 for Stack.
- Stack then overflows WRAM0 by 235 bytes.

**Do not claim a working 30-slot ROM or save system.** Three-bank cartridge SRAM allocation alone does not solve the enlarged active box in fixed 8 KiB DMG WRAM0. The original wBoxDataStart..End expands from 1122 to 1672 bytes. CGB WRAMX is not an acceptable universal fix for monochrome Game Boy hardware. Original save data in SRAM bank 1 also grows 550 bytes and must be checked independently for capacity/format and compatibility.

## Required design resolution before build retry

Choose and implement a DMG-compatible working-box representation, e.g. one of:

1. Move enough *noncritical* RAM structures to existing safely reusable overlays **after** verifying all lifetime overlap, or
2. Refactor box commands to use a 20-record working window, with remaining 10 backed by dedicated SRAM and properly banked access. This is a substantial change to insert, deposit/withdraw, naming, printing, checksum and persistence paths.

Do NOT quietly relocate WRAM sections, stack or OAM to force the link. Do NOT mark storage or persistence gates green until debug/release builds, ROM tests, 7x30 capture matrix, native SAVE/reset/CONTINUE, and deposit/withdrawal all pass.

## Additional known dependencies

- YEL-QOL-011 fixture programs hardcode 1122-byte box layout, six boxes per bank and 20-slot data offsets. Update to 1672 bytes, four boxes per bank and 30-slot offsets.
- `SaveCurrentBoxData` and `LoadCurrentBoxData` must be audited for new SRAM bank layout and versioned saved format.
- Legacy 20-slot save compatibility remains **undecided and unimplemented**; reject incompatible save formats safely until a migration path is approved.
