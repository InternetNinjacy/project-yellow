; Inputs: A slot, HL physical SRAM box base, DE moving output/input
; buffer, C mode (0 SRAM->WRAM, 1 WRAM->SRAM).
; Preserves A/C/HL, increments DE by field length.
MACRO YEL012_COPY_FIELD
	push af
	push hl
	push bc
	ld bc, \1
	add hl, bc
	ld bc, \2
.loop\@
	and a
	jr z, .ready\@
	add hl, bc
	dec a
	jr .loop\@
.ready\@
	pop bc ; C mode
	push af
	ld b, \3
.bytes\@
	ld a, c
	and a
	jr nz, .write\@
	ld a, [hli]
	ld [de], a
	jr .advance\@
.write\@
	ld a, [de]
	ld [hli], a
.advance\@
	inc de
	dec b
	jr nz, .bytes\@
	pop af
	pop hl
	pop af
ENDM

; YEL-QOL-012: physical 30-slot box record access.
; Complete record = 33 Pokémon bytes + 11 OT + 11 nickname.
; This is the low-level primitive only: callers must validate the
; box header, own transaction boundaries and refresh SRAM checksums.
DEF YEL012_SRAM_MON_OFFSET EQU MONS_PER_BOX + 2
DEF YEL012_SRAM_OT_OFFSET EQU YEL012_SRAM_MON_OFFSET + MONS_PER_BOX * BOXMON_STRUCT_LENGTH
DEF YEL012_SRAM_NICK_OFFSET EQU YEL012_SRAM_OT_OFFSET + MONS_PER_BOX * NAME_LENGTH
DEF YEL012_RECORD_BUFFER_SIZE EQU BOXMON_STRUCT_LENGTH + 2 * NAME_LENGTH
ASSERT MONS_PER_BOX == 30
ASSERT YEL012_SRAM_NICK_OFFSET + MONS_PER_BOX * NAME_LENGTH == 1682

; A: zero-based slot 0..29, DE: caller-supplied 55-byte WRAM buffer.
; Returns carry on invalid index. Clobbers AF/BC/DE/HL.
Yel012ReadBoxRecord::
	ld c, 0
	jr Yel012TransferBoxRecord

Yel012WriteBoxRecord::
	ld c, 1
	; fallthrough

Yel012TransferBoxRecord:
	cp MONS_PER_BOX
	jp nc, .invalid
	push bc ; mode
	push de ; buffer
	push af ; slot
	call GetBoxSRAMLocation ; HL=box base, B=SRAM bank
	call EnableSRAM
	ld a, b
	ld [rRAMB], a
	pop af ; slot
	pop de ; buffer
	pop bc ; mode (C)
	; SRAM access is now enabled. Each field restores the box base.
	YEL012_COPY_FIELD YEL012_SRAM_MON_OFFSET, BOXMON_STRUCT_LENGTH, BOXMON_STRUCT_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_OT_OFFSET, NAME_LENGTH, NAME_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_NICK_OFFSET, NAME_LENGTH, NAME_LENGTH
	call DisableSRAM
	and a ; carry clear
	ret
.invalid
	scf
	ret

