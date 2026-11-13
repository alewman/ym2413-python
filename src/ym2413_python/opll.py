"""The chip: registers, eighteen operators, and the sequence of output words.

Written from ``docs/spec.md``, not from another program. Every rule below names
the spec statement it implements, or says CHOICE (nothing speaks to it and this
core had to pick) or PROVISIONAL (an unsettled item taken at the hand-off brief's
default: T numbers, ``docs/handoff-brief.md``). ``docs/provenance-audit.md`` has
the chain behind each statement.

The unit of time is the slot: four input clocks, one pass through the chip's one
operator circuit (spec 2.3). A sample is eighteen slots. Operators are numbered
by slot, 0 to 17 (spec 2.4): ``tables.MODULATOR_SLOT`` and ``tables.CARRIER_SLOT``
say which channel each belongs to.

All state is plain attributes (ints, lists of ints, one bytearray), so that a
board's save-state walker can copy it out and back. ``variant`` is configuration
and never changes.
"""

from __future__ import annotations

from ym2413_python.tables import (
    CARRIER_SLOT,
    COPY_SLOT,
    ENVELOPE_PATTERNS,
    EXP,
    KEY_SCALE_STEPS,
    LOG_SIN,
    MODULATOR_SLOT,
    MULTIPLIER_X2,
    SLOT_BASS_DRUM,
    SLOT_CHANNEL,
    SLOT_CYMBAL,
    SLOT_HI_HAT,
    SLOT_IS_CARRIER,
    SLOT_SNARE,
    SLOT_TOM,
    TREMOLO,
    TREMOLO_PERIOD,
    VIBRATO_PERIOD,
)
from ym2413_python.variants import OPLLVariant

#: Input clocks in one slot (spec 2.3: documented, S1; measured, S4).
CLOCKS_PER_CYCLE = 4

#: Slots in one output sample: 72 input clocks (spec 2.2, 2.3).
CYCLES_PER_SAMPLE = 18

# Envelope states of a keyed operator (spec 8.16 to 8.21). "Release" is not a
# state: it is simply "the key is off" (spec 8.22).
DAMP, ATTACK, DECAY, SUSTAIN = range(4)

#: The envelope level at and above which an operator is silent and at which the
#: damp phase ends: its top five bits set (spec 6.8, 8.17: measured, S4).
QUIET = 124

#: The largest envelope level and the largest total attenuation (spec 8.1, 6.7).
BOTTOM = 127

# Phases, in 1/1024 periods, that make the snare's and the cymbal's four output
# values out of the ordinary sine look-up: the positive peak, the negative peak,
# and the two zeros (spec 11.8, 11.9).
PHASE_PLUS_ZERO, PHASE_PLUS_PEAK, PHASE_MINUS_ZERO, PHASE_MINUS_PEAK = 0x000, 0x100, 0x200, 0x300


def decay_step(rate: int, counter: int) -> int:
    """How far the envelope level rises this sample at an effective rate.

    ``counter`` is the chip's shared sample counter (spec 8.4).
    """
    if rate < 4:
        return 0  # spec 8.6: documented (S1 Table III-7 note), measured
    if rate < 52:
        # Spec 8.5 (measured): an opportunity when the counter's low s bits are
        # zero; the next three bits pick a place in the rate's pattern.
        s = 13 - (rate >> 2)
        if counter & ((1 << s) - 1):
            return 0
        return ENVELOPE_PATTERNS[rate & 3][(counter >> s) & 7]
    if rate >= 60:
        return 2  # spec 8.8: measured
    # Spec 8.7 (measured): a 16-sample cycle in which 0, 4, 8 or 12 samples go at
    # the faster of two speeds. CHOICE (U23): the faster samples are those where
    # counter bits 2 and 3 pick a 1 from the even places of the rate's pattern.
    faster = ENVELOPE_PATTERNS[rate & 3][(counter >> 1) & 6]
    if rate < 56:
        return 1 if faster else counter & 1
    return 2 if faster else 1


def attack_step(rate: int, counter: int, level: int) -> int:
    """The envelope level after one sample of attack at an effective rate."""
    if rate < 4 or rate >= 60:
        # Spec 8.13 (measured): with the rate at 0, or at the instant setting once
        # an attack is under way, the attack stalls.
        return level
    if rate < 48:
        # Spec 8.11 (measured): as decay, but the counter's lowest two bits are
        # ignored, so an opportunity lasts four samples; spec 8.10: each applies
        # x -> x - (x >> 4) - 1.
        s = 13 - (rate >> 2)
        if (counter >> 2) & ((1 << (s - 2)) - 1):
            return level
        if not ENVELOPE_PATTERNS[rate & 3][(counter >> s) & 7]:
            return level
        return level - (level >> 4) - 1
    # Spec 8.12 (measured): every sample; the shift is 4, 3, 2 for rates 48, 52,
    # 56, and one less on 4, 8 or 12 samples of 16 for the rates between.
    # CHOICE (U23): which samples, as in decay_step.
    shift = 4 - ((rate - 48) >> 2)
    if ENVELOPE_PATTERNS[rate & 3][(counter >> 1) & 6]:
        shift -= 1
    return level - (level >> shift) - 1


class OPLL:
    """A YM2413 or a DS1001, chosen by ``variant`` (``docs/api.md``)."""

    def __init__(self, variant: OPLLVariant) -> None:
        self.variant = variant

        # Where in the 72-clock sample the chip is. CHOICE (U9): a sample is taken
        # to begin with slot 0; no source says where it begins as seen from the
        # pins. Not touched by reset().
        self.clock_phase = 0  # input clocks into the current slot, 0 to 3
        self.slot = 0  # the next slot to compute, 0 to 17

        # Finished samples, and the sums of the sample in progress (T6).
        self.melody: list[int] = []
        self.rhythm: list[int] = []
        self.melody_sum = 0
        self.rhythm_sum = 0

        #: For the validation harness: set it to a list and each sample appends
        #: its eighteen (melody word, rhythm word) pairs, the words in the chip's
        #: own form (one's complement: -1 is "minus zero"). None costs nothing.
        self.trace: list | None = None

        self.reset()

    # ------------------------------------------------------------------ reset

    def reset(self) -> None:
        """The /IC pin, or the VRC7's sound-reset bit.

        Spec 14.1 (documented, S1): every register is cleared. Everything else
        here is PROVISIONAL (T5, U3): no source says what the envelopes, phases,
        counters and noise register hold afterwards.
        """
        self.address = 0
        self.registers = bytearray(0x40)
        self.test = 0

        # One entry per operator, indexed by slot.
        self.phase = [0] * 18  # 19 bits: 10 index the sine, 9 are fraction (spec 7.2)
        self.level = [BOTTOM] * 18  # envelope level, 0 loudest (spec 8.1)
        self.state = [SUSTAIN] * 18
        self.key = [0] * 18

        # The two previous outputs of each channel's modulator (spec 6.12).
        self.previous = [0] * 9
        self.before_previous = [0] * 9

        self.counter = 0  # the shared sample counter (spec 8.4)
        self.tremolo_time = 0  # samples into the tremolo cycle (spec 10.2)
        if self.variant.reset_clears_vibrato or not hasattr(self, "vibrato_time"):
            self.vibrato_time = 0  # samples into the vibrato cycle (spec 7.7)
        self.tremolo = 0  # this sample's tremolo level, 0 to 13
        self.noise = self.variant.reset_noise  # 23 stages (spec 11.7)

        # Each percussion word as last computed, for its second output (spec 11.12).
        self.held = [0] * 18

        # What each operator's instrument says, decoded from the registers and the
        # ROM whenever a write changes them. Derived, and saved like the rest.
        self.tremolo_on = [0] * 18
        self.vibrato_on = [0] * 18
        self.sustained = [0] * 18  # EG-TYP
        self.rate_scaling = [0] * 18  # KSR
        self.multiplier = [1] * 18  # twice the multiplier
        self.key_scale = [0] * 18  # the KSL code
        self.base = [0] * 18  # attenuation from TL or the volume, in envelope steps
        self.half_sine = [0] * 18
        self.attack_rate = [0] * 18
        self.decay_rate = [0] * 18
        self.sustain_level = [0] * 18
        self.release_rate = [0] * 18
        self.releases = [0] * 18  # whether key-off puts the operator into release
        self.feedback = [0] * 9
        self.rhythm_mode = 0
        self._decode_everything()

    # ----------------------------------------------------------------- writes

    def write(self, port: int, value: int) -> None:
        """A write with A0 = ``port``: 0 latches an address, 1 stores data there.

        Spec 3.1, 3.2 (documented, S1): the address stays latched. PROVISIONAL
        (T7, U9): a data write acts on every slot that starts after it; the waits
        the manual asks for are not modelled.
        """
        value &= 0xFF
        if port & 1 == 0:
            self.address = value
            return
        address = self.address
        if address >= 0x40:
            return  # PROVISIONAL (T7; spec 4.4): no source; ignored
        low = address & 0x0F
        if address >= 0x10 and low >= 9:
            # Spec 4.3 (measured, S4 ksl.txt): $19-$1F, $29-$2F and $39-$3F act as
            # $10-$16, $20-$26 and $30-$36.
            address -= 9
            low -= 9
        if address < 0x08:
            self.registers[address] = value  # the user tone (spec 4, 5.1)
            for channel in range(9):
                self._decode_channel(channel)
        elif address == 0x0E:
            self.registers[address] = value & 0x3F
            self._decode_everything()
        elif address == 0x0F:
            # Spec 13: documented for the VRC7 at tier 3 (S6); PROVISIONAL on the
            # YM2413 (T4).
            self.registers[address] = value
            self.test = value & self.variant.test_bits
        elif address < 0x10:
            return  # PROVISIONAL (T7; spec 4.4): $08-$0D, no source; ignored
        elif address < 0x20:
            self.registers[address] = value  # F-number bits 7-0
        elif address < 0x30:
            self.registers[address] = value & 0x3F  # spec 4.2: bits 7-6 unused
            self._decode_keys()
        else:
            self.registers[address] = value
            self._decode_channel(low)

    def _decode_everything(self) -> None:
        # Spec 11.1 (documented): bit 5 of $0E is rhythm mode. PROVISIONAL (T10,
        # U8): switching it changes only which settings and which keys the six
        # operators of channels 6 to 8 use; their envelopes and phases carry on.
        self.rhythm_mode = 1 if self.variant.rhythm_forced else (self.registers[0x0E] >> 5) & 1
        for channel in range(9):
            self._decode_channel(channel)
        self._decode_keys()

    def _decode_channel(self, channel: int) -> None:
        """Work out both operators' settings for a channel (spec 4, 5, 11.11)."""
        registers = self.registers
        modulator, carrier = MODULATOR_SLOT[channel], CARRIER_SLOT[channel]
        percussion = self.rhythm_mode and channel >= 6
        voice = registers[0x30 + channel] >> 4
        volume = registers[0x30 + channel] & 0x0F
        if percussion:
            row = self.variant.percussion[channel - 6]  # spec 5.3, 5.6
        elif voice == 0:
            row = registers  # spec 5.1: the user tone in $00-$07
        else:
            row = self.variant.voices[voice - 1]

        for operator, which in ((modulator, 0), (carrier, 1)):
            flags = row[which]
            self.tremolo_on[operator] = flags >> 7
            self.vibrato_on[operator] = (flags >> 6) & 1
            self.sustained[operator] = (flags >> 5) & 1
            self.rate_scaling[operator] = (flags >> 4) & 1
            self.multiplier[operator] = MULTIPLIER_X2[flags & 0x0F]
            self.key_scale[operator] = row[2 + which] >> 6
            self.attack_rate[operator] = row[4 + which] >> 4
            self.decay_rate[operator] = row[4 + which] & 0x0F
            self.sustain_level[operator] = row[6 + which] >> 4
            self.release_rate[operator] = row[6 + which] & 0x0F
        self.half_sine[modulator] = (row[3] >> 3) & 1  # DM
        self.half_sine[carrier] = (row[3] >> 4) & 1  # DC
        self.feedback[channel] = row[3] & 0x07

        # Spec 6.7: a modulator's base attenuation is its total level, 0.75 dB a
        # step, two envelope steps; a carrier's is the volume, 3 dB a step, eight.
        self.base[modulator] = 2 * (row[2] & 0x3F)
        self.base[carrier] = 8 * volume
        # Spec 8.23 (measured): a modulator does not change rate at key-off.
        self.releases[modulator] = 0
        self.releases[carrier] = 1
        if percussion and channel >= 7:
            # The hi-hat and the tom are single operators on modulator slots.
            # They "always act like a carrier" (S4 rhythm.md, prose). Their volume
            # is the high nibble of $37 and $38 (spec 4, S1's second map).
            # PROVISIONAL (T12, U11): eight envelope steps a volume step, and no
            # total level.
            self.base[modulator] = 8 * voice
            self.releases[modulator] = 1

    def _decode_keys(self) -> None:
        """Each operator's key, and the start of a note where one goes on."""
        registers = self.registers
        rhythm = registers[0x0E] if self.rhythm_mode else 0
        for channel in range(9):
            on = (registers[0x20 + channel] >> 4) & 1
            modulator_on = carrier_on = on
            if rhythm and channel >= 6:
                # PROVISIONAL (T9, U7; spec 11.4, measured loosely): in rhythm
                # mode each sound is keyed by its $0E bit OR its channel's key bit.
                if channel == 6:
                    modulator_on = carrier_on = on | ((rhythm >> 4) & 1)  # bass drum
                elif channel == 7:
                    modulator_on = on | (rhythm & 1)  # hi-hat
                    carrier_on = on | ((rhythm >> 3) & 1)  # snare
                else:
                    modulator_on = on | ((rhythm >> 2) & 1)  # tom
                    carrier_on = on | ((rhythm >> 1) & 1)  # top cymbal
            for operator, now in (
                (MODULATOR_SLOT[channel], modulator_on),
                (CARRIER_SLOT[channel], carrier_on),
            ):
                if now and not self.key[operator]:
                    # Spec 8.16 (measured): key off to key on enters damp.
                    # PROVISIONAL (T14, U13): modulators and percussion too.
                    self.state[operator] = DAMP
                self.key[operator] = now

    # ------------------------------------------------------------------- time

    def run(self, clocks: int) -> None:
        """Advance by input clocks. ``run(a); run(b)`` equals ``run(a + b)``.

        A slot is computed as its first clock passes, so a write made between two
        calls acts on the slots that begin after it (T7).
        """
        before = self.clock_phase
        after = before + clocks
        slots = (after + 3) // CLOCKS_PER_CYCLE - (before + 3) // CLOCKS_PER_CYCLE
        self.clock_phase = after % CLOCKS_PER_CYCLE
        for _ in range(slots):
            self._run_slot()

    def take_outputs(self) -> list[tuple[int, int]]:
        """The samples finished since the last take, as (melody, rhythm) pairs.

        CHOICE (T6; spec section 12): the chip's fact is a train of nine-bit
        words, one per slot, on two pins. Each pair here is the sum of one
        sample's words on the melody pin and on the rhythm pin (each percussion
        word appears twice, as the chip outputs it: spec 11.12). A word counts as
        its signed size, -255 to +255; the two zeros both count as 0.
        """
        pairs = list(zip(self.melody, self.rhythm, strict=True))
        self.melody = []
        self.rhythm = []
        return pairs

    def take_samples(self) -> list[int]:
        """The same samples as one number each: melody plus rhythm (T6)."""
        return [melody + rhythm for melody, rhythm in self.take_outputs()]

    # ------------------------------------------------------------- one sample

    def _begin_sample(self) -> None:
        """What happens once a sample: the shared counter and the two LFOs."""
        test = self.test
        self.counter = (self.counter + 1) & 0xFFFFFF  # spec 8.4; width is U19
        if test & 0x02:
            # Spec 13.2 (S6, tier 3): bit 1 holds both LFOs at zero.
            self.tremolo_time = 0
            self.vibrato_time = 0
        else:
            # Spec 13.2: bit 3 makes the LFOs move every sample: the tremolo 64
            # times faster and the vibrato 1,024 times faster.
            # CHOICE (U15, U19): the LFOs are counted apart from the envelope
            # counter, since the VRC7's reset clears one and not the other.
            fast = test & 0x08
            self.tremolo_time = (self.tremolo_time + (64 if fast else 1)) % TREMOLO_PERIOD
            self.vibrato_time = (self.vibrato_time + (1024 if fast else 1)) % VIBRATO_PERIOD
        self.tremolo = TREMOLO[self.tremolo_time >> 6]  # spec 10.2 (measured)

    def _run_slot(self) -> None:
        slot = self.slot
        if slot == 0:
            self._begin_sample()
        variant = self.variant
        channel = SLOT_CHANNEL[slot]
        percussion = self.rhythm_mode and channel >= 6
        melody_word = rhythm_word = 0

        if self.rhythm_mode and variant.rhythm_output and slot in COPY_SLOT:
            # Spec 11.12 (documented and measured): each percussion word is
            # output a second time, unchanged, in a slot of the next sample.
            rhythm_word = self.held[COPY_SLOT[slot]]

        if channel < variant.channels or (percussion and variant.rhythm_output):
            self._step_envelope(slot, channel)
            self._step_phase(slot, channel)
            if not percussion:
                word = self._melodic_word(slot, channel)
                if SLOT_IS_CARRIER[slot]:
                    melody_word = word
            else:
                word = self._percussion_word(slot)
                if slot != 12:  # the bass drum's modulator is not heard
                    self.held[slot] = word
                    rhythm_word = word

        # Spec 11.7 (measured): the noise register is a 23-stage shift register
        # with polynomial x^23 + x^9 + 1, stepped once per slot.
        noise = self.noise
        self.noise = (noise >> 1) | (((noise ^ (noise >> 14)) & 1) << 22)

        # Spec 12.3: the words are not added inside the chip. CHOICE (T6): the
        # core hands out their sum over a sample; a negative word ~m counts -m.
        self.melody_sum += melody_word + (melody_word < 0)
        self.rhythm_sum += rhythm_word + (rhythm_word < 0)
        if self.trace is not None:
            if slot == 0:
                self.trace.append([])
            if self.trace:
                self.trace[-1].append((melody_word, rhythm_word))

        slot += 1
        if slot == CYCLES_PER_SAMPLE:
            slot = 0
            self.melody.append(self.melody_sum)
            self.rhythm.append(self.rhythm_sum)
            self.melody_sum = 0
            self.rhythm_sum = 0
        self.slot = slot

    # --------------------------------------------------------------- envelope

    def _effective_rate(self, operator: int, channel: int, rate: int) -> int:
        """Spec 8.2, 8.3 (documented, S1 III-1-2 and Table III-2; measured)."""
        if rate == 0:
            return 0
        high = self.registers[0x20 + channel]
        block_and_top = high & 0x0F  # BLOCK and F-number bit 8
        scaling = block_and_top if self.rate_scaling[operator] else block_and_top >> 2
        return min(63, 4 * rate + scaling)

    def _step_envelope(self, operator: int, channel: int) -> None:
        level = self.level[operator]
        counter = self.counter
        variant = self.variant

        if not self.key[operator] and self.releases[operator]:
            # Spec 8.22 (measured and documented): release is "the key is off",
            # whatever state the operator was in. Spec 8.24: it runs to 127.
            if (self.registers[0x20 + channel] >> 5) & 1:
                rate = variant.sustained_release_rate  # the SUS bit: rate 5
            elif self.sustained[operator]:
                rate = self.release_rate[operator]
            else:
                rate = variant.percussive_release_rate  # rate 7
            rate = self._effective_rate(operator, channel, rate)
            # PROVISIONAL (T13, U14): a step past the bottom stops at 127.
            self.level[operator] = min(BOTTOM, level + decay_step(rate, counter))
            return

        state = self.state[operator]
        if state == DAMP:
            if level >= QUIET:
                # Spec 8.17 (measured): damp ends at 124, not 127; spec 7.10: the
                # phase is set to zero then. CHOICE (U20): each operator resets
                # its own phase when its own damp ends.
                self.phase[operator] = 0
                rate = self._effective_rate(operator, channel, self.attack_rate[operator])
                if rate >= 60:
                    # Spec 8.13 (measured): the instant attack is decided here.
                    self.level[operator] = 0
                    self.state[operator] = DECAY
                else:
                    self.state[operator] = ATTACK
                return
            # Spec 8.16 (measured): damp is a decay at fixed rate 12, key-scaled.
            rate = self._effective_rate(operator, channel, variant.damp_rate)
            self.level[operator] = min(BOTTOM, level + decay_step(rate, counter))
            return

        if state == ATTACK:
            if level == 0:
                state = self.state[operator] = DECAY  # spec 8.18
            else:
                rate = self._effective_rate(operator, channel, self.attack_rate[operator])
                self.level[operator] = attack_step(rate, counter, level)
                return

        if state == DECAY:
            # Spec 8.19 (measured): decay ends when the level's top four bits
            # equal SL: equality, not "at or beyond".
            if level >> 3 == self.sustain_level[operator]:
                state = self.state[operator] = SUSTAIN
            else:
                rate = self._effective_rate(operator, channel, self.decay_rate[operator])
                self.level[operator] = min(BOTTOM, level + decay_step(rate, counter))
                return

        # Spec 8.20 (measured): sustain is one state with two rates. A sustained
        # tone holds; a percussive one goes on at RR. Spec 8.21: SL plays no part.
        if not self.sustained[operator]:
            rate = self._effective_rate(operator, channel, self.release_rate[operator])
            self.level[operator] = min(BOTTOM, level + decay_step(rate, counter))

    # ------------------------------------------------------------------ phase

    def _step_phase(self, operator: int, channel: int) -> None:
        if self.test & 0x04:
            self.phase[operator] = 0  # spec 13.2 (S6): bit 2 holds every phase at zero
            return
        registers = self.registers
        high = registers[0x20 + channel]
        f_number = registers[0x10 + channel] | ((high & 1) << 8)
        block = (high >> 1) & 7
        multiplier = self.multiplier[operator]
        if self.vibrato_on[operator]:
            # Spec 7.8: measured approximately for the top pitch range,
            # PROVISIONAL below it (T3, U4).
            offset = self.variant.vibrato_offsets[f_number >> 6][self.vibrato_time >> 10]
            step = (((2 * f_number + offset) * multiplier) << block) >> 2
        else:
            # Spec 7.3 (measured): ((F-number x twice the multiplier) << block) >> 1.
            step = ((f_number * multiplier) << block) >> 1
        # Spec 7.2, 7.3: 19 bits; what overflows is lost. Spec 7.6: a step of 0
        # leaves the phase where it is.
        self.phase[operator] = (self.phase[operator] + step) & 0x7FFFF

    # ----------------------------------------------------------------- output

    def _operate(self, operator: int, channel: int, phase: int) -> int:
        """One pass through the operator circuit (spec section 6).

        ``phase`` is in 1/1024 periods. The result is the eleven-bit value v of
        spec 6.5 in one's complement: -1 is "minus zero" (spec 6.6).
        """
        level = self.level[operator]
        if self.test & 0x01:
            level = 0  # spec 13.2 (S6): bit 0 replaces the envelope's output by 0
        if level >= QUIET:
            return 0  # spec 6.8 (measured): a quiet operator outputs +0

        # Spec 6.2 (measured): a quarter is stored; the second quarter reads it
        # backwards and the second half changes the sign.
        index = phase & 0xFF
        if phase & 0x100:
            index ^= 0xFF
        negative = phase & 0x200

        # Spec 6.7 (measured): attenuation in envelope steps, clipped at 127.
        high = self.registers[0x20 + channel]
        f_number_top = ((high & 1) << 3) | (self.registers[0x10 + channel] >> 5)
        attenuation = (
            self.base[operator]
            + KEY_SCALE_STEPS[self.key_scale[operator]][(high >> 1) & 7][f_number_top]
            + level
        )
        if self.tremolo_on[operator]:
            attenuation += self.tremolo  # spec 10.1 (measured)
        if attenuation > BOTTOM:
            attenuation = BOTTOM

        # Spec 6.5 (measured): each envelope step is 16 units of the logarithm.
        x = LOG_SIN[index] + (attenuation << 4)
        value = (EXP[(x & 0xFF) ^ 0xFF] + 1024) >> (x >> 8)
        if negative:
            if self.half_sine[operator]:
                value = 0  # spec 6.9 (measured): size zero, the sign still set
            return ~value
        return value

    def _melodic_word(self, operator: int, channel: int) -> int:
        phase = self.phase[operator] >> 9
        if not SLOT_IS_CARRIER[operator]:
            feedback = self.feedback[channel]
            if feedback:
                # Spec 6.12: the sum of the modulator's two previous outputs
                # (measured, S4), shifted right by 8 - FB (documented: S1 Table
                # III-6). PROVISIONAL (U24): the shift of a negative sum rounds
                # down.
                phase += (self.previous[channel] + self.before_previous[channel]) >> (8 - feedback)
            value = self._operate(operator, channel, phase & 0x3FF)
            self.before_previous[channel] = self.previous[channel]
            self.previous[channel] = value
            return 0
        # Spec 6.11 (measured): the carrier's phase is moved by twice the
        # modulator's output. PROVISIONAL (T11; spec 6.13, U21): the output used
        # is the previous sample's, which gives the one-sample lag S4 measured.
        # By this slot the modulator has already run this sample, so that output
        # is the older of the two remembered.
        phase += 2 * self.before_previous[channel]
        # Spec 6.10 (measured): a carrier's word is the value shifted right by 3:
        # nine bits, -255 to +255 with both zeros.
        return self._operate(operator, channel, phase & 0x3FF) >> 3

    def _cymbal_bit(self) -> int:
        """The one bit the top cymbal and the hi-hat share (spec 11.9).

        Measured (S4) as a function of five phase bits, two of C8's and three of
        M7's, up to sixteen forms that fit the captures equally. PROVISIONAL,
        emulator tier (T8, U5): emu2413's form (MIT), the first of the sixteen,
        on bits of the ten-bit phase. CHOICE: each sound reads the two phases as
        they stand at its own slot.
        """
        m7 = self.phase[SLOT_HI_HAT] >> 9
        c8 = self.phase[SLOT_CYMBAL] >> 9
        c5 = (c8 >> 5) & 1
        return (c5 == (c8 >> 3) & 1) & ((m7 >> 7) & 1 == (m7 >> 2) & 1) & (c5 == (m7 >> 3) & 1)

    def _percussion_word(self, operator: int) -> int:
        """Channels 6 to 8 in rhythm mode (spec section 11)."""
        if operator == SLOT_BASS_DRUM or operator == 12:
            # Spec 11.5 (measured): the bass drum is an ordinary two-operator voice.
            return self._melodic_word(operator, 6)
        channel = SLOT_CHANNEL[operator]
        noise = self.noise & 1
        if operator == SLOT_TOM:
            # Spec 11.6 (measured): a plain sine at channel 8's pitch.
            phase = self.phase[operator] >> 9
        elif operator == SLOT_SNARE:
            # Spec 11.8 (measured): one phase bit and the noise bit choose among
            # four values. PROVISIONAL (T8, U5, U6): the bit is bit 8 of the
            # snare's own ten-bit phase, and the table is the first of S4's two.
            if (self.phase[operator] >> 17) & 1:
                phase = PHASE_MINUS_ZERO if noise else PHASE_MINUS_PEAK
            else:
                phase = PHASE_PLUS_PEAK if noise else PHASE_PLUS_ZERO
        elif operator == SLOT_CYMBAL:
            # Spec 11.9: a positive or negative peak (measured). PROVISIONAL,
            # emulator tier: which is which (emu2413).
            phase = PHASE_PLUS_PEAK if self._cymbal_bit() else PHASE_MINUS_PEAK
        else:
            # Spec 11.10, PROVISIONAL, emulator tier (U22): the hi-hat.
            phase = self.variant.hi_hat_phases[2 * self._cymbal_bit() + noise]
        return self._operate(operator, channel, phase & 0x3FF) >> 3
