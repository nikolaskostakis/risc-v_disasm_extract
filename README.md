# asm_parser

A Python command-line tool for parsing RISC-V assembly (disassembly) files. It counts instruction occurrences, categorizes them by RISC-V ISA extension (RV32I, RV32M, RV32A, RV32F, RV32D, RV32C, RV32B, Zicsr, Zifencei, Zicntr), and can extract lines containing specific instructions to a separate file.

## Requirements

- Python 3.10+ (uses `str | None` type hints)
- No third-party dependencies — only the Python standard library (`csv`, `logging`, `argparse`, `string`, `io`)

## Input format

The parser expects objdump-style disassembly lines, where each line is whitespace-separated as:

```
<address>: <opcode (hex)> <instruction> <operands...>
```

For example:

```
   1000:	00000513          	li	a0,0
```

A line is only treated as an instruction if it has more than two whitespace-separated fields and the opcode field (2nd column) is exactly 8 characters (a 32-bit hex opcode). Lines are skipped if the instruction field:
- consists entirely of hex digits,
- starts with `.`, `<`, `(`, `@`, or `)`, or
- ends with `.`

## Usage

```bash
python asm_parser.py <input_file> [options]
```

### Options

| Flag | Description |
|---|---|
| `input_file` | Path to the input assembly/disassembly file (required) |
| `-o`, `--output-name` | Base name used for generated output files |
| `-csv` | Save raw instruction counts to a CSV file |
| `-isa-csv` | Save per-ISA-extension instruction counts to a CSV file |
| `-e`, `--extract` | One or more instruction mnemonics to extract to `<output_name>.asm` (or `extraction.asm` if `-o` is not given) |

### Examples

Count instructions and print a summary:

```bash
python asm_parser.py program.dump
```

Save raw instruction counts to `counts.csv`:

```bash
python asm_parser.py program.dump -o counts -csv
```

Save ISA extension breakdown to `report_isa_sets.csv`:

```bash
python asm_parser.py program.dump -o report -isa-csv
```

Extract all `lw` and `sw` instructions to `extraction.asm`:

```bash
python asm_parser.py program.dump -e lw sw
```

Extract all `lw` and `sw` instructions to `report.asm`:

```bash
python asm_parser.py program.dump -o report -e lw sw
```

## Output files

- **`<output_name>.csv`** (or `instructions.csv` by default) — two rows: instruction mnemonics and their counts, written when `-csv` is passed.
- **`<output_name>_isa_sets.csv`** (or `isa_sets.csv` by default) — two rows: ISA extension/unknown-instruction names and their counts, written when `-isa-csv` is passed. Instructions that don't match a known ISA set are listed individually under an `unknown_` prefix.
- **`<output_name>.asm`** (or `extraction.asm` by default) — lines containing the requested instructions (via `-e`/`--extract`), one per line.
