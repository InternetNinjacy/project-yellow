#!/usr/bin/env python3
"""Execute isolated YEL-QOL-012 assembler entrypoints in real PyBoy CPU.

This is NOT the Python reference model or a live game save test.
Uses a ROM0 bootstrap hook to prepare CPU registers and call bank $3B code
before the regular game initializes; SRAM and WRAM are seeded explicitly.
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
           'Yel012PrepareCaptureInsert','Yel012CommitTransaction','Yel012AbortTransaction',
           'wCurrentBoxNum','wBoxDataStart','sYel012TransactionStatus',
           'sYel012TransactionNewRecord','sYel012TransactionShadow','sYel012TransactionBackup']
    for n in names:
        if n not in sym:raise RuntimeError('Missing symbol '+n)
    rom=Path(args.rom).read_bytes()
    em=PyBoy(args.rom,window='null',cgb=False,sound_emulated=False)
    em.set_emulation_speed(0)
    results=[]
    context={'call':None,'done':False,'started':False,'flags':None}
    regs=em.register_file
    # Isolated CPU calls have no initialized VBlank/joypad handlers;
    # keep IME harmless by masking IE and acknowledging IF.
    em.memory[0xffff]=0
    em.memory[0xff0f]=0
    # Park execution in an inert WRAM JR -2, preventing Game Freak's
    # real startup from corrupting CPU state between isolated calls.
    em.memory[0xc000]=0x18
    em.memory[0xc001]=0xfe
    def boot(ctx):
        # This ROM0 instruction is the emulator's CPU trampoline.
        if ctx['call'] is None:return
        if not ctx['started']:
            n=ctx['call']
            bank,addr=sym[n]
            assert bank==BANK,(n,bank)
            ctx['started']=True
            regs.SP=0xcff0
            em.memory[0xcfef]=0x01
            em.memory[0xcfee]=0x00
            # Return address 0x0100 (little endian), triggers hook again.
            regs.SP=0xcfee
            em.memory[0x2000]=bank
            regs.PC=addr
            regs.A=ctx.get('a',0)
            regs.D=(ctx.get('de',0)>>8)&0xff
            regs.E=ctx.get('de',0)&0xff
        else:
            ctx['flags']=regs.F
            ctx['done']=True
            ctx['call']=None
            regs.PC=0xc000
    em.hook_register(0,0x100,boot,context)
    context['interrupts']=0
    def isolate_interrupt(ctx):
        ctx['interrupts']+=1
        sp=regs.SP
        # The isolated CPU transaction has no game IRQ initialization.
        # Simulate an empty RETI for the pushed return address.
        regs.PC=em.memory[sp] | (em.memory[(sp+1)&0xffff]<<8)
        regs.SP=(sp+2)&0xffff
        em.memory[0xffff]=0
        em.memory[0xff0f]=0
    for vector in (0x40,0x48,0x50,0x58,0x60):
        em.hook_register(0,vector,isolate_interrupt,context)
    def call(n,a=0,de=0):
        context.update(call=n,started=False,done=False,flags=None,a=a,de=de)
        em.memory[0xffff]=0
        em.memory[0xff0f]=0
        regs.PC=0x0100
        for _ in range(350):
            em.tick(1,render=False,sound=False)
            if context['done']:return context['flags']
        raise AssertionError(f'{n}: CPU did not return to ROM0 trampoline; PC={regs.PC:04x} SP={regs.SP:04x} A={regs.A:02x} B={regs.B:02x} C={regs.C:02x} D={regs.D:02x} E={regs.E:02x} HL={regs.HL:04x} IE={em.memory[0xffff]:02x} IF={em.memory[0xff0f]:02x} interrupts={context[\"interrupts\"]}')
    def sram(bank,addr,length):
        return bytes(em.memory[bank,addr+i] for i in range(length))
    def set_sram(bank,addr,payload):
        for i,x in enumerate(payload):em.memory[bank,addr+i]=x
    def get(name):return sym[name][1]
    try:
        # Start via real CPU trampoline. No synthetic Python transaction results.
        for case,(boxid,count,mode) in enumerate([(0,29,'capture'),(4,30,'abort'),(8,20,'capture')]):
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
                flag=call('Yel012AbortTransaction')
                assert flag&16==0,(case,'abort',flag)
                assert sram(bank,base,BOX)==before,(case,'abort corruption')
            results.append({'box':boxid+1,'bank':bank,'mode':mode,'status':'PASS_ASSEMBLY_CPU'})
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
