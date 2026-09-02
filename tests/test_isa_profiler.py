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
# (all subsets), RV32M, RV32A, RV32F, RV32D, compressed (RVC) forms of
# several base instructions, Zba/Zbb/Zbc/Zbs, Zicond, Zfh, Zicsr,
# Zifencei, Zicntr, and RV32V -- plus one deliberately unrecognized
# mnemonic ("reserved0") to exercise the "unknown" bucket. The compressed
# block resolves to c.li/c.jr (from "ret")/c.beqz/c.and/c.lw/c.swsp (from
# "sw a1,4(sp)", exercising the sp-base disambiguation) -- see
# resolve_compressed_mnemonic().
EXPECTED_COMPLEX_INSTRUCTIONS = {
    "add": 1, "amoadd.w": 1, "and": 2, "andn": 1, "auipc": 1,
    "bext": 1, "bne": 1, "c.and": 1, "c.beqz": 1, "c.jr": 1, "c.li": 1,
    "c.lw": 1, "c.swsp": 1, "clmul": 1, "clz": 1, "csrrw": 1,
    "czero.eqz": 1, "div": 1, "fadd.d": 1, "fadd.h": 1, "fadd.s": 1,
    "fence.i": 1, "fmul.s": 1, "jal": 1, "lb": 1, "lr.w": 1, "min": 1,
    "mul": 2, "rdcycle": 1, "rem": 1, "reserved0": 1, "sb": 1,
    "sh1add": 1, "slli": 1, "slt": 1, "vadd.vv": 1, "vle32.v": 1,
    "vmul.vv": 1, "vse32.v": 1, "vsetvli": 1,
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

    def test_unambiguous_mnemonic_gets_simple_prefix(self):
        self.assertEqual(
            ip.resolve_compressed_mnemonic("li", "a0,5"), "c.li"
        )
        self.assertEqual(
            ip.resolve_compressed_mnemonic("ebreak", ""), "c.ebreak"
        )

    def test_every_resolved_name_is_a_known_rv32C_mnemonic(self):
        # regression guard: every case above (and a few more real ones)
        # must land on a name that's actually in isa_rv32.rv32C, or
        # it'll silently fall into the "unknown" bucket instead of
        # being categorized
        isa_lists = ip.get_isa_lists()
        cases = [
            ("ret", ""), ("jr", "a1"), ("jalr", "a1"),
            ("addi", "a0,a0,3"), ("addi", "sp,sp,-16"),
            ("addi", "a1,sp,16"), ("lw", "a0,4(a1)"),
            ("lw", "a0,8(sp)"), ("sw", "a0,4(a1)"), ("sw", "a0,8(sp)"),
            ("li", "a0,5"), ("mv", "a0,a1"), ("add", "a0,a0,a1"),
            ("and", "a0,a0,a1"), ("nop", ""), ("ebreak", ""),
        ]
        for instr, operands in cases:
            resolved = ip.resolve_compressed_mnemonic(instr, operands)
            self.assertIn(resolved, isa_lists["rv32C"], resolved)


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
    # get_isa_lists()'s comment on zmmul.
    KNOWN_OVERLAPS = {frozenset({"zmmul", "rv32M_mul"})}

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
            "rv32I_loads", "rv32I_stores", "rv32I_other",
            "rv32M_mul", "rv32M_div", "rv32M_rem",
            "rv32A", "rv32F", "rv32D", "rv32C",
            "zba", "zbb", "zbc", "zbs",
            "zicond", "zfh", "zicsr", "zifencei", "zicntr",
            "rv32V_config", "rv32V_loads", "rv32V_stores",
            "rv32V_integer",
        ]
        for name in expected_nonzero:
            self.assertGreater(
                categorized[name], 0, f"{name} should have matched"
            )

    def test_rv32C_matches_resolved_compressed_instructions(self):
        # the fixture's six compressed instances (c.li, c.jr, c.beqz,
        # c.and, c.lw, c.swsp) all resolve to real rv32C mnemonics, so
        # rv32C's count reflects exactly them, not 0
        categorized = ip.save_instuction_sets(self.instructions)
        self.assertEqual(categorized["rv32C"], 6)

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
