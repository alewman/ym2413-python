"""The contract: time, the port and the outputs."""

from __future__ import annotations

from ym2413_python import CLOCKS_PER_CYCLE, CYCLES_PER_SAMPLE, DS1001, OPLL, YM2413


def test_a_cycle_every_four_input_clocks() -> None:
    chip = OPLL()
    chip.run(3)
    assert chip.take_outputs() == []
    chip.run(1)
    assert len(chip.take_outputs()) == 1
    chip.run(CLOCKS_PER_CYCLE * CYCLES_PER_SAMPLE)
    assert len(chip.take_outputs()) == CYCLES_PER_SAMPLE
    assert chip.clock == 4 + 72


def test_silence_after_reset() -> None:
    chip = OPLL(YM2413)
    chip.run(72 * 100)
    # The NMOS DAC drives a silent slot's sign: 0 or 1 by the slot's word.
    assert {mo for mo, _ in chip.take_outputs()} <= {0, 1}


def play_note(variant) -> list[tuple[int, int]]:
    chip = OPLL(variant)
    for register, value in ((0x30, 0x10), (0x10, 0x81), (0x20, 0x19)):  # 440 Hz-ish
        chip.write(0, register)
        chip.run(12)
        chip.write(1, value)
        chip.run(84)
    chip.take_outputs()
    chip.run(72 * 3000)
    return chip.take_samples()


def test_a_note_sounds_on_mo_and_not_ro() -> None:
    samples = play_note(YM2413)
    assert len(samples) == 3000
    assert max(abs(mo) for mo, _ in samples) > 50
    # RO drives only each slot's sign (0 or 1) with rhythm mode off: no music.
    assert max(abs(ro) for _, ro in samples) <= CYCLES_PER_SAMPLE


def test_the_vrc7_has_no_rhythm_pin() -> None:
    samples = play_note(DS1001)
    assert {ro for _, ro in samples} == {0}
    assert max(abs(mo) for mo, _ in samples) > 50


def test_a_write_lands_on_the_next_cycle_not_at_once() -> None:
    chip = OPLL()
    chip.write(0, 0x0F)
    assert chip.address == 0  # nothing until a cycle runs
    chip.run(CLOCKS_PER_CYCLE * 2)
    chip.write(1, 0x04)
    assert chip.test == 0
    chip.run(CLOCKS_PER_CYCLE * 2)
    assert chip.test == 0x04
