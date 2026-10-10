# YEL-CHALLENGE-001 — Viridian Doubles Training School

Status: **approved design; implementation preparation only**. This file is not evidence that double battles or the event are playable.

## Source-confirmed integration points (master, reviewed 2026-10-10)

- `data/maps/objects/ViridianCity.asm`: Poké Mart entrance warp at (29,19); school entrance warp at (21,15). The sleeping old man currently occupies (18,9). The source has eight existing NPC objects; do not shift object IDs without revisiting toggles and sprite references.
- `scripts/ViridianCity.asm`: `ViridianCityDefaultScript` calls `ViridianCityCheckSleepingOldMan`. The original old-man script and catching-training state must be preserved.
- `scripts/ViridianMart.asm`: original `ViridianMartDefaultScript` and `ViridianMartOaksParcelScript` drive the parcel; leave them intact until the pre-Mart gate can be tested in actual gameplay.
- `data/maps/objects/ViridianSchoolHouse.asm`: original house has three NPCs and a two-tile exit; no trainer battle exists there.
- `scripts/ViridianSchoolHouse.asm`: only original text dispatch exists. A new instructor object and true-doubles event need to be added.
- `text/ViridianSchoolHouse.asm`: existing text is original school dialogue; separate the three noncombatant supporter roles from the new instructor.

## Locked mechanics and script narrative

- Starter is Weedle, Pidgey or Rattata (random roughly equally), independently of gift.
- New NPC blocks the Mart entrance until the lesson concludes, mentioning the shopkeeper is attending the doubles school. Keep the sleeping old-man north gate and stock Oak's Parcel script intact.
- One permanent Level 5 gift, selected from Poliwag (Bubble/Tail Whip), Nidoran♀ (Scratch/Growl), Paras (Scratch/Leer), with remaining move slots empty. Apply 1.5× EXP and original traded badge obedience.
- One instructor controls Oddish Lv4 (Absorb/Growl) and Meowth Lv4 (Scratch/Tail Whip), simultaneously in an actual 2v2 battle. No other school battle.
- Either battle victory or defeat completes the lesson; never require a rematch and never grant the gift twice. The Mart becomes accessible and vanilla parcel delivery proceeds.
- Instructor's enthusiastic introduction, gift choice invitation, and win-or-lose congratulations are approved. Exact wording is in the Drive authority. Other NPCs advocate for official doubles; clerks across Kanto are a family with a doubles-awareness theme. Official recognition happens only after defeating the final Elite Four member.
- School gives no League badge.

Authority: https://docs.google.com/document/d/1hoyEIC2aI1of3iBKJF-NT-GvcBtaCGjxjp4nNhy4Z50/edit

## Required implementation order

1. Verify live branch/CI and map coordinates/valid event flag capacity; ensure object-count and toggleable-actor constraints are safe.
2. Design event state machine: NOT_STARTED → GIFT_CHOSEN → INTRO_BATTLE_IN_PROGRESS → COMPLETED. Completion persistent on victory OR loss, including whiteout and reload; never duplicate gifts. Do not advance to parcel before completion.
3. Build/integrate the YEL-BATTLE-001 true doubles engine and YEL-BAL-003 gift outsider treatment. No fake single battle masquerading as doubles.
4. Add school instructor, selection UI, school NPC dialogue and spectator; add Mart entrance blocker and visibility conditioned on event completion. Ensure save/load and original parcel-script compatibility.
5. Compile and run emulator regression matrix: 3 starters × 3 gifts × win/loss; save before and after; full party; repeat school talk; whiteout; reentry; northern old man, parcel, old Trainer and Mart functionality. Preserve screenshot, controller trace, ROM SHA, source commit, game flags, and logs.
6. Merge only when the full event is proven playable on a normal game path, not DEBUG-only and not boot smoke alone.

Dependencies: YEL-BATTLE-001, YEL-BAL-003, starter randomization, YEL-TEST-005.
This staged PR is not yet game-functional.
