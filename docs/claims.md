# Claims

Each claim the repository makes, with the evidence for it and the tier of that
evidence. Tiers are [phase0.md](phase0.md)'s: 1 a capture from hardware, 2 the
manufacturer, 3 a community document checked on hardware, 5 an emulator. Section
numbers in brackets are [spec.md](spec.md)'s. "Checked by" names what was run on
2026-11-13; all of it passed on PyPy 3.11 unless a difference is stated.

**Not claimed anywhere:** that either variant is exact to a console; that the
YM2413's fifteen melodic voices are the chip's (they are an emulator's
hand-tuned table, T1); that anything about write timing inside a sample,
rhythm-mode edge cases, the test register on the YM2413, or the state after reset
matches hardware; that the core equals any other emulator.

"S4's write-ups" are the openMSX project's accounts of measurements on one real
YM2413 (andete/ym2413 at `4893d1c`, by Wouter Vermaelen). The tests are written
from their prose and tables, not from their capture files (rung 2b is not done),
so a tier-1 claim here means "agrees with what S4 reports measuring".

## Claims with evidence above the emulator tier

| # | Claim | Evidence | Tier | Checked by |
|---|---|---|---|---|
| 1 | The log-sine and exponential ROMs, and the arithmetic from attenuation to a word: the sixteen peak amplitudes by volume (255, 180, 127, ... 1, 1), 400 codes in a full-volume sine, four codes at volumes 14 and 15, one's-complement negatives with two zeros [6.1-6.6, 6.10] | S11's ROM read-outs (OPL2/OPL3) as S4 quotes them; S4 `tab.txt`, `20150311.txt` | 1 | `tests/test_measured.py` |
| 2 | An operator is silent (+0) from envelope level 124; the total attenuation is clipped at 127; the peak widths 342 and 332 samples at levels 112 and 113 [6.7, 6.8] | S4 `small-signals.txt` | 1 | `test_measured.py` |
| 3 | Half-sine: -0 for exactly half the period [6.9] | S4 `small-signals.txt`; S1 | 1, 2 | `test_measured.py`, `test_manual.py` |
| 4 | Modulation and feedback: carrier words equal a separately written reference of spec 6.5 to 6.13 at six depths and six feedback settings, sample for sample; the "15 equal, then 1 other" pattern; every half period all depths change sign on the same sample [6.11-6.13] | S4 `mod-car.txt`, `fb.txt`; feedback amount from S1 Table III-6 | 1 (form), 2 (amount) | `test_measured.py`, `test_manual.py` |
| 5 | The phase counter: 19 bits, the step formula, all 30 flat-segment lengths and 16 periods S4 tabulates, the 19-bit overflow example, F-number 0 freezing the phase [7.2, 7.3, 7.6] | S4 `20150316.txt` | 1 | `test_measured.py` |
| 6 | Vibrato at the top pitch range: eight regions of 1,024 samples with S4's step sizes [7.7, 7.8] | S4 `20151201.txt`, which calls its own fit "not an exact match" | 1, approximate | `test_measured.py` |
| 7 | Decay and release step lengths for rates 4 to 61, and the first-segment lengths after attack that fix each pattern's alignment [8.5-8.8] | S4 `20150320.txt`, `attack.txt`, `adsr-transitions.txt` | 1 | `test_measured.py` |
| 8 | Attack: the sequences from 127 and from 124, three single samples then a plateau, the mixing of two formulas at rates 48 to 59, the worked example 21, 15, 13, rate 15 instant only at the end of damp [8.10-8.14] | S4 `attack.txt` | 1 | `test_measured.py` |
| 9 | The states: damp at rate 12 ending at 124 and faster at higher pitch; decay ends on equality with SL (a level passed is never met; level 9 can stick); SL changes in sustain do nothing; EG-TYP switches sustain between holding and falling; key-off goes to release from any state; release rates RR, 5 and 7 by SUS and EG-TYP; a modulator has no release [8.16-8.25] | S4 `envelope.txt`, `attack.txt`; S1 Figure III-1 | 1, 2 | `test_measured.py`, `test_manual.py` |
| 10 | Key scale of rate for ten settings, each "confirmed" by S4; KSL codes 1, 2, 3 are 1.5, 3, 6 dB per octave [8.3, 9] | S4 `sl-ksr.txt`, `ksl.txt`; S1 Tables III-2, III-5 | 1, 2 | `test_measured.py`, `test_manual.py` |
| 11 | Tremolo: levels 0 to 13, held 960, 512 and 192 samples; one envelope step each [10] | S4 `am.txt`; S1 (3.7 Hz) | 1, 2 | `test_measured.py`, `test_manual.py` |
| 12 | Noise: a 23-stage register with polynomial x^23 + x^9 + 1, stepped once per slot; S4's 120 printed snare bits and 50 simultaneous hi-hat and snare bits occur in the model's sequence [11.7] | S4 `lfsr.txt`, `rhythm.md` (2020 update) | 1 | `test_measured.py` |
| 13 | Rhythm: the snare's four outputs; the bass drum equals the user tone with S4's bytes; the tom is a sine at channel 8's pitch; the cymbal is two peaks reaching full scale; channel key bits OR with the rhythm keys (loosely measured) [11.4-11.9] | S4 `rhythm.md` | 1 | `test_measured.py` |
| 14 | Register aliases $19-$1F, $29-$2F, $39-$3F [4.3] | S4 `ksl.txt` | 1 | `test_measured.py` |
| 15 | The write protocol, the clear at reset, 72 clocks a sample, Tables III-1 (multipliers), III-2, III-3, III-5, III-6, III-7 (every decay and attack time), III-8-2 (F-numbers), III-9 (rhythm slots), Table II-3 (slot order), Figure III-1 (shapes, damp 10 ms, SUS rate 5), tremolo 3.7 Hz [2-12] | Yamaha's YM2413 application manual (S1) | 2 | `tests/test_manual.py` (229 tests) |
| 16 | Vibrato is 6.07 Hz, not the printed 6.4 (contradiction C2) | S4 against S1 | 1 over 2 | `test_manual.py` |
| 17 | The DS1001's 15 voices and the 3 drum rows are the NESdev wiki's read-out of the chip's ROM [5.5, 5.6] | S6, "dumped using the VRC7 rewired into a debug mode" | 3 | `tests/test_community.py` |
| 18 | Each ROM voice plays as its row loaded as the user tone, on both variants [5.1] | S1, S6 | 2, 3 | `test_community.py` |
| 19 | The DS1001 sounds six channels and nothing on the rhythm side; the VRC7 reset clears registers and tremolo, not vibrato; the four test-register bits; the wiki's frequency formula [1, 13, 14] | S6, S7 | 3 | `test_community.py` |
| 20 | SMS Power's rhythm set-up plays all five percussion sounds | S9 | 3 | `test_community.py` |

## Provisional: decisions, not evidence

T numbers are those of [provenance.md](provenance.md); U numbers are spec.md's.
Held as data on `OPLLVariant` or labelled PROVISIONAL or CHOICE in the code. Each
is pinned by one test in `tests/test_provisional.py`; they prove nothing about
hardware.

| # | Behaviour | Basis | Tier |
|---|---|---|---|
| T1 | The YM2413's 15 melodic voices | emu2413's hand-tuned table (MIT); not a dump | 5 |
| T2 | The snare's last byte is $68 on both | S4's fit and the DS1001 read-out; S6 and ymfm say $48 for the YM2413 (C4) | 1 against 3 |
| T3 | Vibrato offsets below the top pitch range | emu2413's table | 5 |
| T4 | The YM2413's test register acts like the VRC7's | S6, for the VRC7 only | 3 for the DS1001, none for the YM2413 |
| T5 | State after reset: envelopes at 127, phases, counter and LFOs at 0, noise register 1 | none; the noise register must not be 0 | none |
| T6 | `take_outputs` sums each pin's words over a sample | a choice of interface | none |
| T7 | A write acts from the next slot boundary; unmapped addresses are ignored | none | none |
| T8 | The cymbal and hi-hat bit: emu2413's form, the first of S4's sixteen | S4 measured it up to 16 equivalent forms; the pick is emu2413's | 1 up to the ambiguity, 5 for the pick |
| T9 | Rhythm keys OR with channel keys | S4, marked TODO | 1, loose |
| T10 | Switching rhythm mode keeps envelopes and phases | none | none |
| T11 | The carrier hears the modulator's output of the previous sample | reproduces S4's measured one-sample lag | 1 for the effect, a choice for the mechanism |
| T12 | Hi-hat and tom: eight steps a volume step, no total level | none | none |
| T13 | Attack from 125 or 126 uses the same formula; the level saturates at 127 | none | none |
| T14 | Modulators and percussion are damped at key-on | S4, "not 100% sure" | 1, uncertain |
| T15 | The DS1001's channels 6 to 8 take writes and stay silent | S6 says the rhythm bit acts as set | 3 for silence |
| U20 | The sample in which damp ends already sounds; both phases restart then | spec 7.10's wording for "both"; the sample is a choice | 1, partly |
| U22 | The hi-hat's four phases | emu2413 | 5 |
| U23 | Counter bits 2 and 3 choose the faster samples at rates 48 to 59 | the slow-rate rule continued | none |
| U24 | Negative modulator values: one's complement, then doubled or shifted | none | none |

## Claims about the checks themselves

| # | Claim | Evidence |
|---|---|---|
| C1 | Each rung can fail: 30 deliberate faults, every one noticed. Rung 0 notices 6, rung 1 17, rung 2a 24, rung 3 10, the provisional tests 13 | `validation/faults.py`, run 2026-11-13 (about 4 minutes) |
| C2 | Against Nuked-OPLL run as a closed box, plain sines and vibrato agree on every slot; elsewhere the differences are those listed as O1 to O7 in [validation.md](validation.md), all open | `validation/closed_box.py`, run 2026-11-13. Tier 5: a detector |
| C3 | Nothing in the core was changed because of the closed box, and no constant was fitted to its output | git history; [validation.md](validation.md), rung 6 |
| C4 | Nuked-OPLL's `opll.c` was not opened; the harness uses only the three calls its header declares. The header's state structure was seen and is not used | `validation/nuked_harness.c`; [provenance.md](provenance.md), "Material seen and not used" |
| C5 | One test (`test_test_bit_2_silences_a_modulated_carrier_too`) is an expected failure: S6 says test bit 2 silences the chip, and with a sounding modulator the core does not | `tests/test_community.py` |
| C6 | Everything seen during the work that the rules keep out is listed, with what was done about it | [provenance.md](provenance.md), "Material seen and not used" |

## What has no evidence at all

Rung 4 is empty: no recording of a console's YM2413 or VRC7 is in hand. Rung 2b
(S4's capture files themselves) is not done. Until they are, every claim above
stands at the tier shown and no higher.
