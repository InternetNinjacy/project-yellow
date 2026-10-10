# YEL-TEST-005 — Approved hybrid capture station contract

**User decision:** hybrid validation is approved. Shared harness owns test tools.
YEL-QOL-011 retains ownership of the capture feature and its assertions.

## Gate A: DEBUG engine-driven capture station (fast integration)

Build a test-only encounter station gated by `IF DEF(_DEBUG)` in source,
NOT a memory-edited PyBoy state disguised as ordinary gameplay. The
existing DEBUG Red's House 1F graphics object must not be replaced without
coordinating with YEL-TEST-003; it is an existing developer graphics fixture.
Use a separate test-only interaction or area after auditing available
ROM space, battle initiation and gift/item procedures.

Required station interactions (ALL actual game routines):
- Grant a party of six legitimate Pokémon through game gift/party insertion
  handlers. Check the insertion routine handles party count and names.
- Give standard Poké Balls using the game's bag routine.
- Enter a standard wild encounter with a reliably catchable opponent using
  the game's wild battle initialization. Exercise capture without changing
  the storage feature code.
- Record before/after RAM/SRAM and normal in-game save/continue behavior.
- Seed PC record edge cases only in separate controlled fixture copies;
  distinguish these from the party/gifts acquired by in-game code.

No direct PyBoy memory writes should be used to claim the party/item/battle
setup is engine-derived. A developer-only station may itself arrange test
inputs internally, but it must use actual normal game data handling routines.
The station must not ship in release builds.

## Gate B: natural gameplay regression (independent)

Start from clean *release* ROM, process title/intro, get a Pokémon and
Poké Balls through ordinary story events, capture additional Pokémon until
party size is six, then reach a fresh pre-capture wild battle. No debugging
events, party seeding, direct memory writes or loaded artificial checkpoints.
Record controller trace, map events and ROM/symbol/trace hashes.

## Reusable navigation implementation

- `scripts/yel_test_005_navigation.py`: BFS shortest path using explicit
  passable-grid constraints, strict single-tile step/warp verification.
- `scripts/yel_test_005_navigate.py`: controller-only single-tile runner from
  a separately documented private checkpoint; no memory writes.
- `tests/test_yel_test_005_navigation.py`: path, obstruction, coordinate,
  warp and multi-tile failure cases.

These are *navigation primitives*, not a fully automatic map extraction,
collision resolver, or context-sensitive dialogue engine. Before using the
planner to reach a warp, map collision data must be extracted and verified
from exact build/map definitions. A map rectangle is NOT a collision map.
The runtime does not yet accept an allowed-warp table. Full route automation
and DEBUG encounter-room code are separate pending implementation gates.

## Acceptance / CI

1. Navigation pure-unit tests pass.
2. Real controller route reaches downstairs, verifying map ID and coordinates
   from source-defined warp data; wrong transition fails.
3. DEBUG build and release build each compile. Binary difference is confined
   to approved debug gates; release must contain no new test interaction.
4. DEBUG station produces six party members, actual bag items and wild-battle
   flags through tested game procedures. Save private base checkpoint.
5. Seven YEL-QOL-011 scenarios preserve each existing record by exact
   (box index, slot index, 33-byte mon bytes, OT, nickname).
6. Native save/restart/CONTINUE retains boxes and active selection.
7. Independently complete normal-story release route.
8. Preserve PR #6 as draft until capture, storage and persistence all PASS.

**Current honest status:** navigation components committed, DEBUG capture
station assembly NOT IMPLEMENTED, natural six-party route NOT IMPLEMENTED,
seven matrix cases and game-native persistence NOT EXECUTED.

## DEBUG capture station implementation checkpoint

Branch code now adds DEBUG-only party members PIDGEY level 5 and RATTATA
level 5 to the existing 4 DEBUG starting members, via `AddPartyMon` in
`engine/debug/debug_party.asm`. It also adds thirty standard POKE_BALL
items to `DebugNewGameItemsList`; existing `AddItemToInventory` places
them in the bag. Normal New Game does NOT activate this mode; the title
DEBUG menu is entered by holding SELECT+START on the fully loaded title
screen and selecting DEBUG. UP+SELECT+B opens the clear-save dialogue,
**not** the DEBUG menu.

A confirmed Actions DEBUG New Game probe reached wPartyCount=6 with
15 inventory entries, run
https://github.com/InternetNinjacy/project-yellow/actions/runs/38054424709 .
That result established party setup; the new CI flag `--require-debug-setup`
independently tests the precise POKE_BALL item quantity.

The first prototype encounter trigger for Red's House 2F was reverted.
DEBUG New Game actually begins at Pallet Town (map ID 0), coordinates (5,6).
`scripts/PalletTown.asm` now contains a _DEBUG-only one-shot encounter
trigger on tile (5,7), conditional on party size 6, setting
`wCurOpponent=PIDGEY` and `wCurEnemyLevel=3` to go through the
stock overworld battle dispatcher. The original Pallet script is untouched
in non-DEBUG builds. The updated controller trace presses DOWN after
DEBUG New Game to initiate this encounter; `--require-debug-encounter`
fails if the actual wild battle flag and enemy species are not observed.

**Do not call the battle stage complete unless CI passes the new
hard gates.** The native capture, seven box layouts, SRAM persistence,
and independent natural route are still separate pending gates.
