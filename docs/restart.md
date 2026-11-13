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
8. **A reference model may be run, never read** (the owner, 2026-11-12: "to run
   it through some harness so we could see what it does, not to copy its
   code"). A Nuked model, or any other GPL or LGPL emulator, may be fetched into
   the git-ignored `reference/`, built, and driven by a small harness written
   here, so that its outputs can be compared with ours. The conditions:
   - the harness uses the model's public header for the calls it must make and
     nothing else; the model's `.c` files are not opened, searched or quoted;
   - the harness is the only code that touches the model, lives in
     `validation/`, and nothing built from the model is committed or shipped;
   - a model is a **detector**: a difference says where to look. When a
     comparison fails, the answer is sought in the documents, the recordings and
     further measurements of the model's outputs. Opening the model's source to
     see why is the one thing that turns a referee back into a blueprint, and
     it is not done. If nothing else settles it, the difference is written down
     as open;
   - the README says which models were run and that their code was not read.

9. **Provenance is the point** (the owner, 2026-11-13: "we need to cite where we
   got all of our pieces of information"). Every fact the core relies on carries
   its chain: the document or post, its author, how the fact was established
   (manufacturer's statement, measurement on a real chip and by what method,
   read-out, recording), and anything upstream of it that is known. A reader must
   be able to follow any number in the code back to where it came from.
10. **Second-hand facts: the middle rule.** A fact is usable when someone
    established it on real hardware and says so in prose, whatever first
    suggested it, including an emulator. So a researcher's "I measured this on
    my console and it is X" is a source even where X was first seen in an
    emulator's code; cite the researcher and note the history. What stays out:
    - code fragments, wherever they appear (a forum post, a write-up, an issue
      thread): stop reading at the code block; never transcribe one;
    - tables that a source says were copied from a GPL or LGPL program, unless
      the same values are established independently, in which case cite that;
    - a fact whose only support is "an emulator does this": it may be used as a
      provisional default, marked emulator-tier, with the emulator named, and
      only from a permissively licensed emulator's own documentation or code.
    If a source mixes measurement with quoted GPL code, take the measurement and
    say in the provenance that the source also quotes code that was not used.
11. **A chip's ROM contents are facts about the chip.** Bytes read out of real
    hardware and published (for example the VRC7's instrument set on the NESdev
    wiki, from the chip's debug mode) are usable with their full chain cited.
    Values tuned by ear or by hand in an emulator are that emulator's work:
    usable only from a permissive source, with its notice, and marked as not a
    dump.

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
