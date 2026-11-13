"""Rung 2a: what was measured on a real YM2413 (S4), as its write-ups state it.

S4 is the openMSX YM2413 reverse-engineering project: write-ups by Wouter
Vermaelen in the repository andete/ym2413 (commit 4893d1c), of measurements made
by driving one real chip from a micro-controller and sampling its two output
pins. Each test names the write-up its numbers were typed from. The numbers come
from the write-ups' prose and from their tables of measurements; their program
fragments were not read (docs/provenance-audit.md). "measured" throughout.

Nothing here reads S4's capture files: that is rung 2b (tests/test_captures.py).
"""

from __future__ import annotations

import pytest
from helpers import (
    PLAIN_SINE,
    SAMPLE,
    C,
    M,
    attribute,
    carrier_peak,
    levels,
    melody,
    note,
    press,
    reference_value,
    rhythm,
    runs,
    struck,
    tone_chip,
    user_tone,
    words,
    write,
)

from ym2413_python import OPLL, YM2413

# ------------------------------------------------- the operator (spec 6)

# tab.txt: "the maximum amplitude value for each volume: 255 180(!) 127 90 63 45
# 31 22 15 11 7 5 3 2 1 1".
PEAKS = (255, 180, 127, 90, 63, 45, 31, 22, 15, 11, 7, 5, 3, 2, 1, 1)


@pytest.mark.parametrize("volume", range(16))
def test_peak_amplitude_for_each_volume(volume):
    chip = tone_chip(PLAIN_SINE, f_number=256, block=1, volume=volume)
    out = melody(chip, 1024)
    assert max(out) == PEAKS[volume] and min(out) == -PEAKS[volume]


@pytest.mark.parametrize("sl", range(16))
def test_peak_amplitude_for_each_sustain_level(sl):
    # sl-ksr.txt: "these are the exact same amplitudes as for the volume setting".
    # envelope.txt: "internal-sustain-envelope-level = 8 * SL".
    tone = (0x21, 0x21, 0x3F, 0x00, 0x00, 0xFF, 0x00, sl << 4)
    chip = tone_chip(tone, f_number=256, block=1)
    chip.run(SAMPLE * 200)
    chip.take_outputs()
    assert chip.level[C[0]] == 8 * sl
    assert max(melody(chip, 1024)) == PEAKS[sl]


def test_sustain_level_15_is_level_120_not_the_bottom():
    # 20150320.txt: "we picked SL=15 ... the EG will only go down to -45dB";
    # "That corresponds to 120 different EG levels". Contradiction C5.
    tone = (0x21, 0x21, 0x3F, 0x00, 0x00, 0xFF, 0x00, 0xF0)
    assert levels(tone_chip(tone), C[0], 300)[-1] == 120


def one_period_of_words(volume: int) -> list[int]:
    chip = tone_chip(PLAIN_SINE, f_number=256, block=1, volume=volume)
    return [sample[C[0]][0] for sample in words(chip, 1024)]


def test_a_full_volume_sine_uses_exactly_400_codes():
    # tab.txt: "If we count the number of unique values in the column for
    # volume=0 we also get 400" (of the 512 codes; +0 and -0 are two).
    assert len(set(one_period_of_words(0))) == 400


@pytest.mark.parametrize("volume", (14, 15))
def test_the_quietest_volumes_use_four_codes(volume):
    # tab.txt: "Both volume=14 and 15 (only) use 4 possible values, 1, 0, -1, -2
    # (corresponding to +1, +0, -0, -1)", 14 louder on average than 15.
    assert set(one_period_of_words(volume)) == {1, 0, -1, -2}


def test_volume_14_is_louder_than_15_on_average():
    loud = sum(1 for word in one_period_of_words(14) if word in (1, -2))
    quiet = sum(1 for word in one_period_of_words(15) if word in (1, -2))
    assert loud > quiet


def test_the_sine_has_1024_steps():
    # 20150311.txt: the period divided by the flat-segment length "is always
    # exactly 1024".
    chip = tone_chip(PLAIN_SINE, f_number=64, block=1)  # one table step in 8 samples
    phases = [value >> 9 for value in attribute(chip, "phase", C[0], 8 * 1024 * 2)]
    lengths = {length for _, length in runs(phases)[1:-1]}
    assert lengths == {8}
    assert len(set(phases)) == 1024


def test_negative_values_are_the_bit_inverse_of_positive_ones():
    # tab.txt: "this creates a 1-complements result ... two possible
    # representations for zero (+0 and -0)".
    period = one_period_of_words(0)
    start = next(i for i in range(1, 1024) if period[i - 1] < 0 <= period[i])
    turned = period[start:] + period[:start]
    assert all(turned[i + 512] == ~turned[i] for i in range(512))
    assert 0 in period and -1 in period


def test_half_sine_is_minus_zero_for_exactly_half_the_period():
    # small-signals.txt: "the lengths of the segments with value -0 ... are
    # exactly 512 samples long (exactly half a period in this experiment)": "the
    # absolute value of the 2nd part is set to zero, but the sign still toggles".
    tone = list(PLAIN_SINE)
    tone[3] = 0x10
    chip = tone_chip(tone, f_number=256, block=1)
    period = [sample[C[0]][0] for sample in words(chip, 2048)]
    assert (-1, 512) in runs(period)
    assert min(period) == -1


def test_mute_at_envelope_level_124_and_the_peak_widths_before_it():
    # small-signals.txt, first experiment: one sine period of 1,024 samples, the
    # envelope one level lower every 4,096 samples. "The widths of those peaks
    # are respectively 342 and 332 samples" at levels 112 and 113; "the signal
    # stops changing at the point where we expect envelope level 124" and stays
    # at +0 ("not -0, nor alternating").
    tone = (0x21, 0x21, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00)
    chip = tone_chip(tone, f_number=256, block=1)
    chip.run(SAMPLE * 2048)
    for level, width in ((112, 342), (113, 332), (124, 0)):
        chip.level[C[0]] = level
        period = [sample[C[0]][0] for sample in words(chip, 1024)]
        assert sum(1 for word in period if word > 0) == width
        if level == 124:
            assert set(period) == {0}


def test_total_attenuation_is_clipped_at_127():
    # small-signals.txt, second experiment (volume 8): the total "increases by
    # one every 4096 samples until it reaches level 127 ... Beyond this point the
    # total attenuation level remains at 127 (until the envelope level reaches
    # 124)". With volume 8 (64 steps) the total passes 127 at envelope level 63.
    tone = (0x21, 0x21, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00)
    chip = tone_chip(tone, f_number=256, block=1, volume=8)
    chip.run(SAMPLE * 2048)
    shapes = []
    for level in (62, 63, 64, 100, 123):
        chip.level[C[0]] = level
        shapes.append(sum(1 for sample in words(chip, 1024) if sample[C[0]][0] > 0))
    assert shapes[0] > shapes[1] == shapes[2] == shapes[3] == shapes[4] > 0
    assert shapes[1] == sum(1 for phase in range(512) if reference_value(phase, 127) >> 3 > 0)


def test_a_quiet_modulator_outputs_plus_zero():
    # small-signals.txt, third experiment: "a strong indication that also the
    # modulator output is kept at a constant value +0 once the modulator
    # envelope level reaches value 124".
    tone = (0x21, 0x21, 0x00, 0x00, 0xF0, 0xF0, 0x00, 0x00)
    chip = tone_chip(tone)
    chip.run(SAMPLE * 100)
    chip.level[M[0]] = 123
    assert set(attribute(chip, "previous", 0, 600)) != {0}
    chip.level[M[0]] = 124
    assert set(attribute(chip, "previous", 0, 600)[2:]) == {0}


# ------------------------------------------- modulation and feedback (6.11-13)


def two_operator_reference(total_level: int, feedback: int, count: int, step: int) -> list[int]:
    """Carrier words predicted from spec 6.5 to 6.13 with a separate writing of
    the operator: both operators at envelope level 0, the same pitch, starting
    from phase 0 with nothing remembered."""
    out = []
    previous = before = 0
    phase = 0
    for _ in range(count):
        phase += step
        index = phase >> 9
        fed = (previous + before) >> (8 - feedback) if feedback else 0
        before, previous = previous, reference_value(index + fed, 2 * total_level)
        out.append(reference_value(index + 2 * before, 0) >> 3)
    return out


@pytest.mark.parametrize("total_level", (0, 8, 32, 37, 48, 63))
def test_modulator_into_carrier(total_level):
    # mod-car.txt: registers $10 = $40, block 0, both operators at half speed, so
    # "each of the 1024 entries in the sine table is repeated 16 times"; TL from 0
    # to 63; with the final model "the graph matches _exactly_ with the measured
    # data ... for all values". The depth at TL 0 is "-8pi..8pi".
    tone = (0x20, 0x20, total_level, 0x00, 0xF0, 0xF0, 0x00, 0x00)
    chip = struck(tone, f_number=0x40, block=0)
    chip.run(SAMPLE)  # damp ends: both phases are reset, both levels go to 0
    got = [sample[C[0]][0] for sample in words(chip, 16 * 1024)]
    assert got == two_operator_reference(total_level, 0, 16 * 1024, 32)


def test_the_modulator_is_one_sample_out_of_step_with_the_carrier():
    # mod-car.txt: "Instead of seeing the same value for 16 consecutive samples we
    # only see 15 samples with the same value, followed by 1 other value again
    # followed by 15 constant samples."
    tone = (0x20, 0x20, 8, 0x00, 0xF0, 0xF0, 0x00, 0x00)
    chip = struck(tone, f_number=0x40, block=0)
    chip.run(SAMPLE)
    got = [sample[C[0]][0] for sample in words(chip, 16 * 1024)]
    lengths = [length for _, length in runs(got)]
    pairs = sum(1 for a, b in zip(lengths, lengths[1:], strict=False) if (a, b) == (15, 1))
    assert pairs > 200
    assert max(lengths) <= 16 * 12  # the flat top of the sine


def test_every_half_period_all_modulation_depths_cross_zero_together():
    # mod-car.txt: "every half period, the waveforms for all TL-values indeed
    # _exactly_ overlap".
    crossings = []
    for total_level in (0, 20, 63):
        tone = (0x20, 0x20, total_level, 0x00, 0xF0, 0xF0, 0x00, 0x00)
        chip = struck(tone, f_number=0x40, block=0)
        chip.run(SAMPLE)
        got = [sample[C[0]][0] for sample in words(chip, 16 * 1024)]
        crossings.append(got[8192 - 8 : 8192 + 8])
    assert crossings[0] == crossings[1] == crossings[2]


@pytest.mark.parametrize("total_level, feedback", ((37, 1), (37, 4), (37, 7), (0, 5), (0, 7), (63, 7)))
def test_feedback(total_level, feedback):
    # fb.txt: TL 63 with FB 7, TL 37 and TL 0 with FB 0 to 7; "This model can
    # _exactly_ predict the measured data" once the two remembered outputs have
    # settled, chaos at TL 0, FB 7 included. The form is the sum of the last two
    # outputs; the amount is S1's Table III-6 (see test_manual).
    tone = (0x20, 0x20, total_level, feedback, 0xF0, 0xF0, 0x00, 0x00)
    chip = struck(tone, f_number=0x40, block=0)
    chip.run(SAMPLE)
    assert chip.previous[0] == chip.before_previous[0] == 0  # nothing remembered yet
    got = [sample[C[0]][0] for sample in words(chip, 16 * 1024)]
    assert got == two_operator_reference(total_level, feedback, 16 * 1024, 32)


def test_feedback_0_is_no_feedback():
    # fb.txt: "FB=0 really means _no_ feedback".
    assert two_operator_reference(37, 0, 4000, 32) != two_operator_reference(37, 1, 4000, 32)


def test_each_time_the_same_note_is_played_the_wave_is_the_same():
    # mod-car.txt: "Each time the same note is played, the wave looks exactly the
    # same" (spec 7.10: the phases are reset when the damp phase ends).
    tone = (0x21, 0x21, 0x10, 0x00, 0xF0, 0xF0, 0x00, 0x0F)
    chip = tone_chip(tone, f_number=0x123, block=3, key=0)
    takes = []
    for wait in (700, 1234):
        press(chip, 0, 0x123, 3)
        takes.append(melody(chip, 500))
        note(chip, 0, 0x123, 3, key=0)
        chip.run(SAMPLE * wait)
        chip.take_outputs()
    assert takes[0] == takes[1] and max(takes[0]) > 200


# ------------------------------------------------------- the phase (spec 7)

# 20150316.txt, first table: MULTI, block, F-number -> flat-segment length.
# None is "inf": the phase does not move.
REPEATS = [
    (0, 0, 0, None), (0, 0, 1, None), (0, 0, 2, 512), (0, 0, 3, 512), (0, 0, 4, 256),
    (0, 0, 8, 128), (0, 1, 0, None), (0, 1, 1, 512), (0, 1, 2, 256), (0, 1, 3, 170.67),
    (0, 1, 4, 128), (0, 1, 8, 64), (0, 2, 0, None), (0, 2, 1, 256), (0, 2, 2, 128),
    (0, 2, 3, 85.33), (0, 2, 4, 64), (0, 2, 8, 32), (1, 0, 0, None), (1, 0, 1, 512),
    (1, 0, 2, 256), (1, 0, 3, 170.67), (1, 0, 4, 128), (1, 0, 8, 64), (1, 1, 0, None),
    (1, 1, 1, 256), (1, 1, 2, 128), (1, 1, 3, 85.33), (1, 1, 4, 64), (1, 1, 8, 32),
]  # fmt: skip


@pytest.mark.parametrize("multi, block, f_number, repeats", REPEATS)
def test_flat_segment_lengths(multi, block, f_number, repeats):
    # "Whenever fnum=0 the phase doesn't change"; "ML=0,block=0,fnum=1 is the only
    # additional combination"; "the phase keeps it's current value, it's not reset".
    tone = list(PLAIN_SINE)
    tone[1] = 0x20 | multi
    chip = tone_chip(tone, f_number=f_number, block=block)
    chip.phase[C[0]] = 5 << 9
    phases = [value >> 9 for value in attribute(chip, "phase", C[0], 512 * 7)]
    if repeats is None:
        assert set(phases) == {5}
        return
    lengths = [length for _, length in runs(phases)[1:-1]]
    assert round(sum(lengths) / len(lengths), 2) == repeats
    if repeats == 170.67:  # "I measured lengths 171,171,170 for 3 successive segments"
        assert sorted(lengths[:3]) == [170, 171, 171]


# 20150316.txt, second table: MULTI, block, F-number 256 -> period in samples.
PERIODS = [(0, block, 4096 >> block) for block in range(8)] + [
    (1, 7, 16), (2, 7, 8), (3, 7, 5.33), (4, 7, 4), (5, 7, 3.2), (6, 7, 2.67), (7, 7, 2.29), (8, 7, 2),
]  # fmt: skip


@pytest.mark.parametrize("multi, block, period", PERIODS)
def test_period_lengths_at_high_pitch(multi, block, period):
    tone = list(PLAIN_SINE)
    tone[1] = 0x20 | multi
    chip = tone_chip(tone, f_number=256, block=block)
    before = chip.phase[C[0]]
    chip.run(SAMPLE)
    step = (chip.phase[C[0]] - before) % (1 << 19)
    assert round((1 << 19) / step, 2) == period


def test_the_step_overflows_19_bits_harmlessly():
    # 20150316.txt, remark 7: MULTI 15, block 7, F-number 511 predicts $EF880,
    # "=0x6F880" in 19 bits.
    tone = list(PLAIN_SINE)
    tone[1] = 0x2F
    chip = tone_chip(tone, f_number=511, block=7)
    before = chip.phase[C[0]]
    chip.run(SAMPLE)
    assert (chip.phase[C[0]] - before) % (1 << 19) == 0x6F880


def test_vibrato_steps_for_the_top_pitch_range():
    # 20151201.txt: $10 = $C0, $20 = $1D (F-number $1C0, block 6); "regions" of
    # 1,024 samples, the pattern repeating every 8,192. The eight step sizes are
    # the ones docs/validation.md records from that write-up. Approximate in the
    # source: "I only verified the last row", by aligning waveforms.
    chip = tone_chip((0x21, 0x61, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00), f_number=0x1C0, block=6)
    chip.vibrato_time = 8191
    steps = []
    last = chip.phase[C[0]]
    for _ in range(8192):
        chip.run(SAMPLE)
        steps.append((chip.phase[C[0]] - last) % (1 << 19))
        last = chip.phase[C[0]]
    chip.take_outputs()
    assert runs(steps) == [
        (28672, 1024), (28768, 1024), (28896, 1024), (28768, 1024),
        (28672, 1024), (28576, 1024), (28448, 1024), (28576, 1024),
    ]  # fmt: skip


# ---------------------------------------------- decay and release (spec 8.5-8.8)

# 20150320.txt (rate 14: "in sequence 2048, 1024 and 1024 samples. And this is
# exactly what we measured"; rates 4, 9 and 19 confirmed the same way) and
# attack.txt section 3, the re-measured rows: samples spent on each level, 0.5
# meaning two levels in one sample. Each row is one turn of a cycle.
STEP_LENGTHS = {
    4: [8192], 9: [2048, 2048, 2048, 1024, 1024], 14: [2048, 1024, 1024],
    19: [1024, 512, 512, 512, 512, 512, 512],
    44: [8, 8, 8, 8], 45: [8, 8, 8, 4, 4], 46: [8, 4, 4, 8, 4, 4], 47: [8, 4, 4, 4, 4, 4, 4],
    48: [4, 4, 4, 4], 49: [4, 4, 4, 2, 2], 50: [4, 2, 2, 4, 2, 2], 51: [4, 2, 2, 2, 2, 2, 2],
    52: [2] * 8, 53: [2] * 6 + [1] * 4, 54: [2, 2, 1, 1, 1, 1] * 2, 55: [2, 2] + [1] * 12,
    56: [1] * 16, 57: [0.5] * 4 + [1] * 12, 58: ([0.5] * 4 + [1] * 4) * 2,
    59: [0.5] * 12 + [1] * 4, 60: [0.5], 61: [0.5],
}  # fmt: skip


def decaying_chip(rate: int) -> OPLL:
    """A carrier falling at an effective rate from level 0 (see test_manual)."""
    tone = (0x00, 0x01, 0x3F, 0x00, 0x00, 0xF0, 0x00, rate >> 2)
    chip = struck(tone, f_number=0x40, block=2 * (rate & 3))
    chip.run(SAMPLE)
    return chip


@pytest.mark.parametrize("rate", sorted(STEP_LENGTHS))
def test_decay_step_lengths(rate):
    cycle = STEP_LENGTHS[rate]
    chip = decaying_chip(rate)
    chip.counter = 12345
    span = int(sum(cycle) * 6) + 40
    trace = levels(chip, C[0], min(span, 126 * 8192))
    segments = runs(trace)[1:-1]
    got = []
    for (level, length), (after, _) in zip(segments, segments[1:], strict=False):
        got += [0.5] * ((after - level) // 2 - (0 if length > 1 else 0)) if after - level == 2 else []
        if after - level == 1:
            got.append(length)
        elif length > 1:
            got[-1:] = [length - 0.5 if False else length]
    if 0.5 in cycle:
        # Two levels in one sample: describe each sample by what it did.
        deltas = [b - a for a, b in zip(trace, trace[1:], strict=False) if b < 127]
        got = [0.5 if delta == 2 else 1 for delta in deltas if delta]
        assert 0 not in deltas
    else:
        got = [length for (_, length) in segments]
    doubled = cycle * 3
    size = len(cycle)
    assert any(got[offset : offset + 2 * size] == doubled[: 2 * size] for offset in range(size)), got[:20]


def test_rates_60_to_63_move_two_levels_every_sample():
    # 20150320.txt: "60..63 -> as expected: increase 2 levels per step".
    trace = levels(decaying_chip(63), C[0], 20)
    assert trace[:6] == [2, 4, 6, 8, 10, 12]


def first_segments(attack: int, decay: int, block: int) -> set[int]:
    """Lengths of the first decay segment (the time spent at level 0), over many
    starting values of the shared counter, to the nearest $100 samples."""
    seen = set()
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, attack << 4 | decay, 0x00, 0xF0)
    for start in range(0, 0x4000, 0x55):
        chip = struck(tone, f_number=0x40, block=block)
        chip.counter = start
        while chip.level[C[0]] != 0:
            chip.run(SAMPLE * 16)
        chip.take_outputs()
        while chip.level[C[0]] == 0:
            chip.run(SAMPLE * 16)
        chip.take_outputs()
        # the level left 0 within the last 16 samples; it reached 0 within 16
        # samples of some multiple of 16 earlier: count again precisely
        seen.add(start)
    return seen


def first_segment_set(attack: int, decay: int, block: int) -> set[int]:
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, attack << 4 | decay, 0x00, 0xF0)
    found = set()
    for start in range(0, 0x4000, 0x155):
        chip = struck(tone, f_number=0x40, block=block)
        chip.counter = start
        trace = levels(chip, C[0], 0x3800)
        first = trace.index(0)
        length = next(i for i in range(first, len(trace)) if trace[i] != 0) - first
        found.add(round(length / 0x100) * 0x100)
    return found


def test_first_segment_after_attack_4_decay_2():
    # adsr-transitions.txt: "for the combination AR=4/DR=2 such numbers are
    # '0x200, 0x600 and 0xe00' ... eventually also found a segment with width
    # 0xa00": (2n + 1) x L. This is what fixes the first pattern's rotation.
    assert first_segment_set(4, 2, 0) == {0x200, 0x600, 0xA00, 0xE00}


@pytest.mark.parametrize(
    "block, lengths",
    (
        # "5-out-of-8 ... I measured lengths: 0x100 0x300 0x400 0x500 0x700 0x900
        # 0xb00 0xc00 0xd00 0xf00"
        (2, (1, 3, 4, 5, 7, 9, 0xB, 0xC, 0xD, 0xF)),
        # "6-out-of-8 ... 0x100 0x200 0x300 0x500 0x600 0x700 0xa00 0xd00 0xe00.
        # The model predicts 0x900 0xb00 0xf00 should also be present"
        (4, (1, 2, 3, 5, 6, 7, 9, 0xA, 0xB, 0xD, 0xE, 0xF)),
        # "7-out-of-8 ... 0x100 ... 0x700 0xb00 0xc00. The values 0x{9,a,d,e,f}00
        # should also be present (only 0x800 and 0x1000 are missing)"
        (6, (1, 2, 3, 4, 5, 6, 7, 9, 0xA, 0xB, 0xC, 0xD, 0xE, 0xF)),
    ),
)
def test_first_segment_after_attack_5_decay_2(block, lengths):
    # adsr-transitions.txt, "Extend to higher frequencies". Every length S4
    # measured must occur, and none that S4's account excludes.
    assert first_segment_set(5, 2, block) == {0x100 * length for length in lengths}


# ---------------------------------------------------------- attack (8.10-8.14)

# attack.txt 2.3 and 2.9: the two sequences.
FROM_127 = [127, 119, 111, 104, 97, 90, 84, 78, 73, 68, 63, 59, 55, 51, 47, 44, 41, 38, 35, 32,
            29, 27, 25, 23, 21, 19, 17, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]  # fmt: skip
FROM_124 = [124, 116, 108, 101, 94, 88, 82, 76, 71, 66, 61, 57, 53, 49, 45, 42, 39, 36, 33, 30,
            28, 26, 24, 22, 20, 18, 16, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]  # fmt: skip


def attacking_chip(attack: int, block: int = 0, release: int = 15) -> OPLL:
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, attack << 4, 0x00, release)
    return struck(tone, f_number=0x40, block=block)


@pytest.mark.parametrize("attack", (7, 10, 11, 12))
def test_attack_sequence_from_127(attack):
    # attack.txt 2.3: "if we start at envelope level 127 and iteratively apply
    # 'f4' we get our measured sequence"; "the same as the levels for any attack
    # rate below 12:0"; and 2.6: "In column 12:0 we see the familiar sequence".
    chip = attacking_chip(attack)
    trace = [127] + levels(chip, C[0], 3000)
    assert [level for level, _ in runs(trace[: trace.index(0) + 1])] == FROM_127


def test_attack_sequence_from_124_after_a_damp_phase():
    # attack.txt 2.9: "Each time there is a damp phase (release didn't finish
    # ...) attack starts from 124."
    chip = attacking_chip(10, release=0)
    chip.run(SAMPLE * 400)  # up to level 0
    note(chip, 0, 0x40, 0, key=0)  # release rate 0: the level stays
    press(chip, 0, 0x40, 0)
    trace = levels(chip, C[0], 3000)
    start = trace.index(124)
    climb = [level for level, _ in runs(trace[start:])]
    assert climb[: len(FROM_124)] == FROM_124
    assert max(trace[:start]) == 124  # damp went no further


@pytest.mark.parametrize("attack, plateau", ((7, 125), (10, 13), (11, 5)))
def test_three_single_samples_then_a_plateau(attack, plateau):
    # attack.txt 2.2: at rate 10:0 "we see lengths of 13 plus 3 extra samples.
    # This is true for all attack rates less than 12:0"; 2.4: at 11:0 "only a
    # short plateau of 5 samples". (7:0 is 128 samples: 125 plus 3.)
    chip = attacking_chip(attack)
    trace = levels(chip, C[0], 6000)
    lengths = [length for _, length in runs(trace[: trace.index(0)])[1:]]
    for index in range(4, len(lengths) - 4, 4):
        assert sorted(lengths[index : index + 4]) == [1, 1, 1, plateau]


# attack.txt 2.6: "columns <n>:1 4x formula f<m> followed by 12x formula f<m+1>;
# <n>:2 4x followed by 4x; <n>:3 12x followed by 4x"; 12:x uses f3 and f4, 13:x
# f2 and f3, 14:x f1 and f2; f<n> is x - (x >> n) - 1.
@pytest.mark.parametrize("rate", range(48, 60))
def test_fast_attack_mixes_two_formulas(rate):
    slower = 4 - (rate - 48) // 4
    faster_in_16 = (0, 4, 8, 12)[rate & 3]
    used = []
    for counter in range(16):
        chip = attacking_chip(rate >> 2, block=2 * (rate & 3))
        chip.run(SAMPLE)
        chip.counter = counter
        chip.level[C[0]] = 127
        trace = [127] + levels(chip, C[0], 16)
        for before, after in zip(trace, trace[1:], strict=False):
            if before >= 64:  # where the two formulas give different results
                shift = next(n for n in (1, 2, 3, 4) if before - (before >> n) - 1 == after)
                assert shift in (slower, slower - 1)
                used.append(shift == slower - 1)
        # The first sample of each start is at a different place in the cycle.
    first_samples = used and [
        attack_formula_is_faster(rate, counter) for counter in range(16)
    ]
    assert sum(first_samples) == faster_in_16
    if rate & 3 == 2:  # four on, four off
        assert runs(first_samples + first_samples)[1][1] == 4


def attack_formula_is_faster(rate: int, counter: int) -> bool:
    chip = attacking_chip(rate >> 2, block=2 * (rate & 3))
    chip.run(SAMPLE)
    chip.counter = counter
    chip.level[C[0]] = 127
    chip.run(SAMPLE)
    slower = 4 - (rate - 48) // 4
    return chip.level[C[0]] == 127 - (127 >> (slower - 1)) - 1


def test_the_worked_example_at_rate_13_3():
    # attack.txt 2.6: "the envelope level in that cell is 21. If we apply formula
    # 'f2' on it we obtain 15 ... we need formula 'f3' to get to 13."
    assert 21 - (21 >> 2) - 1 == 15 and 15 - (15 >> 3) - 1 == 13
    seen = set()
    for counter in range(16):
        chip = attacking_chip(13, block=6)
        chip.run(SAMPLE)
        chip.counter = counter
        chip.level[C[0]] = 21
        seen.add(tuple(levels(chip, C[0], 2)))
    assert (15, 13) in seen


def test_attack_15_is_instant_only_when_damp_ends():
    # attack.txt 2.8: "attack=15 is only checked at the end of the damp phase";
    # "whenever attack rate 0 or 15 is active the attack curve is paused".
    chip = attacking_chip(0)
    assert set(levels(chip, C[0], 500)) == {127}  # rate 0: no attack
    write(chip, 0x05, 0xF0)
    assert set(levels(chip, C[0], 500)) == {127}  # 15 now: still stalled
    write(chip, 0x05, 0xC0)
    assert levels(chip, C[0], 100)[-1] == 0  # any other rate continues
    # "the very first sample after attack indeed already has maximum amplitude":
    # a quarter of the sample rate, so the first sample is at 90 degrees.
    chip = struck((0x00, 0x21, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00), f_number=256, block=7)
    assert melody(chip, 1) == [255]


# ----------------------------------------------------- the states (8.16-8.25)


def test_damp_is_rate_12_and_ends_at_124():
    # envelope.txt: "the DP phase corresponds to a base decay-rate of '12'. This
    # indeed corresponds to a 0..-48dB time of 10.22ms"; attack.txt 2.9: it stops
    # at 124. From level 0 at rate 48: 124 steps, one every 4 samples.
    chip = attacking_chip(4, release=0)
    chip.run(SAMPLE * 30_000)
    chip.take_outputs()
    assert chip.level[C[0]] == 0
    note(chip, 0, 0x40, 0, key=0)
    press(chip, 0, 0x40, 0)
    trace = levels(chip, C[0], 700)
    damp = trace[: trace.index(124) + 1]
    assert 124 * 4 - 4 <= len(damp) <= 124 * 4 + 4
    assert {length for _, length in runs(damp)[1:-1]} == {4}
    assert max(trace) == 124


def test_damp_is_faster_at_higher_pitch():
    # envelope.txt: "for higher frequencies the rate is faster, just as it is for
    # all the other rates".
    spans = []
    for block in (0, 6):
        tone = (0x00, 0x21, 0x3F, 0x00, 0x00, 0x40, 0x00, 0x00)
        chip = struck(tone, f_number=0x40, block=block)
        chip.run(SAMPLE)
        chip.level[C[0]] = 0
        chip.state[C[0]] = 2
        note(chip, 0, 0x40, block, key=0)
        press(chip, 0, 0x40, block)
        spans.append(levels(chip, C[0], 700).index(124))
    assert spans[1] < spans[0]


def test_release_runs_to_127():
    # attack.txt 2.9: "the release phase changes the envelope level all the way
    # to 127".
    chip = attacking_chip(15)
    chip.run(SAMPLE * 10)
    note(chip, 0, 0x40, 0, key=0)
    assert levels(chip, C[0], 2000)[-1] == 127


def sustaining(sl: int, decay: int = 12, sustained: int = 1, release: int = 0) -> OPLL:
    tone = (0x00, sustained << 5 | 0x01, 0x3F, 0x00, 0x00, 0xF0 | decay, 0x00, sl << 4 | release)
    return struck(tone, f_number=0x40, block=0)


def test_decay_stops_on_equality_so_a_level_passed_is_never_met():
    # envelope.txt b2: "started with a high SL value, waited till the envelope
    # decayed beyond a certain level and then changed SL to a value that
    # represents a level above the current level. This makes the envelope
    # continue to decay until -48dB."
    chip = sustaining(15, decay=8)
    chip.run(SAMPLE * 3000)
    assert 40 < chip.level[C[0]] < 100
    write(chip, 0x07, 0x20)
    assert levels(chip, C[0], 12_000)[-1] == 127


def test_sustain_can_stick_at_level_9():
    # envelope.txt b3: from an odd level, a decay of two levels a sample; "I
    # indeed measured a level of 9 instead of 8 (as expected for SL=1)".
    chip = sustaining(1, decay=1)
    chip.run(SAMPLE)
    chip.level[C[0]] = 5
    write(chip, 0x05, 0xFF)
    assert levels(chip, C[0], 50)[-1] == 9


def test_changing_sl_during_sustain_does_nothing():
    # envelope.txt b1.
    chip = sustaining(2)
    chip.run(SAMPLE * 2000)
    assert chip.level[C[0]] == 16
    write(chip, 0x07, 0xA0)
    assert set(levels(chip, C[0], 3000)) == {16}


def test_eg_typ_switches_sustain_between_holding_and_falling():
    # envelope.txt d1: "Switching EG_TYPE back and forth keeps switching between
    # the SL and RR phases."
    chip = sustaining(2, release=8)
    chip.run(SAMPLE * 2000)
    assert set(levels(chip, C[0], 600)) == {16}
    write(chip, 0x01, 0x01)
    falling = levels(chip, C[0], 600)
    assert falling[-1] > 18
    write(chip, 0x01, 0x21)
    assert len(set(levels(chip, C[0], 600))) == 1


def release_span(sustained: int, sus: int, release: int) -> int:
    """Samples from key-off at level 0 to level 8, a rate's signature."""
    tone = (0x00, sustained << 5 | 0x01, 0x3F, 0x00, 0x00, 0xF0, 0x00, release)
    chip = struck(tone, f_number=0x40, block=0)
    chip.run(SAMPLE * 3)
    chip.counter = 0
    chip.level[C[0]] = 0
    chip.write(0, 0x20)
    chip.write(1, sus << 5)
    return levels(chip, C[0], 40_000).index(8)


def test_release_rates():
    # envelope.txt: percussive tone, "SUS-ON selects the RS curve with a
    # basis-rate=5. SUS-OFF selects RR' with basis-rate=7"; sustained tone, "For
    # SUS-ON the basis-rate is fixed at 5, for SUS-OFF the basis rate is the
    # selected RR-rate."
    by_rate = {rate: release_span(1, 0, rate) for rate in (5, 7, 9, 3)}
    assert len(set(by_rate.values())) == 4
    assert release_span(1, 0, 9) == by_rate[9]  # sustained, SUS off: RR
    assert release_span(1, 1, 9) == by_rate[5]  # sustained, SUS on: 5
    assert release_span(0, 0, 9) == by_rate[7]  # percussive, SUS off: 7
    assert release_span(0, 1, 9) == by_rate[5]  # percussive, SUS on: 5
    assert release_span(0, 0, 3) == by_rate[7]


def test_sus_and_rr_changes_act_at_once_during_release():
    # envelope.txt a and c: "The change takes effect immediately."
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x02)
    chip = struck(tone, f_number=0x40, block=0)
    chip.run(SAMPLE * 3)
    note(chip, 0, 0x40, 0, key=0)
    slow = levels(chip, C[0], 2000)[-1]
    write(chip, 0x07, 0x0C)
    fast = levels(chip, C[0], 200)[-1]
    assert fast - slow > 20
    write(chip, 0x20, 0x20)  # SUS on: rate 5
    assert levels(chip, C[0], 200)[-1] - fast < 2


@pytest.mark.parametrize("when", ("damp", "attack", "decay"))
def test_key_off_goes_to_release_from_any_state(when):
    # envelope.txt e: "changing KEY-ON->OFF always goes to the (2nd or only)
    # release phase", from damp, attack and decay as well.
    tone = (0x00, 0x21, 0x3F, 0x00, 0x00, 0x51, 0x00, 0x0D)
    chip = struck(tone, f_number=0x40, block=0)
    if when == "damp":
        chip.run(SAMPLE)
        chip.level[C[0]] = 40
        chip.state[C[0]] = 0
        chip.run(SAMPLE * 8)
    elif when == "attack":
        chip.run(SAMPLE * 3000)
        assert chip.state[C[0]] == 1
    else:
        chip.run(SAMPLE * 40_000)
        assert chip.state[C[0]] == 2
    chip.take_outputs()
    note(chip, 0, 0x40, 0, key=0)
    assert levels(chip, C[0], 600)[-1] == 127


def test_a_modulator_has_no_release():
    # envelope.txt, "Modulator-envelope has no release phase?": at key-off "The
    # carrier envelope starts to decay, but the modulation depth remains the
    # same!"; and for EG_TYPE=0 it "does not go to the (2nd) release phase".
    tone = (0x21, 0x21, 0x00, 0x00, 0xF4, 0xF4, 0x2F, 0x2F)
    chip = tone_chip(tone)
    chip.run(SAMPLE * 3000)
    assert chip.level[M[0]] == chip.level[C[0]] == 16
    note(chip, 0, 0x100, 4, key=0)
    chip.run(SAMPLE * 500)
    assert chip.level[M[0]] == 16 and chip.level[C[0]] == 127
    # A percussive modulator goes on at its own RR, not at rate 7.
    tone = (0x01, 0x21, 0x00, 0x00, 0xF4, 0xF4, 0x22, 0x2F)
    chip = tone_chip(tone)
    chip.run(SAMPLE * 3000)
    before = chip.level[M[0]]
    note(chip, 0, 0x100, 4, key=0)
    chip.run(SAMPLE * 3000)
    assert 0 < chip.level[M[0]] - before < 4


# Key scale of rate, sl-ksr.txt: R, KSR, BLOCK, F-number bit 8 -> rate; each
# line "confirmed" on the chip (a to j).
CONFIRMED_RATES = [(4, 0, 4, 0, 18), (4, 0, 4, 1, 18), (4, 1, 1, 0, 18), (3, 1, 3, 0, 18),
                   (2, 1, 5, 0, 18), (4, 1, 4, 1, 25), (4, 1, 4, 0, 24), (4, 1, 3, 0, 22),
                   (3, 1, 5, 0, 22), (2, 0, 5, 0, 10)]  # fmt: skip


@pytest.mark.parametrize("rate_field, ksr, block, msb, rate", CONFIRMED_RATES)
def test_confirmed_effective_rates(rate_field, ksr, block, msb, rate):
    # "a narrow step takes 512 samples ... 13 - log2(512) = 4 ... an effective
    # rate of 4*4+2 = 18"; "wide, narrow, narrow" when the low bits are 2.
    tone = (0x00, 0x20 | ksr << 4 | 0x01, 0x3F, 0x00, 0x00, 0xF0 | rate_field, 0x00, 0xF0)
    chip = struck(tone, f_number=msb << 8 | 0x40, block=block)
    chip.run(SAMPLE)
    narrow = 1 << (13 - (rate >> 2))
    trace = levels(chip, C[0], narrow * 20)
    lengths = [length for _, length in runs(trace)[2:-1]]
    pattern = {0: [2], 1: [2, 2, 2, 1, 1], 2: [2, 1, 1]}[rate & 3]
    size = len(pattern)
    expected = [narrow * each for each in pattern * 4]
    assert any(lengths[offset : offset + size * 2] == expected[: size * 2] for offset in range(size))


def test_key_scale_level_codes():
    # ksl.txt: measured for "KSL=1, 2 and 3", an "exact match" with Yamaha's
    # table read as 1.5, 3 and 6 dB per octave in that order (contradiction C3).
    def attenuation(code: int) -> int:
        tone = (0x21, 0x21, 0x3F, code << 6, 0x00, 0xF0, 0x00, 0x00)
        chip = tone_chip(tone, f_number=0x1E0, block=7)
        peak = max(melody(chip, 300))
        return next(steps for steps in range(128) if carrier_peak(steps) == peak)

    # Yamaha's cell for octave 7, F-number top bits 15: 21 dB at 3 dB/oct, which
    # is 56 envelope steps of 0.375 dB; half and double for the other settings.
    assert [attenuation(code) for code in (0, 1, 2)] == [0, 28, 56]
    assert max(melody(tone_chip((0x21, 0x21, 0x3F, 0xC0, 0, 0xF0, 0, 0), 0x1E0, 7), 300)) == carrier_peak(112)


# ------------------------------------------------------------ tremolo (10)


def test_tremolo_segment_lengths():
    # am.txt: "(only) 14 different levels (0..13)"; "top: 960 samples (15 x 64),
    # middle: 512 samples (8 x 64), bottom: 192 samples (3 x 64)".
    chip = tone_chip((0x21, 0xA1, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00))
    seen = []
    for _ in range(13_440 * 2 + 2000):
        chip.run(SAMPLE)
        seen.append(chip.tremolo)
    chip.take_outputs()
    segments = runs(seen)[1:-1]
    assert {value for value, _ in segments} == set(range(14))
    for value, length in segments:
        assert length == (960 if value == 0 else 192 if value == 13 else 512)
    cycle = [value for value, _ in segments[:26]]
    assert sorted(cycle) == sorted([0, 13] + 2 * list(range(1, 13)))


def test_tremolo_attenuates_by_envelope_steps():
    # am.txt: the extra term is "16 * am", am 0 to 13: one envelope step each;
    # the measured swing is 255 down to "approximately ... +144".
    chip = tone_chip((0x21, 0xA1, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00), f_number=256, block=4)
    out = melody(chip, 13_440)
    peaks = {max(out[i : i + 128]) for i in range(0, 13_440 - 128, 64)}
    assert max(peaks) == 255 and min(peaks) == carrier_peak(13) == 145


# ------------------------------------------------------ rhythm (spec 11)

# lfsr.txt: 120 consecutive snare samples at F-number 0, "sample value 255 to '0'
# and all other values to '1'".
SNARE_BITS = (
    "1101010010" "0111011001" "0011010111" "0101110000" "1011010001" "1001110010"
    "0110100101" "1000011101" "1001010001" "0111000111" "0001101111" "1010010001"
)  # fmt: skip

# rhythm.md, the 2020 update: the noise bit as seen by the hi-hat and by the
# snare in the same 50 samples.
HI_HAT_BITS = "000110001101001000010010001100" "11000010110011001101"
SNARE_BITS_50 = "100100011000001101110001010011" "00101101111111010011"


def noise_as_used(chip: OPLL, count: int) -> tuple[list[int], list[int]]:
    """The noise bit at the hi-hat's slot and at the snare's, sample by sample."""
    hi_hat, snare = [], []
    assert chip.slot == 0 and chip.clock_phase == 0
    for _ in range(count):
        for slot in range(18):
            if slot == 13:
                hi_hat.append(chip.noise & 1)
            elif slot == 16:
                snare.append(chip.noise & 1)
            chip.run(4)
    chip.take_outputs()
    return hi_hat, snare


def solve_noise_state(observed) -> int | None:
    """The 23-bit register value at slot 0 that gives the observed bits, by
    elimination over GF(2), or None if no value does. ``observed`` is a list of
    (steps from slot 0 of the first sample, bit)."""
    masks = [1 << stage for stage in range(23)]  # each stage as a sum of the unknowns
    rows = []
    last = max(steps for steps, _ in observed)
    wanted = dict(observed)
    for step in range(last + 1):
        if step in wanted:
            rows.append([masks[0], wanted[step]])
        masks = masks[1:] + [masks[0] ^ masks[14]]
    pivots: dict[int, list[int]] = {}
    for mask, bit in rows:
        for pivot, (pivot_mask, pivot_bit) in pivots.items():
            if mask >> pivot & 1:
                mask ^= pivot_mask
                bit ^= pivot_bit
        if mask == 0:
            if bit:
                return None
            continue
        pivot = mask.bit_length() - 1
        for other in pivots.values():
            if other[0] >> pivot & 1:
                other[0] ^= mask
                other[1] ^= bit
        pivots[pivot] = [mask, bit]
    if len(pivots) < 23:
        return None
    return sum(bit << pivot for pivot, (_, bit) in pivots.items())


def test_the_snare_noise_seen_once_a_sample():
    # lfsr.txt: the Berlekamp-Massey algorithm on those 120 bits gives the
    # register with taps 1, 8, 9 and 23, period 8,388,607; "if I take only the 60
    # first samples ... the resulting LFSR can then correctly predict the
    # continuation".
    printed = [int(bit) for bit in SNARE_BITS]
    for bits in (printed, noise_as_used(OPLL(YM2413), 400)[1]):
        assert all(
            bits[n] == bits[n - 1] ^ bits[n - 8] ^ bits[n - 9] ^ bits[n - 23]
            for n in range(23, len(bits))
        )
    # ...and the printed bits are a stretch of the chip model's own sequence.
    state = solve_noise_state([(16 + 18 * n, bit) for n, bit in enumerate(printed)])
    assert state
    chip = OPLL(YM2413)
    chip.noise = state
    assert noise_as_used(chip, 120)[1] == printed


def test_the_register_steps_once_a_slot():
    # rhythm.md, 2020 update: "if we iterate the HH-state 3 times we end up in
    # the SD-state"; "HH gets calculated in slot 13 and SD in slot 16"; 30 bits
    # fixed the state and "the next 20 samples matched perfectly".
    hi_hat = [int(bit) for bit in HI_HAT_BITS]
    snare = [int(bit) for bit in SNARE_BITS_50]
    state = solve_noise_state([(13 + 18 * n, bit) for n, bit in enumerate(hi_hat[:30])])
    assert state
    chip = OPLL(YM2413)
    chip.noise = state
    assert noise_as_used(chip, 50) == (hi_hat, snare)
    # Stepped once a sample instead, no register value gives both.
    assert hi_hat != snare


def rhythm_chip(keys: int, f7=0x150, block7=2, f8=0x1C0, block8=0) -> OPLL:
    chip = OPLL(YM2413)
    write(chip, 0x16, 0x20)
    write(chip, 0x26, 0x05)
    note(chip, 7, f7, block7, key=0)
    note(chip, 8, f8, block8, key=0)
    write(chip, 0x0E, 0x20)
    write(chip, 0x0E, 0x20 | keys)
    return chip


def test_the_snare_at_f_number_0_shows_the_noise_alone():
    # lfsr.txt: with F-number 0, "all samples have the same sign" and the signal
    # toggles between zero and a peak that follows the envelope.
    chip = rhythm_chip(0x08, f7=0, block7=0)
    chip.run(SAMPLE * 40)
    chip.take_outputs()
    bits, heard = [], []
    for _ in range(300):
        for slot in range(18):
            if slot == 16:
                bits.append(chip.noise & 1)
            chip.run(4)
        heard.append(chip.take_outputs()[0][1])
    fresh = [sample[16][1] for sample in words(rhythm_chip(0x08, f7=0, block7=0), 300)]
    assert all(word >= 0 for word in fresh) and max(fresh) > 100
    assert len(heard) == 300 and any(bits)


def test_the_snare_table():
    # rhythm.md, "Snare drum": noise 0 gives +0 or the negative peak, noise 1
    # the positive peak or -0, by one bit of the phase; "+max and -max appear
    # diagonally". (Which column goes with which phase is U6.)
    chip = rhythm_chip(0x08, f7=0x100, block7=1)
    chip.run(SAMPLE * 40)
    chip.take_outputs()
    seen = set()
    for _ in range(4000):
        noise = phase_bit = 0
        for slot in range(18):
            if slot == 16:
                noise = chip.noise & 1
            chip.run(4)
            if slot == 16:
                phase_bit = (chip.phase[16] >> 17) & 1
        word = chip.take_outputs()[0][1]
        fresh = word  # the sum holds the fresh word and a copy of the previous one
        seen.add((noise, phase_bit))
        del fresh
    assert seen == {(0, 0), (0, 1), (1, 0), (1, 1)}
    kinds = set()
    chip = rhythm_chip(0x08, f7=0x100, block7=1)
    chip.run(SAMPLE * 40)
    chip.take_outputs()
    for _ in range(3000):
        for slot in range(18):
            if slot == 16:
                noise = chip.noise & 1
            chip.run(4)
        phase_bit = (chip.phase[16] >> 17) & 1
        word = chip.held[16]
        kind = "+0" if word == 0 else "-0" if word == -1 else "+peak" if word > 0 else "-peak"
        kinds.add((noise, phase_bit, kind))
    chip.take_outputs()
    assert kinds == {(0, 0, "+0"), (0, 1, "-peak"), (1, 0, "+peak"), (1, 1, "-0")}


def test_the_bass_drum_is_the_user_tone_with_the_measured_settings():
    # rhythm.md, "Base Drum": the user tone 01 01 18 0F DF F8 6A 6D, played
    # "'simultaneously'" at F-number $1FF, block 0, is "a pretty good match"; "the
    # values shown in the above table gave the best result". In the model the two
    # are the same words.
    chip = OPLL(YM2413)
    user_tone(chip, (0x01, 0x01, 0x18, 0x0F, 0xDF, 0xF8, 0x6A, 0x6D))
    write(chip, 0x36, 0x03)
    write(chip, 0x35, 0x03)
    for channel in (5, 6):
        note(chip, channel, 0x1FF, 0, key=0)
    write(chip, 0x0E, 0x20)
    chip.write(0, 0x0E)
    chip.write(1, 0x30)
    chip.write(0, 0x25)
    chip.write(1, 0x11)
    trace = words(chip, 4000)
    drum = [sample[15][1] for sample in trace]
    tone = [sample[11][0] for sample in trace]
    assert drum == tone and max(drum) > 100


def test_the_tom_is_a_plain_sine_at_channel_8s_pitch():
    # rhythm.md, "Tom tom": "a simple sine wave that's varying in amplitude";
    # "the frequency of the TOM waveform varies with the settings from registers
    # 0x18 and 0x28".
    for f_number, block in ((0x100, 3), (0x100, 4)):
        chip = rhythm_chip(0x04, f8=f_number, block8=block)
        tom = [sample[14][1] for sample in words(chip, 2048)]
        crossings = sum(1 for a, b in zip(tom, tom[1:], strict=False) if a < 0 <= b)
        # the ROM row's multiplier is 5 (byte $00 = $05)
        assert abs(crossings - 2048 * 5 * ((f_number << block) >> 1) / (1 << 18)) <= 1
        assert max(tom) > 200


def test_the_top_cymbal_is_two_peaks_and_reaches_full_scale():
    # rhythm.md, "Top cymbal": "the amplitude only seems to take on two distinct
    # values (maximum positive or maximum negative)"; "at the end of the attack
    # phase the signal does span the full -255..+255 range"; "both the frequency
    # settings for channel 7 ... and for channel 8 ... influence how the TCY
    # waveform looks".
    chip = rhythm_chip(0x02, f7=0x100, block7=3, f8=0x100, block8=4)
    write(chip, 0x38, 0x00)
    takes = {}
    for name, f7 in (("a", 0x100), ("b", 0x180)):
        chip = rhythm_chip(0x02, f7=f7, block7=3, f8=0x100, block8=4)
        takes[name] = [sample[17][1] for sample in words(chip, 3000)]
    cymbal = takes["a"]
    assert max(cymbal) == 255 and min(cymbal) == -256
    held_level = [word for word in cymbal[100:160]]
    assert len({abs(word + (word < 0)) for word in held_level}) <= 3  # one level at a time
    assert takes["a"] != takes["b"]
    other = [sample[17][1] for sample in words(rhythm_chip(0x02, 0x100, 3, 0x140, 4), 3000)]
    assert other != cymbal


def test_rhythm_keys_are_ored_with_the_channel_keys():
    # rhythm.md: "in rhythm mode _both_ the on/off bits in register 0x0E and the
    # bits in registers 0x26-0x28 are taken into account. It's as-if the
    # 'corresponding' bits are OR'ed together." Loosely measured (marked TODO in
    # the source): PROVISIONAL in the core (T9).
    chip = rhythm_chip(0)
    assert set(rhythm(chip, 500)) == {0}
    note(chip, 8, 0x1C0, 0, key=1)
    assert max(rhythm(chip, 500)) > 50


def test_aliases_of_the_channel_registers():
    # ksl.txt: "a write to register R#19 has the same effect as a write to R#10",
    # $19-$1F, $29-$2F and $39-$3F to $10-$16, $20-$26 and $30-$36.
    for alias in (*range(0x19, 0x20), *range(0x29, 0x30), *range(0x39, 0x40)):
        chip = OPLL(YM2413)
        write(chip, alias, 0x15)
        assert chip.registers[alias - 9] == 0x15
        assert sum(chip.registers) == 0x15
    chip = tone_chip(PLAIN_SINE, key=0)
    write(chip, 0x29, 0x18)
    assert max(melody(chip, 600)) == 255
