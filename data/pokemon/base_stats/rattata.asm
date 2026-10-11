	db DEX_RATTATA ; pokedex id

	db  40,  65,  40,  80,  25
	;   hp  atk  def  spd  spc

	db DARK, DARK ; type
	db 255 ; catch rate
	db 57 ; base exp

	INCBIN "gfx/pokemon/front/rattata.pic", 0, 1 ; sprite dimensions
	dw RattataPicFront, RattataPicBack

	db TACKLE, TAIL_WHIP, NO_MOVE, NO_MOVE ; level 1 learnset
	db GROWTH_MEDIUM_FAST ; growth rate

	; tm/hm learnset (approved set; TM34 pending Poison Fang remap)
	tmhm BODY_SLAM, DOUBLE_EDGE, HYPER_BEAM, RAGE, DIG, \
	     TOXIC, MIMIC, DOUBLE_TEAM, REST, SUBSTITUTE, POISON_FANG, \
	     CUT
	; end

	db 0 ; padding
