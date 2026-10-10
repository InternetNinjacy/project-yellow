SECTION "Sprite Buffers", SRAM

sSpriteBuffer0:: ds SPRITEBUFFERSIZE
sSpriteBuffer1:: ds SPRITEBUFFERSIZE
sSpriteBuffer2:: ds SPRITEBUFFERSIZE

	ds $100

sHallOfFame:: ds HOF_TEAM * HOF_TEAM_CAPACITY


SECTION "Save Data", SRAM

	ds $598

sGameData::
sPlayerName::  ds NAME_LENGTH
sMainData::    ds wMainDataEnd - wMainDataStart
sSpriteData::  ds wSpriteDataEnd - wSpriteDataStart
sPartyData::   ds wPartyDataEnd - wPartyDataStart
sCurBoxData::  ds wBoxDataEnd - wBoxDataStart
sTileAnimations:: db
sGameDataEnd::
sMainDataCheckSum:: db


; The PC boxes will not fit into one SRAM bank,
; so they use multiple SECTIONs
DEF box_n = 0
MACRO boxes
	REPT \1
		DEF box_n += 1
	sBox{d:box_n}:: ds wBoxDataEnd - wBoxDataStart
	ENDR
ENDM

SECTION "Saved Boxes 1", SRAM
	boxes 4
sBank2AllBoxesChecksum:: db
sBank2IndividualBoxChecksums:: ds 4

SECTION "Saved Boxes 2", SRAM
	boxes 4
sBank3AllBoxesChecksum:: db
sBank3IndividualBoxChecksums:: ds 4

SECTION "YEL012 Transaction Backup", SRAM
sYel012TransactionBackup:: ds 1682
sYel012TransactionNewRecord:: ds 55

SECTION "Saved Boxes 3", SRAM
	boxes 4
sBank4AllBoxesChecksum:: db
sBank4IndividualBoxChecksums:: ds 4

; Twelve 30-mon boxes occupy three distinct SRAM banks
	ASSERT box_n == NUM_BOXES, \
		"boxes: Expected {d:NUM_BOXES} total boxes, got {d:box_n}"

ENDSECTION
