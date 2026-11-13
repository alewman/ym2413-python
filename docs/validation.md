# Validation ladder

**Where it stands, 2026-11-13** (detail in [build-status.md](build-status.md)):

| Rung | Judge | State |
|---|---|---|
| 0 | the API contract | passes (24 tests) |
| 1 | Yamaha's manual (S1) | passes (229 tests) |
| 2a | the openMSX project's measurements, as written up | passes (192 tests) |
| 2b | its capture files, sample for sample | not done: the format is unknown (U18) |
| 3 | the NESdev wiki and SMS Power | passes (50 tests, one an expected failure: an open difference) |
| 4 | console recordings | none exist |
| 5 | emu2413 and ymfm as detectors | not run |
| 6 | Nuked-OPLL as a closed box | run; findings O1 to O7 open (below) |
| 7 | the boards | not adopted yet |

`validation/faults.py`: 30 faults, every one caught (rung 0 catches 6, rung 1
17, rung 2a 24, rung 3 10, the provisional record 13). Some faults in the list
just below were not used because the code has no such switch (stepping the noise
once a sample, SL 15 as the bottom); the 30 used are in the script.

The text below is the ladder as proposed on 2026-11-12, kept as written, with
the closed box's results added under rung 6.


Written 2026-11-12 for the build that follows Phase 0. The rungs are ordered by how
far their judge can be trusted, the best first. A lower rung never overrules a
higher one. Source IDs are [phase0.md](phase0.md)'s; C and U numbers and section
numbers are [spec.md](spec.md)'s.

Two things hold for every rung:

- **Each check names its source in the test itself**: document, page or file, and
  the word documented or measured.
- **Each rung must be able to fail.** Before a rung is called passed, break the
  model on purpose in ways that rung should catch and see it fail. A starting list:
  swap two rows of the envelope step patterns; use n = 3 for the slow attack; let
  damp run to 127; drop the mute at level 124; use -0 for +0 in the half sine; step
  the noise register once a sample; shift the feedback by one more; make SL 15 the
  bottom; exchange KSL codes 1 and 2; give a modulator a release. The count of
  faults caught goes in the README beside the rung.

What the ladder cannot do is in the last section. Read it before claiming anything.

## Rung 0: the contract with the boards

Not a judge of the chip; it keeps the core usable.

- The names and calls in [api.md](api.md) exist and behave as it says: `write`,
  `run`, `take_samples`, `take_outputs`, `reset`; `CLOCKS_PER_CYCLE` is 4 and
  `CYCLES_PER_SAMPLE` is 18.
- `run(a)` then `run(b)` gives the same output as `run(a + b)`, for any split,
  including splits inside a slot.
- State is plain attributes; a state copied out and back continues identically.
- An instance, and every object it owns, has fewer than 80 attributes (PyPy turns a
  larger one into a dict).
- `DS1001` produces nothing on the rhythm side and nothing from channels 6 to 8.

**Exit**: all pass on PyPy 3.11 and CPython 3.11.

## Rung 1: the manufacturer's documents

Every check is a row of a printed table or a sentence of S1, cited by section and
page. These need no hardware and no other program.

- Register fields: each field of section 4 reaches the behaviour it names, for
  modulator and carrier (S1 section II-7).
- Multiplier: all 16 rows of Table III-1, as measured tone frequency.
- F-number: fsam × F × 2^block / 2^19 for the 24 rows of Tables III-8-1 and III-8-2
  evaluated at 50 kHz as the manual does (C6), and the general formula at the real
  rate.
- Key scale rate: the 32 cells of Table III-2.
- Total level: the six weights of Table III-3 (0.75 to 24 dB); volume and sustain
  level: four weights each (3 to 24 dB), as measured output ratios within the
  9-bit output's rounding.
- Key scale level: all 128 cells of Table III-5 at 3 dB per octave, and half and
  double for the other two settings, to the nearest envelope step.
- Feedback: the doubling of Table III-6 (each step doubles the fed-back swing).
- **Decay times**: all 60 rows of Table III-7's left half. From level 0 to 127 at
  each effective rate, the model's time in samples × 72 / 3,579,545 s equals the
  printed milliseconds to the printed two decimals, allowing the one early first
  step of spec 8.4 (start the shared counter at 0 for the test).
- **Attack times**: the rows of Table III-7's right half up to rate 47 as 21, 17,
  14, 12 × 2^k samples (spec 8.15); the faster rows as a looser bound, since S4
  found the table "start[s] to deviate" there.
- The envelope figure: percussive and sustained shapes, SUS forcing rate 5.
- Rhythm slots: Table III-9. The percussion sounds appear twice per sample (section
  III-4).
- Tremolo 3.7 Hz and vibrato rate to one decimal (vibrato fails S1's 6.4 on
  purpose: the test asserts 6.07 and cites C2).
- Reset clears every register (section III-1).

**Proves**: the model does what Yamaha told programmers it does. **Does not
prove**: any table's contents, the attack's shape, anything bit-exact.

**Exit**: every row passes; each listed fault that this rung can see is caught.

## Rung 2: measurements of a real YM2413 (S4)

This is the rung that makes the core more than a reading of the manual. It has two
forms, and the first does not depend on any file of S4's.

**2a. The stated results.** Each numbered "measured" statement in spec.md becomes a
test whose expected values are the numbers S4 reports in prose, typed into the test
with the write-up's file name:

- Peak amplitude for each of the 16 volumes: 255, 180, 127, 90, 63, 45, 31, 22, 15,
  11, 7, 5, 3, 2, 1, 1 (`tab.txt`), and the same for sustain levels.
- A full-volume sine uses exactly 400 distinct output codes (`tab.txt`).
- Phase: the flat-segment lengths of the 30-row table in `20150316.txt`, the period
  lengths of its high-frequency table, including the two cases that do not move.
- Decay step lengths for rates 4, 9, 14, 19, 48 to 59 and 60 to 63 (spec 8.5 to
  8.8).
- First-segment lengths after attack-to-decay and decay-to-release changes: the set
  of possible lengths for AR 4 / DR 2 is {$200, $600, $A00, $E00} samples, and for
  AR 5 / DR 2 with rate & 3 = 1, 2, 3 the sets `adsr-transitions.txt` lists. Run the
  model from every starting value of the shared counter and compare the *set*.
- Attack: the sequence 127, 119, 111, 104, 97, 90, 84, 78, 73, 68, 63, 59, 55, 51,
  47, 44, 41, 38, ... and the one from 124; three single samples then a plateau of
  2^s - 3; the 4/12, 8/8, 12/4 mixing for rates 49 to 51, 53 to 55, 57 to 59;
  AR 15 instant only when in force at the end of damp.
- Damp at rate 12 ending at 124; release ending at 127.
- Sustain: equality on the top bits (SL raised behind the level lets decay run on).
- Tremolo: 960, 512 and 192 samples at levels 0, 1 to 12 and 13; period 13,440.
- Vibrato: steps of 28,672, 28,768, 28,896, 28,768, 28,672, 28,576, 28,448, 28,576
  for F-number $1C0, block 6, MULTI 1 (`20151201.txt`).
- Mute at level 124; total attenuation clipped at 127; the peak widths 342 and 332
  samples at levels 112 and 113 in that experiment (`small-signals.txt`).
- Half sine: -0 for exactly half the period.
- Noise: the 120 snare bits printed in `lfsr.txt` occur in the model's snare
  sequence; the 50 hi-hat and 50 snare bits printed in `rhythm.md` occur together
  with the snare three steps behind.
- Register aliases $19 to $1F, $29 to $2F, $39 to $3F.
- Modulator: no change of rate at key-off.

**2b. The captures themselves** (S5), if decision P1 allows them to be read and
their format can be worked out (U18): feed the register writes S4 lists for an
experiment, and compare the model's carrier output for channel 0 with the captured
levels sample for sample, after aligning the start and allowing for the two unknown
starting values (the shared counter and, with feedback, the two remembered
outputs). The capture files are read in place; nothing is copied here.

**Proves**: agreement with one real chip on everything S4 measured. **Does not
prove**: a second chip, the YM2413B, the DS1001, or anything S4 did not measure.

**Exit**: 2a complete; every listed fault caught; 2b either done with the number of
samples compared and the number that differ, or written down as blocked and why.

## Rung 3: community documents checked on hardware

- DS1001: the 15 instruments of S6's table are what `OPLL(DS1001)` plays (a test
  that the variant's ROM equals the pinned wiki file's table, parsed at test time
  from `famicom-python/reference`, skipped if absent; and a behavioural check that
  instrument n equals the user tone loaded with row n).
- DS1001: six channels; rhythm sounds never reach the output; writes to registers
  of channels 6 to 8 change nothing audible (S6).
- The reset bit: registers cleared; tremolo position cleared, vibrato position not
  (S6, S7).
- Test register, as S6 gives it for the VRC7: four bits, four effects (spec 13.2).
  Marked tier 3; on `YM2413` the same behaviour is provisional (T4).
- The frequency formula as S6 prints it.
- SMS Power's rhythm set-up values (S9) play the five sounds.

**Proves**: agreement with the NESdev wiki's account of the VRC7. **Does not
prove** that account.

**Exit**: all pass; each test's docstring says "tier 3".

## Rung 4: recordings (none in hand)

Nothing in hand is a recording of a YM2413 or a VRC7 that a test can use.

- rainwarrior's 2018 expansion-audio survey is in `famicom-python/reference`, but
  the recordings there are of other chips; the VRC7's is a level figure (+11.3 dB),
  which is the board's to match.
- S6 names a recording comparing the VRC7's and the YM2413's voices on the wiki
  (`VRC7_and_YM2413_on_FAMICOM_LP_intro.ogg`): lossy, music, not fetched. It could
  serve as a listening check of the built-in voices and no more.
- JoppyFurr's test ROM (S10) is made for side-by-side comparison with a console.
  Nobody in the family has a console with an FM unit, a Japanese Master System, or
  a *Lagrange Point* cartridge (decision P7).

**Exit**: none. The README says the rung is empty.

## Rung 5: permissive emulators (detectors)

emu2413 (MIT) and ymfm (BSD-3-Clause), each built from the pinned source into a
small harness under `validation/` and fed the streams of `seed/streams.py`. They
may be read as well as run, but a difference is settled by rungs 1 to 3, never by
adopting an emulator's answer because it is an emulator's.

- Compare per-sample channel sums over each stream, with a tolerance: these
  emulators do not claim bit-exactness, and neither should the comparison. Report,
  per stream, the fraction of samples that are equal, within 1, and the worst
  difference.
- Use user-tone streams for the comparison of synthesis; the built-in voices differ
  between the two emulators themselves (C9) and say nothing until U1 is settled.
- ymfm treats SL 15 differently (C5) and both differ from S4 in places S4 measured:
  those are expected differences and are listed, not fixed.

**Exit**: a table in the README. No pass mark.

## Rung 6: a die-derived model run as a closed box (detector, rule 8)

Nuked-OPLL, run and never read. Not fetched or built in Phase 0.

**The harness** (`validation/nuked_harness.c`, the only file that touches the
model):

- `scripts/fetch_references.py` gains a pin for the model's repository at one
  commit, with a comment that only its public header, its licence and its README
  may be opened. The `.c` file is compiled and never opened, searched, grepped or
  quoted, including when a comparison fails.
- The harness includes the public header and uses only what the header declares:
  the call that resets a chip of a given type (the header should name a YM2413 type
  and a DS1001 type), the call that writes a byte to port 0 or 1, and the call that
  advances the chip by one clock and returns its two outputs. If the header exposes
  the chip structure's fields, the harness does not read them: outputs only.
- It reads a stream on standard input (cycle, port, value, as `seed/streams.py`
  produces them, at four clocks per cycle), drives the model clock by clock, and
  writes one line per clock or per slot: the melody and rhythm output values.
- Nothing built from the model is committed. The harness's output goes to
  `validation/streams/` (git-ignored).

**What is compared**: the model's output sequence with ours for the same stream:
first per sample (the sum of the words in each 72 clocks), then per slot. For each
stream: the first clock at which they differ, the number of differing samples, and
the largest difference.

**What a difference means**: where to look. The answer is then sought in S1, S4 and
S6, and by *further experiments on the closed box* (change one register, compare
again), as rule 8 allows. If nothing settles it, the difference is written in the
README as open. The model's source stays closed.

**Two uses that need the owner's word first** (decision P6): using the
closed box to recover the YM2413's instrument ROM by searching for the user tone
that reproduces each built-in voice exactly, and using it to choose among spec.md's
unsettled items (U4, U5, U7, U8, U9). Both go beyond "a difference says where to
look"; both are, in rule 8's words, "further measurements of the model's outputs".

**Exit**: a table of differences per stream in the README, with each difference
either traced to a documented or measured statement (and fixed, on that
statement's authority) or listed as open. The README says the model was run and
its code was not read.

### Results, 2026-11-13

Run: Nuked-OPLL at commit `1269cf5` (Nuke.YKT, GPL-2.0; its repository has no
README, so only `opll.h` and `LICENSE` were opened), compiled with
`validation/nuked_harness.c` by `python validation/closed_box.py`. The model's
`opll.c` was not opened, searched or quoted; the compiler's messages went to an
unread log. **Nothing in the core was changed because of this rung, and no
constant was fitted to the model's output.**

How the harness turned out against the plan above: one `OPLL_Clock` call is one
slot (measured: a sample's words repeat every 18 calls), so the comparison is per
slot, not per clock; the output goes to standard output and is compared in
memory; the header does expose the model's state structure (its field names were
seen when the header was opened, as rule 8 allows) and the harness does not touch
it.

**Normalisations, each measured from the model's output only** (the script's
docstring has the detail): the model writes a word as sign × (size + 1), so +0 is
1 and -0 is -1, and it gives 0 in slots that carry no word; the core's word is
mapped to that form. A plain sine keyed on agrees on every slot of both variants
once the model's words are taken 40 slots later (the "phase frame"). A volume
write instead lines up 4 slots later (the "register frame"). Both frames were
run.

**"Sized"** counts the slots that differ by more than which zero: the YM2413
model also puts ±0 words on its rhythm pin outside rhythm mode where the core
puts +0, and the DS1001 model rests at 0 where the YM2413 model rests at +0.
Those differences are zero-only and are not listed below (U10).

| Stream | Variant | Pin | Slots | Differ | Sized (phase frame) | Sized (register frame) |
|---|---|---|---:|---:|---:|---:|
| silence | YM2413 | melody | 8992 | 0 | 0 | 0 |
| silence | YM2413 | rhythm | 8992 | 0 | 0 | 0 |
| silence | DS1001 | melody | 8992 | 0 | 0 | 0 |
| each_instrument | YM2413 | melody | 700312 | 28238 | 27783 | 28296 |
| each_instrument | YM2413 | rhythm | 700312 | 20158 | 0 | 0 |
| each_instrument | DS1001 | melody | 700312 | 32512 | 32236 | 32277 |
| custom_instrument | YM2413 | melody | 363112 | 8665 | 7338 | 9299 |
| custom_instrument | YM2413 | rhythm | 363112 | 7581 | 0 | 0 |
| custom_instrument | DS1001 | melody | 363112 | 8665 | 7338 | 9299 |
| feedback_and_half_sines | YM2413 | melody | 217240 | 6434 | 6419 | 7741 |
| feedback_and_half_sines | YM2413 | rhythm | 217240 | 7507 | 0 | 0 |
| feedback_and_half_sines | DS1001 | melody | 217240 | 6434 | 6419 | 7741 |
| all_channels | YM2413 | melody | 127072 | 25326 | 25052 | 38432 |
| all_channels | YM2413 | rhythm | 127072 | 34776 | 0 | 0 |
| all_channels | DS1001 | melody | 127072 | 27969 | 27858 | 35598 |
| rhythm | YM2413 | melody | 294112 | 72648 | 8484 | 7375 |
| rhythm | YM2413 | rhythm | 294112 | 76575 | 67280 | 60003 |
| rhythm | DS1001 | melody | 294112 | 4004 | 3998 | 4018 |
| envelopes | YM2413 | melody | 948880 | 17195 | 15586 | 17050 |
| envelopes | YM2413 | rhythm | 948880 | 16207 | 0 | 0 |
| envelopes | DS1001 | melody | 948880 | 17195 | 15586 | 17050 |
| vibrato_tremolo | YM2413 | melody | 369256 | 20305 | 20305 | 20139 |
| vibrato_tremolo | YM2413 | rhythm | 369256 | 9534 | 0 | 0 |
| vibrato_tremolo | DS1001 | melody | 369256 | 20305 | 20305 | 20139 |
| test_register | YM2413 | melody | 137056 | 24359 | 24359 | 24322 |
| test_register | YM2413 | rhythm | 137056 | 4141 | 0 | 0 |
| test_register | DS1001 | melody | 137056 | 18047 | 18047 | 17835 |
| fast_writes | YM2413 | melody | 41210 | 18666 | 6045 | 6040 |
| fast_writes | YM2413 | rhythm | 41210 | 19401 | 13868 | 13858 |
| fast_writes | DS1001 | melody | 41210 | 6462 | 5638 | 5635 |
| multiples | YM2413 | melody | 193936 | 8769 | 8599 | 8340 |
| multiples | YM2413 | rhythm | 193936 | 5467 | 0 | 0 |
| multiples | DS1001 | melody | 193936 | 8769 | 8599 | 8340 |
| rates | YM2413 | melody | 831760 | 18745 | 18086 | 18488 |
| rates | YM2413 | rhythm | 831760 | 13043 | 0 | 0 |
| rates | DS1001 | melody | 831760 | 18745 | 18086 | 18488 |
| key_scaling | YM2413 | melody | 153712 | 8234 | 8233 | 8218 |
| key_scaling | YM2413 | rhythm | 153712 | 4585 | 0 | 0 |
| key_scaling | DS1001 | melody | 153712 | 8234 | 8233 | 8218 |
| back_to_back | YM2413 | melody | 34615 | 644 | 619 | 634 |
| back_to_back | YM2413 | rhythm | 34615 | 940 | 0 | 0 |
| back_to_back | DS1001 | melody | 34615 | 1809 | 1795 | 1609 |
| rhythm_toggles | YM2413 | melody | 32187 | 7355 | 2696 | 2608 |
| rhythm_toggles | YM2413 | rhythm | 32187 | 8256 | 6637 | 6080 |
| rhythm_toggles | DS1001 | melody | 32187 | 0 | 0 | 0 |
| slow_envelope | YM2413 | melody | 5371552 | 271925 | 269169 | 321797 |
| slow_envelope | YM2413 | rhythm | 5371552 | 241347 | 0 | 0 |
| slow_envelope | DS1001 | melody | 5371552 | 275232 | 272508 | 409434 |
| timer_rollover | YM2413 | melody | 10741720 | 461986 | 452873 | 446799 |
| timer_rollover | YM2413 | rhythm | 10741720 | 282018 | 0 | 0 |
| timer_rollover | DS1001 | melody | 10741720 | 461986 | 452873 | 446799 |
| rhythm_key_races | YM2413 | melody | 186148 | 5574 | 3674 | 3674 |
| rhythm_key_races | YM2413 | rhythm | 186148 | 34496 | 32262 | 32262 |
| rhythm_key_races | DS1001 | melody | 186148 | 0 | 0 | 0 |
| random_1 | YM2413 | melody | 159802 | 46959 | 18600 | 20375 |
| random_1 | YM2413 | rhythm | 159802 | 40821 | 19232 | 14607 |
| random_1 | DS1001 | melody | 159802 | 20897 | 19244 | 19689 |
| random_2 | YM2413 | melody | 187990 | 80038 | 32897 | 36000 |
| random_2 | YM2413 | rhythm | 187990 | 68762 | 33143 | 27701 |
| random_2 | DS1001 | melody | 187990 | 34499 | 31750 | 32548 |

**Single-feature probes** (YM2413, phase frame, one channel, F-number $123,
block 4):

| Probe | Carrier words differing |
|---|---|
| Plain sine | 0 |
| Vibrato, carrier only (the pitch range's row is T3, emulator tier) | 0 |
| Envelope, carrier only: attack, decay, sustain, release | 48 to 50 of ~12,000 |
| Tremolo, carrier only | 15,906 of 20,000, from sample 511 on |
| Modulator sounding (TL 16, or TL 63), with or without feedback | ~94 % |

**Findings, all OPEN** (none is settled by a document or a measurement):

- **O1. Modulation.** Wherever a modulator sounds, the model's carrier runs about
  one sample ahead of the core's. The core keeps the one-sample lag S4 measured
  (spec 6.13, T11, rung 2a's "15 then 1" test passes); C7 already records an
  emulator that removed such a delay. This one difference accounts for most of
  the table.
- **O2. Key-on latency.** From a key-on write, the model's sound starts two
  samples later than the core's (that is why the two frames differ). Spec U20
  (the sample of the phase reset) and U9 (write timing).
- **O3. Write deadline.** A write two slots before a channel's slot changes that
  slot in the core (T7) and waits a sample in the model. U9.
- **O4. Envelope step timing.** With a carrier alone, envelope steps fall one
  sample apart now and then: the shared counter's phase against reset and the
  choice of counter bits (U3, U19, U23).
- **O5. Tremolo.** The tremolo's steps fall at other samples from sample 511 on:
  the LFO's start position or its alignment with the counter (U15).
- **O6. Test register and rhythm mode.** `test_register`, `rhythm`,
  `rhythm_toggles` and `rhythm_key_races` differ in ways not yet separated from
  O1 to O3; T4, T8 to T10 and U5 to U8 are all in play.
- **O7. Built-in voices.** `each_instrument` differs on both variants. On the
  DS1001 the voices are the chip's own ROM (rung 3), so its differences come from
  O1 to O5, not the bytes. On the YM2413 the voices are emulator-tier data (T1);
  per decision P6 the differences were **not** examined voice by voice and
  nothing was inferred about the ROM.

Not done here, and why: further one-register experiments on the closed box for
O6; and any use of the model to choose among unsettled items, which needs the
owner's word (P6).

## Rung 7: the boards

sms-python's FM unit and famicom-python's mapper 85 adopt the core through api.md.
Their own judges (frame hashes, `db_vrc7`'s +11.3 dB, MAME and Mesen2 at board
level) are theirs. A change of mix level or speed is reported to them, not hidden.

## What the ladder cannot do

- It cannot prove the YM2413's built-in voices until U1 has a source. Rungs 1 to 3
  never touch them; rung 5's emulators disagree with each other.
- It cannot prove write timing within a sample, the test register on the YM2413, or
  rhythm-mode switching: only rung 6 speaks to them, and rung 6 is a detector.
- Rung 2 rests on one chip measured by one person. It is by far the best evidence
  there is, and it is still one chip.
- No rung compares against sound from a real console.

The claim rungs 0 to 3 support, and no larger one: *the core does what Yamaha's
manual says and what the openMSX project measured on a real YM2413; its DS1001
voices are the ones read out of a VRC7; its YM2413 voices are (whatever T1
decides) and are not proven.*
