# risc-v_disasm_extract

A toolset for working with RISC-V disassembly: `disasm.sh` turns a compiled ELF into a readable disassembly and a hex dump, and `isa_profiler.py` counts instruction occurrences, categorizes them by RISC-V ISA extension (RV32I, RV32M, RV32A, RV32F, RV32D, RV32C, RV32B, Zicsr, Zifencei, Zicntr), and can extract lines matching specific instructions, or whole ISA sets/subsets, to a separate file.

## Layout

- [`src/`](src/) — `disasm.sh` and `isa_profiler.py` (see [src/README.md](src/README.md) for details on each)
- [`out/`](out/) — generated files, created automatically if missing

## Requirements

- Python 3.10+ — no third-party dependencies, only the standard library
- To run `disasm.sh`: the `riscv32-unknown-elf` toolchain (`objdump`, `objcopy`, `readelf`) and `hexdump` on `PATH` — `disasm.sh` checks for these up front and reports exactly which are missing if not, and verifies the input is actually a RISC-V ELF before disassembling
- `make` (optional, for the `Makefile` pipeline below)

## Usage

### Via Makefile

```bash
make ELF=path/to/test1.out [NAME=name]          # full pipeline: disasm + profiler
make disasm ELF=path/to/test1.out [NAME=name]   # just the disassembly step
make profiler ASM=out/test1.asm [NAME=name]     # just the profiling step
make check                                      # check disasm.sh's required tools and Python version
make clean                                      # remove generated files from out/
make help                                       # describe targets and variables
```

`NAME` is optional and shared across both steps (`-o` for `isa_profiler.py`, second argument to `disasm.sh`); omit it and each tool falls back to its own default naming. `PROFILER_FLAGS` (default `-isa-csv`) controls which `isa_profiler.py` flags run, e.g. `make ELF=... PROFILER_FLAGS="-csv -isa-csv"`.

`disasm` and `all` only forward `ELF`/`NAME` to `disasm.sh` — there's no `DISASM_FLAGS` passthrough. `disasm.sh`'s own flags (`-h`/`--help`, `-v`/`--version`, `-c`/`--check`) are run directly instead; `make check` runs `disasm.sh --check` and then also verifies `$(PYTHON)` (default `python3`) is 3.10+, since `isa_profiler.py` requires it.

`DEST`, if set, also copies whatever files a target newly wrote to `out/` into that directory (created if missing), e.g. `make ELF=... DEST=/tmp/results`. Both tools still always write to `out/` first — `DEST` is an additional copy, not a redirect, since the underlying tools aren't configurable that way.

### Directly

```bash
src/disasm.sh <elf_file> [output_name]  # or -h/--help, -v/--version, -c/--check
python src/isa_profiler.py <input_file> [options]
```

#### isa_profiler.py options

| Flag | Description |
| --- | --- |
| `input_file` | Path to the input assembly/disassembly file (required) |
| `-o`, `--output-name` | Base name used for generated output files |
| `-csv` | Save raw instruction counts to a CSV file |
| `-isa-csv` | Save per-ISA-extension instruction counts to a CSV file |
| `-e`, `--extract` | One or more instruction mnemonics to extract to `<output_name>.asm` (or `extraction.asm` if `-o` is not given) |
| `-es`, `--extract-set` | One or more ISA sets/subsets to extract (e.g. `rv32I`, `rv32I_loads`, `rv32A`), combinable with `-e`; case-insensitive, matches an exact set/subset or a whole set's subsets by prefix |
| `-list-sets`, `--list-sets` | Print the known ISA sets/subsets and exit (`input_file` not required) |
| `--version` | Print the tool's version and exit (`input_file` not required) |

### Examples

Full pipeline from an ELF file, using the default naming:

```bash
make ELF=path/to/test1.out
```

Count instructions and print a summary:

```bash
python src/isa_profiler.py out/test1.asm
```

Save raw instruction counts to `out/counts.csv`:

```bash
python src/isa_profiler.py out/test1.asm -o counts -csv
```

Save ISA extension breakdown to `out/report_isa_sets.csv`:

```bash
python src/isa_profiler.py out/test1.asm -o report -isa-csv
```

Extract all `lw` and `sw` instructions to `out/extraction.asm`:

```bash
python src/isa_profiler.py out/test1.asm -e lw sw
```

Extract every RV32I instruction (all of its subsets) plus the RV32A extension:

```bash
python src/isa_profiler.py out/test1.asm -es rv32I rv32A
```

Extract just the RV32I load instructions:

```bash
python src/isa_profiler.py out/test1.asm -es rv32I_loads
```

## Input format

`isa_profiler.py` expects objdump-style disassembly lines, where each line is whitespace-separated as:

``` asm
<address>: <opcode (hex)> <instruction> <operands...>
```

For example:

``` asm
   1000: 00000513              li a0,0
```

A line is only treated as an instruction if it has more than two whitespace-separated fields and the opcode field (2nd column) is exactly 8 characters (a 32-bit hex opcode). Lines are skipped if the instruction field:

- consists entirely of hex digits,
- starts with `.`, `<`, `(`, `@`, or `)`, or
- ends with `.`

`disasm.sh` produces disassembly in this format automatically.

## Output files

All generated files are written to `out/`.

- **`<output_name>.asm`** (or `<elf_basename>.asm` by default) — readable disassembly, from `disasm.sh`.
- **`<output_name>.hexdump.asm`** — byte-per-line hex dump for use with Verilog's `$readmemh`, from `disasm.sh`.
- **`<output_name>.csv`** (or `instructions.csv` by default) — two rows: instruction mnemonics and their counts, written when `-csv` is passed to `isa_profiler.py`.
- **`<output_name>_isa_sets.csv`** (or `isa_sets.csv` by default) — two rows: ISA extension/unknown-instruction names and their counts, written when `-isa-csv` is passed. Instructions that don't match a known ISA set are listed individually under an `unknown_` prefix.
- **`<output_name>.asm`** (or `extraction.asm` by default) — lines containing the requested instructions (via `-e`/`--extract`), one per line.

## License

[MIT](LICENSE)
