# SPDX-License-Identifier: MIT
"""Rung 0: the contract with the boards (docs/api.md, docs/validation.md).

Not a judge of the chip: these keep the core usable by sms-python and
famicom-python as api.md describes it.
"""

from __future__ import annotations

import dataclasses
import random

import pytest
from helpers import PLAIN_SINE, SAMPLE, melody, note, tone_chip, variant_id, write

import ym2413_python
from ym2413_python import CLOCKS_PER_CYCLE, CYCLES_PER_SAMPLE, DS1001, OPLL, YM2413, OPLLVariant

BOTH = (YM2413, DS1001)
PLAIN = (int, bool, type(None))


def random_stream(seed: int, writes: int = 400) -> list[tuple[int, int, int]]:
    """(input clocks to run first, port, byte), aimed at registers that exist."""
    rng = random.Random(seed)
    registers = [*range(0x08), 0x0E, 0x0F, *range(0x10, 0x19), *range(0x20, 0x29)]
    registers += [*range(0x30, 0x39)]
    stream = []
    for _ in range(writes):
        stream.append((rng.randrange(0, 40), 0, rng.choice(registers)))
        stream.append((rng.randrange(0, 2500), 1, rng.randrange(256)))
    return stream


def play(chip: OPLL, stream) -> None:
    for clocks, port, value in stream:
        chip.run(clocks)
        chip.write(port, value)


def test_the_names_api_md_lists_are_the_public_surface():
    assert sorted(ym2413_python.__all__) == sorted(
        ["OPLL", "OPLLVariant", "YM2413", "DS1001", "CLOCKS_PER_CYCLE", "CYCLES_PER_SAMPLE"]
    )
    for name in ("write", "run", "take_samples", "take_outputs", "reset"):
        assert callable(getattr(OPLL, name))


def test_the_time_constants():
    # api.md: the output rate is the clock divided by 72. Spec 2.2, 2.3.
    assert CLOCKS_PER_CYCLE == 4
    assert CYCLES_PER_SAMPLE == 18


def test_a_variant_is_a_frozen_record_of_plain_values():
    assert dataclasses.is_dataclass(OPLLVariant)
    with pytest.raises(dataclasses.FrozenInstanceError):
        YM2413.channels = 3  # type: ignore[misc]

    def plain(value) -> bool:
        if isinstance(value, tuple):
            return all(plain(item) for item in value)
        return isinstance(value, (int, str, bool))

    for variant in BOTH:
        for field in dataclasses.fields(variant):
            assert plain(getattr(variant, field.name)), field.name


@pytest.mark.parametrize("variant", BOTH, ids=variant_id)
def test_one_sample_per_72_clocks(variant):
    chip = OPLL(variant)
    chip.run(72 * 1000 + 71)
    assert len(chip.take_samples()) == 1000
    chip.run(1)
    assert len(chip.take_outputs()) == 1


@pytest.mark.parametrize("variant", BOTH, ids=variant_id)
def test_take_samples_is_the_sum_of_take_outputs(variant):
    a, b = OPLL(variant), OPLL(variant)
    stream = random_stream(5)
    play(a, stream)
    play(b, stream)
    pairs = a.take_outputs()
    assert pairs and any(pair != (0, 0) for pair in pairs)
    assert b.take_samples() == [melody + rhythm for melody, rhythm in pairs]
    assert a.take_outputs() == [] and b.take_samples() == []


@pytest.mark.parametrize("variant", BOTH, ids=variant_id)
@pytest.mark.parametrize("seed", range(4))
def test_run_a_then_b_equals_run_a_plus_b(variant, seed):
    # validation.md, rung 0: for any split, including splits inside a slot.
    stream = random_stream(seed)
    whole, pieces = OPLL(variant), OPLL(variant)
    rng = random.Random(100 + seed)
    for clocks, port, value in stream:
        whole.run(clocks)
        left = clocks
        while left:
            piece = min(left, rng.choice((1, 1, 2, 3, 5, 7, 72, 500)))
            pieces.run(piece)
            left -= piece
        whole.write(port, value)
        pieces.write(port, value)
    assert whole.take_outputs() == pieces.take_outputs()
    assert vars(whole) == vars(pieces)


def copy_state(source: OPLL, target: OPLL) -> None:
    """What a save-state walker does: copy every attribute but the configuration."""
    for name, value in vars(source).items():
        if name == "variant":
            continue
        if isinstance(value, (list, bytearray)):
            value = type(value)(value)
        setattr(target, name, value)


@pytest.mark.parametrize("variant", BOTH, ids=variant_id)
def test_state_is_plain_and_a_copy_continues_identically(variant):
    stream = random_stream(9)
    chip = OPLL(variant)
    play(chip, stream[:400])
    chip.take_outputs()
    for name, value in vars(chip).items():
        if name == "variant":
            continue
        assert isinstance(value, (*PLAIN, list, bytearray)), name
        if isinstance(value, list):
            assert all(isinstance(item, PLAIN) for item in value), name
    twin = OPLL(variant)
    copy_state(chip, twin)
    play(chip, stream[400:])
    play(twin, stream[400:])
    assert chip.take_outputs() == twin.take_outputs()
    assert vars(chip) == vars(twin)


@pytest.mark.parametrize("variant", BOTH, ids=variant_id)
def test_fewer_than_80_attributes(variant):
    # PyPy turns an instance with 80 or more attributes into a dict.
    assert len(vars(OPLL(variant))) < 80


def test_nothing_callable_is_kept_as_state():
    assert not any(callable(value) for value in vars(OPLL(YM2413)).values())


def test_the_ds1001_has_no_rhythm_side_and_no_channels_6_to_8():
    # api.md; spec 1, 11.14 (S6, tier 3); PROVISIONAL in its reach (T15).
    chip = OPLL(DS1001)
    write(chip, 0x0E, 0x3F)
    for channel in range(6, 9):
        write(chip, 0x30 + channel, 0x10)
        note(chip, channel, 0x150, 4)
    chip.run(SAMPLE * 3000)
    assert set(chip.take_outputs()) == {(0, 0)}
    # ...while channel 5 sounds.
    write(chip, 0x35, 0x10)
    note(chip, 5, 0x150, 4)
    pairs = [pair for pair in (chip.run(SAMPLE * 3000), chip.take_outputs())[1]]
    assert max(abs(melody) for melody, _ in pairs) > 100
    assert {rhythm for _, rhythm in pairs} == {0}


def test_reset_keeps_the_place_in_the_sample():
    # CHOICE: reset() does not move the chip's place in its 72-clock cycle, so a
    # board always gets one sample per 72 clocks.
    chip = tone_chip(PLAIN_SINE)
    chip.run(100)
    chip.reset()
    chip.run(72 * 10 - 100)
    assert len(chip.take_samples()) == 10


def test_a_sample_is_within_the_range_the_words_allow():
    # T6: nine melody words and ten percussion words of at most 255 each.
    chip = OPLL(YM2413)
    play(chip, random_stream(3))
    for melody_sum, rhythm_sum in chip.take_outputs():
        assert abs(melody_sum) <= 9 * 255 and abs(rhythm_sum) <= 10 * 255


def test_melody_helper_sees_a_note():
    assert max(melody(tone_chip(PLAIN_SINE), 600)) == 255
