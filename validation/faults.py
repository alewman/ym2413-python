#!/usr/bin/env python3
"""Can each rung fail? Break the core on purpose and see which tests notice.

docs/validation.md: every rung's exit asks that the listed faults be caught. Each
fault below is one textual change to a copy of the package (under the git-ignored
validation/build/faults/); the test suite is run against the copy and the test
files with failures are listed. The unbroken copy is run first and must pass.

    python validation/faults.py

Exit status 1 if the unbroken copy fails or any fault goes unnoticed by every rung.
The faults are chosen from the spec's measured and documented statements, plus a
few provisional defaults (which only the provisional record should notice).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "ym2413_python"
WORK = ROOT / "validation" / "build" / "faults"

RUNGS = {
    "test_contract.py": "rung 0",
    "test_manual.py": "rung 1",
    "test_measured.py": "rung 2a",
    "test_community.py": "rung 3",
    "test_provisional.py": "provisional",
}

# (what is broken, file, text to find, replacement, every occurrence?)
FAULTS: tuple[tuple[str, str, str, str, bool], ...] = (
    ("log-sine ROM: no half-step offset (6.3)", "tables.py", "(i + 0.5) * math.pi / 512", "(i + 1) * math.pi / 512", False),
    ("exponential ROM one step off (6.4)", "tables.py", "2 ** (i / 256) - 1", "2 ** ((i + 1) / 256) - 1", False),
    ("MULTI 11 is 11, not 10 (7.4)", "tables.py", "18, 20, 20, 24", "18, 20, 22, 24", False),
    ("decay pattern for rate & 3 = 1 rotated (8.5)", "tables.py", "(0, 1, 0, 1, 1, 1, 0, 1)", "(1, 0, 1, 1, 1, 0, 1, 0)", False),
    ("tremolo top held 4 x 64 samples (10.2)", "tables.py", "if step < 114:", "if step < 115:", False),
    ("vibrato period 7,768 as S1 says (C2)", "tables.py", "VIBRATO_PERIOD = 8_192", "VIBRATO_PERIOD = 7_768", False),
    ("mute at 120, not 124 (6.8)", "opll.py", "QUIET = 124", "QUIET = 120", False),
    ("rate shift 12 - rate/4 (8.5)", "opll.py", "s = 13 - (rate >> 2)", "s = 12 - (rate >> 2)", True),
    ("attack formula x - x/8 - 1 (8.10)", "opll.py", "level - (level >> 4) - 1", "level - (level >> 3) - 1", False),
    ("noise taps x^23 + x^10 + 1 (11.7)", "opll.py", "noise ^ (noise >> 14)", "noise ^ (noise >> 13)", False),
    ("no register aliases (4.3)", "opll.py", "            address -= 9\n            low -= 9\n", "            return\n", False),
    ("modulator TL 1.5 dB a step (6.7)", "opll.py", "self.base[modulator] = 2 * (row[2] & 0x3F)", "self.base[modulator] = 4 * (row[2] & 0x3F)", False),
    ("volume 1.5 dB a step (6.7)", "opll.py", "self.base[carrier] = 8 * volume", "self.base[carrier] = 4 * volume", False),
    ("SUS release at rate 7 (8.22)", "opll.py", "rate = variant.sustained_release_rate  # the SUS bit: rate 5", "rate = variant.percussive_release_rate", False),
    ("decay ends at or beyond SL (8.19)", "opll.py", "if level >> 3 == self.sustain_level[operator]:", "if level >> 3 >= self.sustain_level[operator]:", False),
    ("phase counter 18 bits (7.2)", "opll.py", "& 0x7FFFF", "& 0x3FFFF", False),
    ("phase step not halved (7.3)", "opll.py", "step = ((f_number * multiplier) << block) >> 1", "step = (f_number * multiplier) << block", False),
    ("half sine keeps its size (6.9)", "opll.py", "                value = 0  # spec 6.9 (measured): size zero, the sign still set\n", "", False),
    ("modulation not doubled (6.11)", "opll.py", "phase += 2 * self.before_previous[channel]", "phase += self.before_previous[channel]", False),
    ("carrier word shifted by 4 (6.10)", "opll.py", "return self._operate(operator, channel, phase & 0x3FF) >> 3\n\n    def _cymbal_bit", "return self._operate(operator, channel, phase & 0x3FF) >> 4\n\n    def _cymbal_bit", False),
    ("feedback one step weaker (6.12)", "opll.py", "(8 - feedback)", "(9 - feedback)", False),
    ("total attenuation not clipped (6.7)", "opll.py", "attenuation = min(attenuation, BOTTOM)", "pass", False),
    ("percussion not repeated (11.12)", "opll.py", "rhythm_word = self.held[COPY_SLOT[slot]]", "rhythm_word = 0", False),
    ("test bit 0 ignored (13.2)", "opll.py", "if self.test & 0x01:", "if self.test & 0x100:", False),
    ("damp at rate 11 (8.16)", "variants.py", "damp_rate: int = 12", "damp_rate: int = 11", False),
    ("percussive release at rate 6 (8.22)", "variants.py", "percussive_release_rate: int = 7", "percussive_release_rate: int = 6", False),
    ("DS1001 with nine channels (S6)", "variants.py", "    channels=6,\n", "", False),
    ("VRC7 reset clears the vibrato (S6)", "variants.py", "    reset_clears_vibrato=False,\n", "", False),
    ("hi-hat phases swapped (provisional, U22)", "variants.py", "(0x2D0, 0x234, 0x034, 0x0D0)", "(0x234, 0x2D0, 0x0D0, 0x034)", False),
    ("instant attack decided later (8.13)", "opll.py", "                if rate >= 60:\n", "                if rate >= 64:\n", False),
)  # fmt: skip


def run_tests(package_parent: Path, check_import: bool = False) -> tuple[bool, set[str]]:
    """Run the suite against the package under ``package_parent``.

    PYTHONPATH comes before the editable install on the path, so the copy is what
    the tests import; ``check_import`` proves it once.
    """
    environment = dict(os.environ, PYTHONPATH=str(package_parent), PYTHONDONTWRITEBYTECODE="1")
    if check_import:
        check = subprocess.run(
            [sys.executable, "-c", "import ym2413_python; print(ym2413_python.__file__)"],
            env=environment, capture_output=True, text=True, check=True,
        )  # fmt: skip
        if str(package_parent) not in check.stdout:
            sys.exit(f"the copy at {package_parent} is not the package under test")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
         "-o", "pythonpath=tests", "-rfE", "--tb=no"],
        cwd=ROOT, env=environment, capture_output=True, text=True, check=False,
    )  # fmt: skip
    failed = set(re.findall(r"^(?:FAILED|ERROR) tests/(test_\w+\.py)", result.stdout, re.MULTILINE))
    return result.returncode == 0, failed


def make_copy(
    index: int, file: str = "", find: str = "", replacement: str = "", every=False
) -> Path:
    parent = WORK / f"{index:02d}"
    target = parent / "ym2413_python"
    target.mkdir(parents=True, exist_ok=True)
    for source in PACKAGE.glob("*.py"):
        text = source.read_text()
        if source.name == file:
            count = text.count(find)
            if count == 0 or (count > 1 and not every):
                sys.exit(f"fault {index}: {find!r} occurs {count} times in {file}")
            text = text.replace(find, replacement)
        (target / source.name).write_text(text)
    return parent


def main() -> int:
    passed, failed = run_tests(make_copy(0), check_import=True)
    if not passed:
        print(f"the unbroken copy fails: {sorted(failed)}")
        return 1
    print("unbroken copy: all tests pass\n")
    copies = [make_copy(index, *fault[1:]) for index, fault in enumerate(FAULTS, start=1)]
    workers = max(1, min(4, (os.cpu_count() or 2) // 2))
    with ThreadPoolExecutor(workers) as pool:
        results = list(pool.map(run_tests, copies))
    caught = dict.fromkeys(RUNGS, 0)
    unnoticed = []
    for index, ((what, *_), (passed, failed)) in enumerate(
        zip(FAULTS, results, strict=True), start=1
    ):
        if not passed and not failed:
            failed = set(RUNGS)  # the suite could not even be collected
        for name in failed:
            caught[name] += 1
        seen_by = ", ".join(RUNGS[name] for name in RUNGS if name in failed) or "NOBODY"
        if not failed:
            unnoticed.append(what)
        print(f"{index:2d}. {what}: {seen_by}")
    print()
    for name, rung in RUNGS.items():
        print(f"{rung} ({name}): notices {caught[name]} of {len(FAULTS)} faults")
    print(f"unnoticed by every rung: {len(unnoticed)} {unnoticed if unnoticed else ''}")
    return 1 if unnoticed else 0


if __name__ == "__main__":
    sys.exit(main())
