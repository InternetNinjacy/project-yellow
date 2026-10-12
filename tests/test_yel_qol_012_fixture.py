"""Deterministic physical fixture construction; no emulator/gameplay claims."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from yel_qol_012_fixture import seed_scenario, BOX_BYTES

class FakeMemory(dict):
    def __getitem__(self, key):
        return super().get(key, 0)

class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.memory = FakeMemory()
        self.sym = {"sBox1": (2,0xa000),
                    "sBank2AllBoxesChecksum": (2,0xba48),
                    "sBank2IndividualBoxChecksums": (2,0xba49)}
    def test_all_bank_boundaries_and_full_other_boxes(self):
        for index in (0,3,4,7,8,11):
            with self.subTest(destination=index):
                mem = FakeMemory()
                result = seed_scenario(mem, self.sym, index, 29, others_full=True)
                self.assertEqual(result["kind"], "synthetic-emulator-fixture")
                for i in range(12):
                    bank = 2+i//4
                    base = self.sym["sBox1"][1] + (i%4)*BOX_BYTES
                    self.assertEqual(mem[bank,base], 29 if i == index else 30)
                    self.assertEqual(mem[bank,base + (30 if i==index else 31)], 255)
                for bank in (2,3,4):
                    base = self.sym["sBox1"][1]
                    entire = bytes(mem[bank,base+k] for k in range(4*BOX_BYTES))
                    checksum = mem[bank,self.sym["sBank2AllBoxesChecksum"][1]]
                    self.assertEqual(checksum, (~sum(entire)) & 255)
    def test_reject_invalid_counts(self):
        with self.assertRaises(ValueError):
            seed_scenario(self.memory,self.sym,0,31)

if __name__ == "__main__":
    unittest.main()
