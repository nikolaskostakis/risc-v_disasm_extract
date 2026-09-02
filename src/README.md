# src/

## disasm.sh

Disassembles a RISC-V ELF file into a readable `.asm` and generates a byte-per-line hex dump.

```bash
disasm.sh <elf_file> [output_name]
```

Runs `objdump -d` to produce `<output_name>.asm` (input for `isa_profiler.py`) and `objcopy` + `hexdump` to produce `<output_name>.mem` (for Verilog's `$readmemh`). Both are written to `out/`. `output_name` defaults to the ELF file's basename. Verifies `<elf_file>` is actually a RISC-V ELF (via `readelf -h`) before disassembling. Requires the `riscv32-unknown-elf` toolchain (`objdump`, `objcopy`, `readelf`) and `hexdump` on `PATH` — checked up front, with a clear error naming whatever's missing.

| Flag | Description |
| --- | --- |
| `-h`, `--help` | Show usage and exit |
| `-v`, `--version` | Print the tool's version and exit |
| `-c`, `--check` | Check that the required tools are on `PATH` and exit, without needing an ELF file (`make check` runs this, then also verifies the Python version) |

## isa_profiler.py

Parses a RISC-V disassembly, counts instruction occurrences, and categorizes them by ISA extension.

```bash
python isa_profiler.py <input_file> [options]
```

| Flag | Description |
| --- | --- |
| `input_file` | Disassembly file to parse (required) |
| `-h`, `--help` | Show usage and exit |
| `-o`, `--output-name` | Base name for generated output files |
| `-csv` | Save raw instruction counts to CSV |
| `-isa-csv` | Save per-ISA-extension instruction counts to CSV |
| `-e`, `--extract` | Instruction mnemonics to extract to a separate `.asm` file |
| `-es`, `--extract-set` | ISA sets/subsets to extract, e.g. `rv32I`, `rv32I_loads`, `rv32A` (combinable with `-e`) |
| `-eh`, `--extract-hex` | With `-e`/`-es`: also write a hexdump of the extracted instructions (4 little-endian bytes per line, one instruction per line). Warns and does nothing if used without `-e`/`-es` |
| `-list-sets` | Print the known ISA sets/subsets and exit; `input_file` not required |
| `-list-instr` | Print the instruction mnemonics in the given set(s)/subset(s), one per line, and exit; `input_file` not required |
| `-v`, `--version` | Print the tool's version and exit; `input_file` not required |

### ISA sets and subsets

Names are case-insensitive. A whole set (e.g. `rv32I`) expands to all of its subsets; a subset (e.g. `rv32I_loads`) matches just that category. Used by both `-isa-csv` categorization and `-es`/`--extract-set`. Run `isa_profiler.py -list-sets` to print this list from the CLI directly — whole sets are printed with their subsets tab-indented beneath them.

| Set | Subsets |
| --- | --- |
| `rv32I` | `rv32I_logic`, `rv32I_addsub`, `rv32I_shifts`, `rv32I_comparisons`, `rv32I_jumps`, `rv32I_branches`, `rv32I_loads`, `rv32I_stores`, `rv32I_other` |
| `rv32M` | `rv32M_mul`, `rv32M_div`, `rv32M_rem` |
| `rv32A` | — |
| `rv32F` | — |
| `rv32D` | — |
| `rv32C` | — |
| `rv32B` | — |
| `zicsr` | — |
| `zifencei` | — |
| `zicntr` | — |

---

All generated files are written to `out/`. See the [top-level README](../README.md) for the full input format and usage examples.
