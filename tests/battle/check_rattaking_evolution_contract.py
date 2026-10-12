#!/usr/bin/env python3
"""Source-level evolution contract; NOT a substitute for in-game SAVE/CONTINUE."""
from pathlib import Path
import re
evos=Path("data/pokemon/evos_moves.asm").read_text()
dex=Path("constants/pokedex_constants.asm").read_text()
species=Path("constants/pokemon_constants.asm").read_text()
stats=Path("data/pokemon/base_stats/rattaking.asm").read_text()
checks={
    "Rattata evolves at level 18": r"RattataEvosMoves:\s*; Evolutions\s*db EVOLVE_LEVEL, 18, RATICATE",
    "Raticate evolves to Rattaking at level 36": r"RaticateEvosMoves:\s*; Evolutions\s*db EVOLVE_LEVEL, 36, RATTAKING",
    "Rattaking has a terminal evolution record": r"RattakingEvosMoves:\s*; Evolutions\s*db 0",
    "Rattaking has a pointer": r"dw RattakingEvosMoves",
}
for name,pattern in checks.items():
    if not re.search(pattern,evos):
        raise AssertionError(name+" not wired")
    print("PASS source:",name)
assert re.search(r"const RATTAKING\s*; \$BF",species)
assert "DEX_RATTAKING" in dex
assert "DEX_RATTAKING" in stats and "db DARK, DARK" in stats
print("PASS source: Rattaking species, dex and pure Dark base-stat record")
print("NOT TESTED: real level-up evolution animation, SRAM SAVE and CONTINUE")
