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
	push bc ; preserve read/write mode C
	push de ; 55-byte source/destination buffer
	push af ; slot
	call GetBoxSRAMLocation ; HL physical box, B SRAM bank
	call EnableSRAM
	ld a, b
	ld [rRAMB], a
	pop af ; slot
	pop de ; record buffer
	pop bc ; C is read/write mode
	ld b, a ; physical slot index
	ld a, [hl] ; stored occupancy
	cp MONS_PER_BOX + 1
	jr nc, .badOpen ; corrupt count
	cp b
	jr c, .badOpen ; slot beyond occupied records
	jr z, .badOpen
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
	jr z, .badOpen
	cp $ff
	jr z, .badOpen
	; The header and count remain unchanged; caller owns consistency
	; between the record species and indexed species table.
	ld a, b ; zero-based slot
	YEL012_COPY_FIELD YEL012_SRAM_MON_OFFSET, BOXMON_STRUCT_LENGTH, BOXMON_STRUCT_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_OT_OFFSET, NAME_LENGTH, NAME_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_NICK_OFFSET, NAME_LENGTH, NAME_LENGTH
	ld a, c
	and a
	jr z, .done
	; Refresh the entire bank checksum and four per-box checksums.
	ld hl, sBox1
	ld bc, sBank2AllBoxesChecksum - sBox1
	call CalcCheckSum
	ld [sBank2AllBoxesChecksum], a
	call CalcIndividualBoxCheckSums
.done
	call DisableSRAM
	and a
	ret
.badOpen
	call DisableSRAM
.invalid
	scf
	ret
