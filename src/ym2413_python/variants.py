"""Instruments and the parts built around the OPLL engine.

An instrument is eight bytes in the layout of the custom instrument's registers
$00-$07 (Yamaha's catalog): per operator (modulator, carrier) AM, vibrato,
envelope type, KSR and MULTI; the modulator's KSL and TL; the carrier's KSL,
both half-sine bits and the feedback; attack and decay; sustain level and
release. Each part's ROM holds fifteen of them, then six half-instruments for
the rhythm slots (bass drum modulator, hi-hat, tom, bass drum carrier, snare,
top cymbal), each holding one operator's half.

The ROM contents are measurements of silicon: the VRC7's were dumped from a
real chip in its debug mode (VRC7_audio.wiki, siliconpr0n); the others are as
Nuked-OPLL has them (opll.c:114-212), checked against those dumps where both
exist (tests/test_variants.py).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Instrument:
    """One instrument; two-element tuples are (modulator, carrier)."""

    tl: int
    dc: int
    dm: int
    fb: int
    am: tuple[int, int]
    vib: tuple[int, int]
    et: tuple[int, int]
    ksr: tuple[int, int]
    multi: tuple[int, int]
    ksl: tuple[int, int]
    ar: tuple[int, int]
    dr: tuple[int, int]
    sl: tuple[int, int]
    rr: tuple[int, int]

    @classmethod
    def from_bytes(cls, raw: bytes) -> Instrument:
        """Decode the eight register bytes (the catalog's $00-$07)."""
        m, c = raw[0], raw[1]
        return cls(
            tl=raw[2] & 0x3F,
            dc=(raw[3] >> 4) & 1,
            dm=(raw[3] >> 3) & 1,
            fb=raw[3] & 7,
            am=(m >> 7, c >> 7),
            vib=((m >> 6) & 1, (c >> 6) & 1),
            et=((m >> 5) & 1, (c >> 5) & 1),
            ksr=((m >> 4) & 1, (c >> 4) & 1),
            multi=(m & 0x0F, c & 0x0F),
            ksl=(raw[2] >> 6, raw[3] >> 6),
            ar=(raw[4] >> 4, raw[5] >> 4),
            dr=(raw[4] & 0x0F, raw[5] & 0x0F),
            sl=(raw[6] >> 4, raw[7] >> 4),
            rr=(raw[6] & 0x0F, raw[7] & 0x0F),
        )

    def to_bytes(self) -> bytes:
        """The eight register bytes (bit 5 of byte 3 reads as 0)."""
        ops = [
            self.am[s] << 7 | self.vib[s] << 6 | self.et[s] << 5 | self.ksr[s] << 4 | self.multi[s]
            for s in (0, 1)
        ]
        return bytes(
            [
                *ops,
                self.ksl[0] << 6 | self.tl,
                self.ksl[1] << 6 | self.dc << 4 | self.dm << 3 | self.fb,
                self.ar[0] << 4 | self.dr[0],
                self.ar[1] << 4 | self.dr[1],
                self.sl[0] << 4 | self.rr[0],
                self.sl[1] << 4 | self.rr[1],
            ]
        )


def _rom(rows: str) -> tuple[Instrument, ...]:
    return tuple(Instrument.from_bytes(bytes.fromhex(row)) for row in rows.split("\n") if row)


#: The rhythm half-instruments shared by every part with a rhythm section.
_DRUMS = """\
01 00 18 0f df 00 6a 00
01 00 00 00 c8 00 a7 00
05 00 00 00 f8 00 59 00
00 01 00 00 00 f8 00 6d
00 01 00 00 00 d8 00 48
00 01 00 00 00 aa 00 55"""

YM2413_ROM = _rom(
    """\
71 61 1e 17 d0 78 00 17
13 41 1a 0d d8 f7 23 13
13 01 99 00 f2 c4 11 23
31 61 0e 07 a8 64 70 27
32 21 1e 06 e0 76 00 28
31 22 16 05 e0 71 00 18
21 61 1d 07 82 81 10 07
23 21 2d 14 a2 72 00 07
61 61 1b 06 64 65 10 17
41 61 0b 18 85 f7 71 07
13 01 83 11 fa e4 10 04
17 c1 24 07 f8 f8 22 12
61 50 0c 05 c2 f5 20 42
01 01 55 03 c9 95 03 02
61 41 89 03 f1 e4 40 13
"""
    + _DRUMS
)

#: The VRC7's: the debug-mode dump (VRC7_audio.wiki "Internal patch set"). Its snare
#: carrier's byte 7 is $68 where the YM2413's is $48; the VRC7 has no rhythm output.
DS1001_ROM = _rom(
    """\
03 21 05 06 e8 81 42 27
13 41 14 0d d8 f6 23 12
11 11 08 08 fa b2 20 12
31 61 0c 07 a8 64 61 27
32 21 1e 06 e1 76 01 28
02 01 06 00 a3 e2 f4 f4
21 61 1d 07 82 81 11 07
23 21 22 17 a2 72 01 17
35 11 25 00 40 73 72 01
b5 01 0f 0f a8 a5 51 02
17 c1 24 07 f8 f8 22 12
71 23 11 06 65 74 18 16
01 02 d3 05 c9 95 03 02
61 63 0c 00 94 c0 33 f6
21 72 0d 00 c1 d5 56 06
"""
    + _DRUMS.replace("00 d8 00 48", "00 d8 00 68")
)

YMF281_ROM = _rom(
    """\
62 21 1a 07 ff 67 00 16
20 10 45 01 f6 83 80 03
13 01 96 00 f2 d3 11 03
31 61 0b 0f a8 64 70 17
32 21 1e 06 e1 76 00 28
20 61 82 0e 9a 61 20 27
21 61 1b 07 84 83 10 07
37 32 ca 02 66 64 40 27
41 61 07 03 c5 77 51 07
36 01 5e 07 f2 f3 f0 f3
20 00 18 06 f5 e3 20 13
17 81 24 07 f8 f8 22 03
35 64 00 00 ff f3 70 f5
0f 31 03 07 fc e3 3f fc
2a 21 00 07 bf 84 00 f5
"""
    + _DRUMS
)

YM2423_ROM = _rom(
    """\
61 61 1b 07 94 54 10 05
b3 b1 52 04 f3 f2 a0 e9
61 21 11 85 f2 f2 50 75
b3 b2 28 07 f3 f2 90 b4
72 31 97 05 51 6f 70 09
33 30 18 06 f7 f4 50 85
71 31 1c 07 51 71 20 26
71 f4 1b 07 73 3f 00 06
70 30 4d 03 42 6f 20 06
60 20 10 85 f3 f3 20 04
61 61 1b 07 c5 96 f0 f6
f9 f1 db 00 f5 f3 70 f2
60 a2 91 03 94 b1 e0 f7
30 30 17 06 d3 e1 b0 eb
31 36 0d 05 f2 f4 20 99
"""
    + _DRUMS
)


@dataclass(frozen=True)
class OPLLVariant:
    """What differs between parts: data, not code.

    ``output_stage``: "nmos" (the YM2413's: a sign-magnitude DAC word, a muted
    slot driving its sign), "b" (the B parts': a muted slot drives 0) or "vrc7"
    (the DS1001's: one output, MO). ``rhythm_forced``: rhythm mode stuck on,
    which with no RO pin leaves six melody channels (the DS1001).
    """

    name: str
    instruments: tuple[Instrument, ...]
    output_stage: str = "nmos"
    rhythm_forced: bool = False
    nuked_type: int = 0  # Nuked-OPLL's chip type, for the referee

    @property
    def has_rhythm_output(self) -> bool:
        return self.output_stage != "vrc7"


YM2413 = OPLLVariant("YM2413", YM2413_ROM, nuked_type=0)
DS1001 = OPLLVariant("DS1001", DS1001_ROM, "vrc7", rhythm_forced=True, nuked_type=1)
YM2413B = OPLLVariant("YM2413B", YM2413_ROM, "b", nuked_type=2)
YMF281 = OPLLVariant("YMF281", YMF281_ROM, nuked_type=3)
YMF281B = OPLLVariant("YMF281B", YMF281_ROM, "b", nuked_type=4)
YM2423 = OPLLVariant("YM2423", YM2423_ROM, nuked_type=6)

VARIANTS = {v.name: v for v in (YM2413, DS1001, YM2413B, YMF281, YMF281B, YM2423)}
