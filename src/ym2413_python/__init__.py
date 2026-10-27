"""Yamaha YM2413 (OPLL) and its relatives: a readable reference core."""

from .chip import CLOCKS_PER_CYCLE, CYCLES_PER_SAMPLE, EXPONENT, LOG_SINE, OPLL
from .variants import (
    DS1001,
    VARIANTS,
    YM2413,
    YM2413B,
    YM2423,
    YMF281,
    YMF281B,
    Instrument,
    OPLLVariant,
)

__all__ = [
    "CLOCKS_PER_CYCLE",
    "CYCLES_PER_SAMPLE",
    "DS1001",
    "EXPONENT",
    "LOG_SINE",
    "OPLL",
    "VARIANTS",
    "YM2413",
    "YM2413B",
    "YM2423",
    "YMF281",
    "YMF281B",
    "Instrument",
    "OPLLVariant",
]
