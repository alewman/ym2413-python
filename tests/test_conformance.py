"""The conformance kit: this core still writes every committed trace."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ym2413_python.conformance import FORMAT, check, run

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "conformance"


def test_this_chip_still_writes_every_reference_trace() -> None:
    assert check(EXAMPLES) == []


def test_a_manifest_of_another_version_is_refused() -> None:
    manifest = json.loads(next(EXAMPLES.glob("*.json")).read_text())
    manifest["version"] = 2
    with pytest.raises(ValueError):
        run(manifest)


def test_traces_carry_the_format_line_and_one_line_per_sample() -> None:
    manifest = json.loads((EXAMPLES / "timing-ym2413.json").read_text())
    lines = run(manifest).splitlines()
    assert lines[0] == FORMAT
    samples = sum(line.startswith("S ") for line in lines)
    assert samples == manifest["clocks"] // 72
