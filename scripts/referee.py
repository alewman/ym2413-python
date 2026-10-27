#!/usr/bin/env python
"""Run register streams through the core and Nuked-OPLL, cycle by cycle.

A stream is a list of ``(cycle, port, value)`` writes, sorted; a write is applied
before the internal cycle it names (validation/opll_ref.c's convention). Both
sides start from /IC and run ``cycles`` internal cycles; the result is the first
cycle whose (MO, RO) differ, or None.

    python scripts/referee.py            # the synthetic streams of streams.py
"""

from __future__ import annotations

import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from ym2413_python import CLOCKS_PER_CYCLE, OPLL, VARIANTS, OPLLVariant

ROOT = Path(__file__).resolve().parent.parent
REFEREE = ROOT / "reference" / "build-referees" / "opll_ref"

Stream = list[tuple[int, int, int]]


def nuked(variant: OPLLVariant, stream: Stream, cycles: int) -> list[tuple[int, int]]:
    with tempfile.TemporaryDirectory() as tmp:
        events, out = Path(tmp) / "events.bin", Path(tmp) / "out.bin"
        events.write_bytes(b"".join(struct.pack("<QBB", c, p, v) for c, p, v in stream))
        subprocess.run(
            [str(REFEREE), str(variant.nuked_type), str(events), str(out), str(cycles)],
            check=True,
        )
        data = out.read_bytes()
    return list(struct.iter_unpack("<hh", data))


def core(variant: OPLLVariant, stream: Stream, cycles: int) -> list[tuple[int, int]]:
    chip = OPLL(variant)
    writes = iter(stream)
    pending = next(writes, None)
    for cycle in range(cycles):
        while pending is not None and pending[0] <= cycle:
            chip.write(pending[1], pending[2])
            pending = next(writes, None)
        chip.run(CLOCKS_PER_CYCLE)
    return chip.take_outputs()


def compare(variant: OPLLVariant, stream: Stream, cycles: int) -> int | None:
    """The first cycle where the core and Nuked-OPLL differ, or None."""
    theirs, ours = nuked(variant, stream, cycles), core(variant, stream, cycles)
    for cycle, (a, b) in enumerate(zip(ours, theirs, strict=True)):
        if a != b:
            return cycle
    return None


def main(argv: list[str] | None = None) -> int:
    from streams import STREAMS

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--only", help="a stream name to run alone")
    parser.add_argument("--variant", action="append", help="variant names (default: all)")
    args = parser.parse_args(argv)
    variants = [VARIANTS[n] for n in args.variant] if args.variant else list(VARIANTS.values())
    bad = 0
    for name, (stream, cycles) in STREAMS.items():
        if args.only and name != args.only:
            continue
        for variant in variants:
            first = compare(variant, stream, cycles)
            status = "equal" if first is None else f"DIFFER at cycle {first}"
            print(f"{name:28s} {variant.name:8s} {cycles:9,d} cycles: {status}", flush=True)
            bad += first is not None
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
