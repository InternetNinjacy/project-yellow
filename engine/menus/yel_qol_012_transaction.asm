; YEL-QOL-012 transaction engine, isolated in ROM bank $3b.
; WARNING: callers must not use the legacy whole-box copy path. This
; provides an isolated transaction interface, not yet called from battle/PC.
; SRAM bank 5 contains the original, mutable shadow, window backup and
; incoming 55-byte capture. Status: 0 idle, 1 staged, 2 committing.
DEF YEL012_BOX_SIZE EQU MONS_PER_BOX * (1 + BOXMON_STRUCT_LENGTH + 2 * NAME_LENGTH) + 2
DEF YEL012_WINDOW_SIZE EQU 1122 ; 20-slot working window size; verify in symbol-map CI
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
	jp c, .slot
	sub 4
	inc b
	jp .bank
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
	jp nz, .loop
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
	jp nz, .each
	ret

; Stage a physical box to its rollback snapshot and mutable shadow.
; Back up the old WRAM working window before modifying it.
; On success carry clear, bank-5 transaction status=1.
Yel012BeginTransaction::
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	and a
	jp nz, .failClose
	ld hl, wBoxDataStart
	ld de, sYel012TransactionWindowBackup
	ld bc, YEL012_WINDOW_SIZE
	call CopyData
	ld a, [wCurrentBoxNum]
	and BOX_NUM_MASK
	cp NUM_BOXES
	jp nc, .failed
	call Yel012GetBoxSRAMLocation
	ld a, b
	call OpenSRAM
	ld a, [hl]
	cp MONS_PER_BOX + 1
	jp nc, .failed
	; The physical count and its terminator are validated before copying.
	ld c, a
	ld b, 0
	inc hl
	add hl, bc
	ld a, [hl]
	cp $ff
	jp nz, .failed
	call Yel012CopyPhysicalAndSnapshotZero
	jp c, .failed
	call Yel012ValidateShadow
	jp c, .failed
	ld a, 5
	call OpenSRAM
	ld a, [wCurrentBoxNum]
	and BOX_NUM_MASK
	ld [sYel012TransactionBox], a
	xor a
	ld [sYel012TransactionPagePending], a
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
	jp z, .start\@
	ld bc, 20 * \2
	add hl, bc
.start\@
	ld de, \3
	ld a, [wBoxCount]
.loop\@
	and a
	jp z, .done\@
	push af
	ld bc, \2
	call CopyData
	pop af
	dec a
	jp .loop\@
.done\@
ENDM

; Save a validated fixed-size staging page to the bank-5 shadow.
; Physical box remains unchanged until Yel012CommitTransaction.
MACRO YEL012_WRITE_FIELD
	ld de, sYel012TransactionShadow + \1
	ld a, [sYel012TransactionPage]
	and a
	jp z, .start\@
	ld hl, 20 * \2
	add hl, de
	ld d, h
	ld e, l
.start\@
	ld hl, \3
	ld a, [wBoxCount]
.loop\@
	and a
	jp z, .done\@
	push af
	ld bc, \2
	call CopyData
	pop af
	dec a
	jp .loop\@
.done\@
ENDM

Yel012StageWindow::
	cp 0
	jp z, .indexOK
	cp 20
	jp nz, .invalid
.indexOK
	push af
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	cp 1
	jp nz, .badPop
	ld a, [sYel012TransactionPagePending]
	and a
	jp nz, .badPop
	pop af
	ld [sYel012TransactionPage], a
	ld b, a
	ld a, [sYel012TransactionShadow]
	sub b
	jp c, .invalidClose
	cp 20
	jp c, .countOK
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
	ld a, 1
	ld [sYel012TransactionPagePending], a
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

; Commit a previously staged 0..19 or 20..29 page into bank-5
; shadow. No physical SRAM write occurs. All validation happens before
; any shadow bytes are changed, preserving the full rollback original.
Yel012CommitStagedWindow::
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	cp 1
	jp nz, .reject
	ld a, [sYel012TransactionPagePending]
	cp 1
	jp nz, .reject
	ld a, [sYel012TransactionPage]
	ld b, a
	ld a, [sYel012TransactionShadow]
	sub b
	jp c, .reject
	cp 20
	jp c, .expectedCount
	ld a, 20
.expectedCount
	ld b, a
	ld a, [wBoxCount]
	cp b
	jp nz, .reject
	; Require the window's species list to match each Pokémon record.
	ld hl, wBoxSpecies
	ld de, wBoxMons
	ld a, b
.checkNext
	and a
	jp z, .sentinel
	push af
	ld a, [hli]
	and a
	jp z, .badItem
	cp $ff
	jp z, .badItem
	ld c, a
	ld a, [de]
	cp c
	jp nz, .badItem
	push hl
	ld hl, BOXMON_STRUCT_LENGTH
	add hl, de
	ld d, h
	ld e, l
	pop hl
	pop af
	dec a
	jp .checkNext
.badItem
	pop af
	jp .reject
.sentinel
	ld a, [hl]
	cp $ff
	jp nz, .reject
	YEL012_WRITE_FIELD 1, 1, wBoxSpecies
	YEL012_WRITE_FIELD YEL012_SRAM_MON_OFFSET, BOXMON_STRUCT_LENGTH, wBoxMons
	YEL012_WRITE_FIELD YEL012_SRAM_OT_OFFSET, NAME_LENGTH, wBoxMonOT
	YEL012_WRITE_FIELD YEL012_SRAM_NICK_OFFSET, NAME_LENGTH, wBoxMonNicks
	xor a
	ld [sYel012TransactionPagePending], a
	call Yel012ValidateShadow
	push af
	call CloseSRAM
	pop af
	ret
.reject
	call CloseSRAM
	scf
	ret

; Compare BC bytes in the physical SRAM bank (HL) to staged WRAM (DE).
; Carry is set on a verification mismatch.
Yel012ComparePhysicalPage:
.loop
	ld a, [de]
	cp [hl]
	jp nz, .mismatch
	inc de
	inc hl
	dec bc
	ld a, b
	or c
	jp nz, .loop
	and a
	ret
.mismatch
	scf
	ret

; HL is either bank-5 original or bank-5 modified shadow.
; Copies both chunks to the selected physical box and verifies each.
; On success physical SRAM remains enabled for checksum update.
Yel012FlushSnapshotToPhysical:
	ld a, 5
	call OpenSRAM
	ld de, wBoxDataStart
	ld bc, YEL012_WINDOW_SIZE
	call CopyData
	push hl ; source second-chunk address in bank 5
	call Yel012GetBoxSRAMLocation
	ld d, h
	ld e, l
	ld a, b
	call OpenSRAM
	ld hl, wBoxDataStart
	ld bc, YEL012_WINDOW_SIZE
	call CopyData
	call Yel012GetBoxSRAMLocation
	ld de, wBoxDataStart
	ld bc, YEL012_WINDOW_SIZE
	call Yel012ComparePhysicalPage
	jp c, .firstFailed
	pop hl
	ld a, 5
	call OpenSRAM
	ld de, wBoxDataStart
	ld bc, YEL012_REMAINDER
	call CopyData
	call Yel012GetBoxSRAMLocation
	ld de, YEL012_WINDOW_SIZE
	add hl, de
	ld d, h
	ld e, l
	ld a, b
	call OpenSRAM
	ld hl, wBoxDataStart
	ld bc, YEL012_REMAINDER
	call CopyData
	call Yel012GetBoxSRAMLocation
	ld de, YEL012_WINDOW_SIZE
	add hl, de
	ld de, wBoxDataStart
	ld bc, YEL012_REMAINDER
	jp Yel012ComparePhysicalPage
.firstFailed
	pop hl
	scf
	ret

; Check count, species terminator and all occupied species header entries
; against the first byte of the corresponding 33-byte Pokémon data.
; Caller must have bank 5 SRAM enabled.
Yel012ValidateShadow:
	ld a, [sYel012TransactionShadow]
	cp MONS_PER_BOX + 1
	jp nc, .corrupt
	ld b, a
	ld c, a
	ld hl, sYel012TransactionShadow + 1
	ld e, c
	ld d, 0
	add hl, de
	ld a, [hl]
	cp $ff
	jp nz, .corrupt
	ld de, sYel012TransactionShadow + 1
	ld hl, sYel012TransactionShadow + YEL012_SRAM_MON_OFFSET
	ld a, b
	and a
	jp z, .valid
.loop
	ld a, [de]
	and a
	jp z, .corrupt
	cp $ff
	jp z, .corrupt
	cp [hl]
	jp nz, .corrupt
	inc de
	push bc
	ld bc, BOXMON_STRUCT_LENGTH
	add hl, bc
	pop bc
	dec b
	jp nz, .loop
.valid
	and a
	ret
.corrupt
	scf
	ret

; Stage a single occupied 0..29 record into the transaction shadow.
; A slot, DE complete 55-byte WRAM record; carry on invalid status,
; pending page, invalid species or unoccupied index.
; The authoritative SRAM box is not touched until final commit.
Yel012StageRecordReplacement::
	cp MONS_PER_BOX
	ret nc
	push af
	push de
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	cp 1
	jp nz, .badStack
	ld a, [sYel012TransactionPagePending]
	and a
	jp nz, .badStack
	pop hl
	ld a, [hl]
	and a
	jp z, .badSlotStack
	cp $ff
	jp z, .badSlotStack
	ld de, sYel012TransactionNewRecord
	ld bc, YEL012_RECORD_BUFFER_SIZE
	call CopyData
	pop af
	ld b, a
	ld a, [sYel012TransactionShadow]
	cp b
	jp c, .invalidOpen
	jp z, .invalidOpen
	ld a, b
	ld c, 1
	ld hl, sYel012TransactionShadow
	ld de, sYel012TransactionNewRecord
	YEL012_COPY_FIELD YEL012_SRAM_MON_OFFSET, BOXMON_STRUCT_LENGTH, BOXMON_STRUCT_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_OT_OFFSET, NAME_LENGTH, NAME_LENGTH
	YEL012_COPY_FIELD YEL012_SRAM_NICK_OFFSET, NAME_LENGTH, NAME_LENGTH
	ld e, b
	ld d, 0
	ld hl, sYel012TransactionShadow + 1
	add hl, de
	ld a, [sYel012TransactionNewRecord]
	ld [hl], a
	call Yel012ValidateShadow
	push af
	call CloseSRAM
	pop af
	ret
.badStack
	pop de
.badSlotStack
	pop af
.invalidOpen
	call CloseSRAM
	scf
	ret

; Prepare a new captured Pokémon in the bank-5 transaction, but do not
; write the live physical box. Caller passes DE -> 55-byte WRAM record.
; Carry set on absent transaction, invalid Pokémon, or full box.
Yel012PrepareCaptureInsert::
	push de
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	cp 1
	jp nz, .failPop
	ld a, [sYel012TransactionPagePending]
	and a
	jp nz, .failPop
	ld a, [sYel012TransactionShadow]
	cp MONS_PER_BOX
	jp nc, .failPop
	pop hl
	push hl
	ld a, [hl]
	and a
	jp z, .failPop
	cp $ff
	jp z, .failPop
	ld de, sYel012TransactionNewRecord
	ld bc, YEL012_RECORD_BUFFER_SIZE
	call CopyData
	pop de
	; Shadow is altered only after complete input is safely staged.
	ld a, [sYel012TransactionShadow]
	ld hl, sYel012TransactionShadow + 1
	ld de, 1
	call Yel012ShiftFieldRight
	ld a, [sYel012TransactionShadow]
	ld hl, sYel012TransactionShadow + YEL012_SRAM_MON_OFFSET
	ld de, BOXMON_STRUCT_LENGTH
	call Yel012ShiftFieldRight
	ld a, [sYel012TransactionShadow]
	ld hl, sYel012TransactionShadow + YEL012_SRAM_OT_OFFSET
	ld de, NAME_LENGTH
	call Yel012ShiftFieldRight
	ld a, [sYel012TransactionShadow]
	ld hl, sYel012TransactionShadow + YEL012_SRAM_NICK_OFFSET
	ld de, NAME_LENGTH
	call Yel012ShiftFieldRight
	ld hl, sYel012TransactionNewRecord
	ld a, [hl]
	ld [sYel012TransactionShadow + 1], a
	ld de, sYel012TransactionShadow + YEL012_SRAM_MON_OFFSET
	ld bc, BOXMON_STRUCT_LENGTH
	call CopyData
	ld de, sYel012TransactionShadow + YEL012_SRAM_OT_OFFSET
	ld bc, NAME_LENGTH
	call CopyData
	ld de, sYel012TransactionShadow + YEL012_SRAM_NICK_OFFSET
	ld bc, NAME_LENGTH
	call CopyData
	ld hl, sYel012TransactionShadow
	inc [hl]
	ld c, [hl]
	ld b, 0
	inc hl
	add hl, bc
	ld [hl], $ff
	call Yel012ValidateShadow
	push af
	call CloseSRAM
	pop af
	ret
.failPop
	pop de
	call CloseSRAM
	scf
	ret

; Overlap-safe backwards shift by one record within SRAM bank 5.
; Input HL=field start, DE=field stride, A=number of occupied records.
Yel012ShiftFieldRight:
	ld bc, 0
	and a
	ret z
.count
	add hl, de
	push hl
	ld h, b
	ld l, c
	add hl, de
	ld b, h
	ld c, l
	pop hl
	dec a
	jp nz, .count
	dec hl
	push hl
	add hl, de
	ld d, h
	ld e, l
	pop hl
.move
	ld a, [hld]
	ld [de], a
	dec de
	dec bc
	ld a, b
	or c
	jp nz, .move
	ret

; Abort a staged transaction, leave physical SRAM untouched and restore
; all 1122 bytes of the caller's original working-box window.
Yel012AbortTransaction::
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	cp 1
	jp nz, .invalid
	call Yel012RestoreWindow
	xor a
	ld [sYel012TransactionStatus], a
	call CloseSRAM
	and a
	ret
.invalid
	call CloseSRAM
	scf
	ret

; Check all shadow records before writing; verify both physical chunks.
; If either physical write fails verification, restore the original
; physical bytes from the saved snapshot and recompute checksums.
; This is runtime rollback; unexpected power loss requires boot recovery.
Yel012CommitTransaction::
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	cp 1
	jp nz, .invalid
	ld a, [wCurrentBoxNum]
	and BOX_NUM_MASK
	ld b, a
	ld a, [sYel012TransactionBox]
	cp b
	jp nz, .invalid
	ld a, [sYel012TransactionPagePending]
	and a
	jp nz, .invalid
	call Yel012ValidateShadow
	jp c, .invalid
	ld a, 2
	ld [sYel012TransactionStatus], a
	ld hl, sYel012TransactionShadow
	call Yel012FlushSnapshotToPhysical
	jp c, .rollback
	call Yel012RefreshPhysicalChecksums
	jp .success
.rollback
	ld hl, sYel012TransactionBackup
	call Yel012FlushSnapshotToPhysical
	jp c, .rollbackFailed
	call Yel012RefreshPhysicalChecksums
	ld a, 5
	call OpenSRAM
	call Yel012RestoreWindow
	xor a
	ld [sYel012TransactionStatus], a
	call CloseSRAM
	scf
	ret
.success
	ld a, 5
	call OpenSRAM
	call Yel012RestoreWindow
	xor a
	ld [sYel012TransactionStatus], a
	call CloseSRAM
	and a
	ret
.rollbackFailed
	; Keep status=2 to signal an incomplete transaction on next boot.
	call CloseSRAM
	scf
	ret
.invalid
	call CloseSRAM
	scf
	ret
