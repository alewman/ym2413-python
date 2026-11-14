#!/usr/bin/env python3
"""Fetch the references docs/phase0.md relies on into the git-ignored reference/.

Every fetched file is pinned twice: by the commit in its URL, and by the SHA-256
of its bytes. Nothing fetched here is committed or shipped.

    python scripts/fetch_references.py            fetch what is missing, then verify
    python scripts/fetch_references.py --verify   verify only: no network
    python scripts/fetch_references.py --local    also check the files cited in place
                                                  from sms-python and famicom-python

A file whose bytes do not match its pin is left where it is, reported, and the
script exits 1. Nothing is ever deleted or overwritten: move a bad file into
trash/ by hand and run again.

What is fetched, and under what terms (docs/phase0.md has the full table):

- emu2413, Mitsutaka Okazaki, MIT. Permissive source: may be read.
- ymfm, Aaron Giles, BSD-3-Clause. Permissive source: may be read.
- "Copyright-free OPLL(x) ROM patches", a wiki page by David Viens (plgDavid):
  instrument settings for the YM2413 and its relatives matched BY EAR (the page
  says they are not exact), CC BY-SA. A document; ymfm's tables come from it.

What is cited in place and only checked by --local (never copied here):

- Yamaha's YM2413 application manual and catalog sheet, and SMS Power's wiki
  snapshot, under sms-python's reference/.
- The NESdev wiki's VRC7 pages under famicom-python's reference/.
- The openMSX YM2413 reverse-engineering project (andete/ym2413), a clone under
  sms-python's reference/src/ym2413. It states no licence. Only its
  measurement write-ups and result data are pinned. Its .cc and .hh files are
  not to be opened (docs/phase0.md, "Sources found and not read").

The two boards are looked for beside this repository; SMS_PYTHON_DIR and
FAMICOM_PYTHON_DIR name other checkouts.

Nuked-OPLL (Nuke.YKT, GPL-2.0-or-later) IS fetched, for the closed-box rung
only, under docs/restart.md rule 8: validation/nuked_harness.c is compiled
against it and nothing else touches it. Only opll.h and LICENSE may be opened
(the repository has no README). opll.c is compiled and never opened, searched or
quoted, including when a comparison fails.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
# The two boards' checkouts, beside this repository unless the environment says otherwise.
SMS_PYTHON = Path(os.environ.get("SMS_PYTHON_DIR", ROOT.parent / "sms-python"))
FAMICOM_PYTHON = Path(os.environ.get("FAMICOM_PYTHON_DIR", ROOT.parent / "famicom-python"))
USER_AGENT = "reference-fetch"

EMU2413 = "https://raw.githubusercontent.com/digital-sound-antiques/emu2413/a1d5120903b75f93d3eb7690e34a29c0b4add903"
YMFM = "https://raw.githubusercontent.com/aaronsgiles/ymfm/81aec25ccbb98f4873a255f7551ac4dadac59b4a"
# A GitHub wiki: the raw host takes no commit in the path. Wiki HEAD when pinned:
# b8b2030f2ce9f220f66d490924ef26ab17269caa. The SHA-256 below is the real pin.
PATCHES = "https://raw.githubusercontent.com/wiki/plgDavid/misc"
NUKED_OPLL = (
    "https://raw.githubusercontent.com/nukeykt/Nuked-OPLL/1269cf5a783b65583b50fa2464d08be75830aaa0"
)

# The capture project cited in place is andete/ym2413 at commit
# 4893d1c09faa0450b5d3355f19b7682d72822501 (2020-05-01).


@dataclass(frozen=True)
class Pin:
    path: str  # under reference/
    url: str
    sha256: str


PINS: tuple[Pin, ...] = (
    # emu2413: MIT, Copyright (c) 2001-2019 Mitsutaka Okazaki (LICENSE and the
    # header of emu2413.c both read).
    Pin(
        "emu2413/LICENSE",
        f"{EMU2413}/LICENSE",
        "8fb093f26ed0d78c8ca033bbec7063ac5b34c5d2475e6bd121d03ccfaaf2355f",
    ),
    Pin(
        "emu2413/README.md",
        f"{EMU2413}/README.md",
        "79b34ffc2e0112659cfeb69eb6b623a3d726213a34479faf5bfe2d93f71c6903",
    ),
    Pin(
        "emu2413/emu2413.c",
        f"{EMU2413}/emu2413.c",
        "35d492c180320bd473ece0fddca771ef54d9b25884a094468560f865f540abe5",
    ),
    Pin(
        "emu2413/emu2413.h",
        f"{EMU2413}/emu2413.h",
        "24d132a37fbc28426d24db90954f723b477d37277aae03db77c7dac8c4a637e3",
    ),
    # ymfm: BSD-3-Clause, Copyright (c) 2021, Aaron Giles (LICENSE and each file's
    # header read). The OPL family files and the shared FM engine they use.
    Pin(
        "ymfm/LICENSE",
        f"{YMFM}/LICENSE",
        "2d2e9213c170a9866c616fa85b6da993a6724e10befc61f468ed9bfb84c4691c",
    ),
    Pin(
        "ymfm/README.md",
        f"{YMFM}/README.md",
        "85fa831f01bb266efe5384e56d0d1f921ca4275a4415ba0123c5226602a44a1a",
    ),
    Pin(
        "ymfm/src/ymfm_opl.h",
        f"{YMFM}/src/ymfm_opl.h",
        "b01d13720c61cf040d10a2e68ee3e002e4467b9c795978514d58be6245dcbda5",
    ),
    Pin(
        "ymfm/src/ymfm_opl.cpp",
        f"{YMFM}/src/ymfm_opl.cpp",
        "e745673678d0de9733488427397e794d42348bb000dd45f6665d6f063963d517",
    ),
    Pin(
        "ymfm/src/ymfm_fm.h",
        f"{YMFM}/src/ymfm_fm.h",
        "1b27bfb7fa4963d7c54cb06fd9bf659450362d8ed496c6af7d487b068cac45c9",
    ),
    Pin(
        "ymfm/src/ymfm_fm.ipp",
        f"{YMFM}/src/ymfm_fm.ipp",
        "4fb7fe59d4494a19e9f9c7888eb644a63d86e109fdefb27a8117bf6a5f6ab4b9",
    ),
    # David Viens, "Copyright-free OPLL(x) ROM patches" (GitHub wiki page).
    Pin(
        "opll-patches/Copyright-free-OPLL(x)-ROM-patches.md",
        f"{PATCHES}/Copyright-free-OPLL(x)-ROM-patches.md",
        "f49652c807c39e9ca221023d7357747d3ae5a6d45a491f226cf2cfe9fde63437",
    ),
    # Nuke.YKT, Nuked-OPLL, GPL-2.0-or-later: a closed-box detector (rule 8).
    # RUN ONLY. opll.c must not be opened; the harness uses opll.h alone.
    Pin(
        "nuked-opll/LICENSE",
        f"{NUKED_OPLL}/LICENSE",
        "8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643",
    ),
    Pin(
        "nuked-opll/opll.h",
        f"{NUKED_OPLL}/opll.h",
        "4af73da64dfcb6a19392104c8d37865da9c3a00382ba377617bc1fe1228e82de",
    ),
    Pin(
        "nuked-opll/opll.c",
        f"{NUKED_OPLL}/opll.c",
        "d486915d0238be9650250ac91b0bb4024bfc236acd1893359648e5088144fc45",
    ),
)

# Files cited in place. Checked by --local, never copied.
LOCAL: tuple[tuple[Path, str], ...] = (
    # Yamaha, YM2413 application manual (30 pages, image only)
    (
        Path(SMS_PYTHON, "reference/smspower/chipsym2413am.pdf"),
        "d5e4864a76ae538b80a910c56a32218919148adde1a7101aafdfd8eb63bcc656",
    ),
    # the same manual as 31 GIF pages
    (
        Path(SMS_PYTHON, "reference/smspower/ym2413am.zip"),
        "605654dda8c33b89ce35bef69d66ffc61ff235a081e687ffe1db330408fceaf6",
    ),
    # Yamaha, YM2413 catalog LSI-212413A2, 1996.6 (10 pages)
    (
        Path(SMS_PYTHON, "reference/smspower/ym2413pdf.zip"),
        "564e137e1ce2076cdd29c510c34df82ac69fa289edf15acb1dadce585287d4ca",
    ),
    # SMS Power wiki, YM2413
    (
        Path(SMS_PYTHON, "reference/smspower-wiki/YM2413.pmwiki"),
        "d66a48f206db44b56a51430a259f50f70b38734755ba5e36a6acf1540eef874d",
    ),
    # SMS Power wiki, audio control port
    (
        Path(SMS_PYTHON, "reference/smspower-wiki/AudioControlPort.pmwiki"),
        "01554535fab750624c15f1a0661363147268a3833bac1b416bbf1b4de3bcd2b1",
    ),
    # SMS Power forum, YM2413 TestRom thread
    (
        Path(SMS_PYTHON, "reference/smspower-forum/topic-20057.txt"),
        "5f4c70c932e5229d0e93565ef3b15c5f8607c017fd1aff7bb3b1f2255e109daf",
    ),
    # JoppyFurr, YM2413 TestRom 1.00
    (
        Path(SMS_PYTHON, "tests/test_roms/smspower/YM2413TestRom-SMS-1.00.zip"),
        "15b3f259cc96719219e5ebd539ce4fc757ad0979332623275cc954b085342d19",
    ),
    # NESdev wiki, VRC7 audio
    (
        Path(FAMICOM_PYTHON, "reference/nesdev-wiki/VRC7_audio.wiki"),
        "1e48625aa57d63e44b4b818e8e2305f9478d0ed99b4db176cf422d09e4b3f35f",
    ),
    # NESdev forum, VRC7 and 5B amplifier investigation
    (
        Path(FAMICOM_PYTHON, "reference/nesdev-forum/17745.html"),
        "f913c22f7e139761b76b40f3e484fa3255bed06d961534cc34f155d3ce3ead37",
    ),
    # Yamaha, YM2413B catalog LSI-212413B2, 1999.5 (10 pages)
    (
        Path(SMS_PYTHON, "reference/src/ym2413/doc/YM2413B(-F).pdf"),
        "c8a6a15a6c976358071e60be952505d77001118f9b677149a0ad904fe7458b90",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150209.txt"),
        "03c175d317cb85962da444afe9babffd1728d6fe4d0d3aee3fa9441c5e747ee6",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150305.txt"),
        "aa0263b80c5dba962014f8b6911cab3f47f84b4ef593ebe046024e4416e2a27d",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150311.txt"),
        "b28943372b34b295ab7b50558b134428b815e90934c25bf4e28ce87ea76912ca",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150316.txt"),
        "e0c348e1458f782a1fd4641cdc6797b8ea30effc2644f4e825f22d4143197a5d",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150320.txt"),
        "f63cd6565cc3bb1024baaeea9c070e5f55d71e9ae34ebe23c53ad26e0adc8e7f",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150327/attack-rates.txt"),
        "09fdcd714a0f487c4e79285a818c1851b65facc26c4e7862c49374acf6e47e22",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150409/tab.txt"),
        "24113f9cd423913d4819e7b32ca2c872b9b10c3b3da89ab6b797e3b3bca698ca",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20150409/predicted-sine.txt"),
        "4a51f9346022c90980ba83d9bad3a00cc002cf512b0a1fef015d98052de82d3d",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20151128/am.txt"),
        "4578fc0335c0ae80599dd29445e7bc50f29239d5e8ea9dca3e1cb633a5976256",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20151201.txt"),
        "6a202ee16596cfb8a1c67daa16dce4bff42f19447d942784786221d519ccd9fd",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20151203/mod-car.txt"),
        "e654af4414bc5d1f9beaaff30bbc1fc239ba0698a581a66cde1826e22fc4b6d9",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20151212/fb.txt"),
        "840791a10206fd91857662b1eb9e008ac415e559bd4eb88693b98807ac3c4c2c",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20151216/ksl.txt"),
        "559e668316c6a6ab6d56a4accdf598864234532964e1ee8166f38d99ab61f4c6",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20151224/sl-ksr.txt"),
        "90507d06eeb1b2a7f205bb3d43b2a552bf88779931c207220ae2396ef9581588",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20151231/envelope.txt"),
        "9a0840b2be45c3b96419d7f830fb7ca2db013b60c36ce55dae716a06887b9a86",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20160210/adsr-transitions.txt"),
        "1f90b721f259590344acb68f87aaf1133370a7a848d32c8edbfd1820b79e68c3",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20160716/small-signals.txt"),
        "6114bf7aeac15968ec61cbe3706536e09ce0f55d452a0ee523ef2b26b0d733c6",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20170126/attack.txt"),
        "141099a9f2e5f1853aff31708f0589e7f9c469a45612a2442060857d66eecf80",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/20170126/formula-f1-4.txt"),
        "1635c3f068a97414b9c6bfb50ee5aba3988d6d5b3e4d6fb70e5ee4fe0fed4570",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/lfsr/lfsr.txt"),
        "a4ca471829546c90609ceb94ff97e1865c1d08ee1feb94e84b9a36de723e3c2e",
    ),
    # capture project write-up
    (
        Path(SMS_PYTHON, "reference/src/ym2413/results/rhythm/rhythm.md"),
        "0a5d0a2458a7fae67acaaed46c91837633894edd4a7fc47e1b3f9aea80cb86b3",
    ),
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(pin: Pin) -> None:
    target = REFERENCE / pin.path
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(pin.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    got = hashlib.sha256(data).hexdigest()
    if got != pin.sha256:
        print(f"REFUSED  {pin.path}: fetched bytes are {got}, pin is {pin.sha256}")
        return
    target.write_bytes(data)
    print(f"fetched  {pin.path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true", help="verify only, no network")
    parser.add_argument("--local", action="store_true", help="also check files cited in place")
    args = parser.parse_args()

    bad = 0
    for pin in PINS:
        target = REFERENCE / pin.path
        if not target.exists() and not args.verify:
            try:
                fetch(pin)
            except OSError as error:
                print(f"FAILED   {pin.path}: {error}")
        if not target.exists():
            print(f"MISSING  {pin.path}")
            bad += 1
        elif digest(target) != pin.sha256:
            print(f"MISMATCH {pin.path}: {digest(target)}")
            bad += 1
        else:
            print(f"ok       {pin.path}")

    if args.local:
        for path, sha256 in LOCAL:
            if not path.exists():
                print(f"MISSING  {path}")
                bad += 1
            elif digest(path) != sha256:
                print(f"MISMATCH {path}: {digest(path)}")
                bad += 1
            else:
                print(f"ok       {path}")

    print("all pins verified" if not bad else f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
