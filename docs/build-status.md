# Build status, 2026-11-13 (session stopped early)

Written for whoever continues, with no memory of the session assumed. Read
[restart.md](restart.md), [handoff-brief.md](handoff-brief.md) and
[provenance-audit.md](provenance-audit.md) first.

## Commits of this session

| Hash | What |
|---|---|
| `ee92fa5` | Provenance audit of the spec; spec and hand-off brief amended |
| `1c0e6cf` | The core (`src/ym2413_python/`), `pyproject.toml`, CI file, `seed/streams.py` moved to `validation/streams.py` |
| `46447ca` | Rung 0 (`tests/test_contract.py`) and rung 1 (`tests/test_manual.py`) |
| `389f9c6` | Work in progress: rung 2a (`tests/test_measured.py`) |

## Done and checked

- **Provenance audit: complete.** Every numbered statement of `spec.md` (sections
  1 to 14) has a row in `provenance-audit.md`. None remains unaudited. Struck or
  restated: 7.8 (vibrato rows other than the top one: now emu2413's table,
  emulator tier), 11.9 (the cymbal's particular form and sign: emu2413's),
  11.10 (the hi-hat's four phases: emu2413's), 8.12 and 8.7 (counter alignment:
  a choice), 10.2 (restated from the measured durations), 6.5, 6.11, 6.12, 6.13
  (restated; feedback amount now from Yamaha's Table III-6; lag direction a
  choice), 5.5 (chain written out). New unknowns U22, U23, U24.
- **The core** runs: about 11 times real time on PyPy 3.11 for one second of
  chip time, so the "whole sample in one pass" fast path was not written.
- **Rung 0**: 24 tests passed (last run before `test_measured.py` was added).
- **Rung 1**: 229 tests passed in `tests/test_manual.py` (all 60 rows of the
  decay table, the attack table, Tables III-1, III-2, III-3, III-5, III-6,
  III-8-2, III-9).
- Two findings worth keeping: the noise register as written (feedback from
  stages 0 and 14, stepped per slot) gives, seen every 18th step, exactly the
  recurrence S4's 120 printed snare bits satisfy; and the operator arithmetic
  gives S4's measured peak widths of 342 and 332 samples at levels 112 and 113.

## Rung 2a triage (second session, 2026-11-13)

`tests/test_measured.py` was run and each of its 32 failures decided against
`spec.md`. Now **445 tests pass** (24 contract, 229 manual, 192 measured), and
`ruff check` and `ruff format --check` (0.16.8, the pinned version) are clean.

**One change to the core, from the spec, not from a test.** The core reset each
operator's phase when that operator's own damp ended (a CHOICE under U20). Spec
7.10 says "both of a channel's phase counters are set to zero when the envelope
leaves the damp state". The two differ when a modulator was held through key-off
(spec 8.23) and damps from a low level while the carrier's damp ends at once. Now
the carrier's damp end resets both, in the same sample, before either steps; the
modulator's slot comes first, so it resets itself when it sees its carrier about
to leave damp. The single-operator percussion sounds still reset only their own
phase. The exact sample is still CHOICE (U20). New test:
`test_the_carriers_damp_end_resets_both_phases`.

**Open, written down, not fixed.** With a sounding, sustained modulator, notes
played again after a key-off do not repeat sample for sample: under T14 the
modulator damps from its held level on every key-on, and where its damp steps fall
depends on the free-running counter. S4's "each time the same note is played, the
wave looks exactly the same" may be a visual remark, or may count against T14
(U13). No document settles it; T14 stands.

**Faults of the tests** (31 of the 32), each checked against the spec:

- The modulation and feedback reference left out the sample in which damp ends;
  that sample already sounds (U20 choice). With it, all six depth and six feedback
  cases match the separate writing of the operator exactly.
- `test_the_sine_has_1024_steps`: block 1 gives 4 samples a step, not 8; block 0.
- `test_the_modulator_is_one_sample_out_of_step`: a bound of 192 on run lengths
  had no source; the long runs are the spec's arithmetic (the reference agrees).
- Half-period crossing: the test compared 16 words exactly; S4's "overlap" is
  taken as the sign change falling on the same sample at every depth (it does, at
  samples 8192 and 16384). The sine table has no exact zero (6.3).
- Note repeated: PLAIN_SINE has RR 0, so the carrier never released.
- Flat-segment means of 512/3 and 256/3 cannot be hit to two decimals by a finite
  window; checked to 0.05 and as {floor, ceil} lengths.
- Decay rate 9: the row was [2048 ×3, 1024 ×2]; spec 8.5 gives s = 11, so
  [4096 ×3, 2048 ×2]. S4's prose confirms rate 9 without printing its cycle; the
  row was the earlier session's own arithmetic. Rate 25: window too short.
- First segments: starts every $155 samples missed lengths; every $40 finds
  exactly S4's sets for AR 4/DR 2 and AR 5/DR 2 at blocks 2, 4, 6.
- Attack from 124: `trace[:start]` excluded the 124 itself.
- Instant attack: MULTI 1 is a 16-sample period; MULTI 4 is the quarter-rate tone
  the comment meant. The level-0 check is the measured part; the word 255 rests
  on the U20 choice.
- Key-off from decay: SL 0 never decays; SL 15.
- Modulator without release: DR 4 at block 4 needs ~13,000 samples to reach 16;
  the percussive half now compares with a twin chip that keeps the key on.
- Bass drum: volume 3 kept the peak at 86; volume 0.
- Cymbal: "≤ 3 sizes" had no source; now the size never rises after the peak.
- Aliases: 0x18 cleared F-number bit 8, leaving F-number 0; 0x19.
- Scaffolding removed: `first_segments`, the dead loop in
  `test_decay_step_lengths`, the dead half of `test_the_snare_table`.

Lint fixes were mechanical (`itertools.pairwise`, one `min`, the fetch script
made executable, formatting).

## Rungs 3 and the provisional record (second session, 2026-11-13)

- `tests/test_community.py` (rung 3, every test tier 3): the DS1001's 15 voices
  and 3 drum rows equal the pinned NESdev wiki table (parsed at test time from
  famicom-python, skipped if absent); each ROM voice of both variants plays as
  its row loaded as the user tone; six channels and no rhythm on the DS1001; the
  reset bit (registers and tremolo cleared, vibrato kept); the four test bits;
  the wiki's frequency formula; SMS Power's rhythm set-up plays all five sounds.
  **One open difference, recorded as a strict xfail, not fixed:** S6 says test
  bit 2 makes the output silent; with a sounding modulator the core's carrier is
  moved by the modulator's output at phase 0, which is not zero (spec 6.3), so a
  small word is heard. No document says how the chip avoids it.
- `tests/test_provisional.py`: one labelled test for each of T1 to T15 and U20,
  U22, U23, U24, pinning the default so that changing it is deliberate.
- **514 tests pass, 1 xfailed** (the open item above). Lint clean.

## Rung 6: Nuked-OPLL as a closed box (second session, 2026-11-13)

Pinned at `1269cf5` (`scripts/fetch_references.py`); `validation/nuked_harness.c`
uses only `OPLL_Reset`, `OPLL_Clock`, `OPLL_Write`; `validation/closed_box.py` runs
every stream of `validation/streams.py` on both variants in two alignment frames
and reports per pin. Results and the open findings O1 to O7 are in
`docs/validation.md`, rung 6. **No core change came from it; nothing was tuned.**
The main finding: wherever a modulator sounds, the model's carrier runs about a
sample ahead of the core's, which keeps S4's measured lag (T11, C7). Plain sines
and vibrato agree on every slot.

## Not started

- Rung 2b (S4's capture files in place), rung 5 (emu2413 as a detector).
  Further one-register experiments on the closed box for finding O6.
- `validation/faults.py`.
- `README.md` (still the Phase 0 text), `docs/claims.md`, the update of
  `docs/validation.md`, `docs/api.md` (T6's integer outputs and `trace`).
- What sms-python and famicom-python must change.

## Not read, and why

- `/data/backup/nuked-derived/`, any Nuked `.c`, GPL emulators, the boards' FM
  source: forbidden. Not opened.
- S4's `.cc`/`.hh` files, every code fence and code-like line in its write-ups,
  `rhythm.md` between "## Nuke.YKT" and "## [2020/01/02] Update", the numeric
  tables of `20150320.txt`, `am.txt`, `20151201.txt`: hidden by a filter
  (`reference/scratch/prose.py`, git-ignored).
- S4's `attack-rates.txt`, `formula-f1-4.txt`, `predicted-sine.txt`: not needed.
- `reference/scratch/attack_f.txt` (left by Phase 0): contents unknown, may be
  code. Not opened.
- ymfm: not opened this session. S2, S7, S8, S9, S11: not re-read.

## Rule slips, however small

1. Formula lines inside S4's running text were displayed (phase step,
   "eg_shift = 13 - (rate / 4)", "m = 16 - (rate / 4)").
2. Two rows of an emulator-derived key-scale table in `ksl.txt` were displayed;
   the same numbers follow from Yamaha's Table III-5 and the core computes them
   from that.
3. S4's numbered list of sixteen boolean forms for the cymbal was read (running
   text, not a code block).
4. More of emu2413 (MIT) was read than its tables: its percussion functions,
   key handling, and the carrier, modulator and exponential look-up functions
   beside them. Permitted, but the brief said port no code; none was ported.
   The opll.py arithmetic was written from the spec; a reviewer may wish to
   compare `_operate` with emu2413's `lookup_exp_table` for independence.
5. A test log was first written to `validation/build.log` (not ignored) and
   then moved into the ignored `validation/build/`. It was never committed.
6. A hung pytest process of my own was ended with `kill`.
7. Second session: a grep of `20150320.txt` through `prose.py --tables`
   displayed the same `eg_shift` formula line as slip 1 (the filter does not
   catch it). Nothing was taken from it; spec 8.5 already states the rule.
8. Second session: Nuked-OPLL's `opll.h` (allowed) declares the model's whole
   state structure; its field names were seen, among them names for rhythm-mode
   phase bits. Nothing was taken from them: the provisional cymbal form (T8)
   predates this and was not changed, and the harness does not touch the
   structure.

All of these are also in `provenance-audit.md` except 5 and 6.

## Next steps, in order

1. Done (rung 2a triage above).
2. Done (rung 3 and the provisional record above).
3. Done; keep it clean.
4. Done (rung 6 above). Was: extend `scripts/fetch_references.py` with a pinned Nuked-OPLL (header,
   LICENSE, README may be opened; `opll.c` never). Write
   `validation/nuked_harness.c` and `validation/closed_box.py` after
   sn76489-python's; feed `validation/streams.py`. Record differences as open;
   do not open the source, do not tune.
5. Rung 5 with emu2413 if brief; rung 2b if the capture format is clear.
6. `validation/faults.py` after sn76489-python's, under two minutes.
7. README, `docs/claims.md`, `docs/validation.md`, `docs/api.md`.
8. Final commit; never push.
