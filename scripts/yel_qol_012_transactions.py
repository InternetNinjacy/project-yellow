#!/usr/bin/env python3
"""YEL-QOL-012 testable transactional SRAM design model.

Reference model ONLY; the ROM assembly must separately implement and test this.
A complete shadow box is prepared before one authoritative replacement.
Power-loss atomicity additionally requires a persistent journal/version protocol.
"""
from dataclasses import dataclass
from yel_qol_012_records import (
    CAPACITY, BOX_BYTES, BoxRecord, read_record, write_record, validate_box,
    MON_OFFSET, OT_OFFSET, NICK_OFFSET, MON_BYTES, NAME_BYTES,
)

WORKING_SLOTS=20
RECORD_BYTES=MON_BYTES+2*NAME_BYTES

@dataclass
class StagedTransaction:
    original: bytes
    shadow: bytearray
    committed: bool=False

    @classmethod
    def begin(cls, physical: bytes):
        validate_box(physical)
        return cls(bytes(physical),bytearray(physical))

    def _write(self,slot:int,record:BoxRecord):
        if not 0<=slot<CAPACITY:
            raise IndexError(slot)
        self.shadow[1+slot]=record.mon[0]
        m=MON_OFFSET+slot*MON_BYTES
        o=OT_OFFSET+slot*NAME_BYTES
        n=NICK_OFFSET+slot*NAME_BYTES
        self.shadow[m:m+MON_BYTES]=record.mon
        self.shadow[o:o+NAME_BYTES]=record.ot
        self.shadow[n:n+NAME_BYTES]=record.nickname

    def stage_window(self,start:int):
        if self.committed:
            raise RuntimeError("Already committed")
        if not 0<=start<CAPACITY:
            raise IndexError(start)
        return [read_record(bytes(self.shadow),i)
                for i in range(start,min(self.shadow[0],start+WORKING_SLOTS))]

    def replace(self,slot:int,record:BoxRecord):
        if self.committed:
            raise RuntimeError("Already committed")
        if slot<0 or slot>=self.shadow[0]:
            raise IndexError(slot)
        self._write(slot,record)

    def capture_prepend(self,record:BoxRecord):
        if self.committed:
            raise RuntimeError("Already committed")
        count=self.shadow[0]
        if count>=CAPACITY:
            raise OverflowError("PC box full")
        # Move entire logical records together from high to low slots.
        # Reverse traversal makes overlapping insertion safe.
        for index in range(count,0,-1):
            self._write(index,read_record(bytes(self.shadow),index-1))
        self._write(0,record)
        self.shadow[0]=count+1
        self.shadow[1+count+1]=255

    def commit(self,simulate_failure=False):
        if self.committed:
            raise RuntimeError("Already committed")
        validate_box(bytes(self.shadow))
        if simulate_failure:
            self.rollback()
            raise IOError("Pre-commit transaction failure")
        self.committed=True
        return bytes(self.shadow)

    def rollback(self):
        self.shadow=bytearray(self.original)
        self.committed=False
        return self.original
