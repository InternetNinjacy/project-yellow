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

; Non-mutating bridge between the physical 30-slot scan and a future
; capture transaction. Callers MUST NOT use this result as permission to
; run legacy CopyBoxToOrFromSRAM / AutoSwitchBoxForCapture.
;
; Returns: carry clear, A = selected zero-based box index (0..11).
;          carry set on uninitialized, corrupt, active transaction or full.
; This deliberately leaves wCurrentBoxNum and the 20-slot WRAM window
; untouched. The later live hook must establish a versioned 30-slot save,
; atomically select the returned box and only then invoke
; Yel012CaptureToBoxTransaction; it must not announce a caught Pokémon
; before a successful physical commit.
Yel012PreflightCaptureTarget::
	call Yel012FindCaptureBox
	ret


; Explicit new-game-only storage initializer. Never call from the ball
; path, Continue, or a generic "missing marker" recovery path.
; SRAM banks 2..4 contain twelve physical 1682-byte boxes.
DEF YEL012_STORAGE_VERSION EQU 1
DEF YEL012_STORAGE_VERSION_CHECK EQU $fe

Yel012InitializeFreshStorage::
	; Invalidate the marker BEFORE modifying any physical boxes.
	ld a, 5
	call OpenSRAM
	xor a
	ld [sYel012StorageVersion], a
	ld [sYel012StorageVersionCheck], a
	ld [sYel012TransactionStatus], a
	ld [sYel012TransactionPagePending], a
	call CloseSRAM
	ld c, 0
.boxLoop
	push bc
	ld a, c
	call Yel012ResolvePhysicalBox
	ld a, b
	call OpenSRAM
	; Fully clear the box, not just its count and sentinel, so that
	; future checksum validation cannot depend on old SRAM bytes.
	ld bc, YEL012_BOX_SIZE
	push hl
.clear
	xor a
	ld [hli], a
	dec bc
	ld a, b
	or c
	jr nz, .clear
	pop hl
	inc hl
	ld [hl], $ff
	call CloseSRAM
	pop bc
	inc c
	ld a, c
	cp NUM_BOXES
	jr c, .boxLoop
	ld b, 2
.checksumBanks
	push bc
	ld a, b
	call OpenSRAM
	call Yel012RefreshPhysicalChecksums
	call CloseSRAM
	pop bc
	inc b
	ld a, b
	cp 5
	jr c, .checksumBanks
	ld a, 5
	call OpenSRAM
	ld a, YEL012_STORAGE_VERSION
	ld [sYel012StorageVersion], a
	ld a, YEL012_STORAGE_VERSION_CHECK
	ld [sYel012StorageVersionCheck], a
	call CloseSRAM
	and a
	ret

; Strict version predicate: carry clear only for explicitly initialized
; layout. An absent/bad version is never a request to erase storage.
Yel012CheckStorageVersion::
	ld a, 5
	call OpenSRAM
	ld a, [sYel012StorageVersion]
	cp YEL012_STORAGE_VERSION
	jr nz, .bad
	ld a, [sYel012StorageVersionCheck]
	cp YEL012_STORAGE_VERSION_CHECK
	jr nz, .bad
	call CloseSRAM
	and a
	ret
.bad
	call CloseSRAM
	scf
	ret
