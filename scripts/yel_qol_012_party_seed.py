"""Synthetic six-member WRAM party fixture, entirely test-only.

This is NOT evidence that Pokémon were acquired through gameplay.
It avoids CPU-entry trampolines; future battle, Poké Ball, SAVE and
CONTINUE must still execute the ROM using real controller inputs.
"""
PARTY_RECORD_BYTES = 44
ROSTER=(1,2,3,4,5,6)  # valid Generation I internal species indices
def seed_six_party(memory, syms):
    required=("wPartyCount","wPartySpecies","wPartyMon1","wPartyMon1OT","wPartyMon1Nick")
    missing=[name for name in required if name not in syms]
    if missing:raise ValueError("missing symbols "+", ".join(missing))
    mem=lambda name:syms[name][1]
    memory[mem("wPartyCount")]=6
    for i,species in enumerate(ROSTER):
        memory[mem("wPartySpecies")+i]=species
    memory[mem("wPartySpecies")+6]=255
    for index,species in enumerate(ROSTER):
        rec=bytearray(PARTY_RECORD_BYTES)
        rec[0]=species
        rec[1:3]=bytes((0,40)) # current HP
        rec[3]=5 # level
        rec[8]=33 # TACKLE
        rec[29]=35 # PP
        rec[33]=5 # party level
        rec[34:44]=bytes((0,40, 0,25, 0,25, 0,25, 0,25))
        base=mem("wPartyMon1")+index*PARTY_RECORD_BYTES
        for j,byte in enumerate(rec):memory[base+j]=byte
        for field,prefix in (("wPartyMon1OT",0x80),("wPartyMon1Nick",0x81)):
            # Standard Gen I name terminator $50.
            location=mem(field)+11*index
            for j in range(11): memory[location+j]=(prefix+index if j<10 else 0x50)
    return {"fixture":"TEST_ONLY_SYNTHETIC_WRAM_PARTY",
            "count":6,"species":list(ROSTER)}
