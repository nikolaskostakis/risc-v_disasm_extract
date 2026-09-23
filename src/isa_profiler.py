"""
RISC-V instruction counter and ISA extension profiler
"""
__author__ = "Nikolaos Kostakis"
__version__ = "1.5"

import os
import sys
import csv
import logging
import argparse
import string

from io import TextIOWrapper
from logging import Logger
import isa_rv32
from isa_rv32 import HEX_MNEMONICS, ISA_UMBRELLAS, CORE_PROFILES

def setupLogger() -> Logger:
    '''
    Set up and configure the logging system with colored output.

    Creates a logger with a custom ANSI color formatter that provides colored
    output for different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    The logger is configured to output to stdout with DEBUG level.

    :return: Configured logger instance
    :rtype: Logger
    '''
    class AnsiColorFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord):
            no_style = '\033[0m'
            bold = '\033[91m'
            grey = '\033[90m'
            yellow = '\033[93m'
            red = '\033[31m'
            red_light = '\033[91m'
            start_style = {
                'DEBUG': grey,
                'INFO': no_style,
                'WARNING': yellow,
                'ERROR': red,
                'CRITICAL': red_light + bold,
            }.get(record.levelname, no_style)
            end_style = no_style
            return f'{start_style}{super().format(record)}{end_style}'

    logger = logging.getLogger()

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG) # DEBUG INFO WARNING ERROR CRITICAL
    formatter = AnsiColorFormatter('{levelname}: {message}', style='{')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG) # DEBUG INFO WARNING ERROR CRITICAL

    return logger

def setupArgeparse() -> argparse.ArgumentParser:
    '''
    Set up and configure the command-line argument parser.

    Creates an ArgumentParser with the following arguments:
    - input_file: Positional argument for the assembly file to parse (not
      required when -list-sets, -list-instr, or -list-core is given)
    - -o/--output-name: Optional base name for output files
    - -csv: Flag to save raw instruction counts to CSV
    - -e/--extract: List of instructions to extract to a separate file
    - -es/--extract-set: List of ISA sets/subsets to extract to a
      separate file
    - -eh/--extract-hex: Flag to also write a hexdump of the extracted
      instructions (warns and does nothing without -e/-es)
    - -isa-csv: Flag to save ISA instruction set counts to CSV
    - -list-sets: Flag to print the known ISA sets/subsets and exit
    - -list-instr: List of ISA sets/subsets whose instructions should be
      printed, one per line, and exit
    - -list-core: List of CPU core names whose known ISA extensions
      should be printed, and exit
    - --version: Flag to print the tool's version and exit

    :return: Configured argument parser
    :rtype: argparse.ArgumentParser
    '''
    parser = argparse.ArgumentParser(
        description="RISC-V Instruction Counter and ISA Extension Profiler"
    )

    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )

    parser.add_argument(
        "input_file",
        type=str,
        nargs="?",
        default=None,
        help="Input Assembly file"
    )

    parser.add_argument(
        "-o", "--output-name",
        type=str,
        help="Name used in created output files",
        metavar="output_name",
        default=None
    )

    parser.add_argument(
        "-csv",
        action="store_true",
        help="Extract instructions to csv file"
    )

    parser.add_argument(
        "-e", "--extract",
        nargs="*",
        metavar="instr1, instr2,",
        help="Instructions to be extracted",
        default=[]
    )

    parser.add_argument(
        "-es", "--extract-set",
        nargs="*",
        metavar="set1, set2,",
        help="ISA sets/subsets to extract, e.g. rv32I, rv32I_loads, rv32A",
        default=[]
    )

    parser.add_argument(
        "-eh", "--extract-hex",
        action="store_true",
        help="Also write a hexdump of the extracted instructions (with -e/-es)"
    )

    parser.add_argument(
        "-isa-csv",
        action="store_true",
        help="Save ISA instruction sets to CSV file"
    )

    parser.add_argument(
        "-list-sets",
        action="store_true",
        help="Print the known ISA sets/subsets and exit"
    )

    parser.add_argument(
        "-list-instr",
        nargs="*",
        metavar="set1, set2,",
        default=None,
        help="Print the instructions in the given ISA sets/subsets and exit"
    )

    parser.add_argument(
        "-list-core",
        nargs="*",
        metavar="core1, core2,",
        default=None,
        help="Print the known ISA extensions for the given CPU core(s) "
             "and exit"
    )

    return parser

def out_path(
    fileName: str
) -> str:
    '''
    Resolve a filename to the project's out/ directory, creating it if needed.

    :param fileName: Name of the file to resolve
    :type fileName: str
    :return: Absolute path to the file inside out/
    :rtype: str
    '''
    outDir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "out"
    )
    os.makedirs(outDir, exist_ok=True)

    return os.path.join(outDir, fileName)

def get_filePointer(fileName:str) -> TextIOWrapper:
    '''
    Open and return a file pointer for the specified assembly file.

    Attempts to open the file in read mode. If the file is not found,
    logs an error message and exits the program.

    :param fileName: Path to the assembly file to open
    :type fileName: str
    :return: File pointer to the opened file
    :rtype: TextIOWrapper
    :raises SystemExit: If the file cannot be found
    '''

    try:
        filePointer = open(fileName)
    except FileNotFoundError:
        logging.error("File not found, exiting...")
        sys.exit()

    logging.debug(f"Opened file: {fileName}")
    return filePointer

def resolve_compressed_mnemonic(instr: str, operands: str) -> str:
    '''
    Map a compressed (RVC) instruction's displayed objdump mnemonic to
    its real "c.*"/"cm.*" name.

    objdump always disassembles a compressed instruction using its
    base/pseudo-op alias, and for a few instructions that alias is
    ambiguous (or outright misleading) by mnemonic text alone:
    - "ret" is always the c.jr ra alias -- there's no separate "c.ret"
    - "addi" covers three different real instructions: c.addi16sp
      (destination and source are both literally "sp"), c.addi4spn
      (only the source is "sp"), and plain c.addi (neither is)
    - "lw"/"sw"/"flw"/"fsw"/"fld"/"fsd" each cover two real
      instructions -- the "...sp" (Zcf/Zcd/Zca stack-pointer) form
      when the memory operand's base register is literally "sp", else
      the plain (general-base) form
    Most other compressed instructions' displayed mnemonics map 1:1
    onto their real "c.*" name by simple prefixing. Zcmp/Zcmt's
    "cm.*" mnemonics are the exception to even that: objdump already
    prints their real, complete name, so they're returned unchanged
    rather than re-prefixed into nonsense like "c.cm.push".

    :param instr: The mnemonic objdump printed (e.g. "addi", "ret")
    :type instr: str
    :param operands: The raw operand text following the mnemonic, with
                      no whitespace (objdump's own format)
    :type operands: str
    :return: The instruction's real "c.*"/"cm.*" mnemonic
    :rtype: str
    '''
    if instr.startswith("cm."):
        return instr

    if instr == "ret":
        return "c.jr"

    if instr == "addi":
        rd, rs1 = operands.split(",")[:2]
        if rd == "sp" and rs1 == "sp":
            return "c.addi16sp"
        if rs1 == "sp":
            return "c.addi4spn"
        return "c.addi"

    if instr in ("lw", "sw", "flw", "fsw", "fld", "fsd"):
        base = operands.rsplit("(", 1)[-1].rstrip(")")
        if base == "sp":
            return f"c.{instr}sp"
        return f"c.{instr}"

    return f"c.{instr}"

# CSR pseudo-ops with an explicit destination register, where the CSR
# name is the second comma-separated operand (e.g. "csrr a0,mstatus")
_CSR_MNEMONICS_RD_FIRST = {
    "csrr", "csrrw", "csrrs", "csrrc", "csrrwi", "csrrsi", "csrrci",
}
# CSR pseudo-ops with no destination register (implicitly x0), where
# the CSR name is the first operand (e.g. "csrw hpmcounter5,a0")
_CSR_MNEMONICS_CSR_FIRST = {
    "csrw", "csrs", "csrc", "csrwi", "csrsi", "csrci",
}

def resolve_zihpm_mnemonic(instr: str, operands: str) -> str:
    '''
    Map a Zihpm hardware-performance-counter CSR access to a
    "rdhpmcounter<N>" (or "...h" for the RV32 upper half) label.

    Unlike Zicntr's cycle/time/instret, which objdump aliases to their
    own pseudo-op names (rdcycle etc.), a hpmcounter3-31 CSR access has
    no dedicated mnemonic -- it always disassembles as a generic CSR
    pseudo-op (e.g. "csrr a0,hpmcounter5"), indistinguishable by
    mnemonic text from any other CSR access (e.g. "csrr a0,mstatus").
    The CSR name has to be read from the operand text instead, at a
    position that depends on whether the pseudo-op has an explicit
    destination register (see _CSR_MNEMONICS_RD_FIRST/_CSR_FIRST).

    Every real access form (csrr, csrrs, csrrsi, csrw, ...) to the same
    counter collapses to one label, since a real 32-bit hpmcounter
    read/write is never meaningfully different from another for
    counting purposes here -- mirrors rdcycle/rdcycleh's single name
    per counter rather than one per instruction form.

    :param instr: The mnemonic objdump printed (e.g. "csrr", "csrw")
    :type instr: str
    :param operands: The raw operand text following the mnemonic, with
                      no whitespace (objdump's own format)
    :type operands: str
    :return: "rdhpmcounter<N>"/"rdhpmcounter<N>h" if this is a Zihpm
             CSR access, otherwise instr unchanged
    :rtype: str
    '''
    if instr in _CSR_MNEMONICS_RD_FIRST:
        parts = operands.split(",")
        csr = parts[1] if len(parts) > 1 else ""
    elif instr in _CSR_MNEMONICS_CSR_FIRST:
        csr = operands.split(",")[0]
    else:
        return instr

    if not csr.startswith("hpmcounter"):
        return instr

    suffix = csr[len("hpmcounter"):]
    isHigh = suffix.endswith("h")
    number = suffix[:-1] if isHigh else suffix
    if not number.isdigit() or not (3 <= int(number) <= 31):
        return instr

    return f"rdhpmcounter{number}" + ("h" if isHigh else "")

# Every "<mnemonic>.inx" label that appears in isa_rv32's zfinx/zdinx/
# zqinx/zhinx tables -- i.e. the set of real "<mnemonic>.inx" suffixed
# names resolve_inx_mnemonic() is allowed to produce. Derived directly
# from those tables (the single source of truth for which mnemonics
# have an "inx" counterpart) rather than duplicated here.
_INX_SUFFIXED = (
    set(isa_rv32.zfinx) | set(isa_rv32.zdinx)
    | set(isa_rv32.zqinx) | set(isa_rv32.zhinx)
)

def resolve_inx_mnemonic(instr: str, operands: str) -> str:
    '''
    Map an F/D/Q/Zfh-family instruction using integer registers to its
    "<mnemonic>.inx" label (Zfinx/Zdinx/Zqinx/Zhinx/Zhinxmin).

    Under Zfinx and its siblings, there's no separate floating-point
    register file -- the same F/D/Q/Zfh instructions read and write
    the integer registers instead. objdump prints the exact same
    mnemonic text either way (e.g. "fadd.s" whether it used fa0/fa1
    or a0/a1), so the only way to tell them apart is the operand
    text: a real F/D/Q/Zfh instruction always has at least one
    "f"-prefixed register operand (fa0, ft1, fs2, ...), since RISC-V's
    float ABI register names all start with "f" and its integer ones
    never do; an "inx" instruction has none.

    Loads/stores (flw, fld, ...) and the direct GPR<->FPR bit-move
    instructions (fmv.x.w, fmv.w.x, ...) have no "inx" equivalent at
    all -- see isa_rv32.py's _NO_INX_EQUIVALENT -- so they're left
    alone even though they also lack an "f"-prefixed operand in their
    own right (their destination is already an integer register in
    the real F/D/Q/Zfh form too).

    :param instr: The mnemonic objdump printed (e.g. "fadd.s")
    :type instr: str
    :param operands: The raw operand text following the mnemonic, with
                      no whitespace (objdump's own format)
    :type operands: str
    :return: "<mnemonic>.inx" if this is an inx-family instruction,
             otherwise instr unchanged
    :rtype: str
    '''
    suffixed = f"{instr}.inx"
    if suffixed not in _INX_SUFFIXED:
        return instr

    if any(tok.startswith("f") for tok in operands.split(",")):
        return instr

    return suffixed

def get_asmInstr(
    filePointer:TextIOWrapper
) -> dict:
    '''
    Parse assembly instructions from the file and count their occurrences.

    Reads through the assembly file line by line, extracts instruction
    mnemonics, and counts their frequency. Filters out invalid instructions
    based on:
    - Instructions that are all hexadecimal digits (raw data words objdump
      sometimes prints in place of a mnemonic), except real mnemonics that
      happen to consist entirely of hex-digit characters (see HEX_MNEMONICS)
    - Instructions starting with '.', '(', '@', or ')'
    - Instructions ending with '.'
    - Lines that don't have the expected format (address + instruction)
    - Opcode fields that aren't valid hex, or aren't 8 digits (32-bit)
      or 4 digits (16-bit compressed/RVC) wide

    A compressed (RVC) instruction is counted under its real "c.*"
    mnemonic (see resolve_compressed_mnemonic()), kept separate from
    its 32-bit counterpart even though objdump prints both the same way
    (e.g. c.li and li both print as "li"). A Zihpm hardware-performance-
    counter CSR access is counted under "rdhpmcounter<N>"/"...h" (see
    resolve_zihpm_mnemonic()), kept separate from an unrelated CSR
    access even though both print as the same generic CSR pseudo-op
    (e.g. "csrr a0,hpmcounter5" and "csrr a0,mstatus" both print "csrr").

    :param filePointer: Open file pointer to the assembly file
    :type filePointer: TextIOWrapper
    :return: Dictionary mapping instruction mnemonics to their counts,
             sorted alphabetically
    :rtype: dict
    '''

    instructions = {}

    for line in filePointer:
        splitLine = line.split()

        if len(splitLine) > 2:
            opcode = splitLine[1]
            instr = splitLine[2]

            is_hex_digits = all(c in string.hexdigits for c in instr)
            if is_hex_digits and instr not in HEX_MNEMONICS:
                continue

            if instr[0] in '.<()@':
                continue

            if instr.endswith('.'):
                continue

            is_valid_opcode = (
                len(opcode) in (4, 8)
                and all(c in string.hexdigits for c in opcode)
            )
            if is_valid_opcode:
                operands = splitLine[3] if len(splitLine) > 3 else ""
                if len(opcode) == 4:
                    instr = resolve_compressed_mnemonic(instr, operands)
                else:
                    instr = resolve_zihpm_mnemonic(instr, operands)
                    instr = resolve_inx_mnemonic(instr, operands)

                if instr not in instructions:
                    instructions.update({instr:1})
                else:
                    instructions[instr] = instructions[instr] + 1


    instructions = {
        k: v for k, v in sorted(
            instructions.items(), key=lambda item: item[0]
        )
    }

    return instructions

def get_splitInstr(
    instructions: dict,
    instrList: list
) -> list[str]:
    '''
    Filter a list of instructions to only include those present in the
    parsed file.

    Takes a list of instruction names and removes any that are not found
    in the parsed instructions dictionary, logging warnings for missing
    instructions.

    :param instructions: Dictionary of parsed instructions and their counts
    :type instructions: dict
    :param instrList: List of instruction names to filter
    :type instrList: list
    :return: Filtered list containing only instructions present in the file
    :rtype: list[str]
    '''
    newlist = instrList.copy()

    for instr in instrList:
        if instr not in instructions:
            logging.warning(
                f"Instruction \"{instr}\" is not present in the file..."
            )
            newlist.remove(instr)

    return newlist

def save_intructions(
    instructions:dict,
    output_name: str | None
) -> None:
    '''
    Save raw instruction counts to a CSV file.

    Creates a CSV file with instruction names in the first row and their
    corresponding counts in the second row. Uses the provided output name
    as a base for the filename if specified.

    :param instructions: Dictionary of instruction counts
    :type instructions: dict
    :param output_name: Base name for the output file (optional)
    :type output_name: str | None
    '''

    fileName = "instructions.csv"
    if output_name is not None:
        fileName = f"{output_name}.csv"
    fileName = out_path(fileName)

    with open(fileName, 'w') as fp:
        csvWriter = csv.writer(fp)
        csvWriter.writerow(instructions.keys())
        csvWriter.writerow(instructions.values())

    logging.debug(f"Wrote {len(instructions)} instruction(s) to {fileName}")
    return

def save_isa_sets_to_csv(
    isa_sets: dict,
    output_name: str | None
) -> None:
    '''
    Save ISA instruction set counts to a CSV file.

    Creates a CSV file with ISA set names in the first row and their
    corresponding counts in the second row. Unknown instructions are
    flattened with "unknown_" prefix. Uses the provided output name
    as a base for the filename if specified.

    :param isa_sets: Dictionary with ISA set names and their counts
    :type isa_sets: dict
    :param output_name: Base name for the output file (optional)
    :type output_name: str | None
    '''
    fileName = "isa_sets.csv"
    if output_name is not None:
        fileName = f"{output_name}_isa_sets.csv"
    fileName = out_path(fileName)

    # Build lists for CSV rows
    names = []
    counts = []

    for set_name, count in isa_sets.items():
        if isinstance(count, dict):
            # Handle unknown instructions (nested dict)
            for instr, cnt in count.items():
                names.append(f"{set_name}_{instr}")
                counts.append(cnt)
        else:
            names.append(set_name)
            counts.append(count)

    with open(fileName, 'w') as fp:
        csvWriter = csv.writer(fp)
        csvWriter.writerow(names)
        csvWriter.writerow(counts)

    logging.debug(f"Wrote {len(names)} ISA set entry(ies) to {fileName}")
    return

def get_isa_lists() -> dict[str, list[str]]:
    '''
    Assemble isa_rv32's per-category instruction tables into the
    RISC-V ISA extension set/subset mapping the rest of the tool uses.

    Each key is either a whole ISA extension (e.g. "rv32A") or one of its
    functional subsets (e.g. "rv32I_loads", "rv32M_mul"), mapped to the
    instruction mnemonics it contains. Subset keys must be named
    "<WholeSet>_<subset>", with no underscore in <WholeSet> itself --
    get_setInstr()'s prefix matching and print_isa_lists()'s grouping both
    split on the first underscore to recover the whole-set name.

    :return: Mapping of ISA set/subset names to their instruction mnemonics
    :rtype: dict[str, list[str]]
    '''
    return {
        # RV32I grouped by functional category
        "rv32I_logic": isa_rv32.rv32I_logic,
        "rv32I_addsub": isa_rv32.rv32I_addsub,
        "rv32I_shifts": isa_rv32.rv32I_shifts,
        "rv32I_comparisons": isa_rv32.rv32I_comparisons,
        "rv32I_jumps": isa_rv32.rv32I_jumps,
        "rv32I_branches": isa_rv32.rv32I_branches,
        "rv32I_loads": isa_rv32.rv32I_loads,
        "rv32I_stores": isa_rv32.rv32I_stores,
        "rv32I_other": isa_rv32.rv32I_other,
        "rv32M_mul": isa_rv32.rv32M_mul,
        "rv32M_div": isa_rv32.rv32M_div,
        "rv32M_rem": isa_rv32.rv32M_rem,
        "rv32A": isa_rv32.rv32A,
        "rv32F": isa_rv32.rv32F,
        "rv32D": isa_rv32.rv32D,
        "rv32Q": isa_rv32.rv32Q,
        # RV32B's 4 ratified sub-extensions -- see ISA_UMBRELLAS for how
        # "rv32B" maps to these
        "zba": isa_rv32.zba,
        "zbb": isa_rv32.zbb,
        "zbc": isa_rv32.zbc,
        "zbs": isa_rv32.zbs,
        # Scalar-crypto bitmanip -- zbb/zbc must stay listed above these
        # so they claim the instructions zbkb/zbkc intentionally share
        # with them first (same reasoning as zmmul below)
        "zbkb": isa_rv32.zbkb,
        "zbkc": isa_rv32.zbkc,
        "zbkx": isa_rv32.zbkx,
        "zmmul": isa_rv32.zmmul,
        "zicond": isa_rv32.zicond,
        "zfh": isa_rv32.zfh,
        # zfh must stay listed above this so it claims the 8
        # instructions zfhmin intentionally shares with it first (same
        # reasoning as zmmul above)
        "zfhmin": isa_rv32.zfhmin,
        "zfa": isa_rv32.zfa,
        "zfinx": isa_rv32.zfinx,
        "zdinx": isa_rv32.zdinx,
        "zqinx": isa_rv32.zqinx,
        "zhinx": isa_rv32.zhinx,
        # zhinx must stay listed above this so it claims the 4
        # instructions zhinxmin intentionally shares with it first
        # (same reasoning as zfhmin/zfh above)
        "zhinxmin": isa_rv32.zhinxmin,
        "zfbfmin": isa_rv32.zfbfmin,
        "zicsr": isa_rv32.zicsr,
        "zifencei": isa_rv32.zifencei,
        "zicntr": isa_rv32.zicntr,
        "zihpm": isa_rv32.zihpm,
        # RV32C's 3 real sub-extensions -- see ISA_UMBRELLAS for how
        # "rv32C" maps to these
        "zca": isa_rv32.zca,
        "zcf": isa_rv32.zcf,
        "zcd": isa_rv32.zcd,
        # Separate Zc-family extensions, not part of the rv32C umbrella
        "zcb": isa_rv32.zcb,
        "zcmp": isa_rv32.zcmp,
        "zcmt": isa_rv32.zcmt,
        # RV32V grouped by functional category, like RV32I/RV32M
        "rv32V_config": isa_rv32.rv32V_config,
        "rv32V_loads": isa_rv32.rv32V_loads,
        "rv32V_stores": isa_rv32.rv32V_stores,
        "rv32V_integer": isa_rv32.rv32V_integer,
        "rv32V_fixed_point": isa_rv32.rv32V_fixed_point,
        "rv32V_float": isa_rv32.rv32V_float,
        "rv32V_reduction": isa_rv32.rv32V_reduction,
        "rv32V_mask": isa_rv32.rv32V_mask,
        "rv32V_permute": isa_rv32.rv32V_permute,
        "rv32V_whole_reg": isa_rv32.rv32V_whole_reg,
        # Separate vector extensions, not part of the rv32V umbrella
        "zvfbfmin": isa_rv32.zvfbfmin,
        "zvfbfwma": isa_rv32.zvfbfwma,
    }

def print_isa_lists(isa_lists: dict[str, list[str]]) -> None:
    '''
    Print the known ISA sets/subsets, one whole set per line with its
    functional subsets (if any) tab-indented beneath it.

    A key with an underscore (e.g. "rv32I_loads") is treated as a subset
    of the whole set named by the part before the first underscore (e.g.
    "rv32I"); its instruction count is rolled up into that whole set's
    total. A key listed as a member in ISA_UMBRELLAS (e.g. "zba", under
    "rv32B") is grouped the same way, under its umbrella name instead of
    a shared prefix. A key that's neither has no subsets and is printed
    on its own.

    :param isa_lists: Mapping of set/subset names to instruction mnemonics
    :type isa_lists: dict[str, list[str]]
    '''
    subsetsOf: dict[str, list[str]] = {}
    grouped: set[str] = set()

    for name in isa_lists:
        if "_" in name:
            whole = name.split("_", 1)[0]
            subsetsOf.setdefault(whole, []).append(name)
            grouped.add(name)

    for umbrella, members in ISA_UMBRELLAS.items():
        subsetsOf.setdefault(umbrella, []).extend(members)
        grouped.update(members)

    tops = (set(isa_lists) - grouped) | set(subsetsOf)

    for name in sorted(tops):
        if name in subsetsOf:
            subs = sorted(subsetsOf[name])
            total = sum(len(isa_lists[sub]) for sub in subs)
            print(f"{name} ({total} instructions)")
            for sub in subs:
                print(f"\t{sub} ({len(isa_lists[sub])} instructions)")
        else:
            print(f"{name} ({len(isa_lists[name])} instructions)")

def print_core_extensions(core_names: list[str]) -> None:
    '''
    Print the known RISC-V ISA extensions for one or more named CPU
    cores, from isa_rv32.CORE_PROFILES.

    Matching is case-insensitive. This is reference data about
    specific silicon/RTL designs (see CORE_PROFILES's comment for
    sourcing), not something derived from get_isa_lists() or real
    disassembly. Extension names shown match this tool's own
    -es/-list-instr keys wherever a matching table exists, so they can
    be used directly with those flags. A name that matches no known
    core is logged as a warning and skipped.

    :param core_names: Core names to look up
    :type core_names: list[str]
    '''
    for name in core_names:
        profile = CORE_PROFILES.get(name.lower())
        if profile is None:
            logging.warning(f'Unknown core "{name}", skipping...')
            continue

        print(name)
        for label, key in (
            ("base", "base"),
            ("always", "always"),
            ("optional", "optional"),
            ("not supported", "not_supported"),
            ("custom (not tracked by this tool)", "custom"),
        ):
            items = profile.get(key)
            if not items:
                continue
            print(f"\t{label}:")
            for item in items:
                print(f"\t\t{item}")
        print(f"\tsource: {profile['source']}")

def save_instuction_sets(
    instructions: dict
) -> dict:
    '''
    Categorize instructions into RISC-V ISA extension sets and count
    occurrences.

    Takes a dictionary of instruction counts and categorizes each instruction
    into its corresponding RISC-V ISA extension (RV32I, RV32M, RV32A, etc.).
    Instructions that don't match any known ISA set are collected under
    "unknown".

    :param instructions: Dictionary of instruction counts from parsing
    :type instructions: dict
    :return: Dictionary with ISA set names as keys and their total counts
             as values. Unknown instructions are stored as a nested dict
             under "unknown" key.
    :rtype: dict
    '''
    isa_lists = get_isa_lists()

    # initialise counters for every set
    isaSets: dict[str, int] = {name: 0 for name in isa_lists}
    unknown: dict[str, int] = {}

    # tally
    for instr, cnt in instructions.items():
        matched = False
        for setname, ops in isa_lists.items():
            if instr in ops:
                isaSets[setname] += cnt
                matched = True
                break
        if not matched:
            unknown[instr] = cnt

    if len(unknown) > 0:
        isaSets["unknown"] = unknown

    return isaSets

def get_setInstr(
    setNames: list,
    isa_lists: dict
) -> list[str]:
    '''
    Resolve ISA extension set/subset names to the instruction mnemonics
    they contain.

    Matching is case-insensitive. A name may refer to an exact set/subset key
    (e.g. "rv32A", "rv32I_loads"), to a whole set made up of several
    functional subsets sharing its name as a prefix (e.g. "rv32I" expands
    to every rv32I_* subset), or to an umbrella of independently-named
    sets listed in ISA_UMBRELLAS (e.g. "rv32B" expands to Zba/Zbb/Zbc/Zbs).
    Names that match nothing are logged as warnings and skipped.

    :param setNames: ISA set or subset names to resolve
    :type setNames: list
    :param isa_lists: Mapping of set/subset names to instruction mnemonics
    :type isa_lists: dict
    :return: Deduplicated list of instruction mnemonics from the matched sets
    :rtype: list[str]
    '''
    lowerKeys = {key.lower(): key for key in isa_lists}
    lowerUmbrellas = {
        name.lower(): members for name, members in ISA_UMBRELLAS.items()
    }

    instrs: list[str] = []
    seen: set[str] = set()

    for name in setNames:
        lname = name.lower()

        if lname in lowerKeys:
            matchedKeys = [lowerKeys[lname]]
        elif lname in lowerUmbrellas:
            matchedKeys = lowerUmbrellas[lname]
        else:
            prefix = f"{lname}_"
            matchedKeys = [
                key for lkey, key in lowerKeys.items()
                if lkey.startswith(prefix)
            ]

        if not matchedKeys:
            logging.warning(
                f"ISA set \"{name}\" does not match any known set or "
                "subset..."
            )
            continue

        for key in matchedKeys:
            for instr in isa_lists[key]:
                if instr not in seen:
                    seen.add(instr)
                    instrs.append(instr)

    return instrs

def extractInstr(
    instrList: list,
    filePointer: TextIOWrapper,
    output_name: str | None = None
):
    '''
    Extract specific instructions from the assembly file to a new file.

    Reads through the assembly file and writes lines containing the specified
    instructions to '<output_name>.asm', or 'extraction.asm' if no output
    name is given. Only includes lines that match the expected format and
    contain instructions from the provided list. A compressed (RVC) line or
    a Zihpm hpmcounter CSR access is matched against its real resolved
    mnemonic (see resolve_compressed_mnemonic()/resolve_zihpm_mnemonic()),
    same as get_asmInstr(), even though the written line keeps objdump's
    own displayed text unchanged.

    :param instrList: List of instruction mnemonics to extract
    :type instrList: list
    :param filePointer: Open file pointer to the assembly file
    :type filePointer: TextIOWrapper
    :param output_name: Base name for the output file (optional)
    :type output_name: str | None
    '''
    fileName = "extraction.asm"
    if output_name is not None:
        fileName = f"{output_name}.asm"

    resolvedPath = out_path(fileName)
    fp = open(resolvedPath, 'w')

    filePointer.seek(0)

    written = 0
    for line in filePointer:
        splitLine = line.split()

        if len(splitLine) > 2:
            opcode = splitLine[1]
            instr = splitLine[2]

            is_valid_opcode = (
                len(opcode) in (4, 8)
                and all(c in string.hexdigits for c in opcode)
            )
            if is_valid_opcode:
                operands = splitLine[3] if len(splitLine) > 3 else ""
                if len(opcode) == 4:
                    matchInstr = resolve_compressed_mnemonic(
                        instr, operands
                    )
                else:
                    matchInstr = resolve_zihpm_mnemonic(instr, operands)
                    matchInstr = resolve_inx_mnemonic(matchInstr, operands)

                if matchInstr in instrList:
                    fp.write(' '.join(splitLine[2:])+'\n')
                    written += 1

    fp.close()
    logging.debug(f"Wrote {written} line(s) to {resolvedPath}")

def extractHex(
    instrList: list,
    filePointer: TextIOWrapper,
    output_name: str | None = None
):
    '''
    Extract the raw machine code of specific instructions to a hexdump file.

    Reads through the assembly file and writes the little-endian bytes of
    each matching instruction's opcode, one instruction per line, in the
    same file order as extractInstr(). objdump prints each opcode in
    human-reading order (e.g. "00000513"); this converts it to the
    little-endian memory byte order (e.g. "13 05 00 00") used by disasm.sh's
    own <name>.mem, so the two stay consistent. A line has 4 bytes for a
    32-bit instruction or 2 bytes for a 16-bit compressed (RVC) one, so
    lines are not fixed-width -- each carries exactly the instruction's
    real encoded size. A compressed line or a Zihpm hpmcounter CSR
    access is matched against its real resolved mnemonic, same as
    get_asmInstr() -- see resolve_compressed_mnemonic()/
    resolve_zihpm_mnemonic().

    :param instrList: List of instruction mnemonics to extract
    :type instrList: list
    :param filePointer: Open file pointer to the assembly file
    :type filePointer: TextIOWrapper
    :param output_name: Base name for the output file (optional)
    :type output_name: str | None
    '''
    fileName = "extraction.mem"
    if output_name is not None:
        fileName = f"{output_name}.mem"

    resolvedPath = out_path(fileName)
    fp = open(resolvedPath, 'w')

    filePointer.seek(0)

    written = 0
    for line in filePointer:
        splitLine = line.split()

        if len(splitLine) > 2:
            opcode = splitLine[1]
            instr = splitLine[2]

            is_valid_opcode = (
                len(opcode) in (4, 8)
                and all(c in string.hexdigits for c in opcode)
            )
            matchInstr = instr
            if is_valid_opcode:
                operands = splitLine[3] if len(splitLine) > 3 else ""
                if len(opcode) == 4:
                    matchInstr = resolve_compressed_mnemonic(
                        instr, operands
                    )
                else:
                    matchInstr = resolve_zihpm_mnemonic(instr, operands)
                    matchInstr = resolve_inx_mnemonic(matchInstr, operands)

            if is_valid_opcode and matchInstr in instrList:
                beBytes = bytes.fromhex(opcode)
                leBytes = beBytes[::-1]
                fp.write(' '.join(f'{b:02x}' for b in leBytes) + '\n')
                written += 1

    fp.close()
    logging.debug(f"Wrote {written} line(s) to {resolvedPath}")

def main():
    '''
    Main entry point for the RISC-V assembly parser.

    Orchestrates the parsing process:
    1. Sets up logging and parses command-line arguments
    2. If -list-sets, -list-instr, or -list-core was given, prints the
       requested ISA set/instruction/core info and exits
    3. Opens and parses the assembly file
    4. Optionally saves raw instruction counts to CSV
    5. Optionally extracts specific instructions (and their hexdump, with -eh)
       to separate files
    6. Optionally categorizes instructions by ISA extension and saves the
       counts to CSV

    See setupArgeparse() for the full flag list, or run with -h/--help.
    '''
    logger = setupLogger()
    parser = setupArgeparse()
    args = parser.parse_args()

    # -list-sets: print every known ISA set/subset and exit, no file needed
    if args.list_sets:
        print_isa_lists(get_isa_lists())
        return

    # -list-instr: print the instructions in the given set(s)/subset(s)
    # and exit, no file needed
    if args.list_instr is not None:
        if len(args.list_instr) == 0:
            parser.error(
                "-list-instr requires at least one set/subset name"
            )
        instrs = get_setInstr(args.list_instr, get_isa_lists())
        if len(instrs) == 0:
            logger.error(
                "No instructions matched the given set(s)/subset(s)"
            )
            return
        for instr in instrs:
            print(instr)
        return

    # -list-core: print the known ISA extensions for the given CPU
    # core(s) and exit, no file needed
    if args.list_core is not None:
        if len(args.list_core) == 0:
            parser.error("-list-core requires at least one core name")
        print_core_extensions(args.list_core)
        return

    # everything below here parses an actual assembly file
    if args.input_file is None:
        parser.error("input_file is required")

    # parse the file into a {instruction: count} dictionary
    filePointer = get_filePointer(args.input_file)
    instructions = get_asmInstr(filePointer)
    total = sum(instructions.values())
    logger.debug(
        f"Parsed {len(instructions)} distinct instruction(s), "
        f"{total} total occurrence(s)"
    )

    # base name shared by every output file this run produces
    output_name = None
    if args.output_name is not None:
        output_name = args.output_name
        logger.debug(f"Output name: {output_name}")

    # -csv: save the raw instruction counts
    if args.csv == True:
        save_intructions(instructions, output_name)

    # resolve which instructions to extract, from -e and/or -es combined
    iList = []
    if len(args.extract) != 0:
        iList += get_splitInstr(instructions, args.extract)

    if len(args.extract_set) != 0:
        setInstr = get_setInstr(args.extract_set, get_isa_lists())
        iList += [instr for instr in setInstr if instr in instructions]

    iList = list(dict.fromkeys(iList))

    extractionRequested = len(args.extract) != 0 or len(args.extract_set) != 0

    # -eh only makes sense alongside an actual extraction
    if args.extract_hex and not extractionRequested:
        logger.warning(
            '-eh/--extract-hex has no effect without -e/--extract '
            'or -es/--extract-set'
        )

    # write the extracted instructions (.asm) and, with -eh, their
    # hexdump (.mem)
    if extractionRequested:
        if len(iList) == 0:
            logger.error('No valid instructions to be extracted')
            return
        else:
            logger.info(f'Instructions: {iList}')

        extractInstr(iList, filePointer, output_name)
        if args.extract_hex:
            extractHex(iList, filePointer, output_name)
    filePointer.close()

    # -isa-csv: categorize instructions by ISA extension and save the counts
    if args.isa_csv:
        isa_sets = save_instuction_sets(instructions)
        categorized = sum(
            v for v in isa_sets.values() if not isinstance(v, dict)
        )
        unknownCount = len(isa_sets.get("unknown", {}))
        logger.debug(
            f"Categorized {categorized} instruction occurrence(s) "
            f"across ISA sets, {unknownCount} unknown mnemonic(s)"
        )
        save_isa_sets_to_csv(isa_sets, output_name)

if __name__ == "__main__":
    main()