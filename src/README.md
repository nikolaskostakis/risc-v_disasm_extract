# src/

## disasm.sh

Disassembles a RISC-V ELF file into a readable `.asm` and generates a byte-per-line hex dump.

```bash
disasm.sh <elf_file> [output_name]
```

Runs `objdump -d` to produce `<output_name>.asm` (input for `asm_parser.py`) and `objcopy` + `hexdump` to produce `<output_name>.hexdump.asm` (for Verilog's `$readmemh`). Both are written to `out/`. `output_name` defaults to the ELF file's basename. Requires the `riscv32-unknown-elf` toolchain (`objdump`, `objcopy`) and `hexdump` on `PATH`. Run with `-h`/`--help` for usage.

## asm_parser.py

Parses a RISC-V disassembly, counts instruction occurrences, and categorizes them by ISA extension.

```bash
python asm_parser.py <input_file> [options]
```

| Flag | Description |
|---|---|
| `input_file` | Disassembly file to parse (required) |
| `-o`, `--output-name` | Base name for generated output files |
| `-csv` | Save raw instruction counts to CSV |
| `-isa-csv` | Save per-ISA-extension instruction counts to CSV |
| `-e`, `--extract` | Instruction mnemonics to extract to a separate `.asm` file |

All generated files are written to `out/`. See the [top-level README](../README.md) for the full input format and usage examples.
