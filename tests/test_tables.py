"""Rung 0: the ROMs the core generates from formulas, pinned by hash."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from ym2413_python import EXPONENT, LOG_SINE

NUKED = Path(__file__).resolve().parent.parent / "reference" / "src" / "Nuked-OPLL" / "opll.c"


def digest(table: tuple[int, ...]) -> str:
    return hashlib.sha256(b"".join(v.to_bytes(2, "little") for v in table)).hexdigest()


def test_log_sine_is_the_dies() -> None:
    # The same 256 words as the YM2612's (ym2612-python pins LOG_SIN to this hash).
    assert digest(LOG_SINE) == "a099b16dd3aa2f56cabc1fee590db31ee412ee361da4f0c67497092cf57c4776"


def test_exponent_is_the_dies() -> None:
    assert digest(EXPONENT) == "03ed28cf706e8dc04592257609777ddf0d30432e5a28f4b1e1d4c32ba5c9a1e6"


@pytest.mark.referee
def test_tables_equal_nuked_opll_word_for_word() -> None:
    if not NUKED.exists():
        pytest.skip("Nuked-OPLL not fetched: python scripts/fetch_references.py")
    source = NUKED.read_text()

    def table(name: str) -> tuple[int, ...]:
        body = source[source.index(name) :]
        body = body[body.index("{") + 1 : body.index("};")]
        return tuple(int(x, 16) for x in re.findall(r"0x[0-9a-f]+", body))

    assert table("logsinrom") == LOG_SINE
    assert table("exprom") == EXPONENT
