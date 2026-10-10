; YEL-QOL-012 transaction engine, isolated in ROM bank $3b.
; WARNING: callers must not use the legacy whole-box copy path. This
; provides an isolated transaction interface, not yet called from battle/PC.
; SRAM bank 5 contains the original, mutable shadow, window backup and
; incoming 55-byte capture. Status: 0 idle, 1 staged, 2 committing.
DEF YEL012_BOX_SIZE EQU MONS_PER_BOX * (1 + BOXMON_STRUCT_LENGTH + 2 * NAME_LENGTH) + 2
DEF YEL012_WINDOW_SIZE EQU wBoxDataEnd - wBoxDataStart
DEF YEL012_REMAINDER EQU YEL012_BOX_SIZE - YEL012_WINDOW_SIZE
ASSERT YEL012_BOX_SIZE == 1682
ASSERT YEL012_WINDOW_SIZE == 1122
ASSERT YEL012_REMAINDER == 560

; B=physical bank, HL=physical box pointer; derives from current selection.
Yel012GetBoxSRAMLocation::
	ld a, [wCurrentBoxNum]
	and BOX_NUM_MASK
	ld b, 2
.bank
	cp 4
	jr c, .slot
	sub 4
	inc b
	jr .bank
.slot
	add a
	ld e, a
	ld d, 0
	ld hl, .ptrs
	add hl, de
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ret
.ptrs
	dw sBox1, sBox2, sBox3, sBox4

; Local checksum implementation avoids cross-bank direct calls.
Yel012CalcChecksum:
	ld d, 0
.loop
	ld a, [hli]
	add d
	ld d, a
	dec bc
	ld a, b
	or c
	jr nz, .loop
	ld a, d
	cpl
	ret

; SRAM bank 2, 3 or 4 must already be enabled/mapped.
Yel012RefreshPhysicalChecksums::
	ld hl, sBox1
	ld bc, sBank2AllBoxesChecksum - sBox1
	call Yel012CalcChecksum
	ld [sBank2AllBoxesChecksum], a
	ld hl, sBox1
	ld de, sBank2IndividualBoxChecksums
	ld b, 4
.each
	push bc
	push de
	ld bc, YEL012_BOX_SIZE
	call Yel012CalcChecksum
	pop de
	ld [de], a
	inc de
	pop bc
	dec b
	jr nz, .each
	ret

; Stage a physical box to its rollback snapshot and mutable shadow.
; Back up the old WRAM working window before modifying it.
; On success carry clear, bank-5 transaction status=1.
Yel012BeginTransaction::
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	and a
	jr nz, .failClose
	ld hl, wBoxDataStart
	ld de, sYel012TransactionWindowBackup
	ld bc, YEL012_WINDOW_SIZE
	call CopyData
	call Yel012GetBoxSRAMLocation
	ld a, b
	call OpenSRAM
	ld a, [hl]
	cp MONS_PER_BOX + 1
	jr nc, .failed
	; The physical count and its terminator are validated before copying.
	ld c, a
	ld b, 0
	inc hl
	add hl, bc
	ld a, [hl]
	cp $ff
	jr nz, .failed
	call Yel012CopyPhysicalAndSnapshotZero
	jr c, .failed
	ld a, 5
	call OpenSRAM
	ld a, 1
	ld [sYel012TransactionStatus], a
	call Yel012RestoreWindow
	call CloseSRAM
	and a
	ret
.failed
	ld a, 5
	call OpenSRAM
	call Yel012RestoreWindow
.failClose
	call CloseSRAM
	scf
	ret

; Physical -> bank5 original+shadow through the 20-slot buffer.
Yel012CopyPhysicalAndSnapshotZero:
	call Yel012GetBoxSRAMLocation
	ld a, b
	call OpenSRAM
	ld de, wBoxDataStart
	ld bc, YEL012_WINDOW_SIZE
	call CopyData
	ld a, 5
	call OpenSRAM
	ld hl, wBoxDataStart
	ld de, sYel012TransactionBackup
	ld bc, YEL012_WINDOW_SIZE
	call CopyData
	ld hl, wBoxDataStart
	ld de, sYel012TransactionShadow
	ld bc, YEL012_WINDOW_SIZE
	call CopyData
	call Yel012GetBoxSRAMLocation
	ld de, YEL012_WINDOW_SIZE
	add hl, de
	ld a, b
	call OpenSRAM
	ld de, wBoxDataStart
	ld bc, YEL012_REMAINDER
	call CopyData
	ld a, 5
	call OpenSRAM
	ld hl, wBoxDataStart
	ld de, sYel012TransactionBackup + YEL012_WINDOW_SIZE
	ld bc, YEL012_REMAINDER
	call CopyData
	ld hl, wBoxDataStart
	ld de, sYel012TransactionShadow + YEL012_WINDOW_SIZE
	ld bc, YEL012_REMAINDER
	call CopyData
	and a
	ret

; Restore the precise prior WRAM 20-record staging window (bank 5 selected).
Yel012RestoreWindow:
	ld hl, sYel012TransactionWindowBackup
	ld de, wBoxDataStart
	ld bc, YEL012_WINDOW_SIZE
	jp CopyData

; A=0 or 20 selects a page of the staged 30-record shadow.
; Transfer species, mons, OT and nicknames into wBox... in correct
; 20-slot WRAM layout, NOT a raw physical 1682-byte memcpy.
MACRO YEL012_STAGE_FIELD
	ld hl, sYel012TransactionShadow + \1
	ld a, [sYel012TransactionPage]
	and a
	jr z, .start\@
	ld bc, 20 * \2
	add hl, bc
.start\@
	ld de, \3
	ld a, [wBoxCount]
.loop\@
	and a
	jr z, .done\@
	push af
	ld bc, \2
	call CopyData
	pop af
	dec a
	jr .loop\@
.done\@
ENDM

Yel012StageWindow::
	cp 0
	jr z, .indexOK
	cp 20
	jr nz, .invalid
.indexOK
	push af
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	cp 1
	jr nz, .badPop
	pop af
	ld [sYel012TransactionPage], a
	ld b, a
	ld a, [sYel012TransactionShadow]
	sub b
	jr c, .invalidClose
	cp 20
	jr c, .countOK
	ld a, 20
.countOK
	ld [wBoxCount], a
	YEL012_STAGE_FIELD 1, 1, wBoxSpecies
	ld hl, wBoxSpecies
	ld a, [wBoxCount]
	ld e, a
	ld d, 0
	add hl, de
	ld [hl], $ff
	YEL012_STAGE_FIELD YEL012_SRAM_MON_OFFSET, BOXMON_STRUCT_LENGTH, wBoxMons
	YEL012_STAGE_FIELD YEL012_SRAM_OT_OFFSET, NAME_LENGTH, wBoxMonOT
	YEL012_STAGE_FIELD YEL012_SRAM_NICK_OFFSET, NAME_LENGTH, wBoxMonNicks
	call CloseSRAM
	and a
	ret
.badPop
	pop af
.invalidClose
	call CloseSRAM
.invalid
	scf
	ret
