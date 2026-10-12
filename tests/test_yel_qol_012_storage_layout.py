import importlib.util
import pathlib
import unittest

path=pathlib.Path(__file__).resolve().parents[1]/"scripts/yel_qol_012_storage_layout.py"
spec=importlib.util.spec_from_file_location("qol012",path)
mod=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)

class ExpandedPCLayout(unittest.TestCase):
    def test_layout(self):
        mod.check_layout()
    def test_capacity(self):
        self.assertEqual(mod.BOXES*mod.SLOTS,360)
        self.assertEqual(mod.BOX_BYTES,1682)
    def test_banking_boundaries(self):
        self.assertEqual((mod.box_location(0).bank,mod.box_location(0).offset),(2,0))
        self.assertEqual((mod.box_location(3).bank,mod.box_location(3).offset),(2,5046))
        self.assertEqual((mod.box_location(4).bank,mod.box_location(4).offset),(3,0))
        self.assertEqual((mod.box_location(8).bank,mod.box_location(8).offset),(4,0))
        self.assertEqual((mod.box_location(11).bank,mod.box_location(11).offset),(4,5046))
    def test_invalid(self):
        with self.assertRaises(ValueError):mod.box_location(12)

if __name__=="__main__":unittest.main()
