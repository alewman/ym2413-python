"""The Yamaha YM2413 (OPLL) and the Konami VRC7's DS1001.

Written from documents and measurements (``docs/spec.md``), not from another
program's source: ``docs/restart.md`` has the rules. The names below are the
whole public surface (``docs/api.md``).
"""

from ym2413_python.opll import CLOCKS_PER_CYCLE, CYCLES_PER_SAMPLE, OPLL
from ym2413_python.variants import DS1001, YM2413, OPLLVariant

__all__ = [
    "CLOCKS_PER_CYCLE",
    "CYCLES_PER_SAMPLE",
    "DS1001",
    "OPLL",
    "YM2413",
    "OPLLVariant",
]
