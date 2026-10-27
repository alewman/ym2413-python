# Phase 0: what this core is, what judges it, and how it gets built

Written 2026-10-27 to start the work. The decisions marked **(decided)** were made
here so the build could proceed while Aubrey was away; each says why and can be
reversed before anything leaves this repository.

## Why a core

The YM2413 is one chip used by several machines: the Master System's FM sound
unit (Japan's Mark III and Master System), MSX-MUSIC, and, as Konami's DS1001,
the VRC7 in the Famicom's *Lagrange Point*. By the family's extraction rule a chip
more than one machine needs becomes its own core; famicom-python and sms-python
are its first two users. Nothing of it exists in either board yet (famicom-python
has no mapper 85; sms-python has no FM unit), so this is a new core, not an
extraction.

## Scope

| Part | What differs | In scope |
| --- | --- | --- |
| **YM2413** (OPLL) | the reference: 9 channels or 6 + 5 rhythm, MO and RO pins | yes, first |
| **DS1001** (VRC7) | its own 15-instrument ROM (dumped from a real chip in debug mode: VRC7_audio.wiki); rhythm mode stuck on with no RO pin, so six channels; a different output stage | yes, second |
| YM2413B, YMF281, YMF281B | the B parts' output stage; the YMF281's instrument ROM | yes, as data |
| YM2423 (OPLL-X) | its instrument ROM | yes, as data |
| YM2420 (OPLL2) | its frequency registers are laid out differently | later |

What differs between parts is data on a variant value, as sn76489-python's
`PSGVariant`, not subclasses.

## The contract (draft)

```python
from ym2413_python import OPLL, YM2413, DS1001

chip = OPLL(YM2413)
chip.write(0, 0x10)  # A0 = 0: the address
chip.run(12)  # input clocks; the catalog asks 12 between address and data
chip.write(1, 0x40)  # A0 = 1: the data
chip.run(84)  # and 84 after data
outputs = chip.take_outputs()  # [(mo, ro), ...], one per internal cycle
```

- **Time**: the host counts **input clocks** (3,579,545 Hz on an NTSC Master System
  or MSX; 3,579,545 Hz on the VRC7's board too, from its own crystal). One internal
  cycle is four input clocks; one sample is 18 cycles (72 clocks, 49,716 Hz).
  `run(clocks)` advances; a write lands on the next cycle. (decided: input clocks,
  as sn76489-python, so the host never knows the divider.)
- **Outputs**: per internal cycle, the two numbers the DAC is driven with that
  cycle, MO and RO, as the chip multiplexes them: one slot each per channel
  and operator. `take_outputs()` hands them over; `take_samples()` sums each
  sample's 18 cycles per pin, the level a board's analogue filter integrates.
  (decided: the cycle values are the contract, because they are what the judge
  compares; the sample sums are a convenience.)
- **Registers**: the YM2413's map ($00-$07 the custom instrument, $0E rhythm, $0F
  test, $10-$38 the channels). The test register is modelled, since the judge
  models it and games never write it.

## Oracles and tiers

| Oracle | Tier | Role |
| --- | --- | --- |
| Yamaha, *YM2413 catalog* (1996-06, Bitsavers) | manufacturer | the programmer's model: pins, register map, instrument list, write timing |
| VRC7 instrument ROM dumped through the chip's debug mode (siliconpr0n; VRC7_audio.wiki) | hardware | the DS1001's instruments |
| **Nuked-OPLL** @ 1269cf5 (nukeykt, from the VRC7's die shot; YM2413 differences from Yamaha's parts) | die-derived | **the judge**: MO and RO every internal cycle, every variant |
| emu2413 @ a1d5120 (MIT), ymfm @ 81aec25 (BSD-3) | emulators | detectors: where they and the judge differ, the judge wins; where the judge is silent, they are evidence only |

Nuked-OPLL marks two of its own corners as uncertain (opll.c:844 "TODO: This might
be incorrect", the RO multiplexing; :975 "Not quite true", the rhythm output on
other cycles). Those stay open claims however well the core matches it.

## The ladder

0. **Tables and data.** The log-sine and exponent ROMs generated from their
   formulas and checked equal to the die's (pinned by SHA-256); each variant's
   instrument ROM equal to its source (the VRC7's to the debug-mode dump).
1. **Every cycle against Nuked-OPLL, synthetic streams.** Register writes that
   exercise one thing each: every instrument, the custom instrument, key-on and
   -off at awkward moments, every envelope rate, sustain, KSL/KSR, vibrato and
   tremolo, feedback, both rhythm modes, the test register bits, write timing
   closer than the catalog asks. Every variant.
2. **Every cycle against Nuked-OPLL, music.** Register streams from real software:
   Master System FM and MSX-MUSIC logs (VGM files, fetched, never committed) and,
   once the boards drive it, *Lagrange Point* from famicom-python.
3. **Seeded faults** (mutation testing), and a conformance kit (text traces with
   expected outputs) for transcriptions, as the other cores have.
4. **Adoption**: famicom-python's VRC7 (mapper 85 with its sound, at the measured
   +11.3 dB level, docs/undocumented-behavior.md) and sms-python's FM unit.

Speed is not a goal (the reference boards are correct, not fast); a Rust
transcription and its -fast fork would come later, as for the YM2612.

## Licence (decided)

The core is MIT, like the family. Nuked-OPLL is GPL-2.0, a stronger licence than
Nuked-OPN2's LGPL-2.1 that ym2612-python cites. So: Nuked-OPLL is fetched into
`reference/` (ignored), built locally as the judge by `validation/opll_ref.c`, which
only drives it, and read for the chip's behaviour, cited by file and line; its code
is not transcribed. The core is written from the manual, the wiki, the permissive
emulators and the facts the judge establishes (tables and instrument data are
measurements of silicon, not code). Where the core's structure must follow the
die's pipeline to agree cycle by cycle, it is written in this repository's own
words and names.

## Decisions

- The licence approach above: approved (2026-10-27), MIT like the family's cores.
- Public: yes (2026-10-27), as the other chip cores.
- Still open: whether the VRC7's output level in famicom-python stays rainwarrior's
  +11.3 dB (AV Famicom) or also takes NewRisingSun-style recordings if any turn up.
