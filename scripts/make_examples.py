#!/usr/bin/env python
"""Make the conformance examples: short manifests and this core's traces of them.

    python scripts/make_examples.py

Each example is checked against Nuked-OPLL (the referee, validation/build_referees.sh)
before it is written: an example the judge disagrees with is not written. Written to
examples/conformance/ as NAME.json and NAME.trace.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from referee import REFEREE, compare
from streams import SAMPLE, Writer

from ym2413_python import VARIANTS
from ym2413_python.conformance import run

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "examples" / "conformance"


def custom(w: Writer, raw: list[int]) -> None:
    for register, value in enumerate(raw):
        w.reg(register, value)


def instruments() -> Writer:
    w = Writer()
    w.note(0, 0x181, 4)
    for number in range(16):
        w.reg(0x30, number << 4)
        w.wait(60)
    w.note(0, 0x181, 4, key=False)
    w.wait(100)
    return w


def feedback() -> Writer:
    w = Writer()
    for fb in range(8):
        custom(w, [0x21, 0x21, 0x10, (fb & 3) << 3 | fb, 0xF0, 0xF0, 0x0F, 0x0F])
        w.reg(0x30, 0x00)
        w.note(0, 0x120, 4)
        w.wait(50)
    return w


def rhythm() -> Writer:
    w = Writer()
    for ch, fnum in zip((6, 7, 8), (0x120, 0x150, 0x1C0), strict=True):
        w.note(ch, fnum, 2, key=False)
    w.reg(0x36, 0x02)
    w.reg(0x37, 0x31)
    w.reg(0x38, 0x13)
    for pattern in (0x30, 0x28, 0x24, 0x22, 0x21, 0x3F):
        w.reg(0x0E, pattern)
        w.wait(120)
        w.reg(0x0E, 0x20)
        w.wait(30)
    w.reg(0x0E, 0x00)
    w.wait(60)
    return w


def envelopes() -> Writer:
    w = Writer()
    rng = random.Random(5)
    for i in range(12):
        rates = rng.randrange(8, 16) << 4 | rng.randrange(8, 16)
        carrier = [rates, rng.randrange(256)]
        carrier_flags = (i & 1) << 5 | (i & 2) << 3 | 0x01
        custom(w, [0x01, carrier_flags, 0x20, 0x00, 0xF8, carrier[0], 0x0F, carrier[1]])
        w.reg(0x30, 0x00)
        w.note(2, rng.randrange(512), rng.randrange(8), sustain=bool(i & 4))
        w.wait(70)
        w.note(2, 0x100, 4, key=False, sustain=bool(i & 8))
        w.wait(50)
    return w


def scaling() -> Writer:
    w = Writer()
    for multi in range(0, 16, 3):
        for ksl in range(4):
            levels = [ksl << 6 | 0x10, ksl << 6]
            custom(w, [multi, 0x10 | (15 - multi), *levels, 0xF0, 0xF0, 0x00, 0x00])
            w.reg(0x30, 0x00)
            for top in range(0, 16, 1 + multi % 3):  # every KSL table row in turn
                w.note(5, top << 5 | 0x0F, (multi + ksl) & 7)
                w.wait(6)
    return w


def lfo() -> Writer:
    """Vibrato and tremolo with test bit 3, which runs the LFOs every sample."""
    w = Writer()
    custom(w, [0xC1, 0xC1, 0x10, 0x05, 0xF0, 0xF0, 0x00, 0x00])
    w.reg(0x30, 0x00)
    w.note(0, 0x1FF, 5)
    w.reg(0x0F, 0x08)
    w.wait(1200)
    w.reg(0x0F, 0x02)
    w.wait(100)
    w.reg(0x0F, 0x00)
    w.wait(100)
    return w


def test_bits() -> Writer:
    w = Writer()
    w.reg(0x30, 0x30)
    w.note(0, 0x150, 4)
    for value in (0x01, 0x04, 0x02, 0x05, 0x00):
        w.reg(0x0F, value)
        w.wait(80)
    return w


def timing() -> Writer:
    """Writes faster than the catalog asks, back to back, and data without an address."""
    w = Writer()
    rng = random.Random(6)
    w.reg(0x30, 0x40)
    w.note(0, 0x120, 4)
    for _ in range(120):
        register = rng.choice((0x10, 0x20, 0x30, 0x0E, 0x05, 0x19)) + rng.randrange(3)
        gaps = {"after_address": rng.randrange(1, 4), "after_data": rng.randrange(1, 20)}
        w.reg(register, rng.randrange(256), **gaps)
    w.events += [(w.cycle, 0, 0x30), (w.cycle + 1, 0, 0x10), (w.cycle + 2, 1, 0x21)]
    w.cycle += 40
    w.wait(100)
    return w


def races() -> Writer:
    w = Writer()
    custom(w, [0x01, 0x01, 0x00, 0x07, 0xFF, 0xFF, 0x0F, 0x0F])
    for ch in (6, 7, 8):
        w.reg(0x30 + ch, 0x00)
    rng = random.Random(7)
    for _ in range(150):
        ch = rng.choice((6, 7, 8))
        w.reg(0x20 + ch, 0x18, after_address=1, after_data=rng.randrange(1, 18))
        rhythm = rng.choice((0x20, 0x00, 0x3F))
        w.reg(0x0E, rhythm, after_address=1, after_data=rng.randrange(1, 18))
        w.wait(rng.randrange(2, 6))
        w.reg(0x20 + ch, 0x08, after_address=1, after_data=1)
    return w


EXAMPLES = [
    ("instruments-ym2413", "YM2413", instruments),
    ("instruments-ds1001", "DS1001", instruments),
    ("instruments-ymf281", "YMF281", instruments),
    ("instruments-ym2423", "YM2423", instruments),
    ("feedback-ym2413", "YM2413", feedback),
    ("rhythm-ym2413", "YM2413", rhythm),
    ("rhythm-ym2413b", "YM2413B", rhythm),
    ("rhythm-ds1001", "DS1001", rhythm),
    ("envelopes-ym2413", "YM2413", envelopes),
    ("scaling-ym2413", "YM2413", scaling),
    ("lfo-ym2413", "YM2413", lfo),
    ("test-bits-ym2413", "YM2413", test_bits),
    ("timing-ym2413", "YM2413", timing),
    ("races-ym2413", "YM2413", races),
]


def main() -> int:
    if not REFEREE.exists():
        print("the referee is not built: sh validation/build_referees.sh")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, variant, build in EXAMPLES:
        w = build()
        cycles = w.cycle + 20 * SAMPLE
        if compare(VARIANTS[variant], w.events, cycles) is not None:
            print(f"{name}: the referee disagrees; not written")
            bad += 1
            continue
        manifest = {
            "version": 1,
            "name": name,
            "variant": variant,
            "clocks": cycles * 4,
            "events": [
                {"t": cycle * 4, "kind": ("address", "data")[port], "data": value}
                for cycle, port, value in w.events
            ],
        }
        (OUT / f"{name}.json").write_text(json.dumps(manifest, indent=1) + "\n")
        trace = run(manifest)
        (OUT / f"{name}.trace").write_text(trace)
        print(f"{name}: {cycles:,} cycles, {len(w.events)} writes, {trace.count(chr(10))} lines")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
