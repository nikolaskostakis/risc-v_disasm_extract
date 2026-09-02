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
| `-eh`, `--extract-hex` | With `-e`/`-es`: also write a hexdump of the extracted instructions, one per line, little-endian (4 bytes for a 32-bit instruction, 2 for a compressed one). Warns and does nothing if used without `-e`/`-es` |
| `-list-sets` | Print the known ISA sets/subsets and exit; `input_file` not required |
| `-list-instr` | Print the instruction mnemonics in the given set(s)/subset(s), one per line, and exit; `input_file` not required |
| `-v`, `--version` | Print the tool's version and exit; `input_file` not required |

## isa_rv32.py

Not a standalone tool — the raw per-category instruction tables (and `HEX_MNEMONICS`/`ISA_UMBRELLAS`) that `isa_profiler.py`'s `get_isa_lists()` assembles into the `{name: instructions}` mapping defining which mnemonics belong to which supported RISC-V ISA set/subset. Kept separate so the instruction-list data isn't buried in the parsing/profiling logic; the assembly logic itself (`get_isa_lists()`) stays in `isa_profiler.py`. To support a new extension, add its instruction list here as its own module-level constant and register it in `get_isa_lists()`. Named `isa_rv32` (not `isa_sets`) so an `isa_rv64` module could sit alongside it if 64-bit support is ever added.

Names are case-insensitive. A whole set (e.g. `rv32I`) expands to all of its subsets; a subset (e.g. `rv32I_loads`) matches just that category. `rv32I`/`rv32M`'s subsets are our own functional groupings (not official RISC-V names), matched by shared name prefix; `rv32B`'s members are real, independently-named, ratified sub-extensions (`Zba`/`Zbb`/`Zbc`/`Zbs`), so each also works on its own (e.g. `-es Zba`), not just as part of the `rv32B` umbrella (see `ISA_UMBRELLAS`). Used by both `-isa-csv` categorization and `-es`/`--extract-set`. Run `isa_profiler.py -list-sets` to print this list from the CLI directly — whole sets are printed with their subsets tab-indented beneath them.

| Set | Subsets |
| --- | --- |
| `rv32I` | `rv32I_logic`, `rv32I_addsub`, `rv32I_shifts`, `rv32I_comparisons`, `rv32I_jumps`, `rv32I_branches`, `rv32I_loads`, `rv32I_stores`, `rv32I_other` |
| `rv32M` | `rv32M_mul`, `rv32M_div`, `rv32M_rem` |
| `rv32A` | — |
| `rv32F` | — |
| `rv32D` | — |
| `rv32C` | — (objdump always disassembles a compressed instruction using its base/pseudo-op alias, e.g. `c.li` prints as `li`, so `isa_profiler.py` resolves it back to its real `c.*` name before counting — see `resolve_compressed_mnemonic()`'s comment in `isa_profiler.py`) |
| `rv32B` | `zba`, `zbb`, `zbc`, `zbs` (the 4 ratified Bitmanip sub-extensions — each also usable standalone, e.g. `-es zbb`) |
| `zmmul` | — (the multiply-only subset of `rv32M`; same instructions as `rv32M_mul`, so it's intentionally excluded from `-isa-csv` categorization — see `rv32M_mul` for that breakdown) |
| `zicond` | — |
| `zfh` | — |
| `zicsr` | — |
| `zifencei` | — |
| `zicntr` | — |
| `rv32V` | `rv32V_config`, `rv32V_loads`, `rv32V_stores`, `rv32V_integer`, `rv32V_fixed_point`, `rv32V_float`, `rv32V_reduction`, `rv32V_mask`, `rv32V_permute`, `rv32V_whole_reg` (segment load/store instructions are not included) |

---

All generated files are written to `out/`. See the [top-level README](../README.md) for the full input format and usage examples.
