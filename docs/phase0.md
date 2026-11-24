# Phase 0: the sources and what each can settle

Written 2026-11-12 under [restart.md](restart.md), before any chip model was
written. This document lists every source found, how it was read, and what it can
and cannot settle. The behaviour itself is in [spec.md](spec.md); the decisions
named P1 to P9 below, and everything seen during the work that the rules keep
out, are in [provenance.md](provenance.md).

## How to read the table

**Tier**

1. Captured from hardware, or a photograph or measurement of the die.
2. The manufacturer's documents (Yamaha).
3. Community documents and tests whose authors checked them on real hardware.
4. Hardware-description reimplementations. (None was found that may be read.)
5. Emulators.

**Read**: *direct* means the file was opened and read here. *summary* means it was
read through a fetch tool that returns a summary, so nothing from it is quoted as
exact wording.
*not read* means not opened, and says why.

Paths under `reference/` are fetched by `scripts/fetch_references.py` and pinned by
commit and SHA-256. Paths in sms-python and famicom-python (checkouts beside this
repository) are cited in place, not copied; `fetch_references.py --local` checks
that they are still the bytes read.

## Sources read

| ID | What | Where | Licence, author | Tier | Read |
|----|------|-------|-----------------|------|------|
| S1 | "FM Operator Type-LL (OPLL) Application Manual", 30 pages: outline, pins, bus, register map, every register, the rate tables, F-number tables, rhythm, DAC figure, electrical data | `sms-python/reference/smspower/chipsym2413am.pdf` (image only). A byte-identical copy is `sms-python/reference/src/ym2413/doc/YM2413am.pdf`. `ym2413am.zip` beside it holds 31 GIF pages of the same manual and was not opened | © Yamaha. "Scanned by Ricardo Bittencourt, cleaned and converted to PDF by HansO, 2001". No licence; cited and quoted briefly | 2 | direct. Every page by OCR; printed pages 4, 5, 6, 8 to 17 and 19 also viewed as images, which is where every table in spec.md was read. OCR of the tables is unusable |
| S2 | "YM2413 OPLL" catalog sheet, catalog no. LSI-212413A2, 1996.6, 10 pages: pins, block diagram, register map, the envelope figure, timing, electrical data | `ym2413.pdf` inside `sms-python/reference/smspower/ym2413pdf.zip` (image only) | © Yamaha. Its last page says "Copying prohibited © 1987 YAMAHA CORPORATION" (decision P4) | 2 | direct: pages 1 and 3 viewed, the rest by OCR |
| S3 | "YM2413B OPLL" catalog sheet, catalog no. LSI-212413B2, 1999.5, 10 pages | `sms-python/reference/src/ym2413/doc/YM2413B(-F).pdf` (image only). An 8-page scan of S2 sits beside it as `ym2413_ds.pdf` | © Yamaha | 2 | first page only, viewed. Not studied: see U17 |
| S4 | The openMSX YM2413 reverse-engineering project: 21 dated write-ups of measurements on a real YM2413 (a micro-controller board drives the chip's pins and clock and samples MO and RO with an ADC), 2015 to 2020 | `sms-python/reference/src/ym2413/results/` (<https://github.com/andete/ym2413> at `4893d1c`). The write-ups are by Wouter Vermaelen (one is signed "Wouter"; the commits are his); the repository is Joost Yervante Damad's ("andete") | **No licence stated.** Read and cited; nothing copied into this repository (decision P1) | 1 | direct, the prose of all 21 files listed in `fetch_references.py`. Long numeric tables and the C fragments printed inside the write-ups were skipped by a filter where possible; see provenance.md, "Material seen and not used" |
| S5 | The same project's captured data: 81 `gold-*` rhythm captures, 16 volume captures (`analyze/volume/*.raw`, `*.out`), about 150 plots | `sms-python/reference/src/ym2413/results/rhythm/`, `analyze/volume/`, `results/**/*.png` | as S4 | 1 | not opened, apart from confirming that `gold-sd-000` is a text file. The format is undocumented in what was read (U18) |
| S6 | NESdev wiki, "VRC7 audio": registers, the test register, the DS1001's instrument set read out through the chip's debug mode, the debug mode's pins, differences from the OPLL | `famicom-python/reference/nesdev-wiki/VRC7_audio.wiki` | NESdev wiki content; no licence in the file; cited | 3 (its instrument table and test-register notes are from hardware) | direct, whole file |
| S7 | NESdev forum thread 17745, "VRC7 and 5B amplifier investigation, also VRC7 LFO reset!" (rainwarrior and others, 2018) | `famicom-python/reference/nesdev-forum/17745.html` | forum posts; cited | 3, with recordings | direct, the first page's VRC7 passages |
| S8 | famicom-python's own notes on measured expansion-audio levels (rainwarrior's `db_vrc7`: +11.3 dB against an APU square; James-F: +10.88 dB) | `famicom-python/docs/undocumented-behavior.md`, "Measured expansion-audio mix levels" | the family's own document, citing NESdev forum thread 17741 (not opened here) | 3, second hand | direct, that table only |
| S9 | SMS Power development wiki, "YM2413" and "Audio Control Port" | `sms-python/reference/smspower-wiki/YM2413.pmwiki`, `AudioControlPort.pmwiki` | SMS Power site content; cited | 3 | direct, whole files. The YM2413 page includes S4's notes by reference and says of them: "the die shots referred to in the above notes are actually from a FHB013 which is a YM2413 derivative with a different instrument set. There are no actual YM2413 die shots available." |
| S10 | JoppyFurr, "YM2413 TestRom" (SMS Power coding competition 2024): an interactive tool for comparing an emulator with a console | ROM: `sms-python/tests/test_roms/smspower/YM2413TestRom-SMS-1.00.zip`. Thread: `sms-python/reference/smspower-forum/topic-20057.txt`. Source: <https://github.com/JoppyFurr/YM2413-TestRom> (not fetched, licence not checked) | homebrew | 3 (a tool) | thread direct; ROM not run |
| S11 | Matthew Gambrell and Olli Niemitalo, "OPLx decapsulated", 20 April 2008: the log-sine and exponential ROMs of a YM3812 and a YMF262 read bit by bit under a microscope, with formulas that reproduce them | <https://docs.google.com/document/d/18IGx18NQY_Q1PJVZ-bHywao9bhsDoAqoIn1rIm42nwo> (not fetched into `reference/`) | no licence statement | 1, for the OPL2 and OPL3 | summary. S4 quotes its two formulas, and those were read direct |
| S12 | Mitsutaka Okazaki, emu2413 v1.6.4 | `reference/emu2413/` (<https://github.com/digital-sound-antiques/emu2413> at `a1d5120`) | MIT, "Copyright (c) 2001-2019 Mitsutaka Okazaki" (`LICENSE` read; the source header says 2026) | 5 | direct: `LICENSE`, `README.md`, the header, the instrument tables and the constant tables after them (lines 1 to 224), and the commit titles of `emu2413.c`. The synthesis code was searched for attributions, not studied |
| S13 | Aaron Giles, ymfm | `reference/ymfm/` (<https://github.com/aaronsgiles/ymfm> at `81aec25`): `LICENSE`, `README.md`, `src/ymfm_opl.h`, `ymfm_opl.cpp`, `ymfm_fm.h`, `ymfm_fm.ipp` | BSD-3-Clause, "Copyright (c) 2021, Aaron Giles" (`LICENSE` and file headers read) | 5 | direct: README, the OPLL passages of `ymfm_opl.cpp` (key code, envelope constants, write ports, output, instrument tables); the shared engine searched for attributions, not studied |
| S14 | David Viens (plgDavid) and Hubert Lamontagne, "Copyright-free OPLL(x) ROM patches": instrument settings for the YM2413, YM2423, YMF281 and VRC7 | `reference/opll-patches/` (GitHub wiki of `plgDavid/misc`, wiki commit `b8b2030`) | "License: Attribution-ShareAlike CC BY-SA" on the page | 3 by method (matched against real chips by ear), but declared inexact | direct, whole page |
| S15 | SMS Power's FM-unit schematics for a home-made board, with the mail that came with them | `sms-python/reference/smspower/smsopll.zip` | Leonard Silva de Oliveira; no licence | 3 | `mails.txt` only. Nothing about the chip |
| S16 | Search-engine summaries (one query) | - | - | - | summary. Yielded only pointers: Yamaha's sheets on Bitsavers (`YM2413_198604.pdf`, `YM2413_199606.pdf`, not fetched), and file names of GPL emulators, none opened |

Nothing was ported from any of these. S12 and S13 are the only source code read on
purpose, and both are permissive.

## Sources found and not read

| What | Why not |
|------|---------|
| siliconpr0n's wiki page "vendor:yamaha:opl2" (<https://siliconpr0n.org/archive/doku.php?id=vendor:yamaha:opl2>), which S6 cites for the "VRC7 Instrument ROM Dump" and S12 cites for "VRC7 presets ... by Nuke.YKT" | The site answers HTTP 403 to a plain fetch, twice. No way round the refusal was tried. It may also hold the YM2413's own instrument ROM; that is a recollection, not something read here. Decision P2 |
| The die photographs S4 points to (`siliconpr0n.org/map/yamaha/ym2413b/mz_ns50xu/`, `.../fhb013/mz_ns50xu/`), and S4's annotated crops of them | A photograph settles nothing without tracing it. S4's reading of them (register widths, the DAC's 32 by 16 switch array) is taken from S4's prose. S9 says the die is an FHB013, not a YM2413 |
| S4's source files: `results/**/model*.cc`, `tables.hh`, `ar-dr.cc`, `lfsr.cc`, `rhythm/model6.*`, `sweep.cc`, `top4.cc`, `analyze/*.cc`, `testprog/`, `tool/`, `tool2/` | Emulator and tool source in a repository with no licence: excluded |
| S4's `doc/ym2413-instr.ods` beyond its first rows | It tabulates the instrument settings of two emulators (Okazaki's and Burczynski's) side by side. The second is GPL-derived. Opened to see what it was; closed; nothing taken |
| The section headed "Nuke.YKT" in S4's `rhythm/rhythm.md` | It quotes lines of Nuked-OPLL. Part of it was read before it was recognised: see provenance.md, "Material seen and not used" |
| Nuked-OPLL, wherever it sits (copies were at `sms-python/reference/src/Nuked-OPLL` and `famicom-python/reference/src/Nuked-OPLL` in Phase 0; famicom-python's moved aside on 2026-11-24, sms-python's in the same sweep) | restart.md rule 1. Not opened, not searched |
| MAME's `ym2413.cpp` and `ymf262.cpp` (Jarek Burczynski and others, GPL), openMSX's YM2413 engines, Genesis Plus GX, Gearsystem, BlastEm, VGMPlay's cores | restart.md rule 1 |
| The withdrawn core and anything derived from it (not published) | restart.md rule 2 |
| famicom-python's and sms-python's `src/` audio code and their descriptions of the old core's internals | excluded: they describe the withdrawn core |
| openMSX issue 581, which S4 says holds "new information regarding the YM2413 test register" | An issue thread of a GPL project that may quote its code. Unsure, so not opened. Decision P5 |
| NESdev forum posts p=236371 ("VRC7 test register described"), p=224897 (the silence bit) and thread 9141 (patch set revisions) | Not in the pinned snapshot; S6 summarises them. Reading them is allowed; they have not been fetched |
| The OPL3 research forum S4 cites (`forums.submarine.org.uk`, posts by "carbon14" and "opl3") | Not fetched. It is about the YMF262; S4 states what it took from it |
| Yamaha's manuals for the Y8950, YMF262 and YMF278 | S4 quotes their tremolo and vibrato depths (4.8 dB, 14 cents). Not in hand |
| Kevin Horton's `vrcvii.txt`, zzo38's `vrc7test.zip` (both linked from S6) | Not fetched yet: a hardware-era description and a test program, both worth reading |

Nothing by the excluded author was fetched, read or cited. S4's files were searched
for his name before reading (no match). The siliconpr0n photographs S4 uses carry
the imaging code `mz`, which is not his.

## What was checked here

Scratch work only, under `reference/scratch/` (not committed):

1. **The manual's rate tables are arithmetic.** Decay rate 4 in Table III-7 is printed
   as 20926.60 ms; 127 × 2^13 samples at 72 / 3,579,545 s each is 20,926.58 ms. The
   fastest decay is printed as 1.27 ms; 63 samples is 1.27 ms. Attack rate 4 is
   printed as 1730.15 ms; 21 × 2^12 samples is 1,730.15 ms. So S4's reading of the
   table (its `127, 102, 85, 73` and `21, 17, 14, 12` multipliers) holds for the
   rows tried.
2. **The manual's F-number table was computed for 50 kHz, not 49,716 Hz.** A = 440 Hz
   in octave 4 is printed as F-number 288; 440 × 2^18 / 50,000 / 2^3 = 288.4, while
   at the true sample rate it is 290.0.
3. **The LFO rates.** 49,716 / 13,440 = 3.699 Hz (the manual's 3.7 Hz tremolo);
   49,716 / 8,192 = 6.069 Hz against the manual's 6.4 Hz vibrato (contradiction C2).
4. **The DS1001 instrument table in S6 equals emu2413's VRC7 table**, all 15 rows and
   the three percussion rows (script comparison). They are one dump, twice printed.
5. **The two permissive emulators do not agree on the YM2413's instruments.**
   emu2413's and ymfm's tables differ in 31 of 120 bytes, and in every one of the 15
   rows. ymfm's DS1001 table differs from the debug-mode dump in 48 bytes.

## The built-in instruments: where the data can come from

This is the largest provenance question, so it is answered here in one place.

**DS1001 (VRC7).** Settled. S6 prints the 15 instruments and the three percussion
rows, "dumped using the VRC7 rewired into a debug mode", citing siliconpr0n. S12
prints the same bytes and credits them: "VRC7 presets ... by Nuke.YKT". It is a
read-out of the chip's ROM through its own pins: tier 1 by method, taken here from
a tier 3 page. The person credited is the author of the Nuked models; the bytes are
Konami's and Yamaha's, and they are taken from the NESdev wiki, not from his code
(decision P3).

**YM2413.** Not settled. No allowed source in hand claims to be a dump of the
YM2413's instrument ROM.

- S13 (ymfm) says of its table: "table below taken from
  https://github.com/plgDavid/misc/wiki/Copyright-free-OPLL(x)-ROM-patches".
- That page (S14) says: "The following OPLL patches have been guessed by ear to the
  point where rapidly toggling between the custom sound and each individual ROM
  sound made no difference", and: "They are NOT exact, but this is exactly the
  point, to be copyright safe." It is CC BY-SA.
- S12 (emu2413) does not say where its 15 melodic rows came from. Its header thanks
  andete's notes, "ymf262.c by Jarek Burczynski", Nuke.YKT for the VRC7 presets and
  Chabin for the YMF281B's. Its commit titles read "Improve ROM instruments"
  (2019-12-11), "Tweak ROM voice parameters" (2020-01-06), "Fix piano attack rate",
  "Fix acoustic bass decay": a table adjusted by hand over time, not a dump. Its
  percussion rows are marked "(from VRC7)".
- S4's author worked on the instrument ROM for over a year and reports "settings
  that are close (sometimes very close) to the built-in instruments, but never 100%
  identical"; his melodic values are not published in what was read.
- For the **percussion** rows there is a measurement: S4 found custom-instrument
  settings that reproduce the bass drum on a real YM2413, and envelope settings for
  the other four that "match pretty well", and they equal the VRC7 dump's three
  rows. S6 and S13 disagree with that in one byte (contradiction C4).

So today the choices for the YM2413's 15 melodic instruments are: emu2413's table
(MIT, hand-tuned, close); the siliconpr0n page if a person opens it and it proves to
hold a dump (P2); or values recovered by measurement, either from a real chip
(nobody in the family has one wired up) or from a reference model run as a closed
box (decision P6). The core uses emu2413's table, marked as not a dump (T1 in
provenance.md).

## What each source can and cannot settle

- **S1, S2 (Yamaha)** settle the register map; every field's meaning; the multiplier
  table; the key-scale-rate table; total level, volume and sustain level weights; the
  key-scale-level table at 3 dB per octave; the feedback table; total envelope times
  for every rate; the three fixed rates in the envelope figure as times; the names of
  the instruments; which slots make which percussion sound; the order of slots and
  that MO and RO are time-multiplexed pulses with the percussion output twice; 72
  clocks per sample; the write waits; that IC clears the registers. They do **not**
  give any table's contents, the envelope's step size (the printed "0,325 dB" is not
  what the chip does), the shape of the attack, the LFO depths or shapes, the
  instrument ROM, the noise generator, the percussion phase logic, the output
  word's scaling, the test register, or anything bit-exact.
- **S4** settles, by capture from one YM2413: the output's 9-bit range with two
  zeros; the sine and exponential tables (the OPL2's, per S11) and how they are
  combined; volume, sustain and envelope weights; the 10.9-bit phase counter and its
  step formula; the multiplier table; vibrato's rate and the bottom row of its
  depths; tremolo's rate, depth and exact stepping; modulation and feedback
  scaling, including the one-sample lag; key scale level and rate; decay, release
  and attack stepping for every rate; the damp phase and its end; the envelope's
  states and what each register change does; the modulator's missing release; the
  muting of quiet operators; the half-sine's signed zero; the noise generator and
  where it is stepped; the percussion phase formulas (one of them only up to 16
  equivalent forms); the slot order and the percussion repeats; register aliases
  $19 to $1F. It **cannot** settle the melodic instrument ROM, the test register,
  rhythm-mode switching while notes play, the sustain bit on channels 7 to 9 in
  rhythm mode, reset state, write timing inside a sample, or anything about a second
  chip: it is one part, of unstated date code.
- **S6** settles the DS1001's instrument ROM, that its rhythm outputs are absent, the
  four test-register bits as tested on a VRC7, the reset bit's reach, and the write
  waits Lagrange Point observes. Its statements about the synthesis core are
  community summary.
- **S7, S8** settle board-level facts only: the VRC7's output clips at a little under
  twice one channel's full level, is low-passed, and stands 11.3 dB (10.9 on a second
  console) above an APU square. These belong to famicom-python.
- **S9** settles the Master System's ports and which consoles have the chip; nothing
  inside the chip beyond S1.
- **S10** can compare by ear or by recording; nobody's recording of it is in hand.
- **S11** settles the contents of the two ROM tables for the OPL2 and OPL3. That the
  OPLL's are the same rests on S4 (die photographs compared by eye, then the captured
  waveforms predicted exactly for volumes 1 to 15).
- **S12, S13** show how two emulators chose to do everything, and name their own
  sources. Where they agree with S4 they add nothing; where S4 is silent they are all
  there is (see below).
- **S14** settles nothing exactly, by its own account.

## Behaviours with no source above tier 5

Only the emulators (S12, S13) speak to these, or a source says so only by quoting an
emulator:

- The YM2413's 15 melodic instruments, as exact bytes (S12: hand-tuned; S13: by ear).
- Vibrato depth for the F-number's top three bits other than 111. S4 prints a table
  it says was "copied from Burczynski core" and measured only its last row.
- The percussion volumes' exact scaling and whether the top cymbal and hi-hat are
  attenuated like a carrier.
- What the three percussion channels' key-on bits and sustain bits do in rhythm mode
  (S4 reports the key bits act as if OR-ed with register $0E's, marked "TODO").
- Rhythm mode switched on or off while notes sound.
- How a board should turn the multiplexed output words into one level per sample
  (S13 sums and scales; the chip does no such thing).

## Behaviours with no source at all (among those allowed)

- The YM2413's test register $0F. S6 describes the VRC7's four bits; S4 has only a
  rumour and a pointer to a thread not read (P5).
- The state after IC or power-on beyond "registers cleared": the phase counters, the
  envelope levels and states, the global counter, the LFO positions, the noise
  register.
- When within a 72-clock sample a write takes effect, what a write does if the wait
  times are not kept, and the longer latency S4 guesses for the alias registers.
- Whether the YM2413B behaves differently from the YM2413 (U17).
- The exact formula for the percussion phase bit among S4's 16 candidates, and
  whether the snare's phase comes from channel 7's modulator or carrier.
- The envelope's behaviour at levels 125 and 126 as attack starting points.
- The DS1001's differences from the YM2413 inside the synthesis core, if any, beyond
  the instrument ROM, the channel count and the missing rhythm output.
- The analogue output: levels in volts beyond "2/5 Vcc" typical, the two zeros'
  spacing, the DAC's non-linearity (S4 saw a 32 by 16 pattern and did not tabulate
  it).

## Material seen and not used

Phase 0 saw some material that the rules keep out: lines of Nuked-OPLL quoted in
S4's `rhythm.md`, small tables S4 says it copied from a GPL emulator, some of S4's
own C fragments, and the spreadsheet above. Each item, and what was done about it,
is listed in [provenance.md](provenance.md), "Material seen and not used".
