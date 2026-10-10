#!/usr/bin/env python3
"""YEL-TEST-005 map-aware controller navigation primitives.

A planner proposes one-tile steps on a bounded grid; the emulator must
confirm each step against real wCurMap/wXCoord/wYCoord values. No WRAM writes.
Collision/obstacle information MUST come from verified map data or observed
rejections, never inferred from rectangular map bounds alone.
"""
from collections import deque

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


def shortest_path(start, goal, width, height, blocked=()):
    """BFS over explicitly supplied collision grid. Returns button names."""
    blocked = set(map(tuple, blocked))
    if width <= 0 or height <= 0:
        raise ValueError("Invalid map bounds")
    def valid(p):
        x, y = p
        return 0 <= x < width and 0 <= y < height and p not in blocked
    start, goal = tuple(start), tuple(goal)
    if not valid(start) or not valid(goal):
        raise ValueError("Start or goal outside passable grid")
    paths = deque([(start, ())])
    seen = {start}
    while paths:
        point, route = paths.popleft()
        if point == goal:
            return list(route)
        for direction, (dx, dy) in DIRS.items():
            dest = (point[0] + dx, point[1] + dy)
            if valid(dest) and dest not in seen:
                seen.add(dest)
                paths.append((dest, route + (direction,)))
    raise ValueError("Goal unreachable with supplied collision data")


def verify_step(before, after, direction, allowed_warp=None):
    """Fail closed unless a single real tile movement or declared warp occurred.

    before/after are dicts with map, x and y integer values.
    allowed_warp = expected destination (map, x, y), only at a warp tile.
    """
    if direction not in DIRS:
        raise ValueError("Unsupported movement direction")
    if before["map"] != after["map"]:
        expected = tuple(allowed_warp) if allowed_warp is not None else None
        if expected != (after["map"], after["x"], after["y"]):
            raise AssertionError("Unexpected map transition")
        return "verified_warp"
    dx, dy = DIRS[direction]
    expected = (before["x"] + dx, before["y"] + dy)
    if (after["x"], after["y"]) != expected:
        raise AssertionError(
            f"Movement {direction} blocked/unfinished: expected {expected}, "
            f"got {(after['x'], after['y'])}"
        )
    return "verified_tile"
