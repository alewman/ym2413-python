#!/bin/sh
# Build the OPLL referee from the pinned die-derived source in reference/src/
# (fetched by scripts/fetch_references.py, never committed here).
#
#   sh validation/build_referees.sh
#
# The binary lands in reference/build-referees/ (git-ignored). Nothing of the
# referee's source is copied into this repository: validation/opll_ref.c only drives it.
#
# Licence: Nuked-OPLL GPL-2.0+. The binary is built locally and run as a referee; it
# is not distributed.
set -e
root=$(cd "$(dirname "$0")/.." && pwd)
src="$root/reference/src"
out="$root/reference/build-referees"
mkdir -p "$out"

CC=${CC:-gcc}
CFLAGS=${CFLAGS:--O2 -w}
$CC --version | head -n 1

echo "opll_ref  (Nuked-OPLL @ 1269cf5)"
$CC $CFLAGS -I "$src/Nuked-OPLL" -o "$out/opll_ref" \
    "$root/validation/opll_ref.c" "$src/Nuked-OPLL/opll.c"

echo "built in $out"
