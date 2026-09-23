# tests/

`isa_profiler.py`'s test suite. Uses only the standard library (`unittest`), consistent with the project's zero-third-party-dependency design — no `pytest`.

## Running standalone

From the repo root:

```bash
python3 -m unittest discover -s tests
make test
```

Both are equivalent; `make test` just runs the same discovery command. To run a single class or test directly:

```bash
python3 -m unittest tests.test_isa_profiler.TestGetSetInstr
python3 -m unittest tests.test_isa_profiler.TestGetSetInstr.test_umbrella_expands_to_all_members
```

`test_isa_profiler.py` adds `src/` to `sys.path` itself (`sys.path.insert(0, str(SRC_DIR))`), so it doesn't matter whether it's invoked via discovery, `make test`, or run directly with `python3 tests/test_isa_profiler.py` — no `PYTHONPATH` setup needed.

## Fixtures

**`fixtures/basic.asm`** — a small, hand-built disassembly covering the parser's edge cases one at a time (hex-digit-only mnemonics, directives, malformed opcode widths, compressed opcodes, and so on).

**`fixtures/complex.asm`** — a broader, genuinely toolchain-assembled disassembly covering every ISA extension the tool supports in one file, for integration-level coverage across the full parse → categorize pipeline.

See [fixtures/README.md](fixtures/README.md) for a line-by-line breakdown of both, including how `complex.asm` was generated and how to extend it.

## What each test class covers

| Class | Covers |
| --- | --- |
| `TestGetAsmInstr` | `get_asmInstr()`'s parsing rules against `basic.asm`: valid instructions are counted correctly, hex-digit-only/directive/trailing-dot lines and malformed-width opcodes are skipped, a compressed (4-hex-digit) opcode resolves to its own `c.*` name and counts separately from its 32-bit counterpart, and `add` (a real mnemonic that happens to be all hex digits) is still counted — a regression test for a bug where it was indistinguishable from filtered-out raw hex data. |
| `TestGetIsaLists` | Structural invariants of `get_isa_lists()`'s output: no whole-set name (e.g. `rv32I`) contains an underscore itself (both `get_setInstr()` and `print_isa_lists()` rely on splitting subset keys on the first underscore), and no instruction mnemonic appears in two different sets unless the overlap is explicitly documented as intentional (e.g. `zmmul` == `rv32M_mul`, `zbkb`/`zbkc`'s real overlap with `zbb`/`zbc`, or `zfhmin`/`zfh` and `zhinxmin`/`zhinx`'s real subset relationships — see `KNOWN_OVERLAPS`). |
| `TestGetSetInstr` | `get_setInstr()`'s name-resolution logic: exact subset matches, a whole set expanding to the union of all its subsets (checked separately for `rv32I` and the larger `rv32V`), case-insensitivity, deduplication when a whole set and one of its own subsets are both requested, an unmatched name returning empty rather than erroring, and the `ISA_UMBRELLAS` mechanism (`rv32B` expanding to `Zba`/`Zbb`/`Zbc`/`Zbs`, each of those also working standalone by its own official name, and `zce` expanding to exactly `zca`/`zcb`/`zcmp`/`zcmt` — notably not `zcf`/`zcd`, unlike `rv32C`'s own umbrella). |
| `TestExtractHex` | `extractHex()`'s `.mem` output: line count matches `extractInstr()`'s `.asm` output one-to-one, a known 32-bit opcode converts to the correct little-endian byte order, and a compressed opcode extracts as its real 2 bytes rather than being padded/truncated to 4. |
| `TestResolveCompressedMnemonic` | `resolve_compressed_mnemonic()`'s disambiguation rules directly: the `ret` → `c.jr` alias, the three-way `addi` → `c.addi`/`c.addi16sp`/`c.addi4spn` split, the `lw`/`sw`/`flw`/`fsw`/`fld`/`fsd` → plain vs `*sp` split, `cm.*` (Zcmp/Zcmt) mnemonics passing through unchanged rather than getting double-prefixed, and that every resolved name actually exists in one of the Zca/Zcf/Zcd/Zcb/Zcmp/Zcmt tables (so nothing silently falls into `unknown`). |
| `TestResolveZihpmMnemonic` | `resolve_zihpm_mnemonic()`'s CSR-operand disambiguation directly: every CSR pseudo-op form (`csrr`/`csrrs`/`csrrsi`/`csrw`/...) resolves a `hpmcounter3`-`hpmcounter31`/`...h` operand to `rdhpmcounter<N>`/`...h` regardless of which operand position the CSR name is in, an unrelated CSR (e.g. `mstatus`) and out-of-range/malformed counter numbers are left unresolved, and every valid resolved name exists in `isa_rv32.zihpm`. |
| `TestResolveInxMnemonic` | `resolve_inx_mnemonic()`'s float-vs-integer-register disambiguation directly: an `f`-prefixed register operand leaves the mnemonic unchanged (real `F`/`D`/`Q`/`Zfh`), none present adds the `.inx` suffix (`Zfinx`/`Zdinx`/`Zqinx`/`Zhinx`), a mixed-operand instruction like `fcvt.w.s` is judged by its float source even though its destination is always an integer register either way, loads/stores/bit-moves (`flw`, `fmv.x.w`, ...) are never relabeled since they have no `inx` form at all, and every width resolves into its own correct table. |
| `TestComplexFixture` | Integration-level coverage against `complex.asm`: every instruction is counted, 32-bit and compressed forms of the same mnemonic (`and`/`c.and`) are tracked separately rather than merged, every supported extension's category ends up non-zero after `save_instuction_sets()` (`zca`/`zcf`/`zcd`/`zcb`/`zcmp`/`zcmt`/`zihpm`/`zbkb`/`zbkx`/`rv32Q`/`zfa`/`zfinx`/`zdinx`/`zqinx`/`zhinx`/`zfbfmin`/`zvfbfmin`/`zvfbfwma` included, populated by the fixture's compressed instructions, hpmcounter read, Zc-family block, the two Zbkb/Zbkx-unique instructions, `fadd.q`/`fminm.s`, four integer-register `fadd.*` variants, a `fcvt.bf16.s`, and the vector block's BF16 conversion/widening-macc instructions), and the unrecognized mnemonic lands in `unknown` by itself. |
| `TestCoreProfiles` | Schema checks on `isa_rv32.CORE_PROFILES` (the reference data behind `-list-core`): every profile has a `source` URL and a non-empty `base`/`always`, and every single-word extension name in a profile actually resolves via `get_setInstr()` (catches typos that would otherwise silently print a made-up extension name). |
| `TestCli` | End-to-end CLI behavior via `subprocess`: `-list-sets`/`-list-instr`/`-list-core` work without an input file, `-list-instr`/`-list-core` with no names errors, `-list-instr` prints the right instructions for a given set, `-list-core` prints known info for `cv32e40p`/`cv32e40x` and warns (not crashes) on an unknown core, an unmatched `-e` name warns instead of crashing, `-eh` without `-e`/`-es` warns and has no effect, `-isa-csv` against `complex.asm` runs clean and its output reflects a newer extension plus the unknown mnemonic, and `-v` prints the version. |

All test-generated output files are written to `out/` and cleaned up by each test (via the module's `cleanup()` helper) even on failure, so repeated runs don't leave stale files behind.

---

See the [top-level README](../README.md) for the tool itself, and [src/README.md](../src/README.md) for `isa_profiler.py`/`isa_rv32.py`/`disasm.sh` details.
