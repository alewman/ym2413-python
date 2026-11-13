"""Shared by the tests: ways to drive the chip as a board would and to read it.

Tests read what ``take_outputs()`` returns, or the chip's own word train through
``trace``, wherever the statement under test is about sound. Where a statement is
about an envelope level, a phase or a counter (most of the measured ones are),
they read the plain attribute that holds it: ``level``, ``phase``, ``counter``.

``reference_value`` is a second, separate writing of spec sections 6.2 to 6.5 from
the two ROM formulas, so that tests about modulation and feedback predict the
chip's numbers instead of repeating its code.
"""

from __future__ import annotations

import itertools
import math
from pathlib import Path

from ym2413_python import CLOCKS_PER_CYCLE, CYCLES_PER_SAMPLE, OPLL, YM2413

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"

SAMPLE = CLOCKS_PER_CYCLE * CYCLES_PER_SAMPLE  # 72 input clocks
CLOCK_HZ = 3_579_545  # the reference clock of S1 section IV-1
SAMPLE_MS = SAMPLE / CLOCK_HZ * 1000

# Slots (spec 2.4).
M = (0, 1, 2, 6, 7, 8, 12, 13, 14)
C = (3, 4, 5, 9, 10, 11, 15, 16, 17)

#: A carrier that plays a plain sine at full level and a modulator that stays
#: silent: its attack rate is 0, so after the damp phase it never leaves the
#: quiet end of its envelope and outputs +0 (spec 6.8, 8.13).
PLAIN_SINE = (0x21, 0x21, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00)


def variant_id(variant) -> str:
    return variant.name


def write(chip: OPLL, register: int, value: int) -> None:
    """One register write with the waits Yamaha asks for (spec 3.3), then rounded
    up to a whole number of samples so that tests can count samples."""
    chip.write(0, register)
    chip.run(12)
    chip.write(1, value)
    chip.run(84 + 48)


def user_tone(chip: OPLL, tone) -> None:
    for register, value in enumerate(tone):
        write(chip, register, value)


def note(chip: OPLL, channel: int, f_number: int, block: int, key=1, sus=0) -> None:
    write(chip, 0x10 + channel, f_number & 0xFF)
    write(chip, 0x20 + channel, sus << 5 | key << 4 | block << 1 | f_number >> 8)


def press(chip: OPLL, channel: int, f_number: int, block: int, sus=0) -> None:
    """Key a channel on without running the chip: the next sample is the first
    in which the key is seen."""
    chip.write(0, 0x20 + channel)
    chip.write(1, sus << 5 | 1 << 4 | block << 1 | f_number >> 8)


def struck(tone, f_number=0x100, block=4, volume=0) -> OPLL:
    """A chip with the user tone on channel 0, keyed on this instant."""
    chip = tone_chip(tone, f_number, block, volume, key=0)
    press(chip, 0, f_number, block)
    return chip


def tone_chip(tone, f_number=0x100, block=4, volume=0, channel=0, variant=YM2413, key=1) -> OPLL:
    """A chip playing the user tone on one channel."""
    chip = OPLL(variant)
    user_tone(chip, tone)
    write(chip, 0x30 + channel, volume)
    note(chip, channel, f_number, block, key=key)
    chip.take_outputs()
    return chip


def samples(chip: OPLL, count: int) -> list[int]:
    chip.run(count * SAMPLE)
    return chip.take_samples()


def melody(chip: OPLL, count: int) -> list[int]:
    chip.run(count * SAMPLE)
    return [pair[0] for pair in chip.take_outputs()]


def rhythm(chip: OPLL, count: int) -> list[int]:
    chip.run(count * SAMPLE)
    return [pair[1] for pair in chip.take_outputs()]


def levels(chip: OPLL, operator: int, count: int) -> list[int]:
    """The operator's envelope level after each of ``count`` samples."""
    out = []
    for _ in range(count):
        chip.run(SAMPLE)
        out.append(chip.level[operator])
    chip.take_outputs()
    return out


def attribute(chip: OPLL, name: str, index: int, count: int) -> list[int]:
    out = []
    for _ in range(count):
        chip.run(SAMPLE)
        out.append(getattr(chip, name)[index])
    chip.take_outputs()
    return out


def words(chip: OPLL, count: int) -> list[list[tuple[int, int]]]:
    """The eighteen (melody word, rhythm word) pairs of each of ``count`` samples.

    Call it on a sample boundary. Words are in the chip's form: -1 is minus zero.
    """
    chip.trace = []
    chip.run(count * SAMPLE)
    trace, chip.trace = chip.trace, None
    chip.take_outputs()
    return trace


def runs(values) -> list[tuple[int, int]]:
    """(value, length) for each run of equal values."""
    out: list[list[int]] = []
    for value in values:
        if out and out[-1][0] == value:
            out[-1][1] += 1
        else:
            out.append([value, 1])
    return [(value, length) for value, length in out]


def rises(values) -> int:
    """Upward crossings of zero."""
    return sum(1 for a, b in itertools.pairwise(values) if a <= 0 < b)


# A second writing of the operator's arithmetic, from the formulas of spec 6.3 to
# 6.5 (S11's, as S4's prose restates them).
_LOG_SIN = [round(-math.log2(math.sin((i + 0.5) * math.pi / 512)) * 256) for i in range(256)]
_EXP = [round((2 ** (i / 256) - 1) * 1024) for i in range(256)]


def reference_value(phase: int, attenuation: int, half_sine: bool = False) -> int:
    """Spec 6.2 to 6.9: the operator's eleven-bit value in one's complement, for a
    phase in 1/1024 periods and a total attenuation in envelope steps."""
    phase &= 0x3FF
    index = phase & 0xFF
    if phase & 0x100:
        index = 255 - index
    x = _LOG_SIN[index] + 16 * min(127, attenuation)
    value = (_EXP[255 - (x & 0xFF)] + 1024) >> (x >> 8)
    if phase & 0x200:
        return -1 - (0 if half_sine else value)
    return value


def carrier_peak(attenuation: int) -> int:
    """The largest carrier word at a total attenuation (spec 6.10)."""
    return max(reference_value(phase, attenuation) for phase in range(256)) >> 3
