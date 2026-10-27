/* A headless harness around Nuked-OPLL (reference/src/Nuked-OPLL, GPL-2.0+, pinned at
 * 1269cf5), built by validation/build_referees.sh and run as a referee.  Nothing of
 * Nuked-OPLL is copied into ym2413-python: this file only drives it.
 *
 *   opll_ref <type> <events.bin> <out.bin> <cycles>
 *
 * type: Nuked-OPLL's chip type (0 YM2413, 1 DS1001 = VRC7, 2 YM2413B, 3 YMF281,
 * 4 YMF281B, 5 YM2420, 6 YM2423).
 *
 * events.bin: little-endian records of {u64 cycle; u8 port; u8 data}, sorted, where
 * `cycle` counts OPLL_Clock calls (internal cycles, four input clocks each) and port
 * is A0 (0 address, 1 data).  A write is applied before the call whose index it names.
 *
 * out.bin: per cycle, the two values OPLL_Clock hands back: {i16 mo; i16 ro}, the
 * melody and rhythm DAC inputs that cycle.
 */
#include <stdio.h>
#include <stdlib.h>
#include "opll.h"

typedef struct { unsigned long long cycle; unsigned char port, data; } event_t;

int main(int argc, char **argv)
{
    if (argc < 5) {
        fprintf(stderr, "usage: %s type events.bin out.bin cycles\n", argv[0]);
        return 2;
    }
    unsigned type = (unsigned)strtoul(argv[1], NULL, 10);
    unsigned long long cycles = strtoull(argv[4], NULL, 10);

    FILE *ef = fopen(argv[2], "rb");
    if (!ef) { perror(argv[2]); return 1; }
    fseek(ef, 0, SEEK_END);
    long count = ftell(ef) / 10;
    fseek(ef, 0, SEEK_SET);
    event_t *events = calloc(count ? count : 1, sizeof(event_t));
    for (long i = 0; i < count; i++) {
        unsigned char rec[10];
        if (fread(rec, 1, 10, ef) != 10) { fprintf(stderr, "short event file\n"); return 1; }
        unsigned long long t = 0;
        for (int b = 7; b >= 0; b--) t = (t << 8) | rec[b];
        events[i].cycle = t;
        events[i].port = rec[8];
        events[i].data = rec[9];
    }
    fclose(ef);

    FILE *of = fopen(argv[3], "wb");
    if (!of) { perror(argv[3]); return 1; }
    setvbuf(of, NULL, _IOFBF, 1 << 20);

    opll_t *chip = calloc(1, sizeof(opll_t));
    OPLL_Reset(chip, type);

    long next = 0;
    int32_t buffer[2];
    for (unsigned long long c = 0; c < cycles; c++) {
        while (next < count && events[next].cycle <= c) {
            OPLL_Write(chip, events[next].port, events[next].data);
            next++;
        }
        OPLL_Clock(chip, buffer);
        unsigned char rec[4];
        rec[0] = buffer[0] & 0xff; rec[1] = (buffer[0] >> 8) & 0xff;
        rec[2] = buffer[1] & 0xff; rec[3] = (buffer[1] >> 8) & 0xff;
        fwrite(rec, 1, 4, of);
    }
    fclose(of);
    free(chip);
    free(events);
    return 0;
}
