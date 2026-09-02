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
| `TestGetIsaLists` | Structural invariants of `get_isa_lists()`'s output: no whole-set name (e.g. `rv32I`) contains an underscore itself (both `get_setInstr()` and `print_isa_lists()` rely on splitting subset keys on the first underscore), and no instruction mnemonic appears in two different sets unless the overlap is explicitly documented as intentional (e.g. `zmmul` == `rv32M_mul`, a real spec-defined relationship — see `KNOWN_OVERLAPS`). |
| `TestGetSetInstr` | `get_setInstr()`'s name-resolution logic: exact subset matches, a whole set expanding to the union of all its subsets (checked separately for `rv32I` and the larger `rv32V`), case-insensitivity, deduplication when a whole set and one of its own subsets are both requested, an unmatched name returning empty rather than erroring, and the `ISA_UMBRELLAS` mechanism (`rv32B` expanding to `Zba`/`Zbb`/`Zbc`/`Zbs`, and each of those also working standalone by its own official name). |
| `TestExtractHex` | `extractHex()`'s `.mem` output: line count matches `extractInstr()`'s `.asm` output one-to-one, a known 32-bit opcode converts to the correct little-endian byte order, and a compressed opcode extracts as its real 2 bytes rather than being padded/truncated to 4. |
| `TestResolveCompressedMnemonic` | `resolve_compressed_mnemonic()`'s disambiguation rules directly: the `ret` → `c.jr` alias, the three-way `addi` → `c.addi`/`c.addi16sp`/`c.addi4spn` split, the `lw`/`sw` → plain vs `*sp` split, and that every resolved name actually exists in `isa_rv32.rv32C` (so nothing silently falls into `unknown`). |
| `TestComplexFixture` | Integration-level coverage against `complex.asm`: every instruction is counted, 32-bit and compressed forms of the same mnemonic (`and`/`c.and`) are tracked separately rather than merged, every supported extension's category ends up non-zero after `save_instuction_sets()` (`rv32C` included, populated by the fixture's compressed instructions), and the unrecognized mnemonic lands in `unknown` by itself. |
| `TestCli` | End-to-end CLI behavior via `subprocess`: `-list-sets`/`-list-instr` work without an input file, `-list-instr` with no names errors, `-list-instr` prints the right instructions for a given set, an unmatched `-e` name warns instead of crashing, `-eh` without `-e`/`-es` warns and has no effect, `-isa-csv` against `complex.asm` runs clean and its output reflects a newer extension plus the unknown mnemonic, and `-v` prints the version. |

All test-generated output files are written to `out/` and cleaned up by each test (via the module's `cleanup()` helper) even on failure, so repeated runs don't leave stale files behind.

---

See the [top-level README](../README.md) for the tool itself, and [src/README.md](../src/README.md) for `isa_profiler.py`/`isa_rv32.py`/`disasm.sh` details.
