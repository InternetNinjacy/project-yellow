#!/usr/bin/env python3
"""Read authoritative SameBoy SGB map and player coordinates via the native debugger.

A standalone PTY is essential: SameBoy SDL's textual debugger is terminal-driven.
Never guess player coordinates from screenshot timing. The probe fails if the
debugger does not respond with memory examinations.
"""
import argparse
import json
import os
import pty
import select
import signal
import subprocess
import time
from pathlib import Path


def symbols(path):
    found = {}
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) < 2 or ":" not in parts[0]:
            continue
        name = parts[1]
        if name in ("wCurMap", "wXCoord", "wYCoord"):
            found[name] = int(parts[0].split(":")[1], 16)
    if set(found) != {"wCurMap", "wXCoord", "wYCoord"}:
        raise ValueError(f"Missing coordinate symbols: {found}")
    return found


def read_for(fd, seconds):
    data = bytearray()
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if select.select([fd], [], [], min(0.2, until - time.monotonic()))[0]:
            try:
                part = os.read(fd, 65536)
            except OSError:
                break
            if not part:
                break
            data.extend(part)
    return data.decode("utf-8", errors="replace")


def press(window, key, hold=0.35):
    subprocess.run(["xdotool", "keydown", "--window", window, key], check=True)
    time.sleep(hold)
    subprocess.run(["xdotool", "keyup", "--window", window, key], check=True)
    time.sleep(1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--emulator", required=True)
    p.add_argument("--rom", required=True)
    p.add_argument("--sym", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    addrs = symbols(args.sym)
    master, slave = pty.openpty()
    process = subprocess.Popen([args.emulator, "--nogl", "--model", "sgb-ntsc", args.rom],
                               stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
    os.close(slave)
    log = ""
    try:
        time.sleep(65)
        windows = subprocess.check_output(["xdotool", "search", "--name", "SameBoy"], text=True).splitlines()
        if not windows:
            raise AssertionError("No SameBoy window")
        window = windows[0]
        press(window, "BackSpace")
        time.sleep(3)
        press(window, "Down")
        press(window, "x")
        time.sleep(5)
        for _ in range(28):
            press(window, "x", 0.22)
        time.sleep(3)
        # SIGINT is documented as the debugger's CPU interruption.
        os.kill(process.pid, signal.SIGINT)
        log += read_for(master, 3)
        if process.poll() is not None:
            raise AssertionError("SameBoy exited instead of entering debugger")
        for label, address in addrs.items():
            os.write(master, f"examine/1 ${address:04x}\n".encode())
            log += read_for(master, 1.5)
        (args.out / "debugger_transcript.txt").write_text(log)
        (args.out / "symbols.json").write_text(json.dumps(addrs, indent=2)+"\n")
        if "wCurMap" in log and "wXCoord" in log and "wYCoord" in log:
            pass
        # In this first probe, demand output after each examine command.
        if log.lower().count("examine/1") < 3 and log.lower().count("$d") < 3:
            raise AssertionError("SameBoy debugger did not echo/read all memory commands")
        print("SGB debugger probe collected three RAM examinations", flush=True)
    finally:
        process.terminate()
        try: process.wait(timeout=3)
        except subprocess.TimeoutExpired: process.kill()
        os.close(master)


if __name__ == "__main__":
    main()
