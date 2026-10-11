# Trainer gender counterparts: separate variant encoding

Approved design registry: `data/trainers/gender_counterparts.csv` (25 counterparts). Existing trainer class IDs, sprites, tables, Jr. Trainer ♂/♀ and Cooltrainer ♂/♀ remain unchanged.

## Implemented groundwork

The original opponent class format uses `OPP_ID_OFFSET = 200`, so appending 25 ordinary classes would overflow an 8-bit opponent ID. Instead, a map trainer's **party-number byte** uses bit 7 as an optional opposite-gender presentation variant. Its lower seven bits remain the existing trainer-party index.

- Define `TRAINER_F_VARIANT | 1` as the last argument of an `object_event` to select an alternate presentation for the first party of its existing class.
- The code stores the parsed selector in `wTrainerGenderVariant` (0 = original, 1 = opposite-gender). The class/opponent ID and `wTrainerNo` remain their original values.
- Original map events contain no variant bit and retain their behavior.
- The variant does not change party, payout, AI, encounter music or battle sprite until their display hooks are implemented.
- All 25 approved variants are eligible for this encoding; the implementation does not consume new class IDs or add sprite art.

Example of the final two arguments of a trainer map object: `OPP_BUG_CATCHER, TRAINER_F_VARIANT | 1`. (Requires a valid existing party #1 and appropriate event sprite.)

## Compatibility and outstanding validation

The class ID encoding and legacy battle logic are unchanged. The 7-bit party-number range allows IDs 1–127; existing trainer parties must be audited against that limit, as must every alternate map assignment. The variant byte is WRAM, not persistent save data; individual trainers are reconstructed from map events. Special scripted opponents, battle intros, saved end-battle dialogue, and gendered naming require follow-on tests.

Do not claim the 25 counterparts are player-visible yet. Next implementation: read `wTrainerGenderVariant` when preparing trainer names and sprite pointers, mapping all 25 approved entries to their alternate names and temporary base sprites. The fixed 12-character class-name storage needs a shortening policy for longer names.

## Checklist
- [x] Create approved design registry without renumbering existing classes.
- [x] Encode alternate presentation in map trainer-party byte and separate runtime variant storage.
- [ ] Wire alternate class names, original-sprite fallback, and trainer intro/music classification.
- [ ] Make map assignments for both genders and verify trainer-party indices.
- [ ] Run builds for regular/debug ROM and emulator battle tests.
- [ ] Produce new battle and overworld artwork.

The legacy `UNUSED_JUGGLER` and `CHIEF` entries remain untouched.
