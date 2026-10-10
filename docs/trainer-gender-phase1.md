# Trainer gender counterparts: Phase 1 registry

Approved roster: **25** counterparts, in `data/trainers/gender_counterparts.csv`. All existing trainer IDs remain unchanged. Existing Jr. Trainer ♂/♀ and Cooltrainer ♂/♀ remain unchanged; unique boss classes are outside scope.

## Blocking encoding constraint

`constants/trainer_constants.asm` defines `OPP_ID_OFFSET EQU 200` and `OPP_<CLASS> = 200 + class index`. Opponent identity is stored in a **byte** (`wEnemyMonOrTrainerClass`). With 47 existing classes, appending 25 new real class indices would yield indices 48–72; indices 56–72 would produce opponent IDs 256–272 and overflow a byte. Lowering 200 without a coordinated wild-species encoding migration is unsafe. **Do not append 25 entries to the current production tables** until the discriminator is redesigned.

The CSV is the canonical *design registry*, not executable class definitions. It is intentionally unreferenced by the ROM and introduces no new sprite assets. Thus no build behavior changes in this branch yet. This is a partial Phase 1 foundation, not a completed implementation.

## Implementer checklist

- [ ] Decouple trainer class identity from the one-byte `OPP_ID_OFFSET` wire representation; preserve species classification, encounter and battle save semantics.
- [ ] Add runtime male/female variant lookup, class names, original-portrait fallback, money, parties, AI and move-choice data.
- [ ] Update trainer encounter music classification and preserve Jessie/James special pictures.
- [ ] Validate trainer names within the fixed-length text limit (notably Bug Catcher, Pokémaniac, Bird Keeper).
- [ ] Compile standard, debug and VC targets; battle-test an existing class and both genders of a new class.
- [ ] Add new art and overworld mapping in later phases.

Original legacy `UNUSED_JUGGLER` and `CHIEF` remain untouched.
