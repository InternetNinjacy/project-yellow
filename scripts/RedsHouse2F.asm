RedsHouse2F_Script:
IF DEF(_DEBUG)
	call YelTest005DebugCaptureEncounter
ENDC
	call EnableAutoTextBoxDrawing
	ld hl, RedsHouse2F_ScriptPointers
	ld a, 0
	call CallFunctionInTable
	ret

RedsHouse2F_ScriptPointers:
	def_script_pointers
	dw_const RedsHouse2FDefaultScript, SCRIPT_REDSHOUSE2F_DEFAULT0
	dw_const RedsHouse2FDefaultScript, SCRIPT_REDSHOUSE2F_DEFAULT1
	dw_const RedsHouse2FDefaultScript, SCRIPT_REDSHOUSE2F_DEFAULT2
	dw_const RedsHouse2FDefaultScript, SCRIPT_REDSHOUSE2F_DEFAULT3
	dw_const RedsHouse2FDefaultScript, SCRIPT_REDSHOUSE2F_DEFAULT4

RedsHouse2FDefaultScript:
	ret

RedsHouse2F_TextPointers:
	def_text_pointers

	text_end ; unused

IF DEF(_DEBUG)
; YEL-TEST-005 capture station, release-invisible.
; Activate ONCE when the player walks to (2,7) in the upstairs room
; with six party members. The overworld's standard battle dispatcher
; handles wCurOpponent; no emulator writes or battle-engine overrides.
YelTest005DebugCaptureEncounter:
	ld a, [wRedsHouse2FCurScript]
	and a
	ret nz
	ld a, [wPartyCount]
	cp PARTY_LENGTH
	ret nz
	ld a, [wXCoord]
	cp 2
	ret nz
	ld a, [wYCoord]
	cp 7
	ret nz
	ld a, PIDGEY
	ld [wCurOpponent], a
	ld a, 3
	ld [wCurEnemyLevel], a
	ld a, 1
	ld [wRedsHouse2FCurScript], a
	ret
ENDC
