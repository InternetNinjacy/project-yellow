# YEL-TEST-002: Emulator Boot and Sprite Verification

## Scope
The first checkpoint boots an unmodified Project Yellow fork of the original Yellow ROM in PyBoy headlessly in DMG mode, captures two 160x144 screenshots, and produces a JSON evidence report. The ROM is built during the CI run and is not uploaded. The test checks that the final frame isn't entirely uniform and that the emulator starts without exceptions.

**This does not confirm a Pokémon appears, that a sprite faces four directions, that Yellow's follower loader works, nor that SGB/GBC palettes are verified.** Status names must reflect this distinction.

## Next gates
1. Confirm baseline DMG boot smoke with CI report and screenshots.
2. Add a game-engine test fixture that creates a controllable **existing Bulbasaur** map object and checks actual VRAM/OAM/render output.
3. Add engine-registered Ivysaur sprite and compare four directions (with mirrored right), text reload and walking.
4. Verify compatible palette implementations on appropriate SGB and GBC modes, using separate emulator evidence.

The existing sprite production record and independent Project Yellow source code are authoritative; never borrow Sam Edition/FireSam assets. Keep all output under numbered species folders and update the Species Tracker after every actual test.
