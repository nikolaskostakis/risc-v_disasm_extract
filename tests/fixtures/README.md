# fixtures/

Input files for `test_isa_profiler.py`. Both are `objdump`-style disassembly text, the same format `isa_profiler.py` parses in normal use — see the [top-level README](../../README.md#input-format) for the format spec.

## basic.asm

Small and hand-built, purely to hit `get_asmInstr()`'s parsing edge cases one at a time. Not meant to look like a real program — line order follows the edge case, not any logical flow.

| Line(s) | Content | Why it's here |
| --- | --- | --- |
| 1-6 | `objdump` header/section banner | Realistic noise around the instructions — also incidentally exercises that header lines (e.g. `file format elf32-littleriscv`, which has `"file"` as a coincidental 4-character 2nd column) are never mistaken for an instruction. |
| 8-16 | Nine valid instructions, one from several different ISA sets (`li`, `beqz`, `add`, `lw`, `ecall`, `mul`, `amoadd.w`, `flw`, `srli`) | The baseline: everything here must be counted, each exactly once. |
| 16 | `srli a4,a5,0x1` (opcode `0017d713`) | Doubles as `TestExtractHex`'s known-opcode little-endian conversion check (`0017d713` → `13 d7 17 00`). |
| 17 | `1234 nop` — a mnemonic that's entirely hex digits | Must be filtered by the "looks like raw hex data" check. |
| 18 | `.word 0x00000000` — an assembler directive | Not a real instruction (starts with `.`); must be skipped. |
| 19 | `foo. bar` — a made-up mnemonic ending in `.` | Exercises the trailing-dot filter. |
| 20 | A second `li`, with a compressed (4-hex-digit) opcode (`4501`) | A *valid* width (16-bit RVC), so it must still be counted — but under its own resolved `c.li` name, kept separate from the 32-bit `li` on line 8 (see `resolve_compressed_mnemonic()`). Also backs `TestExtractHex.test_compressed_opcode_extracted_as_two_bytes` (extracts as 2 real bytes, `01 45`, not padded to 4). |
| 21 | `garbage a0,0` with a 6-hex-digit opcode | Neither a 32-bit (8-digit) nor compressed (4-digit) width, and not something objdump would ever actually produce — must be rejected. |

The `add` on line 10 does double duty: it's a normal valid instruction, but `add` also happens to consist entirely of hex-digit characters (`a`, `d`, `d`) — the same shape as the `1234` on line 17 that's supposed to be filtered out. It regression-tests that `HEX_MNEMONICS` exempts real mnemonics from the hex-digit filter, rather than needing a separate fixture line.

## complex.asm

Broader integration coverage: every ISA extension the tool supports, in one file, run through the full parse → categorize pipeline (not just `get_asmInstr()` in isolation). Unlike `basic.asm`, every opcode/mnemonic pair here is **genuine `objdump` output** — assembled and disassembled with the real `riscv32-unknown-elf` toolchain, not hand-typed — so nothing here is a guess about how an instruction actually gets disassembled.

It's two real disassembly dumps concatenated (one scalar, one vector — see below for why), plus one hand-added line at the very end.

| Block | Extensions covered | Notable entries |
| --- | --- | --- |
| Lines 8-44 (scalar) | RV32I (all subsets), RV32M, RV32A, RV32F, RV32D, compressed (RVC) forms of several base instructions, Zba, Zbb, Zbc, Zbs, Zicond, Zfh, Zicsr, Zifencei, Zicntr | `and` appears 3 times: twice as a normal 32-bit instruction (lines 9-10) and once compressed (line 31) — objdump prints the compressed one the same as the 32-bit ones (`and`), but it resolves to `c.and` and counts separately, not merged. `mul` appears twice (lines 19-20). Lines 28-33 are the compressed block: `li`, `ret` (compressed `jr`), `beqz`, `and`, `lw`, and `sw a1,4(sp)` — the last one exercises `resolve_compressed_mnemonic()`'s sp-base disambiguation, resolving to `c.swsp` rather than `c.sw` since the base register is literally `sp`. |
| Lines 50-55 (vector) | RV32V (config, loads, stores, integer) | Assembled separately (`-march=rv32imv`) since combining vector with everything else in one `-march` string isn't necessary and keeps each snippet's purpose clear. |
| Line 56 | — | Hand-added, not real `objdump` output: `reserved0`, a mnemonic that matches no ISA table, to exercise `save_instuction_sets()`'s "unknown" bucket. Format-valid (8-hex-digit opcode, not all-hex mnemonic) so it parses like any other instruction line up to the categorization step. |

`rv32C` gets populated by this fixture's six compressed instances, each resolved to its real `c.*` name before categorization — see `resolve_compressed_mnemonic()` in `isa_profiler.py` for how objdump's displayed alias (e.g. `li`, or `ret` for `c.jr ra`) maps back to it, and `TestResolveCompressedMnemonic` for dedicated coverage of the trickier cases (`c.addi`/`c.addi16sp`/`c.addi4spn`, `c.lw`/`c.lwsp`) that this fixture alone doesn't exercise.

### Regenerating or extending it

The scalar and vector blocks came from assembling and disassembling two small `.s` files with the real toolchain:

```bash
riscv32-unknown-elf-as -march=rv32imafdc_zba_zbb_zbc_zbs_zicond_zfh_zmmul_zicsr_zifencei_zicntr -mabi=ilp32 wide.s -o wide.o
riscv32-unknown-elf-objdump -d wide.o

riscv32-unknown-elf-as -march=rv32imv -mabi=ilp32 vec.s -o vec.o
riscv32-unknown-elf-objdump -d vec.o
```

To add coverage for a new extension later (e.g. a future `isa_rv64`), write a small `.s` snippet exercising it, assemble with `-march` including that extension, disassemble, and splice the real output lines in — then update `EXPECTED_COMPLEX_INSTRUCTIONS` and `TestComplexFixture` in `test_isa_profiler.py` to match.

---

See [tests/README.md](../README.md) for how to run the suite and what each test class checks.
