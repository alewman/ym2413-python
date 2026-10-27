"""Rung 1 in the suite: a few synthetic streams against Nuked-OPLL, every cycle.

The full run is scripts/referee.py (every stream, every variant); this keeps the
short streams in pytest where the referee is built (validation/build_referees.sh).
"""

from __future__ import annotations

import pytest
from referee import REFEREE, compare
from streams import STREAMS

from ym2413_python import VARIANTS

SHORT = ("silence", "fast_writes", "back_to_back", "rhythm_toggles", "test_register")


@pytest.mark.referee
@pytest.mark.parametrize("variant", sorted(VARIANTS))
@pytest.mark.parametrize("name", SHORT)
def test_short_streams_equal_nuked_opll(name: str, variant: str) -> None:
    if not REFEREE.exists():
        pytest.skip("referee not built: sh validation/build_referees.sh")
    stream, cycles = STREAMS[name]
    assert compare(VARIANTS[variant], stream, cycles) is None
