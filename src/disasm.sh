#!/usr/bin/env bash
#
# Disassembles a RISC-V ELF file and generates a hex dump of it.
#
# Author:  Nikolaos Kostakis
# Version: 1.1
#
# Usage: ./disasm.sh <elf_file> [output_name]
#        ./disasm.sh -h | --help
#        ./disasm.sh -v | --version
#        ./disasm.sh -c | --check

set -euo pipefail

VERSION="1.1"

RISCV="riscv32-unknown-elf"
OBJDUMP="${RISCV}-objdump"
OBJCOPY="${RISCV}-objcopy"
READELF="${RISCV}-readelf"
HEXDUMP="hexdump"

print_help() {
    echo "Usage: $0 <elf_file> [output_name]"
    echo ""
    echo "Disassembles <elf_file> and generates a hex dump of it, writing"
    echo "output_name.asm and output_name.hexdump.asm to out/."
    echo "output_name defaults to the basename of <elf_file>."
    echo ""
    echo "Requires the ${RISCV} toolchain (objdump, objcopy, readelf) and hexdump on PATH."
    echo ""
    echo "  -c, --check  Check that the required tools are on PATH and exit"
}

missing_tools() {
    local missing=""
    for tool in "$OBJDUMP" "$OBJCOPY" "$READELF" "$HEXDUMP"; do
        command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
    done
    echo "$missing"
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    print_help
    exit 0
fi

if [ "${1:-}" = "-v" ] || [ "${1:-}" = "--version" ]; then
    echo "$(basename "$0") $VERSION"
    exit 0
fi

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

if [ $# -lt 1 ]; then
    print_help >&2
    exit 1
fi

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

if ! "$READELF" -h "$ELF_FILE" 2>/dev/null | grep -q 'Machine:.*RISC-V'; then
    echo "Error: '$ELF_FILE' is not a RISC-V ELF file" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$SCRIPT_DIR/../out"
mkdir -p "$OUT_DIR"

ASM_FILE="$OUT_DIR/${OUTPUT_NAME}.asm"
HEXDUMP_FILE="$OUT_DIR/${OUTPUT_NAME}.hexdump.asm"
BIN_FILE="$OUT_DIR/${OUTPUT_NAME}.bin"

echo "Disassembling '$ELF_FILE' -> '$ASM_FILE'"
"$OBJDUMP" -d "$ELF_FILE" > "$ASM_FILE"

echo "Extracting raw binary -> '$BIN_FILE'"
"$OBJCOPY" -O binary "$ELF_FILE" "$BIN_FILE"

echo "Hex dumping -> '$HEXDUMP_FILE'"
"$HEXDUMP" -e '16/1 "%02x " "\n"' "$BIN_FILE" > "$HEXDUMP_FILE"

rm "$BIN_FILE"

echo "Done."
