"""The conformance kit: manifests of writes, and traces of what the chip drives.

A port of this core proves itself by running each manifest in ``examples/conformance``
and writing the trace below, then comparing it with the one committed beside the
manifest (docs/conformance.md). The committed traces were made by this core and
checked against Nuked-OPLL when they were made (scripts/make_examples.py).

    ym2413-conformance run MANIFEST.json            # the trace, to stdout
    ym2413-conformance check examples/conformance   # every example, against its trace

Trace format, version 1, one line per sample (18 internal cycles):

    # ym2413-trace 1
    # NAME VARIANT
    S <sample> <crc32> <sum of MO> <sum of RO>
    # end <clocks> clocks <samples> samples <writes> writes

``crc32`` is CRC-32 (zlib's) of the sample's 36 words, (MO, RO) per cycle in order, each
a little-endian signed 16-bit value; the sums are the pins' words added up.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from pathlib import Path

from .chip import CYCLES_PER_SAMPLE, OPLL
from .variants import VARIANTS

FORMAT = "# ym2413-trace 1"


def run(manifest: dict) -> str:
    """The trace of one manifest."""
    if manifest.get("version") != 1:
        raise ValueError("manifest version must be 1")
    variant = VARIANTS[manifest["variant"]]
    chip = OPLL(variant)
    lines = [FORMAT, f"# {manifest['name']} {variant.name}"]
    events = manifest["events"]
    words: list[tuple[int, int]] = []
    sample = 0

    def drain() -> None:
        nonlocal sample
        words.extend(chip.take_outputs())
        while len(words) >= CYCLES_PER_SAMPLE:
            block, words[:] = words[:CYCLES_PER_SAMPLE], words[CYCLES_PER_SAMPLE:]
            raw = b"".join(struct.pack("<hh", mo, ro) for mo, ro in block)
            mo_sum = sum(mo for mo, _ in block)
            ro_sum = sum(ro for _, ro in block)
            lines.append(f"S {sample} {zlib.crc32(raw):08x} {mo_sum} {ro_sum}")
            sample += 1

    for event in events:
        chip.run(event["t"] - chip.clock)
        drain()
        port = {"address": 0, "data": 1}[event["kind"]]
        chip.write(port, event["data"])
    chip.run(manifest["clocks"] - chip.clock)
    drain()
    lines.append(f"# end {chip.clock} clocks {sample} samples {len(events)} writes")
    return "\n".join(lines) + "\n"


def check(directory: Path) -> list[str]:
    """Every manifest in ``directory`` whose trace differs from the committed one."""
    failures = []
    for manifest_path in sorted(directory.glob("*.json")):
        expected = manifest_path.with_suffix(".trace").read_text()
        if run(json.loads(manifest_path.read_text())) != expected:
            failures.append(manifest_path.stem)
    return failures


def main(argv: list[str] | None = None) -> int:
    summary = __doc__.split("\n\n")[0]
    parser = argparse.ArgumentParser(prog="ym2413-conformance", description=summary)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("run", help="write a manifest's trace to stdout")
    one.add_argument("manifest", type=Path)
    every = sub.add_parser("check", help="check every example in a directory")
    every.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    if args.command == "run":
        sys.stdout.write(run(json.loads(args.manifest.read_text())))
        return 0
    failures = check(args.directory)
    for name in failures:
        print(f"differs: {name}")
    print(f"{len(failures)} differ")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
