#!/usr/bin/env python3
"""YEL-QOL-012 reference model for 30-slot box records.

This validates the exact SRAM byte representation and transactions. It is
a source-contract test model, NOT Game Boy assembly or emulator evidence.
"""
from dataclasses import dataclass

CAPACITY = 30
MON_BYTES = 33
NAME_BYTES = 11
BOX_BYTES = 2 + CAPACITY * (1 + MON_BYTES + 2 * NAME_BYTES)
MON_OFFSET = CAPACITY + 2
OT_OFFSET = MON_OFFSET + CAPACITY * MON_BYTES
NICK_OFFSET = OT_OFFSET + CAPACITY * NAME_BYTES

@dataclass(frozen=True)
class BoxRecord:
    mon: bytes
    ot: bytes
    nickname: bytes
    def __post_init__(self):
        if len(self.mon) != MON_BYTES or len(self.ot) != NAME_BYTES or len(self.nickname) != NAME_BYTES:
            raise ValueError("Pokémon, OT and nickname lengths must be exactly 33/11/11")
        if self.mon[0] in (0, 0xff):
            raise ValueError("Invalid Pokémon species")

def _bounds(slot):
    if not isinstance(slot, int) or not 0 <= slot < CAPACITY:
        raise IndexError("Physical PC index must be 0..29")

def read_record(box: bytes, slot: int) -> BoxRecord:
    _bounds(slot)
    if len(box) != BOX_BYTES:
        raise ValueError("Incorrect SRAM box size")
    if slot >= box[0]:
        raise IndexError("Slot is empty")
    return BoxRecord(
        box[MON_OFFSET + slot*MON_BYTES:MON_OFFSET + (slot+1)*MON_BYTES],
        box[OT_OFFSET + slot*NAME_BYTES:OT_OFFSET + (slot+1)*NAME_BYTES],
        box[NICK_OFFSET + slot*NAME_BYTES:NICK_OFFSET + (slot+1)*NAME_BYTES])

def write_record(box: bytes, slot: int, record: BoxRecord) -> bytes:
    _bounds(slot)
    if len(box) != BOX_BYTES or box[0] > CAPACITY:
        raise ValueError("Invalid source box")
    if slot >= box[0]:
        raise IndexError("Cannot write outside occupied slots")
    out=bytearray(box)
    out[1+slot]=record.mon[0]
    out[MON_OFFSET+slot*MON_BYTES:MON_OFFSET+(slot+1)*MON_BYTES]=record.mon
    out[OT_OFFSET+slot*NAME_BYTES:OT_OFFSET+(slot+1)*NAME_BYTES]=record.ot
    out[NICK_OFFSET+slot*NAME_BYTES:NICK_OFFSET+(slot+1)*NAME_BYTES]=record.nickname
    return bytes(out)

def validate_box(box: bytes):
    if len(box)!=BOX_BYTES or box[0]>CAPACITY or box[1+box[0]]!=0xff:
        raise ValueError("Corrupt box header, sentinel or length")
    for slot in range(box[0]):
        record=read_record(box,slot)
        if box[1+slot]!=record.mon[0]:
            raise ValueError("Species table mismatches stored record")

def replace_in_page(box: bytes, first: int, records: list[BoxRecord]) -> bytes:
    """Atomic reference operation; a page is at most 20 records."""
    if not 0<=first<CAPACITY or not 1<=len(records)<=20 or first+len(records)>box[0]:
        raise IndexError("Page outside populated slots")
    validate_box(box)
    updated=box
    for i,record in enumerate(records):
        updated=write_record(updated,first+i,record)
    validate_box(updated)
    return updated
