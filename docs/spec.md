# Behaviour specification

Written 2026-11-12 from the sources in [phase0.md](phase0.md), in this
repository's own words. Source IDs (S1, S4, ...) are that document's. No statement
here comes from a GPL or LGPL program or from the withdrawn core.

**Audited 2026-11-13** before the core was written: every statement was checked
against the prose of its source, and its chain (source, author, how established,
what is upstream) is in [provenance.md](provenance.md). Statements the
audit struck or changed say so below ("audit:"). Where a number's only support
was a code fragment or a table copied from a GPL program, it is no longer stated
as measured: it is an unknown with a named, emulator-tier default.

Each statement carries one of three marks:

- **documented**: a manufacturer's or community document says so. The source's tier
  tells how far to trust it.
- **measured**: a capture from hardware says so, and the account of the capture was
  read. Unless it says otherwise, "measured" means S4: one real YM2413 driven and
  sampled by a micro-controller board.
- **unsettled**: sources disagree, or only an emulator says so, or nothing does.

Contradictions are numbered C1 onward and unknowns U1 onward; they are gathered in
sections 15 and 16. Section 17 says how exact a core built from this can be.

Conventions: channels are numbered 0 to 8 and slots 0 to 17 here (Yamaha counts from
1). A "sample" is 72 input clocks. "Level" for an envelope means attenuation: 0 is
loudest, 127 is quietest.

## 1. The variants

| Name in `api.md` | Part | Machines |
|---|---|---|
| `YM2413` | Yamaha YM2413 (OPLL) | Sega Mark III FM Sound Unit, Japanese Master System (S9); MSX-MUSIC |
| `DS1001` | The FM section of Konami's VRC7 | Famicom, *Lagrange Point* (S6) |

What is known to differ (S6, tier 3): the DS1001 has its own instrument ROM; it has
six channels, not nine; it has one output and no rhythm output; its rhythm-mode bit
behaves as always set, so channels 6 to 8 are never melodic; nothing can be read
back. Everything else below is stated for the YM2413 and assumed for the DS1001
(U16).

## 2. Pins, clock and timing

1. The chip takes a master clock of 2 to 4 MHz; its LFO rates and envelope times are
   designed for 3.579545 MHz. **documented** (S1 section IV-1; S2's pin table names
   3.579545 MHz).
2. One output sample is computed every 72 master clocks: fsam = fM / 72, 49,716 Hz
   at 3.579545 MHz. **documented** (S1 section III-1-6; S6) and **measured** (S4
   samples once per 72 clocks). S1 rounds this to "50 kHz" and computes its example
   tables from the rounded figure (C6).
3. The chip has one operator circuit and passes through it 18 times per sample, once
   per slot. Each slot lasts 4 master clocks. **documented** (S1 section II-5: "by
   passing through the operator cell 18 times") and **measured** (S4, `rhythm.md`:
   "Each slot lasts for 4 clock cycles").
4. Slot order within a sample, **documented** (S1 Table II-3) and **measured** (S4):

   | Slot | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | Operator | M0 | M1 | M2 | C0 | C1 | C2 | M3 | M4 | M5 | C3 | C4 | C5 | M6 | M7 | M8 | C6 | C7 | C8 |

   M is a channel's modulator, C its carrier. Where a sample "starts" in this
   cycle, as seen from the pins, is not stated by any source (U9).
5. Pins: D0-D7, A0, /CS, /WE, /IC (reset), XIN, XOUT, MO (melody out), RO (rhythm
   out). **documented** (S1 section II-3, S2).
6. With /CS low and /WE high and A0 low, the chip drives "OPLL test data" onto D0 and
   D1 ("Normally not used"). **documented** (S2 pin table). What that data is:
   S6 says of the VRC7's equivalent that D0 carries a serial stream of phase and
   envelope and D1 the DAC value. Not modelled; the boards never read.

## 3. The write protocol

1. A write with A0 = 0 latches a register address; a write with A0 = 1 stores the
   data byte in the addressed register. **documented** (S1 Table II-1).
2. The address stays latched: further data bytes go to the same register.
   **documented** (S1 section III-1: "we only have to send the sub-address the first
   time").
3. After an address write the program must wait 12 master clocks, and after a data
   write 84. **documented** (S1 section II-4 and Table II-2: "If the wait time is
   not observed data will be uncertain"). S6 gives the same in CPU cycles for the
   VRC7 (6 and 42).
4. What the chip does when the waits are not kept, and at which slot a data write
   takes effect, is **unsettled** (U9). S4 offers a reasoned guess only: the channel
   registers sit in 9-stage rotating shift registers, a write must wait for its
   channel to come round, and 84 clocks is one rotation plus a margin.
5. There is nothing a program can usefully read. **documented** (S6 for the VRC7; S1
   gives no read mode beyond the test data of 2.6).

## 4. Register map

**documented** (S1 section II-7, viewed as an image; S2 agrees), with S6's field
letters for the VRC7 identical.

| Address | Bits | Field |
|---|---|---|
| $00 (modulator), $01 (carrier) | 7 | AM: tremolo on |
| | 6 | VIB: vibrato on |
| | 5 | EG-TYP: 1 sustained tone, 0 percussive tone |
| | 4 | KSR: key scale of rate |
| | 3-0 | MULTI: frequency multiplier |
| $02 | 7-6 | KSL of the modulator |
| | 5-0 | TL: modulator total level |
| $03 | 7-6 | KSL of the carrier |
| | 4 | DC: carrier wave half-rectified |
| | 3 | DM: modulator wave half-rectified |
| | 2-0 | FB: modulator feedback |
| $04 (modulator), $05 (carrier) | 7-4, 3-0 | AR attack rate, DR decay rate |
| $06 (modulator), $07 (carrier) | 7-4, 3-0 | SL sustain level, RR release rate |
| $0E | 5 | R: rhythm mode |
| | 4, 3, 2, 1, 0 | BD, SD, TOM, TOP-CY, HH key bits |
| $0F | | TEST ("Normally all addresses are 0") |
| $10-$18 | 7-0 | F-number bits 7-0, channel 0 to 8 |
| $20-$28 | 5 | SUS: sustain on |
| | 4 | KEY: key on |
| | 3-1 | BLOCK |
| | 0 | F-number bit 8 |
| $30-$38 | 7-4 | INST: instrument, 0 is the user tone of $00-$07 |
| | 3-0 | VOL: volume (attenuation) |

In rhythm mode (S1, second map): $36 bits 3-0 are the bass drum's volume; $37 bits
7-4 the hi-hat's and bits 3-0 the snare's; $38 bits 7-4 the tom's and bits 3-0 the
top cymbal's.

1. S1 says the registers hold 271 bits in all. **documented**. S4 reads the die
   photograph as 22 bits per channel (8 + 6 + 8) and 63 for the user tone.
2. Bit 5 of $03 and bits 7-6 of $20-$28 are unused. **documented** (S1 map).
3. Addresses $19-$1F, $29-$2F and $39-$3F act as $10-$16, $20-$26 and $30-$36: the
   low nibble counts on past 8 into the next channel round. **measured** (S4,
   `ksl.txt`: "Tests have shown that e.g. a write to register R#19 has the same
   effect as a write to R#10").
4. Addresses $08-$0D and $40-$FF: no source. **unsettled** (U9).

## 5. The instruments

1. INST 0 selects the user tone in $00-$07, shared by every channel that selects it.
   INST 1 to 15 select a ROM instrument with the same eight-byte layout.
   **documented** (S1 sections I-1, III-1-8; S9).
2. Names, **documented** (S1 section III-1-8): 1 Violin, 2 Guitar, 3 Piano, 4 Flute,
   5 Clarinet, 6 Oboe, 7 Trumpet, 8 Organ, 9 Horn, 10 Synthesizer, 11 Harpsichord,
   12 Vibraphone, 13 Synthesizer Bass, 14 Wood Bass (the register table on page 7
   says "Acoustic Bass"), 15 Electric Guitar.
3. The ROM also holds settings for the five percussion sounds. **documented** (S1
   section V-4: "values that reflect the characteristics of individual percussion
   instruments ... are set in tone ROM").
4. **The YM2413's 15 melodic instruments, as bytes: unsettled (U1, C9).** phase0.md,
   "The built-in instruments", gives the whole account. In short: no allowed source
   claims a dump; emu2413's table (MIT) is hand-tuned; ymfm's is by-ear data from a
   CC BY-SA page that says it is not exact; the two differ in 31 of 120 bytes.
5. **The DS1001's 15 instruments: documented, from a read-out of the chip** (S6,
   "dumped using the VRC7 rewired into a debug mode"; S12 prints the same bytes). The
   table is in S6 and is not repeated here; `variants.py` takes it from the
   pinned wiki file and cites it. *Audit:* the chain is S6, which cites the
   decapping site's page `vendor:yamaha:opl2` (not readable from here: HTTP 403);
   S6 does not name who made the read-out; S12's comment credits "VRC7 presets ...
   by Nuke.YKT". The bytes are Konami's ROM and are taken from the wiki (rule 11).
6. **The percussion settings.** S4 found, on a real YM2413, user-tone bytes that
   reproduce the bass drum ($01 $01 $18 $0F $DF $F8 $6A $6D, "gave the best result"
   among many tried) and, for the four single-operator sounds, the bytes that matter:
   hi-hat $00=$01, $04=$C8, $06=$A7; tom $00=$05, $04=$F8, $06=$59; snare $01=$01,
   $05=$D8, $07=$68; top cymbal $01=$01, $05=$AA, $07=$55. **measured**, as fits
   ("pretty good match" for the snare and cymbal envelopes). They equal the
   percussion rows of the DS1001's ROM read-out (S6). S6 says the YM2413's snare
   byte is $48, not $68, and S13 uses $48 (C4).

## 6. An operator

Every operator is the same circuit: a phase, a sine look-up in logarithmic form, an
attenuation added to it, and an exponential look-up.

1. **The sine table** has 1,024 steps per period. **measured** (S4, `20150311.txt`:
   the period divided by the length of a flat segment "is always exactly 1024").
2. Only a quarter is stored, 256 entries; the second quarter reads the table
   backwards (index bits inverted) and the second half changes the sign.
   **measured** (S4, `tab.txt`) on top of S11.
3. The stored value is the negated base-2 logarithm of the sine, in 1/256 units:
   entry i is round(-log2(sin((i + 0.5) × π / 512)) × 256), for i = 0 to 255 (values
   0 to 2137). **measured for the OPL2 and OPL3 by reading their ROMs** (S11, whose
   formula this is, read by summary and as quoted in S4); **measured for the OPLL
   indirectly** (S4: the die's ROMs look alike, and the predicted waveforms equal
   the captured ones exactly for volumes 1 to 15, with only noise-level differences
   at volume 0).
4. **The exponential table** has 256 entries: entry i is round((2^(i/256) - 1) ×
   1024) (values 0 to 1018). Same sources and standing as 6.3.
5. **From attenuation to a number.** Let x be the logarithmic value (the sine entry
   plus the attenuation of 6.7), a number with 8 fractional bits. Take the table
   entry at 255 minus the low 8 bits of x, add 1024 (the bit the ROM leaves out),
   and shift it right by the integer part of x. Call the result v: at most 2,042,
   11 bits. **measured** (S4 `tab.txt`, refined in `mod-car.txt`). *Audit:* S4's
   prose counts dropped bits from a 12-bit form, which is 2v; 6.10 and 6.11 are
   stated on that form and come to v >> 3 and v.
6. Negative values are the bit-inverse of positive ones, so there are two zeros, +0
   and -0. **measured** (S4 `20150305.txt`: two centre peaks in the DAC histogram
   closer together than any other pair; `tab.txt`).
7. **Attenuation** is counted in envelope steps of 0.375 dB, each worth 16 units of
   x: total = base + key-scale level + envelope level + tremolo, where base is 2 ×
   TL for a modulator (0.75 dB per TL step) and 8 × VOL for a carrier (3 dB per
   step). The total is clipped at 127. **measured** (S4 `small-signals.txt`: "the
   total attenuation level is clipped at 127"; weights from `20150311.txt`,
   `tab.txt`, `mod-car.txt`). The weights agree with S1 (TL "0.75 dB", VOL "3 dB",
   Table III-3). S1 gives the envelope step as "0,325 dB" (C1).
8. **Muting.** When an operator's own envelope level is 124 or more (its top five
   bits set), its output is +0 whatever the rest of the sum is. This holds for
   modulators too. **measured** (S4 `small-signals.txt`, carrier directly; modulator
   by inference from one clean zero crossing, "a strong indication").
9. **Half-sine waveform** (DC, DM): in the second half of the period the magnitude
   is zero but the sign still alternates, so the output there is -0. **measured**
   (S4 `small-signals.txt`); the first half is unchanged (**documented**, S1: "is
   rectified to half wave"; S6).
10. **A carrier's output** is the 12-bit magnitude shifted right by 4: -255 to +255
    with both zeros, 9 bits. **measured** (S4; of the 512 codes a full-volume sine
    uses 400).
11. **A modulator's output** is the same magnitude shifted right by 1 (range about
    ±2,047), and the carrier's phase is advanced by twice that value, in steps of
    1/1024 period: at TL 0 the swing is about ±8π. **measured** (S4 `mod-car.txt`:
    with this "the graph matches exactly with the measured data ... for all values"
    of TL, apart from noise and the first samples after key-on). *Audit:* the
    factor of two is what S4's two prose figures require together (a full-scale
    modulator of ±2,047 giving ±8π); how a negative value rounds is U24, taken as
    the one's complement of 6.6 first, then doubled.
12. **Feedback.** The modulator's phase is advanced by the sum of its own two
    previous outputs (in the form of 6.11) shifted right by 8 - FB; FB = 0 means
    none. **measured** (S4 `fb.txt`: "This model can exactly predict the measured
    data", including chaotic waveforms at TL 0, FB 7, once the two remembered
    outputs have settled). S1 Table III-6 gives the same doubling series as
    modulation indices π/16 to 4π. **documented**. *Audit:* the form (two
    previous outputs, summed) is S4's and measured; the shift amount is in S4 only
    as code and is taken instead from S1's table: 4π for a full-scale modulator at
    FB 7 is a shift of 1, and each step down halves it. The shift of a negative
    sum is U24.
13. In S4's captures the modulator's phase is one sample behind the carrier's.
    **measured**, but it may be a property of how slots are ordered and not a
    separate rule; one emulator removed such a delay (C7). *Audit:* the prose
    gives the observation (fifteen equal samples, then one other, with both
    operators stepping every sixteenth sample) and that a model with the two "1
    sample out of phase" reproduces it. Which is behind is not in the prose. Taken
    (T11, provisional): the carrier is modulated by the modulator's output of the
    previous sample.
14. The two remembered modulator outputs at key-on are not known to be cleared (S4:
    "this might be different from the actual start values"). **unsettled** (U21).

## 7. The phase generator

1. F-number is 9 bits, block 3 bits, MULTI 4 bits. **documented** (S1).
2. Each operator has a 19-bit phase counter: 10 bits index the sine, 9 are
   fraction. **measured** (S4 `20150316.txt`, from flat-segment lengths; the die
   photograph shows 19 rows of 18 stages).
3. Each sample the counter gains ((F-number × M) << block) >> 1, where M is twice
   the multiplier of the table below (so 1, 2, 4, 6, ...). Bits above the 19th are
   lost. **measured** (S4, same file, including the cases where the final shift
   loses a bit: block 0, MULTI 0, F-number 1 does not move at all).
4. Multiplier, **documented** (S1 Table III-1, viewed; S6 identical):

   | MULTI | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
   |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
   | × | 1/2 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 10 | 12 | 12 | 15 | 15 |

5. Hence a tone's frequency is fsam × F-number × 2^block × multiplier / 2^19.
   **documented** (S1's formula for F-number, rearranged; S6 prints it this way).
6. F-number 0 freezes the phase where it is; it is not reset. **measured** (S4).
7. **Vibrato.** A position counter steps every 1,024 samples through 8 positions,
   period 8,192 samples (6.07 Hz). **measured** (S4 `20151201.txt`: regions of 1,024
   samples, pattern repeating every 8,192). S1 says 6.4 Hz (C2).
8. With vibrato on, the step is (((2 × F-number + d) × M) << block) >> 2, where d
   depends on the position and on the F-number's top three bits. For top bits 111
   the eight values of d are 0, +3, +7, +3, 0, -3, -7, -3. **measured,
   approximately** (S4: "I only verified the last row in the table", by aligning
   generated sines with the capture region by region; "not an exact match").
   *Audit:* the table S4 checked against is one he says he copied from a GPL
   emulator; it was not transcribed. The eight values above are the last row of
   S12's table (MIT), and they reproduce the step sizes S4 states for F-number
   $1C0, block 6. For the other seven values of the top bits: **struck as
   measured; unsettled** (U4). Provisional default, emulator tier: S12's table,
   whose peak is the top three bits and whose half-way value is that shifted right
   once. S12 calls it a "rough approximation of 14 cents depth".
9. The depth is about 14 cents at its peak. **documented** only for other Yamaha
   chips (S4 quoting their manuals); S1 gives none.
10. **Phase reset.** Both of a channel's phase counters are set to zero when the
    envelope leaves the damp state for attack (section 8.9), not at the key-on write
    itself. **measured** (S4 `mod-car.txt`: "Each time the same note is played, the
    wave looks exactly the same"; `attack.txt`: "the phase of the sine wave is reset
    to zero at the start of the attack phase"). The exact sample is U20.

## 8. The envelope generator

### Level and rates

1. The envelope level is a 7-bit number per operator, 0 to 127, 0.375 dB per step,
   48 dB in all. **measured** (S4 `20150320.txt`: 120 distinct steps down to SL 15,
   so 128 over the whole range; die photograph: 7 rows of 18 stages). S1 says 48 dB
   and a resolution of "0,325 dB" (C1).
2. Every rate R (AR, DR, RR, or one of the fixed rates below) becomes an effective
   rate 4 × R + Rks, limited to 63; R = 0 gives 0. **documented** (S1 section
   III-1-2: "RATE = 4 × R + Rks ... Note that when R = 0, RATE = 0").
3. Rks: with KSR = 0 it is the block's top two bits (0 to 3); with KSR = 1 it is the
   block and F-number bit 8 together (0 to 15). **documented** (S1 Table III-2,
   viewed) and **measured** (S4 `sl-ksr.txt`, ten settings, each "confirmed").
4. A single counter, shared by all operators, counts samples. **measured** (S4: the
   first step after any change of state comes early by a varying amount, and its
   possible lengths are exactly those a free-running shared counter predicts,
   `adsr-transitions.txt`). Its width is at least 13 bits; the same counter may also
   drive the LFOs (U19).

### Decay, release and damp steps

5. For effective rates 4 to 51, let s = 13 - (rate >> 2). A step is considered when
   the counter's low s bits are all zero. The next three bits of the counter choose
   a position 0 to 7 in an eight-step pattern chosen by rate & 3, and the level
   rises by one where the pattern has a 1:

   | rate & 3 | pattern, positions 0 to 7 |
   |---|---|
   | 0 | 0 1 0 1 0 1 0 1 |
   | 1 | 0 1 0 1 1 1 0 1 |
   | 2 | 0 1 1 1 0 1 1 1 |
   | 3 | 0 1 1 1 1 1 1 1 |

   **measured**: the step lengths for rates 4, 9, 14, 19 and 48 to 51 (S4
   `20150320.txt`), and the alignment of each pattern, which S4 fixed by observing
   which first-segment lengths occur and ruling out every other rotation
   (`adsr-transitions.txt`: "only this one matches the measurements").
6. Rates 0 to 3 never step. **documented** (S1 Table III-7 note) and **measured**.
7. Rates 52 to 59 step in a 16-sample cycle, **measured** (S4 `20150320.txt`,
   re-measured in `attack.txt` "exactly the same result"). Listed as samples spent
   on each level; "½" means the level rises by 2 in one sample:

   | Rate | Cycle |
   |---|---|
   | 52 | 2 each |
   | 53 | 2, 2, 2, 2, 2, 2, 1, 1, 1, 1 |
   | 54 | 2, 2, 1, 1, 1, 1 (twice) |
   | 55 | 2, 2, then twelve of 1 |
   | 56 | 1 each |
   | 57 | four of ½, then twelve of 1 |
   | 58 | four of ½, four of 1 (twice) |
   | 59 | twelve of ½, then four of 1 |

   S4 notes that this is coarser than the patterns of 8.5 would give and that the
   table says what happens, not how the chip does it. *Audit:* S4 prints each
   cycle from an arbitrary start. Where a cycle sits against the shared counter is
   a choice (U23).
8. Rates 60 to 63 rise by 2 every sample. **measured** (S4). S1 prints 1.27 ms for
   all four, which is 63 samples.
9. Total times: S1 Table III-7 lists the 0 to 48 dB time for every rate; they equal
   127 steps of the above (phase0.md, "What was checked here"). **documented**; a
   good unit test.

### Attack

10. An attack moves the level toward 0 by x → x - (x >> n) - 1, with n = 4 for
    effective rates below 48. From 127 that gives 119, 111, 104, 97, 90, ... 1, 0.
    **measured** (S4 `attack.txt`: the only sequence consistent with every captured
    amplitude).
11. For rates 4 to 47 the timing is that of 8.5 with one change: the lowest two
    bits of the counter are ignored in the "low s bits are zero" test, so each
    opportunity lasts four consecutive samples and applies the formula on each. The
    curve is therefore three one-sample levels and then a plateau of 2^s - 3
    samples, repeated. **measured** (S4 `attack.txt`: "plateaus of length pow(2, n)
    - 3 plus 3 intermediate steps", for all rates below 48).
12. For rates 48 to 59 the level changes every sample. Rate 48 uses n = 4 throughout,
    52 uses n = 3, 56 uses n = 2. The rates between alternate over 16 samples between
    the formula of the rate group and the next faster one (n one less): for rate & 3
    = 1, 2, 3 the faster formula is used for 4 samples of 16, 8 of 16 (4 on, 4
    off), and 12 of 16. **measured** (S4 `attack.txt` section 2.6, with the worked
    example 21, 15, 13 at rate 55; S1 Table III-7's attack times for rates 48, 52,
    56 and 59 are 42, 25, 14 and 7 samples, which these formulas give). *Audit:*
    S4's prose says the pattern table of 8.5 is used at its even columns; which
    bits of the shared counter choose the column is in lines that were not read.
    Taken as a choice (U23): counter bits 2 and 3.
13. Rates 60 to 63 are instant, but only as a decision made when damp ends: the
    level is set to 0 and the operator goes straight to decay. If AR is changed to
    15 (or to 0) while an attack is in progress, the attack stalls until the rate
    is changed again. **measured** (S4 `attack.txt`, two experiments).
14. The attack starts from wherever the level is: 127 if a release ran to its end,
    124 if a damp phase preceded it (8.17). **measured** (S4 `attack.txt`: two
    families of plateaus, explained by the two starting points). Starting points
    125 and 126: U12.
15. S1's attack times (Table III-7, right half) are 21, 17, 14 and 12 times a power
    of two samples for rate & 3 = 0 to 3, up to rate 47. **documented**; **measured**
    as consistent by S4.

### States

16. On a key-off to key-on change the operator enters **damp**: the level rises at
    fixed rate 12 (with Rks added, like any rate). **measured** (S4 `envelope.txt`:
    10.22 ms from 0, against S1's "DP: 10 ms"; and "for higher frequencies the rate
    is faster"). Other OPL chips have no such state (S4).
17. Damp ends when the level reaches 124, not 127; then the phases are reset (7.10)
    and attack begins, or decay if 8.13 applies. **measured** (S4 `attack.txt`).
18. **Attack** ends at level 0 and **decay** begins: the level rises at DR. When AR
    and DR give the same effective rate the first decay step can follow at once
    (S4, with the note "this needs more investigation").
19. Decay ends when the level's top four bits equal SL, that is, at level 8 × SL
    (3 dB per SL step, **documented** S1; **measured** S4 `sl-ksr.txt`). The test is
    for equality on the top bits, not "at or beyond": if SL is changed to a level
    already passed, decay runs on to the bottom; and a level of 9 was observed
    holding for SL = 1. **measured** (S4 `envelope.txt`, experiments b2 and b3).
    SL = 15 is level 120 (45 dB), not the bottom (C5).
20. After decay comes **sustain**: with EG-TYP = 1 the level holds; with EG-TYP = 0
    it goes on rising at RR. Changing EG-TYP in this state switches between the two
    at once: they are one state with two rates. **measured** (S4 experiment d1);
    S1 Figure III-1 shows the two shapes. **documented**.
21. Changing SL during sustain does nothing. **measured** (S4 experiment b1).
22. **Release** is simply "key is off", whatever state the operator was in (damp,
    attack, decay or sustain). **measured** (S4 experiment e). Its rate for a
    **carrier**:

    | SUS bit ($2x bit 5) | EG-TYP = 1 | EG-TYP = 0 |
    |---|---|---|
    | 0 | RR | fixed rate 7 |
    | 1 | fixed rate 5 | fixed rate 5 |

    **measured** (S4 `envelope.txt`) and **documented** (S1: "When this bit is "1",
    the RR with the key off will be 5"; S1's figure gives "RR: 310 ms" and "RS: 1.2
    s", which are near rates 7 and 5; S13 reached the same two numbers from the
    figure). Changes to SUS, RR or EG-TYP take effect at once (S4 experiments a, c,
    d2).
23. A **modulator** does not change rate at key-off: it carries on in whatever
    state it was in (holding, if sustained; still rising at RR, if percussive).
    **measured** (S4 `envelope.txt`, "Modulator-envelope has no release phase?");
    S6 says the same of the sustained case on the VRC7. A modulator does appear to
    be damped at key-on (S4, "not 100% sure": U13).
24. Release runs to 127. **measured** (S4 `attack.txt`).
25. Changes to AR, DR and RR take effect at once in the state that uses them.
    **measured** (S4 experiment a).

## 9. Key scale level

1. KSL adds attenuation that grows with pitch. **documented** (S1 section III-1-3).
2. For the 3 dB per octave setting, the attenuation in dB is T[f] - 3 × (7 - block),
   or 0 if that is negative, where f is the F-number's top four bits and T is the
   bottom row of S1 Table III-5 (viewed): 0, 9.000, 12.000, 13.875, 15.000, 16.125,
   16.875, 17.625, 18.000, 18.750, 19.125, 19.500, 19.875, 20.250, 20.625, 21.000.
   The 1.5 dB setting halves it and the 6 dB setting doubles it (S1's notes to the
   table). **documented**, and **measured** as exact on a sparse sample of block and
   F-number for all three settings (S4 `ksl.txt`).
3. In envelope steps (0.375 dB): the 6 dB setting is T × 2 / 0.375 less 16 per block
   below 7; the 3 dB setting is that shifted right once and the 1.5 dB setting
   twice. Whether the chip truncates exactly so is **measured** only on S4's sample.
4. Field values: 0 none, 1 is 1.5 dB per octave, 2 is 3 dB, 3 is 6 dB. **measured**
   (S4, which adds that on other OPL chips 1 and 2 are the other way round). S1's
   Table III-4 can be read either way (C3).

## 10. Tremolo

1. Tremolo adds 0 to 13 envelope steps to the attenuation of every operator whose
   AM bit is set (0 to 4.875 dB). **measured** (S4 `am.txt`: "(only) 14 different
   levels (0..13)"; about 4.8 to 5 dB at the pins).
2. The added value is a triangle: at 0 for 960 samples (15 × 64), at each of 1 to
   12 for 512 samples on the way up and again on the way down, at 13 for 192
   samples (3 × 64). **measured** (S4 `am.txt`, the three durations). That makes
   13,440 samples, 3.699 Hz; S1 says 3.7 Hz. **documented**. *Audit:* restated
   from the measurement alone. S4 arrives at it through a 210-entry table that
   "all emulation cores" use; the table was not read and is not needed.
3. The tremolo position is one counter for the whole chip. **documented** by S1's
   block diagram (one "Vibrato / Amplitude Modulator" block). Its relation to the
   envelope counter and to reset: U15.

## 11. Rhythm mode

1. Setting bit 5 of $0E turns channels 6 to 8 into five percussion sounds; the other
   six channels are unaffected. **documented** (S1 section III-1-7).
2. Which slot makes which sound, **documented** (S1 Table III-9) and **measured**
   (S4 `rhythm.md`):

   | Sound | Operator | Slot |
   |---|---|---|
   | Bass drum | M6 and C6 | 12, 15 |
   | Hi-hat | M7 | 13 |
   | Tom | M8 | 14 |
   | Snare | C7 | 16 |
   | Top cymbal | C8 | 17 |

3. S1 asks the program to load fixed pitches ($16=$20, $17=$50, $18=$C0, $26=$05,
   $27=$05, $28=$01) and to keep the key bits of $26-$28 clear. **documented**. The
   pitches are only advice: the sounds follow whatever is written (S4).
4. In rhythm mode the key bits of $26-$28 still count: each sound behaves as if its
   bit in $0E were OR-ed with its channel's key bit. **measured**, loosely (S4,
   marked "TODO"): U7.
5. The **bass drum** is an ordinary two-operator voice with the ROM's settings
   (5.6). **measured** (S4: a user tone with those bytes tracks it, apart from one
   sample of offset and a small difference in peak that S4 attributes to the
   offset).
6. The **tom** is a single operator producing a plain sine at channel 8's pitch,
   output directly like a carrier. **measured** (S4).
7. **Noise.** A 23-stage shift register with feedback polynomial x^23 + x^9 + 1,
   stepped once per slot (18 times a sample). **measured** (S4: the sequence was
   first recovered from 120 captured snare bits by the Berlekamp-Massey algorithm as
   the once-per-sample polynomial x^23 + x^9 + x^8 + x + 1, which is the same
   register seen every 18th step; then 50 simultaneous hi-hat and snare bits fixed
   the per-slot stepping: the snare's bit is the hi-hat's three steps later,
   matching slots 13 and 16). The hint that it steps per slot came to S4 from the
   author of a model that is not read here; the capture is what the statement rests
   on.
8. The **snare** takes one phase bit and the noise bit and outputs one of four
   values at its envelope's level, **measured** (S4):

   | | phase bit 0 | phase bit 1 |
   |---|---|---|
   | noise 0 | +0 | negative peak |
   | noise 1 | positive peak | -0 |

   S4 could not tell this from the table with its columns exchanged, nor whether the
   phase is M7's or C7's (U6). S4 calls the bit "phase(8)" and also "the upper bit of
   the phase-counter"; which bit of which counter is meant is U5.
9. The **top cymbal** outputs a positive or negative peak according to one bit
   computed from five phase bits: two of C8's (S4's "c85", "c83") and three of M7's
   ("m77", "m73", "m72"). Sixteen forms fit the captures equally (each of three
   terms may be inverted, and the last term has a variant). **measured** up to
   that ambiguity (U5). Its peak is the full ±255. **measured** (S4: "at the end
   of the attack phase the signal does span the full -255..+255 range").
   *Audit:* what S4's names mean, and which value of the bit gives which sign, are
   only in code blocks. **Struck.** Provisional default, emulator tier (S12): the
   form (c85 = c83) and (m77 = m72) and (c85 = m73), the first of S4's sixteen,
   read on bits 5 and 3 of C8's ten-bit phase and bits 7, 3 and 2 of M7's;
   positive peak when it is true, negative when false.
10. The **hi-hat** combines that same bit p with the noise bit, "in a very similar
    way as is done for" the snare (S4, prose). **measured** that far. *Audit:* the
    four phases are printed only in a code block. **Struck as measured; unsettled
    (U22).** Provisional default, emulator tier (S12): one of four fixed phases (in
    1/1024 periods), noise 1 and p: $0D0; noise 0 and p: $034; noise 1 and not p:
    $234; noise 0 and not p: $2D0, with p the form of 11.9. S12 itself pairs the
    noise values the other way round, and also has its snare's noise the other way
    round from the measured table of 11.8; the pairing here is S12's read through
    that one inversion, so that one noise bit serves both sounds.
11. Each percussion sound has its own envelope from the ROM settings (5.6) and its
    own volume nibble (section 4). **documented** (S1 section V-4) and **measured**
    as fits (S4). How TL, key scaling and the volume combine for the three
    single-operator sounds on modulator slots: U11.
12. Each percussion output appears twice per sample, the second an exact copy of
    the first even if registers changed in between. **documented** (S1 section
    III-4: "the same percussion sounds are output twice") and **measured** (S4:
    hi-hat, tom and bass drum repeat in slots 0, 1, 2 and snare and cymbal in slots
    6 and 7 of the following sample).
13. Switching rhythm mode while notes sound, and the SUS bit of $26-$28 in rhythm
    mode: no source (U7, U8).
14. On the DS1001 there is no rhythm output and the mode bit acts as always set.
    **documented** (S6).

## 12. The output stage

1. The chip has a 9-bit DAC and two pins. MO carries the melody channels and RO the
   percussion, each as a train of pulses, one per carrier slot, about a centre level;
   an external integrator turns them into audio. **documented** (S1 sections II-1,
   III-4 and Figure III-3; S2).
2. On MO, channels 0 to 8 appear in slots 3, 4, 5, 9, 10, 11, 15, 16, 17 (channels 6
   to 8 only outside rhythm mode). On RO, in rhythm mode: hi-hat, tom, bass drum,
   snare, cymbal in slots 13 to 17, and their copies in slots 0, 1, 2, 6, 7.
   **documented** (S1 Figure III-3) and **measured** (S4 `rhythm.md` table).
3. Each pulse is one operator's 9-bit output of 6.10: -255 to +255 with two zeros.
   The channels are not added inside the chip. **measured** (S4) and **documented**
   (S6: "the channels are output in series rather than mixed").
4. Between pulses the pin rests at the centre level (S1 Figure III-3 (a), drawn; S4
   does not say which zero). **documented**, loosely.
5. The DAC is a 32 by 16 array of switches; its steps are not equal, and the two
   zeros lie closer together than any other pair of codes. **measured** (S4
   `20150305.txt`, from the die photograph and the histogram). No table of the
   non-linearity exists. The core outputs ideal words.
6. Polarity: S4's captures come out inverted and S4 puts that down to its own
   board. **unsettled** (U10).
7. Typical output swing is 2/5 Vcc. **documented** (S1 section VI.5).
8. The DS1001 has one output for its six channels. **documented** (S6). Its level
   in a Famicom, its clipping and its filter are the board's (S7, S8).

**What the core hands the boards** is a choice, not a fact about the chip: the
sequence of output words is the fact. See [provenance.md](provenance.md), T6.

## 13. The test register

1. $0F is "established to test this LSI" and should be 0. **documented** (S1). That
   is all Yamaha says.
2. On the VRC7, **documented** at tier 3 (S6, from a forum post not read here):
   bit 0 replaces every envelope's output with 0 (full volume) while the envelopes
   run on; bit 1 holds both LFOs at zero; bit 2 holds every phase at zero, so the
   output is silent; bit 3 makes the LFOs advance every sample (tremolo 64 times
   faster, vibrato 1,024 times faster).
3. For the YM2413 itself: **unsettled** (U2). S6's four bits are the best
   description in hand and the figures in bit 3 agree with sections 7.7 and 10.2.

## 14. Reset

1. /IC low clears all registers to 0. **documented** (S1 section III-1; S2).
2. The VRC7's $E000 bit 6 silences the chip and clears its registers, "including
   tremolo LFO state, but not including vibrato LFO state"; register writes are
   ignored while it is set. **documented** at tier 3 (S6, S7).
3. With every register 0: all keys off, rhythm off, instrument 0 with an all-zero
   user tone, volume 0 (loudest). What the envelope levels, phases, shared counter
   and noise register hold: **unsettled** (U3). A noise register of all zeros would
   never produce noise with the polynomial of 11.7, so the chip must avoid or
   escape that state somehow; no source says how.

## 15. Contradictions

- **C1. Envelope step.** S1: resolution "0,325 dB" (as scanned). S4 measured 128
  steps in 48 dB: 0.375 dB. Taken: 0.375, a misprint in S1.
- **C2. Vibrato rate.** S1: 6.4 Hz. S4 measured a period of 8,192 samples: 6.07 Hz.
  Taken: 8,192 samples.
- **C3. KSL codes.** S1 Table III-4's column heads are illegible in the scan; read
  as D7 then D6 it makes code 2 the 1.5 dB setting. S4 measured code 1 = 1.5 dB,
  2 = 3 dB, 3 = 6 dB, and S12 and S13 do the same. Taken: S4.
- **C4. The snare's last byte.** $68 by S4's fit on a YM2413 and in the DS1001's
  ROM; $48 for the YM2413 according to S6 ("Curiously, byte $07 of the snare drum
  ($68) differs from YM2413 ($48)") and S13. The difference is the sustain level, 6
  against 4. Taken provisionally: $68 for both, as the only measured value; held as
  variant data.
- **C5. Sustain level 15.** S4 measured decay stopping at level 120. S13 treats 15
  as the bottom of the range, as on other OPL chips. Taken: S4.
- **C6. Sample rate.** S1 writes "Sampling frequency (50 kHz)" and "3.6 MHz" and
  computes its F-number examples from them. The real figures are fM / 72 and
  3.579545 MHz. The core counts clocks; no constant is needed.
- **C7. Modulator delay.** S4 measured the modulator one sample behind the carrier.
  S12's history has "Remove modulator phase delay" (2020-01-06) with no reason
  given. Taken: S4, to be re-derived from the slot order if possible.
- **C8. Percussion logic in emulators.** S4 reports that the two older emulators
  disagree with each other and with the chip on the snare's table, the cymbal's bit
  and the cymbal's level. Taken: S4's measured forms.
- **C9. The YM2413's instruments.** S12 and S13 differ in 31 of 120 bytes (U1).

## 16. Unknowns

- **U1.** The YM2413's 15 melodic instruments as exact bytes.
- **U2.** The YM2413's test register.
- **U3.** Internal state after reset and at power-on; how the noise register leaves
  zero.
- **U4.** Vibrato offsets for F-number top bits 000 to 110 (default: emu2413's
  table, emulator tier), and the exact step formula away from the one setting S4
  checked.
- **U5.** The percussion phase bit: which of 16 equivalent forms, and which bits of
  which counters S4's "c85", "m77", "phase(8)" denote (10-bit phase or 19-bit
  counter).
- **U6.** Whether the snare's phase bit is M7's or C7's.
- **U7.** Rhythm mode: the OR of key bits (reported, not confirmed); the SUS bits
  and instrument nibbles of $26-$28 and $36-$38.
- **U8.** Rhythm mode switched on or off while notes sound; which envelopes and
  phases carry over.
- **U9.** Write timing: the slot at which a write lands; writes closer than the
  waits allow; the alias registers' latency; addresses outside the map; where a
  sample begins as seen from the pins.
- **U10.** Output polarity, and the resting level between pulses.
- **U11.** Level arithmetic of the single-operator percussion sounds (which of TL,
  KSL, volume apply to hi-hat and tom on modulator slots).
- **U12.** Attack from levels 125 and 126.
- **U13.** Whether modulators are damped at key-on, and whether percussion sounds
  are.
- **U14.** What happens if a +2 step would pass 127 (S4 speculates about a wrap to
  0 and about why the mute test ignores the low two bits).
- **U15.** The LFO counters: their relation to the envelope counter, their start
  values, what resets them.
- **U16.** Whether the DS1001's synthesis differs from the YM2413's in anything but
  ROM, channel count and output; what its registers for channels 6 to 8 do.
- **U17.** Whether the YM2413B (S3, 1999) differs from the YM2413 in behaviour. S3's
  first page drops the line "Si-Gate NMOS LSI" from the feature list; nothing else
  was compared.
- **U18.** The format of S4's capture files (S5), without which rung 2 of
  validation.md cannot use them directly.
- **U19.** The shared counter's width and whether the LFOs are taken from it.
- **U20.** The exact sample of the phase reset and of the one-sample "spike" S4 saw
  at the end of every damp phase.
- **U21.** The feedback history at key-on, and whether the measured one-sample
  lag of 6.13 is the carrier using the modulator's previous output (taken) or a
  phase offset.
- **U22.** The hi-hat's four phases and their pairing with the noise bit and the
  cymbal's bit (default: emu2413's, emulator tier, read as 11.10 says).
- **U23.** For effective rates of 48 and up: which bits of the shared counter
  choose the faster attack formula (8.12), and where the decay cycles of 8.7 sit
  against the counter. Default: counter bits 2 and 3, the slow-rate rule continued.
- **U24.** Rounding of negative modulator outputs when doubled into the carrier's
  phase and when summed and shifted for feedback. Default: one's complement first,
  then an arithmetic shift.

## 17. How exact can a core built from this be?

**Available from allowed sources, to the bit**, for a melodic channel in steady
conditions: both ROM tables, the operator arithmetic, modulation and feedback,
volume, total level, key scaling, tremolo, the phase step, every decay and release
rate, the attack curve for every rate, the envelope's states and the effect of every
register change S4 tried. S4's own model of these reproduced its captures sample for
sample, noise aside. This is tier 1 and covers what a listener hears most of the
time.

**Available, but as fits or with an ambiguity that cannot be heard**: the percussion
envelopes; the cymbal's and hi-hat's phase bit (16 forms, same sound); the noise
sequence (exact) but not its starting state.

**Not available from allowed sources**: the YM2413's melodic instrument ROM (the
largest gap: every game that uses the built-in voices depends on it); vibrato depth
for seven of eight pitch ranges (available at tier 5); the YM2413's test register;
anything about the timing of writes within a sample; rhythm-mode edge cases; the
state after reset.

**Only in the excluded sources**: a description of the chip at the level of its
internal clocks, which is what the withdrawn core claimed to equal.

**Expected outcome.** A core that is sample-exact against S4's captures for
user-tone notes on a single channel, right to the manual for every documented
number, and audibly right but not byte-proven for the YM2413's built-in voices
until U1 is settled. For the DS1001 the built-in voices are byte-proven. Against a
die-derived model run as a closed box, expect agreement on steady notes and
differences wherever section 16 has an entry: the streams in `validation/streams.py` named
`fast_writes`, `back_to_back`, `rhythm_toggles`, `rhythm_key_races` and
`test_register` are built to find exactly those, and the honest result there is a
list of differences written down as open, not a pass.
