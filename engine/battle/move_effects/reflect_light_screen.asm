ReflectLightScreenEffect_:
	ld hl, wPlayerBattleStatus3
	ld de, wPlayerMoveEffect
	ldh a, [hWhoseTurn]
	and a
	jr z, .selectEffect
	ld hl, wEnemyBattleStatus3
	ld de, wEnemyMoveEffect
.selectEffect
	ld a, [de]
	cp LIGHT_SCREEN_EFFECT
	jr nz, .reflect
	ld de, wPlayerLightScreenTurns
	ldh a, [hWhoseTurn]
	and a
	jr z, .checkLightScreen
	ld de, wEnemyLightScreenTurns
.checkLightScreen
	ld a, [de]
	and a
	jr nz, .moveFailed
	set HAS_LIGHT_SCREEN_UP, [hl]
	ld a, 5
	ld [de], a
	ld hl, LightScreenProtectedText
	jr .playAnim
	push hl
	ld hl, PlayCurrentMoveAnimation
	call EffectCallBattleCore
	pop hl
	jp PrintText
.moveFailed
	ld c, 50
	call DelayFrames
	ld hl, PrintButItFailedText_
	jp EffectCallBattleCore

LightScreenProtectedText:
	text_far _LightScreenProtectedText
	text_end

ReflectGainedArmorText:
	text_far _ReflectGainedArmorText
	text_end

EffectCallBattleCore:
	ld b, BANK(BattleCore)
	jp Bankswitch
