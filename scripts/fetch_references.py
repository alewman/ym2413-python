#!/usr/bin/env python
"""Fetch the referees' and detectors' sources and the pinned documents.

    python scripts/fetch_references.py            # fetch what is missing
    python scripts/fetch_references.py --verify   # only check what is there

Into ``reference/`` (ignored). Nuked-OPLL is GPL-2.0: read and run as the judge
here, never copied into this repository. emu2413 (MIT) and ymfm (BSD-3-Clause)
are detectors. The documents are checked by SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "reference" / "src"

REPOS = [
    {
        "path": "Nuked-OPLL",
        "url": "https://github.com/nukeykt/Nuked-OPLL",
        "rev": "1269cf5a783b65583b50fa2464d08be75830aaa0",
        "why": "The YM2413 and its relatives from the VRC7's die: the judge. GPL-2.0.",
    },
    {
        "path": "emu2413",
        "url": "https://github.com/digital-sound-antiques/emu2413",
        "rev": "a1d5120903b75f93d3eb7690e34a29c0b4add903",
        "why": "Mitsutaka Okazaki's emulator, used by many players: a detector. MIT.",
    },
    {
        "path": "ymfm",
        "url": "https://github.com/aaronsgiles/ymfm",
        "rev": "81aec25ccbb98f4873a255f7551ac4dadac59b4a",
        "why": "Aaron Giles's OPL family, MAME's: a detector. BSD-3-Clause.",
    },
]

FILES = [
    {
        "path": "reference/docs/YM2413_199606.pdf",
        "url": "http://www.bitsavers.org/components/yamaha/YM2413_199606.pdf",
        "sha256": "909f1a85d48ae67b0f1d5e4f6dc504acaea1cd33d390335062dfec16e4a6db4a",
        "why": "Yamaha's YM2413 catalog (1996-06): pins, registers, the instrument table.",
    },
    {
        "path": "reference/docs/VRC7_audio.wiki",
        "url": "https://www.nesdev.org/w/index.php?title=VRC7_audio&action=raw",
        "sha256": "1e48625aa57d63e44b4b818e8e2305f9478d0ed99b4db176cf422d09e4b3f35f",
        "why": "NESdev wiki: the VRC7's sound, its instrument ROM dumped in debug mode.",
    },
    {
        "path": "reference/docs/VRC7.wiki",
        "url": "https://www.nesdev.org/w/index.php?title=VRC7&action=raw",
        "sha256": "458fb2f227682a08487111e1cd7fbaad365c1c68495b5b604998e0323f121e14",
        "why": "NESdev wiki: the VRC7 mapper.",
    },
]


#: SMS Power answers Python's default user agent with 403 Forbidden.
USER_AGENT = "Mozilla/5.0 (ym2413-python reference fetch)"


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def fetch_files(verify: bool) -> int:
    bad = 0
    for entry in FILES:
        path = ROOT / entry["path"]
        if sha256(path) == entry["sha256"]:
            print(f"{entry['path']}: ok")
            continue
        if verify:
            print(f"{entry['path']}: missing or wrong SHA-256")
            bad += 1
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(entry["url"], headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            print(f"{entry['path']}: fetched file has the wrong SHA-256; not saved")
            bad += 1
            continue
        path.write_bytes(data)
        print(f"{entry['path']}: fetched")
    return bad


def head(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip() or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--verify", action="store_true", help="check, do not fetch")
    args = parser.parse_args(argv)
    bad = 0
    for entry in REPOS:
        path = SRC / entry["path"]
        if head(path) == entry["rev"]:
            print(f"{entry['path']}: at {entry['rev'][:7]}")
            continue
        if args.verify:
            print(f"{entry['path']}: missing or not at {entry['rev'][:7]}")
            bad += 1
            continue
        path.mkdir(parents=True, exist_ok=True)
        git = ["git", "-C", str(path)]
        if not (path / ".git").exists():
            subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run(
            [*git, "fetch", "-q", "--depth", "1", entry["url"], entry["rev"]], check=True
        )
        subprocess.run([*git, "checkout", "-q", "--detach", "FETCH_HEAD"], check=True)
        if head(path) != entry["rev"]:
            print(f"{entry['path']}: fetched the wrong revision")
            bad += 1
            continue
        print(f"{entry['path']}: fetched {entry['rev'][:7]}")
    bad += fetch_files(args.verify)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
