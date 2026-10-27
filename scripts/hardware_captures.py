#!/usr/bin/env python
"""Compare the core with andete's captures of a real YM2413's rhythm output.

    python scripts/hardware_captures.py                 # every BD and TOM capture
    python scripts/hardware_captures.py gold-tom-100    # one
    python scripts/hardware_captures.py --control       # the same fits, wrong on purpose

andete (openMSX) sampled a real YM2413's MO/RO pins with a 12-bit ADC once per 72
clocks and mapped each sample back to the 9-bit DAC level (results/20150209.txt):
the ``results/rhythm/gold-*`` files, one level per sample, 255 - the signed channel
output. The repository has no licence: fetched by scripts/fetch_references.py into
reference/, read here, never copied.

What a capture does not say is when key-on landed against the chip's free-running
envelope timer, so each fit sweeps key-on over 256 sample offsets (with the referee,
for speed) and keeps the best; the core then reruns the best fit and must equal the
referee on every sample. Exactness is judged on the quiet samples (within 32 levels
of zero, changing by at most 2 a sample): louder and faster stretches carry the
analogue chain's errors (ADC non-linearity, drift, the shaping board's bandwidth),
which andete describes. SD, HH and TCY need the noise generator's state or a
free-running phase counter as well, a search not done here.
"""

from __future__ import annotations

import argparse
import array
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from referee import REFEREE
from streams import SAMPLE, Writer

from ym2413_python import OPLL, VARIANTS

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "reference" / "src" / "andete-ym2413" / "results" / "rhythm"

#: drum: (its key bit in $0E, its frequency channel, the RO cycle of its first copy)
DRUMS = {"bd": (0x10, 6, 1), "tom": (0x04, 8, 0)}

#: Not a bass drum: a full-scale tone of about 14 samples a period, with glitches.
#: Mislabelled, or made with settings the name does not carry.
UNEXPLAINED = {"gold-bd-e25"}


def drum_of(name: str) -> str:
    """gold-bd2-100 is a second BD series (andete does not say what changed)."""
    return name.split("-")[1].rstrip("2")


def settings(name: str) -> tuple[int, int, int | None]:
    """The frequency and key-on length a capture's name carries, as sweep.cc reads it."""
    found = re.search(r"-([0-9a-f])([0-9a-f]{2})$", name)
    if found is None:
        raise ValueError(f"{name}: no frequency in the name")
    f_high, fnum = int(found[1], 16), int(found[2], 16)
    length = int(name.split("-L")[1].split("-")[0]) if "-L" in name else None
    return f_high, fnum, length


def stream(drum: str, name: str, offset: int, control: bool) -> tuple[list, int, int]:
    """The writes, the sample key-on lands in, and the RO cycle to read."""
    key, ch, ro_cycle = DRUMS[drum]
    f_high, fnum, length = settings(name)
    w = Writer()
    w.reg(0x10 + ch, fnum)
    w.reg(0x20 + ch, f_high)
    w.reg(0x36, 0x00)
    w.reg(0x37, 0x00)
    w.reg(0x38, 0x10 if control and drum == "tom" else 0x00)  # TOM 3 dB down
    if control and drum == "bd":
        w.reg(0x36, 0x01)  # BD 3 dB down
    w.reg(0x0E, 0x20)
    w.wait(64 + offset)
    w.reg(0x0E, 0x20 | key)
    on = w.cycle // SAMPLE
    if length is not None:
        w.wait(length)
        w.reg(0x0E, 0x20)
    return w.events, on, ro_cycle


def channel(word: int) -> int:
    """A DAC word back to the signed 9-bit channel output (the word is +1 for >= 0)."""
    return word - 1 if word > 0 else word


def referee_ro(events: list, cycles: int, ro_cycle: int, tmp: Path) -> list[int]:
    ev, out = tmp / "events.bin", tmp / "out.bin"
    ev.write_bytes(b"".join(struct.pack("<QBB", c, p, v) for c, p, v in events))
    subprocess.run([str(REFEREE), "0", str(ev), str(out), str(cycles)], check=True)
    words = array.array("h")
    words.frombytes(out.read_bytes())
    return list(words[ro_cycle * 2 + 1 :: SAMPLE * 2])


def core_ro(events: list, cycles: int, ro_cycle: int) -> list[int]:
    chip = OPLL(VARIANTS["YM2413"])
    words: list[tuple[int, int]] = []
    for cycle, port, value in events:
        chip.run(cycle * 4 - chip.clock)
        words += chip.take_outputs()
        chip.write(port, value)
    chip.run(cycles * 4 - chip.clock)
    words += chip.take_outputs()
    return [ro for _, ro in words[ro_cycle::SAMPLE]]


def compare(model: list[int], gold: list[int]) -> tuple[int, int, list[int]]:
    """Align the first sample that leaves silence, within two samples; the best fit."""
    m0 = next(i for i, v in enumerate(model) if v != 0)
    g0 = next(i for i, g in enumerate(gold) if g != 255)
    best = None
    for shift in range(-2, 3):
        if m0 + shift < 0:
            continue
        levels = [255 - v for v in model[m0 + shift :]]
        diffs = [abs(m - g) for m, g in zip(levels, gold[g0:], strict=False)]
        cost = sum(d * d for d in diffs)
        if best is None or cost < best[0]:
            best = (cost, shift, diffs)
    return best


def quiet(gold: list[int], diffs: list[int], model: list[int]) -> list[int]:
    g = gold[next(i for i, x in enumerate(gold) if x != 255) :]
    return [
        d
        for i, d in enumerate(diffs)
        if i
        and abs(g[i] - 255) <= 32
        and abs(g[i] - g[i - 1]) <= 2
        and abs(model[i] - model[i - 1]) <= 2
    ]


def fit(path: Path, drum: str, offsets: int, control: bool) -> str:
    gold = [int(x) for x in path.read_text().split()]
    best = None
    with tempfile.TemporaryDirectory() as tmp:
        for offset in range(offsets):
            events, on, ro_cycle = stream(drum, path.name, offset, control)
            cycles = (on + len(gold) + 40) * SAMPLE
            model = [channel(w) for w in referee_ro(events, cycles, ro_cycle, Path(tmp))[on:]]
            cost, shift, diffs = compare(model, gold)
            if best is None or cost < best[0]:
                best = (cost, offset, shift, diffs, events, on, ro_cycle, cycles, model)
    cost, offset, shift, diffs, events, on, ro_cycle, cycles, model = best
    ours = [channel(w) for w in core_ro(events, cycles, ro_cycle)[on:]]
    if ours != model:
        raise SystemExit(f"{path.name}: the core differs from the referee at offset {offset}")
    m0 = next(i for i, v in enumerate(model) if v != 0) + shift
    levels = [255 - v for v in model[m0:]]
    q = quiet(gold, diffs, levels)
    n = len(diffs)
    return (
        f"{path.name:<22} {drum:<3} offset {offset:3d}  samples {n:6d}"
        f"  exact {sum(d == 0 for d in diffs) / n:.3f}"
        f"  within 2 {sum(d <= 2 for d in diffs) / n:.3f}"
        f"  quiet {len(q):6d} exact {sum(d == 0 for d in q) / len(q):.3f}"
        f" off by >1 {sum(d > 1 for d in q):5d}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("names", nargs="*", help="captures, e.g. gold-tom-100 (default: all)")
    parser.add_argument("--offsets", type=int, default=256)
    parser.add_argument("--control", action="store_true", help="fit 3 dB too quiet")
    args = parser.parse_args()
    if not REFEREE.exists():
        print("the referee is not built: sh validation/build_referees.sh")
        return 1
    if not GOLD.exists():
        print("the captures are not fetched: python scripts/fetch_references.py")
        return 1
    names = args.names or sorted(p.name for p in GOLD.glob("gold-*") if drum_of(p.name) in DRUMS)
    for name in names:
        if name in UNEXPLAINED:
            print(f"{name:<22} skipped: not the drum its name says")
            continue
        drum = drum_of(name)
        try:
            settings(name)
        except ValueError:
            print(f"{name:<22} skipped: its name carries no frequency")
            continue
        print(fit(GOLD / name, drum, args.offsets, args.control), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
