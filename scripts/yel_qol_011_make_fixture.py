#!/usr/bin/env python3
"""YEL-QOL-011 seeded multi-box fixtures for *existing* legal gameplay states.

Uses a genuine PyBoy saved state at the pre-capture battle prompt. Generates
deterministic known records across all 12 boxes, with coherent box sentinels
and SRAM checksums. Never commits a ROM, save, or emulator state.
This fixture builder does not prove a catch occurred: follow it with emulator
input replay plus full before/after data assertions.
"""
import argparse
import hashlib
import json
from pathlib import Path
from pyboy import PyBoy

NUM_BOXES = 12
CAPACITY = 20
MON_SIZE = 33
NAME_LENGTH = 11
BOX_BYTES = 1 + CAPACITY + 1 + CAPACITY * MON_SIZE + 2 * CAPACITY * NAME_LENGTH

def read_symbols(path):
    symbols = {}
    for raw in Path(path).read_text().splitlines():
        p = raw.split(';', 1)[0].split()
        if len(p) < 2 or ':' not in p[0]:
            continue
        bank, address = p[0].split(':', 1)
        try:
            symbols[p[1]] = int(bank, 16), int(address, 16)
        except ValueError:
            pass
    return symbols

def record(box, slot):
    # Synthetic but structurally valid Gen-I box records, unique per slot.
    # Species 0x10 = Pidgey; experience, OT ID and DVs are unique markers.
    r = bytearray(MON_SIZE)
    r[0] = 0x24   # Pidgey internal species ID in Yellow.
    r[1:3] = (20 + slot).to_bytes(2, 'big')  # HP
    r[3] = 8 + (slot % 8)                    # box level
    r[7] = 45                               # catch rate
    r[8] = 33                               # Tackle move ID
    r[12:14] = (0x1000 + box * 20 + slot).to_bytes(2, 'big')
    r[14:17] = (500 + box * 20 + slot).to_bytes(3, 'big')
    r[27:29] = (0x2000 + box * 20 + slot).to_bytes(2, 'big')
    r[29] = 35                              # tackle PP
    return bytes(r)

def name(box, slot, prefix):
    # Game Boy text format: 0x80=A, 0x81=B, 0x50=terminator.
    # Unique identifiers are also encoded in OT ID, EXP and DVs.
    string = f'{prefix}{box+1:02d}{slot+1:02d}'
    mapping = {chr(65+i): 0x80+i for i in range(26)}
    mapping.update({str(i): 0xF6+i for i in range(10)})
    return bytes([mapping[ch] for ch in string] + [0x50] * (NAME_LENGTH-len(string)))

def box_data(box, count):
    if not (0 <= count <= CAPACITY):
        raise ValueError('Invalid count')
    d = bytearray(BOX_BYTES)
    d[0] = count
    d[1:1+count] = [0x24] * count
    d[1+count] = 0xFF
    offset = CAPACITY + 2
    for slot in range(count):
        d[offset + slot*MON_SIZE:offset+(slot+1)*MON_SIZE] = record(box,slot)
    offset += CAPACITY * MON_SIZE
    for slot in range(count):
        d[offset + slot*NAME_LENGTH:offset+(slot+1)*NAME_LENGTH] = name(box,slot,'O')
    offset += CAPACITY * NAME_LENGTH
    for slot in range(count):
        d[offset + slot*NAME_LENGTH:offset+(slot+1)*NAME_LENGTH] = name(box,slot,'N')
    return bytes(d)

def checksum(data):
    return (~sum(data)) & 0xFF

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rom',required=True)
    p.add_argument('--sym',required=True)
    p.add_argument('--base-state',required=True,help='Existing real game PyBoy state ready to throw a ball')
    p.add_argument('--counts',required=True,help='12 comma-separated counts (0..20)')
    p.add_argument('--active',type=int,required=True,help='0-based active box')
    p.add_argument('--out',required=True)
    a=p.parse_args()
    counts=[int(v) for v in a.counts.split(',')]
    if len(counts)!=NUM_BOXES or any(not 0<=v<=CAPACITY for v in counts):
        raise ValueError('Expected exactly twelve counts from 0 to 20')
    if not 0<=a.active<NUM_BOXES:
        raise ValueError('Active box outside 0..11')
    syms=read_symbols(a.sym)
    needed=['wBoxDataStart','wBoxDataEnd','wCurrentBoxNum','sBox1','sBox7',
            'sBank2AllBoxesChecksum','sBank3AllBoxesChecksum',
            'sBank2IndividualBoxChecksums','sBank3IndividualBoxChecksums']
    absent=[n for n in needed if n not in syms]
    if absent:
        raise RuntimeError(f'Missing symbols: {absent}')
    start=syms['wBoxDataStart'][1]
    end=syms['wBoxDataEnd'][1]
    if end-start!=BOX_BYTES:
        raise RuntimeError(f'Box layout mismatch: source {end-start}, expected {BOX_BYTES}')
    emu=PyBoy(a.rom,window='null',cgb=False,sound_emulated=False)
    target=Path(a.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with open(a.base_state,'rb') as f:
            emu.load_state(f)
        # First-time switching is now initialized; set the original flag bit,
        # while preserving other wCurrentBoxNum flags.
        old=emu.memory[syms['wCurrentBoxNum'][1]]
        emu.memory[syms['wCurrentBoxNum'][1]]=(old & 0x70) | 0x80 | a.active
        for i,count in enumerate(counts):
            b=box_data(i,count)
            if i==a.active:
                emu.memory[start:end]=list(b)
            bank=2 if i<6 else 3
            address=syms['sBox1' if bank==2 else 'sBox7'][1] + (i%6)*BOX_BYTES
            emu.memory[bank,address:address+BOX_BYTES]=list(b)
        for bank,base,aggregate,individual in (
            (2,'sBox1','sBank2AllBoxesChecksum','sBank2IndividualBoxChecksums'),
            (3,'sBox7','sBank3AllBoxesChecksum','sBank3IndividualBoxChecksums')):
            start_sram=syms[base][1]
            raw=bytes(emu.memory[bank,start_sram:start_sram+6*BOX_BYTES])
            emu.memory[bank,syms[aggregate][1]]=checksum(raw)
            for i in range(6):
                emu.memory[bank,syms[individual][1]+i]=checksum(raw[i*BOX_BYTES:(i+1)*BOX_BYTES])
        # This is an emulator-state fixture, not an in-game save.
        with target.open('wb') as f:
            emu.save_state(f)
        manifest={'work':'YEL-QOL-011','fixture':'synthetic records based on real gameplay state',
                  'active_zero_based':a.active,'counts':counts,
                  'rom_sha256':hashlib.sha256(Path(a.rom).read_bytes()).hexdigest(),
                  'base_state_sha256':hashlib.sha256(Path(a.base_state).read_bytes()).hexdigest(),
                  'fixture_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                  'verification':'NOT_RUN_CAPTURE'}
        target.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps(manifest,indent=2))
    finally:
        emu.stop(save=False)

if __name__=='__main__':
    main()
