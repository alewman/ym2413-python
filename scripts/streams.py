"""Synthetic register streams for the referee (scripts/referee.py), each exercising one thing.

Times are internal cycles (four input clocks). ``Writer`` spaces writes as
Yamaha's catalog asks (12 input clocks after an address, 84 after data: 3 and 21
cycles) unless a stream asks for less.
"""

from __future__ import annotations

import random

SAMPLE = 18  # cycles


class Writer:
    def __init__(self, start: int = 64) -> None:
        self.cycle = start
        self.events: list[tuple[int, int, int]] = []

    def reg(self, register: int, value: int, after_address: int = 3, after_data: int = 21) -> None:
        self.events.append((self.cycle, 0, register))
        self.cycle += after_address
        self.events.append((self.cycle, 1, value))
        self.cycle += after_data

    def wait(self, samples: int) -> None:
        self.cycle += samples * SAMPLE

    def note(
        self, channel: int, fnum: int, block: int, key: bool = True, sustain: bool = False
    ) -> None:
        self.reg(0x10 + channel, fnum & 0xFF)
        self.reg(0x20 + channel, sustain << 5 | key << 4 | block << 1 | fnum >> 8)

    def done(self, tail: int = 2000) -> tuple[list[tuple[int, int, int]], int]:
        return self.events, self.cycle + tail * SAMPLE


def silence() -> tuple[list, int]:
    return Writer().done(500)


def each_instrument() -> tuple[list, int]:
    w = Writer()
    for instrument in range(16):
        w.reg(0x30, instrument << 4 | 2)
        w.note(0, 0x1C1, 4)
        w.wait(1500)
        w.note(0, 0x1C1, 4, key=False)
        w.wait(800)
    return w.done()


def custom_instrument() -> tuple[list, int]:
    w = Writer()
    rng = random.Random(1)
    for _ in range(10):
        for register in range(8):
            w.reg(register, rng.randrange(256))
        w.reg(0x30, 0x00 | rng.randrange(16))
        w.note(1, rng.randrange(512), rng.randrange(8))
        w.wait(1200)
        w.note(1, 0x100, 3, key=False)
        w.wait(600)
    return w.done()


def feedback_and_half_sines() -> tuple[list, int]:
    w = Writer()
    for fb in range(8):
        for halves in range(4):
            w.reg(0x00, 0x21)
            w.reg(0x01, 0x21)
            w.reg(0x02, 0x10)
            w.reg(0x03, halves << 3 | fb)
            w.reg(0x04, 0xF0)
            w.reg(0x05, 0xF0)
            w.reg(0x06, 0x0F)
            w.reg(0x07, 0x0F)
            w.reg(0x30, 0x00)
            w.note(0, 0x120, 4)
            w.wait(300)
    return w.done()


def all_channels() -> tuple[list, int]:
    w = Writer()
    for ch in range(9):
        w.reg(0x30 + ch, (ch + 1) << 4 | ch)
        w.note(ch, 0x100 + 37 * ch, 3 + ch % 4, sustain=ch % 2 == 1)
    w.wait(3000)
    for ch in range(9):
        w.note(ch, 0x100 + 37 * ch, 3 + ch % 4, key=False, sustain=ch % 3 == 0)
    w.wait(2000)
    return w.done()


def rhythm() -> tuple[list, int]:
    w = Writer()
    for ch, (fnum, block) in zip((6, 7, 8), ((0x120, 2), (0x150, 2), (0x1C0, 2)), strict=True):
        w.note(ch, fnum, block, key=False)
    w.reg(0x36, 0x02)
    w.reg(0x37, 0x31)
    w.reg(0x38, 0x13)
    for pattern in (0x30, 0x28, 0x24, 0x22, 0x21, 0x3F, 0x35, 0x2A):
        w.reg(0x0E, pattern)
        w.wait(1200)
        w.reg(0x0E, 0x20)
        w.wait(300)
    w.note(0, 0x1C1, 4)
    w.reg(0x30, 0x51)
    w.reg(0x0E, 0x3F)
    w.wait(1500)
    w.reg(0x0E, 0x00)  # rhythm mode off again
    w.wait(800)
    return w.done()


def envelopes() -> tuple[list, int]:
    w = Writer()
    rng = random.Random(2)
    for i in range(24):
        ar, dr, sl, rr = rng.randrange(16), rng.randrange(16), rng.randrange(16), rng.randrange(16)
        et, ksr = i & 1, (i >> 1) & 1
        w.reg(0x00, 0x01)
        w.reg(0x01, et << 5 | ksr << 4 | 0x01)
        w.reg(0x02, (i % 4) << 6 | 0x20)
        w.reg(0x03, (i % 4) << 6)
        w.reg(0x04, 0xF0)
        w.reg(0x05, ar << 4 | dr)
        w.reg(0x06, 0x0F)
        w.reg(0x07, sl << 4 | rr)
        w.reg(0x30, 0x00)
        w.note(2, rng.randrange(512), rng.randrange(8), sustain=bool(i & 4))
        w.wait(rng.choice((200, 900, 2500)))
        w.note(2, 0x100, 4, key=False, sustain=bool(i & 8))
        w.wait(rng.choice((100, 600, 1800)))
    return w.done()


def vibrato_tremolo() -> tuple[list, int]:
    w = Writer()
    w.reg(0x00, 0xC1)
    w.reg(0x01, 0xC1)
    w.reg(0x02, 0x10)
    w.reg(0x03, 0x05)
    w.reg(0x04, 0xF0)
    w.reg(0x05, 0xF0)
    w.reg(0x06, 0x00)
    w.reg(0x07, 0x00)
    w.reg(0x30, 0x00)
    w.note(0, 0x1FF, 5)
    w.wait(20000)  # past a whole vibrato and tremolo cycle
    return w.done(500)


def test_register() -> tuple[list, int]:
    w = Writer()
    w.reg(0x30, 0x30)
    w.note(0, 0x150, 4)
    for value in (0x01, 0x02, 0x04, 0x08, 0x0F, 0x05, 0x0A, 0x00):
        w.reg(0x0F, value)
        w.wait(700)
    return w.done()


def fast_writes() -> tuple[list, int]:
    """Writes closer than the catalog allows: back to back, and data without a new address."""
    w = Writer()
    rng = random.Random(3)
    for _ in range(300):
        w.reg(
            rng.choice((0x10, 0x20, 0x30, 0x13, 0x26, 0x0E, 0x05)) + rng.randrange(3),
            rng.randrange(256),
            after_address=rng.randrange(1, 4),
            after_data=rng.randrange(1, 30),
        )
        if rng.random() < 0.2:
            w.events.append((w.cycle, 1, rng.randrange(256)))
            w.cycle += rng.randrange(1, 5)
    return w.done()


def random_soup(seed: int) -> tuple[list, int]:
    w = Writer()
    rng = random.Random(seed)
    registers = [*range(0x00, 0x08), 0x0E]
    registers += [*range(0x10, 0x19), *range(0x20, 0x29), *range(0x30, 0x39)]
    for _ in range(400):
        w.reg(rng.choice(registers), rng.randrange(256))
        if rng.random() < 0.1:
            w.wait(rng.randrange(400))
    return w.done()


def _custom(w: Writer, raw: list[int]) -> None:
    for register, value in enumerate(raw):
        w.reg(register, value)


def multiples() -> tuple[list, int]:
    """Every MULTI on the carrier, then on the modulator."""
    w = Writer()
    for operator in (1, 0):
        for multi in range(16):
            raw = [0x01, 0x01, 0x18, 0x07, 0xF2, 0xF2, 0x24, 0x24]
            raw[operator] = multi
            _custom(w, raw)
            w.reg(0x30, 0x00)
            w.note(3, 0x0B0, 3)
            w.wait(250)
            w.note(3, 0x0B0, 3, key=False)
            w.wait(60)
    return w.done(300)


def rates() -> tuple[list, int]:
    """Every attack, decay and release rate on the carrier, KSR off and on, two octaves."""
    w = Writer()
    for ksr in (0, 1):
        for block in (1, 6):
            for rate in range(16):
                carrier = [0xFF, rate << 4 | rate, 0x0F, 0x40 | rate]
                _custom(w, [0x01, ksr << 4 | 0x01, 0x3F, 0x07, *carrier])
                w.reg(0x30, 0x00)
                w.note(4, 0x155, block)
                w.wait(400)
                w.note(4, 0x155, block, key=False)
                w.wait(300)
    return w.done(300)


def key_scaling() -> tuple[list, int]:
    """Every KSL on both operators at every block and the F-number's top bits."""
    w = Writer()
    for ksl in range(4):
        _custom(w, [0x01, 0x01, ksl << 6 | 0x08, ksl << 6 | 0x02, 0xF0, 0xF0, 0x00, 0x00])
        w.reg(0x30, 0x00)
        for block in range(8):
            for top in range(0, 16, 3):
                w.note(5, top << 5 | 0x11, block)
                w.wait(40)
    return w.done(300)


def back_to_back() -> tuple[list, int]:
    """Two writes to one port on consecutive cycles: the second is not a new strobe."""
    w = Writer()
    w.reg(0x30, 0x40)
    w.note(0, 0x120, 4)
    for gap in (1, 1, 2, 1, 3):
        w.events.append((w.cycle, 0, 0x10))
        w.events.append((w.cycle + gap, 0, 0x30))
        w.cycle += gap + 3
        w.events.append((w.cycle, 1, 0x71))
        w.events.append((w.cycle + gap, 1, 0x15))
        w.cycle += gap + 40
        w.wait(200)
    # Address, address, data on consecutive cycles: a second address strobe, if it
    # counted, would latch the data byte as the address.
    for value in (0x21, 0x14):
        w.events += [(w.cycle, 0, 0x30), (w.cycle + 1, 0, 0x10), (w.cycle + 2, 1, value)]
        w.cycle += 60
        w.wait(200)
    return w.done(500)


def rhythm_toggles() -> tuple[list, int]:
    """Rhythm mode switched on and off with the data strobe on every cycle of a sample."""
    w = Writer()
    for ch in (6, 7, 8):
        w.note(ch, 0x150, 3, key=False)
    w.reg(0x36, 0x00)
    w.reg(0x37, 0x00)
    w.reg(0x38, 0x00)
    for offset in range(SAMPLE):
        w.cycle += (offset - w.cycle) % SAMPLE
        w.reg(0x0E, 0x3F, after_data=1)
        w.wait(40)
        w.cycle += (offset - w.cycle) % SAMPLE
        w.reg(0x0E, 0x00, after_data=1)
        w.wait(40)
    return w.done(300)


def slow_envelope() -> tuple[list, int]:
    """The slowest rates for six seconds: the envelope timer's high bits come into play."""
    w = Writer()
    _custom(w, [0x01, 0x21, 0x00, 0x07, 0x11, 0x13, 0x11, 0xF1])
    w.reg(0x30, 0x00)
    w.note(0, 0x100, 4)
    w.reg(0x31, 0x10)
    w.note(1, 0x080, 3)
    w.wait(49716 * 3)
    w.note(0, 0x100, 4, key=False)
    w.note(1, 0x080, 3, key=False)
    w.wait(49716 * 3)
    return w.done(100)


def timer_rollover() -> tuple[list, int]:
    """Twelve seconds with a release at rate group 11 kept going: past the envelope
    timer's 2^17 rollover, where the lowest set bit is the top one."""
    w = Writer()
    _custom(w, [0x01, 0x01, 0x3F, 0x07, 0xF0, 0xF0, 0x0B, 0x0B])
    w.reg(0x30, 0x00)
    while w.cycle < 12 * 49716 * SAMPLE:  # re-keyed before it reaches the floor
        w.note(0, 0x100, 4)
        w.wait(300)
        w.note(0, 0x100, 4, key=False)
        w.wait(100)
    return w.done(100)


def rhythm_key_races(seed: int = 4) -> tuple[list, int]:
    """Rhythm mode toggled while channels 6-8 key on, at random cycles, release instant:
    the cycle the rhythm enable takes effect against a key-on starting."""
    w = Writer()
    _custom(w, [0x01, 0x01, 0x00, 0x07, 0xFF, 0xFF, 0x0F, 0x0F])  # full feedback
    for ch in (6, 7, 8):
        w.reg(0x30 + ch, 0x00)
    rng = random.Random(seed)
    for _ in range(1500):
        ch = rng.choice((6, 7, 8))
        w.reg(0x20 + ch, 0x18, after_address=1, after_data=rng.randrange(1, 18))
        rhythm = rng.choice((0x20, 0x00, 0x3F))
        w.reg(0x0E, rhythm, after_address=1, after_data=rng.randrange(1, 18))
        w.wait(rng.randrange(2, 6))
        w.reg(0x20 + ch, 0x08, after_address=1, after_data=1)
        w.wait(rng.randrange(1, 4))
    return w.done(200)


STREAMS = {
    "silence": silence(),
    "each_instrument": each_instrument(),
    "custom_instrument": custom_instrument(),
    "feedback_and_half_sines": feedback_and_half_sines(),
    "all_channels": all_channels(),
    "rhythm": rhythm(),
    "envelopes": envelopes(),
    "vibrato_tremolo": vibrato_tremolo(),
    "test_register": test_register(),
    "fast_writes": fast_writes(),
    "multiples": multiples(),
    "rates": rates(),
    "key_scaling": key_scaling(),
    "back_to_back": back_to_back(),
    "rhythm_toggles": rhythm_toggles(),
    "slow_envelope": slow_envelope(),
    "timer_rollover": timer_rollover(),
    "rhythm_key_races": rhythm_key_races(),
    "random_1": random_soup(11),
    "random_2": random_soup(12),
}
