; YEL-DBL-001: inactive secondary-battler staging from ordinary party records.
; Input: A = zero-based party slot. Does not select doubles format.
; Do not invoke until scratch overlay lifetime has been proven safe.
StageDoublesPlayerSecondFromParty:
	ld [wDoublesPlayer2PartyIndex], a
	ld hl, wPartyMon1Species
	ld bc, PARTYMON_STRUCT_LENGTH
	call AddNTimes
	ld de, wDoublesPlayer2Species
	call CopyDoublesPartyFields
	ld a, [wDoublesPlayer2PartyIndex]
	ld hl, wPartyMonNicks
	call SkipFixedLengthTextEntries
	ld de, wDoublesPlayer2Nick
	ld bc, NAME_LENGTH
	call CopyData
	ld hl, wDoublesPlayer2Attack
	ld de, wDoublesPlayer2UnmodifiedAttack
	jr InitDoublesSecondStatSnapshot

StageDoublesEnemySecondFromParty:
	ld [wDoublesEnemy2PartyIndex], a
	ld hl, wEnemyMon1Species
	ld bc, PARTYMON_STRUCT_LENGTH
	call AddNTimes
	ld de, wDoublesEnemy2Species
	call CopyDoublesPartyFields
	ld a, [wDoublesEnemy2PartyIndex]
	ld hl, wEnemyMonNicks
	call SkipFixedLengthTextEntries
	ld de, wDoublesEnemy2Nick
	ld bc, NAME_LENGTH
	call CopyData
	ld hl, wDoublesEnemy2Attack
	ld de, wDoublesEnemy2UnmodifiedAttack
InitDoublesSecondStatSnapshot:
	ld bc, (NUM_STATS - 1) * 2
	call CopyData
	; DE now points to supplemental current Special Defense.
	; Initial fallback copies legacy Special into both SpD caches;
	; final independent species-SpD calculation is still required.
	ld h, d
	ld l, e
	dec hl
	dec hl
	push hl
	ld bc, 2
	call CopyData
	pop hl
	ld bc, 2
	call CopyData
	; Initialize all six legacy stat stages and independent SpD to 7.
	ld a, BASE_STAT_LEVEL
	ld b, NUM_STAT_MODS
.stageLoop
	ld [de], a
	inc de
	dec b
	jr nz, .stageLoop
	ld [de], a
	inc de
	xor a
	ld b, 3
.statusLoop
	ld [de], a
	inc de
	dec b
	jr nz, .statusLoop
	ret

; HL = beginning of standard party_struct; DE = second battle_struct.
; Reuses the exact vanilla offsets and does not mutate party/SRAM.
CopyDoublesPartyFields:
	ld bc, wBattleMonDVs - wBattleMonSpecies
	call CopyData
	ld bc, MON_DVS - MON_OTID
	add hl, bc
	ld bc, wBattleMonPP - wBattleMonDVs
	call CopyData
	ld bc, NUM_MOVES
	call CopyData
	ld bc, wBattleMonPP - wBattleMonLevel
	call CopyData
	ret

; Controlled volatile SRAM bank-4 transfer (NOT enabled in live battle).
; Inputs: B = previously selected SRAM bank (0..3);
;         C = 0 if SRAM previously disabled, nonzero if enabled.
; Caller must own SRAM access exclusively, know the previous state and keep
; interrupts/other SRAM users from changing that state during this call.
; The mapper has no readable selected-bank or enable-state registers.
; This routine does NOT derive either value from hardware.
; Carry set = invalid bank, NO bank or RAM-enable changes.
; Carry clear = complete transfer, prior bank/enable restored.
; WARNING: Scratch WRAM aliases are unsafe for active battle use; stage
; only in a deliberately controlled, non-overlapping test fixture.
CopyDoublesScratchToDedicatedSRAM:
	ld a, b
	cp 4
	jr nc, .badBank
	push bc
	push hl
	push de
	call EnableSRAM
	ld a, 4
	ld [rRAMB], a
	ld hl, wDoublesSecondaryBattleDataStart
	ld de, sDoublesSecondaryBattleDataStart
	ld bc, wDoublesSecondaryBattleDataEnd - wDoublesSecondaryBattleDataStart
	call CopyData
	jr RestoreDoublesSRAMContext
.badBank
	scf
	ret

CopyDoublesDedicatedSRAMToScratch:
	ld a, b
	cp 4
	jr nc, .badBank
	push bc
	push hl
	push de
	call EnableSRAM
	ld a, 4
	ld [rRAMB], a
	ld hl, sDoublesSecondaryBattleDataStart
	ld de, wDoublesSecondaryBattleDataStart
	ld bc, wDoublesSecondaryBattleDataEnd - wDoublesSecondaryBattleDataStart
	call CopyData
	jr RestoreDoublesSRAMContext
.badBank
	scf
	ret

RestoreDoublesSRAMContext:
	pop de
	pop hl
	pop bc
	ld a, b
	ld [rRAMB], a
	ld a, c
	and a
	jr nz, .wasEnabled
	call DisableSRAM
.wasEnabled
	and a ; clear carry after successful restore
	ret
