"""The YM2413 (OPLL) and its relatives, one internal cycle at a time.

The chip has one operator unit and runs it 18 times a sample, once per operator
slot (nine channels, a modulator and a carrier each), with every stage of the
unit a cycle or more behind the one before: while one slot's sine is being
looked up, the next slot's phase is being added and the slot after that's
envelope worked out. This core keeps that shape, stage by stage, because the
outputs a host can see are the digital words the multiplexed DAC is driven with
each cycle, and those depend on which slot is in which stage when.

Sources: Yamaha's YM2413 catalog (1996) for the programmer's model; the
behaviour of every stage as Nuked-OPLL (reference/src/Nuked-OPLL/opll.c,
GPL-2.0, from the VRC7's die) establishes it, cited below by line and judged
against cycle by cycle (docs/phase0.md); the instrument ROMs as dumped
(``variants.py``). Every register below is a fixed-width hardware word: each
update is masked to its width.
"""

from __future__ import annotations

import math

from .variants import YM2413, Instrument, OPLLVariant

CLOCKS_PER_CYCLE = 4
CYCLES_PER_SAMPLE = 18

# Envelope states (opll.c:26).
ATTACK, DECAY, SUSTAIN, RELEASE = 0, 1, 2, 3

# The rhythm slots, in the order the sequencer visits them (opll.c:33); NONE: a melody slot.
BD0, HH, TOM, BD1, SD, TC, NONE = range(7)


def _log_sine() -> tuple[int, ...]:
    """The quarter sine as -log2, 8.8 fixed point: the die's 256-word ROM (opll.c:43)."""
    return tuple(round(-math.log2(math.sin((i + 0.5) * math.pi / 512)) * 256) for i in range(256))


def _exponent() -> tuple[int, ...]:
    """2^(fraction) as 1.10 fixed point, high to low: the die's ROM (opll.c:79)."""
    return tuple(round(2 ** ((255 - i) / 256) * 1024) for i in range(256))


LOG_SINE = _log_sine()
EXPONENT = _exponent()

#: Which channel the register-reading stage serves on each cycle (opll.c:214).
CHANNEL_OF_CYCLE = (1, 2, 0, 1, 2, 3, 4, 5, 3, 4, 5, 6, 7, 8, 6, 7, 8, 0)
#: MULTI's 4 bits as twice the frequency multiple (opll.c:218).
MULTIPLE = (1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 20, 24, 24, 30, 30)
#: The fast rates' extra steps by the low two rate bits and the timer's low bits (opll.c:222).
STEP_HIGH = ((0, 0, 0, 0), (1, 0, 0, 0), (1, 0, 1, 0), (1, 1, 1, 0))
#: Key scaling: attenuation by the top four F-number bits, before the block (opll.c:229).
KSL_TABLE = (0, 32, 40, 45, 48, 51, 53, 55, 56, 58, 59, 60, 61, 62, 63, 64)


def _modulator_select(cycle: int) -> int:
    """1 when the register-reading stage is on a carrier slot."""
    return ((cycle + 1) // 3) & 1


class OPLL:
    """One chip. ``write`` the address or data port, ``run`` input clocks, collect outputs."""

    def __init__(self, variant: OPLLVariant = YM2413) -> None:
        self.variant = variant
        self.reset()

    # -- power and the port ----------------------------------------------

    def reset(self) -> None:
        """/IC: every register cleared, every slot in release at full attenuation (opll.c:293)."""
        v = self.variant
        self.clock = 0  # input clocks run
        self._phase = 0  # input clocks into the current internal cycle
        self._outputs: list[tuple[int, int]] = []
        self.cycle = 0
        # The bus: the last byte, and each port's write strobe as a two-bit history.
        self.bus = 0
        self._strobe_address = 0
        self._strobe_data = 0
        self._address_edge = False
        self._data_edge = False
        self._fm_address = False  # the latched address names a channel register
        self._fm_data = False  # a channel register is waiting for its slot
        self._mode_address = 0  # $10 | register for $00-$0F, else 0
        self.address = 0
        self.data = 0
        # The channel registers and the instrument registers.
        self.fnum = [0] * 9
        self.block = [0] * 9
        self.key = [0] * 9
        self.sustain = [0] * 9
        self.volume = [0] * 9
        self.instrument = [0] * 9
        self.rhythm = 0x20 if v.rhythm_forced else 0
        self.test = 0
        self.custom = Instrument.from_bytes(bytes(8))
        # Envelope generator.
        self.eg_counter = 0
        self.eg_counter_prev = 0
        self.eg_timer = 0
        self.eg_timer_low_lock = 0
        self.eg_timer_carry = 0
        self.eg_timer_shift = 0
        self.eg_timer_shift_lock = 0
        self.eg_timer_shift_stop = 0
        self.eg_state = [RELEASE] * 18
        self.eg_level = [0x7F] * 18
        self.eg_key = 0  # key-on history, a shift register
        self.eg_start = 0  # "start the attack" history, a 32-bit shift register
        self.eg_off = 0  # "level at the floor" history
        self.eg_rate = 0
        self.eg_max_rate = 0
        self.eg_zero_rate = 0
        self.eg_inc_low = 0
        self.eg_inc_high = 0
        self.eg_rate_high = 0
        self.eg_sl = 0
        self.eg_ksl_tl = 0
        self.eg_out = 0x7F
        self.eg_silent = 0
        # Phase generator.
        self.pg_out = 0
        self.pg_inc = 0
        self.pg_phase = [0] * 18
        self.pg_phase_next = 0
        # Operator.
        self.fb_last = [0] * 9  # the modulator's last two outputs, per channel
        self.fb_before = [0] * 9
        self.fb_sum = 0
        self.op_mod = 0
        self.op_negative = 0  # sign history, a shift register
        self.op_log = 0
        self.op_mantissa = 0
        self.op_shift = 0
        # Channel outputs.
        self.ch_out = 0
        self.ch_hh = self.ch_tom = self.ch_bd = self.ch_sd = self.ch_tc = 0
        # LFO.
        self.lfo_counter = 0
        self.lfo_vib = 0
        self.lfo_am_counter = 0
        self.lfo_am_step = 0
        self.lfo_am_dir = 0
        self.lfo_am_carry = 0
        self.lfo_am_out = 0
        # The register-reading stage's values for the slot it serves.
        self.r_tl = 0
        self.r_dc = 0  # carrier half-sine history (shift register)
        self.r_dm = 0  # modulator half-sine history
        self.r_fb = 0
        self.r_am = 0
        self.r_vib = 0
        self.r_et = 0
        self.r_ksr = 0
        self.r_ksr_freq = 0
        self.r_ksl_freq = 0
        self.r_ksl_block = 0
        self.r_multi = 0
        self.r_ksl = 0
        self.r_rates = [0, 0, 0]  # attack, decay, release
        self.r_sl = 0
        self.r_fnum = 0
        self.r_block = 0
        # Rhythm.
        self.rhythm_on = 0x80 if v.rhythm_forced else 0  # bit 7 now, bit 6 a cycle ago
        self.noise = 0
        self.rhythm_slot = NONE
        self.hh_bit2 = self.hh_bit3 = self.hh_bit7 = self.hh_bit8 = 0
        self.tc_bit3 = self.tc_bit5 = 0
        self.out_m = 0
        self.out_r = 0

    def write(self, port: int, value: int) -> None:
        """A write to the address port (``port`` even, A0 low) or the data port.

        The byte is on the bus at once; the strobe is seen on the next internal
        cycle, as /WE's rising edge (opll.c:1101).
        """
        self.bus = value & 0xFF
        if port & 1:
            self._strobe_data |= 1
        else:
            self._strobe_address |= 1

    def run(self, clocks: int) -> None:
        """Advance ``clocks`` input clocks: an internal cycle at every fourth."""
        phase = self._phase + clocks
        self.clock += clocks
        for _ in range(phase // CLOCKS_PER_CYCLE):
            self._cycle()
        self._phase = phase % CLOCKS_PER_CYCLE

    def take_outputs(self) -> list[tuple[int, int]]:
        """The (MO, RO) words driven since the last call, one pair per internal cycle."""
        outputs, self._outputs = self._outputs, []
        return outputs

    def take_samples(self) -> list[tuple[int, int]]:
        """The same, summed per pin over each whole sample's 18 cycles: the level a
        board's analogue filter integrates. Cycles of an unfinished sample wait."""
        count = len(self._outputs) - len(self._outputs) % CYCLES_PER_SAMPLE
        outputs, self._outputs = self._outputs[:count], self._outputs[count:]
        return [
            (
                sum(mo for mo, _ in outputs[i : i + CYCLES_PER_SAMPLE]),
                sum(ro for _, ro in outputs[i : i + CYCLES_PER_SAMPLE]),
            )
            for i in range(0, count, CYCLES_PER_SAMPLE)
        ]

    # -- one internal cycle (the order of opll.c:1062) -----------------------

    def _cycle(self) -> None:
        self._outputs.append((self.out_m, self.out_r))
        if self.cycle == 0:
            self.lfo_am_out = (self.lfo_am_counter >> 3) & 0x0F
        # The rhythm-enable history shifts with its top bit held (a signed byte).
        self.rhythm_on = (self.rhythm_on >> 1) | (self.rhythm_on & 0x80)
        self._mode_write()
        self.rhythm_slot = min(self.rhythm_slot + 1, NONE)
        if self.cycle == 11 and self.rhythm_on & 0x80:
            self.rhythm_slot = BD0
        self._read_registers_first()
        self._channel_output()
        self._phase_generate()
        self._operator()
        self._phase_increment()
        self._envelope_output()
        self._envelope_ksl_tl()
        self._envelope_generate()
        self._lfo()
        self._noise()
        self._read_registers_second()
        self._register_write()
        self._sample_strobes()
        self.cycle = (self.cycle + 1) % CYCLES_PER_SAMPLE

    # -- the port's registers -------------------------------------------------

    def _sample_strobes(self) -> None:
        """A strobe counts once, on the cycle after it rose (opll.c:233)."""
        self._address_edge = (self._strobe_address & 3) == 1
        self._data_edge = (self._strobe_data & 3) == 1
        self._strobe_address = (self._strobe_address << 1) & 0xFF
        self._strobe_data = (self._strobe_data << 1) & 0xFF

    def _mode_write(self) -> None:
        """$00-$0F: the custom instrument, rhythm and test, written at once (opll.c:241)."""
        mode = self._mode_address
        if not (mode & 0x10 and self._data_edge):
            return
        register, value = mode & 0x0F, self.bus
        if register < 8:
            raw = bytearray(self.custom.to_bytes())
            raw[register] = value
            self.custom = Instrument.from_bytes(bytes(raw))
        elif register == 0x0E:
            self.rhythm = value & 0x3F
            if self.variant.rhythm_forced:
                self.rhythm |= 0x20
            self.rhythm_on = (self.rhythm_on & 0x7F) | ((self.rhythm << 2) & 0x80)
        elif register == 0x0F:
            self.test = value & 0x0F

    def _register_write(self) -> None:
        """$10-$38: latched, then written when the sequencer reaches the channel (opll.c:328)."""
        if self._address_edge:
            self._fm_address = (self.bus & 0xC0) == 0
            if self._fm_address:
                self.address = self.bus
        if self._fm_address and self._data_edge:
            self.data = self.bus
        cycle = self.cycle
        if self._fm_data and not self._address_edge and (self.address & 0x0F) == cycle < 16:
            channel = cycle % 9
            data, group = self.data, self.address & 0xF0
            if group == 0x10:
                self.fnum[channel] = (self.fnum[channel] & 0x100) | data
            elif group == 0x20:
                self.fnum[channel] = (self.fnum[channel] & 0xFF) | (data & 1) << 8
                self.block[channel] = (data >> 1) & 7
                self.key[channel] = (data >> 4) & 1
                self.sustain[channel] = (data >> 5) & 1
            elif group == 0x30:
                self.volume[channel] = data & 0x0F
                self.instrument[channel] = data >> 4
        if self._address_edge:
            self._fm_data = False
        if self._fm_address and self._data_edge:
            self._fm_data = True
        if self._address_edge:
            self._mode_address = 0x10 | (self.bus & 0x0F) if (self.bus & 0xF0) == 0 else 0

    # -- the register-reading stage (opll.c:394, :431) -----------------------------

    def _patch(self, channel: int) -> Instrument:
        """What a slot reads: a rhythm slot's drum, a ROM instrument, or the custom one."""
        if self.rhythm_slot < NONE:
            return self.variant.instruments[15 + self.rhythm_slot]
        number = self.instrument[channel]
        return self.variant.instruments[number - 1] if number else self.custom

    def _read_registers_first(self) -> None:
        cycle = self.cycle
        carrier = _modulator_select(cycle)
        channel = CHANNEL_OF_CYCLE[cycle]
        patch = self._patch(channel)
        if self.rhythm_slot in (HH, TOM):
            # The hi-hat's and tom's slots take their "volume" from the instrument register.
            self.r_tl = self.instrument[channel] << 2
        elif carrier:
            self.r_tl = self.volume[channel] << 2
        else:
            self.r_tl = patch.tl
        self.r_rates = [patch.ar[carrier], patch.dr[carrier], patch.rr[carrier]]
        self.r_et = patch.et[carrier]
        self.r_ksr = patch.ksr[carrier]
        self.r_ksl = patch.ksl[carrier]
        self.r_ksr_freq = (self.block[channel] << 1) | (self.fnum[channel] >> 8)
        self.r_ksl_freq = self.fnum[channel] >> 5
        self.r_ksl_block = self.block[channel]

    def _read_registers_second(self) -> None:
        cycle = self.cycle
        carrier = _modulator_select(cycle)
        channel = CHANNEL_OF_CYCLE[cycle]
        patch = self._patch(channel)
        self.r_fnum = self.fnum[channel]
        self.r_block = self.block[channel]
        self.r_multi = patch.multi[carrier]
        self.r_sl = patch.sl[carrier]
        self.r_fb = patch.fb
        self.r_vib = patch.vib[carrier]
        self.r_am = patch.am[carrier]
        self.r_dc = ((self.r_dc << 1) | patch.dc) & 0xFF
        self.r_dm = ((self.r_dm << 1) | patch.dm) & 0xFF

    # -- phase (opll.c:463, :529) ---------------------------------------------------

    def _phase_generate(self) -> None:
        cycle = self.cycle
        self.pg_phase[(cycle + 17) % 18] = (self.pg_phase_next + self.pg_inc) & 0xFFFFFFFF
        if self.rhythm_on & 0x40 and cycle in (13, 14):
            modulator = 0
        else:
            modulator = ((cycle + 3) // 3) & 1
        phase = self.pg_phase[cycle]
        starting = self.eg_start & 0x8000 if modulator else self.eg_start & 0x01
        if self.test & 0x04 or starting:
            self.pg_phase_next = 0
        else:
            self.pg_phase_next = phase
        if cycle == 13:
            self.hh_bit2 = (phase >> 11) & 1
            self.hh_bit3 = (phase >> 12) & 1
            self.hh_bit7 = (phase >> 16) & 1
            self.hh_bit8 = (phase >> 17) & 1
        elif cycle == 17 and self.rhythm_on & 0x80:
            self.tc_bit3 = (phase >> 12) & 1
            self.tc_bit5 = (phase >> 14) & 1
        out = (phase >> 9) & 0xFFFF
        if self.rhythm_on & 0x80:
            if cycle in (13, 17):
                ring = (
                    (self.hh_bit2 ^ self.hh_bit7)
                    | (self.hh_bit3 ^ self.tc_bit5)
                    | (self.tc_bit3 ^ self.tc_bit5)
                )
                if cycle == 13:  # hi-hat: the ring bit, then a noise-chosen offset
                    out = ring << 9 | (0xD0 if ring ^ (self.noise & 1) else 0x34)
                else:  # top cymbal
                    out = ring << 9 | 0x100
            elif cycle == 16:  # snare: the hi-hat's bit 8 against the noise
                out = self.hh_bit8 << 9 | (self.hh_bit8 ^ (self.noise & 1)) << 8
        self.pg_out = out

    def _phase_increment(self) -> None:
        freq = self.r_fnum << 1
        if self.r_vib:
            vib = self.lfo_vib
            if vib in (1, 3):
                freq += freq >> 8
            elif vib == 2:
                freq += freq >> 7
            elif vib in (5, 7):
                freq -= freq >> 8
            elif vib == 6:
                freq -= freq >> 7
        freq = (freq << self.r_block) >> 1
        self.pg_inc = ((freq * MULTIPLE[self.r_multi]) >> 1) & 0xFFFFFFFF

    # -- envelope (opll.c:562, :581, :601) ------------------------------------------------

    def _envelope_ksl_tl(self) -> None:
        ksl = max(KSL_TABLE[self.r_ksl_freq] - ((8 - self.r_ksl_block) << 3), 0) << 1
        ksl = ksl >> (3 - self.r_ksl) if self.r_ksl else 0
        self.eg_ksl_tl = ksl + (self.r_tl << 1)

    def _envelope_output(self) -> None:
        level = self.eg_level[(self.cycle + 17) % 18] + self.eg_ksl_tl
        if self.r_am:
            level += self.lfo_am_out
        level = min(level, 127)
        if self.test & 0x01:
            level = 0
        self.eg_out = level

    def _fast_step(self) -> int:
        """Decay and release's level step for this slot's rate and the timer (0, 1, 2 or 3)."""
        high, inc_high, prev = self.eg_rate_high, self.eg_inc_high, self.eg_counter_prev
        double = high == 15 or (high == 14 and inc_high)
        single = (
            (high == 14 and not inc_high)
            or (high == 13 and inc_high)
            or (high == 13 and not inc_high and prev & 1)
            or (high == 12 and inc_high and prev & 1)
            or (high == 12 and not inc_high and (prev & 3) == 3)
            or (self.eg_inc_low and (prev & 3) == 3)
        )
        return (double << 1) | bool(single)

    def _envelope_generate(self) -> None:
        cycle = self.cycle
        carrier = _modulator_select(cycle)

        # The envelope timer: an 18-bit counter kept as a serial shift register.
        if (self.eg_counter & 3) != 3:
            increment = 0
        elif cycle == 0:
            increment = 1
        else:
            increment = self.eg_timer_carry
        timer_low = self.eg_timer & 3
        bit = (self.eg_timer & 1) + increment
        self.eg_timer_carry = bit >> 1
        self.eg_timer = ((bit & 1) << 17) | (self.eg_timer >> 1)
        if self.test & 0x08:
            self.eg_timer = (self.eg_timer & 0x2FFFF) | ((self.bus << 14) & 0x10000)
        if not self.eg_timer_shift_stop and (self.eg_timer >> 16) & 1:
            self.eg_timer_shift = cycle
        if cycle == 0 and self.eg_counter_prev & 1:
            self.eg_timer_low_lock = timer_low
            self.eg_timer_shift_lock = self.eg_timer_shift if self.eg_timer_shift <= 13 else 0
            self.eg_timer_shift = 0
        self.eg_timer_shift_stop |= (self.eg_timer >> 16) & 1
        if cycle == 0:
            self.eg_timer_shift_stop = 0
        self.eg_counter_prev = self.eg_counter
        if cycle == 17:
            self.eg_counter = (self.eg_counter + 1) & 0xFF

        # The slot two cycles back: its level and state step.
        slot = (cycle + 16) % 18
        level = self.eg_level[slot]
        next_level = level
        zero = level == 0
        self.eg_silent = int(level == 0x7F)
        state = self.eg_state[slot]
        starting = self.eg_start & 2
        if state != ATTACK and self.eg_off & 2 and not starting:
            next_level = 0x7F
        if self.eg_max_rate and starting:
            next_level = 0
        step = 0
        next_state = ATTACK
        if state == ATTACK:
            if not self.eg_max_rate and self.eg_key & 2 and not zero:
                high = self.eg_rate_high
                shift = self.eg_inc_low if high < 12 else high - 11 + self.eg_inc_high
                if shift > 0:
                    step = (~level) >> (5 - shift)
            next_state = DECAY if zero else ATTACK
        elif state == DECAY:
            if not self.eg_off & 2 and not starting and (level >> 3) != self.eg_sl:
                step = self._fast_step()
            next_state = SUSTAIN if (level >> 3) == self.eg_sl else DECAY
        else:
            if not self.eg_off & 2 and not starting:
                step = self._fast_step()
            next_state = state
        if not self.eg_key & 2:
            next_state = RELEASE
        if starting:
            next_state = ATTACK
        self.eg_level[slot] = (next_level + step) & 0xFF
        self.eg_state[slot] = next_state

        # This cycle's slot: its rate, from the state it is in.
        rate_high, rate_low = self.eg_rate >> 2, self.eg_rate & 3
        self.eg_inc_high = STEP_HIGH[rate_low][self.eg_timer_low_lock]
        total = (self.eg_timer_shift_lock + rate_high) & 0x0F
        self.eg_inc_low = 0
        if rate_high < 12 and not self.eg_zero_rate:
            if total == 12:
                self.eg_inc_low = 1
            elif total == 13:
                self.eg_inc_low = (rate_low >> 1) & 1
            elif total == 14:
                self.eg_inc_low = rate_low & 1
        self.eg_max_rate = int(rate_high == 15)
        self.eg_rate_high = rate_high

        channel = CHANNEL_OF_CYCLE[cycle]
        self.eg_key = ((self.eg_key << 1) | self.key[channel]) & 0xFF
        self.eg_off = ((self.eg_off << 1) | ((self.eg_level[cycle] >> 2) == 0x1F)) & 0xFF
        rhythm_key = {BD0: 4, BD1: 4, SD: 3, TOM: 2, TC: 1, HH: 0}.get(self.rhythm_slot)
        if rhythm_key is not None:
            self.eg_key |= (self.rhythm >> rhythm_key) & 1

        rate = 0
        self.eg_start = (self.eg_start << 1) & 0xFFFFFFFF
        state = self.eg_state[cycle]
        if state == RELEASE and self.eg_key & 1 and self.eg_off & 1:
            state = ATTACK
            self.eg_start |= 1
        if state == ATTACK:
            rate = self.r_rates[0]
        elif state == DECAY:
            rate = self.r_rates[1]
        elif state == SUSTAIN:
            if not self.r_et:
                rate = self.r_rates[2]
        elif self.sustain[channel]:
            rate = 5
        else:
            rate = self.r_rates[2]
        if not self.eg_key & 1 and not carrier and self.rhythm_slot not in (TOM, HH):
            rate = 0
        if self.eg_key & 1 and self.eg_state[cycle] == RELEASE and not self.eg_off & 1:
            rate = 12
        if not self.eg_key & 1 and not self.sustain[channel] and carrier and not self.r_et:
            rate = 7
        self.eg_zero_rate = int(rate == 0)
        ksr = self.r_ksr_freq if self.r_ksr else self.r_ksr_freq >> 2
        self.eg_rate = (rate << 2) + ksr
        if self.eg_rate & 0x40:
            self.eg_rate = 0x3C | (ksr & 3)
        self.eg_sl = self.r_sl

    # -- the operator and the channel (opll.c:888, :828) ---------------------------

    def _operator(self) -> None:
        cycle = self.cycle
        rhythm, rhythm_late = self.rhythm_on & 0x80, self.rhythm_on & 0x40
        # Which stage of the pipeline is on a modulator slot this cycle, per stage.
        mod_out = 0 if rhythm and cycle in (15, 16) else ((cycle + 1) // 3) & 1
        mod_fb = 0 if rhythm_late and cycle in (13, 14) else ((cycle + 3) // 3) & 1
        mod_in = 0 if rhythm_late and cycle in (16, 17) else (cycle // 3) & 1

        modulation = self.op_mod << 1 if mod_in else 0
        if mod_fb and self.r_fb:
            modulation |= self.fb_sum >> (7 - self.r_fb)

        # The exponent stage: the level looked up last cycle, back to linear.
        shift = self.op_shift
        half_sine = self.r_dm & 4 if mod_out else self.r_dc & 4
        if self.eg_silent or (self.op_negative & 2 and half_sine):
            shift |= 12
        output = self.op_mantissa >> shift
        if not self.eg_silent and self.op_negative & 2:
            output = ~output

        level = min(self.op_log + (self.eg_out << 4), 4095)
        self.op_mantissa = EXPONENT[level & 0xFF]
        self.op_shift = level >> 8

        # The sine stage: this slot's phase, with its modulation, to a log level.
        phase = (modulation + self.pg_out) & 0x3FF
        if phase & 0x100:
            phase ^= 0xFF
        self.op_log = LOG_SINE[phase & 0xFF]
        self.op_negative = ((self.op_negative << 1) | (phase >> 9)) & 0xFF
        index = (cycle + 3) % 9
        self.fb_sum = (self.fb_last[index] + self.fb_before[index]) >> 1

        if mod_out:
            self.fb_before[cycle % 9] = self.fb_last[cycle % 9]
            self.fb_last[cycle % 9] = output
        self.op_mod = output & 0x1FF

        rhythm_output = 0
        if self.variant.has_rhythm_output:
            rhythm_output = {2: self.ch_hh, 3: self.ch_tom, 4: self.ch_bd, 8: self.ch_sd,
                             9: self.ch_tc}.get(cycle, 0)  # fmt: skip
            if cycle == 15:
                self.ch_hh = output >> 3
            elif cycle == 16:
                self.ch_tom = output >> 3
            elif cycle == 17:
                self.ch_bd = output >> 3
            elif cycle == 0:
                self.ch_sd = output >> 3
            elif cycle == 1:
                self.ch_tc = output >> 3
        if not rhythm:
            rhythm_output = 0
        self.ch_out = rhythm_output if mod_out else output >> 3

    def _channel_output(self) -> None:
        cycle = self.cycle
        value = self.ch_out
        muted = bool((cycle // 3) & 1) or (bool(self.rhythm_on & 0x40) and (cycle + 15) % 18 >= 12)
        stage = self.variant.output_stage
        if stage == "vrc7":
            out = value + 1 if value >= 0 else value
            self.out_m = 0 if muted else out
            self.out_r = 0
            return
        rhythm_muted = not (self.rhythm_on & 0x40 and cycle in (16, 17, 0, 1, 2, 3, 4, 5, 9, 10))
        if stage == "b":
            self.out_m = 0 if muted else value
            self.out_r = 0 if rhythm_muted else value
            return
        sign = value >> 8
        if value >= 0:
            value += 1
            sign += 1
        self.out_m = sign if muted else value
        self.out_r = sign if rhythm_muted else value

    # -- LFO and noise (opll.c:1014, :1005) -------------------------------------------

    def _lfo(self) -> None:
        cycle = self.cycle
        if cycle == 17:
            vib_step = ((self.lfo_counter & 0x3FF) + 1) >> 10
            self.lfo_am_step = ((self.lfo_counter & 0x3F) + 1) >> 6
            vib_step |= (self.test >> 3) & 1
            self.lfo_vib = (self.lfo_vib + vib_step) & 7
            self.lfo_counter = (self.lfo_counter + 1) & 0xFFFF
        increment = 0
        if (self.lfo_am_step or self.test & 0x08) and cycle < 9:
            increment = self.lfo_am_dir | (cycle == 0)
        if cycle >= 9:
            self.lfo_am_carry = 0
        if cycle == 0:
            if self.lfo_am_dir and (self.lfo_am_counter & 0x7F) == 0:
                self.lfo_am_dir = 0
            elif not self.lfo_am_dir and (self.lfo_am_counter & 0x69) == 0x69:
                self.lfo_am_dir = 1
        bit = (self.lfo_am_counter & 1) + increment + self.lfo_am_carry
        self.lfo_am_carry = bit >> 1
        self.lfo_am_counter = ((bit & 1) << 8) | (self.lfo_am_counter >> 1)
        if self.test & 0x02:
            self.lfo_vib = 0
            self.lfo_counter = 0
            self.lfo_am_dir = 0
            self.lfo_am_counter &= 0xFF

    def _noise(self) -> None:
        """A 23-bit LFSR, taps 0 and 14, kicked when it is all zeros (opll.c:1005)."""
        noise = self.noise
        bit = (noise ^ (noise >> 14)) & 1
        bit |= int(noise == 0) | ((self.test >> 1) & 1)
        self.noise = (bit << 22) | (noise >> 1)
