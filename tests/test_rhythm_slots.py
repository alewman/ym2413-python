"""The DAC's eighteen slots, against andete's measurement of a real YM2413.

andete (openMSX, results/rhythm/rhythm.md in the andete-ym2413 repository) measured
which slot of the 18 carries each sound in rhythm mode: every drum twice, the second
copy always equal to the first, the melodic channels between. The table below is that
measurement; his slot 0 is this core's output cycle 4.
"""

from __future__ import annotations

from ym2413_python import CYCLES_PER_SAMPLE, OPLL, YM2413

#: andete's slots, in his numbering: (sound, slot).
MEASURED = {
    "HH": (13, 0),
    "TOM": (14, 1),
    "BD": (15, 2),
    "SD": (16, 6),
    "TCY": (17, 7),
    "ch0": (3,),
    "ch1": (4,),
    "ch2": (5,),
    "ch3": (9,),
    "ch4": (10,),
    "ch5": (11,),
}
#: andete's slot 0 is this core's output cycle 4.
OFFSET = 4

KEYS = {"BD": 0x10, "SD": 0x08, "TOM": 0x04, "TCY": 0x02, "HH": 0x01}


def write(chip: OPLL, register: int, value: int) -> None:
    chip.write(0, register)
    chip.run(12)
    chip.write(1, value)
    chip.run(84)


def sounding(writes: list[tuple[int, int]]) -> tuple[set[int], list[tuple[int, int]]]:
    """The output cycles where either pin leaves silence, and the words."""
    chip = OPLL(YM2413)
    for register, value in writes:
        write(chip, register, value)
    chip.take_outputs()
    chip.run(72 * 10 - chip.clock % 72)  # to a sample boundary, past the attack's start
    chip.take_outputs()
    chip.run(72 * 300)
    words = chip.take_outputs()
    cycles = {i % CYCLES_PER_SAMPLE for i, (mo, ro) in enumerate(words) if {mo, ro} - {-1, 0, 1}}
    return cycles, words


RHYTHM_FREQUENCIES = [
    (0x16, 0x20),
    (0x26, 0x05),
    (0x17, 0x50),
    (0x27, 0x05),
    (0x18, 0xC0),
    (0x28, 0x01),
]


def test_each_drum_is_output_twice_where_andete_measured() -> None:
    for drum, key in KEYS.items():
        cycles, words = sounding([*RHYTHM_FREQUENCIES, (0x0E, 0x20), (0x0E, 0x20 | key)])
        expected = {(slot + OFFSET) % CYCLES_PER_SAMPLE for slot in MEASURED[drum]}
        assert cycles == expected, drum
        # The copy is the first output again, held in the delay line (it can fall in
        # the next sample: HH's first is cycle 17, its copy cycle 4).
        first, copy = MEASURED[drum]
        start = (first + OFFSET) % CYCLES_PER_SAMPLE
        later = (copy - first) % CYCLES_PER_SAMPLE
        ro = [r for _, r in words]
        for i in range(start, len(ro) - later, CYCLES_PER_SAMPLE):
            assert ro[i] == ro[i + later], drum


def test_melodic_channels_sit_between_the_drums() -> None:
    for ch in range(6):
        cycles, _ = sounding(
            [(0x0E, 0x20), (0x30 + ch, 0x10), (0x10 + ch, 0x81), (0x20 + ch, 0x18)]
        )
        assert cycles == {(MEASURED[f"ch{ch}"][0] + OFFSET) % CYCLES_PER_SAMPLE}, ch
