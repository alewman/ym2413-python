# Hand-off brief: building the core

For the session that writes the code. Written 2026-11-12 at the end of Phase 0.

## Read first, in this order

1. [restart.md](restart.md): the rules. They bind you as they bound Phase 0.
2. [api.md](api.md): what the boards call.
3. [phase0.md](phase0.md): the sources, what was read and how, what was not, and
   the rule slips. Read "Rule slips" before opening any of S4's files.
4. [spec.md](spec.md): the behaviour, statement by statement, with C and U numbers.
5. [validation.md](validation.md): the ladder.
6. `seed/streams.py`: test inputs. Not a model, and not to be changed.

Then run `python scripts/fetch_references.py --local`. It fetches the pinned
permissive sources into the git-ignored `reference/` and checks the files cited in
place from sms-python and famicom-python.

## What is not to be opened

Unchanged from Phase 0: `/data/backup/nuked-derived/`; any Nuked source wherever a
copy sits; MAME's FM cores, openMSX's YM2413 engines, Genesis Plus GX, Gearsystem,
BlastEm, VGMPlay; famicom-python's and sms-python's `src/` audio code and their
descriptions of the old core's internals; anything by the excluded author. Added by
this phase:

- In the capture project (S4): every `.cc` and `.hh` file, `doc/ym2413-instr.ods`,
  and `results/rhythm/rhythm.md` from the heading "## Nuke.YKT" down to the heading
  "## [2020/01/02] Update", and the code lines of that last section and of the
  update at the end of `results/lfsr/lfsr.txt`.
- The short tables three of S4's write-ups say they copied from an emulator
  (`20151128/am.txt`, `20151201.txt`, `20150320.txt`): do not transcribe them.
  spec.md gives the measured behaviour they stand for.
- When a comparison against a model fails, the model's source stays closed (rule 8).

## Scope

A pure-Python model of two variants, `YM2413` and `DS1001`, offering the API in
api.md, whose unit of time is the slot (4 input clocks) and whose output is the
chip's own sequence of 9-bit words. Everything after the pins is the boards': the
integrator, the VRC7's clipping and low-pass (S7), the mix levels (S8, sms-python's
open item 14).

**Other family members** (YM2423, YMF281, YM2420 and the like): not worth
including. No board in the family uses one, and the only allowed data for them is
by-ear instrument settings (S14) and one emulator's presets. A variant is a value
holding a ROM and a few flags, so adding one later costs a table; do no more than
keep it that way.

## Package shape

- Repository `ym2413-python`, package `ym2413_python`, under `src/`.
- `tables.py`: the two ROM tables generated at import from the formulas of spec 6.3
  and 6.4, each with its source in the docstring (S11 for the formula, S4 for its
  standing on this chip); the multiplier table (S1); the key-scale row (S1 Table
  III-5); the envelope step patterns (S4, measured).
- `variants.py`: a frozen dataclass per variant: name, number of channels, whether
  there is a rhythm output, whether rhythm mode is forced on, the 15 instruments,
  the three percussion rows, and one field per unsettled item that a later
  measurement might change (the snare's last byte, the test register's reach). Each
  field's docstring names its source and its standing.
- `opll.py`: the chip. Per-operator state as 18-long lists, not 18 objects with many
  fields each. Fewer than 80 attributes on any instance.
- Exports exactly what api.md lists: `OPLL`, `YM2413`, `DS1001`,
  `CLOCKS_PER_CYCLE` (4), `CYCLES_PER_SAMPLE` (18).
- State as plain attributes; anything frozen that changes at run time declared for
  sms-python's save states (`state.VALUES`).
- Python floor 3.11, the newest PyPy supports. CI, if any: PyPy only, main and
  pull requests.
- MIT. The README says which document each behaviour comes from, which models were
  run and that their code was not read, and carries the notice of anything taken
  from a permissive source (see T1).
- `validation/` holds the harnesses of rungs 5 and 6. `validation/streams/` and
  `reference/` stay out of git.

Speed: the boards are reference boards and need not reach real time, but the
withdrawn core ran *Lagrange Point* at 0.39 times real time by stepping every
clock. Nothing in the spec needs a finer step than the slot, and most samples see
no write: compute a whole sample's 18 slots in one pass when no write falls inside
it, and fall back to slot-by-slot when one does. `run(a); run(b)` must still equal
`run(a + b)`.

## The recommended approach

**Write the core from spec.md, not from another program.** The three options,
weighed:

1. *Write from the manual and the measurements.* S1 gives the registers and every
   documented number; S4 gives, at tier 1, the operator arithmetic, the phase, the
   envelope and the percussion logic in enough detail that its author's own model
   matched captures sample for sample. Each rule in the code can cite a section of
   spec.md and through it a page or a capture. The result is the most readable and
   the best sourced, and it is what rule 3 asks for. Its cost is the list of
   unknowns, each of which needs a marked default.
2. *Port a permissive emulator with its notice.* emu2413 is MIT, small and close in
   structure to S4's findings (its comments credit them). But it is a tuned
   emulator, not a description: its own README lists Jarek Burczynski's `ymf262.c`
   (GPL) among what it "refers to", its instrument table was adjusted by hand
   across a dozen commits, and a port would import those choices without their
   reasons. ymfm is BSD and well commented, but its OPLL is a thin layer over an
   engine shared by a dozen chips, its README disclaims digital accuracy, and parts
   of the shared engine are annotated as written to match the Nuked models. A port
   of either would be legal with its notice and would still be the thing this
   restart exists to avoid: code whose reasons live in someone else's file.
3. *A mix*: write from the spec, and take from a permissive source only **data**
   that has no better origin, with its notice. Today that is one table (T1).

Recommended: 3, which is 1 plus one table.

Order of work: rung 0's skeleton; tables; one operator and the output word (spec 6);
phase (7); envelope (8), which is most of the work; key scaling and tremolo; a
channel with modulation and feedback; rung 1 and rung 2a tests as each part lands;
rhythm (11); the DS1001; then rungs 3, 5 and 6.

## The ladder

| Rung | Judge | State today |
|---|---|---|
| 0 | The API contract | to write |
| 1 | Yamaha's application manual (S1) | document in hand |
| 2a | The measured results S4 reports | write-ups in hand |
| 2b | S4's capture files, sample for sample | data in place; format unknown (U18), P1 |
| 3 | NESdev wiki on the VRC7 (S6) | document in hand |
| 4 | Recordings from a console | **none exist** |
| 5 | emu2413 and ymfm as detectors | sources pinned and fetched |
| 6 | Nuked-OPLL run as a closed box | nothing fetched; harness described |
| 7 | The boards | theirs |

Rungs 0 to 3 can be built and passed with what is in hand.

## Unknowns and contradictions

In full in spec.md sections 15 and 16. The ones that change what a player hears:

- **U1, C9**: the YM2413's 15 built-in voices. Every Master System FM game uses
  them. This is the one large gap.
- **U4**: vibrato depth below the top pitch range.
- **C4**: the snare's sustain level on the YM2413.
- **U7, U8**: rhythm-mode key bits and switching.
- **U11**: how loud the hi-hat, tom, snare and cymbal are against each other.

The ones a test will see and a player will not: U3, U5, U6, U9, U10, U12 to U15,
U19 to U21. U2 (the test register) is heard only by test programs.

Build every unsettled behaviour as variant data or a clearly named switch, so that
a measurement later changes a value and not the structure.

## Open decisions for Aubrey

Split as the sn76489 hand-off settled it: **policy** questions are yours;
**technical** ones the builder takes at the recommended default, marks
*provisional* in code and spec with the source's tier, and keeps as variant data.

### Policy

**P1. The capture project has no licence** (S4, S5: andete/ym2413, the write-ups by
Wouter Vermaelen). Phase 0 read its write-ups and cites them; spec.md's "measured"
statements rest on them almost alone. Three things to rule on: whether the capture
*data files* may be opened and compared against in place (rung 2b); whether the
short C fragments printed inside the write-ups may be consulted, as a description of
what was measured; and whether to ask the authors for a licence or a blessing, in
whose voice.
*Recommendation*: yes to comparing with the data in place, copying nothing. Treat
the fragments as part of the report: read, never transcribed, and the `.cc` files
stay closed. Asking is outward-facing and yours; a short human note would be the
courteous thing, since this core will owe that project more than any other source.

**P2. The siliconpr0n page** (`vendor:yamaha:opl2`) refuses automated fetches. The
NESdev wiki and emu2413 both cite it for the VRC7's ROM; it may also hold a dump of
the YM2413's ROM (a recollection, unverified).
*Recommendation*: open it in a browser, save it into `reference/`, and check two
things before it is used: who is credited (rule 7), and whether it states how each
table was obtained. If it holds a YM2413 dump, U1 is settled at tier 1 and T1 and
P6 fall away.

**P3. The author of the Nuked models.** His wishes about AI use are not known here.
Two things in the spec trace to him at one remove: the DS1001's instrument bytes
(emu2413 credits him for the read-out; taken here from the NESdev wiki), and the
hint that the noise register steps once per slot (told to S4's author, who then
confirmed it by capture).
*Recommendation*: both stand, because the first is a chip's ROM published on a
wiki and the second is S4's measurement. If you learn that he objects to AI use,
say so, and the DS1001's voices need another origin.

**P4. Yamaha's catalog sheet says "Copying prohibited".** The application manual
carries no such line in the scan.
*Recommendation*: as sn76489's D10: cite, quote a sentence at a time, copy no pages
or figures. Tests carry the numbers they check with the page named.

**P5. Issue threads of GPL projects** (openMSX issue 581, said to describe the
YM2413's test register) were not opened, in case they quote code.
*Recommendation*: allow prose in such threads to be read as a community document,
stopping at any code block. It is the only lead on U2 for the YM2413.

**P6. May the closed box be used as a measuring instrument, not only a detector?**
Rule 8 says a difference is settled by documents, recordings "and further
measurements of the model's outputs". One such measurement could settle U1: for
each built-in voice, search for the user-tone bytes whose output equals the built-in
voice's output on the model, sample for sample. No source line is read; the result
is 120 bytes of Yamaha's ROM as that model has them.
*Recommendation*: allow it for U1 only, written up in the README as exactly what it
is ("recovered from the outputs of a die-derived model run as a closed box; not
from its source; not checked on hardware"), and only if P2 does not produce a
dump. It is the difference between a core that is right for every Master System FM
game and one that is close. Do not extend it to choosing among U4 to U9 without
asking again: that would make the model the specification.

**P7. Hardware.** Nothing in the family can record a YM2413 or a VRC7, and the
project is emulation-only by your rule. A bare YM2413 on a micro-controller (the
capture project publishes its board) would settle U1, U2, U3, U7 to U9 at tier 1.
*Recommendation*: note it and move on; revisit only if P2 and P6 both fail.

**P8. emu2413's lineage.** MIT, and its README lists a GPL file among what it
"refers to".
*Recommendation*: take no code from it. Taking its instrument table as data, with
its notice (T1), is within rule 4; say if you would rather not.

**P9. Nothing is posted anywhere.** Phase 0 found one thing others might want to
know: the NESdev wiki and ymfm give the YM2413's snare byte as $48 where a
measurement on the chip gives $68 (C4). The NESdev forum bans AI-written posts.
*Recommendation*: post nothing.

### Technical (builder takes the default; all provisional)

| | Question | Default |
|---|---|---|
| T1 | The YM2413's 15 melodic voices (U1) | emu2413's table, as data, with its MIT notice in the README and the file; marked "tier 5, hand-tuned, not a dump". Replaced by a dump if P2 or P6 yields one. Not ymfm's: it is by-ear data from a CC BY-SA page |
| T2 | The snare's last byte (C4) | $68 on both variants: the only measured value |
| T3 | Vibrato below the top pitch range (U4) | peak = the F-number's top three bits, half-way = peak >> 1, mirrored negative: the shape S4 describes and whose top row it measured |
| T4 | The YM2413's test register (U2) | the four bits S6 gives for the VRC7, on both variants |
| T5 | State after reset (U3) | registers 0; every envelope at 127 with its key off; phases, the shared counter and both LFO positions 0; the noise register 1. The VRC7's reset bit leaves the vibrato position alone (S6) |
| T6 | What the API returns | `take_outputs()`: per sample, the sum of the melody words and the sum of the rhythm words (each percussion word counted twice, as the chip outputs it), as integers. `take_samples()`: their sum. Slot-level words stay available to the validation harness. The boards scale |
| T7 | Write timing (U9) | a data write takes effect at the next slot boundary, for whichever operators it concerns; the waits are not modelled; aliases behave like their targets; addresses $08-$0D and $40 up are ignored |
| T8 | The percussion phase bit (U5, U6) | S4's chosen form, its bits read as bits of the 10-bit phase; the snare's bit from its own operator (with the ROM's settings M7 and C7 run in step, so the choice is inaudible) |
| T9 | Rhythm-mode key bits (U7) | each sound's key is its $0E bit OR its channel's key bit, as S4 reports; SUS acts as in melody mode |
| T10 | Switching rhythm mode mid-note (U8) | operators keep their envelopes and phases; only the instrument rows and the routing change |
| T11 | The modulator's one-sample lag (C7) | reproduce S4's measurement (rung 2a has the "15 then 1" test); do not add a delay line if the slot order already gives it |
| T12 | Single-operator percussion levels (U11) | base attenuation 8 × the sound's own volume nibble, key scaling from its own ROM row, no total level |
| T13 | Attack from 125 or 126; a +2 step at the bottom (U12, U14) | the formula as it stands; the level saturates at 127 |
| T14 | Damp on modulators and percussion (U13) | yes on both, as on carriers |
| T15 | The DS1001's channels 6 to 8 (U16) | registers accepted, nothing output; rhythm mode forced on; no rhythm output |
| T16 | Step size | the slot; whole samples in one pass when no write intervenes |
| T17 | Rung 2b's file format (U18) | work it out from the files and S4's prose once P1 allows; do not open the tools' source to learn it |
| T18 | Other OPLL-family chips | not built |

## Decisions taken (2026-11-13)

The owner chose the middle rule for second-hand facts and asked that every fact
carry its provenance (restart.md rules 9 to 11). The policy questions above, as
they now stand; technical questions T1 to T18 are taken at their defaults,
provisional.

| | Decision |
| --- | --- |
| P1 | The capture project's write-ups are a source under the middle rule: its measurements on a real chip are used and cited, with a note that the write-ups also quote code that was not used. Its C fragments and `.cc`/`.hh` files stay closed; the section of `rhythm.md` that quotes Nuked-OPLL stays closed; the three tables it says were copied from a GPL core are out unless established independently. Its data files may be compared against in place; nothing is copied into this repository. Nobody is contacted for now. |
| P2 | Open: the decapping site's page needs a person with a browser. Until then the YM2413's voices have no dump. |
| P3 | The DS1001's instrument bytes stand, as a chip's ROM read out of real hardware and published on the NESdev wiki (rule 11), with the chain cited including who made the read-out. Revisit if that author objects to AI use. |
| P4 | Yamaha's sheets are cited and quoted a sentence at a time; no pages or figures are copied. |
| P5 | Issue threads of GPL projects are not read. |
| P6 | **Not allowed for now**: the closed box is a detector, not a measuring instrument. The owner has not ruled on recovering ROM contents from a model's outputs. |
| P7 | No hardware. Noted. |
| P8 | No code from emu2413. Its instrument table may be used as data under rule 11: marked hand-tuned, not a dump, emulator tier, with its MIT notice. |
| P9 | Nothing is posted. |
