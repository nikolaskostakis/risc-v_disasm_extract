#!/usr/bin/env bash
#
# Disassembles a RISC-V ELF file and generates a hex dump of it.
#
# Usage: ./disasm.sh <elf_file> [output_name]

set -euo pipefail

RISCV="riscv32-unknown-elf"
OBJDUMP="${RISCV}-objdump"
OBJCOPY="${RISCV}-objcopy"
HEXDUMP="hexdump"

print_help() {
    echo "Usage: $0 <elf_file> [output_name]"
    echo ""
    echo "Disassembles <elf_file> and generates a hex dump of it, writing"
    echo "output_name.asm and output_name.hexdump.asm to out/."
    echo "output_name defaults to the basename of <elf_file>."
    echo ""
    echo "Requires the ${RISCV} toolchain (objdump, objcopy) and hexdump on PATH."
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    print_help
    exit 0
fi

if [ $# -lt 1 ]; then
    print_help >&2
    exit 1
fi

ELF_FILE="$1"
OUTPUT_NAME="${2:-$(basename "$ELF_FILE" | sed 's/\.[^.]*$//')}"

if [ ! -f "$ELF_FILE" ]; then
    echo "Error: file '$ELF_FILE' not found" >&2
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
