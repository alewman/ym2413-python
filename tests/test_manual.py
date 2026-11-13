"""Rung 1: Yamaha's application manual (S1), by section, table and printed page.

Every check is a sentence or a table row of "FM Operator Type-LL (OPLL)
Application Manual". "documented" throughout; where S1 and the measurements of
rung 2 disagree, the test says which was taken and why (contradictions C1, C2,
C6). Tables III-1, III-2, III-5, III-6, III-7, III-8-2 and III-9 were read from
the page images and typed here.
"""

from __future__ import annotations

import math

import pytest
from helpers import (
    CLOCK_HZ,
    PLAIN_SINE,
    SAMPLE,
    SAMPLE_MS,
    C,
    M,
    attribute,
    levels,
    melody,
    note,
    rises,
    struck,
    tone_chip,
    user_tone,
    words,
    write,
)

from ym2413_python import OPLL, YM2413

# ---------------------------------------------------------------- the bus


def test_an_address_write_then_a_data_write_stores_the_byte():
    # S1 Table II-1 (page 4): A0 = 0 address write mode, A0 = 1 data write mode.
    chip = OPLL(YM2413)
    chip.write(0, 0x30)
    chip.write(1, 0x5A)
    assert chip.registers[0x30] == 0x5A


def test_the_address_stays_latched():
    # S1 III-1 (page 8): "we only have to send the sub-address the first time".
    chip = OPLL(YM2413)
    chip.write(0, 0x10)
    chip.write(1, 0x11)
    chip.write(1, 0x22)
    assert chip.registers[0x10] == 0x22


def test_initial_clear_zeroes_every_register():
    # S1 III-1 (page 8): "All registers are cleared to 0 by initialization".
    chip = tone_chip((0x21, 0x21, 0x10, 0x07, 0xF0, 0xF0, 0x00, 0x0F))
    write(chip, 0x0E, 0x3F)
    chip.reset()
    chip.take_outputs()  # what was played before the reset
    assert chip.registers == bytearray(0x40)
    assert set(melody(chip, 500)) == {0}


def test_72_clocks_make_a_sample():
    # S1 III-1-6 (page 14): fsam = fM / 72; with section IV-1's 3.579545 MHz that
    # is 49,716 Hz. S1 rounds to "50 kHz" (C6).
    chip = OPLL(YM2413)
    chip.run(CLOCK_HZ)
    assert len(chip.take_samples()) == CLOCK_HZ // 72 == 49_715


# ------------------------------------------------------- frequency and MULTI

MULTIPLIER = (0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 12, 12, 15, 15)  # S1 Table III-1 (page 9)


@pytest.mark.parametrize("multi", range(16))
def test_table_iii_1_multiplying_factors(multi):
    # F-number 128, block 2: with multiplier 1 one period is 1,024 samples, so in
    # 2,048 samples there are twice the multiplier's worth of cycles.
    tone = list(PLAIN_SINE)
    tone[1] = 0x20 | multi
    chip = tone_chip(tone, f_number=128, block=2)
    assert rises(melody(chip, 2048)) == round(2 * MULTIPLIER[multi])


# S1 Table III-8-2 (page 16): note, frequency in Hz, F-number, for octave 4.
F_NUMBERS = (
    ("G", 392.2, 257), ("G#", 415.3, 272), ("A", 440.0, 288), ("A#", 466.2, 305),
    ("B", 493.9, 323), ("C", 523.3, 343), ("C#", 554.4, 363), ("D", 587.3, 385),
    ("D#", 622.2, 408), ("E", 659.3, 432), ("F", 698.5, 458), ("F#", 740.0, 485),
)  # fmt: skip


@pytest.mark.parametrize("name, hertz, f_number", F_NUMBERS)
def test_table_iii_8_2_f_numbers(name, hertz, f_number):
    # S1 III-1-6 (pages 14, 15): F-number = fmus x 2^18 / fsam / 2^(block - 1).
    # The table is computed for fsam = 50 kHz, not the real 49,716 Hz (C6): at
    # 50 kHz the chip's phase step for the printed F-number is the printed note.
    chip = tone_chip(PLAIN_SINE, f_number=f_number, block=4)
    before = chip.phase[C[0]]
    chip.run(SAMPLE)
    step = (chip.phase[C[0]] - before) % (1 << 19)
    # Within one F-number step (1.53 Hz): the table drops fractions (B is 323.7).
    assert abs(50_000 * step / (1 << 19) - hertz) < 1.53


def test_the_frequency_formula_at_the_real_sample_rate():
    # Spec 7.5: fsam x F-number x 2^block x multiplier / 2^19. F-number 256,
    # block 4, multiplier 1: 1/128 of the sample rate, 388.4 Hz.
    chip = tone_chip(PLAIN_SINE, f_number=256, block=4)
    assert rises(melody(chip, 128 * 100)) == 100


# -------------------------------------------------------------- key scaling

# S1 Table III-2 (page 9): Rks by BLOCK and F-number MSB, for KSR 0 and KSR 1.
RKS = {
    0: (0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3),
    1: (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
}


@pytest.mark.parametrize("ksr", (0, 1))
@pytest.mark.parametrize("cell", range(16))
def test_table_iii_2_key_scale_of_rate(ksr, cell):
    # S1 III-1-2 (page 9): "RATE = 4 x R + Rks". A decay at DR 9 runs at rate
    # 36 + Rks, and each rate has its own count of steps in 4,096 samples.
    block, msb = cell >> 1, cell & 1
    tone = (0x00, 0x20 | ksr << 4 | 0x01, 0x3F, 0x00, 0x00, 0xF9, 0x00, 0xF0)
    chip = struck(tone, f_number=msb << 8 | 0x40, block=block)
    chip.run(SAMPLE)  # damp ends and the instant attack puts the level at 0
    assert chip.level[C[0]] == 0
    chip.counter = 0
    rate = 36 + RKS[ksr][cell]
    # Eight opportunities (spec 8.5) are 2^(16 - rate // 4) samples, in which a
    # rate steps 4, 5, 6 or 7 times by its low two bits: each rate from 36 to 51
    # has its own pair of numbers.
    window = 1 << (16 - (rate >> 2))
    trace = levels(chip, C[0], 2 * window)
    assert (trace[window - 1], trace[-1]) == (4 + (rate & 3), 2 * (4 + (rate & 3))), rate
    assert levels(chip, C[0], window // 2)[-1] < 3 * (4 + (rate & 3))


def test_rate_is_zero_when_r_is_zero():
    # S1 III-1-2 (page 9): "Note that when R = 0, RATE = 0", whatever Rks is.
    tone = (0x00, 0x31, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0xF0)
    chip = tone_chip(tone, f_number=0x1FF, block=7)
    assert set(levels(chip, C[0], 3000)[10:]) == {0}


# S1 Table III-5 (page 11), bottom row: dB at 3 dB/oct in octave 7.
KSL_ROW = (0.0, 9.0, 12.0, 13.875, 15.0, 16.125, 16.875, 17.625,
           18.0, 18.75, 19.125, 19.5, 19.875, 20.25, 20.625, 21.0)  # fmt: skip


def modulator_peak(ksl: int, total_level: int, f_top: int, block: int) -> int:
    """The largest output of a modulator at full envelope level."""
    f_number = f_top << 5 | 0x08
    # A multiplier that moves the phase a few table steps a sample, so that a
    # period is short and still passes close to the sine's top.
    def per_sample(m: int) -> float:
        return ((f_number * round(2 * MULTIPLIER[m])) << block) / 1024

    multi = min(range(16), key=lambda m: abs(per_sample(m) - 3))
    tone = (0x20 | multi, 0x21, ksl << 6 | total_level, 0x00, 0xF0, 0xF0, 0x00, 0x00)
    chip = tone_chip(tone, f_number=f_number, block=block)
    span = int(1024 / per_sample(multi)) + 16
    return max(abs(value) for value in attribute(chip, "previous", 0, span)[8:])


def decibels(peak: int) -> float:
    return 20 * math.log10(2042 / peak)


@pytest.mark.parametrize("block", range(8))
def test_table_iii_5_attenuation_at_3_db_per_octave(block):
    # All sixteen cells of one row. The printed row for octave 7, less 3 dB per
    # octave below it, floored at 0 (the table's other rows show exactly that).
    # Code 2 is the 3 dB setting: measured (S4), see test_measured (C3).
    for f_top in range(16):
        printed = max(0.0, KSL_ROW[f_top] - 3 * (7 - block))
        got = decibels(modulator_peak(2, 0, f_top, block))
        assert abs(got - printed) < 0.2, (block, f_top, got, printed)


@pytest.mark.parametrize("code, factor", ((1, 0.5), (3, 2.0)))
def test_table_iii_5_notes_half_and_double(code, factor):
    # S1 page 11: "Half of the above data at 1.5 dB/oct", "Double ... at 6 dB/oct".
    # To the nearest envelope step (0.375 dB) below.
    for block in (2, 5, 7):
        for f_top in range(16):
            printed = factor * max(0.0, KSL_ROW[f_top] - 3 * (7 - block))
            got = decibels(modulator_peak(code, 0, f_top, block))
            assert -0.5 < got - printed < 0.2, (block, f_top, got, printed)


@pytest.mark.parametrize("bit, db", list(enumerate((0.75, 1.5, 3.0, 6.0, 12.0, 24.0))))
def test_table_iii_3_total_level(bit, db):
    # S1 Table III-3 (page 11): the six bits weigh 0.75 to 24 dB.
    assert abs(decibels(modulator_peak(0, 1 << bit, 8, 4)) - db) < 0.1


@pytest.mark.parametrize("bit, db", list(enumerate((3.0, 6.0, 12.0, 24.0))))
def test_volume_weights(bit, db):
    # S1 III-1-8 (page 17): "The minimum resolution is 3 dB". Within the rounding
    # of a nine-bit word.
    chip = tone_chip(PLAIN_SINE, volume=1 << bit)
    peak = max(melody(chip, 600))
    assert abs(20 * math.log10(255 / peak) - db) < 0.65


@pytest.mark.parametrize("bit, db", list(enumerate((3.0, 6.0, 12.0, 24.0))))
def test_sustain_level_weights(bit, db):
    # S1 III-1-5 (page 12): SL's four bits weigh 3, 6, 12 and 24 dB.
    tone = (0x21, 0x21, 0x3F, 0x00, 0x00, 0xFF, 0x00, (1 << bit) << 4)
    chip = tone_chip(tone)
    chip.run(SAMPLE * 400)
    chip.take_outputs()
    peak = max(melody(chip, 600))
    assert abs(20 * math.log10(255 / peak) - db) < 0.65


# ---------------------------------------------------------------- feedback


@pytest.mark.parametrize("fb", range(8))
def test_table_iii_6_modulation_index(fb):
    # S1 Table III-6 (page 12): 0, pi/16, pi/8, pi/4, pi/2, pi, 2 pi, 4 pi. The
    # index is the largest phase swing the fed-back signal gives: a full-scale
    # modulator (two outputs of 2,042 summed) against a period of 1,024 steps.
    printed = 0.0 if fb == 0 else math.pi / 16 * 2 ** (fb - 1)
    tone = (0x21, 0x21, 0x00, fb, 0xF0, 0xF0, 0x00, 0x00)
    chip = tone_chip(tone, f_number=0x100, block=2)
    still = tone_chip((0x21, 0x21, 0x00, 0, 0xF0, 0xF0, 0x00, 0x00), f_number=0x100, block=2)
    assert (attribute(chip, "previous", 0, 600) == attribute(still, "previous", 0, 600)) == (fb == 0)
    if fb:
        swing = (2 * 2042) / 2 ** (8 - fb)  # the most the chip adds, in 1/1024 periods
        assert abs(swing * 2 * math.pi / 1024 - printed) / printed < 0.01
        # ...and the chip does add it: the first sample where the two differ is
        # the first where the shifted sum of the previous two outputs is not 0.
        chip = tone_chip(tone, f_number=0x100, block=2, key=0)
        still = tone_chip((0x21, 0x21, 0x00, 0, 0xF0, 0xF0, 0, 0), f_number=0x100, block=2, key=0)
        for each in (chip, still):
            note(each, 0, 0x100, 2)
        a, b = attribute(chip, "previous", 0, 400), attribute(still, "previous", 0, 400)
        first = next(i for i in range(400) if a[i] != b[i])
        assert (b[first - 1] + b[first - 2]) >> (8 - fb) != 0
        assert all((b[i - 1] + b[i - 2]) >> (8 - fb) == 0 for i in range(2, first))


# ------------------------------------------------------- Table III-7: decay

# S1 Table III-7 (page 13), left half: effective rate -> ms from 0 dB to 48 dB.
DECAY_MS = {
    63: 1.27, 62: 1.27, 61: 1.27, 60: 1.27, 59: 1.47, 58: 1.71, 57: 2.05, 56: 2.55,
    55: 2.94, 54: 3.42, 53: 4.10, 52: 5.11, 51: 5.87, 50: 6.84, 49: 8.21, 48: 10.22,
    47: 11.75, 46: 13.68, 45: 16.41, 44: 20.44, 43: 23.49, 42: 27.36, 41: 32.83,
    40: 40.87, 39: 46.99, 38: 54.71, 37: 65.65, 36: 81.74, 35: 93.97, 34: 109.42,
    33: 131.31, 32: 163.49, 31: 187.95, 30: 218.84, 29: 262.61, 28: 326.98,
    27: 375.90, 26: 437.69, 25: 525.22, 24: 653.95, 23: 751.79, 22: 875.37,
    21: 1050.45, 20: 1307.91, 19: 1503.58, 18: 1750.75, 17: 2100.89, 16: 2615.82,
    15: 3007.16, 14: 3501.49, 13: 4201.79, 12: 5231.64, 11: 6014.32, 10: 7002.98,
    9: 8403.58, 8: 10463.30, 7: 12028.66, 6: 14006.00, 5: 16807.20, 4: 20926.60,
}  # fmt: skip


def decay_samples(rate: int) -> int:
    """Samples from level 0, with the shared counter at 0, to level 127.

    A percussive tone with SL 0 leaves decay at once and falls at RR (S1 page 12:
    "Attenuation times of the release rate are the same as that of the decay
    rate"), all the way to the bottom.
    """
    tone = (0x00, 0x01, 0x3F, 0x00, 0x00, 0xF0, 0x00, rate >> 2)
    chip = struck(tone, f_number=0x40, block=2 * (rate & 3))
    chip.run(SAMPLE)  # damp ends and the instant attack puts the level at 0
    assert chip.level[C[0]] == 0
    chip.counter = (1 << 24) - 1  # the next sample is counter 0
    chip.run(SAMPLE)
    count = 0  # the first sample is time 0
    stride = 1 << max(0, 13 - (rate >> 2))  # the level can only move this often
    while chip.level[C[0]] != 127:
        chip.run(SAMPLE * stride)
        chip.take_outputs()
        count += stride
    return count


@pytest.mark.parametrize("rate", sorted(DECAY_MS))
def test_table_iii_7_decay_times(rate):
    # Spec 8.9. From counter 0 the model's 127th step falls one opportunity
    # earlier than the printed time (validation.md: "allowing the one early first
    # step"): the printed figures are whole opportunities, 127, 102, 85 and 73
    # pairs of them for rate & 3 = 0 to 3.
    opportunity = 1 << max(0, 13 - (rate >> 2))
    printed = DECAY_MS[rate]
    model = (decay_samples(rate) + opportunity) * SAMPLE_MS
    if rate < 52:
        # The table is printed to 0.01 ms and its longest rows differ from this
        # arithmetic by 0.02 ms in 20,000: two parts in a million.
        assert abs(model - printed) < 0.011 + printed * 2e-6, (model, printed)
    else:
        # The fastest rows: the table's rule of proportion against the chip's
        # measured 16-sample cycles (spec 8.7). Within a sample and a half.
        assert abs(model - printed) < 1.5 * SAMPLE_MS, (model, printed)


def test_table_iii_7_rates_below_4_never_change():
    # S1 page 13: 'When RATE is "0", the envelope will not change.' (R = 0.)
    assert decay_step_never(0)


def decay_step_never(release: int) -> bool:
    tone = (0x00, 0x01, 0x3F, 0x00, 0x00, 0xF0, 0x00, release)
    chip = tone_chip(tone, block=7)
    return set(levels(chip, C[0], 9_000)[5:]) == {0}


# ------------------------------------------------------ Table III-7: attack

# S1 Table III-7 (page 13), right half: effective rate -> ms from 48 dB to 0 dB.
ATTACK_MS = {
    59: 0.14, 58: 0.18, 57: 0.22, 56: 0.28, 55: 0.30, 54: 0.34, 53: 0.42, 52: 0.50,
    51: 0.54, 50: 0.60, 49: 0.70, 48: 0.84, 47: 0.97, 46: 1.13, 45: 1.37, 44: 1.69,
    43: 1.93, 42: 2.25, 41: 2.74, 40: 3.38, 39: 3.86, 38: 4.51, 37: 5.47, 36: 6.76,
    35: 7.72, 34: 9.01, 33: 10.94, 32: 13.52, 31: 15.45, 30: 18.02, 29: 21.88,
    28: 27.03, 27: 30.90, 26: 36.04, 25: 43.77, 24: 54.07, 23: 61.79, 22: 72.09,
    21: 87.54, 20: 108.13, 19: 123.58, 18: 144.18, 17: 175.07, 16: 216.27,
    15: 247.16, 14: 288.36, 13: 350.15, 12: 432.54, 11: 494.33, 10: 576.72,
    9: 700.30, 8: 865.08, 7: 988.66, 6: 1153.43, 5: 1400.60, 4: 1730.15,
}  # fmt: skip


def attack_samples(rate: int, counter: int = 0) -> int:
    """Samples of attack from level 127 to level 0, the shared counter being
    ``counter`` at the first."""
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, (rate >> 2) << 4, 0x00, 0x0F)
    chip = struck(tone, f_number=0x40, block=2 * (rate & 3))
    chip.run(SAMPLE)  # the sample in which damp ends (the level is already 127)
    assert chip.level[C[0]] == 127
    chip.counter = (counter - 1) % (1 << 24)
    count = 0
    while chip.level[C[0]] != 0:
        chip.run(SAMPLE)
        count += 1
    return count


@pytest.mark.parametrize("rate", sorted(ATTACK_MS))
def test_table_iii_7_attack_times(rate):
    # Spec 8.15: up to rate 47 the printed times are 21, 17, 14 and 12 times a
    # power of two samples. The measured attack (spec 8.10, 8.11) takes 42 steps,
    # four to an opportunity, which is those multiples to within one opportunity.
    # Spec 8.12: from rate 48 the level moves every sample, and the printed times
    # are the step counts of the measured formulas (42, 25, 14 ... 7 samples).
    printed = ATTACK_MS[rate]
    if rate < 48:
        model = attack_samples(rate)
        opportunity = 1 << (13 - (rate >> 2))
        assert round(printed / SAMPLE_MS / opportunity) == (21, 17, 14, 12)[rate & 3]
        assert abs(model * SAMPLE_MS - printed) <= opportunity * SAMPLE_MS + 0.006
    else:
        # How long a mixed rate takes depends on where the shared counter is
        # when the attack starts. The printed time lies among the times the model
        # can take.
        model = [attack_samples(rate, counter) for counter in range(16)]
        assert min(model) - 1.5 <= printed / SAMPLE_MS <= max(model) + 1.5, model


def test_table_iii_7_attack_rate_15_takes_no_time():
    # S1 page 13: 0.00 ms for rates 60 to 63.
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x0F)
    chip = struck(tone)
    assert levels(chip, C[0], 3)[0] == 0


# ------------------------------------------------- the envelope figure III-1


def test_figure_iii_1_a_sustained_tone_holds_and_a_percussive_one_falls():
    # S1 III-1-2 and Figure III-1 (pages 9, 10); III-1-5 (page 12): "With
    # percussive tone, it is the critical point of change from decay mode to
    # release mode."
    held = tone_chip((0x00, 0x21, 0x3F, 0x00, 0x00, 0xFC, 0x00, 0x28))
    falling = tone_chip((0x00, 0x01, 0x3F, 0x00, 0x00, 0xFC, 0x00, 0x28))
    assert levels(held, C[0], 6000)[-1] == 16  # SL 2: 6 dB, 16 steps
    assert levels(falling, C[0], 6000)[-1] > 60


def test_sus_on_makes_the_release_rate_5():
    # S1 III-1-6 (page 14): 'When this bit is "1", the RR with the key off will
    # be 5.' Rate 5 x 4 = 20 is printed as 1307.91 ms (Figure III-1: "RS: 1.2 s").
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x0F)
    chip = tone_chip(tone, f_number=0x40, block=0)
    chip.run(SAMPLE * 10)
    note(chip, 0, 0x40, 0, key=0, sus=1)
    took = 0
    while chip.level[C[0]] != 127:
        chip.run(SAMPLE * 64)
        chip.take_outputs()
        took += 64
    assert abs(took * SAMPLE_MS - DECAY_MS[20]) < 25, took


def test_figure_iii_1_damp_takes_10_ms():
    # S1 Figure III-1 (page 10): "DP: 10 ms (0 - 48 dB)". Table III-7 has 10.22 ms
    # at rate 48, which is base rate 12 (measured: S4, see test_measured).
    assert DECAY_MS[4 * YM2413.damp_rate] == 10.22
    assert DECAY_MS[4 * YM2413.percussive_release_rate] == 326.98  # "RR': 310 ms"


# ---------------------------------------------------------- the two LFOs


def test_tremolo_is_3_7_hz():
    # S1 III-1-2 (page 10): "The frequency is 3.7 Hz".
    chip = tone_chip((0x21, 0xA1, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00))
    trace = attribute(chip, "tremolo", 0, 0) or [chip.tremolo]
    seen = []
    for _ in range(3 * 13_440):
        chip.run(SAMPLE)
        seen.append(chip.tremolo)
    chip.take_outputs()
    period = next(p for p in range(1, 20_000) if seen[:13_440] == seen[p : p + 13_440])
    assert round(CLOCK_HZ / 72 / period, 1) == 3.7 and trace is not None


def test_vibrato_is_6_07_hz_not_the_printed_6_4():
    # S1 III-1-2 (page 10) says 6.4 Hz. Measured: a period of 8,192 samples,
    # 6.07 Hz (S4 20151201.txt). The measurement is taken (contradiction C2), and
    # this test would fail on S1's figure on purpose.
    chip = tone_chip((0x21, 0x61, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00), f_number=0x1C0, block=6)
    steps = []
    last = chip.phase[C[0]]
    for _ in range(3 * 8192):
        chip.run(SAMPLE)
        steps.append((chip.phase[C[0]] - last) % (1 << 19))
        last = chip.phase[C[0]]
    chip.take_outputs()
    period = next(p for p in range(1, 10_000) if steps[:8192] == steps[p : p + 8192])
    assert round(CLOCK_HZ / 72 / period, 2) == 6.07
    assert round(CLOCK_HZ / 72 / period, 1) != 6.4


# ----------------------------------------------------- slots and the DAC


def test_table_ii_3_channels_come_out_in_their_carrier_slots():
    # S1 Table II-3 (page 5) and Figure III-3: channel n is output in the slot of
    # its carrier: slots 4, 5, 6, 10, 11, 12, 16, 17, 18 counting from 1.
    for channel in range(9):
        chip = OPLL(YM2413)
        user_tone(chip, (0x21, 0x21, 0x3F, 0x00, 0xF0, 0xF0, 0x00, 0x00))
        note(chip, channel, 0x155, 5)
        heard = {
            slot
            for sample in words(chip, 300)
            for slot, (melody_word, _) in enumerate(sample)
            if melody_word not in (0, -1)
        }
        assert heard == {C[channel]}


RHYTHM_SETUP = ((0x16, 0x20), (0x17, 0x50), (0x18, 0xC0), (0x26, 0x05), (0x27, 0x05), (0x28, 0x01))


def rhythm_chip(keys: int) -> OPLL:
    chip = OPLL(YM2413)
    for register, value in RHYTHM_SETUP:  # S1 Table III-9 (page 16), right half
        write(chip, register, value)
    write(chip, 0x0E, 0x20)
    write(chip, 0x0E, 0x20 | keys)
    return chip


# S1 Table III-9 (page 16), slots counted from 1: BD 13 and 16, SD 17, TOM 15,
# TOP-CYM 18, HH 14. The sound is heard from its last slot.
@pytest.mark.parametrize("bit, slot", ((4, 15), (3, 16), (2, 14), (1, 17), (0, 13)))
def test_table_iii_9_rhythm_slots_and_the_second_output(bit, slot):
    # S1 III-4 (page 19): "the same percussion sounds are output twice".
    chip = rhythm_chip(1 << bit)
    copy = {13: 0, 14: 1, 15: 2, 16: 6, 17: 7}[slot]
    trace = words(chip, 400)
    heard = {
        index
        for sample in trace
        for index, (_, rhythm_word) in enumerate(sample)
        if rhythm_word not in (0, -1)
    }
    assert heard == {slot, copy}
    for earlier, later in zip(trace, trace[1:], strict=False):
        assert later[copy][1] == earlier[slot][1]
    assert all(melody_word == 0 for sample in trace for melody_word, _ in sample)


def test_rhythm_mode_leaves_six_melody_channels():
    # S1 III-1-7 (page 16): "In this mode, the melody section is limited to six
    # sounds."
    chip = rhythm_chip(0)
    for channel in range(9):
        write(chip, 0x30 + channel, 0x10)
        note(chip, channel, 0x155, 5)
    heard = {
        slot
        for sample in words(chip, 300)
        for slot, (melody_word, _) in enumerate(sample)
        if melody_word not in (0, -1)
    }
    assert heard == set(C[:6])
    assert M[6] == 12


def test_half_wave_rectification():
    # S1 III-1-3 (page 12): "The carrier wave is rectified to half wave."
    tone = list(PLAIN_SINE)
    tone[3] = 0x10
    out = melody(tone_chip(tone, f_number=256, block=4), 1280)
    assert max(out) == 255 and min(out) == 0
    assert sum(1 for value in out if value == 0) >= 640
