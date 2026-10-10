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
	; Record layout places the unmodified legacy Special immediately
	; before the two supplemental SpD fields. Fallback until the distinct
	; species SpD derivation is integrated; cannot enable doubles yet.
	ld h, d
	ld l, e
	dec hl
	dec hl
	ld a, [hli]
	ld [de], a
	inc de
	ld a, [hl]
	ld [de], a
	inc de
	ld a, [hld]
	ld [de], a
	inc de
	ld a, [hl]
	ld [de], a
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
