"""The instrument ROMs and each part's data."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ym2413_python import DS1001, VARIANTS, YM2413, Instrument

WIKI = Path(__file__).resolve().parent.parent / "reference" / "docs" / "VRC7_audio.wiki"


def test_instruments_round_trip_through_their_register_bytes() -> None:
    for variant in VARIANTS.values():
        for instrument in variant.instruments:
            assert Instrument.from_bytes(instrument.to_bytes()) == instrument


def test_every_part_has_fifteen_instruments_and_six_rhythm_halves() -> None:
    assert all(len(v.instruments) == 21 for v in VARIANTS.values())


def test_the_vrc7_rom_is_the_debug_mode_dump() -> None:
    if not WIKI.exists():
        pytest.skip("VRC7_audio.wiki not fetched: python scripts/fetch_references.py")
    text = WIKI.read_text()
    table = text[text.index("== Internal patch set ==") : text.index("== Debug Mode ==")]
    rows = re.findall(r"^\s+([1-9A-F]) \| ((?:[0-9A-F]{2} ){7}[0-9A-F]{2})", table, re.M)
    assert len(rows) == 15
    for number, raw in rows:
        assert DS1001.instruments[int(number, 16) - 1].to_bytes() == bytes.fromhex(raw)


def test_the_vrc7_differs_only_in_its_melody_rom_and_the_snare_byte() -> None:
    # The dump's snare carrier byte 7 is $68 where the YM2413's is $48 (the wiki).
    assert DS1001.instruments[19].to_bytes()[7] == 0x68
    assert YM2413.instruments[19].to_bytes()[7] == 0x48
    assert DS1001.instruments[15:19] == YM2413.instruments[15:19]
    assert DS1001.instruments[20] == YM2413.instruments[20]
