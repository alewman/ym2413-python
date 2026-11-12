# Restart rules

This repository is a restart. An earlier core under this name was a
function-by-function translation of a GPL or LGPL C model, published as MIT with
a README that said nothing was copied. That was wrong on both counts. It was
withdrawn on 2026-11-12 and archived privately; this one starts over.

## The rules

1. **No GPL or LGPL source is read.** Not to learn the algorithm, not to check a
   constant, not to settle a doubt. That covers the Nuked models (Nuked-OPLL,
   Nuked-PSG, Nuked-OPN2, Nuked-MD), YM2608-LLE, MAME's GPL sound cores, BlastEm
   and Genesis Plus GX (non-commercial: never copied, and here not read either).
2. **The archived cores are not read**, in Python or Rust, nor any document that
   describes the chip's internals in their terms. They are not in this tree.
3. **Translating a model statement by statement is copying**, whatever the
   language and however many citations it carries. Code here is written from a
   written description of behaviour, not from another program's source.
4. **Permitted sources**: manufacturer manuals and data sheets, community
   documents (wikis, forum research threads), hardware measurements and
   recordings, and source code under a permissive licence (MIT, BSD, zlib, public
   domain). Check the licence in the file itself before reading it. If any
   permissive code is ported, its copyright notice comes with it and the README
   says so.
5. **Every rule in the code names its source**, or says it is a choice.
6. **Say what is known and how.** The earlier core claimed to equal a die-derived
   model at every internal clock. This one claims only what it measures: which
   documents a behaviour comes from, which recordings it was compared with, and
   how close it came. Not every core will be die-exact, and that is fine.
7. **An author who objects to AI use of their work is left out**, even where the
   licence would allow it.
8. **Undecided, so off limits for now**: building and running a Nuked model as a
   closed-box referee (compare outputs, never read source). Do not fetch one
   until the owner says so.

## The order of work

1. **Phase 0**: find the sources and the judges. A document per chip listing
   every source with its licence and tier, what each can and cannot settle, and
   which behaviours have no source at all. No code.
2. **A behaviour spec** written from those sources: registers, timing, outputs,
   each statement with its source.
3. **The code**, written from the spec.
4. **Measurement** against hardware recordings first, emulators second.
5. **Adoption** by the boards, through the API in [api.md](api.md).

If you meet a source whose licence or author's wishes you are unsure of, stop and
report. Do not decide for yourself.
