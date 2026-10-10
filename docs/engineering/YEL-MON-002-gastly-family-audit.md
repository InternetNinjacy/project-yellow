# YEL-MON-002: Gastly family audit and staged changes

Status: changes committed to isolated branch. No ROM build or emulator verification yet.
Parent: feature/yel-mon-001-pidgey-weedle.

## Decision hierarchy
The final October 9, 2026 approval is PURE GHOST for Gastly, Haunter, and Gengar. The former Ghost/Fire proposal is obsolete. Keep this correction when consolidating Pokémon registries.

## Approved design
- Pure Ghost typing for all three species.
- Sleep-focused special-attack identity.
- Hypnosis: Gastly L16, Haunter L18, Gengar L20.
- Dream Eater: Gastly L32, Haunter L34, Gengar L36.
- Shadow Ball: special Ghost attack, base power 80; Gastly L44, Haunter L46, Gengar L48. Not yet implemented; confirm move constant, animation, category, and storage/index capacity before adding.
- Haunter evolves to Gengar either when traded or at level 40.
- Gengar HP 60 / Atk 65 / Def 60 / SpA 130 / SpD 67 / Speed 110 (BST 492). Gastly and Haunter custom full six-stat targets have NOT been recovered; retain their current values pending the original approvals.

## Changes now staged
- All three species changed GHOST/POISON -> GHOST/GHOST in legacy dual-type byte format.
- Six-stat supplementary table Gengar SpD 75 -> 67 (SpA remains 130).
- Level-up sleep moves changed to approved levels.
- Added Haunter L40 evolution alongside trade evolution. Runtime processing of simultaneous alternatives must be tested; no claim of operational behavior.

## Open technical gates
- YEL-BAL-002: independent SpA/SpD runtime wiring, save compatibility, and battle calculations.
- Add Shadow Ball with proper move ID, 80-power Ghost type, special category, level-up distributions, and functional battle behavior.
- Validate both Haunter evolution methods, including trade, level-up, and potentially edge cases around traded Haunter.
- Check Ghost monotype behavior in effectiveness calculations and party info displays.
- Recover Gastly/Haunter approved six-stat targets and any remaining move/TM specifics.
- Build and emulator test, including save/continue. None done here.

Do not merge to master until integration/testing gates pass. This project is Project Yellow, NOT Sam Edition.
