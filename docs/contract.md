# The contract: the chip's ports, its time and its outputs

What a host can rely on and what a port (a transcription into another language)
must reproduce. Checked by `tests/` and by the referee (`scripts/referee.py`); how
strongly each behaviour is known is [claims.md](claims.md).

## One engine, six parts

```python
from ym2413_python import OPLL, YM2413, DS1001

chip = OPLL(DS1001)  # the VRC7's
```

The part is a constructor argument, an `OPLLVariant`: a value, not a subclass.

| Field | `YM2413` | `DS1001` (VRC7) | `YM2413B` | `YMF281` | `YMF281B` | `YM2423` |
| --- | --- | --- | --- | --- | --- | --- |
| `instruments` | the YM2413's | the VRC7's (its debug-mode dump) | the YM2413's | the YMF281's | the YMF281's | the YM2423's |
| `output_stage` | `nmos` | `vrc7` | `b` | `nmos` | `b` | `nmos` |
| `rhythm_forced` | no | yes (no RO pin: six channels) | no | no | no | no |

`instruments` holds 21 `Instrument`s: the fifteen of the ROM (instrument numbers 1-15),
then the six rhythm half-instruments (bass drum modulator, hi-hat, tom, bass drum
carrier, snare, top cymbal). An `Instrument` round-trips through the eight register
bytes of the custom instrument ($00-$07). `VARIANTS` maps each `name` to its part.

## Time

The chip runs from one input clock, 3,579,545 Hz on a Master System, an MSX or the
VRC7's resonator. The core counts **input clocks**:

- `run(clocks)` advances that many. `clock` counts them since `reset()`.
- An **internal cycle** is four input clocks (`CLOCKS_PER_CYCLE`); a **sample** is 18
  cycles (`CYCLES_PER_SAMPLE`, 72 clocks, 49,716 Hz). `cycle` is where in the sample
  the chip is (0-17).
- **A write lands on the next internal cycle.** `write(port, value)` puts the byte on
  the bus and raises the port's strobe; the chip sees the strobe's edge on the
  cycle after it rose. A second strobe on the same port on the very next cycle is not
  a new edge (the bus byte has changed, though).
- The host owns the conversion from its own clock. sms-python's Z80 runs from the
  same crystal (one input clock per T-state); the VRC7's resonator is not locked to
  the NES CPU and a host takes it as two input clocks per CPU cycle.

Yamaha's catalog asks for 12 input clocks after an address write and 84 after data;
the core accepts anything, as the chip does, and does what the chip does with it.

## Power-on

`OPLL(variant)` and `reset()` are /IC: every register cleared, every slot in release
at full attenuation (127), the instrument registers zero. The DS1001's rhythm mode is
on from reset.

## The port

| A0 | API | Behaviour |
| --- | --- | --- |
| 0 | `write(0, value)` | The address. $00-$0F also select an instrument, rhythm or test register for the next data write; $10-$3F a channel register; $40-$FF nothing. |
| 1 | `write(1, value)` | The data. $00-$07, $0E and $0F take it on the next cycle. $10-$38 take it when the chip's sequencer next reaches that register's channel slot (the low nibble must equal the cycle, so $19-$1F alias channels 0-6 at cycles 9-15). |

The chip has no readable register: the test outputs on /WE high are not modelled.

## The outputs

`take_outputs()` returns, per internal cycle since the last call, `(mo, ro)`: the
signed words the melody and rhythm pins' DAC is driven with that cycle, as the chip
multiplexes them, one slot per cycle. That is the contract, and what the judge
compares. On the YM2413 and YMF281 a silent slot drives its sign (0 or 1); on the B
parts 0; the DS1001 drives MO only.

`take_samples()` sums each whole sample's 18 cycles per pin: the level a board's
analogue filter integrates, a convenience. Cycles of an unfinished sample wait for
the next call.
