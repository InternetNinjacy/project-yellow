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
	jp z, .ready\@
	add hl, bc
	dec a
	jp .loop\@
.ready\@
	pop bc ; C mode
	push af
	ld b, \3
.bytes\@
	ld a, c
	and a
	jp nz, .write\@
	ld a, [hli]
	ld [de], a
	jp .advance\@
.write\@
	ld a, [de]
	ld [hli], a
.advance\@
	inc de
	dec b
	jp nz, .bytes\@
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
	jp Yel012TransferBoxRecord

Yel012WriteBoxRecord::
	ld c, 1
	; fallthrough

Yel012TransferBoxRecord:
	cp MONS_PER_BOX
	jp nc, .invalid
	push bc ; preserve read/write mode C
	push de ; 55-byte source/destination buffer
	push af ; slot
	call Yel012GetBoxSRAMLocation ; HL physical box, B SRAM bank
	ld a, b
	call OpenSRAM
	pop af ; slot
	pop de ; record buffer
	pop bc ; C is read/write mode
	ld b, a ; physical slot index
	ld a, [hl] ; stored occupancy
	cp MONS_PER_BOX + 1
	jp nc, .badOpen ; corrupt count
	cp b
	jp c, .badOpen ; slot beyond occupied records
	jp z, .badOpen
	; Verify the physical species header before allowing transfer.
	push hl
	push bc
	inc hl
	ld c, b
	ld b, 0
	add hl, bc
	ld a, [hl] ; species at slot
	pop bc
	pop hl
	and a
	jp z, .badOpen
	cp $ff
	jp z, .badOpen
	; For occupied-slot writes, reject a species mismatch before any
	; SRAM bytes are modified; callers must transact inserts separately.
	push bc
	ld b, a ; expected header species
	ld a, c
	and a
	jp z, .headerOK
	ld a, [de] ; species in incoming mon_struct
	cp b
	jp nz, .badSpecies
.headerOK
	pop bc
	ld a, b ; zero-based slot
	jp .transfer
.badSpecies
	pop bc
	jp .badOpen
.transfer
	YEL012_COPY_FIELD YEL012_SRAM_MON_OFFSET, BOXMON_STRUCT_LENGTH, BOXMON_STRUCT_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_OT_OFFSET, NAME_LENGTH, NAME_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_NICK_OFFSET, NAME_LENGTH, NAME_LENGTH
	ld a, c
	and a
	jp z, .done
	; Refresh the entire bank checksum and four per-box checksums.
	call Yel012RefreshPhysicalChecksums
.done
	call CloseSRAM
	and a
	ret
.badOpen
	call CloseSRAM
.invalid
	scf
	ret
