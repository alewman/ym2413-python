"""The provisional defaults, one labelled test each.

These are not judges. Each pins a value that no source above an emulator settles
(the hand-off brief's T1 to T15, and the spec's unknowns U20, U22, U23, U24), so
that changing one is a deliberate act: a measurement or a document that settles
it changes the value, this test, and the spec's entry together. Every docstring
starts with PROVISIONAL and names the item.
"""

from __future__ import annotations

import itertools

from helpers import (
    PLAIN_SINE,
    SAMPLE,
    C,
    M,
    levels,
    melody,
    note,
    press,
    reference_value,
    struck,
    tone_chip,
    user_tone,
    words,
    write,
)
from test_measured import rhythm_chip, two_operator_reference

from ym2413_python import DS1001, OPLL, YM2413
from ym2413_python.variants import VIBRATO_OFFSETS, YM2413_VOICES

# ------------------------------------------------------------- data defaults


def test_t1_the_ym2413_voices_are_emu2413s_hand_tuned_table():
    """PROVISIONAL, T1 (U1, C9): emulator tier, not a dump. Row 1 (Violin) and
    row 15 (Electric Guitar) as emu2413 v1.6.4 has them."""
    assert YM2413.voices is YM2413_VOICES and len(YM2413.voices) == 15
    assert YM2413.voices[0] == (0x71, 0x61, 0x1E, 0x17, 0xD0, 0x78, 0x00, 0x17)
    assert YM2413.voices[14] == (0x41, 0x41, 0x89, 0x03, 0xF1, 0xE4, 0xC0, 0x13)


def test_t2_the_snare_byte_is_68_on_both_variants():
    """PROVISIONAL, T2 (C4): $68, the only measured value; S6 and ymfm say $48
    for the YM2413."""
    assert YM2413.snare_last_byte == DS1001.snare_last_byte == 0x68


def test_t3_vibrato_below_the_top_row_follows_the_top_rows_rule():
    """PROVISIONAL, T3 (U4): emulator tier. Peak = the F-number's top three bits,
    half-way = peak >> 1, mirrored negative. Only the top row was measured."""
    assert VIBRATO_OFFSETS[7] == (0, 3, 7, 3, 0, -3, -7, -3)
    assert VIBRATO_OFFSETS[4] == (0, 2, 4, 2, 0, -2, -4, -2)
    assert VIBRATO_OFFSETS[1] == (0, 0, 1, 0, 0, 0, -1, 0)
    assert VIBRATO_OFFSETS[0] == (0,) * 8
    assert YM2413.vibrato_offsets == DS1001.vibrato_offsets == VIBRATO_OFFSETS


def test_t4_the_ym2413s_test_register_is_the_vrc7s():
    """PROVISIONAL, T4 (U2): the four bits S6 gives for the VRC7, on the YM2413
    too (their effects are in test_community)."""
    assert YM2413.test_bits == DS1001.test_bits == 0x0F


# -------------------------------------------------------------------- reset


def test_t5_the_state_after_reset():
    """PROVISIONAL, T5 (U3): every envelope at 127 with its key off; phases, the
    shared counter and both LFO positions 0; the noise register 1. The VRC7's
    reset leaves the vibrato position alone (that part tier 3, S6)."""
    for variant in (YM2413, DS1001):
        chip = tone_chip(PLAIN_SINE, variant=variant)
        chip.run(SAMPLE * 3000)
        chip.take_outputs()
        vibrato = chip.vibrato_time
        chip.reset()
        assert chip.level == [127] * 18 and chip.key == [0] * 18
        assert chip.phase == [0] * 18
        assert chip.counter == chip.tremolo_time == 0
        assert chip.noise == 1
        assert chip.vibrato_time == (0 if variant is YM2413 else vibrato)


# ---------------------------------------------------------------- the output


def test_t6_each_percussion_word_counts_twice_in_the_rhythm_sum():
    """PROVISIONAL, T6: a sample's rhythm number is the sum of the rhythm pin's
    eighteen words, so each percussion word is in it twice (spec 11.12): once
    fresh and once as the copy in the next sample."""
    chip = rhythm_chip(0x04, f8=0x100, block8=4)  # the tom alone
    chip.run(SAMPLE * 50)
    chip.take_outputs()
    chip.trace = []
    chip.run(SAMPLE * 200)
    trace, chip.trace = chip.trace, None
    sums = [pair[1] for pair in chip.take_outputs()]
    for sample, total, previous in zip(trace[1:], sums[1:], trace[:-1], strict=True):
        tom, copy = sample[14][1], sample[1][1]
        assert copy == previous[14][1]
        assert total == (tom + (tom < 0)) + (copy + (copy < 0))


def test_t7_a_write_acts_from_the_slot_it_falls_in():
    """PROVISIONAL, T7 (U9): a data write acts from the next slot boundary, so a
    write two clocks into slot 3 changes slot 3's word in that same sample."""
    quiet, loud = (
        tone_chip(PLAIN_SINE, f_number=256, block=1),
        tone_chip(PLAIN_SINE, f_number=256, block=1),
    )
    loud.run(SAMPLE * 10)
    quiet.run(SAMPLE * 10)
    for chip in (quiet, loud):
        chip.take_outputs()
        chip.trace = []
        chip.write(0, 0x30)
        chip.run(4 * 3 + 2)  # slots 0 to 2 done, two clocks into slot 3
    quiet.write(1, 0x0F)  # volume 15
    for chip in (quiet, loud):
        chip.run(SAMPLE - (4 * 3 + 2))
    assert quiet.trace[0][C[0]][0] != loud.trace[0][C[0]][0]
    assert abs(quiet.trace[0][C[0]][0]) <= 2


def test_t7_unmapped_addresses_are_ignored():
    """PROVISIONAL, T7 (spec 4.4): $08-$0D and $40 up change nothing."""
    chip = OPLL(YM2413)
    for address in (*range(0x08, 0x0E), 0x40, 0x7F, 0xFF):
        write(chip, address, 0xFF)
    assert not any(chip.registers)


# --------------------------------------------------------------- percussion


def test_t8_the_cymbals_bit_is_emu2413s_form():
    """PROVISIONAL, T8 (U5): emulator tier. (c85 = c83) and (m77 = m72) and
    (c85 = m73), on bits of the ten-bit phases of C8 and M7; positive peak when
    true. Read as each sound's phases stand at its own slot."""
    chip = rhythm_chip(0x02, f7=0x123, block7=4, f8=0x1A7, block8=5)
    chip.run(SAMPLE * 200)
    chip.take_outputs()
    for _ in range(500):
        chip.trace = []
        chip.run(SAMPLE)
        word = chip.trace[0][17][1]
        chip.trace = None
        chip.take_outputs()
        m7, c8 = chip.phase[13] >> 9, chip.phase[17] >> 9
        bit = (
            ((c8 >> 5) & 1 == (c8 >> 3) & 1)
            and ((m7 >> 7) & 1 == (m7 >> 2) & 1)
            and ((c8 >> 5) & 1 == (m7 >> 3) & 1)
        )
        assert (word >= 0) == bit or word in (0, -1)


def test_t9_a_channel_key_bit_keys_its_rhythm_sounds():
    """PROVISIONAL, T9 (U7): in rhythm mode each sound is keyed by its $0E bit OR
    its channel's key bit; $28's key starts both the tom and the top cymbal."""
    chip = rhythm_chip(0)
    note(chip, 8, 0x1C0, 0, key=1)
    chip.run(SAMPLE * 50)
    chip.take_outputs()
    assert chip.key[14] == chip.key[17] == 1
    assert chip.key[13] == chip.key[16] == 0


def test_t10_switching_rhythm_mode_keeps_envelopes_and_phases():
    """PROVISIONAL, T10 (U8): only the instrument rows and routing change."""
    chip = OPLL(YM2413)
    user_tone(chip, PLAIN_SINE)
    note(chip, 7, 0x150, 3)
    chip.run(SAMPLE * 500)
    chip.take_outputs()
    before = (list(chip.level[12:18]), list(chip.state[12:18]))
    chip.write(0, 0x0E)
    chip.write(1, 0x20)
    assert (list(chip.level[12:18]), list(chip.state[12:18])) == before


def test_t11_the_carrier_hears_the_modulators_previous_sample():
    """PROVISIONAL, T11 (C7, U21): the carrier is moved by the modulator's output
    of the sample before. The same-sample reading gives other words."""
    tone = (0x20, 0x20, 8, 0x00, 0xF0, 0xF0, 0x00, 0x00)
    got = [sample[C[0]][0] for sample in words(struck(tone, f_number=0x40, block=0), 2000)]
    assert got == two_operator_reference(8, 0, 2000, 32)
    same_sample, phase = [], 0
    for _ in range(2000):
        phase += 32
        modulator = reference_value(phase >> 9, 16)
        same_sample.append(reference_value((phase >> 9) + 2 * modulator, 0) >> 3)
    assert got != same_sample


def test_t12_hi_hat_and_tom_levels_are_eight_steps_a_volume_step_no_tl():
    """PROVISIONAL, T12 (U11): base attenuation 8 x the sound's own nibble, no
    total level, on the two single-operator sounds on modulator slots."""
    chip = rhythm_chip(0)
    write(chip, 0x37, 0x50)  # hi-hat 5, snare 0
    write(chip, 0x38, 0x30)  # tom 3, cymbal 0
    assert chip.base[13] == 40 and chip.base[14] == 24
    write(chip, 0x02, 0x3F)  # the user tone's total level plays no part
    assert chip.base[13] == 40 and chip.base[14] == 24


def test_t13_attack_from_125_and_a_step_past_the_bottom():
    """PROVISIONAL, T13 (U12, U14): the attack formula as it stands from 125
    (125 - 7 - 1 = 117); a +2 step from 126 stops at 127."""
    chip = struck((0x00, 0x21, 0x3F, 0x00, 0x00, 0xC0, 0x00, 0x0F), f_number=0x40, block=0)
    chip.run(SAMPLE)
    chip.take_outputs()
    chip.state[C[0]], chip.level[C[0]] = 1, 125
    assert levels(chip, C[0], 1) == [117]  # rate 48: every sample, n = 4
    chip = tone_chip((0x00, 0x31, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x0F), f_number=0x100, block=7)
    note(chip, 0, 0x100, 7, key=0)  # release at RR 15 with KSR: rate 63, +2
    chip.level[C[0]] = 126
    assert levels(chip, C[0], 3) == [127, 127, 127]


def test_t14_modulators_are_damped_at_key_on():
    """PROVISIONAL, T14 (U13): a modulator enters damp at key-on, as a carrier
    does."""
    tone = (0x21, 0x21, 0x00, 0x00, 0xF0, 0xF0, 0x00, 0x0F)
    chip = tone_chip(tone)
    chip.run(SAMPLE * 100)
    note(chip, 0, 0x100, 4, key=0)
    chip.run(SAMPLE * 100)
    chip.take_outputs()
    assert chip.level[M[0]] == 0  # held through key-off (spec 8.23, measured)
    press(chip, 0, 0x100, 4)
    chip.run(SAMPLE * 3)
    chip.take_outputs()
    assert chip.state[M[0]] == 0 and 0 < chip.level[M[0]] < 124


def test_t15_the_ds1001s_channels_6_to_8_take_writes_and_stay_silent():
    """PROVISIONAL, T15 (U16): registers accepted, nothing output."""
    chip = OPLL(DS1001)
    user_tone(chip, PLAIN_SINE)
    note(chip, 7, 0x100, 4)
    assert chip.registers[0x17] == 0x00 and chip.registers[0x27] == 0x19
    assert set(melody(chip, 1000)) == {0}


# ----------------------------------------------------------------- unknowns


def test_u20_the_damp_end_sample_already_sounds():
    """PROVISIONAL, U20: the phases restart, the level of an instant attack goes
    to 0, and the sample is computed, all in the sample in which damp ends."""
    chip = struck((0x00, 0x24, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x00), f_number=256, block=7)
    assert melody(chip, 1) == [255]  # a quarter-rate tone: first sample on the peak


def test_u22_the_hi_hats_four_phases():
    """PROVISIONAL, U22: emulator tier. Phases $2D0, $234, $034, $0D0 for
    (cymbal bit, noise) = (0, 0), (0, 1), (1, 0), (1, 1)."""
    assert YM2413.hi_hat_phases == (0x2D0, 0x234, 0x034, 0x0D0)
    chip = rhythm_chip(0x01, f7=0x123, block7=4, f8=0x1A7, block8=5)
    chip.run(SAMPLE * 300)
    chip.take_outputs()
    seen = set()
    for _ in range(400):
        chip.trace = []
        for slot in range(18):
            if slot == 13:
                noise = chip.noise & 1
            chip.run(4)
            if slot == 13:
                m7, c8 = chip.phase[13] >> 9, chip.phase[17] >> 9
                level = chip.level[13]
        word = chip.trace[0][13][1]
        chip.trace = None
        chip.take_outputs()
        bit = int(
            ((c8 >> 5) & 1 == (c8 >> 3) & 1)
            and ((m7 >> 7) & 1 == (m7 >> 2) & 1)
            and ((c8 >> 5) & 1 == (m7 >> 3) & 1)
        )
        phase = YM2413.hi_hat_phases[2 * bit + noise]
        assert word == (reference_value(phase, chip.base[13] + level) >> 3 if level < 124 else 0)
        seen.add((bit, noise))
    assert len(seen) >= 3


def test_u23_counter_bits_2_and_3_choose_the_faster_samples():
    """PROVISIONAL, U23: for decay rates 52 to 59, counter bits 2 and 3 pick an
    even place of the rate's pattern; at rate 53 (pattern 0 1 0 1 1 1 0 1, even
    places 0 0 1 0) samples 8 to 11 of 16 go at the faster speed (one level),
    the others at half speed."""
    chip = struck((0x00, 0x01, 0x3F, 0x00, 0x00, 0xF0, 0x00, 0x0D), f_number=0x40, block=2)
    chip.run(SAMPLE)
    chip.take_outputs()
    chip.counter = 0
    trace = [chip.level[C[0]], *levels(chip, C[0], 64)]
    for count, (before, after) in enumerate(itertools.pairwise(trace), 1):
        expected = 1 if (count >> 2) & 3 == 2 else count & 1
        assert after - before == expected, count


def test_u24_negative_modulator_values_are_ones_complement_then_shifted():
    """PROVISIONAL, U24: a negative modulator value enters the carrier's phase as
    twice its one's complement form, and feedback shifts the sum arithmetically.
    A sign-and-size reading gives other words."""
    tone = (0x20, 0x20, 0, 5, 0xF0, 0xF0, 0x00, 0x00)
    got = [sample[C[0]][0] for sample in words(struck(tone, f_number=0x40, block=0), 4000)]
    assert got == two_operator_reference(0, 5, 4000, 32)
    out, previous, before, phase = [], 0, 0, 0
    for _ in range(4000):
        phase += 32
        fed = (previous + before) >> 3
        value = reference_value((phase >> 9) + fed, 0)
        before, previous = previous, (value if value >= 0 else value + 1)  # sign and size
        out.append(reference_value((phase >> 9) + 2 * before, 0) >> 3)
    assert got != out
