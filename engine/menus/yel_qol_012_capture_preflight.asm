; YEL-QOL-012: authoritative physical SRAM capture-space preflight.
; Not yet wired into live battle code; all boxes must be initialized
; under the versioned SRAM layout before this entrypoint is used.
;
; A input: zero-based box index, returns HL physical box address,
; B physical SRAM bank 2/3/4. Clobbers DE and A.
Yel012ResolvePhysicalBox::
	ld b, 2
.bank
	cp 4
	jr c, .resolved
	sub 4
	inc b
	jr .bank
.resolved
	add a
	ld e, a
	ld d, 0
	ld hl, .physical
	add hl, de
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ret
.physical
	dw sBox1, sBox2, sBox3, sBox4

; Return carry clear and A=zero-based available box (including current),
; or carry set if uninitialized, corrupt, all full, or transaction active.
; Does not mutate wCurrentBoxNum or overwrite the working WRAM window.
; Fail closed on count/sentinel errors; no automatic box initialization.
Yel012FindCaptureBox::
	ld a, [wCurrentBoxNum]
	bit BIT_HAS_CHANGED_BOXES, a
	jp z, .rejected
	and BOX_NUM_MASK
	cp NUM_BOXES
	jp nc, .rejected
	push af
	ld a, 5
	call OpenSRAM
	ld a, [sYel012TransactionStatus]
	and a
	jp nz, .failPop
	call CloseSRAM
	pop af
	ld c, a
	ld d, NUM_BOXES
.scan
	push de
	push bc
	ld a, c
	call Yel012ResolvePhysicalBox
	ld a, b
	call OpenSRAM
	ld a, [hl]
	cp MONS_PER_BOX + 1
	jp nc, .corrupt
	ld e, a ; physical count
	push hl
	inc hl
	ld a, e
	ld d, 0
	ld e, a
	add hl, de
	ld a, [hl]
	pop hl
	cp $ff
	jp nz, .corrupt
	ld a, [hl]
	call CloseSRAM
	cp MONS_PER_BOX
	jr c, .found
	pop bc
	pop de
	inc c
	ld a, c
	cp NUM_BOXES
	jr c, .next
	ld c, 0
.next
	dec d
	jr nz, .scan
	scf
	ret
.found
	pop bc
	pop de
	ld a, c
	and a
	ret
.corrupt
	call CloseSRAM
	pop bc
	pop de
	scf
	ret
.failPop
	call CloseSRAM
	pop af
.rejected
	scf
	ret
