RedsHouse2F_Object:
	db $a ; border block

	def_warp_events
	warp_event  7,  1, REDS_HOUSE_1F, 3
IF DEF(_DEBUG)
	; Trainer-variant test entrance: real DEBUG map warp, not a RAM teleport.
	warp_event  7,  2, VIRIDIAN_FOREST, 7
	; Separate Youngster female fixture from the Bug Catcher forest fixture.
	warp_event  7,  3, ROUTE_3, 1
	warp_event  7,  4, ROUTE_3, 2
	warp_event  7,  5, SILPH_CO_11F, 4
ENDC

	def_bg_events

	def_object_events

	def_warps_to REDS_HOUSE_2F
