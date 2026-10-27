# Claims: what is known, how strongly, and by what

Tiers ([validation.md](validation.md)): **hardware** (a measurement of a real chip),
**die-derived** (a transcription of the silicon), **manufacturer** (Yamaha's catalog),
**emulator** (another program: evidence only).

| Claim | Tier | Evidence |
| --- | --- | --- |
| The register map, the pins, the two modes, the write timing asked of a host | manufacturer | Yamaha's YM2413 catalog (1996-06) |
| The log-sine and exponent ROMs | die-derived | generated from their formulas, equal to Nuked-OPLL's word for word; the log-sine is the YM2612's too (ym2612-python's pin) |
| The VRC7's fifteen instruments | hardware | its debug-mode dump (VRC7_audio.wiki); equal to Nuked-OPLL's |
| The VRC7's snare carrier byte ($68, the YM2413 $48) | hardware | the same dump; inaudible: the VRC7 has no RO pin, and the referee agrees either way |
| The YM2413's, YMF281's and YM2423's instruments | die-derived | Nuked-OPLL's tables; no independent dump checked here |
| Every stage of the operator pipeline, per internal cycle: phase, envelope, LFO, rhythm and noise, the register write path, the output stage, the test register | die-derived | MO and RO equal Nuked-OPLL on every cycle of 20 synthetic streams and 6 games' music (validation.md) |
| The rhythm drums' DAC slots: each drum twice, the copy equal to the first, in andete's order | hardware | andete's measurement of a real YM2413 (rhythm.md), matched slot for slot (`tests/test_rhythm_slots.py`) |
| BD and TOM levels and envelopes, keyed and released | hardware (corroboration) | 36 of andete's real-chip captures fit; off by more than one level on 1,508 of 138,128 quiet samples; louder stretches carry the ADC chain's error; a 3 dB wrong model fits every capture worse (validation.md) |
| The top cymbal's phase reaches full scale (±255) | hardware | andete's captures; Nuked-OPLL at the pin agrees (it gave ±3 dB once) |
| The VRC7 runs rhythm mode stuck on with no RO pin | die-derived | Nuked-OPLL (from the VRC7's die); the six-channel behaviour is the wiki's |

## Open

- **The rhythm outputs on other cycles**: Nuked-OPLL marks them uncertain
  (opll.c:975 "Not quite true"). The RO pin's slot order, which it also marks
  (opll.c:844), is now settled by andete's measurement (above); what a rhythm slot
  carries on the cycles andete did not sample is not.
- **SD, HH and TCY against andete's captures**: fitting them needs the noise
  generator's state or a free-running phase counter; not done.
- **The analogue output**: the DAC's levels, its non-linearity and the parts'
  output filters are the boards' business (each board measures its own mix level).
- **The YM2420** (OPLL2), whose frequency registers are laid out differently, is
  not modelled.
- **The test outputs** (/WE high) are not modelled.
