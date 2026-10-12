	db DEX_RATICATE ; pokedex id

	db  65,  85,  60,  95,  45
	;   hp  atk  def  spd  spc

	db DARK, DARK ; type
	db 90 ; catch rate
	db 116 ; base exp

	INCBIN "gfx/pokemon/front/raticate.pic", 0, 1 ; sprite dimensions
	dw RaticatePicFront, RaticatePicBack

	db TACKLE, TAIL_WHIP, QUICK_ATTACK, NO_MOVE ; level 1 learnset
	db GROWTH_MEDIUM_FAST ; growth rate

	; tm/hm learnset (approved set; TM34 pending Poison Fang remap)
	tmhm MEGA_PUNCH, MEGA_KICK, BODY_SLAM, DOUBLE_EDGE, HYPER_BEAM, \
	     RAGE, DIG, TOXIC, MIMIC, DOUBLE_TEAM, \
	     REST, SUBSTITUTE, POISON_FANG, SKULL_BASH, CUT, STRENGTH
	; end

	db 0 ; padding
