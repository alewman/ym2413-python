#!/usr/bin/env python
"""Record the sound-port writes a game makes on a board, as a referee stream.

    PYTHONPATH=/path/to/famicom-python/src python scripts/export_board_streams.py ROM \\
        --frames 3600 --out validation/streams/lagrange-point.stream

Two boards:

- ``--board famicom`` (famicom-python's VRC7, mapper 85): every write to $9010
  (address) and $9030 (data) with the CPU cycle it lands on. The VRC7's sound runs
  from its own 3.58 MHz resonator, twice the NTSC CPU clock and not locked to it; the
  stream takes it as exactly two input clocks per CPU cycle, so CPU cycle n falls in
  the chip's internal cycle n // 2.
- ``--board sms`` (sms-python's Japanese Master System with the FM unit): every
  write to ports $F0 (address) and $F1 (data). The YM2413 shares the Z80's crystal,
  so T-state n falls in internal cycle n // 4, exactly. sms-python has no FM unit,
  so this script answers port $F2 itself the way games detect one, reading back the
  last value written in its low three bits (an approximation for exporting, not a
  model of the unit).

Files are {u64 cycle; u8 port; u8 value} records, as validation/opll_ref.c reads
them, into validation/streams/ (ignored: derived from ROMs).
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path


def export_sms(rom: Path, frames: int, buttons: dict[int, int]) -> list[tuple[int, int, int]]:
    from sms_python.board import SMS_JAPAN
    from sms_python.cartridge import Cartridge
    from sms_python.system import System

    system = System(SMS_JAPAN, Cartridge.from_file(rom))
    board = system.board
    writes: list[tuple[int, int, int]] = []
    audio_control = [0]
    read_port, write_port = board.read_port, board.write_port

    def now() -> int:
        return system.cycles + (system._access_t or 0)

    def fm_read(port: int) -> int:
        if port & 0xFF == 0xF2:
            return audio_control[0] & 0x07
        return read_port(port)

    def fm_write(port: int, value: int) -> None:
        port &= 0xFF
        if port in (0xF0, 0xF1):
            writes.append((now() // 4, port & 1, value & 0xFF))
        elif port == 0xF2:
            audio_control[0] = value
        else:
            write_port(port, value)

    board.read_port, board.write_port = fm_read, fm_write
    for frame in range(frames):
        value = next((v for start, v in buttons.items() if start <= frame < start + 6), 0)
        board.io.pad1.pressed = {button for button in range(6) if value >> button & 1}
        system.run_frame()
    return writes


def export(rom: Path, frames: int, buttons: dict[int, int]) -> list[tuple[int, int, int]]:
    from famicom_python.machine import MACHINES
    from famicom_python.system import System

    system = System.from_rom(rom, MACHINES["famicom"])
    board = system.board
    ticks = board.cycle_ticks
    writes: list[tuple[int, int, int]] = []

    def observe(kind: str, address: int, value: int, t: int) -> None:
        if kind == "write" and address & 0xF030 in (0x9010, 0x9030):
            writes.append(((t // ticks) // 2, int(address & 0x20 != 0), value))

    board.bus_observers.append(observe)
    for frame in range(frames):
        # Each press holds its buttons for six frames.
        board.pads[0].buttons = next(
            (value for start, value in buttons.items() if start <= frame < start + 6), 0
        )
        system.run_frames(1)
    return writes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("rom", type=Path)
    parser.add_argument("--board", choices=("famicom", "sms"), default="famicom")
    parser.add_argument("--frames", type=int, default=3600)
    parser.add_argument(
        "--press", default="", help="frame:buttons,... held 6 frames (sms: bit n = button n)"
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    buttons = {int(f): int(b) for f, b in (p.split(":") for p in args.press.split(",") if p)}
    writes = (export_sms if args.board == "sms" else export)(args.rom, args.frames, buttons)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(b"".join(struct.pack("<QBB", c, p, v) for c, p, v in writes))
    last = writes[-1][0] if writes else 0
    print(f"{len(writes)} writes over {last:,} cycles to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
