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
"""

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
# "Zbs", unlike our own made-up rv32I_* groupings.
ISA_UMBRELLAS = {
    "rv32B": ["zba", "zbb", "zbc", "zbs"],
}

# RV32I Base Integer Instructions (grouped by functional category)
# Logic operations (and/or/xor and their immediate forms)
rv32I_logic = [
    "and", "or", "xor", "andi", "ori", "xori",
    # Pseudo-ops that map to logic operations
    "not", "mv", "zext.b"
]

# Add/Sub operations (and their pseudo-ops)
rv32I_addsub = [
    "add", "addi", "sub",
    # Pseudo-ops that map to add/sub
    "nop", "neg", "negw", "sext.w", "zext.w"
]

# Shift operations (logical/arithmetic shifts)
rv32I_shifts = [
    "sll", "slli", "srl", "srli", "sra", "srai"
]

# Comparison operations (and related pseudo-ops)
rv32I_comparisons = [
    "slt", "slti", "sltu", "sltiu",
    # Pseudo-ops
    "seqz", "snez", "sltz", "sgtz"
]

# Jump operations (unconditional jumps and returns)
rv32I_jumps = [
    "jal", "jalr",
    # Pseudo-ops
    "j", "jr", "ret", "call", "tail"
]

# Branch operations (conditional branches)
rv32I_branches = [
    "beq", "bne", "blt", "bge", "bltu", "bgeu",
    # Pseudo-ops
    "beqz", "bnez", "blez", "bgez", "bltz", "bgtz",
    "bgt", "ble", "bgtu", "bleu"
]

# Load operations
rv32I_loads = [
    "lb", "lh", "lw", "lbu", "lhu",
    # Pseudo-ops
    "li", "la", "lbz", "lhz", "lwz"
]

# Store operations
rv32I_stores = [
    "sb", "sh", "sw",
    # Pseudo-ops
    "sbz", "shz", "swz"
]

# Other RV32I operations (control and system)
rv32I_other = [
    "lui", "auipc",
    "fence", "ecall", "ebreak"
]

# RV32M Multiplication and Division Extension
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

# RV32A Atomic Extension
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

# RV32F Single-Precision Floating-Point Extension
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

# RV32D Double-Precision Floating-Point Extension
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

# RV32C Compressed Instructions Extension -- objdump always disassembles
# a compressed instruction using its base/pseudo-op alias (e.g. c.li
# prints as "li"), never these literal "c.*" forms, so
# isa_profiler.get_asmInstr() maps the displayed alias back to the real
# name below via resolve_compressed_mnemonic() before counting it. Most
# aliases map 1:1 by simple "c." prefixing, but a few are ambiguous or
# misleading by text alone and need the operand text too -- see that
# function's docstring for exactly which ones and why (c.jr/"ret",
# c.addi/c.addi16sp/c.addi4spn, and c.lw/c.lwsp, c.sw/c.swsp).
rv32C = [
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

# RV32B Bit Manipulation Extension -- "B" isn't one extension, it's an
# umbrella over 4 separately-ratified, independently-named
# sub-extensions (Zba/Zbb/Zbc/Zbs). Unlike rv32I_shifts etc. (our own
# made-up functional groupings), these are real official extension
# names, so they're kept as bare top-level keys (same as zicsr,
# zmmul, ...) rather than nested under an "rv32B_" prefix. -es rv32B
# still returns the union of all four -- see ISA_UMBRELLAS.

# Zba: address generation
zba = [
    "sh1add", "sh2add", "sh3add"
]

# Zbb: basic bit-manipulation
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

# Zbc: carry-less multiplication
zbc = [
    "clmul", "clmulh", "clmulr"
]

# Zbs: single-bit instructions
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

# Zmmul: the multiply-only subset of RV32M (no divide/remainder) --
# implemented by cores that support multiply but not division. Its
# instructions are the exact same as rv32M_mul (a real, spec-defined
# relationship, not a miscategorization), so this is an intentional
# overlap: -es zmmul and -es rv32M_mul resolve to the same instructions,
# and -isa-csv's "zmmul" column stays at 0 since rv32M_mul claims them
# first during categorization.
zmmul = [
    "mul", "mulh", "mulhsu", "mulhu"
]

# Zicond: integer conditional operations
zicond = [
    "czero.eqz", "czero.nez"
]

# Zfh: half-precision (16-bit) Floating-Point Extension
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

# Zicsr Control and Status Register Extension
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
    "fsflags",    # set floating-point exception flags

    # CSR pseudo-ops with register
    "csrr", "csrw", "csrs", "csrc",

    # CSR pseudo-ops with immediate
    "csrwi", "csrsi", "csrci"
]

# Zifencei Instruction-Fetch Fence Extension
zifencei = [
    "fence.i"  # Instruction fence
]

# Zicntr Counters Extension
zicntr = [
    # Basic counters
    "rdcycle", "rdtime", "rdinstret",

    # High word counters
    "rdcycleh", "rdtimeh", "rdinstreth"
]

# RV32V Vector Extension (grouped by functional category, like RV32I).
# Segment load/store instructions (vlseg2e8.v, vsseg3e32.v, ...) are
# deliberately excluded -- their nfields(2-8) x eew(8/16/32/64) x
# addressing-mode combinatorics would roughly double this file for an
# uncommon feature; add them here if a target ever needs them.

# Configuration-setting instructions
rv32V_config = [
    "vsetvli", "vsetivli", "vsetvl"
]

# Loads: unit-stride, mask, strided, indexed, fault-only-first, and
# whole-register-group
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
rv32V_stores = [
    "vse8.v", "vse16.v", "vse32.v", "vse64.v",
    "vsm.v",
    "vsse8.v", "vsse16.v", "vsse32.v", "vsse64.v",
    "vsuxei8.v", "vsuxei16.v", "vsuxei32.v", "vsuxei64.v",
    "vsoxei8.v", "vsoxei16.v", "vsoxei32.v", "vsoxei64.v",
    "vs1r.v", "vs2r.v", "vs4r.v", "vs8r.v"
]

# Integer arithmetic (.vv/.vx/.vi register/scalar/immediate forms)
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
# narrowing clipping
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

# Floating-point arithmetic, conversion, compare, and classify
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

# Reduction operations (fold a vector down to a single element)
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
# element-index generation
rv32V_mask = [
    "vmand.mm", "vmnand.mm", "vmandn.mm",
    "vmxor.mm", "vmor.mm", "vmnor.mm", "vmorn.mm", "vmxnor.mm",
    "vcpop.m", "vfirst.m",
    "vmsbf.m", "vmsif.m", "vmsof.m",
    "viota.m", "vid.v",
    # Pseudo-ops (aliases of the mm ops above with repeated operands)
    "vmmv.m", "vmclr.m", "vmset.m", "vmnot.m"
]

# Permutation: element move, slide, gather, and compress
rv32V_permute = [
    "vmv.x.s", "vmv.s.x",
    "vslideup.vx", "vslideup.vi",
    "vslidedown.vx", "vslidedown.vi",
    "vslide1up.vx", "vslide1down.vx",
    "vfslide1up.vf", "vfslide1down.vf",
    "vrgather.vv", "vrgather.vx", "vrgather.vi", "vrgatherei16.vv",
    "vcompress.vm"
]

# Whole-register-group move (register-to-register, unmasked, no vl/vtype)
rv32V_whole_reg = [
    "vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v"
]
