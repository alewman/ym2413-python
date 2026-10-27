#!/usr/bin/env python
"""Seed faults into the chip, one at a time, and check the referee catches each.

    python scripts/mutation.py [--jobs N] [--examples-only]

A gate that cannot fail proves nothing. Each mutant changes one place in
``src/ym2413_python/chip.py`` -- a rule the chip is known to have, broken the way a
port might break it -- and the gate is the referee's synthetic streams
(``scripts/streams.py`` through ``scripts/referee.py``, the YM2413, the DS1001 and
the YM2413B), stopping at the first stream that differs. A mutant the gate misses
is listed, and needs a stream.
"""

from __future__ import annotations

import argparse
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHIP = ROOT / "src" / "ym2413_python" / "chip.py"

#: (what is broken, the exact text, its replacement)
MUTANTS = [
    ("carrier select a cycle late", "    return ((cycle + 1) // 3) & 1", "    return (cycle // 3) & 1"),
    ("rhythm sequencer never stops", "self.rhythm_slot = min(self.rhythm_slot + 1, NONE)", "self.rhythm_slot = (self.rhythm_slot + 1) % 7"),
    ("strobe counted while held", "self._address_edge = (self._strobe_address & 3) == 1", "self._address_edge = bool(self._strobe_address & 1)"),
    ("channel registers written on any cycle", "(self.address & 0x0F) == cycle < 16", "(self.address & 0x0F) == cycle % 9"),
    ("hi-hat volume from the volume register", "self.r_tl = self.instrument[channel] << 2", "self.r_tl = self.volume[channel] << 2"),
    ("hi-hat noise offsets swapped", "out = ring << 9 | (0xD0 if ring ^ (self.noise & 1) else 0x34)", "out = ring << 9 | (0x34 if ring ^ (self.noise & 1) else 0xD0)"),
    ("deep vibrato too shallow", "freq += freq >> 7", "freq += freq >> 8"),
    ("KSL shifts wrong", "ksl = ksl >> (3 - self.r_ksl) if self.r_ksl else 0", "ksl = ksl >> (2 - self.r_ksl // 2) if self.r_ksl else 0"),
    ("timer shift lock kept past 13", "self.eg_timer_shift if self.eg_timer_shift <= 13 else 0", "self.eg_timer_shift"),
    ("attack steps one bit less", "step = (~level) >> (5 - shift)", "step = (~level) >> (6 - shift)"),
    ("sustain release rate 6", "            rate = 5\n", "            rate = 6\n"),
    ("key-on damp rate 11", "            rate = 12\n", "            rate = 11\n"),
    ("percussive release rate 6", "            rate = 7\n", "            rate = 6\n"),
    ("rate not clamped at 15", "        if self.eg_rate & 0x40:", "        if False:"),
    ("attenuation not clamped", "level = min(self.op_log + (self.eg_out << 4), 4095)", "level = (self.op_log + (self.eg_out << 4)) & 0xFFF"),
    ("feedback from one sample", "self.fb_sum = (self.fb_last[index] + self.fb_before[index]) >> 1", "self.fb_sum = self.fb_last[index]"),
    ("DAC word not offset", "            sign += 1\n", "            pass\n"),
    ("tremolo counts down only", "increment = self.lfo_am_dir | (cycle == 0)", "increment = cycle == 0"),
    ("tremolo turns at another count", "(self.lfo_am_counter & 0x69) == 0x69", "(self.lfo_am_counter & 0x6B) == 0x6B"),
    ("noise taps 0 and 13", "bit = (noise ^ (noise >> 14)) & 1", "bit = (noise ^ (noise >> 13)) & 1"),
    ("second half of the sine not mirrored", "            phase ^= 0xFF", "            phase ^= 0x00"),
    ("multiple 15 is 28", "MULTIPLE = (1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 20, 24, 24, 30, 30)", "MULTIPLE = (1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 20, 24, 24, 30, 28)"),
    ("KSL table off by one", "KSL_TABLE = (0, 32, 40, 45,", "KSL_TABLE = (0, 32, 40, 44,"),
    ("fast-rate steps changed", "STEP_HIGH = ((0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 1, 0), (1, 1, 1, 0))", "STEP_HIGH = ((0, 0, 0, 0), (1, 0, 0, 0), (1, 1, 0, 0), (1, 1, 1, 0))"),
    ("channel 0 and 2 slots swapped", "CHANNEL_OF_CYCLE = (1, 2, 0,", "CHANNEL_OF_CYCLE = (1, 0, 2,"),
    ("test bit 0 ignored", "        if self.test & 0x01:\n            level = 0", "        if False:\n            level = 0"),
    ("no phase reset on key-on", "        if self.test & 0x04 or starting:\n            self.pg_phase_next = 0", "        if self.test & 0x04:\n            self.pg_phase_next = 0"),
    # The rhythm enable reaches the phase and operator stages a cycle late (rhythm_on bit
    # 6). Using bit 7 there instead is an equivalent mutant: no output shows it (15 and 20
    # seeds of rhythm_key_races, mutant against core, both pins: equal). Its cycles are
    # tested instead:
    ("rhythm cuts the carrier's modulation on other cycles", "mod_in = 0 if rhythm_late and cycle in (16, 17)", "mod_in = 0 if rhythm_late and cycle in (15, 16)"),
    ("B parts drive the sign", "        if stage == \"b\":", "        if False:"),
    ("custom instrument byte 3 bit 4 is DM", "            dc=(raw[3] >> 4) & 1,\n            dm=(raw[3] >> 3) & 1,", "            dc=(raw[3] >> 3) & 1,\n            dm=(raw[3] >> 4) & 1,"),
]  # fmt: skip

GATE_VARIANTS = ("YM2413", "DS1001", "YM2413B")


EXAMPLES_ONLY = "--examples-only" in sys.argv[1:]


def gate(src: Path) -> bool:
    """True when the gate passes (the mutant survives): the referee's streams, or with
    ``--examples-only`` the conformance examples alone (what a port's gate catches)."""
    env = dict(os.environ, PYTHONPATH=f"{src}{os.pathsep}{ROOT / 'scripts'}")
    if EXAMPLES_ONLY:
        command = [sys.executable, "-m", "ym2413_python.conformance", "check",
                   str(ROOT / "examples" / "conformance")]  # fmt: skip
    else:
        variants = [arg for name in GATE_VARIANTS for arg in ("--variant", name)]
        command = [sys.executable, str(ROOT / "scripts" / "referee.py"), "--first", *variants]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    return result.returncode == 0


def run_mutant(mutant: tuple[str, str, str]) -> tuple[str, bool]:
    name, old, new = mutant
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "src"
        shutil.copytree(ROOT / "src", src)
        target = (
            src / "ym2413_python" / "variants.py"
            if "raw[3]" in old
            else (src / "ym2413_python" / "chip.py")
        )
        text = target.read_text()
        if text.count(old) != 1:
            return name, True  # reported as a broken mutant below
        target.write_text(text.replace(old, new))
        return name, gate(src)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--examples-only", action="store_true", help="gate on the examples alone")
    args = parser.parse_args()
    for name, old, _ in MUTANTS:
        target = ROOT / "src" / "ym2413_python" / ("variants.py" if "raw[3]" in old else "chip.py")
        if target.read_text().count(old) != 1:
            print(f"mutant {name!r}: its text is not in {target.name} exactly once")
            return 2
    with multiprocessing.Pool(args.jobs) as pool:
        results = pool.map(run_mutant, MUTANTS)
    survivors = [name for name, survived in results if survived]
    for name, survived in results:
        print(f"{'SURVIVED' if survived else 'caught  '}  {name}")
    print(f"{len(results) - len(survivors)} of {len(results)} caught")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
