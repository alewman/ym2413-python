# ym2413-python

The Yamaha YM2413 (OPLL) FM sound chip, and the VRC7's DS1001 variant, as a
readable pure-Python core for the family's boards (sms-python's FM unit,
famicom-python's mapper 85).

**Status (2026-11-12): a restart, with no model yet.** Read
[docs/restart.md](docs/restart.md) first: it says why this repository starts
over and the rules it starts under. [docs/api.md](docs/api.md) is what the
boards need from it.

`seed/streams.py` is the one thing carried over: synthetic register streams,
each exercising one feature. They are test inputs. They say nothing about what
the chip should output.

MIT.
