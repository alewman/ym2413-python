/*
 * Closed-box harness for Nuked-OPLL (docs/restart.md rule 8, docs/validation.md
 * rung 6).
 *
 * Nuked-OPLL is GPL-2.0-or-later. This file is the only code in the repository
 * that touches it, and it was written from three declarations in the model's
 * public header, opll.h: OPLL_Reset(chip, chip_type), OPLL_Clock(chip, buffer)
 * and OPLL_Write(chip, port, data), with the header's chip-type numbers (0 for
 * the YM2413, 1 for the DS1001). The header also declares the model's state
 * structure; this harness allocates one and never looks inside it. The model's
 * opll.c is compiled and linked, and is not opened, searched or quoted. Nothing
 * built from it is committed or shipped (validation/build/ is git-ignored).
 *
 * Usage: nuked_harness CHIP_TYPE, then commands on standard input, one per line:
 *
 *   w PORT BYTE   OPLL_Write(chip, PORT, BYTE)
 *   c COUNT       call OPLL_Clock COUNT times; after each call append the first
 *                 two words of the buffer to standard output as two 32-bit ints
 *
 * Numbers are decimal or 0x-prefixed. The header does not say what one
 * OPLL_Clock call is in input clocks, how long the buffer must be, or what its
 * words mean: validation/closed_box.py measures what it needs from the output.
 * The buffer here is longer than two words in case the model writes more.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "opll.h"

int main(int argc, char **argv)
{
    static opll_t chip;
    static int32_t block[8192];
    int32_t buffer[16] = {0};
    size_t held = 0;
    char command;
    char first[64], second[64];

    OPLL_Reset(&chip, argc > 1 ? (uint32_t)strtoul(argv[1], NULL, 0) : 0);
    while (scanf(" %c %63s", &command, first) == 2) {
        unsigned long value = strtoul(first, NULL, 0);
        switch (command) {
        case 'w':
            if (scanf(" %63s", second) != 1) {
                return 2;
            }
            OPLL_Write(&chip, (uint32_t)value, (uint8_t)strtoul(second, NULL, 0));
            break;
        case 'c':
            while (value--) {
                OPLL_Clock(&chip, buffer);
                block[held++] = buffer[0];
                block[held++] = buffer[1];
                if (held == sizeof block / sizeof block[0]) {
                    fwrite(block, sizeof block[0], held, stdout);
                    held = 0;
                }
            }
            break;
        default:
            fprintf(stderr, "unknown command %c\n", command);
            return 2;
        }
    }
    fwrite(block, sizeof block[0], held, stdout);
    return 0;
}
