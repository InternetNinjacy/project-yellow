import importlib.util
import pathlib
import sys
import unittest

path=pathlib.Path(__file__).resolve().parents[1]/"scripts/yel_qol_012_records.py"
spec=importlib.util.spec_from_file_location("qol012records",path)
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

def fixture(count=30):
    box=bytearray(m.BOX_BYTES)
    box[0]=count
    box[1+count]=255
    for index in range(count):
        mark=bytes([index+1])
        box[1+index]=index+1
        box[m.MON_OFFSET+index*33:m.MON_OFFSET+(index+1)*33]=mark*33
        box[m.OT_OFFSET+index*11:m.OT_OFFSET+(index+1)*11]=bytes([80+index])*11
        box[m.NICK_OFFSET+index*11:m.NICK_OFFSET+(index+1)*11]=bytes([120+index])*11
    return bytes(box)

class Records(unittest.TestCase):
    def test_layout(self):
        self.assertEqual((m.MON_OFFSET,m.OT_OFFSET,m.NICK_OFFSET,m.BOX_BYTES),(32,1022,1352,1682))
    def test_all_thirty_roundtrip(self):
        original=fixture()
        m.validate_box(original)
        for i in range(30):
            self.assertEqual(m.read_record(original,i).mon,bytes([i+1])*33)
        self.assertEqual(m.read_record(original,29).nickname,bytes([149])*11)
    def test_page_crossing_at_twenty(self):
        original=fixture()
        rec=m.BoxRecord(bytes([42])*33,bytes([91])*11,bytes([151])*11)
        changed=m.replace_in_page(original,19,[rec,rec])
        for slot in range(30):
            if slot in (19,20):
                self.assertEqual(m.read_record(changed,slot),rec)
            else:
                self.assertEqual(m.read_record(changed,slot),m.read_record(original,slot))
    def test_invalid_slot_and_corruption(self):
        with self.assertRaises(IndexError):m.read_record(fixture(),30)
        with self.assertRaises(IndexError):m.read_record(fixture(10),20)
        damaged=bytearray(fixture());damaged[1]=0
        with self.assertRaises(ValueError):m.validate_box(bytes(damaged))
    def test_bad_record_rejected(self):
        with self.assertRaises(ValueError):m.BoxRecord(bytes(33),bytes(11),bytes(11))

if __name__=="__main__":unittest.main()
