# What the boards need

Read off the boards' own code (sms-python `board.py` and `audio.py`;
famicom-python's VRC7 before its sound was switched off), not off the earlier
core. Where a better shape is found, say so and change the boards with it.

```python
from ym2413_python import OPLL, YM2413, DS1001, CLOCKS_PER_CYCLE, CYCLES_PER_SAMPLE

chip = OPLL(YM2413)           # a variant is a value: YM2413, or DS1001 for the VRC7
chip.write(port, value)       # port 0 the address, port 1 the data
chip.run(clocks)              # advance by input clocks (3.579545 MHz on these machines)
samples = chip.take_samples() # sms-python: the mixed output since the last call
outputs = chip.take_outputs() # famicom-python: (melody, rhythm) output words
chip.reset()                  # famicom-python: the VRC7's sound-silence bit
```

- sms-python mixes the FM unit beside the PSG and needs a level per output
  sample, with the sample period expressed as `CLOCKS_PER_CYCLE` and
  `CYCLES_PER_SAMPLE` (the chip's output rate is its clock divided by 72).
- famicom-python averaged the VRC7's output words over one sample and scaled
  them to +11.3 dB against an APU square (rainwarrior's `db_vrc7` measurement).
- The DS1001 has no rhythm output pin and its own instrument set; the NESdev
  wiki has that set from the chip's debug mode.
- sms-python's save states walk the core's objects: state must be plain
  attributes, and any frozen value that changes at run time must be declared
  (`state.VALUES`).

Places to start looking, each to be checked for licence and tier in Phase 0:
Yamaha's YM2413 application manual; the NESdev wiki's VRC7 audio pages; emu2413
(Mitsutaka Okazaki, MIT) and ymfm (Aaron Giles, BSD-3-Clause) as permissive
source; andete's captures of a real YM2413 (his repository states no licence:
measurements may be compared with, the files not copied).
