# risc-v_disasm_extract

A toolset for working with RISC-V disassembly: `disasm.sh` turns a compiled ELF into a readable disassembly and a hex dump, and `isa_profiler.py` counts instruction occurrences and categorizes them by RISC-V ISA extension — the RV32I/M/A/F/D/Q base extensions, RV32B and RV32C's sub-extensions, RV32V, and a range of smaller Z-extensions (bit manipulation, scalar crypto, half/quad-precision and BF16 float, integer-register float, hardware performance counters, and more). See [src/README.md](src/README.md) for the full, current list. `isa_profiler.py` can also extract lines matching specific instructions, or whole ISA sets/subsets, to a separate file.

## Layout

- [`src/`](src/) — `disasm.sh`, `isa_profiler.py`, and `isa_rv32.py` (see [src/README.md](src/README.md) for details on each)
- [`out/`](out/) — generated files, created automatically if missing
- [`tests/`](tests/) — `isa_profiler.py`'s test suite (`python3 -m unittest discover -s tests` or `make test`; see [tests/README.md](tests/README.md) for what each test covers)

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
make test                                       # run isa_profiler.py's test suite
make clean                                      # remove generated files from out/
make help                                       # describe targets and variables
```

`NAME` is optional and shared across both steps (`-o` for `isa_profiler.py`, second argument to `disasm.sh`); omit it and each tool falls back to its own default naming. `PROFILER_FLAGS` (default `-isa-csv`) controls which `isa_profiler.py` flags run, e.g. `make ELF=... PROFILER_FLAGS="-csv -isa-csv"`. `DISASM_FLAGS` (default none) similarly controls which `disasm.sh` flags run alongside `ELF`/`NAME`, e.g. `make ELF=... DISASM_FLAGS="-endian big"`.

`disasm.sh`'s own mode flags (`-h`/`--help`, `-v`/`--version`, `-c`/`--check`) aren't part of `DISASM_FLAGS` — they're run directly instead, e.g. `src/disasm.sh --check`; `make check` runs that and then also verifies `$(PYTHON)` (default `python3`) is 3.10+, since `isa_profiler.py` requires it.

`DEST`, if set, also copies whatever files a target newly wrote to `out/` into that directory (created if missing), e.g. `make ELF=... DEST=/tmp/results`. Both tools still always write to `out/` first — `DEST` is an additional copy, not a redirect, since the underlying tools aren't configurable that way.

### Directly

```bash
src/disasm.sh <elf_file> [output_name] [-endian little|big]  # or -h/--help, -v/--version, -c/--check
python src/isa_profiler.py <input_file> [options]  # or -h/--help, -v/--version
```

#### isa_profiler.py options

| Flag | Description |
| --- | --- |
| `input_file` | Path to the input assembly/disassembly file (required) |
| `-h`, `--help` | Show usage and exit |
| `-o`, `--output-name` | Base name used for generated output files |
| `-csv` | Save raw instruction counts to a CSV file |
| `-isa-csv` | Save per-ISA-extension instruction counts to a CSV file |
| `-e`, `--extract` | One or more instruction mnemonics to extract to `<output_name>.asm` (or `extraction.asm` if `-o` is not given) |
| `-es`, `--extract-set` | One or more ISA sets/subsets to extract (e.g. `rv32I`, `rv32I_loads`, `rv32A`), combinable with `-e`; case-insensitive, matches an exact set/subset or a whole set's subsets by prefix |
| `-eh`, `--extract-hex` | With `-e`/`-es`: also write `<output_name>.mem`, one extracted instruction's raw bytes per line (4 bytes for a 32-bit instruction, 2 for a compressed one), in the same order as the `.asm` extraction. Warns and does nothing if used without `-e`/`-es` |
| `-endian` | Byte order for `-eh`'s hexdump: `little` (default, real RV32 memory order) or `big` (objdump's own printed byte order, unreversed). Always correct either way, even for a compressed instruction, since each opcode's real width is already known. Warns and does nothing without `-eh` |
| `-list-sets` | Print the known ISA sets/subsets and exit, with subsets tab-indented beneath their whole set (`input_file` not required) |
| `-list-instr` | One or more ISA sets/subsets; print the instruction mnemonics they contain (one per line) and exit — same resolution as `-es` (whole-set expansion, case-insensitive, deduplicated), but a static lookup, not filtered by any file (`input_file` not required) |
| `-list-core` | One or more CPU core names (e.g. `cv32e40p`, `cv32e40x`); print the RISC-V ISA extensions each is known to support and exit — reference data from each core's own user manual, not derived from disassembly (`input_file` not required) |
| `-v`, `--version` | Print the tool's version and exit (`input_file` not required) |

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

Also write their raw bytes (little-endian, the default) to `out/extraction.mem`:

```bash
python src/isa_profiler.py out/test1.asm -e lw sw -eh
```

Same, but big-endian:

```bash
python src/isa_profiler.py out/test1.asm -e lw sw -eh -endian big
```

Extract every RV32I instruction (all of its subsets) plus the RV32A extension:

```bash
python src/isa_profiler.py out/test1.asm -es rv32I rv32A
```

Extract just the RV32I load instructions:

```bash
python src/isa_profiler.py out/test1.asm -es rv32I_loads
```

List which instructions belong to `rv32M` and `rv32I_shifts` (no input file needed):

```bash
python src/isa_profiler.py -list-instr rv32M rv32I_shifts
```

Check which ISA extensions a specific core is known to support (no input file needed):

```bash
python src/isa_profiler.py -list-core cv32e40x
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

A line is only treated as an instruction if it has more than two whitespace-separated fields and the opcode field (2nd column) is exactly 8 characters (a 32-bit opcode) or 4 characters (a 16-bit compressed/RVC opcode). objdump always disassembles a compressed instruction using its base/pseudo-op mnemonic (e.g. `c.li` prints as `li`), never the literal `c.li` form, so it's resolved back to its real `c.*` name before counting — kept separate from a 32-bit instruction that happens to print the same way. A handful of these aliases are ambiguous by mnemonic text alone (e.g. `addi` covers `c.addi`, `c.addi16sp`, and `c.addi4spn`) and are disambiguated using the operand text too; see `resolve_compressed_mnemonic()` in `isa_profiler.py`. Lines are skipped if the instruction field:

- consists entirely of hex digits,
- starts with `.`, `<`, `(`, `@`, or `)`, or
- ends with `.`

`disasm.sh` produces disassembly in this format automatically.

## Output files

All generated files are written to `out/`.

- **`<output_name>.asm`** (or `<elf_basename>.asm` by default) — readable disassembly, from `disasm.sh`.
- **`<output_name>.mem`** — byte-per-line hex dump for use with Verilog's `$readmemh`, from `disasm.sh`. Little-endian by default (the real RV32 memory layout); `-endian big` does a uniform 4-byte swap instead — only meaningful for a binary with no compressed (RVC) instructions, since the swap has no notion of real instruction boundaries. A warning is printed if the ELF reports the C/Zca extension.
- **`<output_name>.csv`** (or `instructions.csv` by default) — two rows: instruction mnemonics and their counts, written when `-csv` is passed to `isa_profiler.py`.
- **`<output_name>_isa_sets.csv`** (or `isa_sets.csv` by default) — two rows: ISA extension/unknown-instruction names and their counts, written when `-isa-csv` is passed. Instructions that don't match a known ISA set are listed individually under an `unknown_` prefix.
- **`<output_name>.asm`** (or `extraction.asm` by default) — lines containing the requested instructions (via `-e`/`--extract`), one per line.
- **`<output_name>.mem`** (or `extraction.mem` by default) — one extracted instruction's raw bytes per line (4 bytes for a 32-bit instruction, 2 for a 16-bit compressed one), written when `-eh`/`--extract-hex` is passed alongside `-e`/`-es`. Little-endian by default; `-endian big` writes objdump's own printed byte order instead, unreversed — always correct here, unlike `disasm.sh`'s version, since each opcode's real width is already known. Note this shares its default naming pattern with `disasm.sh`'s own `<output_name>.mem` above — use distinct `-o`/`NAME` values (or separate `DEST` folders) to avoid overwriting one with the other.

## License

[MIT](LICENSE)
