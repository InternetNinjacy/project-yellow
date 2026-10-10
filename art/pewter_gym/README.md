# YEL-GYM1-ART-001 — approved Pewter Gym source assets

These three **real, pixel-level** source PNGs correspond to the original-geometry frozen Pewter Gym preview approved on 2026-10-09.

- `snow_floor_8x8.png`: safe mostly snow-covered indoor floor, 8×8, 2-bit grayscale.
- `sliding_ice_8x8.png`: visibly striped slippery ice, 8×8, 2-bit grayscale.
- `frost_boulder_16x16.png`: heavier ice accumulation on the original rock silhouette, 16×16, 2-bit grayscale.

Original unmodified sources: `gfx/tilesets/gym.png`, `gfx/blocksets/gym.bst`, and `maps/PewterGym.blk`.

Approved full-room preview and source manifest are permanently archived in Drive:
https://drive.google.com/file/d/1Q_30r771GKTb0F-WO-L9s5de7VBh9x8I/view

## Integration status

**Artwork approved; engine integration NOT verified.** The separate branch `feature/pewter-frozen-gym-integration` includes a candidate tile/map generator. Do not alter the shared `gym.png` / `gym.bst`: the original Gym graphics are reused elsewhere. The source raster stays within the current 96 8×8 tile capacity, using currently unused-for-Pewter slots $5E and $5F for snow and ice. A dedicated tileset ID, blockset pointer, Pewter map change, collision table, ice movement and trainer trigger are still necessary.

The generated grayscale asset and illustrative GBC preview are distinct: the latter is not hardware palette verification. Preserve original NPC coordinates and sprite artwork.

## Safety / acceptance gates

1. Generator produces a dedicated `pewter_gym.png` and `pewter_gym.bst`; candidate changed `PewterGym.blk` generated outside tracked source until reviewed.
2. Ensure tile indices stay <= $5F and blocks <= $FF, and match the approved full-room map.
3. Wire Pewter-specific tileset without changing any other Gym.
4. Verify single ice lane is slippery while snowy floor is not. Trigger the optional stationary Gym Trainer only on first slide/direct approach; post-defeat slides must not interrupt; the safe route must work.
5. Build and emulator tests: Gym entry/exit, collision, NPC coordinates, optional battle, reward and saving/loading.

Do not mark engine verified without real emulator evidence.
