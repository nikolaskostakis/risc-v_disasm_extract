'''
Unit and CLI-level tests for isa_profiler.py.

Uses only the standard library (unittest), consistent with the project's
zero-third-party-dependency design. Run with:

    python3 -m unittest discover -s tests
    make test
'''
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SRC_DIR = TESTS_DIR.parent / "src"
OUT_DIR = TESTS_DIR.parent / "out"
FIXTURE = TESTS_DIR / "fixtures" / "basic.asm"
COMPLEX_FIXTURE = TESTS_DIR / "fixtures" / "complex.asm"

sys.path.insert(0, str(SRC_DIR))
import isa_profiler as ip  # noqa: E402

# every instruction basic.asm is expected to actually count (the hex-digit
# mnemonic, directive, and trailing-dot mnemonic lines must all be excluded;
# the second "li" has a 4-hex-digit compressed opcode and resolves to its
# real "c.li" name, kept separate from the 32-bit "li" -- see
# resolve_compressed_mnemonic())
EXPECTED_INSTRUCTIONS = {
    "li": 1,
    "c.li": 1,
    "beqz": 1,
    "add": 1,
    "lw": 1,
    "ecall": 1,
    "mul": 1,
    "amoadd.w": 1,
    "flw": 1,
    "srli": 1,
}

# complex.asm's expected counts. Every line is genuine objdump output
# (assembled and disassembled with the real riscv32-unknown-elf toolchain,
# not hand-typed), covering every ISA extension the tool supports -- RV32I
# (all subsets), RV32M, RV32A, RV32F, RV32D, RV32Q, compressed (RVC)
# forms of several base instructions, Zba/Zbb/Zbc/Zbs, Zbkb/Zbkx,
# Zicond, Zfh, Zfa, Zfinx/Zdinx/Zqinx/Zhinx, Zfbfmin, Zicsr, Zifencei,
# Zicntr, Zihpm, Zca/Zcf/Zcd/Zcb/Zcmp/Zcmt, RV32V, and Zvfbfmin/Zvfbfwma
# -- plus one deliberately unrecognized mnemonic ("reserved0") to
# exercise the "unknown" bucket. The compressed block resolves to
# c.li/c.jr (from "ret")/c.beqz/c.and/c.lw/c.swsp (from "sw a1,4(sp)",
# exercising the sp-base disambiguation) -- see
# resolve_compressed_mnemonic(). The hpmcounter3 read resolves to
# rdhpmcounter3 -- see resolve_zihpm_mnemonic(). Zcmp/Zcmt get their
# own block since they're encoding-incompatible with Zcd/D (a real ISA
# constraint, not a fixture quirk). "pack" (Zbkb) and "xperm4" (Zbkx)
# are both unique to their extension, not part of the zbb/zbc overlap.
# "fadd.q" gives RV32Q real coverage, same family as
# fadd.s/fadd.d/fadd.h. "fminm.s" gives Zfa coverage (Zfhmin isn't
# exercised here, same as zmmul -- it's a pure subset of zfh, already
# covered structurally by KNOWN_OVERLAPS). The next four fadd.s/d/q/h
# using integer registers resolve to fadd.s.inx/d.inx/q.inx/h.inx via
# resolve_inx_mnemonic() -- see that function's docstring for how it
# tells them apart from the identically-named float-register
# instructions already in this fixture (Zhinxmin isn't separately
# exercised, same KNOWN_OVERLAPS reasoning as Zfhmin/Zfh). "fcvt.bf16.s"
# gives Zfbfmin coverage. The vector block's second vsetvli switches to
# e16 for vfwcvtbf16.f.f.v/vfncvtbf16.f.f.w (Zvfbfmin) and
# vfwmaccbf16.vv (Zvfbfwma) -- their mnemonics carry "bf16" directly,
# so unlike the .inx lines they need no resolver, just their own table
# entries; "vsetvli" therefore counts 2, not 1. "auipc" (line 18)
# gives rv32I_upper_imm real coverage, not rv32I_loads -- lui/auipc
# are the only two U-type RV32I instructions (see rv32I_upper_imm's
# comment in isa_rv32.py), a separate subset from the real loads and
# the li/la pseudo-ops they happen to expand to. "ecall"/"fence" give
# rv32I_env/rv32I_fence real coverage -- these two used to be folded
# into one catch-all "rv32I_other" subset together with lui/auipc,
# now split three ways with nothing left over.
EXPECTED_COMPLEX_INSTRUCTIONS = {
    "add": 1, "amoadd.w": 1, "and": 2, "andn": 1, "auipc": 1,
    "bext": 1, "bne": 1, "c.and": 1, "c.beqz": 1, "c.fld": 1,
    "c.flw": 1, "c.jr": 1, "c.li": 1, "c.lw": 1, "c.swsp": 1,
    "c.zext.b": 1, "clmul": 1, "clz": 1, "cm.jt": 1, "cm.push": 1,
    "csrrw": 1, "czero.eqz": 1, "div": 1, "ecall": 1, "fadd.d": 1,
    "fadd.d.inx": 1, "fadd.h": 1, "fadd.h.inx": 1, "fadd.q": 1,
    "fadd.q.inx": 1, "fadd.s": 1, "fadd.s.inx": 1, "fcvt.bf16.s": 1,
    "fence": 1, "fence.i": 1, "fminm.s": 1, "fmul.s": 1, "jal": 1,
    "lb": 1, "lr.w": 1, "min": 1,
    "mul": 2, "pack": 1, "rdcycle": 1, "rdhpmcounter3": 1, "rem": 1,
    "reserved0": 1, "sb": 1, "sh1add": 1, "slli": 1, "slt": 1,
    "vadd.vv": 1, "vfncvtbf16.f.f.w": 1, "vfwcvtbf16.f.f.v": 1,
    "vfwmaccbf16.vv": 1, "vle32.v": 1, "vmul.vv": 1, "vse32.v": 1,
    "vsetvli": 2, "xperm4": 1,
}


def cleanup(*names):
    for name in names:
        for suffix in (".asm", ".mem", ".csv", "_isa_sets.csv"):
            path = OUT_DIR / f"{name}{suffix}"
            if path.exists():
                path.unlink()


class TestGetAsmInstr(unittest.TestCase):
    def setUp(self):
        with open(FIXTURE) as fp:
            self.instructions = ip.get_asmInstr(fp)

    def test_counts_valid_instructions(self):
        self.assertEqual(self.instructions, EXPECTED_INSTRUCTIONS)

    def test_skips_hex_digit_only_mnemonic(self):
        self.assertNotIn("1234", self.instructions)

    def test_skips_directive_lines(self):
        self.assertNotIn(".word", self.instructions)

    def test_skips_trailing_dot_mnemonic(self):
        self.assertNotIn("foo.", self.instructions)

    def test_counts_compressed_opcode_under_its_own_name(self):
        # the second "li" (address 1030) has a 4-hex-digit compressed
        # (RVC) opcode; objdump prints it the same as a 32-bit "li", but
        # it must resolve to its real "c.li" name and count separately
        # from the 32-bit one, not merge into a shared "li" total
        self.assertEqual(self.instructions["li"], 1)
        self.assertEqual(self.instructions["c.li"], 1)

    def test_skips_non_4_or_32bit_opcode(self):
        # an opcode field that's neither 4 nor 8 hex digits (here, 6) is
        # not a real objdump width and must be rejected
        self.assertNotIn("garbage", self.instructions)

    def test_add_is_not_mistaken_for_raw_hex(self):
        # regression test: "add" consists entirely of hex-digit characters
        # (a, d, d), so it was previously indistinguishable from the raw
        # hex data words the parser is supposed to filter out, and got
        # silently dropped -- see HEX_MNEMONICS
        self.assertIn("add", self.instructions)
        self.assertEqual(self.instructions["add"], 1)


class TestResolveCompressedMnemonic(unittest.TestCase):
    '''
    Direct tests of resolve_compressed_mnemonic()'s disambiguation
    rules, verified against real riscv32-unknown-elf-as/objdump output
    (see tests/fixtures/README.md). Covers the cases basic.asm and
    complex.asm don't exercise on their own: c.addi vs c.addi16sp vs
    c.addi4spn, and c.lw vs c.lwsp (c.sw vs c.swsp is covered by
    complex.asm's compressed block instead).
    '''
    def test_ret_resolves_to_jr(self):
        # objdump always prints "c.jr ra" as the pseudo-op "ret", never
        # a literal "c.ret" (which isn't a real instruction)
        self.assertEqual(ip.resolve_compressed_mnemonic("ret", ""), "c.jr")

    def test_jr_with_other_register_resolves_to_jr(self):
        self.assertEqual(
            ip.resolve_compressed_mnemonic("jr", "a1"), "c.jr"
        )

    def test_addi_same_register_resolves_to_addi(self):
        # "addi a0,a0,3" -- rd == rs1, neither is sp
        self.assertEqual(
            ip.resolve_compressed_mnemonic("addi", "a0,a0,3"), "c.addi"
        )

    def test_addi_sp_sp_resolves_to_addi16sp(self):
        # "addi sp,sp,-16" -- rd == rs1 == sp; c.addi can never target
        # sp itself, that encoding is exclusively c.addi16sp
        self.assertEqual(
            ip.resolve_compressed_mnemonic("addi", "sp,sp,-16"),
            "c.addi16sp",
        )

    def test_addi_from_sp_resolves_to_addi4spn(self):
        # "addi a1,sp,16" -- only the source is sp, destination isn't;
        # c.addi4spn's destination register can never be sp either way
        # (its 3-bit register field doesn't include x2/sp)
        self.assertEqual(
            ip.resolve_compressed_mnemonic("addi", "a1,sp,16"),
            "c.addi4spn",
        )

    def test_lw_general_base_resolves_to_lw(self):
        self.assertEqual(
            ip.resolve_compressed_mnemonic("lw", "a0,4(a1)"), "c.lw"
        )

    def test_lw_sp_base_resolves_to_lwsp(self):
        self.assertEqual(
            ip.resolve_compressed_mnemonic("lw", "a0,8(sp)"), "c.lwsp"
        )

    def test_sw_general_base_resolves_to_sw(self):
        self.assertEqual(
            ip.resolve_compressed_mnemonic("sw", "a0,4(a1)"), "c.sw"
        )

    def test_sw_sp_base_resolves_to_swsp(self):
        self.assertEqual(
            ip.resolve_compressed_mnemonic("sw", "a0,8(sp)"), "c.swsp"
        )

    def test_float_loads_stores_share_the_same_sp_disambiguation(self):
        # flw/fsw (Zcf) and fld/fsd (Zcd) have the exact same
        # plain-vs-"...sp" split as lw/sw
        for instr, sp_name in [
            ("flw", "c.flwsp"), ("fsw", "c.fswsp"),
            ("fld", "c.fldsp"), ("fsd", "c.fsdsp"),
        ]:
            self.assertEqual(
                ip.resolve_compressed_mnemonic(instr, "fa0,4(a1)"),
                f"c.{instr}",
            )
            self.assertEqual(
                ip.resolve_compressed_mnemonic(instr, "fa0,8(sp)"),
                sp_name,
            )

    def test_cm_mnemonic_returned_unchanged(self):
        # Zcmp/Zcmt's "cm.*" mnemonics are already complete and real --
        # objdump doesn't alias them from something else, so they must
        # NOT get re-prefixed into "c.cm.push"
        for instr in ("cm.push", "cm.pop", "cm.jt", "cm.jalt"):
            self.assertEqual(
                ip.resolve_compressed_mnemonic(instr, "{ra},-16"), instr
            )

    def test_unambiguous_mnemonic_gets_simple_prefix(self):
        self.assertEqual(
            ip.resolve_compressed_mnemonic("li", "a0,5"), "c.li"
        )
        self.assertEqual(
            ip.resolve_compressed_mnemonic("ebreak", ""), "c.ebreak"
        )

    def test_every_resolved_name_is_a_known_zc_mnemonic(self):
        # regression guard: every case above (and a few more real ones,
        # spanning Zca/Zcf/Zcd/Zcb/Zcmp/Zcmt) must land on a name
        # that's actually in one of those tables, or it'll silently
        # fall into the "unknown" bucket instead of being categorized
        isa_lists = ip.get_isa_lists()
        known = (
            set(isa_lists["zca"]) | set(isa_lists["zcf"])
            | set(isa_lists["zcd"]) | set(isa_lists["zcb"])
            | set(isa_lists["zcmp"]) | set(isa_lists["zcmt"])
        )
        cases = [
            ("ret", ""), ("jr", "a1"), ("jalr", "a1"),
            ("addi", "a0,a0,3"), ("addi", "sp,sp,-16"),
            ("addi", "a1,sp,16"), ("lw", "a0,4(a1)"),
            ("lw", "a0,8(sp)"), ("sw", "a0,4(a1)"), ("sw", "a0,8(sp)"),
            ("flw", "fa0,4(a1)"), ("flw", "fa0,8(sp)"),
            ("fsw", "fa0,4(a1)"), ("fsw", "fa0,8(sp)"),
            ("fld", "fa0,8(a1)"), ("fld", "fa0,16(sp)"),
            ("fsd", "fa0,8(a1)"), ("fsd", "fa0,16(sp)"),
            ("li", "a0,5"), ("mv", "a0,a1"), ("add", "a0,a0,a1"),
            ("and", "a0,a0,a1"), ("nop", ""), ("ebreak", ""),
            ("lbu", "a0,1(a1)"), ("lhu", "a0,2(a1)"), ("lh", "a0,2(a1)"),
            ("sb", "a0,1(a1)"), ("sh", "a0,2(a1)"),
            ("zext.b", "a0"), ("sext.b", "a0"),
            ("zext.h", "a0"), ("sext.h", "a0"), ("not", "a0"),
            ("mul", "a0,a1"),
            ("cm.push", "{ra},-16"), ("cm.pop", "{ra},16"),
            ("cm.popret", "{ra},16"), ("cm.popretz", "{ra},16"),
            ("cm.mva01s", "s0,s1"), ("cm.mvsa01", "s0,s1"),
            ("cm.jt", "5"), ("cm.jalt", "200"),
        ]
        for instr, operands in cases:
            resolved = ip.resolve_compressed_mnemonic(instr, operands)
            self.assertIn(resolved, known, resolved)


class TestResolveZihpmMnemonic(unittest.TestCase):
    '''
    Direct tests of resolve_zihpm_mnemonic()'s CSR-operand
    disambiguation, verified against real riscv32-unknown-elf-as/
    objdump output. A hpmcounter3-31 access has no dedicated mnemonic
    of its own -- it always disassembles as a generic CSR pseudo-op
    (e.g. "csrr a0,hpmcounter5"), the same text an unrelated CSR
    access like "csrr a0,mstatus" would produce, so the CSR name has
    to be read from the operand text instead.
    '''
    def test_rd_first_forms_resolve(self):
        # csrr/csrrs/csrrc/csrrsi/csrrci/csrrw all put the CSR name
        # second: "<mnemonic> rd,csr[,rs1-or-imm]"
        for mnemonic, operands in [
            ("csrr", "a0,hpmcounter5"),
            ("csrrs", "a0,hpmcounter5,a1"),
            ("csrrc", "a0,hpmcounter5,a1"),
            ("csrrsi", "a0,hpmcounter5,3"),
            ("csrrci", "a0,hpmcounter5,3"),
            ("csrrw", "a0,hpmcounter5,a1"),
        ]:
            self.assertEqual(
                ip.resolve_zihpm_mnemonic(mnemonic, operands),
                "rdhpmcounter5",
                f"{mnemonic} {operands}",
            )

    def test_csr_first_forms_resolve(self):
        # csrw/csrs/csrc/csrwi/csrsi/csrci have no destination
        # register, so the CSR name comes first: "<mnemonic> csr,..."
        for mnemonic, operands in [
            ("csrw", "hpmcounter5,a0"),
            ("csrs", "hpmcounter5,a0"),
            ("csrc", "hpmcounter5,a0"),
            ("csrwi", "hpmcounter5,3"),
            ("csrsi", "hpmcounter5,3"),
            ("csrci", "hpmcounter5,3"),
        ]:
            self.assertEqual(
                ip.resolve_zihpm_mnemonic(mnemonic, operands),
                "rdhpmcounter5",
                f"{mnemonic} {operands}",
            )

    def test_high_half_gets_h_suffix(self):
        self.assertEqual(
            ip.resolve_zihpm_mnemonic("csrr", "a0,hpmcounter3h"),
            "rdhpmcounter3h",
        )

    def test_range_boundaries(self):
        self.assertEqual(
            ip.resolve_zihpm_mnemonic("csrr", "a0,hpmcounter3"),
            "rdhpmcounter3",
        )
        self.assertEqual(
            ip.resolve_zihpm_mnemonic("csrr", "a0,hpmcounter31"),
            "rdhpmcounter31",
        )

    def test_out_of_range_or_malformed_csr_not_resolved(self):
        # hpmcounter0-2 aren't real (those are cycle/time/instret by
        # their own names), and hpmcounter32+ doesn't exist -- both
        # must fall through unresolved, not be silently mislabeled
        for operands in ("a0,hpmcounter2", "a0,hpmcounter32"):
            self.assertEqual(
                ip.resolve_zihpm_mnemonic("csrr", operands), "csrr"
            )

    def test_unrelated_csr_not_resolved(self):
        self.assertEqual(
            ip.resolve_zihpm_mnemonic("csrr", "a0,mstatus"), "csrr"
        )

    def test_non_csr_mnemonic_returned_unchanged(self):
        self.assertEqual(
            ip.resolve_zihpm_mnemonic("add", "a0,a1,a2"), "add"
        )

    def test_every_resolved_name_is_a_known_zihpm_mnemonic(self):
        isa_lists = ip.get_isa_lists()
        for n in (3, 5, 17, 31):
            for suffix in ("", "h"):
                resolved = ip.resolve_zihpm_mnemonic(
                    "csrr", f"a0,hpmcounter{n}{suffix}"
                )
                self.assertIn(resolved, isa_lists["zihpm"], resolved)


class TestResolveInxMnemonic(unittest.TestCase):
    '''
    Direct tests of resolve_inx_mnemonic()'s float-vs-integer-register
    disambiguation, verified against real riscv32-unknown-elf-as/
    objdump output. Zfinx/Zdinx/Zqinx/Zhinx instructions print with the
    exact same mnemonic text as their F/D/Q/Zfh counterparts (e.g.
    "fadd.s" either way) -- only the operand register names (an
    "f"-prefixed ABI name vs a plain integer one) say which.
    '''
    def test_float_register_operand_leaves_mnemonic_unchanged(self):
        self.assertEqual(
            ip.resolve_inx_mnemonic("fadd.s", "fa0,fa1,fa2"), "fadd.s"
        )

    def test_integer_register_operands_get_inx_suffix(self):
        self.assertEqual(
            ip.resolve_inx_mnemonic("fadd.s", "a0,a1,a2"), "fadd.s.inx"
        )

    def test_mixed_destination_still_detects_float_source(self):
        # fcvt.w.s's destination is always an integer register even in
        # real F (the result of a float-to-int conversion) -- only the
        # source operand distinguishes F from Zfinx here
        self.assertEqual(
            ip.resolve_inx_mnemonic("fcvt.w.s", "a0,fa1"), "fcvt.w.s"
        )
        self.assertEqual(
            ip.resolve_inx_mnemonic("fcvt.w.s", "a0,a1"), "fcvt.w.s.inx"
        )

    def test_every_width_resolves_to_its_own_inx_family(self):
        for suffix, table in (
            ("s", "zfinx"), ("d", "zdinx"),
            ("q", "zqinx"), ("h", "zhinx"),
        ):
            resolved = ip.resolve_inx_mnemonic(
                f"fadd.{suffix}", "a0,a1,a2"
            )
            isa_lists = ip.get_isa_lists()
            self.assertIn(resolved, isa_lists[table], resolved)

    def test_loads_stores_and_bitmoves_have_no_inx_form(self):
        # flw/fsw/fmv.x.w/fmv.w.x etc have no "inx" counterpart at all
        # (there's no separate register file to load into/store from,
        # or to reinterpret bits between) -- must never be relabeled,
        # even though their own operands don't include an
        # "f"-prefixed one either (a load's base register is always
        # a plain integer register, real F included)
        for instr, operands in [
            ("flw", "fa0,4(a1)"), ("fsw", "fa0,4(a1)"),
            ("fmv.x.w", "a0,fa1"), ("fmv.w.x", "fa0,a1"),
        ]:
            self.assertEqual(
                ip.resolve_inx_mnemonic(instr, operands), instr
            )

    def test_unrelated_mnemonic_returned_unchanged(self):
        self.assertEqual(
            ip.resolve_inx_mnemonic("add", "a0,a1,a2"), "add"
        )


class TestGetIsaLists(unittest.TestCase):
    def setUp(self):
        self.isa_lists = ip.get_isa_lists()

    def test_whole_set_names_have_no_underscore(self):
        # get_setInstr()/print_isa_lists() both split subset keys on the
        # first underscore to recover the whole-set name; a whole-set name
        # that itself contained an underscore would break both
        for key in self.isa_lists:
            if "_" not in key:
                continue
            whole = key.split("_", 1)[0]
            self.assertNotIn("_", whole)

    # zmmul is intentionally == rv32M_mul (Zmmul is a real, spec-defined
    # subset of M, not a miscategorization like zext.h was) -- see
    # get_isa_lists()'s comment on zmmul. zbkb/zbkc are the same kind
    # of real, spec-defined overlap with zbb/zbc (the scalar-crypto
    # subsets of Bitmanip), zfhmin/zfh likewise (Zfhmin is Zfh's
    # minimal load/store/conversion-only subset), and zhinxmin/zhinx
    # the same again one level down (Zhinxmin is Zhinx's equivalent
    # minimal subset) -- see isa_rv32.py's comments on them.
    KNOWN_OVERLAPS = {
        frozenset({"zmmul", "rv32M_mul"}),
        frozenset({"zbkb", "zbb"}),
        frozenset({"zbkc", "zbc"}),
        frozenset({"zfhmin", "zfh"}),
        frozenset({"zhinxmin", "zhinx"}),
    }

    def test_no_unexpected_instruction_overlap_across_sets(self):
        seen = {}
        for set_name, instrs in self.isa_lists.items():
            for instr in instrs:
                other = seen.get(instr)
                if other is not None and other != set_name:
                    pair = frozenset({other, set_name})
                    self.assertIn(
                        pair, self.KNOWN_OVERLAPS,
                        f"{instr} appears in both {other} and {set_name}, "
                        "and this isn't a documented, intentional overlap"
                    )
                seen[instr] = set_name


class TestCoreProfiles(unittest.TestCase):
    '''
    Structural checks on isa_rv32.CORE_PROFILES, the reference data
    behind -list-core. Unlike get_isa_lists()'s tables, this isn't
    derived from real objdump output (a specific core's RTL config
    isn't something a generic toolchain can tell us), so these are
    schema/typo guards rather than behavioral tests.
    '''
    def setUp(self):
        self.isa_lists = ip.get_isa_lists()
        self.core_profiles = ip.isa_rv32.CORE_PROFILES

    def test_every_profile_has_required_fields(self):
        for name, profile in self.core_profiles.items():
            self.assertIn("source", profile, name)
            self.assertTrue(profile["source"].startswith("http"), name)
            self.assertIn("base", profile, name)
            self.assertTrue(len(profile["base"]) > 0, name)
            self.assertIn("always", profile, name)
            self.assertTrue(len(profile["always"]) > 0, name)

    def test_single_word_entries_are_known_extension_names(self):
        # a list entry with no spaces is a bare extension name meant
        # to resolve via this tool's own -es/-list-instr lookup (e.g.
        # "zicsr", or a whole-set name like "rv32I" that only expands
        # via prefix matching, not a literal isa_lists key), as
        # opposed to a free-text/prose note (e.g. "rv32M or
        # zmmul-only (config: M_EXT)") -- every bare one must actually
        # resolve to something, or it's a typo nobody would notice
        for name, profile in self.core_profiles.items():
            for key in ("base", "always", "optional", "not_supported"):
                for item in profile.get(key, []):
                    if " " in item:
                        continue
                    resolved = ip.get_setInstr([item], self.isa_lists)
                    self.assertTrue(
                        len(resolved) > 0, f"{name}.{key}: {item}"
                    )


class TestGetSetInstr(unittest.TestCase):
    def setUp(self):
        self.isa_lists = ip.get_isa_lists()

    def test_exact_subset_match(self):
        result = ip.get_setInstr(["rv32I_shifts"], self.isa_lists)
        self.assertEqual(
            sorted(result), sorted(self.isa_lists["rv32I_shifts"])
        )

    def test_whole_set_expands_all_subsets(self):
        result = set(ip.get_setInstr(["rv32I"], self.isa_lists))
        expected = set()
        for key, instrs in self.isa_lists.items():
            if key.startswith("rv32I_"):
                expected.update(instrs)
        self.assertEqual(result, expected)

    def test_whole_set_expands_all_subsets_rv32V(self):
        # same prefix-expansion mechanism as rv32I, exercised separately
        # since rv32V has its own (larger) set of subsets
        result = set(ip.get_setInstr(["rv32V"], self.isa_lists))
        expected = set()
        for key, instrs in self.isa_lists.items():
            if key.startswith("rv32V_"):
                expected.update(instrs)
        self.assertEqual(result, expected)
        self.assertTrue(len(expected) > 0)

    def test_case_insensitive(self):
        upper = ip.get_setInstr(["RV32A"], self.isa_lists)
        lower = ip.get_setInstr(["rv32a"], self.isa_lists)
        self.assertEqual(upper, lower)
        self.assertTrue(len(upper) > 0)

    def test_dedup_across_overlapping_names(self):
        result = ip.get_setInstr(
            ["rv32I", "rv32I_shifts"], self.isa_lists
        )
        self.assertEqual(len(result), len(set(result)))

    def test_unmatched_name_returns_empty(self):
        result = ip.get_setInstr(["bogus_set_xyz"], self.isa_lists)
        self.assertEqual(result, [])

    def test_umbrella_expands_to_all_members(self):
        # rv32B isn't a naming-prefix of Zba/Zbb/Zbc/Zbs (unlike
        # rv32I/rv32I_shifts), so it can only resolve via ISA_UMBRELLAS
        result = set(ip.get_setInstr(["rv32B"], self.isa_lists))
        expected = set()
        for member in ip.ISA_UMBRELLAS["rv32B"]:
            expected.update(self.isa_lists[member])
        self.assertEqual(result, expected)
        self.assertTrue(len(expected) > 0)

    def test_umbrella_member_works_standalone(self):
        # the official extension name works on its own too, not just as
        # part of the rv32B umbrella
        result = ip.get_setInstr(["Zba"], self.isa_lists)
        self.assertEqual(sorted(result), sorted(self.isa_lists["zba"]))

    def test_zce_umbrella_expands_to_zca_zcb_zcmp_zcmt(self):
        # Zce is the embedded-profile code-size-reduction bundle --
        # verified against the real assembler to be exactly these four
        # and nothing more (notably not Zcf/Zcd, unlike rv32C's own
        # umbrella)
        result = set(ip.get_setInstr(["zce"], self.isa_lists))
        expected = set()
        for member in ("zca", "zcb", "zcmp", "zcmt"):
            expected.update(self.isa_lists[member])
        self.assertEqual(result, expected)
        self.assertTrue(len(expected) > 0)


class TestExtractHex(unittest.TestCase):
    def test_line_count_matches_extractInstr(self):
        name = "unittest_correspondence_tmp"
        try:
            with open(FIXTURE) as fp:
                instrList = list(EXPECTED_INSTRUCTIONS.keys())
                ip.extractInstr(instrList, fp, name)
                ip.extractHex(instrList, fp, name)

            asm_lines = (OUT_DIR / f"{name}.asm").read_text().splitlines()
            mem_lines = (OUT_DIR / f"{name}.mem").read_text().splitlines()
            self.assertEqual(len(asm_lines), len(mem_lines))
            self.assertEqual(
                len(asm_lines), sum(EXPECTED_INSTRUCTIONS.values())
            )
        finally:
            cleanup(name)

    def test_known_opcode_little_endian_conversion(self):
        # srli a4,a5,0x1 -> opcode 0017d713 -> little-endian "13 d7 17 00"
        name = "unittest_hexconv_tmp"
        try:
            with open(FIXTURE) as fp:
                ip.extractHex(["srli"], fp, name)
            content = (OUT_DIR / f"{name}.mem").read_text().strip()
            self.assertEqual(content, "13 d7 17 00")
        finally:
            cleanup(name)

    def test_compressed_opcode_extracted_as_two_bytes(self):
        # basic.asm's 32-bit "li" (opcode 00000513) and compressed "c.li"
        # (opcode 4501) are separate mnemonics now, matched and extracted
        # independently -- "li" pulls only the 32-bit line (4 bytes),
        # "c.li" only the compressed one, written as its real 2-byte
        # little-endian encoding rather than padded/truncated to 4
        name = "unittest_compressed_hexconv_tmp"
        try:
            with open(FIXTURE) as fp:
                ip.extractHex(["li"], fp, name)
            with open(FIXTURE) as fp:
                ip.extractHex(["c.li"], fp, f"{name}_compressed")

            lines = (
                (OUT_DIR / f"{name}.mem").read_text().strip().splitlines()
            )
            compressed_lines = (
                (OUT_DIR / f"{name}_compressed.mem")
                .read_text().strip().splitlines()
            )
            self.assertEqual(lines, ["13 05 00 00"])
            self.assertEqual(compressed_lines, ["01 45"])
        finally:
            cleanup(name, f"{name}_compressed")

    def test_default_endian_is_little(self):
        # endian isn't passed at all -- must match explicit "little"
        name = "unittest_hexconv_default_tmp"
        try:
            with open(FIXTURE) as fp:
                ip.extractHex(["srli"], fp, name)
            content = (OUT_DIR / f"{name}.mem").read_text().strip()
            self.assertEqual(content, "13 d7 17 00")
        finally:
            cleanup(name)

    def test_big_endian_leaves_objdump_byte_order_unchanged(self):
        # srli a4,a5,0x1 -> opcode 0017d713 -> objdump's own printed
        # order, not reversed
        name = "unittest_hexconv_big_tmp"
        try:
            with open(FIXTURE) as fp:
                ip.extractHex(["srli"], fp, name, endian="big")
            content = (OUT_DIR / f"{name}.mem").read_text().strip()
            self.assertEqual(content, "00 17 d7 13")
        finally:
            cleanup(name)

    def test_big_endian_compressed_opcode_two_bytes_unreversed(self):
        # c.li's 4501 opcode, endian="big" -> "45 01" (unreversed),
        # vs. little's "01 45" -- still exactly 2 bytes either way
        name = "unittest_hexconv_big_compressed_tmp"
        try:
            with open(FIXTURE) as fp:
                ip.extractHex(["c.li"], fp, name, endian="big")
            content = (OUT_DIR / f"{name}.mem").read_text().strip()
            self.assertEqual(content, "45 01")
        finally:
            cleanup(name)


class TestComplexFixture(unittest.TestCase):
    '''
    Integration-level tests running the full parse -> categorize
    pipeline against complex.asm, which (unlike basic.asm's narrow set
    of parser edge cases) covers every ISA extension the tool supports
    in one file, including compressed instructions and the newer
    bitmanip/Zicond/Zfh/RV32V additions.
    '''
    def setUp(self):
        with open(COMPLEX_FIXTURE) as fp:
            self.instructions = ip.get_asmInstr(fp)

    def test_counts_every_instruction(self):
        self.assertEqual(self.instructions, EXPECTED_COMPLEX_INSTRUCTIONS)

    def test_compressed_and_32bit_forms_counted_separately(self):
        # "and" appears as two 32-bit instances and one compressed
        # instance (c.and, printed by objdump the same as "and"), and
        # they must NOT be merged into one count
        self.assertEqual(self.instructions["and"], 2)
        self.assertEqual(self.instructions["c.and"], 1)

    def test_categorizes_across_every_supported_extension(self):
        categorized = ip.save_instuction_sets(self.instructions)
        expected_nonzero = [
            "rv32I_logic", "rv32I_addsub", "rv32I_shifts",
            "rv32I_comparisons", "rv32I_jumps", "rv32I_branches",
            "rv32I_loads", "rv32I_stores", "rv32I_upper_imm",
            "rv32I_fence", "rv32I_env",
            "rv32M_mul", "rv32M_div", "rv32M_rem",
            "rv32A", "rv32F", "rv32D", "rv32Q",
            "zba", "zbb", "zbc", "zbs", "zbkb", "zbkx",
            "zicond", "zfh", "zfa", "zfinx", "zdinx", "zqinx", "zhinx",
            "zfbfmin",
            "zicsr", "zifencei", "zicntr",
            "zihpm",
            "zca", "zcf", "zcd", "zcb", "zcmp", "zcmt",
            "rv32V_config", "rv32V_loads", "rv32V_stores",
            "rv32V_integer", "zvfbfmin", "zvfbfwma",
        ]
        for name in expected_nonzero:
            self.assertGreater(
                categorized[name], 0, f"{name} should have matched"
            )

    def test_zca_matches_resolved_compressed_instructions(self):
        # the fixture's six Zca-only compressed instances (c.li, c.jr,
        # c.beqz, c.and, c.lw, c.swsp) all resolve to real zca
        # mnemonics, so zca's count reflects exactly them, not 0
        categorized = ip.save_instuction_sets(self.instructions)
        self.assertEqual(categorized["zca"], 6)

    def test_unknown_instruction_is_isolated(self):
        categorized = ip.save_instuction_sets(self.instructions)
        self.assertEqual(categorized["unknown"], {"reserved0": 1})


class TestCli(unittest.TestCase):
    def run_cli(self, args):
        return subprocess.run(
            [sys.executable, str(SRC_DIR / "isa_profiler.py"), *args],
            capture_output=True, text=True
        )

    def test_list_sets_needs_no_input_file(self):
        result = self.run_cli(["-list-sets"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("rv32I", result.stdout)

    def test_list_instr_no_names_errors(self):
        result = self.run_cli(["-list-instr"])
        self.assertNotEqual(result.returncode, 0)

    def test_list_instr_prints_instructions(self):
        result = self.run_cli(["-list-instr", "rv32I_shifts"])
        self.assertEqual(result.returncode, 0)
        printed = result.stdout.split()
        for instr in ["sll", "slli", "srl", "srli", "sra", "srai"]:
            self.assertIn(instr, printed)

    def test_list_core_no_names_errors(self):
        result = self.run_cli(["-list-core"])
        self.assertNotEqual(result.returncode, 0)

    def test_list_core_prints_known_cores(self):
        result = self.run_cli(["-list-core", "cv32e40p", "cv32e40x"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("cv32e40p", result.stdout)
        self.assertIn("cv32e40x", result.stdout)
        # cv32e40p: standard RISC-V M/C are always present
        self.assertIn("rv32M", result.stdout)
        # cv32e40x: Zc-family extensions are always present
        self.assertIn("zcmp", result.stdout)

    def test_list_core_unknown_core_warns_not_crashes(self):
        result = self.run_cli(["-list-core", "bogus_core_xyz"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Unknown core", result.stderr)

    def test_unmatched_extract_name_warns_not_crashes(self):
        name = "unittest_cli_extract_tmp"
        try:
            result = self.run_cli(
                [str(FIXTURE), "-e", "bogus_instr_xyz", "-o", name]
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("not present", result.stderr)
        finally:
            cleanup(name)

    def test_eh_without_extract_warns(self):
        name = "unittest_cli_eh_tmp"
        try:
            result = self.run_cli([str(FIXTURE), "-eh", "-o", name])
            self.assertEqual(result.returncode, 0)
            self.assertIn("no effect", result.stderr)
        finally:
            cleanup(name)

    def test_endian_without_eh_warns(self):
        name = "unittest_cli_endian_tmp"
        try:
            result = self.run_cli(
                [str(FIXTURE), "-e", "li", "-endian", "big", "-o", name]
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("no effect", result.stderr)
        finally:
            cleanup(name)

    def test_endian_rejects_unknown_value(self):
        result = self.run_cli([str(FIXTURE), "-endian", "middle"])
        self.assertNotEqual(result.returncode, 0)

    def test_endian_big_reflected_in_hexdump(self):
        name = "unittest_cli_endian_big_tmp"
        try:
            result = self.run_cli([
                str(FIXTURE), "-e", "srli", "-eh", "-endian", "big",
                "-o", name
            ])
            self.assertEqual(result.returncode, 0)
            content = (OUT_DIR / f"{name}.mem").read_text().strip()
            self.assertEqual(content, "00 17 d7 13")
        finally:
            cleanup(name)

    def test_isa_csv_covers_complex_fixture(self):
        # end-to-end smoke test: complex.asm's broader mix of extensions
        # runs through the real CLI and -isa-csv without error, and the
        # written CSV reflects both a newer extension and the unknown
        # instruction it's expected to contain
        name = "unittest_cli_isa_csv_tmp"
        try:
            result = self.run_cli(
                [str(COMPLEX_FIXTURE), "-isa-csv", "-o", name]
            )
            self.assertEqual(result.returncode, 0)
            content = (OUT_DIR / f"{name}_isa_sets.csv").read_text()
            self.assertIn("rv32V_integer", content)
            self.assertIn("unknown_reserved0", content)
        finally:
            cleanup(name)

    def test_version(self):
        result = self.run_cli(["-v"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("isa_profiler.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
