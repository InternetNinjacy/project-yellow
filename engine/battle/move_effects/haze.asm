; YEL-BAL-002: Haze only clears the active battlers' stat stages.
; It does not cure persistent/volatile status, clear team screens or reset
; unrelated battle flags. The independent Sp. Def cache is battle-only.
HazeEffect_:
	ld a, BASE_STAT_LEVEL
	ld hl, wPlayerMonAttackMod
	call ResetStatMods
	ld hl, wEnemyMonAttackMod
	call ResetStatMods
	; Revert the original four non-HP battle stats to their unmodified values.
	ld hl, wPlayerMonUnmodifiedAttack
	ld de, wBattleMonAttack
	call ResetStats
	ld hl, wEnemyMonUnmodifiedAttack
	ld de, wEnemyMonAttack
	call ResetStats
	; Reset supplemental Special Defense on both sides independently.
	ld a, BASE_STAT_LEVEL
	ld [wPlayerSpecialDefenseMod], a
	ld [wEnemySpecialDefenseMod], a
	ld hl, wPlayerUnmodifiedSpecialDefense
	ld de, wPlayerSpecialDefense
	ld bc, 2
	call CopyData
	ld hl, wEnemyUnmodifiedSpecialDefense
	ld de, wEnemySpecialDefense
	ld bc, 2
	call CopyData
	ld hl, PlayCurrentMoveAnimation
	call CallBankF
	ld hl, StatusChangesEliminatedText
	jp PrintText

ResetStatMods:
	ld b, NUM_STAT_MODS
.loop
	ld [hli], a
	dec b
	jr nz, .loop
	ret

ResetStats:
	ld b, (NUM_STATS - 1) * 2 ; excludes HP
.loop
	ld a, [hli]
	ld [de], a
	inc de
	dec b
	jr nz, .loop
	ret

StatusChangesEliminatedText:
	text_far _StatusChangesEliminatedText
	text_end
