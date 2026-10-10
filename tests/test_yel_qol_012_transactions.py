import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from yel_qol_012_transactions import StagedTransaction
from yel_qol_012_records import BoxRecord,read_record,validate_box,BOX_BYTES

def record(i):
    return BoxRecord(bytes([i])*33,bytes([(i+31)%256])*11,bytes([(i+91)%256])*11)

def box(count):
    data=bytearray(BOX_BYTES);data[0]=count;data[count+1]=255
    from yel_qol_012_records import MON_OFFSET,OT_OFFSET,NICK_OFFSET
    for i in range(count):
        r=record(i+1)
        data[1+i]=r.mon[0]
        data[MON_OFFSET+i*33:MON_OFFSET+(i+1)*33]=r.mon
        data[OT_OFFSET+i*11:OT_OFFSET+(i+1)*11]=r.ot
        data[NICK_OFFSET+i*11:NICK_OFFSET+(i+1)*11]=r.nickname
    return bytes(data)

class Transactions(unittest.TestCase):
    def test_window_crosses_twenty(self):
        t=StagedTransaction.begin(box(30))
        self.assertEqual(len(t.stage_window(0)),20)
        self.assertEqual(len(t.stage_window(20)),10)
        self.assertEqual(t.stage_window(20)[9],record(30))
    def test_replace_preserves_all_other_records(self):
        old=box(30);t=StagedTransaction.begin(old)
        t.replace(29,record(100))
        new=t.commit();validate_box(new)
        for i in range(30):
            self.assertEqual(read_record(new,i),record(100) if i==29 else read_record(old,i))
    def test_capture_shifts_all_records(self):
        old=box(29);t=StagedTransaction.begin(old)
        t.capture_prepend(record(110))
        new=t.commit();validate_box(new)
        self.assertEqual(new[0],30)
        self.assertEqual(read_record(new,0),record(110))
        for i in range(29):self.assertEqual(read_record(new,i+1),read_record(old,i))
    def test_full_rejected_unchanged(self):
        old=box(30);t=StagedTransaction.begin(old)
        with self.assertRaises(OverflowError):t.capture_prepend(record(110))
        self.assertEqual(t.rollback(),old)
    def test_precommit_failure_rolls_back(self):
        old=box(29);t=StagedTransaction.begin(old)
        t.capture_prepend(record(90))
        with self.assertRaises(IOError):t.commit(simulate_failure=True)
        self.assertEqual(t.rollback(),old)
    def test_invalid_slot_rolls_back(self):
        old=box(2);t=StagedTransaction.begin(old)
        with self.assertRaises(IndexError):t.replace(20,record(30))
        self.assertEqual(t.rollback(),old)

if __name__=="__main__":unittest.main()
