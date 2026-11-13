# The API

The whole public surface is the six names in `ym2413_python.__all__`. Written
for the two boards that use the chip: sms-python (the Mark III FM Sound Unit and
the Japanese Master System) and famicom-python (the VRC7, mapper 85).

```python
from ym2413_python import OPLL, YM2413, DS1001, CLOCKS_PER_CYCLE, CYCLES_PER_SAMPLE

chip = OPLL(YM2413)           # or OPLL(DS1001) for the VRC7
chip.write(0, 0x30)           # port 0: latch a register address
chip.write(1, 0x10)           # port 1: data to the latched address (it stays latched)
chip.run(clocks)              # advance by input clocks (3.579545 MHz on both machines)
pairs = chip.take_outputs()   # [(melody, rhythm), ...], one pair per finished sample
values = chip.take_samples()  # [melody + rhythm, ...], the same samples
chip.reset()                  # the /IC pin, or the VRC7's sound-reset bit ($E000 bit 6)
```

## Time

- `CLOCKS_PER_CYCLE = 4`: input clocks in one slot, one pass through the chip's
  single operator circuit (spec 2.3).
- `CYCLES_PER_SAMPLE = 18`: slots in one output sample. A sample is 72 input
  clocks: 49,716 Hz at 3.579545 MHz (spec 2.2).
- `run(a); run(b)` is the same as `run(a + b)`: the core keeps its place inside a
  slot between calls.
- A data write acts from the next slot boundary (PROVISIONAL, T7). The waits
  Yamaha asks for (12 clocks after an address, 84 after data) are not enforced.

## Output

The chip's fact is a train of nine-bit words, one per slot, on two pins (MO for
melody, RO for rhythm), -255 to +255 with two zeros (spec section 12). What the
core hands back is a choice (T6):

- `take_outputs()` returns, for each sample finished since the last take, the sum
  of that sample's melody words and the sum of its rhythm words, as integers.
  Each percussion word appears twice on RO, as the chip outputs it (spec 11.12),
  so it is counted twice. A word counts as its signed size; both zeros count 0.
- `take_samples()` returns melody + rhythm for the same samples.
- The board scales and filters. Neither the DAC's non-linearity (spec 12.5) nor
  the output polarity (U10) is modelled.

On the DS1001 the rhythm number is always 0: it has no RO pin, and channels 6 to
8 are never heard (spec 1, 11.14; T15).

`chip.trace` is for validation: set it to a list and each sample appends its
eighteen `(melody word, rhythm word)` pairs in the chip's own one's-complement
form (-1 is minus zero). Leave it `None` otherwise.

## Variants

`YM2413` and `DS1001` are frozen `OPLLVariant` records of plain values. No logic
asks which variant it is running; it reads the fields (`voices`, `channels`,
`rhythm_output`, `rhythm_forced`, `snare_last_byte`, `vibrato_offsets`,
`test_bits`, `hi_hat_phases`, the fixed rates, `reset_clears_vibrato`,
`reset_noise`). Each field's docstring says where its value comes from and
whether it is documented, measured or PROVISIONAL. A new variant is
`dataclasses.replace(YM2413, ...)`.

**The YM2413's fifteen melodic voices are not a dump of the chip** (T1): they
are emu2413's hand-tuned table, emulator tier, until a read-out of the ROM exists.
The DS1001's are the chip's ROM as read out through its debug mode.

## State

Every piece of state is a plain attribute (ints, lists of ints, one bytearray),
fewer than 80 of them (PyPy's limit for a fast instance), so a board's save-state
walker can copy it out and back. `variant` is configuration and never changes.
`tests/test_contract.py` checks both.

## Speed

About 11 times real time on PyPy 3.11 with nine channels sounding. The core
computes slot by slot; there is no whole-sample fast path (T16).
