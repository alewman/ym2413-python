# SPDX-License-Identifier: MIT
"""Rung 3: community documents whose accounts rest on hardware (tier 3).

S6 is the NESdev wiki's "VRC7 audio" page, pinned in famicom-python at
``reference/nesdev-wiki/VRC7_audio.wiki``; S9 is SMS Power's "YM2413" page, pinned
in sms-python at ``reference/smspower-wiki/YM2413.pmwiki``. Tests that parse a
pinned file skip when the sibling repository is absent (FAMICOM_PYTHON_DIR and
SMS_PYTHON_DIR name checkouts kept elsewhere). Every test here is tier
3: it proves agreement with the community's account, not that account. Where the
account is about the VRC7 and the core applies it to the YM2413 too, the YM2413
case is PROVISIONAL (T4) and says so.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
from helpers import (
    PLAIN_SINE,
    ROOT,
    SAMPLE,
    C,
    M,
    melody,
    note,
    rises,
    tone_chip,
    user_tone,
    words,
    write,
)

from ym2413_python import DS1001, OPLL, YM2413

# The boards' checkouts, beside this repository unless the environment names others.
FAMICOM_PYTHON = Path(os.environ.get("FAMICOM_PYTHON_DIR", ROOT.parent / "famicom-python"))
SMS_PYTHON = Path(os.environ.get("SMS_PYTHON_DIR", ROOT.parent / "sms-python"))
WIKI = FAMICOM_PYTHON / "reference" / "nesdev-wiki" / "VRC7_audio.wiki"
SMS_POWER = SMS_PYTHON / "reference" / "smspower-wiki" / "YM2413.pmwiki"

# One row of the wiki's tables: "  1 | 03 21 05 06 E8 81 42 27 | Buzzy Bell" or,
# for the drums, "    | 01 01 18 0F DF F8 6A 6D | Bass Drum".
ROW = re.compile(r"^\s*([0-9A-F]?)\s*\|\s*((?:[0-9A-F]{2}\s+){7}[0-9A-F]{2})\s*\|\s*(.+?)\s*$")


def wiki_rows() -> tuple[dict[int, tuple[int, ...]], list[tuple[int, ...]]]:
    if not WIKI.exists():
        pytest.skip(f"{WIKI} is absent (no famicom-python checkout; see FAMICOM_PYTHON_DIR)")
    voices: dict[int, tuple[int, ...]] = {}
    drums: list[tuple[int, ...]] = []
    for line in WIKI.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if not match:
            continue
        row = tuple(int(byte, 16) for byte in match.group(2).split())
        if row == tuple(range(8)):
            continue  # the column heads "00 01 ... 07"
        if match.group(1):
            voices[int(match.group(1), 16)] = row
        else:
            drums.append(row)
    return voices, drums


# ------------------------------------------------------ the DS1001's ROM (S6)


def test_the_ds1001_voices_are_the_wikis_read_out():
    """Tier 3. S6, "Internal patch set": "Exact values for the fixed patch were
    dumped using the VRC7 rewired into a debug mode". Spec 5.5."""
    voices, _ = wiki_rows()
    assert sorted(voices) == list(range(1, 16))
    assert DS1001.voices == tuple(voices[n] for n in range(1, 16))


def test_the_percussion_rows_are_the_wikis_drum_rows():
    """Tier 3. S6: "The VRC7 instrument ROM dump also shows 3 drum patches",
    equal to S4's fits on a YM2413 (spec 5.6; snare byte $68 is C4, T2)."""
    _, drums = wiki_rows()
    assert len(drums) == 3
    assert DS1001.percussion == tuple(drums)
    assert YM2413.percussion == tuple(drums)  # T2: $68 on both


@pytest.mark.parametrize("variant", (YM2413, DS1001), ids=lambda v: v.name)
@pytest.mark.parametrize("voice", range(1, 16))
def test_a_rom_voice_plays_as_its_row_loaded_as_the_user_tone(variant, voice):
    """Tier 3 (S6: "these are hardwired ... instrument $0 ... can be controlled by
    registers $00-$07", the same eight-byte layout); spec 5.1."""
    row = variant.voices[voice - 1]
    from_rom = OPLL(variant)
    user_tone(from_rom, row)  # the same writes on both chips, so they keep in step
    write(from_rom, 0x30, voice << 4)
    note(from_rom, 0, 0x120, 4)
    from_user = OPLL(variant)
    user_tone(from_user, row)
    write(from_user, 0x30, 0x00)
    note(from_user, 0, 0x120, 4)
    assert melody(from_rom, 3000) == melody(from_user, 3000)


# ------------------------------------------- six channels, no rhythm (S6)


def test_the_ds1001_sounds_six_channels_and_never_the_rest():
    """Tier 3. S6: "6 channels of 2-operator FM"; the rhythm bit "is treated as
    though it were always enabled ... The VRC7 has no rhythm DAC, so the 5 rhythm
    channels are always inaudible". T15 for what the registers of channels 6 to
    8 do (accepted, silent)."""
    chip = OPLL(DS1001)
    user_tone(chip, PLAIN_SINE)
    for channel in range(9):
        note(chip, channel, 0x100, 4)
    write(chip, 0x0E, 0x3F)  # every rhythm key, and the mode bit
    trace = words(chip, 2000)
    for slot in range(18):
        heard = {sample[slot] for sample in trace}
        if slot in (C[0], C[1], C[2], C[3], C[4], C[5]):
            assert max(melody for melody, _ in heard) > 200
        else:
            assert heard == {(0, 0)}


# ----------------------------------------------------- the reset bit (S6, S7)


def test_the_vrc7_reset_clears_registers_and_tremolo_not_vibrato():
    """Tier 3. S6, "Audio Reset ($E000)": the bit will "clear its registers
    (including tremolo LFO state, but not including vibrato LFO state)". The
    board calls ``reset()`` for it; spec 14.2."""
    chip = tone_chip(PLAIN_SINE, variant=DS1001)
    chip.run(SAMPLE * 5000)
    chip.take_outputs()
    vibrato, tremolo = chip.vibrato_time, chip.tremolo_time
    assert vibrato and tremolo
    chip.reset()
    assert not any(chip.registers)
    assert chip.tremolo_time == 0
    assert chip.vibrato_time == vibrato


# --------------------------------------------------- the test register (S6)

BOTH = pytest.mark.parametrize("variant", (DS1001, YM2413), ids=lambda v: v.name)


@BOTH
def test_test_bit_0_forces_full_volume_while_the_envelopes_run(variant):
    """Tier 3 on the DS1001; PROVISIONAL on the YM2413 (T4). S6: "Bit 0: The
    envelope generators are replaced with constant 0 output (full volume) ...
    The envelopes are still running while their output is overridden"."""
    chip = tone_chip(PLAIN_SINE, variant=variant, key=0)  # released: level 127
    assert max(melody(chip, 600)) == 0
    write(chip, 0x0F, 0x01)
    assert max(melody(chip, 600)) == 255
    assert chip.level[C[0]] == 127  # the envelope itself is untouched
    write(chip, 0x0F, 0x00)
    assert max(melody(chip, 600)) == 0


@BOTH
def test_test_bit_1_holds_both_lfos_at_zero(variant):
    """Tier 3 / T4. S6: "Bit 1: Hold LFO phase at zero. This halts, disables, and
    resets both the tremolo and vibrato LFO"."""
    chip = tone_chip(PLAIN_SINE, variant=variant)
    chip.run(SAMPLE * 3000)
    write(chip, 0x0F, 0x02)
    chip.run(SAMPLE * 3000)
    chip.take_outputs()
    assert chip.tremolo_time == chip.vibrato_time == chip.tremolo == 0


@BOTH
def test_test_bit_2_holds_every_phase_at_zero_and_silences_a_carrier(variant):
    """Tier 3 / T4. S6: "Bit 2: Holds and resets waveform phase to zero. The
    envelopes are not halted, though the output will be silent"."""
    chip = tone_chip(PLAIN_SINE, variant=variant)
    write(chip, 0x0F, 0x04)
    trace = words(chip, 600)
    assert {sample[C[0]][0] for sample in trace} == {0}
    assert chip.phase[C[0]] == chip.phase[M[0]] == 0


@pytest.mark.xfail(
    strict=True,
    reason=(
        "OPEN, not fixed: S6 says the output is silent with bit 2 set. With a "
        "sounding modulator the core's carrier is moved by the modulator's output "
        "at phase 0, which is not zero (the sine table has no zero, spec 6.3), so "
        "a small word is heard. No document says how the chip avoids it."
    ),
)
def test_test_bit_2_silences_a_modulated_carrier_too():
    """Tier 3. As above, with the modulator at full level."""
    chip = tone_chip((0x21, 0x21, 0x00, 0x00, 0xF0, 0xF0, 0x00, 0x00), variant=DS1001)
    write(chip, 0x0F, 0x04)
    assert {sample[C[0]][0] for sample in words(chip, 600)} == {0}


@BOTH
def test_test_bit_3_runs_the_lfos_every_sample(variant):
    """Tier 3 / T4. S6: "Bit 3: Update tremolo and vibrato LFOs every sample ...
    (Tremolo is 64x faster, and vibrato is 1024x faster.)" Spec 7.7, 10.2."""
    chip = tone_chip(PLAIN_SINE, variant=variant)
    write(chip, 0x0F, 0x08)
    tremolo, vibrato = chip.tremolo_time, chip.vibrato_time
    chip.run(SAMPLE)
    chip.take_outputs()
    assert (chip.tremolo_time - tremolo) % 13_440 == 64
    assert (chip.vibrato_time - vibrato) % 8_192 == 1024


# ------------------------------------------------ the frequency formula (S6)


@BOTH
@pytest.mark.parametrize("f_number, octave", ((0x100, 4), (0x0AB, 6), (0x1FF, 2)))
def test_the_frequency_formula_as_the_wiki_prints_it(variant, f_number, octave):
    """Tier 3. S6: F = 49716 Hz × freq / 2^(19 - octave), for a multiplier of 1.
    Counted as rising zero crossings of a plain sine over 20,000 samples."""
    chip = tone_chip(PLAIN_SINE, f_number=f_number, block=octave, variant=variant)
    count = 20_000
    expected = count * f_number / 2 ** (19 - octave)
    assert abs(rises(melody(chip, count)) - expected) <= 1


# ---------------------------------------------- SMS Power's rhythm set-up (S9)


def test_sms_powers_rhythm_values_play_the_five_sounds():
    """Tier 3. S9, "Rhythm mode": "$16 $20, $17 $50, $18 $C0, $26 $05, $27 $05,
    $28 $01", as Yamaha advises (S1), with the five keys in $0E. Each sound's
    slot on the rhythm pin (spec 12.2) carries a word."""
    if SMS_POWER.exists():
        text = SMS_POWER.read_text(encoding="utf-8", errors="replace")
        for register, value in (
            ("16", "20"),
            ("17", "50"),
            ("18", "C0"),
            ("26", "05"),
            ("27", "05"),
            ("28", "01"),
        ):
            assert re.search(rf"\|\|\${register}\s*\|\|\${value}\b", text), register
    chip = OPLL(YM2413)
    for register, value in (
        (0x16, 0x20),
        (0x17, 0x50),
        (0x18, 0xC0),
        (0x26, 0x05),
        (0x27, 0x05),
        (0x28, 0x01),
    ):
        write(chip, register, value)
    write(chip, 0x0E, 0x20)
    write(chip, 0x0E, 0x3F)
    trace = words(chip, 3000)
    for slot in (13, 14, 15, 16, 17):  # hi-hat, tom, bass drum, snare, top cymbal
        assert max(abs(sample[slot][1]) for sample in trace) > 50, slot
