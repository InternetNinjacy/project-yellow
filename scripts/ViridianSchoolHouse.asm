ViridianSchoolHouse_Script:
	call EnableAutoTextBoxDrawing
	ret

; YEL-CHALLENGE-001: both legitimate battle outcomes go through this
; shared completion entry point AFTER the battle engine has returned.
; The true doubles caller must invoke this on victory and defeat (including
; whiteout recovery) rather than setting the event at battle start.
ViridianSchoolHouseCompleteLessonAfterBattle:
	CheckEvent EVENT_VIRIDIAN_SCHOOL_GIFT_CLAIMED
	ret z ; do not unlock the Mart before the permanent gift exists
	SetEvent EVENT_VIRIDIAN_SCHOOL_LESSON_COMPLETE
	ret

ViridianSchoolHouse_TextPointers:
	def_text_pointers
	dw_const ViridianSchoolHouseBrunetteGirlText, TEXT_VIRIDIANSCHOOLHOUSE_BRUNETTE_GIRL
	dw_const ViridianSchoolHouseCooltrainerFText, TEXT_VIRIDIANSCHOOLHOUSE_COOLTRAINER_F
	dw_const ViridianSchoolHouseLittleGirlText,   TEXT_VIRIDIANSCHOOLHOUSE_LITTLE_GIRL

ViridianSchoolHouseBrunetteGirlText:
	text_far _ViridianSchoolHouseBrunetteGirlText
	text_end

ViridianSchoolHouseCooltrainerFText:
	text_asm
	farcall ViridianSchoolHousePrintCooltrainerFText
	jp TextScriptEnd

ViridianSchoolHouseLittleGirlText:
	text_asm
	farcall ViridianSchoolHousePrintLittleGirlText
	jp TextScriptEnd
