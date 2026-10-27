# ym2413-python

A readable, pure-Python reference core of Yamaha's **YM2413** (OPLL) FM sound
generator and the parts built from it: Konami's **VRC7** sound (DS1001), the
YM2413B, the YMF281 and the YM2423. Nine two-operator FM channels (or six and five
rhythm sounds), a ROM of fifteen instruments plus one programmable, vibrato and
tremolo, and the time-multiplexed 9-bit DAC on the melody (MO) and rhythm (RO) pins.

It is a chip in the family's shape (chips are cores, boards compose cores), beside
[z80-python](https://github.com/alewman/z80-python),
[ym2612-python](https://github.com/alewman/ym2612-python) and
[sn76489-python](https://github.com/alewman/sn76489-python). Two boards need it:
[famicom-python](https://github.com/alewman/famicom-python) for the VRC7
(*Lagrange Point*) and sms-python for the Master System's FM sound unit.

## Validation

| What | Result | Tier |
| --- | --- | --- |
| MO and RO at every internal cycle against Nuked-OPLL @ 1269cf5: 20 synthetic streams, six parts | **126,612,624 cycles, 0 different** | die-derived (the judge) |
| The same, music recorded from the boards: *Lagrange Point* (VRC7) and five Master System FM soundtracks | **805,042,105 cycles in all, 0 different** | die-derived |
| The log-sine and exponent ROMs, generated from their formulas | equal to the die's word for word | die-derived |
| The VRC7's fifteen instruments | equal to its debug-mode dump byte for byte | hardware |
| 30 seeded faults | 30 caught by the referee; 29 by the 14 conformance examples alone | not an oracle |

What each result supports is [docs/claims.md](docs/claims.md); the runs are
[docs/validation.md](docs/validation.md); the API is [docs/contract.md](docs/contract.md);
a port proves itself with [docs/conformance.md](docs/conformance.md); how the work
was planned is [docs/phase0.md](docs/phase0.md).

## Minimal host

```python
from ym2413_python import OPLL, YM2413

chip = OPLL(YM2413)
for register, value in ((0x30, 0x10), (0x10, 0x81), (0x20, 0x19)):  # violin, about 440 Hz
    chip.write(0, register)
    chip.run(12)  # input clocks, as Yamaha's catalog asks between address and data
    chip.write(1, value)
    chip.run(84)
chip.run(3_579_545 // 10)  # a tenth of a second
samples = chip.take_samples()  # [(mo, ro), ...] at 49,716 Hz, each the sum of 18 cycles
```

## Install and test

```text
python -m pip install -e ".[dev]"
python -m pytest                                  # referee tests skip without it
python scripts/fetch_references.py                # Nuked-OPLL, detectors, documents
sh validation/build_referees.sh                   # the judge, locally
python scripts/referee.py                         # every stream, every part
```

Python 3.11 or newer (the newest PyPy supports). No dependencies. **Status**
(2026-10-27): the core holds rungs 0-3; adoption by famicom-python and sms-python
is next.

## Licence

MIT. Nuked-OPLL (GPL-2.0), the judge, is fetched into `reference/` and built
locally as a referee; it is read for the chip's behaviour, cited by file and line,
and never copied ([docs/phase0.md](docs/phase0.md), "Licence").
