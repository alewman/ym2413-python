# ym2413-python

The Yamaha YM2413 (OPLL) FM sound chip, and the VRC7's DS1001 variant, as a
readable pure-Python core for the family's boards (sms-python's FM unit,
famicom-python's mapper 85).

**Status (2026-11-12): Phase 0 is done; there is no model yet.** This repository is
a restart: read [docs/restart.md](docs/restart.md) first for why and for the rules.
Phase 0 found the sources and the judges and wrote no chip code:

- [docs/phase0.md](docs/phase0.md): every source, its licence and tier, what it can
  settle, and what has no source.
- [docs/spec.md](docs/spec.md): the behaviour, each statement marked documented,
  measured or unsettled.
- [docs/validation.md](docs/validation.md): the ladder of checks.
- [docs/handoff-brief.md](docs/handoff-brief.md): for the build session, with the
  open decisions.
- [docs/api.md](docs/api.md): what the boards need.

`python scripts/fetch_references.py --local` fetches and verifies the references.

`seed/streams.py` is the one thing carried over: synthetic register streams,
each exercising one feature. They are test inputs. They say nothing about what
the chip should output.

MIT.
