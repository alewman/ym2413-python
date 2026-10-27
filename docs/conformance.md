# Conformance: proving another core is the same chip

For someone writing a YM2413 core in another language who wants to use this one as
the reference: what "the same chip" means here, the manifest and trace formats, and
what a port may claim. The tooling is `ym2413_python.conformance`; the shape is the
family's (z80-python's, ym2612-python's, sn76489-python's kits).

## What must match

At every internal cycle (four input clocks), the two words the DAC is driven with:
**MO** and **RO**, exactly as `take_outputs()` returns them. Nothing analogue.

## The manifest

```json
{
 "version": 1,
 "name": "rhythm-ym2413",
 "variant": "YM2413",
 "clocks": 72928,
 "events": [
  {"t": 256, "kind": "address", "data": 22},
  {"t": 268, "kind": "data", "data": 32}
 ]
}
```

| Key | Meaning |
| --- | --- |
| `variant` | a part's name: `YM2413`, `DS1001`, `YM2413B`, `YMF281`, `YMF281B`, `YM2423` |
| `clocks` | run to this many input clocks after /IC |
| `events` | in clock order. Before an event at `t` the chip is run to `t` input clocks; `address` writes A0 = 0, `data` A0 = 1 |

## The trace

```text
# ym2413-trace 1
# rhythm-ym2413 YM2413
S 0 e7cd5f0f 17 17
S 1 10a034f0 18 18
...
# end 72928 clocks 1012 samples 44 writes
```

One `S` line per sample (18 internal cycles): the sample's number, the CRC-32 (zlib's)
of its 36 words, (MO, RO) per cycle in order, each a little-endian signed 16-bit
value, and each pin's words summed. The CRC pins every cycle's value; a difference
names the sample, and the referee (`scripts/referee.py`) names the cycle. The header
line names the format version: a trace of another version is refused, not misread.
`#` lines are compared too, so a port writes them exactly.

## Running it

```text
ym2413-conformance run examples/conformance/rhythm-ym2413.json   # a trace to stdout
ym2413-conformance check examples/conformance                    # every example
```

## The examples

Fourteen, in `examples/conformance/`, each checked against Nuked-OPLL when it was made
(`scripts/make_examples.py`): the instrument ROMs of four parts, feedback with both
half-sines, rhythm mode on three output stages, envelope rates and the sustain bits,
MULTI and KSL across every key-scaling row, the LFOs (test bit 3 runs them every
sample, so a whole cycle fits in a short trace), the test bits, writes faster than the
catalog asks, and rhythm toggled against key-ons.

## What a port may claim

Passing every example: the same chip as this core on what the examples exercise, which
catches 29 of the 30 seeded faults of `scripts/mutation.py --examples-only`. The one it
misses, the envelope timer's shift lock past bit 13, shows only at the timer's 2^17
rollover, over ten seconds of chip time, too long for a committed trace: a port that
wants it runs the referee's `timer_rollover` stream. Equal to Nuked-OPLL on every
cycle is this core's claim (validation.md), and a port earns it the same way, against
the referee.
