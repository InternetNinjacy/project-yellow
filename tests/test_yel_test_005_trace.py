#!/usr/bin/env python3
"""Pure trace-format tests; no ROM or emulator needed."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "yel_test_005_replay", ROOT / "scripts" / "yel_test_005_replay.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TraceValidation(unittest.TestCase):
    def test_valid_common_capture_schema(self):
        MODULE.validate([
            {"frames": 120},
            {"button": "a", "frames": 1, "after": 30},
            {"button": "up", "frames": 8},
        ])

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            MODULE.validate([])

    def test_rejects_unbounded(self):
        with self.assertRaises(ValueError):
            MODULE.validate([{"frames": 100001}])

    def test_rejects_unknown_button(self):
        with self.assertRaises(ValueError):
            MODULE.validate([{"button": "turbo", "frames": 1}])

    def test_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            MODULE.validate([{"frames": 1, "memory_write": "FF"}])

    def test_rejects_zero_length_press(self):
        with self.assertRaises(ValueError):
            MODULE.validate([{"button": "a", "frames": 0}])

    def test_rejects_boolean_frame(self):
        with self.assertRaises(ValueError):
            MODULE.validate([{"frames": True}])


if __name__ == "__main__":
    unittest.main()
