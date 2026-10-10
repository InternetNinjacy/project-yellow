GetTrainerName_::
	ld hl, wLinkEnemyTrainerName
	ld a, [wLinkState]
	and a
	jr nz, .foundName
	ld hl, wRivalName
	ld a, [wTrainerClass]
	cp RIVAL1
	jr z, .foundName
	cp RIVAL2
	jr z, .foundName
	cp RIVAL3
	jr z, .foundName
	ld [wNameListIndex], a
	ld a, TRAINER_NAME
	ld [wNameListType], a
	ld a, BANK(TrainerNames)
	ld [wPredefBank], a
	call GetName
	ld hl, wNameBuffer
.foundName
	ld de, wTrainerName
	ld bc, TRAINER_NAME_LENGTH
	call CopyData
	; The opponent class and party data never change for presentation variants.
	ld a, [wTrainerGenderVariant]
	and a
	ret z
	ld a, [wTrainerClass]
	ld b, a
	ld hl, TrainerVariantClasses
	ld c, 0
.findVariant
	ld a, [hli]
	cp b
	jr z, .variantFound
	inc c
	ld a, c
	cp NUM_TRAINER_GENDER_VARIANTS
	ret z
	jr .findVariant
.variantFound
	ld a, c
	ld hl, TrainerVariantNames
	ld bc, TRAINER_NAME_LENGTH
	call AddNTimes
	ld de, wTrainerName
	ld bc, TRAINER_NAME_LENGTH
	jp CopyData

DEF NUM_TRAINER_GENDER_VARIANTS EQU 25
TrainerVariantClasses:
	db YOUNGSTER
	db BUG_CATCHER
	db LASS
	db SAILOR
	db POKEMANIAC
	db SUPER_NERD
	db HIKER
	db BIKER
	db BURGLAR
	db ENGINEER
	db FISHER
	db SWIMMER
	db CUE_BALL
	db GAMBLER
	db BEAUTY
	db PSYCHIC_TR
	db ROCKER
	db JUGGLER
	db TAMER
	db BIRD_KEEPER
	db BLACKBELT
	db SCIENTIST
	db ROCKET
	db GENTLEMAN
	db CHANNELER

TrainerVariantNames:
	list_start TRAINER_NAME_LENGTH - 1
	li "YOUNGSTER♀"
	li "BUG CATCHR♀"
	li "LAD"
	li "SAILOR♀"
	li "POKéMANIAC♀"
	li "SUPER NERD♀"
	li "HIKER♀"
	li "BIKER♀"
	li "BURGLAR♀"
	li "ENGINEER♀"
	li "FISHERMAN♀"
	li "SWIMMER♀"
	li "TOUGH GIRL"
	li "GAMBLER♀"
	li "HIMBO"
	li "PSYCHIC♀"
	li "ROCKER♀"
	li "JUGGLER♀"
	li "TAMER♀"
	li "BIRDKEEPER♀"
	li "BLACKBELT♀"
	li "SCIENTIST♀"
	li "ROCKET♀"
	li "GRANDMA"
	li "CHANNELER♂"
	assert_list_length NUM_TRAINER_GENDER_VARIANTS

