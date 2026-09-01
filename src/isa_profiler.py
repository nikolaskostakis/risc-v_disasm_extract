"""
RISC-V instruction counter and ISA extension profiler
"""
__author__ = "Nikolaos Kostakis"
__version__ = "1.2"

import os
import sys
import pprint
import csv
import logging
import argparse
import string

from io import TextIOWrapper
from logging import Logger

def setupLogger() -> Logger:
    '''
    Set up and configure the logging system with colored output.
    
    Creates a logger with a custom ANSI color formatter that provides
    colored output for different log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL).
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
    #logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    return logger

def setupArgeparse() -> argparse.ArgumentParser:
    '''
    Set up and configure the command-line argument parser.
    
    Creates an ArgumentParser with the following arguments:
    - input_file: Positional argument for the assembly file to parse (not
      required when -list-sets is given)
    - -o/--output-name: Optional base name for output files
    - -csv: Flag to save raw instruction counts to CSV
    - -e/--extract: List of instructions to extract to a separate file
    - -es/--extract-set: List of ISA sets/subsets to extract to a separate file
    - -isa-csv: Flag to save ISA instruction set counts to CSV
    - -list-sets: Flag to print the known ISA sets/subsets and exit
    - --version: Flag to print the tool's version and exit

    :return: Configured argument parser
    :rtype: argparse.ArgumentParser
    '''
    parser = argparse.ArgumentParser(description="RISC-V Instruction Counter and ISA Extension Profiler")

    parser.add_argument(
        "--version",
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
        "-isa-csv",
        action="store_true",
        help="Save ISA instruction sets to CSV file"
    )

    parser.add_argument(
        "-list-sets", "--list-sets",
        action="store_true",
        help="Print the known ISA sets/subsets and exit"
    )

    return parser

def out_path(fileName: str) -> str:
    '''
    Resolve a filename to the project's out/ directory, creating it if needed.

    :param fileName: Name of the file to resolve
    :type fileName: str
    :return: Absolute path to the file inside out/
    :rtype: str
    '''
    outDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
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
    
    return filePointer

def get_asmInstr(filePointer:TextIOWrapper) -> dict:
    '''
    Parse assembly instructions from the file and count their occurrences.
    
    Reads through the assembly file line by line, extracts instruction mnemonics,
    and counts their frequency. Filters out invalid instructions based on:
    - Instructions that are all hexadecimal digits
    - Instructions starting with '.', '(', '@', or ')'
    - Instructions ending with '.'
    - Lines that don't have the expected format (address + instruction)
    
    :param filePointer: Open file pointer to the assembly file
    :type filePointer: TextIOWrapper
    :return: Dictionary mapping instruction mnemonics to their counts, sorted alphabetically
    :rtype: dict
    '''

    instructions = {}

    for line in filePointer:
        splitLine = line.split()

        if len(splitLine) > 2:
            instr = splitLine[2]

            if all(char in string.hexdigits for char in instr):
                continue

            if instr[0] in '.<()@':
                continue

            if instr.endswith('.'):
                continue

            if (len(splitLine[1]) == 8):
                if instr not in instructions:
                    instructions.update({instr:1})
                else:
                    instructions[instr] = instructions[instr] + 1

    
    instructions = {k: v for k, v in sorted(instructions.items(), key=lambda item: item[0])}

    return instructions

def get_splitInstr(instructions: dict, instrList: list) -> list[str]:
    '''
    Filter a list of instructions to only include those present in the parsed file.
    
    Takes a list of instruction names and removes any that are not found
    in the parsed instructions dictionary, logging warnings for missing instructions.
    
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
            logging.warning(f"Instruction \"{instr}\" is not present in the file...")
            newlist.remove(instr)
    
    return newlist

def save_intructions(instructions:dict, output_name: str | None) -> None:
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

    with open(out_path(fileName), 'w') as fp:
        csvWriter = csv.writer(fp)
        csvWriter.writerow(instructions.keys())
        csvWriter.writerow(instructions.values())

    return

def save_isa_sets_to_csv(isa_sets: dict, output_name: str | None) -> None:
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

    return

def get_isa_lists() -> dict[str, list[str]]:
    '''
    Build the RISC-V ISA extension set/subset instruction lists.

    Each key is either a whole ISA extension (e.g. "rv32A") or one of its
    functional subsets (e.g. "rv32I_loads", "rv32M_mul"), mapped to the
    instruction mnemonics it contains.

    :return: Mapping of ISA set/subset names to their instruction mnemonics
    :rtype: dict[str, list[str]]
    '''
    # RV32I Base Integer Instructions (grouped by functional category)
    # Logic operations (and/or/xor and their immediate forms)
    rv32I_logic = [
        "and", "or", "xor", "andi", "ori", "xori",
        # Pseudo-ops that map to logic operations
        "not", "mv", "zext.b", "zext.h"
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
        "amoswap.w.aq", "amoadd.w.aq", "amoxor.w.aq", "amoand.w.aq", "amoor.w.aq",
        "amomin.w.aq", "amomax.w.aq", "amominu.w.aq", "amomaxu.w.aq",
        
        # With release (rl) ordering
        "lr.w.rl", "sc.w.rl",
        "amoswap.w.rl", "amoadd.w.rl", "amoxor.w.rl", "amoand.w.rl", "amoor.w.rl",
        "amomin.w.rl", "amomax.w.rl", "amominu.w.rl", "amomaxu.w.rl",
        
        # With acquire-release (aqrl) ordering
        "lr.w.aqrl", "sc.w.aqrl",
        "amoswap.w.aqrl", "amoadd.w.aqrl", "amoxor.w.aqrl", "amoand.w.aqrl", "amoor.w.aqrl",
        "amomin.w.aqrl", "amomax.w.aqrl", "amominu.w.aqrl", "amomaxu.w.aqrl"
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

    # RV32C Compressed Instructions Extension
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
        "c.mv", "c.ebreak"
    ]

    # RV32B Bit Manipulation Extension
    rv32B = [
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
        "orc.b", "rev8",
        
        # Carry-less multiplication
        "clmul", "clmulh", "clmulr",
        
        # Bit set operations
        "bset", "bseti",
        
        # Bit clear operations
        "bclr", "bclri",
        
        # Bit invert operations
        "binv", "binvi",
        
        # Bit extract operations
        "bext", "bexti",
        
        # Shift and add operations
        "sh1add", "sh2add", "sh3add"
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

    return {
        # RV32I grouped by functional category
        "rv32I_logic": rv32I_logic,
        "rv32I_addsub": rv32I_addsub,
        "rv32I_shifts": rv32I_shifts,
        "rv32I_comparisons": rv32I_comparisons,
        "rv32I_jumps": rv32I_jumps,
        "rv32I_branches": rv32I_branches,
        "rv32I_loads": rv32I_loads,
        "rv32I_stores": rv32I_stores,
        "rv32I_other": rv32I_other,
        "rv32M_mul": rv32M_mul,
        "rv32M_div": rv32M_div,
        "rv32M_rem": rv32M_rem,
        "rv32A": rv32A,
        "rv32F": rv32F,
        "rv32D": rv32D,
        "rv32C": rv32C,
        "rv32B": rv32B,
        "zicsr": zicsr,
        "zifencei": zifencei,
        "zicntr": zicntr,
    }

def save_instuction_sets(instructions: dict) -> dict:
    '''
    Categorize instructions into RISC-V ISA extension sets and count occurrences.

    Takes a dictionary of instruction counts and categorizes each instruction
    into its corresponding RISC-V ISA extension (RV32I, RV32M, RV32A, etc.).
    Instructions that don't match any known ISA set are collected under "unknown".

    :param instructions: Dictionary of instruction counts from parsing
    :type instructions: dict
    :return: Dictionary with ISA set names as keys and their total counts as values.
             Unknown instructions are stored as a nested dict under "unknown" key.
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

def get_setInstr(setNames: list, isa_lists: dict) -> list[str]:
    '''
    Resolve ISA extension set/subset names to the instruction mnemonics they contain.

    Matching is case-insensitive. A name may refer to an exact set/subset key
    (e.g. "rv32A", "rv32I_loads") or to a whole set made up of several
    functional subsets (e.g. "rv32I" expands to every rv32I_* subset).
    Names that match nothing are logged as warnings and skipped.

    :param setNames: ISA set or subset names to resolve
    :type setNames: list
    :param isa_lists: Mapping of set/subset names to instruction mnemonics
    :type isa_lists: dict
    :return: Deduplicated list of instruction mnemonics from the matched sets
    :rtype: list[str]
    '''
    lowerKeys = {key.lower(): key for key in isa_lists}

    instrs: list[str] = []
    seen: set[str] = set()

    for name in setNames:
        lname = name.lower()

        if lname in lowerKeys:
            matchedKeys = [lowerKeys[lname]]
        else:
            prefix = f"{lname}_"
            matchedKeys = [key for lkey, key in lowerKeys.items() if lkey.startswith(prefix)]

        if not matchedKeys:
            logging.warning(f"ISA set \"{name}\" does not match any known set or subset...")
            continue

        for key in matchedKeys:
            for instr in isa_lists[key]:
                if instr not in seen:
                    seen.add(instr)
                    instrs.append(instr)

    return instrs

def extractInstr(instrList: list, filePointer:TextIOWrapper, output_name: str | None = None):
    '''
    Extract specific instructions from the assembly file to a new file.

    Reads through the assembly file and writes lines containing the specified
    instructions to '<output_name>.asm', or 'extraction.asm' if no output
    name is given. Only includes lines that match the expected format and
    contain instructions from the provided list.

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

    fp = open(out_path(fileName), 'w')

    filePointer.seek(0)

    for line in filePointer:
        splitLine = line.split()

        if len(splitLine) > 2:
            instr = splitLine[2]

            if (len(splitLine[1]) == 8):
                if instr in instrList:
                    fp.write(' '.join(splitLine[2:])+'\n')

    fp.close()

def main():
    '''
    Main entry point for the RISC-V assembly parser.
    
    Orchestrates the parsing process:
    1. Sets up logging
    2. Parses command-line arguments
    3. Opens and parses the assembly file
    4. Optionally saves raw instruction counts to CSV
    5. Categorizes instructions by ISA extension
    6. Optionally saves ISA set counts to CSV
    7. Optionally extracts specific instructions to a file
    
    Command-line usage:
    python isa_profiler.py input_file [options]
    
    Options:
    -o OUTPUT_NAME    Base name for output files
    -csv              Save raw instruction counts to CSV
    -isa-csv          Save ISA instruction set counts to CSV
    -e INSTR...       Extract specific instructions to file
    -es SET...        Extract instructions from ISA sets/subsets to file
    -list-sets        Print the known ISA sets/subsets and exit
    --version         Print the tool's version and exit
    '''
    logger = setupLogger()
    parser = setupArgeparse()
    args = parser.parse_args()

    if args.list_sets:
        isa_lists = get_isa_lists()
        for name in sorted(isa_lists):
            print(f"{name} ({len(isa_lists[name])} instructions)")
        return

    if args.input_file is None:
        parser.error("input_file is required")

    filePointer = get_filePointer(args.input_file)
    instructions = get_asmInstr(filePointer)
    #pprint.pprint(instructions)

    output_name = None
    if args.output_name is not None:
        output_name = args.output_name
        print(output_name)

    if args.csv == True:
        save_intructions(instructions, output_name)

    iList = []
    if len(args.extract) != 0:
        iList += get_splitInstr(instructions, args.extract)

    if len(args.extract_set) != 0:
        setInstr = get_setInstr(args.extract_set, get_isa_lists())
        iList += [instr for instr in setInstr if instr in instructions]

    iList = list(dict.fromkeys(iList))

    if len(args.extract) != 0 or len(args.extract_set) != 0:
        if len(iList) == 0:
            logger.error('No valid instructions to be extracted')
            return
        else:
            logger.info(f'Instructions: {iList}')

        extractInstr(iList, filePointer, output_name)
    filePointer.close()


    if args.isa_csv:
        isa_sets = save_instuction_sets(instructions)
        #pprint.pprint(isa_sets)
        save_isa_sets_to_csv(isa_sets, output_name)

if __name__ == "__main__":
    main()