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

## Done but not checked

- **`tests/test_measured.py` (rung 2a): 159 pass, 32 fail** on its first and
  only run. The failures have NOT been looked at. Some are surely faults of the
  tests (the file was written in one go and contains leftover scaffolding:
  `first_segments`, the muddled loop in `test_decay_step_lengths`, dead code in
  `test_the_snare_table`). Some may be real faults of the core. Failing:
  `test_feedback` (all six; two say `assert 6 == 0`: `previous` is not 0 after
  the damp-end sample, so the helper's "nothing remembered" assumption is
  wrong, and `test_modulator_into_carrier` passing suggests only feedback start
  state differs), `test_every_half_period...`, `test_each_time_the_same_note...`,
  four `test_flat_segment_lengths` rows with F-number 3, `test_decay_step_lengths[9]`,
  the three `first_segment` tests (one raises StopIteration), the 124 attack
  sequence, `test_attack_15_is_instant_only_when_damp_ends`,
  `test_key_off...[decay]`, `test_a_modulator_has_no_release`,
  `test_confirmed_effective_rates[...25]`, the bass-drum-equals-user-tone test,
  the top-cymbal test, `test_aliases_of_the_channel_registers`.
  **Do not tune the core to make them pass: for each, decide from the spec
  whether test or core is wrong.**
- `ruff check` and `ruff format --check` have not been run at all.
- `.github/workflows/ci.yml` is copied from sn76489-python unchanged (it already
  matches what was asked); not exercised.

## Not started

- `tests/test_community.py` (rung 3: DS1001 voices against the pinned wiki file,
  reset bit, test register, six channels).
- `tests/test_provisional.py` (one labelled test per T1 to T15 and U22 to U24).
- Rung 2b (S4's capture files in place), rung 5 (emu2413 as a detector), rung 6
  (Nuked-OPLL closed box: nothing fetched, no harness, `fetch_references.py`
  not extended). **No detector has been run; no constant was tuned to one.**
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

All of these are also in `provenance-audit.md` except 5 and 6.

## Next steps, in order

1. `.venv-pypy/bin/python -m pytest -q tests/test_measured.py` (7 seconds; write
   output to `validation/build/`). Go through the 32 failures one by one against
   `spec.md`. Tidy the scaffolding named above.
2. Write `tests/test_community.py` and `tests/test_provisional.py`.
3. `ruff check .` and `ruff format --check .`; fix.
4. Extend `scripts/fetch_references.py` with a pinned Nuked-OPLL (header,
   LICENSE, README may be opened; `opll.c` never). Write
   `validation/nuked_harness.c` and `validation/closed_box.py` after
   sn76489-python's; feed `validation/streams.py`. Record differences as open;
   do not open the source, do not tune.
5. Rung 5 with emu2413 if brief; rung 2b if the capture format is clear.
6. `validation/faults.py` after sn76489-python's, under two minutes.
7. README, `docs/claims.md`, `docs/validation.md`, `docs/api.md`.
8. Final commit; never push.
