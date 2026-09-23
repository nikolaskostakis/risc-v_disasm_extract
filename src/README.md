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
| `-list-core` | Print the known ISA extensions for the given CPU core(s) and exit; `input_file` not required |
| `-v`, `--version` | Print the tool's version and exit; `input_file` not required |

## isa_rv32.py

Not a standalone tool — the raw per-category instruction tables (and `HEX_MNEMONICS`/`ISA_UMBRELLAS`) that `isa_profiler.py`'s `get_isa_lists()` assembles into the `{name: instructions}` mapping defining which mnemonics belong to which supported RISC-V ISA set/subset. Kept separate so the instruction-list data isn't buried in the parsing/profiling logic; the assembly logic itself (`get_isa_lists()`) stays in `isa_profiler.py`. To support a new extension, add its instruction list here as its own module-level constant and register it in `get_isa_lists()`. Named `isa_rv32` (not `isa_sets`) so an `isa_rv64` module could sit alongside it if 64-bit support is ever added.

Names are case-insensitive. A whole set (e.g. `rv32I`) expands to all of its subsets; a subset (e.g. `rv32I_loads`) matches just that category. `rv32I`/`rv32M`'s subsets are our own functional groupings (not official RISC-V names), matched by shared name prefix; `rv32B`/`rv32C`'s members are real, independently-named, ratified sub-extensions, so each also works on its own (e.g. `-es Zba`, `-es Zca`), not just as part of its umbrella (see `ISA_UMBRELLAS`). `Zcb`/`Zcmp`/`Zcmt` are separate Zc-family extensions a core may add on top of C, not part of `rv32C` itself, so they're standalone entries with no umbrella. Used by both `-isa-csv` categorization and `-es`/`--extract-set`. Run `isa_profiler.py -list-sets` to print this list from the CLI directly — whole sets are printed with their subsets tab-indented beneath them.

Compressed (RVC) instructions have no mnemonic of their own in real disassembly — objdump always prints the base/pseudo-op alias instead (e.g. `c.li` prints as `li`), so `isa_profiler.py` resolves the alias back to its real name before counting. Most resolve by simple prefixing; a handful are ambiguous by mnemonic text alone and need the operand text too. See `resolve_compressed_mnemonic()`'s comment in `isa_profiler.py` for exactly which ones and why.

| Set | Subsets |
| --- | --- |
| `rv32I` | `rv32I_logic`, `rv32I_addsub`, `rv32I_shifts`, `rv32I_comparisons`, `rv32I_jumps`, `rv32I_branches`, `rv32I_loads`, `rv32I_stores`, `rv32I_other` |
| `rv32M` | `rv32M_mul`, `rv32M_div`, `rv32M_rem` |
| `rv32A` | — |
| `rv32F` | — |
| `rv32D` | — |
| `rv32Q` | — (quad-precision, 128-bit float; same instruction shape as `rv32F`/`rv32D`, just `.q`-suffixed) |
| `rv32B` | `zba`, `zbb`, `zbc`, `zbs` (the 4 ratified Bitmanip sub-extensions — each also usable standalone, e.g. `-es zbb`) |
| `zbkb` | — (scalar-crypto Bitmanip: a curated Zbb subset for constant-time safety plus 5 unique instructions; the 7 shared instructions are excluded from `-isa-csv`'s `zbkb` count, same as `zmmul` — see `zbb` for that breakdown) |
| `zbkc` | — (scalar-crypto carry-less multiply: `clmul`/`clmulh` only, a subset of `zbc`; entirely excluded from `-isa-csv`'s `zbkc` count, same as `zmmul` — see `zbc`) |
| `zbkx` | — (scalar-crypto crossbar permutation; no overlap with anything else) |
| `rv32C` | `zca`, `zcf`, `zcd` (the Zc spec's formal definition of "C" — RV32-only `zcf`; each also usable standalone, e.g. `-es zca`) |
| `zcb` | — (extra compressed forms beyond `rv32C`; every one aliases to a mnemonic already in another table, e.g. `c.mul` prints as `mul`) |
| `zcmp` | — (compressed stack push/pop and register-pair moves; incompatible with `zcd`/`rv32D` in the real ISA encoding, so a target can't use both) |
| `zcmt` | — (compressed jump-table jump/call, via the `jvt` CSR) |
| `zce` | `zca`, `zcb`, `zcmp`, `zcmt` (the embedded-profile code-size-reduction bundle — a separate umbrella from `rv32C`, and notably doesn't include `zcf`/`zcd`) |
| `zmmul` | — (the multiply-only subset of `rv32M`; same instructions as `rv32M_mul`, so it's intentionally excluded from `-isa-csv` categorization — see `rv32M_mul` for that breakdown) |
| `zicond` | — |
| `zfh` | — |
| `zfhmin` | — (minimal half-precision: load/store/move/conversion only, no arithmetic; a real subset of `zfh`, same intentional-overlap pattern as `zmmul` — see `zfh` for that breakdown) |
| `zfa` | — (additional float instructions — load-immediate, min/max-number, round-to-integer, quiet compares — across every width this tool supports, H/S/D/Q, plus 3 RV32-specific instructions for D's register pairs) |
| `zfinx` | — (`F`'s instructions on the integer register file instead of a dedicated FP one — same mnemonics as `rv32F`, e.g. `fadd.s`, so `isa_profiler.py` resolves them apart by operand text: any `f`-prefixed register name means real `rv32F`, none means `zfinx` — see `resolve_inx_mnemonic()`'s comment in `isa_profiler.py`. Load/store and the direct GPR↔FPR bit-move instructions have no `zfinx` form at all — there's no separate register file to move between) |
| `zdinx` | — (`D`'s equivalent of `zfinx`) |
| `zqinx` | — (`Q`'s equivalent of `zfinx`) |
| `zhinx` | — (`Zfh`'s equivalent of `zfinx`) |
| `zhinxmin` | — (minimal `zhinx`: conversion only, no arithmetic; a real subset of `zhinx`, same intentional-overlap pattern as `zfhmin`/`zfh`) |
| `zfbfmin` | — (minimal BF16/brain-float16 support: conversion to/from single-precision only) |
| `zicsr` | — |
| `zifencei` | — |
| `zicntr` | — |
| `zihpm` | — (`hpmcounter3`-`hpmcounter31`/`hpmcounter3h`-`hpmcounter31h` have no mnemonic of their own — every access disassembles as a generic CSR pseudo-op like `csrr`, so `isa_profiler.py` reads the CSR name from the operand text to resolve it to `rdhpmcounter<N>`/`rdhpmcounter<N>h` — see `resolve_zihpm_mnemonic()`'s comment in `isa_profiler.py`) |
| `rv32V` | `rv32V_config`, `rv32V_loads`, `rv32V_stores`, `rv32V_integer`, `rv32V_fixed_point`, `rv32V_float`, `rv32V_reduction`, `rv32V_mask`, `rv32V_permute`, `rv32V_whole_reg` (segment load/store instructions are not included) |
| `zvfbfmin` | — (vector BF16/brain-float16 conversion only, no arithmetic — the vector equivalent of `zfbfmin`; both mnemonics carry `bf16` directly, e.g. `vfwcvtbf16.f.f.v`, so unlike `zfinx`/`zihpm` no resolver is needed) |
| `zvfbfwma` | — (single widening BF16 multiply-add, `vfwmaccbf16.vv`/`.vf`; verified standalone against the real assembler — doesn't require `zvfbfmin` to also be enabled) |

### Known CPU core profiles

`CORE_PROFILES` maps a few named CPU cores to the RISC-V ISA extensions they support, for `-list-core`. Unlike everything above, this isn't derived from real `objdump` output — a specific core's silicon/RTL configuration isn't something a generic toolchain can tell us — so each entry is sourced from that core's own user manual (cited in its `-list-core` output) instead. Currently covers `cv32e40p` and `cv32e40x` (both from OpenHW Group's CORE-V family); add a new core by adding an entry to `CORE_PROFILES` in `isa_rv32.py`, following the existing `base`/`always`/`optional`/`not_supported`/`custom` shape.

---

All generated files are written to `out/`. See the [top-level README](../README.md) for the full input format and usage examples.
