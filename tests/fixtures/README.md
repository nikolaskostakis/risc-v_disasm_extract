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

It's three real disassembly dumps concatenated (scalar, vector, and a Zcmp/Zcmt block kept separate for a real ISA-encoding reason — see below), plus one hand-added line at the very end.

| Block | Extensions covered | Notable entries |
| --- | --- | --- |
| Lines 8-57 (scalar) | RV32I (all subsets), RV32M, RV32A, RV32F, RV32D, RV32Q, compressed (RVC) forms of several base instructions, Zba, Zbb, Zbc, Zbs, Zbkb, Zbkx, Zicond, Zfh, Zfa, Zfinx, Zdinx, Zqinx, Zhinx, Zfbfmin, Zicsr, Zifencei, Zicntr, Zihpm, Zca, Zcf, Zcd, Zcb | `and` appears 3 times: twice as a normal 32-bit instruction (lines 9-10) and once compressed (line 31) — objdump prints the compressed one the same as the 32-bit ones (`and`), but it resolves to `c.and` and counts separately, not merged. `mul` appears twice (lines 19-20). Lines 28-33 are the Zca compressed block: `li`, `ret` (compressed `jr`), `beqz`, `and`, `lw`, and `sw a1,4(sp)` — the last one exercises `resolve_compressed_mnemonic()`'s sp-base disambiguation, resolving to `c.swsp` rather than `c.sw` since the base register is literally `sp`. Line 45, `csrr a0,hpmcounter3`, exercises `resolve_zihpm_mnemonic()` — the same displayed text a `csrr` of any other CSR would produce, resolved to `rdhpmcounter3` only because the operand names a Zihpm counter. Lines 46-48 are Zcf/Zcd/Zcb: `flw`/`fld` (general base, resolving to plain `c.flw`/`c.fld`, not the `sp`-relative forms) and `zext.b` (Zcb, aliases to the same pseudo-op `rv32I_logic`'s 32-bit `zext.b` uses). Lines 49-50, `pack`/`xperm4`, are unique to Zbkb/Zbkx respectively — neither is part of the Zbb/Zbc overlap those extensions otherwise share. Line 51, `fadd.q`, gives RV32Q real coverage, same family as the `fadd.s`/`fadd.d`/`fadd.h` already in this block. Line 52, `fminm.s`, gives Zfa real coverage (Zfhmin isn't exercised here — same reasoning as `zmmul`/`zbkb`/`zbkc`, it's a pure subset of `zfh`, already covered structurally). Lines 53-56 repeat `fadd.s`/`fadd.d`/`fadd.q`/`fadd.h` with integer register operands (`a0,a1,a2` instead of `fa0,fa1,fa2`) — objdump prints identical mnemonic text to the float-register versions above, so these exercise `resolve_inx_mnemonic()`'s operand-based disambiguation into `fadd.s.inx`/`fadd.d.inx`/`fadd.q.inx`/`fadd.h.inx` (Zfinx/Zdinx/Zqinx/Zhinx; Zhinxmin isn't separately exercised, same reasoning as Zfhmin). Line 57, `fcvt.bf16.s`, gives Zfbfmin real coverage. |
| Lines 63-72 (vector) | RV32V (config, loads, stores, integer), Zvfbfmin, Zvfbfwma | Assembled separately (`-march=rv32imv_zvfbfmin_zvfbfwma`) since combining vector with everything else in one `-march` string isn't necessary and keeps each snippet's purpose clear. A second `vsetvli` switches to `e16` before the BF16 lines, matching how a real BF16 sequence would reconfigure `vtype` — though for a pure disassembly fixture this is just realism, not a requirement (the mnemonic text doesn't depend on the preceding `vsetvli`). |
| Lines 79-81 (Zcmp/Zcmt) | Zcmp, Zcmt | Its own block for a real reason, not just tidiness: Zcmp/Zcmt's encoding is incompatible with Zcd/D (a genuine RISC-V ISA constraint — a core can't implement both), so this snippet had to be assembled with a different `-march` than the scalar block above, which uses D. `cm.push {ra},-16` and `cm.jt 5` both print their real, complete mnemonic directly — no alias to resolve, unlike everything in the scalar block's compressed sections. |
| Line 82 | — | Hand-added, not real `objdump` output: `reserved0`, a mnemonic that matches no ISA table, to exercise `save_instuction_sets()`'s "unknown" bucket. Format-valid (8-hex-digit opcode, not all-hex mnemonic) so it parses like any other instruction line up to the categorization step. |

A few extensions are populated indirectly rather than by a mnemonic that matches their table 1:1:

- **`zca`** comes from this fixture's six Zca compressed instances, each resolved to its real `c.*` name before categorization — see `resolve_compressed_mnemonic()` in `isa_profiler.py` for how objdump's displayed alias (e.g. `li`, or `ret` for `c.jr ra`) maps back to it, and `TestResolveCompressedMnemonic` for dedicated coverage of the trickier cases (`c.addi`/`c.addi16sp`/`c.addi4spn`, `c.lw`/`c.lwsp`, and the float loads/stores) that this fixture alone doesn't exercise.
- **`zihpm`** comes from the single `hpmcounter3` read (resolved via `resolve_zihpm_mnemonic()`) — see `TestResolveZihpmMnemonic` for coverage of the other CSR pseudo-op forms and CSR names this fixture doesn't exercise.
- **`rv32C`** itself is a pure umbrella over `zca`/`zcf`/`zcd` (see `ISA_UMBRELLAS`), so it never appears as a key in `-isa-csv` output — only its three real members do. `zce` is a second, separate umbrella over `zca`/`zcb`/`zcmp`/`zcmt` (not `zcf`/`zcd`), also never a key on its own.
- **`zbkb`/`zbkx`** are exercised only by `pack`/`xperm4`, their *unique* instructions — the 7 they intentionally share with Zbb/Zbc (`andn`, `rol`, `rev8`, ...) aren't repeated here since `zbb`/`zbc` already cover them structurally via `KNOWN_OVERLAPS`, the same way `zmmul` doesn't get its own fixture line either.
- **`zfinx`/`zdinx`/`zqinx`/`zhinx`** each get populated by exactly one instruction, resolved via `resolve_inx_mnemonic()` — see `TestResolveInxMnemonic` for dedicated coverage of the trickier cases (a mixed-operand instruction like `fcvt.w.s`, and confirming loads/stores/bit-moves are never relabeled) that this fixture alone doesn't exercise.
- **`zvfbfmin`/`zvfbfwma`** are populated by the vector block's three BF16 lines (`vfwcvtbf16.f.f.v`, `vfncvtbf16.f.f.w`, `vfwmaccbf16.vv`) — unlike `zfinx`'s family, their mnemonics carry `bf16` directly, so they need no operand-based resolver, just their own table entries.

### Regenerating or extending it

The scalar, vector, and Zcmp/Zcmt blocks came from assembling and disassembling small `.s` files with the real toolchain:

```bash
riscv32-unknown-elf-as -march=rv32imafdcq_zba_zbb_zbc_zbs_zbkb_zbkx_zicond_zfh_zfa_zfbfmin_zmmul_zicsr_zifencei_zicntr_zca_zcf_zcd_zcb -mabi=ilp32 wide.s -o wide.o
riscv32-unknown-elf-objdump -d wide.o

riscv32-unknown-elf-as -march=rv32imv_zvfbfmin_zvfbfwma -mabi=ilp32 vec.s -o vec.o
riscv32-unknown-elf-objdump -d vec.o

riscv32-unknown-elf-as -march=rv32izcmp_zcmt zcmp.s -o zcmp.o
riscv32-unknown-elf-objdump -d zcmp.o
```

The four `.inx` lines came from **separate** invocations, each with its own `-march`, then spliced by hand into the scalar block above — `Zfinx`/`Zdinx`/`Zqinx`/`Zhinx` each genuinely conflict with plain `F`/`D`/`Q`/`Zfh` at assembly time (verified: `-march=..._f..._zfinx` is a real assembler error, "`zfinx` is conflict with the `f/d/q/zfh/zfhmin` extension"), so there's no single `-march` string that could produce both the float-register and integer-register forms of `fadd.s` together:

```bash
riscv32-unknown-elf-as -march=rv32i_zfinx inx_add.s -o inx_add.o   # fadd.s a0,a1,a2
riscv32-unknown-elf-as -march=rv32i_zdinx inx_add2.s -o inx_add2.o # fadd.d a0,a2,a4
riscv32-unknown-elf-as -march=rv32izqinx_zdinx inx_add3.s -o inx_add3.o # fadd.q a0,a2,a4
riscv32-unknown-elf-as -march=rv32i_zhinx inx_add4.s -o inx_add4.o # fadd.h a0,a1,a2
```

Zcmp/Zcmt need their own `.s` file and `-march` (without `d`/`zcd`) because of the encoding conflict noted above — don't try to fold them into the scalar block's march string.

To add coverage for a new extension later (e.g. a future `isa_rv64`), write a small `.s` snippet exercising it, assemble with `-march` including that extension, disassemble, and splice the real output lines in — then update `EXPECTED_COMPLEX_INSTRUCTIONS` and `TestComplexFixture` in `test_isa_profiler.py` to match.

---

See [tests/README.md](../README.md) for how to run the suite and what each test class checks.
