"""
Supported RV32 ISA extension/subset instruction tables.

This is the single reference for which mnemonics belong to which RV32
ISA set or subset -- kept separate from isa_profiler.py so the actual
parsing/profiling logic isn't buried under a few hundred lines of
instruction-list data. isa_profiler.get_isa_lists() assembles these
tables into the {name: instructions} mapping the rest of the tool uses.

To add support for a new extension, add its instruction list here as
its own module-level constant and register it in get_isa_lists()'s
returned dict; nothing else needs to change unless the new extension is
(like rv32B) an umbrella over other independently-named sets, in which
case add an entry to ISA_UMBRELLAS too.

Named isa_rv32 (not isa_sets) so an isa_rv64 module could sit alongside
it if 64-bit support is ever added.

Unless a comment below says otherwise, all chapter/section references
are to "The RISC-V Instruction Set Manual, Volume I: Unprivileged
Architecture", Version 20260120: Official Release
(https://docs.riscv.org/reference/isa/v20260120/unpriv/unpriv-index.html)
-- called just "the ISA manual" below. A handful of extensions are still
defined in their own separate specification rather than in the main
manual, and are cited by that document's own title/version instead:
RV32B's Zba/Zbb/Zbc/Zbs (RISC-V Bit-Manipulation ISA-extensions),
the scalar-crypto Zbkb/Zbkc/Zbkx (RISC-V Cryptography Extensions,
Volume I: Scalar & Entropy Source Instructions), RV32V (RISC-V "V"
Vector Extension), and the vector BF16 Zvfbfmin/Zvfbfwma (RISC-V BF16
Extensions). Every citation below was checked directly against the
real document text, not recalled from memory.
"""
__author__ = "Nikolaos Kostakis"
__version__ = "1.2"

# Real RISC-V mnemonics that happen to consist entirely of hex-digit
# characters (0-9a-f), so isa_profiler.get_asmInstr()'s "looks like raw
# hex data" filter must not reject them. "add" is the only one currently
# in use (verified against every mnemonic in get_isa_lists()).
HEX_MNEMONICS = {"add"}

# ISA sets that are an umbrella over other, independently-named sets,
# where the umbrella name isn't a naming-prefix of its members (so the
# usual rv32I_shifts-style prefix matching in get_setInstr() can't find
# them). Maps the umbrella name to the get_isa_lists() keys it covers.
# "rv32B" is one such umbrella: "B" isn't a prefix of "Zba"/"Zbb"/"Zbc"/
# "Zbs", unlike our own made-up rv32I_* groupings. "rv32C" is another:
# the RISC-V "Zc" spec formally defines "C" as Zca + Zcf (RV32) + Zcd.
# Zcb/Zcmp/Zcmt are separate Zc-family extensions, not part of C, so
# they're not listed here. "Zce" is a third: the embedded-profile
# code-size-reduction bundle, Zca + Zcb + Zcmp + Zcmt (verified against
# the real assembler -- -march=rv32izce alone accepts an instruction
# from each of those four and nothing beyond them, notably not
# Zcf/Zcd).
ISA_UMBRELLAS = {
    "rv32B": ["zba", "zbb", "zbc", "zbs"],
    "rv32C": ["zca", "zcf", "zcd"],
    "zce": ["zca", "zcb", "zcmp", "zcmt"],
}

# Known CPU core profiles for the -list-core flag: which RISC-V
# extensions each named core supports. Unlike everything else in this
# file, this isn't derived from real objdump output -- a specific
# core's silicon/RTL configuration isn't something a generic toolchain
# can tell us, so each entry is sourced from that core's own user
# manual instead (see "source"). Extension names match this tool's own
# -es/-list-instr keys wherever a matching table exists, so they can
# be used directly; entries with no matching table (e.g. Zfinx, or a
# core's own custom/non-standard extensions) are informational only,
# clearly marked as not tracked by this tool.
#
# cv32e40p and cv32e40x are both parameterized/configurable cores, so
# "always" is what's present in every configuration, "optional" is
# gated by a named build parameter (given in each entry), and
# "not supported" / "custom" call out anything worth knowing that
# doesn't fit either.
CORE_PROFILES = {
    "cv32e40p": {
        "source": (
            "https://docs.openhwgroup.org/projects/cv32e40p-user-manual/"
        ),
        "base": ["rv32I"],
        "always": ["rv32M", "rv32C", "zicsr", "zifencei", "zicntr"],
        "optional": [
            "rv32F (config: FPU=1) -- mutually exclusive with Zfinx "
            "(the same F instructions, but reading/writing the "
            "integer register file instead of a dedicated FP one; "
            "Zfinx has no separate table here, not tracked by this "
            "tool)",
        ],
        "not_supported": ["rv32A"],
        "custom": [
            "Xcv* PULP/CORE-V extensions -- hardware loops, "
            "post-increment load/store, MAC, SIMD, and more "
            "(config: COREV_PULP=1) -- not standard RISC-V, not "
            "tracked by this tool",
            "Xcvelw event-load (config: COREV_CLUSTER=1) -- not "
            "standard RISC-V, not tracked by this tool",
        ],
    },
    "cv32e40x": {
        "source": (
            "https://docs.openhwgroup.org/projects/cv32e40x-user-manual/"
        ),
        "base": ["rv32I (or RV32E, config: RV32)"],
        "always": [
            "rv32C", "zca", "zcb", "zcmp", "zcmt",
            "zicsr", "zifencei", "zicntr", "zihpm",
            "zkt (a data-independent-execution-latency guarantee, "
            "not a set of instructions -- nothing for this tool to "
            "count even though it's always present)",
        ],
        "optional": [
            "rv32M or zmmul-only (config: M_EXT)",
            "rv32A (config: A_EXT)",
            "zba+zbb, zba+zbb+zbs, or zba+zbb+zbc+zbs (config: "
            "B_EXT -- 4 mutually exclusive levels, no plain zba-only "
            "or zbs-without-zbb option)",
        ],
        "custom": [
            "Xif custom extension interface (config: X_EXT) -- lets "
            "an implementer add their own instructions externally; "
            "not a fixed instruction set, not tracked by this tool",
        ],
    },
}

# RV32I Base Integer Instructions, v2.1 (grouped by functional
# category -- our own groupings, not the manual's; the manual itself
# splits by encoding format instead (register-immediate vs.
# register-register), so most subsets below actually span two of its
# sections, cited together per subset rather than one each).
# Logic operations (and/or/xor and their immediate forms) -- ISA
# manual sec. 1.1.4.1 "Integer Register-Immediate Instructions" (andi/
# ori/xori) and sec. 1.1.4.2 "Integer Register-Register Instructions"
# (and/or/xor)
rv32I_logic = [
    "and", "or", "xor", "andi", "ori", "xori",
    # Pseudo-ops that map to logic operations
    "not", "mv", "zext.b"
]

# Add/Sub operations (and their pseudo-ops) -- ISA manual sec. 1.1.4.1
# (addi) and sec. 1.1.4.2 (add/sub)
rv32I_addsub = [
    "add", "addi", "sub",
    # Pseudo-ops that map to add/sub
    "nop", "neg", "negw", "sext.w", "zext.w"
]

# Shift operations (logical/arithmetic shifts) -- ISA manual sec. 1.1.4.1
# (slli/srli/srai) and sec. 1.1.4.2 (sll/srl/sra)
rv32I_shifts = [
    "sll", "slli", "srl", "srli", "sra", "srai"
]

# Comparison operations (and related pseudo-ops) -- ISA manual
# sec. 1.1.4.1 (slti/sltiu) and sec. 1.1.4.2 (slt/sltu)
rv32I_comparisons = [
    "slt", "slti", "sltu", "sltiu",
    # Pseudo-ops
    "seqz", "snez", "sltz", "sgtz"
]

# Jump operations (unconditional jumps and returns) -- ISA manual
# sec. 1.1.5.1 "Unconditional Jumps"
rv32I_jumps = [
    "jal", "jalr",
    # Pseudo-ops
    "j", "jr", "ret", "call", "tail"
]

# Branch operations (conditional branches) -- ISA manual sec. 1.1.5.2
# "Conditional Branches"
rv32I_branches = [
    "beq", "bne", "blt", "bge", "bltu", "bgeu",
    # Pseudo-ops
    "beqz", "bnez", "blez", "bgez", "bltz", "bgtz",
    "bgt", "ble", "bgtu", "bleu"
]

# Load operations -- ISA manual sec. 1.1.6 "Load and Store Instructions"
rv32I_loads = [
    "lb", "lh", "lw", "lbu", "lhu",
    # Pseudo-ops
    "li", "la", "lbz", "lhz", "lwz"
]

# Store operations -- ISA manual sec. 1.1.6 "Load and Store Instructions"
rv32I_stores = [
    "sb", "sh", "sw",
    # Pseudo-ops
    "sbz", "shz", "swz"
]

# lui/auipc: the only two U-type instructions in RV32I. The ISA
# manual's sec. 1.1.4.1 "Integer Register-Immediate Instructions" lists
# them alongside addi/andi/etc. since that section groups by encoding
# format, but they don't actually add/subtract/compare a register
# value like those do -- they just form a 20-bit upper immediate (into
# rd for lui, or added to pc for auipc), so a dedicated subset keeps
# this project's own operation-based grouping honest instead of
# forcing them under addsub/logic. "li"/"la" (rv32I_loads above) are
# pseudo-ops that happen to expand to a real lui/auipc (verified
# against the real assembler), but lui/auipc aren't memory operations
# themselves, hence their own subset rather than rv32I_loads.
rv32I_upper_imm = [
    "lui", "auipc"
]

# fence: the base memory-ordering instruction. Its own subset since it
# doesn't belong to any of the operation-based groupings above. ISA
# manual sec. 1.1.7 "Memory Ordering Instructions" -- distinct from
# Zifencei's "fence.i" (sec. 4.1, a separate extension, further down).
rv32I_fence = [
    "fence"
]

# Environment call and breakpoint -- used to trap into the execution
# environment (an OS, hypervisor, or debugger). ISA manual sec. 1.1.8
# "Environment Call and Breakpoints".
rv32I_env = [
    "ecall", "ebreak"
]

# RV32M Multiplication and Division Extension, v2.0 -- ISA manual
# chapter 11, sec. 11.1 "M Extension for Integer Multiplication and
# Division" (Zmmul, the multiply-only subset, has its own version --
# see zmmul further down)
# Multiplication operations
rv32M_mul = [
    "mul", "mulh", "mulhsu", "mulhu"
]

# Division operations
rv32M_div = [
    "div", "divu"
]

# Remainder operations
rv32M_rem = [
    "rem", "remu"
]

# RV32A Atomic Extension, v2.1 -- ISA manual chapter 12, sec. 12.1
# "A Extension for Atomic Instructions"
rv32A = [
    # Basic load-reserved and store-conditional
    "lr.w", "sc.w",

    # Atomic memory operations (no ordering)
    "amoswap.w", "amoadd.w", "amoxor.w", "amoand.w", "amoor.w",
    "amomin.w", "amomax.w", "amominu.w", "amomaxu.w",

    # With acquire (aq) ordering
    "lr.w.aq", "sc.w.aq",
    "amoswap.w.aq", "amoadd.w.aq", "amoxor.w.aq", "amoand.w.aq",
    "amoor.w.aq", "amomin.w.aq", "amomax.w.aq", "amominu.w.aq",
    "amomaxu.w.aq",

    # With release (rl) ordering
    "lr.w.rl", "sc.w.rl",
    "amoswap.w.rl", "amoadd.w.rl", "amoxor.w.rl", "amoand.w.rl",
    "amoor.w.rl", "amomin.w.rl", "amomax.w.rl", "amominu.w.rl",
    "amomaxu.w.rl",

    # With acquire-release (aqrl) ordering
    "lr.w.aqrl", "sc.w.aqrl",
    "amoswap.w.aqrl", "amoadd.w.aqrl", "amoxor.w.aqrl",
    "amoand.w.aqrl", "amoor.w.aqrl", "amomin.w.aqrl", "amomax.w.aqrl",
    "amominu.w.aqrl", "amomaxu.w.aqrl"
]

# RV32F Single-Precision Floating-Point Extension, v2.2 -- ISA manual
# chapter 20, sec. 20.1 "F Extension for Single-Precision Floating-
# Point"
rv32F = [
    # Load and store
    "flw", "fsw",

    # Fused multiply-add operations
    "fmadd.s", "fmsub.s", "fnmsub.s", "fnmadd.s",

    # Arithmetic operations
    "fadd.s", "fsub.s", "fmul.s", "fdiv.s", "fsqrt.s",

    # Sign manipulation
    "fsgnj.s", "fsgnjn.s", "fsgnjx.s",

    # Min/Max operations
    "fmin.s", "fmax.s",

    # Conversion to integer
    "fcvt.w.s", "fcvt.wu.s", "fmv.x.w",

    # Comparison operations
    "feq.s", "flt.s", "fle.s", "fclass.s",

    # Conversion from integer
    "fcvt.s.w", "fcvt.s.wu", "fmv.w.x",

    "fmv.s",    # Move single-precision float
    "fabs.s",   # Absolute value
    "fneg.s"    # Negate
]

# RV32D Double-Precision Floating-Point Extension, v2.2 -- ISA manual
# chapter 21, sec. 21.1 "D Extension for Double-Precision Floating-
# Point"
rv32D = [
    # Load and store
    "fld", "fsd",

    # Fused multiply-add operations
    "fmadd.d", "fmsub.d", "fnmsub.d", "fnmadd.d",

    # Arithmetic operations
    "fadd.d", "fsub.d", "fmul.d", "fdiv.d", "fsqrt.d",

    # Sign manipulation
    "fsgnj.d", "fsgnjn.d", "fsgnjx.d",

    # Min/Max operations
    "fmin.d", "fmax.d",

    # Conversion between single and double
    "fcvt.s.d", "fcvt.d.s",

    # Comparison operations
    "feq.d", "flt.d", "fle.d", "fclass.d",

    # Conversion to integer
    "fcvt.w.d", "fcvt.wu.d",

    # Conversion from integer
    "fcvt.d.w", "fcvt.d.wu",

    "fmv.d",    # Move double-precision float
    "fabs.d",   # Absolute value
    "fneg.d"    # Negate
]

# RV32Q Quad-Precision (128-bit) Floating-Point Extension, v2.2 --
# ISA manual chapter 22, sec. 22.1 "Q Extension for Quad-Precision
# Floating-Point"
rv32Q = [
    # Load and store
    "flq", "fsq",

    # Fused multiply-add operations
    "fmadd.q", "fmsub.q", "fnmsub.q", "fnmadd.q",

    # Arithmetic operations
    "fadd.q", "fsub.q", "fmul.q", "fdiv.q", "fsqrt.q",

    # Sign manipulation
    "fsgnj.q", "fsgnjn.q", "fsgnjx.q",

    # Min/Max operations
    "fmin.q", "fmax.q",

    # Conversion between single/double/quad
    "fcvt.s.q", "fcvt.q.s", "fcvt.d.q", "fcvt.q.d",

    # Comparison operations
    "feq.q", "flt.q", "fle.q", "fclass.q",

    # Conversion to integer
    "fcvt.w.q", "fcvt.wu.q",

    # Conversion from integer
    "fcvt.q.w", "fcvt.q.wu",

    "fmv.q",    # Move quad-precision float
    "fabs.q",   # Absolute value
    "fneg.q"    # Negate
]

# RV32C Compressed Instructions Extension, v2.0 (ISA manual chapter
# 27, sec. 27.1 "C Extension for Compressed Instructions") -- "C"
# isn't one extension any more than "B" is: the RISC-V "Zc" (Code Size
# Reduction) spec (chapter 28, sec. 28.1 "Zc* Extension for Code Size
# Reduction", v1.0.0) formally defines it as Zca (sec. 28.1.5) + Zcf
# (sec. 28.1.6, RV32-only) + Zcd (sec. 28.1.7), so "rv32C" is a pure
# umbrella (see ISA_UMBRELLAS) over those three real, independent
# tables below, the same way "rv32B" is over Zba/Zbb/Zbc/Zbs. Zcb
# (sec. 28.1.8), Zcmp (sec. 28.1.9), and Zcmt (sec. 28.1.10, further
# down) are separate Zc-family extensions a core may add on top of C,
# not part of C itself, so they're kept as plain standalone entries
# with no umbrella relationship to rv32C. The manual states one
# version, "1.0.0", for the whole Zc* chapter -- it doesn't break out
# a separate version per individual Zc sub-extension.
#
# objdump always disassembles a compressed instruction using its
# base/pseudo-op alias (e.g. c.li prints as "li"), never these literal
# "c.*"/"cm.*" forms, so isa_profiler.get_asmInstr() maps the displayed
# alias back to the real name below via resolve_compressed_mnemonic()
# before counting it. Most aliases map 1:1 by simple "c." prefixing,
# but a few are ambiguous or misleading by text alone and need the
# operand text too -- see that function's docstring for exactly which
# ones and why (c.jr/"ret", c.addi/c.addi16sp/c.addi4spn, and
# c.lw/c.lwsp, c.sw/c.swsp, c.flw/c.flwsp, c.fsw/c.fswsp,
# c.fld/c.fldsp, c.fsd/c.fsdsp). Zcmp/Zcmt's "cm.*" mnemonics need no
# such mapping -- objdump already prints their real, complete name.
zca = [
    # Stack pointer operations
    "c.addi4spn", "c.addi16sp",

    # Load and store (immediate offset)
    "c.lw", "c.sw",

    # Immediate operations
    "c.addi", "c.li", "c.lui", "c.slli", "c.srli", "c.srai", "c.andi",

    # Register operations
    "c.sub", "c.xor", "c.or", "c.and", "c.add",

    # Control flow
    "c.j", "c.jal", "c.jr", "c.jalr", "c.beqz", "c.bnez",

    # Stack pointer load/store
    "c.lwsp", "c.swsp",

    # Miscellaneous
    "c.mv", "c.ebreak", "c.nop"
]

# Zcf Compressed Single-Precision Float Load/Store Extension (RV32-only
# -- on RV64 these encodings are repurposed for c.ld/c.sd instead)
zcf = [
    "c.flw", "c.fsw", "c.flwsp", "c.fswsp"
]

# Zcd Compressed Double-Precision Float Load/Store Extension
zcd = [
    "c.fld", "c.fsd", "c.fldsp", "c.fsdsp"
]

# Zcb Additional Compressed Instructions Extension -- small,
# commonly-useful compressed forms beyond the base Zca set (Zc*
# chapter, sec. 28.1.8). Every one of these aliases to a mnemonic
# already in another table (e.g. c.mul prints as "mul", already in
# rv32M_mul), so resolve_compressed_mnemonic()'s default "c." prefix
# handles them with no extra rules.
zcb = [
    # Narrow load/store (byte/halfword) -- Zca only has word-size
    "c.lbu", "c.lhu", "c.lh", "c.sb", "c.sh",

    # Sign/zero extension and bitwise not (needs Zbb for the sext/zext
    # pseudo-ops these compress)
    "c.zext.b", "c.sext.b", "c.zext.h", "c.sext.h", "c.not",

    # Multiply (needs M/Zmmul for the "mul" this compresses)
    "c.mul"
]

# Zcmp Push/Pop and Double-Move Extension (Zc* chapter, sec. 28.1.9)
# -- stack-frame save/restore and register-pair moves in a single
# compressed instruction, for function prologues/epilogues. Uses
# "cm." mnemonics that objdump prints as-is (no base/pseudo-op alias
# to resolve).
zcmp = [
    "cm.push", "cm.pop", "cm.popret", "cm.popretz",
    "cm.mva01s", "cm.mvsa01"
]

# Zcmt Table Jump Extension (Zc* chapter, sec. 28.1.10) -- jump/call
# through an entry in the jvt (jump vector table) CSR, indexed by a
# small immediate. Also uses "cm." mnemonics printed as-is.
zcmt = [
    "cm.jt", "cm.jalt"
]

# RV32B Bit Manipulation Extension -- "B" isn't one extension, it's an
# umbrella over 4 separately-ratified, independently-named
# sub-extensions (Zba/Zbb/Zbc/Zbs). Unlike rv32I_shifts etc. (our own
# made-up functional groupings), these are real official extension
# names, so they're kept as bare top-level keys (same as zicsr,
# zmmul, ...) rather than nested under an "rv32B_" prefix. -es rv32B
# still returns the union of all four -- see ISA_UMBRELLAS.
#
# All four are defined in their own standalone document, "RISC-V
# Bit-Manipulation ISA-extensions", Version 1.0.0-38-g865e7a7,
# 2021-06-28 -- not the main ISA manual (the section numbers below are
# that document's own overview sections for each extension; detailed
# per-instruction encodings live in its sec. 2, alphabetically, not
# cited individually here). The standalone document itself only says
# each extension is "frozen", with no clean "Version 1.0.0" line of
# its own; that version number instead comes from the main ISA
# manual's chapter 29.1, which mirrors these same four extensions and
# does state it explicitly per extension.

# Zba: address generation, v1.0.0 -- Bit-Manipulation spec sec. 1.1
zba = [
    "sh1add", "sh2add", "sh3add"
]

# Zbb: basic bit-manipulation, v1.0.0 -- Bit-Manipulation spec sec. 1.2
zbb = [
    # Logic operations
    "andn", "orn", "xnor",

    # Count operations
    "clz", "ctz", "cpop",

    # Min/Max operations
    "max", "maxu", "min", "minu",

    # Sign/Zero extension
    "sext.b", "sext.h", "zext.h",

    # Rotate operations
    "rol", "ror", "rori",

    # Bit manipulation
    "orc.b", "rev8"
]

# Zbc: carry-less multiplication, v1.0.0 -- Bit-Manipulation spec
# sec. 1.3
zbc = [
    "clmul", "clmulh", "clmulr"
]

# Zbs: single-bit instructions, v1.0.0 -- Bit-Manipulation spec sec. 1.4
zbs = [
    # Bit set operations
    "bset", "bseti",

    # Bit clear operations
    "bclr", "bclri",

    # Bit invert operations
    "binv", "binvi",

    # Bit extract operations
    "bext", "bexti"
]

# Zbkb: bit manipulation for scalar cryptography, v1.0.0 -- "RISC-V
# Cryptography Extensions, Volume I: Scalar & Entropy Source
# Instructions", Version v1.0.1, 18th Feb 2022 (Ratified), sec. 2.1 --
# a separate document from Bit-Manipulation above, same version-
# number caveat (this standalone doc doesn't itself print a clean
# "Version 1.0.0" either; it's from the main manual's chapter 29.1
# again). A curated subset of Zbb (andn/orn/xnor/rol/ror/rori/rev8,
# chosen for constant-time safety) plus a few instructions unique to
# Zbkb itself. The 7 shared ones are a real, spec-defined overlap with
# zbb (same relationship as zmmul/rv32M_mul): -es zbkb and -es zbb
# both resolve those, and -isa-csv's "zbkb" column only ever reflects
# the 5 unique instructions, since zbb claims the shared ones first.
zbkb = [
    # Unique to Zbkb
    "pack", "packh", "brev8", "zip", "unzip",

    # Shared with Zbb (same instructions, not a miscategorization)
    "andn", "orn", "xnor", "rol", "ror", "rori", "rev8"
]

# Zbkc: carry-less multiplication for scalar cryptography, v1.0.0 --
# Scalar Crypto spec sec. 2.2 -- the constant-time-safe half of Zbc
# (clmul/clmulh only, no clmulr). Every instruction here is a real,
# spec-defined overlap with zbc, so -isa-csv's "zbkc" column is
# always 0 (zbc claims them first) -- same relationship as
# zmmul/rv32M_mul.
zbkc = [
    "clmul", "clmulh"
]

# Zbkx: crossbar permutation for scalar cryptography, v1.0.0 -- Scalar
# Crypto spec sec. 2.3
zbkx = [
    "xperm4", "xperm8"
]

# Zmmul: the multiply-only subset of RV32M (no divide/remainder), v1.0
# -- ISA manual chapter 11, sec. 11.1.3 "Zmmul Extension" (its own
# version, distinct from the surrounding M chapter's v2.0) --
# implemented by cores that support multiply but not division. Its
# instructions are the exact same as rv32M_mul (a real, spec-defined
# relationship, not a miscategorization), so this is an intentional
# overlap: -es zmmul and -es rv32M_mul resolve to the same instructions,
# and -isa-csv's "zmmul" column stays at 0 since rv32M_mul claims them
# first during categorization.
zmmul = [
    "mul", "mulh", "mulhsu", "mulhu"
]

# Zicond: integer conditional operations, v1.0.0 -- ISA manual
# chapter 10, sec. 10.1 "'Zicond' Extension for Integer Conditional
# Operations"
zicond = [
    "czero.eqz", "czero.nez"
]

# Zfh: half-precision (16-bit) Floating-Point Extension, v1.0 -- ISA
# manual chapter 23, sec. 23.1 "Zfh and Zfhmin Extensions for Half-
# Precision Floating-Point" (one shared version for both Zfh and
# Zfhmin; the manual doesn't state a Zfhmin-only number)
zfh = [
    # Load and store
    "flh", "fsh",

    # Fused multiply-add operations
    "fmadd.h", "fmsub.h", "fnmsub.h", "fnmadd.h",

    # Arithmetic operations
    "fadd.h", "fsub.h", "fmul.h", "fdiv.h", "fsqrt.h",

    # Sign manipulation
    "fsgnj.h", "fsgnjn.h", "fsgnjx.h",

    # Min/Max operations
    "fmin.h", "fmax.h",

    # Conversion to/from other float widths
    "fcvt.s.h", "fcvt.h.s", "fcvt.d.h", "fcvt.h.d",

    # Move to/from integer register (reinterpret bits)
    "fmv.x.h", "fmv.h.x",

    # Comparison operations
    "feq.h", "flt.h", "fle.h", "fclass.h",

    # Conversion to/from integer
    "fcvt.w.h", "fcvt.wu.h", "fcvt.h.w", "fcvt.h.wu",

    "fmv.h",    # Move half-precision float
    "fabs.h",   # Absolute value
    "fneg.h"    # Negate
]

# Zfhmin: minimal half-precision support (ISA manual sec. 23.1.6,
# same chapter/version as Zfh above) -- load/store, move to/from
# integer registers, and conversion to/from other float widths only,
# no arithmetic. Every one of these 8 instructions is a real,
# spec-defined subset of Zfh (same relationship as Zmmul/rv32M_mul):
# -es zfhmin and -es zfh both resolve them, and -isa-csv's "zfhmin"
# column stays at 0 since zfh claims them first during categorization.
zfhmin = [
    "flh", "fsh",
    "fmv.x.h", "fmv.h.x",
    "fcvt.s.h", "fcvt.h.s", "fcvt.d.h", "fcvt.h.d"
]

# Zfa: additional floating-point instructions, v1.0 -- ISA manual
# chapter 25, sec. 25.1 "Zfa Extension for Additional Floating-Point
# Instructions" -- load-immediate, "minimum-number"/"maximum-number"
# (different NaN handling from fmin/fmax), round-to-integer-in-place,
# and quiet (non-trapping) compares, each across every float width
# this tool supports (H/S/D/Q), plus 3 RV32-specific instructions for
# accessing D's register pairs without a full load/store round-trip.
zfa = [
    # Load immediate float constant
    "fli.h", "fli.s", "fli.d", "fli.q",

    # Minimum-number / maximum-number (NaN-handling differs from
    # fmin/fmax)
    "fminm.h", "fminm.s", "fminm.d", "fminm.q",
    "fmaxm.h", "fmaxm.s", "fmaxm.d", "fmaxm.q",

    # Round to integer, in place
    "fround.h", "fround.s", "fround.d", "fround.q",
    "froundnx.h", "froundnx.s", "froundnx.d", "froundnx.q",

    # Quiet (non-trapping) compares
    "fleq.h", "fleq.s", "fleq.d", "fleq.q",
    "fltq.h", "fltq.s", "fltq.d", "fltq.q",

    # RV32-only: access D's register pairs directly
    "fcvtmod.w.d", "fmvh.x.d", "fmvp.d.x"
]

# Zfbfmin: minimal BF16 (brain-float16) support, v1.0 -- ISA manual
# chapter 24, sec. 24.1.4.1 "Zfbfmin - Scalar BF16 Converts" (within
# the "BF16" Extensions for BFloat16-precision Floating-Point
# chapter; sibling sections 24.1.4.2/24.1.4.3 are the vector
# Zvfbfmin/Zvfbfwma, further down near the rest of RV32V) --
# conversion to/from single-precision only, no arithmetic, load/
# store, or a dedicated BF16 register width of its own (BF16 values
# live in an F register, just interpreted with a different
# exponent/mantissa split).
zfbfmin = [
    "fcvt.bf16.s", "fcvt.s.bf16"
]

# Mnemonics that exist in F/D/Q/Zfh but have no "inx" (integer-register)
# counterpart: loads/stores (there's no separate register file to load
# into or store from under Zfinx/Zdinx/Zqinx/Zhinx) and the direct
# GPR<->FPR bit-reinterpret moves (meaningless once GPR and FPR are
# already the same file). Zfa has no "inx" variant of its own at all
# (verified against the real assembler: Zfa conflicts with Zfinx --
# its instructions are defined against the FPR file only), so it's not
# subtracted from anywhere below.
_NO_INX_EQUIVALENT = {
    "flw", "fsw", "fmv.x.w", "fmv.w.x",
    "fld", "fsd",
    "flq", "fsq",
    "flh", "fsh", "fmv.x.h", "fmv.h.x",
}

# Zfinx/Zdinx/Zhinx/Zhinxmin, v1.0 -- ISA manual chapter 26,
# sec. 26.1 "Zfinx, Zdinx, Zhinx, Zhinxmin Extensions for Floating-
# Point in Integer Registers" (one shared version for all four; the
# manual doesn't break out a separate Zhinxmin-only number, same as
# Zfh/Zfhmin above). Integer-register-file variants of F/D/Zfh/
# Zfhmin -- literally the same instructions (same mnemonic, same
# encoding), just reading/writing the integer register file instead
# of a dedicated FP one, for targets with no separate FPU register
# file at all. objdump prints the exact same mnemonic text either way
# (e.g. "fadd.s" for both F's and Zfinx's add), so
# isa_profiler.resolve_inx_mnemonic() distinguishes them by operand
# text instead: any operand naming an "f"-prefixed register (fa0,
# ft1, ...) means the real FPR-based instruction, and none doing so
# means the integer-register "inx" variant -- relabeled with a
# ".inx" suffix before counting (e.g. "fadd.s.inx") so it's tracked
# separately rather than merged into rv32F's count. zhinxmin is a
# real subset of zhinx (same relationship as Zfhmin/Zfh), so it's an
# intentional overlap, same KNOWN_OVERLAPS treatment.
#
# Zqinx (Q's would-be "inx" counterpart) is NOT included in that list
# above and is NOT a ratified RISC-V extension -- the manual's
# sec. 26.1.5 explicitly describes it only as a hypothetical future
# possibility ("An RV32Zqinx extension could also be defined but
# would require quad-register groups"), with no actual encoding ever
# specified. This table only exists because the real riscv32-unknown-
# elf-as assembler accepts "-march=...zqinx..." and produces real,
# working encodings for it anyway (verified directly) -- so it's
# tracked here as a genuine toolchain-level name, not a spec-ratified
# one. Don't read "zqinx" as having the same manual backing as its
# siblings.
zfinx = [f"{m}.inx" for m in rv32F if m not in _NO_INX_EQUIVALENT]
zdinx = [f"{m}.inx" for m in rv32D if m not in _NO_INX_EQUIVALENT]
zqinx = [f"{m}.inx" for m in rv32Q if m not in _NO_INX_EQUIVALENT]
zhinx = [f"{m}.inx" for m in zfh if m not in _NO_INX_EQUIVALENT]
zhinxmin = [f"{m}.inx" for m in zfhmin if m not in _NO_INX_EQUIVALENT]

# Zicsr Control and Status Register Extension, v2.0 -- ISA manual
# chapter 5, sec. 5.1 "Zicsr Extension for Control and Status
# Register (CSR) Instructions"
zicsr = [
    # CSR operations with register source
    "csrrw", "csrrs", "csrrc",

    # CSR operations with immediate source
    "csrrwi", "csrrsi", "csrrci",

    # RV32F/D CSR Pseudo-Instructions
    "frrm",      # read floating-point rounding mode
    "fsrm",      # set floating-point rounding mode from register
    "fsrmi",     # set floating-point rounding mode immediate
    "frflags",   # read floating-point exception flags
    "fsflags",   # set floating-point exception flags

    # CSR pseudo-ops with register
    "csrr", "csrw", "csrs", "csrc",

    # CSR pseudo-ops with immediate
    "csrwi", "csrsi", "csrci"
]

# Zifencei Instruction-Fetch Fence Extension, v2.0 -- ISA manual
# chapter 4, sec. 4.1 "Zifencei Extension for Instruction-Fetch Fence"
zifencei = [
    "fence.i"  # Instruction fence
]

# Zicntr Counters Extension, v2.0 -- ISA manual chapter 6, sec. 6.1.1,
# within sec. 6.1 "Zicntr and Zihpm Extensions for Counters" (one
# shared version for Zicntr and Zihpm below; the manual doesn't state
# a Zicntr-only number)
zicntr = [
    # Basic counters
    "rdcycle", "rdtime", "rdinstret",

    # High word counters
    "rdcycleh", "rdtimeh", "rdinstreth"
]

# Zihpm Hardware Performance Counters Extension, v2.0 -- ISA manual
# sec. 6.1.2 (same chapter/shared version as Zicntr above) --
# hpmcounter3-31 have no dedicated mnemonic of their own (unlike
# Zicntr's cycle/time/instret, which objdump aliases to rdcycle/
# rdtime/rdinstret); a real access always disassembles as a generic
# CSR pseudo-op (e.g. "csrr a0,hpmcounter5"), so
# isa_profiler.get_asmInstr() resolves it to "rdhpmcounter<N>" via
# the CSR-name operand before counting -- see
# resolve_zihpm_mnemonic(). Names here follow that same
# rdhpmcounter<N> convention rather than the CSR names themselves.
zihpm = (
    [f"rdhpmcounter{n}" for n in range(3, 32)]
    + [f"rdhpmcounter{n}h" for n in range(3, 32)]
)

# RV32V Vector Extension, v1.0, ratified Nov 2021 (grouped by
# functional category, like RV32I). Defined in its own standalone
# document, "RISC-V 'V' Vector Extension", Version 1.0 -- not the
# main ISA manual, though the same content is also mirrored there as
# chapter 30.1; the chapter/section numbers cited below are the
# standalone document's own numbering, since that's what's commonly
# referenced elsewhere (the manual's mirror renumbers everything
# under its own chapter 30). Segment load/store instructions
# (vlseg2e8.v, vsseg3e32.v, ...) are deliberately excluded -- their
# nfields(2-8) x eew(8/16/32/64) x addressing-mode combinatorics
# would roughly double this file for an uncommon feature; add them
# here if a target ever needs them.

# Configuration-setting instructions -- Vector spec chapter 6
rv32V_config = [
    "vsetvli", "vsetivli", "vsetvl"
]

# Loads: unit-stride, mask, strided, indexed, fault-only-first, and
# whole-register-group -- Vector spec chapter 7 ("Vector Loads and
# Stores"), sec. 7.4 (unit-stride, incl. vlm.v), sec. 7.5 (strided),
# sec. 7.6 (indexed), sec. 7.7 (fault-only-first), sec. 7.9 (whole-
# register) -- this chapter 7 is shared with rv32V_stores below;
# the spec doesn't split loads and stores into separate chapters
rv32V_loads = [
    "vle8.v", "vle16.v", "vle32.v", "vle64.v",
    "vlm.v",
    "vlse8.v", "vlse16.v", "vlse32.v", "vlse64.v",
    "vluxei8.v", "vluxei16.v", "vluxei32.v", "vluxei64.v",
    "vloxei8.v", "vloxei16.v", "vloxei32.v", "vloxei64.v",
    "vle8ff.v", "vle16ff.v", "vle32ff.v", "vle64ff.v",
    "vl1re8.v", "vl1re16.v", "vl1re32.v", "vl1re64.v",
    "vl2re8.v", "vl2re16.v", "vl2re32.v", "vl2re64.v",
    "vl4re8.v", "vl4re16.v", "vl4re32.v", "vl4re64.v",
    "vl8re8.v", "vl8re16.v", "vl8re32.v", "vl8re64.v"
]

# Stores: unit-stride, mask, strided, indexed, and whole-register-group
# -- same Vector spec chapter 7/sections as rv32V_loads above (minus
# sec. 7.7, fault-only-first, which is load-only)
rv32V_stores = [
    "vse8.v", "vse16.v", "vse32.v", "vse64.v",
    "vsm.v",
    "vsse8.v", "vsse16.v", "vsse32.v", "vsse64.v",
    "vsuxei8.v", "vsuxei16.v", "vsuxei32.v", "vsuxei64.v",
    "vsoxei8.v", "vsoxei16.v", "vsoxei32.v", "vsoxei64.v",
    "vs1r.v", "vs2r.v", "vs4r.v", "vs8r.v"
]

# Integer arithmetic (.vv/.vx/.vi register/scalar/immediate forms) --
# Vector spec chapter 11 "Vector Integer Arithmetic Instructions",
# sec. 11.1-11.16
rv32V_integer = [
    # Add/Subtract
    "vadd.vv", "vadd.vx", "vadd.vi",
    "vsub.vv", "vsub.vx",
    "vrsub.vx", "vrsub.vi",

    # Widening add/subtract
    "vwaddu.vv", "vwaddu.vx", "vwadd.vv", "vwadd.vx",
    "vwsubu.vv", "vwsubu.vx", "vwsub.vv", "vwsub.vx",
    "vwaddu.wv", "vwaddu.wx", "vwadd.wv", "vwadd.wx",
    "vwsubu.wv", "vwsubu.wx", "vwsub.wv", "vwsub.wx",

    # Integer widening sign/zero extension
    "vzext.vf2", "vzext.vf4", "vzext.vf8",
    "vsext.vf2", "vsext.vf4", "vsext.vf8",

    # Add-with-carry / subtract-with-borrow
    "vadc.vvm", "vadc.vxm", "vadc.vim",
    "vmadc.vvm", "vmadc.vxm", "vmadc.vim",
    "vmadc.vv", "vmadc.vx", "vmadc.vi",
    "vsbc.vvm", "vsbc.vxm",
    "vmsbc.vvm", "vmsbc.vxm", "vmsbc.vv", "vmsbc.vx",

    # Bitwise logic
    "vand.vv", "vand.vx", "vand.vi",
    "vor.vv", "vor.vx", "vor.vi",
    "vxor.vv", "vxor.vx", "vxor.vi",

    # Shifts (and narrowing shifts)
    "vsll.vv", "vsll.vx", "vsll.vi",
    "vsrl.vv", "vsrl.vx", "vsrl.vi",
    "vsra.vv", "vsra.vx", "vsra.vi",
    "vnsrl.wv", "vnsrl.wx", "vnsrl.wi",
    "vnsra.wv", "vnsra.wx", "vnsra.wi",

    # Compare
    "vmseq.vv", "vmseq.vx", "vmseq.vi",
    "vmsne.vv", "vmsne.vx", "vmsne.vi",
    "vmsltu.vv", "vmsltu.vx",
    "vmslt.vv", "vmslt.vx",
    "vmsleu.vv", "vmsleu.vx", "vmsleu.vi",
    "vmsle.vv", "vmsle.vx", "vmsle.vi",
    "vmsgtu.vx", "vmsgtu.vi",
    "vmsgt.vx", "vmsgt.vi",

    # Min/Max
    "vminu.vv", "vminu.vx",
    "vmin.vv", "vmin.vx",
    "vmaxu.vv", "vmaxu.vx",
    "vmax.vv", "vmax.vx",

    # Multiply/Divide/Remainder
    "vmul.vv", "vmul.vx",
    "vmulh.vv", "vmulh.vx",
    "vmulhu.vv", "vmulhu.vx",
    "vmulhsu.vv", "vmulhsu.vx",
    "vdivu.vv", "vdivu.vx",
    "vdiv.vv", "vdiv.vx",
    "vremu.vv", "vremu.vx",
    "vrem.vv", "vrem.vx",

    # Widening multiply
    "vwmul.vv", "vwmul.vx",
    "vwmulu.vv", "vwmulu.vx",
    "vwmulsu.vv", "vwmulsu.vx",

    # Multiply-add
    "vmacc.vv", "vmacc.vx",
    "vnmsac.vv", "vnmsac.vx",
    "vmadd.vv", "vmadd.vx",
    "vnmsub.vv", "vnmsub.vx",

    # Widening multiply-add
    "vwmaccu.vv", "vwmaccu.vx",
    "vwmacc.vv", "vwmacc.vx",
    "vwmaccsu.vv", "vwmaccsu.vx",
    "vwmaccus.vx",

    # Merge and move
    "vmerge.vvm", "vmerge.vxm", "vmerge.vim",
    "vmv.v.v", "vmv.v.x", "vmv.v.i"
]

# Fixed-point arithmetic: saturating, averaging, scaling shifts, and
# narrowing clipping -- Vector spec chapter 12 "Vector Fixed-Point
# Arithmetic Instructions", sec. 12.1/12.2 (saturating/averaging
# add-sub), sec. 12.4 (scaling shift), sec. 12.5 (narrowing clip).
# (sec. 12.3, fractional multiply with rounding/saturation, isn't
# included in this table)
rv32V_fixed_point = [
    "vsaddu.vv", "vsaddu.vx", "vsaddu.vi",
    "vsadd.vv", "vsadd.vx", "vsadd.vi",
    "vssubu.vv", "vssubu.vx",
    "vssub.vv", "vssub.vx",
    "vaaddu.vv", "vaaddu.vx",
    "vaadd.vv", "vaadd.vx",
    "vasubu.vv", "vasubu.vx",
    "vasub.vv", "vasub.vx",
    "vsmul.vv", "vsmul.vx",
    "vssrl.vv", "vssrl.vx", "vssrl.vi",
    "vssra.vv", "vssra.vx", "vssra.vi",
    "vnclipu.wv", "vnclipu.wx", "vnclipu.wi",
    "vnclip.wv", "vnclip.wx", "vnclip.wi"
]

# Floating-point arithmetic, conversion, compare, and classify --
# Vector spec chapter 13 "Vector Floating-Point Instructions",
# sec. 13.1-13.19 (add/sub, widening add/sub, fused multiply-add,
# sqrt/reciprocal estimates, min/max, sign manipulation, compare,
# classify, convert). Exception: "vfmv.f.s"/"vfmv.s.f" below are
# grouped here functionally (float moves), but the spec itself
# defines them in chapter 16 sec. 16.2 "Floating-Point Scalar Move
# Instructions" (the Permutation chapter, alongside rv32V_permute's
# integer equivalents) -- only "vfmv.v.f" (splat a scalar across a
# vector) is genuinely chapter 13's own sec. 13.16 "Vector Floating-
# Point Move Instruction".
rv32V_float = [
    # Add/Subtract (and widening forms)
    "vfadd.vv", "vfadd.vf",
    "vfsub.vv", "vfsub.vf",
    "vfrsub.vf",
    "vfwadd.vv", "vfwadd.vf",
    "vfwsub.vv", "vfwsub.vf",
    "vfwadd.wv", "vfwadd.wf",
    "vfwsub.wv", "vfwsub.wf",

    # Multiply/Divide (and widening multiply)
    "vfmul.vv", "vfmul.vf",
    "vfdiv.vv", "vfdiv.vf",
    "vfrdiv.vf",
    "vfwmul.vv", "vfwmul.vf",

    # Fused multiply-add
    "vfmacc.vv", "vfmacc.vf",
    "vfnmacc.vv", "vfnmacc.vf",
    "vfmsac.vv", "vfmsac.vf",
    "vfnmsac.vv", "vfnmsac.vf",
    "vfmadd.vv", "vfmadd.vf",
    "vfnmadd.vv", "vfnmadd.vf",
    "vfmsub.vv", "vfmsub.vf",
    "vfnmsub.vv", "vfnmsub.vf",
    "vfwmacc.vv", "vfwmacc.vf",
    "vfwnmacc.vv", "vfwnmacc.vf",
    "vfwmsac.vv", "vfwmsac.vf",
    "vfwnmsac.vv", "vfwnmsac.vf",

    # Square root and reciprocal estimates
    "vfsqrt.v", "vfrsqrt7.v", "vfrec7.v",

    # Min/Max and sign manipulation
    "vfmin.vv", "vfmin.vf",
    "vfmax.vv", "vfmax.vf",
    "vfsgnj.vv", "vfsgnj.vf",
    "vfsgnjn.vv", "vfsgnjn.vf",
    "vfsgnjx.vv", "vfsgnjx.vf",

    # Move to/from scalar float register
    "vfmv.f.s", "vfmv.s.f", "vfmv.v.f",

    # Compare
    "vmfeq.vv", "vmfeq.vf",
    "vmfne.vv", "vmfne.vf",
    "vmflt.vv", "vmflt.vf",
    "vmfle.vv", "vmfle.vf",
    "vmfgt.vf", "vmfge.vf",

    "vfclass.v",  # Classify

    # Convert to/from integer
    "vfcvt.xu.f.v", "vfcvt.x.f.v", "vfcvt.f.xu.v", "vfcvt.f.x.v",
    "vfcvt.rtz.xu.f.v", "vfcvt.rtz.x.f.v",

    # Widening convert
    "vfwcvt.xu.f.v", "vfwcvt.x.f.v",
    "vfwcvt.f.xu.v", "vfwcvt.f.x.v", "vfwcvt.f.f.v",
    "vfwcvt.rtz.xu.f.v", "vfwcvt.rtz.x.f.v",

    # Narrowing convert
    "vfncvt.xu.f.w", "vfncvt.x.f.w",
    "vfncvt.f.xu.w", "vfncvt.f.x.w", "vfncvt.f.f.w",
    "vfncvt.rod.f.f.w",
    "vfncvt.rtz.xu.f.w", "vfncvt.rtz.x.f.w"
]

# Reduction operations (fold a vector down to a single element) --
# Vector spec chapter 14 "Vector Reduction Operations", sec. 14.1-14.4
rv32V_reduction = [
    "vredsum.vs",
    "vredmaxu.vs", "vredmax.vs", "vredminu.vs", "vredmin.vs",
    "vredand.vs", "vredor.vs", "vredxor.vs",
    "vwredsumu.vs", "vwredsum.vs",
    "vfredosum.vs", "vfredusum.vs",
    "vfredmax.vs", "vfredmin.vs",
    "vfwredosum.vs", "vfwredusum.vs"
]

# Mask register logical operations, population/element-finding, and
# element-index generation -- Vector spec chapter 15 "Vector Mask
# Instructions", sec. 15.1-15.6, sec. 15.8-15.9
rv32V_mask = [
    "vmand.mm", "vmnand.mm", "vmandn.mm",
    "vmxor.mm", "vmor.mm", "vmnor.mm", "vmorn.mm", "vmxnor.mm",
    "vcpop.m", "vfirst.m",
    "vmsbf.m", "vmsif.m", "vmsof.m",
    "viota.m", "vid.v",
    # Pseudo-ops (aliases of the mm ops above with repeated operands)
    "vmmv.m", "vmclr.m", "vmset.m", "vmnot.m"
]

# Permutation: element move, slide, gather, and compress -- Vector
# spec chapter 16 "Vector Permutation Instructions", sec. 16.1
# (integer scalar move, "vmv.x.s"/"vmv.s.x" -- its float counterpart
# "vfmv.f.s"/"vfmv.s.f" lives in sec. 16.2 but is grouped under
# rv32V_float above instead, functionally), sec. 16.3 (slides),
# sec. 16.4 (gather), sec. 16.5 (compress)
rv32V_permute = [
    "vmv.x.s", "vmv.s.x",
    "vslideup.vx", "vslideup.vi",
    "vslidedown.vx", "vslidedown.vi",
    "vslide1up.vx", "vslide1down.vx",
    "vfslide1up.vf", "vfslide1down.vf",
    "vrgather.vv", "vrgather.vx", "vrgather.vi", "vrgatherei16.vv",
    "vcompress.vm"
]

# Whole-register-group move (register-to-register, unmasked, no
# vl/vtype) -- Vector spec sec. 16.6 "Whole Vector Register Move",
# same chapter 16 as rv32V_permute above -- distinct from sec. 7.9's
# whole-register-group LOADS/STORES (rv32V_loads/rv32V_stores), which
# move data to/from memory rather than register-to-register
rv32V_whole_reg = [
    "vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v"
]

# Zvfbfmin: vector equivalent of Zfbfmin, v1.0 -- defined in its own
# standalone document, "RISC-V BF16 Extensions", Version 1.0, Ratified
# 05 July 2024 (not the Vector spec above, nor the main ISA manual,
# though the manual does also mirror it as sec. 24.1.4.2 near scalar
# Zfbfmin) -- sec. 3.2 "'Zvfbfmin' - Vector BF16 Converts" for the
# extension itself, sec. 4.3/4.4 for "vfncvtbf16.f.f.w"/
# "vfwcvtbf16.f.f.v"'s own instruction definitions. BF16 (brain-
# float16) conversion only, no arithmetic. Both mnemonics carry
# "bf16" directly in their name (unlike scalar Zfbfmin's
# fcvt.bf16.s/fcvt.s.bf16), so they're real, unambiguous objdump
# output -- no resolver needed.
zvfbfmin = [
    "vfncvtbf16.f.f.w", "vfwcvtbf16.f.f.v"
]

# Zvfbfwma: single widening BF16 multiply-add, in its .vv/.vf forms,
# v1.0 -- same "RISC-V BF16 Extensions" document as Zvfbfmin above,
# sec. 3.3 "'Zvfbfwma' - Vector BF16 widening mul-add" for the
# extension, sec. 4.5 for "vfwmaccbf16"'s instruction definition
# (covers both the .vv and .vf forms). Verified against the real
# assembler as its own standalone extension (assembles fine without
# Zvfbfmin also enabled), so it's a separate table rather than
# folded into zvfbfmin.
zvfbfwma = [
    "vfwmaccbf16.vv", "vfwmaccbf16.vf"
]
