# Validation: the oracles, the ladder, and every run

## Tiers

1. **hardware**: a measurement of a real chip (the VRC7's debug-mode instrument dump;
   andete's captures of a YM2413's pins).
2. **manufacturer**: Yamaha's YM2413 catalog (1996-06).
3. **die-derived**: a transcription of the chip's silicon from die photographs.
4. **emulator**: another program; evidence, never a judge.

## The oracles

| Oracle | Tier | Role | Pin |
| --- | --- | --- | --- |
| VRC7 instrument ROM, dumped in the chip's debug mode (siliconpr0n) | hardware | the DS1001's instruments | `reference/docs/VRC7_audio.wiki` (SHA-256 in `scripts/fetch_references.py`) |
| Yamaha, *YM2413 catalog* | manufacturer | the programmer's model | `reference/docs/YM2413_199606.pdf` |
| **Nuked-OPLL** (nukeykt), from the VRC7's die | die-derived | **the judge**: MO and RO, every internal cycle, every part | `reference/src/Nuked-OPLL` @ 1269cf5, GPL-2.0, built locally as `opll_ref` |
| andete's captures of a real YM2413's MO/RO pins through a 12-bit ADC (2015-2017, for openMSX) | hardware | the rhythm drums' levels and envelopes; the DAC's slot order | `reference/src/andete-ym2413` @ 4893d1c, no licence: read, never copied |
| emu2413 (Okazaki), ymfm (Giles) | emulator | detectors, not yet run | @ a1d5120 (MIT), @ 81aec25 (BSD-3) |

`validation/opll_ref.c` drives Nuked-OPLL and copies nothing; Nuked-OPLL is read for
the chip's behaviour and cited by file and line (docs/phase0.md, "Licence").

## Rung 0: tables and data (2026-10-27)

The log-sine and exponent ROMs, generated from `-log2(sin((i + 0.5)·π/512))·256` and
`2^((255 - i)/256)·1024`, equal Nuked-OPLL's word for word (`tests/test_tables.py`,
pinned by SHA-256; the log-sine hash is the one ym2612-python pins for the YM2612: the
two chips share the ROM). The VRC7's fifteen instruments equal its debug-mode dump
byte for byte (`tests/test_variants.py`).

## Rung 1: every cycle, synthetic streams (2026-10-27)

`scripts/referee.py` runs `scripts/streams.py`'s 20 streams through the core and
Nuked-OPLL from /IC and compares (MO, RO) on every internal cycle: each instrument
and the custom one; feedback with both half-sines; all nine channels; rhythm mode,
its toggling at every cycle of a sample and against key-ons; envelope rates, KSR,
KSL and MULTI swept; vibrato and tremolo over whole cycles; the test register;
writes faster than the catalog asks and back to back; the slowest envelopes for six
seconds and the envelope timer's 2^17 rollover over twelve; seeded random writes.

| Part | Streams | Cycles | Different |
| --- | ---: | ---: | ---: |
| YM2413, DS1001, YM2413B, YMF281, YMF281B, YM2423 | 20 each | 21,102,104 each, 126,612,624 in all | **0** |

## Rung 2: every cycle, music (2026-10-27)

Register streams recorded from the boards running the games
(`scripts/export_board_streams.py`, into the ignored `validation/streams/`):
*Lagrange Point* on famicom-python's VRC7 (a local branch adding mapper 85; Start,
then A every three seconds, three minutes) and five Master System FM soundtracks on
sms-python's Japanese console (the script answers the FM unit's detection port
itself; sixty seconds each, Button 1 pressed at intervals).

| Stream | Writes | Cycles | Parts | Different |
| --- | ---: | ---: | --- | ---: |
| *Lagrange Point* (VRC7) | 32,110 | 160,794,033 | DS1001, YM2413, YM2413B | **0** |
| *Phantasy Star* (Japan) (Rev 1) | 19,882 | 53,781,698 | YM2413, YM2413B | **0** |
| *Ys* (Japan) | 16,626 | 53,751,531 | YM2413 | **0** |
| *Kenseiden* (Japan) | 21,462 | 53,780,890 | YM2413 | **0** |
| *Fantasy Zone II* (Japan) | 88,007 | 53,782,761 | YM2413 | **0** |
| *Super Wonder Boy - Monster World* (Japan) | 22,694 | 53,781,428 | YM2413 | **0** |

The VRC7 stream takes the VRC7's resonator as exactly two input clocks per CPU cycle
(it is not locked to the CPU on the cartridge); the Master System's YM2413 shares
the Z80's crystal, so its streams are exact.

## Rung 3: seeded faults (2026-10-27)

`scripts/mutation.py` breaks one rule of `chip.py` or `variants.py` at a time and runs
the referee (YM2413, DS1001, YM2413B) to the first difference: **30 of 30 caught**. The
first run caught 27; each miss became a stream (back-to-back strobes on one port, the
envelope timer's 2^17 rollover with a rate-11 slot kept going, rhythm toggled against
key-ons with feedback). The rhythm enable's one-cycle delay into the phase and
operator stages proved invisible on both pins (the mutant against the core directly
on 35 seeds of the race stream: equal): an equivalent mutant, recorded and replaced
by a mutant of the cycles that rule acts on.

The conformance examples alone (`--examples-only`, what a port's gate is): **29 of 30**;
the one missed needs the timer's 2^17 rollover, ten seconds of chip time
([conformance.md](conformance.md)).

## Hardware: andete's captures (2026-10-27)

andete drove a real YM2413 from a microcontroller, sampled its pins with a 12-bit ADC
once per 72 clocks, and mapped each sample back to the DAC's level through a
calibrated table (results/20150209.txt): the `results/rhythm/gold-*` files, one level
per sample, 255 minus the signed channel output. What a capture does not record is
when key-on landed against the free-running envelope timer, so
`scripts/hardware_captures.py` sweeps key-on over 256 sample offsets with the referee,
keeps the best fit, and reruns it on the core, which must equal the referee on every
sample. A capture's name carries the frequency and the key-on length (as andete's
sweep.cc reads it); the volume is taken as 0.

**BD and TOM, 36 captures, 218,200 samples: every one fits.** On the quiet samples
(within 32 levels of zero, changing by at most two a sample) the core is exact on
59 % to 100 % of them, 89.5 % in all, and off by more than one level on 1,508 of
138,128. Loud and fast stretches are off by up to 79 levels where the waveform
swings by a hundred a sample: the analogue chain's error, which andete describes
(the ADC's non-linearity, calibration drift, the shaping board's bandwidth). There
is no drift in time: the best local alignment stays put through every capture, and
the long release tails match exactly for thousands of samples.

The control is the same search with the drum one volume step (3 dB) quieter: every
capture fits worse, the quiet samples off by more than a level rising from 0-316 to
41-4,800 (a TOM off by one F-number: 0 to 1,319). The captures tell levels and
envelopes apart; they do not pin the envelope timer to a cycle (neighbouring offsets
score alike), so they corroborate the referee rather than sharpen it.

| Captures | Count | Quiet samples exact | Off by > 1 (quiet) | Control, off by > 1 |
| --- | ---: | ---: | ---: | ---: |
| BD (`gold-bd-*`), keyed 1000 or 5000 samples or held | 19 | 59 %-100 % | 0-316 | 41-4,800 |
| BD, second series (`gold-bd2-*`; andete does not say what changed) | 13 | 59 %-100 % | 0-175 | 36-844 |
| TOM (`gold-tom-*`) | 4 | 91 %-92 % | **0** | 291-1,433 |

Not fitted: `gold-bd-2` and `gold-bd-2b` (no frequency in the name), `gold-bd-e25`
(a full-scale tone of about 14 samples a period, not a bass drum: mislabelled or made
with settings its name does not carry). SD and HH need the noise generator's 2^23
state, TCY a free-running phase counter: searches not done.

**The slot order.** andete's rhythm.md tables which of the DAC's 18 slots carries
each sound in rhythm mode, measured: each drum twice, the second copy always equal
to the first (a five-deep delay line he found on the die), the melodic channels
between. The core matches that table slot for slot with his slot 0 as its output
cycle 4 (`tests/test_rhythm_slots.py`). Nuked-OPLL marks this stage "might be
incorrect" (opll.c:844); the measurement says it is right.

andete's notes once disagreed with Nuked-OPLL over the top cymbal (its phase gave
±3 dB, his captures reach ±255); Nuked-OPLL has since changed to the full-scale phase
(`| 0x100`), and the pinned version agrees with the measurement.

## Not yet

The detectors' comparison, and adoption by famicom-python (the VRC7's sound) and
sms-python (the FM unit).

## Speed

Not a goal (reference boards are correct, not fast). On PyPy the referee's core side
runs about 29 million internal cycles a minute, 0.6x real time.
