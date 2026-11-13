"""The chip's fixed tables, each with its source and standing.

Section numbers ("spec 6.3") are those of ``docs/spec.md``; S numbers are the
sources of ``docs/phase0.md``; ``docs/provenance-audit.md`` has each statement's
chain. Nothing here differs between the YM2413 and the DS1001: what differs is in
``variants.py``.
"""

from __future__ import annotations

import math

#: The logarithmic sine ROM: a quarter period in 256 steps, each the negated
#: base-2 logarithm of the sine in 1/256 units, taken at the middle of the step.
#: Spec 6.3. The formula is Matthew Gambrell's and Olli Niemitalo's, who read the
#: ROMs of a YM3812 and a YMF262 bit by bit under a microscope ("OPLx
#: decapsulated", 2008: S11); Wouter Vermaelen (S4, ``tab.txt``) found the OPLL's
#: ROM alike on the die and predicted captured waveforms from it exactly for
#: volumes 1 to 15. Measured for those chips; measured indirectly for this one.
LOG_SIN: tuple[int, ...] = tuple(
    round(-math.log2(math.sin((i + 0.5) * math.pi / 512)) * 256) for i in range(256)
)

#: The exponential ROM: 256 steps of 2^(i/256), scaled by 1,024, with the bit
#: that is always set left out. Spec 6.4; same sources and standing as LOG_SIN.
EXP: tuple[int, ...] = tuple(round((2 ** (i / 256) - 1) * 1024) for i in range(256))

#: Twice the frequency multiplier for each MULTI value (so that the 1/2 of value
#: 0 is a whole number). Documented: spec 7.4, Yamaha's application manual (S1),
#: Table III-1. Measured as doubled values in the phase step: spec 7.3 (S4).
MULTIPLIER_X2: tuple[int, ...] = (1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 20, 24, 24, 30, 30)

#: Attenuation in dB at 3 dB per octave in the top octave, by the F-number's top
#: four bits. Documented: spec 9.2, S1 Table III-5, bottom row, read from the
#: page image.
KEY_SCALE_DB: tuple[float, ...] = (
    0.000, 9.000, 12.000, 13.875, 15.000, 16.125, 16.875, 17.625,
    18.000, 18.750, 19.125, 19.500, 19.875, 20.250, 20.625, 21.000,
)  # fmt: skip

#: An envelope step in dB. Measured: spec 8.1 (S4: 128 steps in 48 dB). S1 prints
#: "0,325 dB" (contradiction C1).
ENVELOPE_STEP_DB = 0.375


def _key_scale_steps() -> tuple[tuple[tuple[int, ...], ...], ...]:
    """KEY_SCALE_STEPS[code][block][F-number's top four bits], in envelope steps.

    Spec 9.2 to 9.4. The 6 dB setting is twice S1's row less 6 dB per octave below
    the top, floored at zero (S1's notes to Table III-5); the 3 dB setting is that
    halved and the 1.5 dB setting quartered, dropping fractions (spec 9.3:
    measured on a sparse sample by S4, ``ksl.txt``). Code 1 is 1.5 dB, code 2 is
    3 dB, code 3 is 6 dB: measured (S4), against one reading of S1's Table III-4
    (contradiction C3).
    """
    six_db = [
        [max(0, round(2 * db / ENVELOPE_STEP_DB) - 16 * (7 - block)) for db in KEY_SCALE_DB]
        for block in range(8)
    ]
    shifts = (None, 2, 1, 0)
    return tuple(
        tuple(
            tuple(0 if shift is None else steps >> shift for steps in six_db[block])
            for block in range(8)
        )
        for shift in shifts
    )


KEY_SCALE_STEPS = _key_scale_steps()

#: For effective rates 4 to 51: where in each run of eight opportunities the
#: envelope steps, by the rate's low two bits. Measured: spec 8.5. S4
#: (``adsr-transitions.txt``) fixed each pattern and its rotation by listing the
#: first-segment lengths that occur on the chip and ruling out every other
#: candidate. S4 first met the scheme in a GPL emulator and says so; the
#: measurement is the source here (docs/restart.md, rule 10).
ENVELOPE_PATTERNS: tuple[tuple[int, ...], ...] = (
    (0, 1, 0, 1, 0, 1, 0, 1),
    (0, 1, 0, 1, 1, 1, 0, 1),
    (0, 1, 1, 1, 0, 1, 1, 1),
    (0, 1, 1, 1, 1, 1, 1, 1),
)

#: Samples in one tremolo cycle, and the measured lengths that make it up
#: (spec 10.2, S4 ``am.txt``): 960 samples at 0, 512 at each of 1 to 12 going up
#: and again coming down, 192 at 13.
TREMOLO_PERIOD = 13_440

#: Samples in one vibrato cycle: eight positions of 1,024 samples. Measured:
#: spec 7.7 (S4 ``20151201.txt``). S1 says 6.4 Hz, which would be 7,768
#: (contradiction C2).
VIBRATO_PERIOD = 8_192


def tremolo_level(sample_in_cycle: int) -> int:
    """Envelope steps the tremolo adds, 0 to 13, at a place in its cycle.

    Spec 10.1 and 10.2: measured (S4). CHOICE: the cycle is taken to begin where
    the level becomes 0; nothing says how it lies against anything else (U15).
    """
    step = sample_in_cycle >> 6  # every measured length is a multiple of 64
    if step < 15:
        return 0
    if step < 111:
        return 1 + ((step - 15) >> 3)
    if step < 114:
        return 13
    return 12 - ((step - 114) >> 3)


#: TREMOLO[step]: the 210 steps of 64 samples, from the rule above.
TREMOLO: tuple[int, ...] = tuple(tremolo_level(step << 6) for step in range(TREMOLO_PERIOD >> 6))

#: Which slot is which operator: the modulators and carriers of channels 0 to 8.
#: Documented: spec 2.4 (S1 Table II-3); measured (S4 ``rhythm.md``).
MODULATOR_SLOT: tuple[int, ...] = (0, 1, 2, 6, 7, 8, 12, 13, 14)
CARRIER_SLOT: tuple[int, ...] = (3, 4, 5, 9, 10, 11, 15, 16, 17)
SLOT_CHANNEL: tuple[int, ...] = (0, 1, 2, 0, 1, 2, 3, 4, 5, 3, 4, 5, 6, 7, 8, 6, 7, 8)
SLOT_IS_CARRIER: tuple[bool, ...] = tuple(slot in CARRIER_SLOT for slot in range(18))

#: Rhythm mode: the slots of the five sounds (spec 11.2: S1 Table III-9, S4).
SLOT_BASS_MODULATOR, SLOT_HI_HAT, SLOT_TOM, SLOT_BASS_DRUM, SLOT_SNARE, SLOT_CYMBAL = range(12, 18)

#: Rhythm mode: the slot of the next sample in which each sound's word is output
#: a second time (spec 11.12, 12.2: S1 Figure III-3; measured by S4).
COPY_SLOT: dict[int, int] = {0: SLOT_HI_HAT, 1: SLOT_TOM, 2: SLOT_BASS_DRUM, 6: SLOT_SNARE, 7: SLOT_CYMBAL}  # fmt: skip
