#!/usr/bin/env python3
"""Execute isolated YEL-QOL-012 assembler entrypoints in real PyBoy CPU.

This is NOT the Python reference model or a live game save test.
Uses direct writable CPU registers to invoke bank $3B code
after normal boot initialization; SRAM and WRAM are seeded explicitly.
Any failed check exits nonzero, producing no raw save-state artifacts.
"""
import argparse,json,hashlib
from pathlib import Path
from pyboy import PyBoy

BOX=1682
MON=33
NAME=11
MON_OFFSET=32
OT_OFFSET=1022
NICK_OFFSET=1352
BANK=0x3b
SLOT_BYTES=55

def symbols(path):
    found={}
    for line in Path(path).read_text().splitlines():
        word=line.split(';')[0].split()
        if len(word)>=2 and ':' in word[0]:
            bank,addr=word[0].split(':',1)
            try:found[word[1]]=(int(bank,16),int(addr,16))
            except ValueError:pass
    return found

def seed(count,offset):
    data=bytearray(BOX);data[0]=count;data[count+1]=255
    for i in range(count):
        species=((i+offset)%150)+1
        data[1+i]=species
        data[MON_OFFSET+i*MON:MON_OFFSET+(i+1)*MON]=bytes([species])+bytes([(i*11+offset)%256])*32
        data[OT_OFFSET+i*NAME:OT_OFFSET+(i+1)*NAME]=bytes([(i+61+offset)%256])*NAME
        data[NICK_OFFSET+i*NAME:NICK_OFFSET+(i+1)*NAME]=bytes([(i+117+offset)%256])*NAME
    return bytes(data)

def record(i,offset):
    return bytes([((i+offset)%150)+1])+bytes([(i*11+offset)%256])*32+bytes([(i+61+offset)%256])*NAME+bytes([(i+117+offset)%256])*NAME

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--rom',required=True);p.add_argument('--sym',required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    sym=symbols(args.sym)
    names=['Yel012BeginTransaction','Yel012StageWindow','Yel012CommitStagedWindow',
           'Yel012ReadBoxRecord','wBoxCount','wBoxSpecies','wBoxMons','wBoxMonOT','wBoxMonNicks',
           'Yel012PrepareCaptureInsert','Yel012CommitTransaction','Yel012AbortTransaction',
           'wCurrentBoxNum','wBoxDataStart','sYel012TransactionStatus',
           'sYel012TransactionNewRecord','sYel012TransactionShadow','sYel012TransactionBackup']
    for n in names:
        if n not in sym:raise RuntimeError('Missing symbol '+n)
    rom=Path(args.rom).read_bytes()
    em=PyBoy(args.rom,window='null',cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    # Finish the emulator's actual boot ROM/startup before manipulating PC.
    # The real game may then sit at its title screen; transaction tests
    # replace the CPU entry and SRAM contents explicitly.
    em.tick(400,render=False,sound=False)
    results=[]
    regs=em.register_file
    # Real CPU execution with an inert WRAM return loop, no ROM hooks.
    # CPU calls return to $C000: JR -2. JR does not change flags.
    em.memory[0xc000]=0x18
    em.memory[0xc001]=0xfe
    em.memory[0xffff]=0
    em.memory[0xff0f]=0
    def call(n,a=0,de=0):
        bank,addr=sym[n]
        assert bank==BANK,(n,bank)
        # Prime mapped ROMX directly, a valid LR35902 return stack, and
        # a distinct CPU entrypoint on each invocation.
        em.memory[0x2000]=bank
        em.memory[0xffff]=0
        em.memory[0xff0f]=0
        em.memory[0xcfee]=0x00
        em.memory[0xcfef]=0xc0
        regs.SP=0xcfee
        regs.A=a
        regs.D=(de>>8)&0xff
        regs.E=de&0xff
        regs.PC=addr
        for _ in range(350):
            em.tick(1,render=False,sound=False)
            if regs.PC in (0xc000,0xc001):
                return regs.F
        raise AssertionError(
          f'{n}: direct CPU call did not return; PC={regs.PC:04x} SP={regs.SP:04x} '
          f'AF={regs.A:02x}/{regs.F:02x} BC={regs.B:02x}/{regs.C:02x} '
          f'DE={regs.D:02x}/{regs.E:02x} HL={regs.HL:04x} '
          f'IE={em.memory[0xffff]:02x} IF={em.memory[0xff0f]:02x}')
    def sram(bank,addr,length):
        return bytes(em.memory[bank,addr+i] for i in range(length))
    def set_sram(bank,addr,payload):
        for i,x in enumerate(payload):em.memory[bank,addr+i]=x
    def get(name):return sym[name][1]
    try:
        # Start via real CPU trampoline. No synthetic Python transaction results.
        for case,(boxid,count,mode) in enumerate([(0,29,'capture'),(4,30,'abort'),(8,29,'capture')]):
            bank=2+boxid//4
            base=get('sBox1')+(boxid%4)*BOX
            before=seed(count,case+3)
            set_sram(bank,base,before)
            set_sram(5,get('sYel012TransactionStatus'),b'\x00')
            em.memory[get('wCurrentBoxNum')]=boxid|0x80
            flag=call('Yel012BeginTransaction')
            assert flag&16==0,(case,'begin',flag)
            assert sram(5,get('sYel012TransactionBackup'),BOX)==before,(case,'snapshot')
            if mode=='capture':
                new=record(150,case+3)
                inputaddr=get('wBoxDataStart')
                for j,c in enumerate(new):em.memory[inputaddr+j]=c
                flag=call('Yel012PrepareCaptureInsert',de=inputaddr)
                assert flag&16==0,(case,'prepare',flag)
                shadow=sram(5,get('sYel012TransactionShadow'),BOX)
                assert shadow[0]==count+1,(case,'count')
                flag=call('Yel012CommitTransaction')
                assert flag&16==0,(case,'commit',flag)
                after=sram(bank,base,BOX)
                assert after==shadow,(case,'physical vs shadow')
                for i in range(count):
                    assert after[MON_OFFSET+(i+1)*MON:MON_OFFSET+(i+2)*MON]==before[MON_OFFSET+i*MON:MON_OFFSET+(i+1)*MON],(case,'shift mon',i)
                    assert after[OT_OFFSET+(i+1)*NAME:OT_OFFSET+(i+2)*NAME]==before[OT_OFFSET+i*NAME:OT_OFFSET+(i+1)*NAME],(case,'shift ot',i)
                    assert after[NICK_OFFSET+(i+1)*NAME:NICK_OFFSET+(i+2)*NAME]==before[NICK_OFFSET+i*NAME:NICK_OFFSET+(i+1)*NAME],(case,'shift nick',i)
            else:
                # Reject a new capture with count=30 before any page is dirty.
                inputaddr=get('wBoxDataStart')
                new=record(150,case+3)
                for j,c in enumerate(new):em.memory[inputaddr+j]=c
                flag=call('Yel012PrepareCaptureInsert',de=inputaddr)
                assert flag&16,(case,'full box insertion wrongly accepted',flag)
                assert sram(bank,base,BOX)==before,(case,'full rejection changed physical SRAM')
                # Exercise both WRAM pages of a full 30-record physical box.
                for page,pagecount in ((0,20),(20,10)):
                    flag=call('Yel012StageWindow',a=page)
                    assert flag&16==0,(case,'page stage',page,flag)
                    assert em.memory[get('wBoxCount')]==pagecount,(case,'page count',page)
                    for i in range(pagecount):
                        slot=i+page
                        assert em.memory[get('wBoxSpecies')+i]==before[1+slot],(case,'page species',slot)
                        for label,offset,stride,sz in (
                            ('mon',MON_OFFSET,MON,MON),
                            ('ot',OT_OFFSET,NAME,NAME),
                            ('nick',NICK_OFFSET,NAME,NAME)):
                            wrambase=get({'mon':'wBoxMons','ot':'wBoxMonOT',
                                          'nick':'wBoxMonNicks'}[label])
                            seen=bytes(em.memory[wrambase+i*stride+j] for j in range(sz))
                            wanted=before[offset+slot*stride:offset+(slot+1)*stride]
                            assert seen==wanted,(case,'staged page',label,slot)
                    if page==0:
                        flag=call('Yel012CommitStagedWindow')
                        assert flag&16==0,(case,'valid page commit',flag)
                    else:
                        # Force a species-table mismatch: the shadow must not
                        # be physically committed and abort must restore it.
                        em.memory[get('wBoxSpecies')]=0
                        flag=call('Yel012CommitStagedWindow')
                        assert flag&16,(case,'invalid page wrongly accepted',flag)
                assert sram(5,get('sYel012TransactionBackup'),BOX)==before,(case,'rollback snapshot')
                flag=call('Yel012AbortTransaction')
                assert flag&16==0,(case,'abort',flag)
                assert sram(bank,base,BOX)==before,(case,'abort corruption')
            # Execute the banked LR35902 55-byte record reader for every
            # physical 0..29 slot, including all OT/nickname fields.
            final=sram(bank,base,BOX)
            assert final[0]==30,(case,'final occupancy',final[0])
            for index in range(30):
                addr=get('wBoxDataStart')
                flag=call('Yel012ReadBoxRecord',a=index,de=addr)
                assert flag&16==0,(case,'record read',index,flag)
                seen=bytes(em.memory[addr+j] for j in range(SLOT_BYTES))
                expected=(final[MON_OFFSET+index*MON:MON_OFFSET+(index+1)*MON]
                          +final[OT_OFFSET+index*NAME:OT_OFFSET+(index+1)*NAME]
                          +final[NICK_OFFSET+index*NAME:NICK_OFFSET+(index+1)*NAME])
                assert seen==expected,(case,'record bytes differ',index)
            results.append({'box':boxid+1,'bank':bank,'mode':mode,
                            'slots_verified':30,'status':'PASS_ASSEMBLY_CPU'})
        status='PASS_ISOLATED_ASSEMBLY_TRANSACTION_NOT_SAVE_VERIFIED'
    except Exception as exc:
        status='FAIL'
        results.append({'status':'FAIL','error':str(exc)})
        raise
    finally:
        em.stop(save=False)
        out.write_text(json.dumps({'schema':'YEL-QOL-012-CPU/1',
                                   'rom_sha256':hashlib.sha256(rom).hexdigest(),
                                   'status':status if 'status' in locals() else 'FAIL',
                                   'cases':results},indent=2)+'\n')
if __name__=='__main__':main()
