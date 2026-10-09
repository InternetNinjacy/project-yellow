#!/usr/bin/env python3
"""YEL-TEST-003: deterministic DEBUG-lab Bulbasaur engine verification.

This test enters Yellow's existing DEBUG menu, starts a debug new game, then
uses emulator savestates to explore Red's House 2F until the real map engine
crosses into Red's House 1F. It does not patch map state or teleport the player.

Once in the lab it verifies the first map object's Bulbasaur identity, exact
compiled 2bpp bytes in VRAM, matching OAM tile use, visible OBJ/background
transparency, natural WALK movement, and all four facings.
"""
import argparse
import hashlib
import io
import json
import re
from collections import deque
from pathlib import Path

from pyboy import PyBoy

REDS_HOUSE_1F = 0x25
REDS_HOUSE_2F = 0x26
SPRITE_BULBASAUR = 0x41
FACING_NAMES = {0x00: "down", 0x04: "up", 0x08: "left", 0x0C: "right"}
DIRECTIONS = ("up", "down", "left", "right")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_sym(path: Path):
    symbols = {}
    rx = re.compile(r"^[0-9A-Fa-f]{2}:([0-9A-Fa-f]{4})\s+(\S+)")
    for raw in path.read_text(errors="replace").splitlines():
        m = rx.match(raw.strip())
        if m:
            symbols[m.group(2)] = int(m.group(1), 16)
    return symbols


def mem8(emu, addr):
    return int(emu.memory[addr])


def mem_bytes(emu, start, size):
    return bytes(mem8(emu, start + i) for i in range(size))


def tick(emu, frames, render=True):
    for _ in range(frames):
        emu.tick(1, render=render)


def tap(emu, button, hold=3, settle=12):
    emu.button_press(button)
    tick(emu, hold)
    emu.button_release(button)
    tick(emu, settle)


def screenshot(emu, path: Path):
    emu.screen.image.copy().convert("RGB").save(path)


def save_state_bytes(emu):
    f = io.BytesIO()
    emu.save_state(f)
    return f.getvalue()


def load_state_bytes(emu, data):
    emu.load_state(io.BytesIO(data))


def wait_for_map(emu, w_cur_map, wanted, limit):
    for _ in range(limit):
        if mem8(emu, w_cur_map) in wanted:
            return mem8(emu, w_cur_map)
        emu.tick(1)
    raise AssertionError(
        f"Timed out waiting for map {sorted(wanted)}; current={mem8(emu, w_cur_map):#04x}"
    )


def enter_debug_menu(emu, symbols, out, limit=6000):
    """Reach the real DebugMenu routine using a symbol-resolved CPU hook."""
    state = {"seen": False}

    def hit_debug_menu(ctx):
        ctx["seen"] = True

    emu.hook_register(None, "DebugMenu", hit_debug_menu, state)

    elapsed = 0
    while elapsed < limit and not state["seen"]:
        # Select is harmless during startup. On the actual _DEBUG title loop it
        # jumps into DebugMenu, where the hook proves execution reached it.
        tap(emu, "select", hold=2, settle=18)
        elapsed += 20
        if state["seen"]:
            break
        tick(emu, 40)
        elapsed += 40

    emu.hook_deregister(None, "DebugMenu")
    if not state["seen"]:
        screenshot(emu, out / "debug_menu_not_reached.png")
        raise AssertionError("Timed out before CPU executed DebugMenu")

    # Let DebugMenu finish drawing and enter HandleMenuInput.
    tick(emu, 45)
    if (
        mem8(emu, symbols["wTopMenuItemY"]) != 7
        or mem8(emu, symbols["wMaxMenuItem"]) != 1
    ):
        raise AssertionError("CPU hit DebugMenu but its two-item menu did not initialize")
    screenshot(emu, out / "debug_menu.png")
    return elapsed


def choose_debug_new_game(emu, symbols, out, limit=3600):
    """Select DEBUG and drive the stock debug intro to SpecialEnterMap."""
    state = {"start_seen": False, "prompt_seen": False, "enter_seen": False}

    def hit_start_debug(ctx):
        ctx["start_seen"] = True

    def hit_prompt(ctx):
        ctx["prompt_seen"] = True

    def hit_special_enter(ctx):
        ctx["enter_seen"] = True

    # The stock DEBUG path still displays OakSpeechText3. Hook its actual text
    # wait routine so the confirmation press cannot be consumed while printing.
    emu.hook_register(None, "StartNewGameDebug", hit_start_debug, state)
    emu.hook_register(None, "ManualTextScroll", hit_prompt, state)
    emu.hook_register(None, "SpecialEnterMap", hit_special_enter, state)

    for _ in range(8):
        if mem8(emu, symbols["wCurrentMenuItem"]) == 1:
            break
        tap(emu, "down", hold=3, settle=8)
    if mem8(emu, symbols["wCurrentMenuItem"]) != 1:
        screenshot(emu, out / "debug_row_not_selected.png")
        raise AssertionError("Could not select DEBUG row in DebugMenu")

    screenshot(emu, out / "debug_selected.png")
    tap(emu, "a", hold=3, settle=8)

    elapsed = 0
    while elapsed < limit and not state["prompt_seen"]:
        emu.tick(1)
        elapsed += 1

    if not state["start_seen"]:
        raise AssertionError("A press did not execute StartNewGameDebug")
    if not state["prompt_seen"]:
        screenshot(emu, out / "debug_intro_prompt_not_reached.png")
        raise AssertionError("DEBUG Oak intro never reached ManualTextScroll")

    screenshot(emu, out / "debug_intro_prompt.png")

    # ManualTextScroll uses JoypadLowSensitivity and requires a NEW A/B edge.
    # Ensure the A used to choose DEBUG has been observed as released before
    # creating the confirmation edge for OakSpeechText3.
    emu.button_release("a")
    tick(emu, 12)
    elapsed += 12
    tap(emu, "a", hold=4, settle=24)
    elapsed += 28

    while elapsed < limit and not state["enter_seen"]:
        emu.tick(1)
        elapsed += 1

    emu.hook_deregister(None, "StartNewGameDebug")
    emu.hook_deregister(None, "ManualTextScroll")
    emu.hook_deregister(None, "SpecialEnterMap")

    if not state["enter_seen"]:
        screenshot(emu, out / "debug_intro_not_finished.png")
        raise AssertionError("DEBUG new-game intro never reached SpecialEnterMap")

    return elapsed


def move_one_step(emu, button, w_cur_map, w_y, w_x):
    """Attempt one grid movement and return resulting map/y/x."""
    before = (mem8(emu, w_cur_map), mem8(emu, w_y), mem8(emu, w_x))
    emu.button_press(button)
    tick(emu, 5)
    emu.button_release(button)

    # A normal Yellow grid step plus map transition settles comfortably here.
    for _ in range(48):
        emu.tick(1)
        now = (mem8(emu, w_cur_map), mem8(emu, w_y), mem8(emu, w_x))
        if now[0] != before[0]:
            tick(emu, 90)
            return (mem8(emu, w_cur_map), mem8(emu, w_y), mem8(emu, w_x))
    return (mem8(emu, w_cur_map), mem8(emu, w_y), mem8(emu, w_x))


def find_lab_by_exploration(emu, symbols, out):
    w_cur_map = symbols["wCurMap"]
    w_y = symbols["wYCoord"]
    w_x = symbols["wXCoord"]

    cur = mem8(emu, w_cur_map)
    if cur == REDS_HOUSE_1F:
        return []
    if cur != REDS_HOUSE_2F:
        raise AssertionError(f"Debug new game reached unexpected map {cur:#04x}")

    root = save_state_bytes(emu)
    start = (mem8(emu, w_y), mem8(emu, w_x))
    q = deque([(start, root, [])])
    seen = {start}
    exploration = []

    while q and len(seen) <= 96:
        (y, x), state, path = q.popleft()
        for direction in DIRECTIONS:
            load_state_bytes(emu, state)
            new_map, ny, nx = move_one_step(emu, direction, w_cur_map, w_y, w_x)
            exploration.append({
                "from": [y, x],
                "input": direction,
                "to_map": new_map,
                "to": [ny, nx],
            })
            if new_map == REDS_HOUSE_1F:
                screenshot(emu, out / "lab_entry.png")
                (out / "exploration.json").write_text(json.dumps(exploration, indent=2) + "\n")
                return path + [direction]
            if new_map != REDS_HOUSE_2F:
                continue
            pos = (ny, nx)
            if pos == (y, x) or pos in seen:
                continue
            seen.add(pos)
            q.append((pos, save_state_bytes(emu), path + [direction]))

    (out / "exploration.json").write_text(json.dumps(exploration, indent=2) + "\n")
    raise AssertionError(f"Could not reach downstairs lab; explored {len(seen)} upstairs positions")


def matching_oam_entries(emu, shadow_oam, first_tile, tile_count):
    entries = []
    valid = set(range(first_tile, first_tile + tile_count))
    raw = mem_bytes(emu, shadow_oam, 40 * 4)
    for i in range(40):
        y, x, tile_id, attr = raw[i * 4 : i * 4 + 4]
        if y and x and tile_id in valid:
            entries.append({
                "index": i,
                "y": y,
                "x": x,
                "tile": tile_id,
                "attr": attr,
            })
    return entries


def transparency_check(emu, out, oam_entries):
    before = emu.screen.image.copy().convert("RGB")
    screenshot(emu, out / "sprite_obj_enabled.png")

    lcdc = mem8(emu, 0xFF40)
    emu.memory[0xFF40] = lcdc & ~0x02  # OBJ display off, BG still rendered
    tick(emu, 2)
    after = emu.screen.image.copy().convert("RGB")
    after.save(out / "sprite_obj_disabled.png")
    emu.memory[0xFF40] = lcdc
    tick(emu, 2)

    xs = [max(0, e["x"] - 8) for e in oam_entries]
    ys = [max(0, e["y"] - 16) for e in oam_entries]
    xe = [min(160, x + 8) for x in xs]
    ye = [min(144, y + 8) for y in ys]
    if not xs:
        raise AssertionError("No Bulbasaur OAM entries available for transparency check")
    left, top, right, bottom = min(xs), min(ys), max(xe), max(ye)

    same = 0
    different = 0
    for y in range(top, bottom):
        for x in range(left, right):
            if before.getpixel((x, y)) == after.getpixel((x, y)):
                same += 1
            else:
                different += 1
    if different == 0:
        raise AssertionError("Disabling OBJ did not change Bulbasaur's OAM bounding area")
    if same == 0:
        raise AssertionError("Bulbasaur bounding area had no background-preserving pixels")
    return {
        "bbox": [left, top, right, bottom],
        "same_background_pixels": same,
        "different_obj_pixels": different,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rom", default="pokeyellow_debug.gbc")
    ap.add_argument("--sym", default="pokeyellow_debug.sym")
    ap.add_argument("--sprite-2bpp", default="gfx/sprites/bulbasaur.2bpp")
    ap.add_argument("--out", default="test-results/dev-lab-bulbasaur")
    args = ap.parse_args()

    rom = Path(args.rom)
    sym = Path(args.sym)
    sprite_2bpp = Path(args.sprite_2bpp)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    symbols = parse_sym(sym)
    required = [
        "wCurMap", "wYCoord", "wXCoord", "wSprite01StateData1",
        "wSprite01StateData2", "wShadowOAM", "vSprites",
        "wTopMenuItemY", "wMaxMenuItem", "wMenuWatchedKeys",
        "wCurrentMenuItem",
    ]
    missing = [name for name in required if name not in symbols]
    if missing:
        raise AssertionError(f"Missing required RGBDS symbols: {missing}")

    expected = sprite_2bpp.read_bytes()
    if len(expected) != 192:
        raise AssertionError(f"Bulbasaur 2bpp must be 192 bytes, got {len(expected)}")

    result = {
        "test": "YEL-TEST-003 DEBUG lab Bulbasaur engine verification",
        "rom": rom.name,
        "rom_sha256": hashlib.sha256(rom.read_bytes()).hexdigest(),
        "mode": "DMG emulation (cgb=False)",
        "target_map": "REDS_HOUSE_1F",
        "expected_map_id": REDS_HOUSE_1F,
        "expected_sprite_id": SPRITE_BULBASAUR,
        "expected_2bpp_sha256": hashlib.sha256(expected).hexdigest(),
        "status": "RUNNING",
    }

    emu = None
    try:
        emu = PyBoy(
            str(rom), window="null", cgb=False, sound_emulated=False,
            symbols=str(sym),
        )
        emu.set_emulation_speed(0)

        # Reach the actual DEBUG menu by its WRAM menu signature, not a fixed
        # frame count. Boot/intro duration can vary with emulator/audio behavior.
        result["frames_to_debug_menu"] = enter_debug_menu(emu, symbols, out)

        # Select the DEBUG row and prove its entry routine executes.
        result["frames_through_debug_intro"] = choose_debug_new_game(
            emu, symbols, out
        )

        start_map = wait_for_map(
            emu, symbols["wCurMap"], {REDS_HOUSE_2F, REDS_HOUSE_1F}, 4000
        )
        tick(emu, 120)
        result["debug_new_game_initial_map"] = start_map

        path = find_lab_by_exploration(emu, symbols, out)
        result["upstairs_input_path"] = path
        result["lab_map_id"] = mem8(emu, symbols["wCurMap"])
        result["lab_player_coord"] = [
            mem8(emu, symbols["wYCoord"]),
            mem8(emu, symbols["wXCoord"]),
        ]
        if result["lab_map_id"] != REDS_HOUSE_1F:
            raise AssertionError("Exploration did not end in REDS_HOUSE_1F")

        tick(emu, 120)
        s1 = symbols["wSprite01StateData1"]
        s2 = symbols["wSprite01StateData2"]
        pic1 = mem8(emu, s1)
        pic2 = mem8(emu, s2 + 0x0D)
        result["object_picture_id_state1"] = pic1
        result["object_picture_id_state2"] = pic2
        if pic1 != SPRITE_BULBASAUR or pic2 != SPRITE_BULBASAUR:
            raise AssertionError(
                f"Lab object is not Bulbasaur: state1={pic1:#04x}, state2={pic2:#04x}"
            )

        # Prove the exact compiled 192-byte Bulbasaur source exists in live VRAM.
        vram = mem_bytes(emu, 0x8000, 0x1800)
        idx = vram.find(expected)
        if idx < 0:
            raise AssertionError("Exact Bulbasaur 2bpp sequence not found in live VRAM")
        vram_addr = 0x8000 + idx
        first_tile = idx // 16
        result["vram_match_address"] = hex(vram_addr)
        result["vram_tile_id_base"] = first_tile
        result["vram_exact_192_byte_match"] = True

        oam_entries = matching_oam_entries(
            emu, symbols["wShadowOAM"], first_tile, len(expected) // 16
        )
        result["bulbasaur_oam_entries"] = oam_entries
        if len(oam_entries) < 4:
            raise AssertionError(
                f"Expected at least four live Bulbasaur OAM tiles, found {len(oam_entries)}"
            )

        result["transparency"] = transparency_check(emu, out, oam_entries)

        # Observe the real WALK/ANY_DIR object naturally. Facing byte values are
        # documented by the engine: 0 down, 4 up, 8 left, c right.
        facing_seen = {}
        positions = set()
        saw_moving_status = False
        max_frames = 12000
        for frame in range(max_frames):
            emu.tick(1)
            if mem8(emu, symbols["wCurMap"]) != REDS_HOUSE_1F:
                raise AssertionError("Bulbasaur lab observation unexpectedly left the map")

            movement_status = mem8(emu, s1 + 1)
            if movement_status == 3:
                saw_moving_status = True
                if not (out / "walking.png").exists():
                    screenshot(emu, out / "walking.png")

            positions.add((mem8(emu, s2 + 4), mem8(emu, s2 + 5)))
            facing = mem8(emu, s1 + 9) & 0x0C
            if facing in FACING_NAMES and facing not in facing_seen:
                name = FACING_NAMES[facing]
                path_out = out / f"facing_{name}.png"
                screenshot(emu, path_out)
                facing_seen[facing] = {
                    "name": name,
                    "frame": frame,
                    "screenshot": path_out.name,
                }
            if len(facing_seen) == 4 and saw_moving_status and len(positions) >= 2:
                break

        result["facings"] = [facing_seen[k] for k in sorted(facing_seen)]
        result["movement_status_3_observed"] = saw_moving_status
        result["distinct_object_positions"] = [list(p) for p in sorted(positions)]
        if len(facing_seen) != 4:
            raise AssertionError(
                "Did not naturally observe all four Bulbasaur facings; "
                f"saw {[FACING_NAMES[k] for k in sorted(facing_seen)]}"
            )
        if not saw_moving_status or len(positions) < 2:
            raise AssertionError("WALK behavior was not observed moving the lab object")

        # Record hashes for all screenshots as immutable evidence references.
        result["screenshot_sha256"] = {
            p.name: sha256(p) for p in sorted(out.glob("*.png"))
        }
        result["status"] = "ENGINE_VISUAL_PASS"
    except Exception as exc:
        result["status"] = "ENGINE_VISUAL_FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if emu is not None:
            emu.stop(save=False)
        (out / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
