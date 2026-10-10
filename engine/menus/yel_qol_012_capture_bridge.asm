; YEL-QOL-012: capture-to-transaction bridge.
; This is compiled but NOT connected to live battle or gift callsites.
; It must only be enabled after the physical save format/box preflight is
; made authoritative. It deliberately reuses the original nickname flow
; with a one-Pokemon empty working window (never shifts 30 in WRAM).
;
; Entry: physically initialized current box (0..29 occupants), and all
; battle capture state required by SendNewMonToBox is already prepared.
; Carry clear if physical commit succeeded; carry set on failure.
; On success or ordinary abort the prior 1122-byte WRAM box window is
; restored. Callers must check carry, not display success on a failure.
Yel012CaptureToBoxTransaction::
	call Yel012BeginTransaction
	jp c, .fail
	; The legacy routine constructs species + mon bytes + names, but
	; operates on a temporary EMPTY one-slot window instead of the 30-box.
	xor a
	ld [wBoxCount], a
	ld a, $ff
	ld [wBoxSpecies], a
	callfar SendNewMonToBox
	; Assemble the three separate Gen-I working arrays into one 55-byte
	; contiguous transient record. Source is higher than destination,
	; so forward copying of the 33-byte mon block is overlap-safe.
	ld hl, wBoxMon1
	ld de, wBoxDataStart
	ld bc, BOXMON_STRUCT_LENGTH
	call CopyData
	ld hl, wBoxMon1OT
	ld de, wBoxDataStart + BOXMON_STRUCT_LENGTH
	ld bc, NAME_LENGTH
	call CopyData
	ld hl, wBoxMon1Nick
	ld de, wBoxDataStart + BOXMON_STRUCT_LENGTH + NAME_LENGTH
	ld bc, NAME_LENGTH
	call CopyData
	ld de, wBoxDataStart
	call Yel012PrepareCaptureInsert
	jp c, .abort
	call Yel012CommitTransaction
	jp c, .abort
	and a
	ret
.abort
	; A write-verification failure may leave status=2 for recovery.
	; Do not clear that status or claim that physical rollback succeeded.
	call Yel012AbortTransaction
.fail
	scf
	ret

; Execute a capture insertion against the first valid physical target
; without invoking legacy 1122-byte whole-box swaps. The box selection
; is temporary: preserve player-visible current box and legacy window.
; Caller MUST gate caught text, Pokédex, and ball consumption on carry.
; Not a replacement for the full live ItemUseBall state machine yet.
Yel012CaptureToAvailableBox::
	call Yel012FindCaptureBox
	ret c
	ld b, a
	ld a, [wCurrentBoxNum]
	push af
	ld a, b
	set BIT_HAS_CHANGED_BOXES, a
	ld [wCurrentBoxNum], a
	call Yel012CaptureToBoxTransaction
	; Save the transaction return flags before restoring selection.
	push af
	pop bc
	pop af
	ld [wCurrentBoxNum], a
	push bc
	pop af
	ret
