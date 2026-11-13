# Validation ladder (proposed)

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

**Two uses that need the owner's word first** (decisions P6 and P3): using the
closed box to recover the YM2413's instrument ROM by searching for the user tone
that reproduces each built-in voice exactly, and using it to choose among spec.md's
unsettled items (U4, U5, U7, U8, U9). Both go beyond "a difference says where to
look"; both are, in rule 8's words, "further measurements of the model's outputs".

**Exit**: a table of differences per stream in the README, with each difference
either traced to a documented or measured statement (and fixed, on that
statement's authority) or listed as open. The README says the model was run and
its code was not read.

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
