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

**Status: Phase 0** (2026-10-27): scope, contract, oracles and the ladder are
written ([docs/phase0.md](docs/phase0.md)); the references are pinned
(`scripts/fetch_references.py`) and the referee harness is in `validation/`. The
core is being built against that plan.

## Licence

MIT. Nuked-OPLL (GPL-2.0), the judge, is fetched into `reference/` and built
locally as a referee; it is read for the chip's behaviour, cited by file and line,
and never copied ([docs/phase0.md](docs/phase0.md), "Licence").
