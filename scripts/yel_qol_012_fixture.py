#!/usr/bin/env python3
"""Test-only physical SRAM fixture for YEL-QOL-012.

Called exclusively by a PyBoy harness AFTER a debug new-game initializes
versioned storage. This is fixture seeding, not earned gameplay progress.
No production ROM/game event invokes this utility.
"""
BOX_BYTES=1682
MON_OFFSET=32
OT_OFFSET=1022
NICK_OFFSET=1352

def fill_box(memory, symbols, index, count, species=16):
    """Seed one 30-slot SRAM box, with coherent species+55-byte records."""
    if type(index) is not int or not 0 <= index < 12:
        raise ValueError("index must be 0..11")
    if type(count) is not int or not 0 <= count <= 30:
        raise ValueError("count must be 0..30")
    bank=2+index//4
    base=symbols["sBox1"][1]+(index%4)*BOX_BYTES
    buf=bytearray(BOX_BYTES)
    buf[0]=count
    buf[count+1]=0xff
    for n in range(count):
        buf[1+n]=species
        off=MON_OFFSET+n*33
        buf[off]=species
        buf[off+3]=5  # level (Gen I box-struct level field)
        # 11-byte OT/nickname fields are deterministic and distinct.
        buf[OT_OFFSET+n*11:OT_OFFSET+(n+1)*11]=bytes([0x80+n%20])*10+b"\x50"
        buf[NICK_OFFSET+n*11:NICK_OFFSET+(n+1)*11]=bytes([0x81+n%20])*10+b"\x50"
    for n,value in enumerate(buf):
        memory[bank,base+n]=value
    return bytes(buf)

def fix_bank_checksums(memory, symbols, bank):
    """Mirror the Gen-I complement-of-sum bank and individual checksums."""
    if bank not in (2,3,4):
        raise ValueError("bank must be 2..4")
    base=symbols["sBox1"][1]
    total=4*BOX_BYTES
    full=bytes(memory[bank,base+i] for i in range(total))
    all_addr=symbols["sBank2AllBoxesChecksum"][1]
    indiv_addr=symbols["sBank2IndividualBoxChecksums"][1]
    memory[bank,all_addr]=(~sum(full))&0xff
    for i in range(4):
        memory[bank,indiv_addr+i]=(~sum(full[i*BOX_BYTES:(i+1)*BOX_BYTES]))&0xff

def seed_scenario(memory, symbols, destination, occupied=29, others_full=False):
    """Explicitly opt-in: fill 12 boxes, one available destination."""
    for i in range(12):
        fill_box(memory,symbols,i,30 if others_full else 0)
    fill_box(memory,symbols,destination,occupied)
    for bank in (2,3,4):
        fix_bank_checksums(memory,symbols,bank)
    return {"kind":"synthetic-emulator-fixture","destination":destination,
            "count":occupied,"other_boxes_full":bool(others_full)}
