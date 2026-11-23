#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Rung 6: Nuked-OPLL run as a closed box beside the core (docs/validation.md).

Nuked-OPLL (Nuke.YKT, GPL-2.0-or-later) is a DETECTOR: a difference says where
to look and proves nothing about a chip. Its source was not read
(docs/restart.md rule 8). ``nuked_harness.c`` drives it through the three calls
its header declares; everything said about it below was learned from its output.
A difference is written down in docs/validation.md, never fixed by changing the
core to agree, and no constant is fitted to the model's output (docs/provenance.md, P6).

    python validation/closed_box.py            build if needed, run every stream
    python validation/closed_box.py --list     name the streams
    python validation/closed_box.py NAME ...   run some

The streams are ``validation/streams.py``'s, the same register writes at the same
slots on both. Three normalisations, each measured from the model's output on a
plain sine (``calibrate``) and nothing else:

1. One ``OPLL_Clock`` call is one slot: a sample's words repeat every 18 calls.
2. Two frames, both measured. In the "phase" frame (``OFFSET``, 40 slots, the
   default) a plain sine keyed on agrees slot for slot: it is checked at start-up
   for each variant. In the "register" frame (``--offset 4``) a volume write
   changes the words of both on the same slot. The two differ by two samples:
   from a key-on write the model's sound starts two samples later than the
   core's (U20, U9; docs/validation.md). Neither frame is "right"; each hides
   the other's differences.
3. Encoding. The model writes a word as sign x (size + 1): +0 is 1, -0 is -1,
   +255 is 256, -255 is -256. The core's one's-complement word w is mapped to
   w + 1 when w >= 0 and kept otherwise. The model also has a value 0, which no
   word maps to: it is what it gives in slots that carry no word (its resting
   level, U10). A model 0 is counted equal to a core +0.

Each stream is reported per pin: slots compared, slots that differ, and where the
first difference falls (sample, slot). Exit status is 0 whatever is found.
"""

from __future__ import annotations

import argparse
import os
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "validation"))

from streams import STREAMS, Writer

from ym2413_python import DS1001, OPLL, YM2413

MODEL = ROOT / "reference" / "nuked-opll"
BUILD = ROOT / "validation" / "build"
HARNESS = BUILD / "nuked_harness"
#: The harness is linked with Nuked-OPLL, so it is a GPL tool, kept outside this
#: repository since 2026-11-22 (docs/provenance.md, "History"): YM2413_GPL_TOOLS names
#: the folder that holds nuked_harness.c (emu-tools-gpl's tools/ym2413-python).
GPL_TOOLS = os.environ.get("YM2413_GPL_TOOLS")

#: The header's chip-type numbers.
CHIP_TYPE = {"YM2413": 0, "DS1001": 1}

#: Slots by which the model's words follow the core's (normalisation 2).
OFFSET = 40

#: Samples at the start of each stream left out of the count: both are settling
#: from reset, and their reset states are not known to match (U3).
SETTLE = 4

Events = list[tuple[int, int, int]]


def build() -> None:
    """Compile the harness against the fetched model. Compiler messages are kept
    out of sight (-w, stderr to a file): they would quote the model's source."""
    if not GPL_TOOLS:
        sys.exit("nuked_harness.c is a GPL tool kept outside this repository: set YM2413_GPL_TOOLS")
    sources = [Path(GPL_TOOLS) / "nuked_harness.c", MODEL / "opll.c"]
    for source in sources:
        if not source.exists():
            sys.exit(f"{source} is missing: run scripts/fetch_references.py")
    if HARNESS.exists() and all(HARNESS.stat().st_mtime > s.stat().st_mtime for s in sources):
        return
    BUILD.mkdir(parents=True, exist_ok=True)
    command = ["cc", "-O2", "-w", "-I", str(MODEL), "-o", str(HARNESS), *map(str, sources)]
    with (BUILD / "cc.log").open("wb") as log:
        if subprocess.run(command, stderr=log, check=False).returncode:
            sys.exit("the harness did not compile; validation/build/cc.log is not to be read")


def model_slots(
    events: Events, length: int, variant, offset: int = OFFSET
) -> list[tuple[int, int]]:
    """The model's (melody, rhythm) words, one pair per slot, ``offset`` slots on."""
    commands, now = [], 0
    for cycle, port, value in events:
        commands += [f"c {cycle - now}", f"w {port} {value}"]
        now = cycle
    commands.append(f"c {length - now + offset}")
    result = subprocess.run(
        [str(HARNESS), str(CHIP_TYPE[variant.name])],
        input="\n".join(commands).encode(),
        capture_output=True,
        check=True,
    )
    values = struct.unpack(f"<{len(result.stdout) // 4}i", result.stdout)
    return list(zip(values[0::2], values[1::2], strict=True))[offset:]


def core_slots(events: Events, length: int, variant) -> list[tuple[int, int]]:
    """The core's (melody, rhythm) words, one pair per slot, one's complement."""
    chip, now = OPLL(variant), 0
    chip.trace = []
    for cycle, port, value in events:
        chip.run(4 * (cycle - now))
        chip.write(port, value)
        now = cycle
    chip.run(4 * (length - now))
    return [pair for sample in chip.trace for pair in sample]


def encode(word: int) -> int:
    """A core word in the model's encoding (normalisation 3)."""
    return word + 1 if word >= 0 else word


def same(core_word: int, model_word: int) -> bool:
    return encode(core_word) == model_word or (model_word == 0 and core_word == 0)


def zeros_only(core_word: int, model_word: int) -> bool:
    """Both words are a zero or the resting level: the difference is between +0,
    -0 and rest, which the board's integrator does not hear as a tone."""
    return core_word in (0, -1) and model_word in (0, 1, -1)


Report = dict[str, tuple[int, int, int, tuple[int, int] | None]]


def compare(events: Events, length: int, variant, offset: int = OFFSET) -> Report:
    """Per pin: slots compared, slots that differ, slots that differ by more than
    which zero (see ``zeros_only``), and the first of those (sample, slot)."""
    core, model = core_slots(events, length, variant), model_slots(events, length, variant, offset)
    count = min(len(core), len(model))
    report = {}
    for pin, name in ((0, "melody"), (1, "rhythm")):
        compared = differ = sized = 0
        first = None
        for k in range(SETTLE * 18, count):
            compared += 1
            if not same(core[k][pin], model[k][pin]):
                differ += 1
                if not zeros_only(core[k][pin], model[k][pin]):
                    sized += 1
                    if first is None:
                        first = divmod(k, 18)
        report[name] = (compared, differ, sized, first)
    return report


def show(name: str, variant, slot: int, start: int, count: int, offset: int = OFFSET) -> None:
    """Print one slot's words, core then model (in the model's encoding), for
    ``count`` samples from ``start``, with the writes that fall among them."""
    events, length = STREAMS[name]
    core, model = core_slots(events, length, variant), model_slots(events, length, variant, offset)
    for cycle, port, value in events:
        if start * 18 <= cycle < (start + count) * 18:
            print(f"  write at {divmod(cycle, 18)}: port {port} value ${value:02X}")
    for sample in range(start, start + count):
        k = sample * 18 + slot
        print(
            f"  {sample:>7} melody {encode(core[k][0]):>5} {model[k][0]:>5}   rhythm {encode(core[k][1]):>5} {model[k][1]:>5}"
        )


def calibrate() -> None:
    """Check normalisations 1 to 3 on a plain sine for both variants: every slot
    must agree, or the comparison below means nothing."""
    w = Writer()
    for register, value in enumerate((0x21, 0x21, 0x3F, 0, 0, 0xF0, 0, 0)):
        w.reg(register, value)
    w.reg(0x30, 0)
    w.note(0, 0x123, 4)
    w.wait(3000)
    events, length = w.done(100)
    for variant in (YM2413, DS1001):
        report = compare(events, length, variant)
        if report["melody"][1]:
            sys.exit(f"calibration failed for {variant.name}: {report['melody']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("names", nargs="*")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--show", nargs=4, metavar=("VARIANT", "SLOT", "SAMPLE", "COUNT"))
    parser.add_argument(
        "--offset", type=int, default=OFFSET, help="40: phase frame; 4: register frame"
    )
    args = parser.parse_args()
    if args.list:
        print("\n".join(STREAMS))
        return 0
    build()
    calibrate()
    if args.show:
        variant = {"YM2413": YM2413, "DS1001": DS1001}[args.show[0]]
        for name in args.names:
            show(name, variant, *map(int, args.show[1:]), offset=args.offset)
        return 0
    names = args.names or list(STREAMS)
    print(
        f"{'stream':<26}{'variant':<8}{'pin':<8}{'slots':>10}{'differ':>9}{'sized':>9}  first sized (sample, slot)"
    )
    for name in names:
        events, length = STREAMS[name]
        for variant in (YM2413, DS1001):
            for pin, (compared, differ, sized, first) in compare(
                events, length, variant, args.offset
            ).items():
                where = "" if first is None else f"{first}"
                print(
                    f"{name:<26}{variant.name:<8}{pin:<8}{compared:>10}{differ:>9}{sized:>9}  {where}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
