#!/usr/bin/env python3
"""YEL-TEST-005 capture precondition audit unit tests without PyBoy."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "capture_audit", ROOT / "scripts" / "yel_test_005_capture_audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PreCaptureAudit(unittest.TestCase):
    def setUp(self):
        self.mem = bytearray(0x10000)
        self.syms = {name: (0, addr) for name, addr in {
            "wPartyCount": 0xC100, "wPartySpecies": 0xC101,
            "wNumBagItems": 0xC200, "wBagItems": 0xC201,
            "wIsInBattle": 0xC300, "wEnemyMonSpecies2": 0xC301
        }.items()}
        self.mem[0xC100] = 6
        self.mem[0xC101:0xC107] = b"\x01\x02\x03\x04\x05\x06"
        self.mem[0xC200] = 1
        self.mem[0xC201:0xC203] = b"\x04\x05"
        self.mem[0xC300] = 1
        self.mem[0xC301] = 36

    def test_full_party_wild_with_balls(self):
        report = audit.inspect(self.mem, self.syms)
        self.assertTrue(report["capture_preconditions_pass"])
        self.assertEqual(report["poke_ball_quantity"], 5)

    def test_five_party_fails(self):
        self.mem[0xC100] = 5
        self.assertFalse(audit.inspect(self.mem, self.syms)["capture_preconditions_pass"])

    def test_no_balls_fails(self):
        self.mem[0xC202] = 0
        self.assertFalse(audit.inspect(self.mem, self.syms)["capture_preconditions_pass"])

    def test_trainer_battle_fails(self):
        self.mem[0xC300] = 2
        self.assertFalse(audit.inspect(self.mem, self.syms)["capture_preconditions_pass"])

    def test_no_enemy_fails(self):
        self.mem[0xC301] = 0
        self.assertFalse(audit.inspect(self.mem, self.syms)["capture_preconditions_pass"])

    def test_bad_party_header_rejected(self):
        self.mem[0xC100] = 7
        with self.assertRaises(ValueError):
            audit.inspect(self.mem, self.syms)


if __name__ == "__main__":
    unittest.main()
