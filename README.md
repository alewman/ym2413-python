# ym2413-python

The Yamaha YM2413 (OPLL) FM sound chip, and the VRC7's DS1001 variant, as a
readable pure-Python core for the family's boards (sms-python's FM unit,
famicom-python's mapper 85). No runtime dependencies. PyPy 3.11 is the supported
interpreter.

```python
from ym2413_python import OPLL, YM2413

chip = OPLL(YM2413)
for register, value in ((0x30, 0x30), (0x10, 0x20), (0x20, 0x17)):
    chip.write(0, register)   # latch an address
    chip.write(1, value)      # piano, full volume; F-number $120, block 3, key on
    chip.run(84)
chip.run(3_579_545)           # one second of the chip's clock
pairs = chip.take_outputs()   # one (melody, rhythm) pair per 72 clocks
```

[docs/api.md](docs/api.md) is the whole surface.

## Status

**Built from documents.** The code is written from [docs/spec.md](docs/spec.md),
which is written from the sources listed in [docs/phase0.md](docs/phase0.md);
[docs/provenance.md](docs/provenance.md) gives every statement's chain and the
decisions taken where no source settles a question. Every rule in the code names
its spec section, or says CHOICE or PROVISIONAL. The rules it is written under
are in [docs/restart.md](docs/restart.md).

What it supports, and no more: *the core does what Yamaha's application manual
says, reproduces what the openMSX project reports measuring on one real YM2413,
and plays the DS1001's own instrument ROM as the NESdev wiki gives it.* **No
recording of a console is in hand, so nothing here is claimed exact to a
console.** The YM2413's fifteen built-in melodic voices are an emulator's
hand-tuned table, not a dump: the largest gap. [docs/claims.md](docs/claims.md)
lists each claim with its evidence; [docs/validation.md](docs/validation.md)
says what was run and what it showed.

- 514 tests pass on PyPy 3.11 (rungs 0 to 3 and the provisional behaviours),
  plus one expected failure recorded as an open difference.
- `validation/faults.py` breaks the core in 30 ways; every fault is noticed.
- Nuked-OPLL was run as a closed box and **its source was not read**
  (`validation/closed_box.py`). Plain sines and vibrato agree on every slot;
  the differences elsewhere are written down as open, and nothing was tuned to
  it. The largest: the model leaves out the one-sample modulator lag that the
  openMSX measurements show and this core keeps.
- About 11 times real time on PyPy with nine channels sounding.
- Used by sms-python (the FM unit) and famicom-python (the VRC7). Not on PyPI.
- [ym2413-rust](../ym2413-rust) is a Rust port, proven equivalent to a pinned
  revision of this core.

## What is known, and how

*documented*: a document says so (tier 2 is Yamaha, tier 3 a community author
who tested on hardware). *measured*: a capture from hardware says so (here, the
openMSX project's write-ups). *provisional*: no source settles it; the value is a
decision, held as data on the variant or labelled in the code. Spec section
numbers in brackets.

| Behaviour | `YM2413` | `DS1001` |
|---|---|---|
| Register map, write protocol, slot order [2-4] | documented, tier 2 | documented, tier 3 (S6) |
| Built-in melodic voices [5.4, 5.5] | **provisional**: emu2413's hand-tuned table (T1) | documented, tier 3: the chip's ROM, read out |
| Percussion settings [5.6] | measured as fits; snare byte disputed (C4) | read out (not heard: no rhythm pin) |
| Sine and exponential ROMs, operator arithmetic [6.1-6.10] | measured (via the OPL2/OPL3 ROM read-outs) | assumed the same (U16) |
| Modulation, feedback, the one-sample lag [6.11-6.13] | measured; the lag's mechanism a choice (T11) | assumed the same |
| Phase generator [7.1-7.6] | measured | assumed the same |
| Vibrato [7.7, 7.8] | top pitch range measured approximately; the rest provisional (T3) | as left |
| Envelope rates, attack, states [8] | measured; the alignment of rates 48 to 59 a choice (U23) | assumed the same |
| Key scaling [9] | documented and measured | assumed the same |
| Tremolo [10] | measured | assumed the same |
| Rhythm mode [11] | measured, with provisional percussion phases (T8, U22) | none: no rhythm output |
| Test register [13] | **provisional**: the VRC7's account (T4) | documented, tier 3 |
| State after reset [14] | **provisional** (T5) | registers, tremolo cleared; vibrato kept: tier 3 |
| Write timing inside a sample [3.4] | **provisional** (T7) | as left |

## Layout

- `src/ym2413_python/`: `opll.py` (the chip), `tables.py` (ROMs and tables, each
  with its source), `variants.py` (the two parts as data).
- `tests/`: `test_contract.py` (rung 0), `test_manual.py` (rung 1, Yamaha),
  `test_measured.py` (rung 2a, the openMSX measurements), `test_community.py`
  (rung 3), `test_provisional.py` (the decisions).
- `validation/`: `streams.py` (synthetic register streams: test inputs, not a
  model), `faults.py` and `closed_box.py` (rung 6). The rung's harness,
  `nuked_harness.c`, is linked with Nuked-OPLL, so it is a GPL tool kept outside
  this repository: set `YM2413_GPL_TOOLS` to the folder that holds it.
- `scripts/fetch_references.py`: fetches and verifies the pinned references into
  the git-ignored `reference/`. Nuked-OPLL is fetched for the closed box only;
  its `opll.c` is compiled and never opened.
- `docs/provenance.md`: where each fact comes from, the decisions taken, what was
  not read and why, and what was seen and not used.

```sh
python -m pytest                       # all rungs
python validation/faults.py            # can each rung fail?
python validation/closed_box.py        # the closed-box comparison (needs a C compiler)
```

## History

This core was rebuilt in November 2026. Its predecessor followed a GPL-licensed
model's source code too closely to be published under the MIT licence, and was
withdrawn. This version is written from manufacturer documents and hardware
measurements under the rules in [docs/restart.md](docs/restart.md); the model is
only run, as a closed box, to find differences.

## Licence

MIT. `variants.py` also carries emu2413's MIT notice, for its instrument table
used as data (T1, T3, U22).
