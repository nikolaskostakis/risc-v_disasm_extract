#!/usr/bin/env bash
#
# Disassembles a RISC-V ELF file and generates a hex dump of it.
#
# Author:  Nikolaos Kostakis
# Version: 1.2
#
# Usage: ./disasm.sh <elf_file> [output_name] [-endian little|big]
#        ./disasm.sh -h | --help
#        ./disasm.sh -v | --version
#        ./disasm.sh -c | --check

set -euo pipefail

VERSION="1.2"

RISCV="riscv32-unknown-elf"
OBJDUMP="${RISCV}-objdump"
OBJCOPY="${RISCV}-objcopy"
READELF="${RISCV}-readelf"
HEXDUMP="hexdump"

print_help() {
    echo "Usage: $0 <elf_file> [output_name] [-endian little|big]"
    echo ""
    echo "Disassembles <elf_file> and generates a hex dump of it, writing"
    echo "output_name.asm and output_name.mem to out/."
    echo "output_name defaults to the basename of <elf_file>."
    echo ""
    echo "Requires the ${RISCV} toolchain (objdump, objcopy, readelf) and hexdump on PATH."
    echo ""
    echo "  -endian little|big  Byte order for output_name.mem (default: little,"
    echo "                      the real RV32 memory layout). 'big' does a uniform"
    echo "                      4-byte swap of the raw binary -- only meaningful"
    echo "                      for a binary with no compressed (RVC) instructions,"
    echo "                      since a 4-byte swap doesn't respect 16-bit"
    echo "                      instruction boundaries; a warning is printed if the"
    echo "                      ELF's own RISC-V arch string reports the C/Zca"
    echo "                      extension."
    echo "  -c, --check  Check that the required tools are on PATH and exit"
}

missing_tools() {
    local missing=""
    for tool in "$OBJDUMP" "$OBJCOPY" "$READELF" "$HEXDUMP"; do
        command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
    done
    echo "$missing"
}

# -h/--help: show usage and exit
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    print_help
    exit 0
fi

# -v/--version: print the version and exit
if [ "${1:-}" = "-v" ] || [ "${1:-}" = "--version" ]; then
    echo "$(basename "$0") $VERSION"
    exit 0
fi

# -c/--check: report which required tools (if any) are missing and exit,
# without needing an ELF file
if [ "${1:-}" = "-c" ] || [ "${1:-}" = "--check" ]; then
    missing="$(missing_tools)"
    if [ -n "$missing" ]; then
        echo "Missing required tool(s):$missing" >&2
        echo "Install the ${RISCV} toolchain (for objdump/objcopy/readelf) and hexdump." >&2
        exit 1
    fi
    echo "All required tools found on PATH: $OBJDUMP, $OBJCOPY, $READELF, $HEXDUMP"
    exit 0
fi

# pull -endian/--endian out of the argument list wherever it appears,
# leaving <elf_file> [output_name] as the remaining positional args
ENDIAN="little"
POSITIONAL=()
while [ $# -gt 0 ]; do
    case "$1" in
        -endian|--endian)
            ENDIAN="${2:-}"
            shift 2
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done
set -- "${POSITIONAL[@]+"${POSITIONAL[@]}"}"

if [ "$ENDIAN" != "little" ] && [ "$ENDIAN" != "big" ]; then
    echo "Error: -endian must be 'little' or 'big' (got '$ENDIAN')" >&2
    exit 1
fi

# everything below here does a real disassemble, so an ELF file is required
if [ $# -lt 1 ]; then
    print_help >&2
    exit 1
fi

# fail fast if any required tool is missing, before touching the ELF file
missing="$(missing_tools)"
if [ -n "$missing" ]; then
    echo "Error: required tool(s) not found on PATH:$missing" >&2
    echo "Install the ${RISCV} toolchain (for objdump/objcopy/readelf) and hexdump." >&2
    exit 1
fi

ELF_FILE="$1"
OUTPUT_NAME="${2:-$(basename "$ELF_FILE" | sed 's/\.[^.]*$//')}"

if [ ! -f "$ELF_FILE" ]; then
    echo "Error: file '$ELF_FILE' not found" >&2
    exit 1
fi

# verify it's actually a RISC-V ELF before disassembling it as one
if ! "$READELF" -h "$ELF_FILE" 2>/dev/null | grep -q 'Machine:.*RISC-V'; then
    echo "Error: '$ELF_FILE' is not a RISC-V ELF file" >&2
    exit 1
fi

# resolve out/ relative to this script, so it works from any cwd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/../out"
mkdir -p "$OUT_DIR"

ASM_FILE="$OUT_DIR/${OUTPUT_NAME}.asm"
HEXDUMP_FILE="$OUT_DIR/${OUTPUT_NAME}.mem"
BIN_FILE="$OUT_DIR/${OUTPUT_NAME}.bin"

# readable disassembly, for isa_profiler.py
echo "Disassembling '$ELF_FILE' -> '$ASM_FILE'"
"$OBJDUMP" -d "$ELF_FILE" > "$ASM_FILE"

# raw binary, just a stepping stone to the hex dump below
echo "Extracting raw binary -> '$BIN_FILE'"
"$OBJCOPY" -O binary "$ELF_FILE" "$BIN_FILE"

# -endian big: uniformly swap each 4-byte word of the raw image. This is
# only actually correct for a binary with no 16-bit compressed
# instructions in it -- the swap has no idea where real instruction
# boundaries are, so on an RVC binary it corrupts them instead of
# reflecting a genuine big-endian encoding. Warn (but still proceed) if
# the ELF's own RISC-V arch attribute reports C or Zca.
if [ "$ENDIAN" = "big" ]; then
    ARCH="$("$READELF" -A "$ELF_FILE" 2>/dev/null | grep 'Tag_RISCV_arch' | sed 's/^ *//' || true)"
    if echo "$ARCH" | grep -qE '(^|_)c[0-9]|_zca'; then
        echo "Warning: '$ELF_FILE' reports the C/Zca (compressed instruction)" >&2
        echo "  extension ($ARCH). -endian big's 4-byte swap does not respect" >&2
        echo "  16-bit instruction boundaries and will corrupt this binary's" >&2
        echo "  memory image rather than genuinely byte-swap it." >&2
    fi

    BIN_SIZE=$(wc -c < "$BIN_FILE")
    if [ $((BIN_SIZE % 4)) -ne 0 ]; then
        echo "Error: '$ELF_FILE' is $BIN_SIZE byte(s), not a multiple of 4 --" >&2
        echo "  cannot do a 4-byte -endian big swap on it" >&2
        rm -f "$BIN_FILE"
        exit 1
    fi

    echo "Byte-swapping to big-endian 4-byte words"
    "$OBJCOPY" --reverse-bytes=4 -I binary -O binary "$BIN_FILE" "$BIN_FILE.swapped"
    mv "$BIN_FILE.swapped" "$BIN_FILE"
fi

# byte-per-line hex dump, for Verilog's $readmemh
echo "Hex dumping -> '$HEXDUMP_FILE'"
"$HEXDUMP" -e '16/1 "%02x " "\n"' "$BIN_FILE" > "$HEXDUMP_FILE"

rm "$BIN_FILE"

echo "Done."
