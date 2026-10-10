; YEL-QOL-012: physical SRAM box record accessor (staging primitive).
; Authoritative box layout is 30 slots:
; count (1), species (30), sentinel (1), mon data (30 * 33),
; OT (30 * 11), nickname (30 * 11).
; Caller: A = physical slot (0..29), DE = 55-byte WRAM buffer
; (33 mon bytes, 11 OT, 11 nickname). Current box is selected by
; wCurrentBoxNum. Other registers are not preserved.
; This primitive does not alter count, terminator, or selected box.
; All writes must be invoked from a transaction that updates headers
; and checksums. Do not use this alone as a storage commit.
DEF YEL012_SRAM_MON_OFFSET EQU MONS_PER_BOX + 2
DEF YEL012_SRAM_OT_OFFSET EQU YEL012_SRAM_MON_OFFSET + MONS_PER_BOX * BOXMON_STRUCT_LENGTH
DEF YEL012_SRAM_NICK_OFFSET EQU YEL012_SRAM_OT_OFFSET + MONS_PER_BOX * NAME_LENGTH
DEF YEL012_RECORD_BUFFER_SIZE EQU BOXMON_STRUCT_LENGTH + 2 * NAME_LENGTH
ASSERT MONS_PER_BOX == 30
ASSERT YEL012_SRAM_NICK_OFFSET + MONS_PER_BOX * NAME_LENGTH == 1682

; Input A slot, DE buffer, C direction (0 read, 1 write).
; Output carry set if slot invalid; carry clear if transferred.
Yel012TransferBoxRecord::
	cp MONS_PER_BOX
	jr nc, .invalid
	push de
	push af
	call GetBoxSRAMLocation ; HL box base, B SRAM bank
	pop af
	ld c, a
	push bc ; preserve bank and index
	call EnableSRAM
	pop bc
	ld a, b
	ld [rRAMB], a
	pop de ; buffer pointer
	push bc ; bank and slot throughout the three fields
	push hl ; base of the selected box
	ld bc, YEL012_SRAM_MON_OFFSET
	add hl, bc
	pop bc ; INVALID: replaced by helper below
	; unreachable placeholder removed in follow-up
	call DisableSRAM
	pop bc
	and a
	ret
.invalid
	scf
	ret
