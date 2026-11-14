# Provenance

Where every fact in this core comes from, what was decided where no source
settles a question, what was deliberately left unread, and what was seen during
the work that the rules in [restart.md](restart.md) keep out. Source IDs (S1,
S4, ...) are [phase0.md](phase0.md)'s; section, C and U numbers are
[spec.md](spec.md)'s.

## 1. Where the facts come from

[phase0.md](phase0.md) has the full table of sources: each one's location, licence,
author, tier and how it was read. By kind:

- **The register map, the write protocol, every documented number** (multipliers,
  key-scale tables, the weights of total level, volume and sustain level, the
  feedback table, every decay and attack time, the slot order, the rhythm slots):
  Yamaha's application manual (S1) and catalog sheets (S2, S3).
- **The operator arithmetic, the phase generator, the envelope's stepping and
  states, tremolo, vibrato at the top pitch range, modulation and feedback, the
  noise generator and the percussion logic**: the openMSX project's measurements
  on one real YM2413 (S4), as its write-ups report them in prose and in printed
  tables of measurements. The two ROM tables follow the formulas of the OPL2 and
  OPL3 ROM read-outs (S11), which S4 restates and checks against its captures.
- **The DS1001's instrument ROM, its test register and its reset bit**: the NESdev
  wiki (S6), from a read-out of the chip through its debug mode.
- **What no allowed source above an emulator settles**: the YM2413's fifteen
  melodic voices, the vibrato offsets below the top pitch range, the hi-hat's
  phases and the cymbal's particular form are emu2413's (S12, MIT, emulator
  tier), each marked so where it is used. emu2413's notice travels with them.

### How the sources were read

- **S1.** The OCR text of every page for the prose; printed pages 9 to 13 and 16
  as images for Tables III-1, III-2, III-4 to III-7, III-9 and Figure III-1.
- **S4.** Through a filter that hides every line that looks like program text,
  everything inside a code fence, the whole of `rhythm.md` from the heading
  "## Nuke.YKT" to the heading "## [2020/01/02] Update", and, for the three
  write-ups that print tables copied from an emulator (`20150320.txt`,
  `20151128/am.txt`, `20151201.txt`), every line that is mostly numbers. What
  was left was read in full for 18 of the 21 files. `20150327/attack-rates.txt`
  and `20170126/formula-f1-4.txt` were not read (the spec cites neither;
  `attack.txt` supersedes the first), and `20150409/predicted-sine.txt` is a
  table of a model's output and was not opened.
- **S6.** Whole file.
- **S12, emu2413 (MIT).** Its `LICENSE`, lines 1 to 224 (the instrument and
  constant tables with their comments), and the functions that make the
  percussion sounds, key the percussion slots and look up the exponential table,
  with the carrier and modulator functions beside them. Permissive source may be
  read (rule 4); nothing was ported. It is used only as rule 10 allows: as a
  named, emulator-tier default where nothing better exists, and as corroboration.
- **S2, S7, S8, S9, S11, S13, S14** were read in Phase 0 and not re-read for the
  audit below. None of them carries a number the core computes with, except
  S11's two formulas, which S4's prose restates.

### The audit of the spec

Before any chip code was written (2026-11-13), every numbered statement of
spec.md was checked against its source's **prose** or a measurement the source
reports, without re-reading the passages listed in section 4. Where a number's
only support was a code fragment or a table copied from a GPL program, it was
struck or restated:

- **7.8, vibrato offsets.** The top pitch range stays, as S4's measurement,
  marked approximate. The other seven rows were a table S4 says it copied from a
  GPL emulator; they are struck and become U4, with emu2413's `pm_table` as the
  emulator-tier default (T3).
- **8.12, fast attack.** The counts (4 of 16, 4 on and 4 off, 12 of 16) stay
  measured; which counter bits select is a choice (U23).
- **8.7, fast decay.** The measured cycles stay; where they sit against the
  shared counter is a choice (U23).
- **10.2, tremolo.** Restated from the three measured durations (960, 512, 192
  samples) and fourteen levels; the 210-entry table and 64-sample step were how
  S4 says the emulators do it.
- **11.9, cymbal.** One bit from five phase bits of two operators, sixteen forms
  indistinguishable on the captures, full swing: kept. The particular form and
  the sign (only in code blocks): struck, emu2413's used instead (T8).
- **11.10, hi-hat.** The four phases (only in a code block): struck as measured;
  emu2413's $034, $0D0, $234, $2D0 used instead, read with the snare's measured
  noise polarity (U22).
- **6.5, 6.11, 6.12, 6.13.** Restated: the exponential look-up without a
  separate doubling step (same numbers); the modulation factor as the only one
  consistent with S4's prose, with negative rounding a new unknown (U24); the
  feedback shift derived from Yamaha's Table III-6 instead of code; the lag's
  direction a choice (U21, T11).
- **5.5, the DS1001's voices.** The chain written out in full (below).

No statement of the spec was found to rest on the passage that quotes the GPL
model: the noise statement (11.7) cites S4's capture, and the percussion tables
cite S4's own prose tables.

### Every statement and its chain

Sources, once:

- **S1**: Yamaha, "FM Operator Type-LL (OPLL) Application Manual". The
  manufacturer's own statement. Scanned by Ricardo Bittencourt, made into a PDF by
  HansO in 2001; read from the SMS Power copy. Nothing upstream.
- **S4**: Wouter Vermaelen (openMSX), write-ups in the repository
  `andete/ym2413` (Joost Yervante Damad's) at commit `4893d1c`, 2015 to 2020. No
  licence. Method: one real YM2413 on a board with an ARM micro-controller that
  drives the chip's pins and clock and samples MO and RO with a 12-bit ADC, 16
  times oversampled, the chip clocked slowly; ADC values mapped back to the chip's
  9-bit codes through a calibrated histogram. Upstream is noted per statement
  where S4 names one. The write-ups also print C fragments and quote two
  emulators; those were not used.
- **S6**: NESdev wiki, "VRC7 audio" (wiki authors; the snapshot pinned in
  `fetch_references.py`). Upstream: two forum posts it cites (p=224897,
  p=236371, not read) and the decapping site's page (not readable).
- **S11**: Matthew Gambrell and Olli Niemitalo, "OPLx decapsulated" (2008): the
  ROMs of a YM3812 and a YMF262 read bit by bit under a microscope. Known here
  through S4's prose restatement of its two formulas.
- **S12**: emu2413 v1.6.4, Mitsutaka Okazaki, MIT. An emulator: tier 5.

"prose" means the support is in running text or a prose table that was read;
"table" means a table of measurements in the source.

| Statement | Chain | How established | Standing |
|---|---|---|---|
| 1 (variants, machines) | S6 for the differences; S9 for machines (not re-checked) | community document | documented, tier 3 |
| 2.1 clock range | S1 IV-1, prose | manufacturer | documented |
| 2.2 72 clocks a sample | S1 III-1-6 (fsam), S6 prose ("72 internal clock cycles"); S4 `20150209.txt` prose ("Pattern repeats every 72 YM2413 clocks") | manufacturer; observed on the pins | documented and measured |
| 2.3 18 slots of 4 clocks | S1 II-5 prose; S4 `rhythm.md` prose | manufacturer; S4 restating S1's figure after verifying positions | documented; the 4-clock slot measured |
| 2.4 slot order | S1 Table II-3; S4 `rhythm.md` prose table ("I also verified the positions") | manufacturer; capture at 72 times the sample rate | documented and measured |
| 2.5 pins | S1 II-2, II-3 | manufacturer | documented |
| 2.6 test data on D0, D1 | S1 II-3 prose; S6 debug-mode section | manufacturer; community | documented; not modelled |
| 3.1, 3.2 address then data; address stays | S1 Table II-1, III-1 prose | manufacturer | documented |
| 3.3 waits of 12 and 84 clocks | S1 II-4 prose; S6 prose (6 and 42 CPU cycles) | manufacturer | documented |
| 3.4 writes inside the waits | S4 `ksl.txt` prose, offered there as a guess | none | unsettled (U9) |
| 3.5 nothing to read | S6 prose | community | documented, tier 3 |
| 4 register map | S1 II-7 (page viewed as OCR; fields confirmed in III-1-2 to III-1-8 prose and tables); S6 tables | manufacturer | documented |
| 4.1 271 bits | S1 III-1 prose; S4 `fb.txt` prose for the die reading | manufacturer; die photograph read by S4 | documented |
| 4.2 unused bits | S1 map | manufacturer | documented |
| 4.3 aliases $19-$1F, $29-$2F, $39-$3F | S4 `ksl.txt` prose and its prose table | "Tests have shown" on the chip | measured |
| 4.4 other addresses | none | none | unsettled (U9) |
| 5.1, 5.2 instrument 0 and the names | S1 I-1, II-7, III-1-8 | manufacturer | documented |
| 5.3 percussion settings are in ROM | S1 V-4 prose | manufacturer | documented |
| 5.4 the YM2413's fifteen voices | no dump in any allowed source. Default: S12's table (lines 31 to 46 of `emu2413.c`), which its commit titles show was adjusted by hand | an emulator author's tuning | **unsettled (U1); emulator tier, not a dump** |
| 5.5 the DS1001's fifteen voices | S6, "Internal patch set": "dumped using the VRC7 rewired into a debug mode", citing the decapping site's page `vendor:yamaha:opl2` (HTTP 403 to a plain fetch; not read). S6's "Debug Mode" section describes the pins the read-out used. S12's comment credits the same bytes as "VRC7 presets ... by Nuke.YKT" and its table equals S6's in all 18 rows | read out of a real chip's ROM through its debug pins; the person is named only at one remove (S12's comment) | documented from a read-out (rule 11) |
| 5.6 percussion bytes | S4 `rhythm.md` prose tables: the bass drum's eight bytes ("the values shown in the above table gave the best result"), and the bytes that matter for tom, snare, cymbal, hi-hat ("work well", "pretty good match"). S6 prints the same rows from the VRC7 read-out and says the YM2413's snare byte is $48 | fits on a real YM2413; a read-out of a different chip | measured as fits; C4 stands |
| 6.1 1,024 steps | S4 `20150311.txt` prose | period over flat-segment length "always exactly 1024" | measured |
| 6.2 quarter stored, mirrored, sign | S4 `tab.txt` prose bullets ("mirroring corresponds to simply flipping all the bits", "flipping the sign") | S4's model matched to captures; S11 upstream | measured |
| 6.3, 6.4 the two tables' contents | S11's formulas as S4 `tab.txt` restates them in prose (index plus one half, base-2 logarithm negated, times 256, rounded; two to the power, times 1,024, tenth bit dropped; ranges 0 to 2137 and 0 to 1018). S12 prints the same two formulas in comments and the same tables | ROM of other chips read under a microscope (S11); for the OPLL, die photographs compared by eye and waveforms predicted "*exactly*" for volumes 1 to 15 (S4) | measured for OPL2/OPL3; measured indirectly for the OPLL |
| 6.5 the look-up | S4 `tab.txt` prose bullets under "Lookup in expTable" | as 6.3 | measured (restated) |
| 6.6 one's complement, two zeros | S4 `tab.txt` prose; `20150305.txt` prose (two centre peaks) | histogram of DAC codes | measured |
| 6.7 attenuation weights, clip at 127 | S4 `tab.txt` prose ("an increase of 128" per volume step, 16 per envelope step); `am.txt` prose (tremolo's 16 "found by experimentation"); `small-signals.txt` prose ("clipped at 127"); S1 Table III-3 and III-1-8 for 0.75 dB and 3 dB | captures; manufacturer for the dB weights | measured; documented for the weights |
| 6.8 mute at envelope level 124 | S4 `small-signals.txt` prose (carrier: counted and by peak widths; modulator: "a strong indication") | captures | measured (modulator by inference) |
| 6.9 half sine gives -0 | S4 `small-signals.txt` prose ("exactly 512 samples long"); S1 III-1-3 | capture; manufacturer | measured and documented |
| 6.10 carrier is 9 bits | S4 `tab.txt` prose (400 distinct values, peak row) | captures | measured |
| 6.11 modulator into carrier | S4 `mod-car.txt` prose ("-8pi..8pi", "drop 1 bit instead of 4", "matches _exactly_ ... for all values"); `fb.txt` prose ("-2047..+2047") | captures for TL 0 to 63 | measured; rounding U24 |
| 6.12 feedback | form: S4 `fb.txt` prose. Amount: S1 Table III-6 (page viewed) | captures; manufacturer | measured (form), documented (amount) |
| 6.13 the lag | S4 `mod-car.txt` prose | capture | measured as an observation; direction a choice |
| 6.14 feedback history at key-on | S4 `fb.txt` prose ("might be different from the actual start values") | none | unsettled (U21) |
| 7.1 field widths | S1 | manufacturer | documented |
| 7.2 19-bit counter | S4 `20150316.txt` prose and table (largest repeat count 512; die: "19 chains of 18 flip-flops") | captures; die photograph | measured |
| 7.3 the step | S4 `20150316.txt`: the 30-row table of repeat counts and the period table, with the prose notes on the two settings that do not move and on the lost bit | captures | measured |
| 7.4 multiplier | S1 Table III-1 (viewed); S6 table | manufacturer | documented |
| 7.5 frequency formula | S1 III-1-6 rearranged; S6 prints it | manufacturer | documented |
| 7.6 F-number 0 freezes | S4 `20150316.txt` prose note | capture | measured |
| 7.7 vibrato period | S4 `20151201.txt` prose ("regions ... 1024 samples", "repeats every 8192 samples") | captures aligned against generated sines, "approximately" | measured |
| 7.8 vibrato offsets | top range: S4 `20151201.txt` prose ("I only verified the last row"). Upstream: a table S4 copied from a GPL emulator, not transcribed here; the eight values are taken from S12's last row, which S4's stated step sizes for F-number $1C0, block 6 agree with. Other ranges: S12 | S4's check by alignment; an emulator's table | top range measured, approximate; **the rest unsettled (U4), emulator tier** |
| 7.9 depth 14 cents | S4 `20151201.txt` prose quoting Yamaha's manuals for other chips | manufacturer, other chips | documented for other chips only |
| 7.10 phase reset when damp ends | S4 `mod-car.txt`, `attack.txt` prose | captures | measured; exact sample U20 |
| 8.1 127 levels of 0.375 dB | S4 `20150320.txt` prose (120 steps to SL 15) | captures | measured (C1) |
| 8.2 effective rate | S1 III-1-2 (viewed) | manufacturer | documented |
| 8.3 Rks | S1 Table III-2 (viewed); S4 `sl-ksr.txt` prose table of ten settings, each "confirmed" | manufacturer; captures | documented and measured |
| 8.4 one shared counter | S4 `20150320.txt`, `adsr-transitions.txt` prose | first-segment lengths | measured |
| 8.5 step timing and patterns | the divider: S4 `sl-ksr.txt` prose ("13 - log2(512) = 4") and S1 Table III-7. The four patterns and their alignment: S4 `adsr-transitions.txt`, which lists the measured first-segment lengths for each and rules out every other rotation. History: S4 first took the scheme from a GPL emulator (he says so) and closes by noting that emulator's cores hold "exactly these sequences" | captures, by elimination | measured (the middle rule: S4's measurement is the source; the emulator is history) |
| 8.6 rates 0 to 3 | S1 Table III-7 note; S4 prose | manufacturer; capture | documented and measured |
| 8.7 rates 52 to 59 | S4 `attack.txt` section 3, printed rows, "exactly the same result as before" | captures, twice | measured; alignment a choice (U23) |
| 8.8 rates 60 to 63 | S4 `20150320.txt` prose; `attack.txt` rows | captures | measured |
| 8.9 total decay times | S1 Table III-7 (viewed; all 60 rows typed into the tests from the page) | manufacturer | documented |
| 8.10 attack formula | S4 `attack.txt` prose ("divide that by 16 (and round down). Subtract ... then subtract one more") and the printed sequences from 127 and 124 | captures | measured |
| 8.11 slow attack timing | S4 `attack.txt` prose ("IGNORE the 2 LSB bits"; "plateaus ... 13 plus 3 extra samples") | captures | measured |
| 8.12 fast attack | S4 `attack.txt` prose (single formula at 12:0, 13:0, 14:0; pairs and the 4/12, 4/4, 12/4 counts; the worked example 21 to 15 to 13). S1 Table III-7's attack column agrees: 0.84, 0.50, 0.28 and 0.14 ms are 42, 25, 14 and 7 samples | captures; manufacturer | measured; bit selection a choice (U23) |
| 8.13 attack rate 15 | S4 `attack.txt` section 2.8 prose, two experiments | captures | measured |
| 8.14 start at 127 or 124 | S4 `attack.txt` section 2.9 prose | captures | measured; 125, 126 are U12 |
| 8.15 attack times | S1 Table III-7 (viewed) | manufacturer | documented |
| 8.16, 8.17 damp at rate 12, ending at 124 | S4 `envelope.txt` prose (10.22 ms; "for higher frequencies the rate is faster"); `attack.txt` 2.9; S1 Figure III-1 ("DP: 10 ms") | captures; manufacturer | measured |
| 8.18 attack to decay | S4 `adsr-transitions.txt` prose | captures | measured, with S4's caveat |
| 8.19 sustain level test | S4 `sl-ksr.txt` table, `envelope.txt` experiments b2, b3 prose | captures | measured |
| 8.20, 8.21 sustain as one state | S4 `envelope.txt` d1, b1 prose; S1 Figure III-1 | captures; manufacturer | measured |
| 8.22 release rates | S4 `envelope.txt` prose; S1 III-1-6 ("the RR with the key off will be 5") and Figure III-1 | captures; manufacturer | measured and documented |
| 8.23 modulator has no release | S4 `envelope.txt` prose, two experiments; S6 prose | captures; community | measured; damp of modulators U13 |
| 8.24, 8.25 | S4 `attack.txt` 2.9; `envelope.txt` experiment a | captures | measured |
| 9.1 to 9.4 key scale level | S1 Tables III-4, III-5 (viewed) and notes; S4 `ksl.txt` prose ("There's an exact match between these tables and the measured values") for codes 1, 2, 3 | manufacturer; sparse captures | documented and measured (C3) |
| 10.1, 10.2 tremolo | S4 `am.txt` prose: fourteen levels, 960 / 512 / 192 samples, factor 16 "by experimentation" | captures. History: the emulators' scheme, described first | measured (restated) |
| 10.3 one counter for the chip | S1 block diagram | manufacturer | documented; U15 |
| 11.1 to 11.3 | S1 III-1-7, Table III-9 (viewed); S4 `rhythm.md` prose tables | manufacturer; captures | documented and measured |
| 11.4 key bits OR-ed | S4 `rhythm.md` prose, marked TODO. S12 does the same | captures, loosely | measured loosely (U7) |
| 11.5, 11.6 bass drum, tom | S4 `rhythm.md` prose | captures against a user tone | measured |
| 11.7 noise | S4 `lfsr.txt` (120 printed bits; Berlekamp-Massey; the once-a-sample polynomial) and its 2020 update with `rhythm.md`'s last section (50 hi-hat and 50 snare bits printed; "if we iterate the HH-state 3 times we end up in the SD-state"; "the next 20 samples matched perfectly"). History, as S4 tells it: the per-slot register and its polynomial were first seen by S4 in a GPL model's code and explained to him by its author; he then checked them by capture | captures | measured (the middle rule) |
| 11.8 snare | S4 `rhythm.md` prose table | captures | measured; U5, U6 |
| 11.9 cymbal | S4 `rhythm.md` prose | captures | measured up to sixteen forms; form and sign **emulator tier (S12)** |
| 11.10 hi-hat | S12 | an emulator | **unsettled (U22); emulator tier** |
| 11.11 own envelope and volume | S1 V-4; S4 prose | manufacturer; fits | documented; levels U11 (S12 scales the volume nibble as 3 dB a step and applies no total level) |
| 11.12 output twice | S1 III-4 prose; S4 `rhythm.md` prose ("_always_ identical") | manufacturer; captures | documented and measured |
| 11.13 | none | none | unsettled (U7, U8) |
| 11.14 | S6 prose | community | documented, tier 3 |
| 12.1 to 12.8 | S1 II-1, III-4; S4 `20150305.txt`, `rhythm.md`, `mod-car.txt` prose; S6 | manufacturer; captures; community | as marked in the spec |
| 13.1 to 13.3 | S1 III-1-1; S6 prose (from a forum post not read) | manufacturer; community | documented, tier 3, for the VRC7; U2 for the YM2413 |
| 14.1 to 14.3 | S1 III-1 prose; S6 prose; S4 `lfsr.txt` prose on the all-zero state | manufacturer; community | documented; U3 |

The audit shows that each statement has support in prose, a printed measurement,
or a named permissive emulator. It cannot show that what was seen before the
audit (section 4) left no trace in the wording of the spec; where the spec's
numbers went beyond what the prose supports, they were struck as listed above.

## 2. Decisions taken

### Policy

- **P1. The capture project (S4, S5).** Its write-ups have no licence. They are a
  source under the middle rule (restart.md rule 10): their measurements on a real
  chip are used and cited, with the note that the write-ups also quote code that
  was not used. Its C fragments and `.cc`/`.hh` files stay closed; the section of
  `rhythm.md` that quotes Nuked-OPLL stays closed; the three tables it says were
  copied from a GPL core are not used unless established independently. Its data
  files may be compared against in place; nothing is copied into this
  repository. The project's authors have not been contacted.
- **P2. The decapping site's page** (siliconpr0n, `vendor:yamaha:opl2`) refuses
  automated fetches and has not been read. It is cited by the NESdev wiki and
  emu2413 for the VRC7's ROM and may hold a dump of the YM2413's (unverified).
  Until it is read, the YM2413's voices have no dump.
- **P3. The DS1001's instrument bytes** stand, as a chip's ROM read out of real
  hardware and published on the NESdev wiki (rule 11), with the chain cited
  including who made the read-out. They would need another origin if that
  author objected to AI use (rule 7).
- **P4. Yamaha's sheets** (the catalog sheet says "Copying prohibited") are cited
  and quoted a sentence at a time; no pages or figures are copied. Tests carry
  the numbers they check with the page named.
- **P5. Issue threads of GPL projects** (for example openMSX issue 581, said to
  describe the YM2413's test register) are not read.
- **P6. The closed box as a measuring instrument.** Rule 8 allows it (recovering
  ROM contents, fitting constants), with values marked as closed-box
  measurements. It has not been used that way for this core: the YM2413's voices
  are emu2413's table, no constant was fitted to the model's output, and the
  rung 6 differences were not examined voice by voice. Used for U1, it could
  recover the 120 bytes of the YM2413's voice ROM as that model has them; choosing
  among the other unknowns (U4 to U9) that way would make the model the
  specification.
- **P7. Hardware.** None: the project is emulation-only. A bare YM2413 on a
  micro-controller (the capture project publishes its board) would settle U1,
  U2, U3 and U7 to U9 at tier 1.
- **P8. emu2413** is MIT, and its README lists a GPL file among what it "refers
  to". No code is taken from it. Its instrument table is used as data under rule
  11: marked hand-tuned, not a dump, emulator tier, with its MIT notice.
- **P9. Nothing is posted** to outside forums or projects. (Phase 0 found one
  thing others might want to know: the NESdev wiki and ymfm give the YM2413's
  snare byte as $48 where a measurement on the chip gives $68, C4.)

### Scope

A pure-Python model of two variants, `YM2413` and `DS1001`, offering the API in
[api.md](api.md), whose unit of time is the slot (4 input clocks) and whose
output is the chip's own sequence of 9-bit words. Everything after the pins is
the boards': the integrator, the VRC7's clipping and low-pass (S7), the mix
levels (S8). Every unsettled behaviour is variant data or a clearly named
switch, so that a measurement changes a value and not the structure.

The core is written from spec.md, not from another program, and takes from a
permissive source only **data** that has no better origin, with its notice:
today emu2413's tables (T1, T3, U22). Porting emu2413 or ymfm was considered and
rejected: both are tuned emulators whose reasons live in their own files, and a
port would import those choices without them.

### Technical defaults (all provisional)

Each is held as variant data or labelled PROVISIONAL or CHOICE in the code, and
pinned by one test in `tests/test_provisional.py`.

| | Question | What the core does |
|---|---|---|
| T1 | The YM2413's 15 melodic voices (U1) | emu2413's table, as data, with its MIT notice in the README and the file; marked "tier 5, hand-tuned, not a dump". Not ymfm's: that is by-ear data from a CC BY-SA page |
| T2 | The snare's last byte (C4) | $68 on both variants: the only measured value |
| T3 | Vibrato below the top pitch range (U4) | emu2413's `pm_table` (MIT), emulator tier |
| T4 | The YM2413's test register (U2) | the four bits S6 gives for the VRC7, on both variants |
| T5 | State after reset (U3) | registers 0; every envelope at 127 with its key off; phases, the shared counter and both LFO positions 0; the noise register 1. The VRC7's reset bit leaves the vibrato position alone (S6) |
| T6 | What the API returns | `take_outputs()`: per sample, the sum of the melody words and the sum of the rhythm words (each percussion word counted twice, as the chip outputs it), as integers. `take_samples()`: their sum. Slot-level words stay available to the validation harness. The boards scale |
| T7 | Write timing (U9) | a data write takes effect at the next slot boundary, for whichever operators it concerns; the waits are not modelled; aliases behave like their targets; addresses $08-$0D and $40 up are ignored |
| T8 | The percussion phase bit (U5, U6) | emu2413's form, which is the first of S4's sixteen, with emu2413's four hi-hat phases; the snare's bit from its own operator (with the ROM's settings M7 and C7 run in step, so the choice is inaudible) |
| T9 | Rhythm-mode key bits (U7) | each sound's key is its $0E bit OR its channel's key bit, as S4 reports; SUS acts as in melody mode |
| T10 | Switching rhythm mode mid-note (U8) | operators keep their envelopes and phases; only the instrument rows and the routing change |
| T11 | The modulator's one-sample lag (C7) | reproduce S4's measurement: the carrier is modulated by the modulator's output of the previous sample |
| T12 | Single-operator percussion levels (U11) | base attenuation 8 × the sound's own volume nibble, key scaling from its own ROM row, no total level |
| T13 | Attack from 125 or 126; a +2 step at the bottom (U12, U14) | the formula as it stands; the level saturates at 127 |
| T14 | Damp on modulators and percussion (U13) | yes on both, as on carriers |
| T15 | The DS1001's channels 6 to 8 (U16) | registers accepted, nothing output; rhythm mode forced on; no rhythm output |
| T16 | Step size | the slot. A whole-sample fast path was not needed: the core runs about 11 times real time on PyPy |
| T17 | Rung 2b's file format (U18) | to be worked out from the files and S4's prose; the tools' source is not opened to learn it |
| T18 | Other OPLL-family chips (YM2423, YMF281, YM2420) | not built: no board uses one, and the only allowed data for them is by-ear settings. A variant is a value holding a ROM and a few flags, so adding one later costs a table |

## 3. What was deliberately not read, and why

[phase0.md](phase0.md), "Sources found and not read", lists the sources found and
left unread with the reason for each. In short:

- **GPL and LGPL source** (restart.md rule 1): Nuked-OPLL wherever a copy sits
  (its `opll.c` is compiled for the closed box and never opened; only `opll.h`
  and `LICENSE` were opened), MAME's FM cores, openMSX's YM2413 engines, Genesis
  Plus GX, Gearsystem, BlastEm, VGMPlay.
- **The withdrawn core and anything derived from it** (rule 2; not published),
  and the boards' own audio source and their descriptions of the withdrawn
  core's internals.
- **In the capture project (S4):** every `.cc` and `.hh` file; every code fence
  and code-like line in the write-ups; `rhythm.md` between "## Nuke.YKT" and
  "## [2020/01/02] Update", and the code lines of that last section and of the
  update at the end of `lfsr.txt`; the numeric tables of `20150320.txt`,
  `am.txt` and `20151201.txt`, which S4 says were copied from an emulator; the
  spreadsheet `doc/ym2413-instr.ods` beyond identifying it; `attack-rates.txt`,
  `formula-f1-4.txt` and `predicted-sine.txt` (not needed).
- **Issue threads of GPL projects** (P5), in case they quote code.
- **The decapping site's page** (P2): refused to a plain fetch, twice; a second
  attempt with a browser's user-agent string was refused by the fetch tool and
  not retried another way, and no web-archive copy was available.
- **A scratch file left by the research phase** (`reference/scratch/attack_f.txt`,
  git-ignored): its contents were unknown and might have been program text.
- **Anything by an author who objects to AI use** (rule 7). S4's files were
  searched for the excluded author's name before reading (no match).

## 4. Material seen and not used

Things the rules keep out that were nevertheless seen during the work, and what
was done about each. Nothing from any of them is in the code.

1. **Lines of Nuked-OPLL quoted in S4's `rhythm.md`.** The file ends with a
   section comparing S4's findings with Nuked-OPLL and quoting its code. Three
   quoted expressions (the snare's and the cymbal's phase lines) and a table of
   that model's percussion settings were read before the section was recognised.
   No spec statement rests on them: the percussion statements cite S4's own
   measured formulas, which precede that section (spec 11.7 to 11.10, checked in
   the audit above).
2. **Tables S4 says were copied from a GPL emulator**: the tremolo sequence, the
   vibrato table and the envelope step patterns. The spec states the tremolo
   (10.2) and the step patterns (8.5) from S4's separate measurements of them;
   of the vibrato table only the measured row is used, and the other rows were
   struck and taken from emu2413 (7.8, U4, T3).
3. **S4's own C fragments and formula lines** (unlicensed source inside a
   measurement report): the table formulas, the exponent look-up and the
   operator chain in its short models, and formula lines written into running
   text (the phase step, "eg_shift = 13 - (rate / 4)", "m = 16 - (rate / 4)";
   the second was displayed once more by a later search of `20150320.txt`).
   The statements they bear on (7.3, 8.5, 8.12) are supported by S4's printed
   tables of measurements and prose, and the spec restates the behaviour in
   prose and arithmetic, not in their shape.
4. **Two rows of an emulator's key-scale table in S4's `ksl.txt`** (sixteen
   numbers). The same numbers are Yamaha's Table III-5, bottom row, multiplied by
   16/3; the core computes them from Yamaha's row (spec 9.2).
5. **S4's numbered list of sixteen boolean forms for the cymbal**, in running
   text. What its names mean is given only in a code block, which was not read;
   the particular form and the sign were struck and emu2413's used (11.9, T8).
6. **The spreadsheet `doc/ym2413-instr.ods`** in S4's repository, which tabulates
   the instrument settings of two emulators, one of them GPL-derived. Opened to
   identify it and closed; nothing taken.
7. **The state structure in Nuked-OPLL's `opll.h`** (a file rule 8 allows to be
   opened). Its field names were seen, among them names for rhythm-mode phase
   bits. Nothing was taken: the provisional cymbal form (T8) predates it and was
   not changed, and the harness does not touch the structure.
8. **A search-engine summary** named GPL emulator files and paraphrased one
   comment from them ("to-do item to tune up instruments ROM"). Nothing was
   opened.
9. **emu2413's synthesis functions** (MIT, permitted reading) beyond its tables:
   the percussion functions, key handling, and the carrier, modulator and
   exponential look-up functions beside them. Nothing was ported; they are
   recorded as emulator-tier corroboration under 6.5, 6.11 and 6.12, and the
   core's arithmetic is written from the spec. A reviewer may compare `_operate`
   in `opll.py` with emu2413's `lookup_exp_table` to check independence.
