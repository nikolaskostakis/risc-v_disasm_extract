# Author:  Nikolaos Kostakis
# Version: 1.3
#
# Usage:
#   make ELF=path/to/test1.out [NAME=name]          # full pipeline: disasm + profiler
#   make disasm ELF=path/to/test1.out [NAME=name]
#   make profiler ASM=out/test1.asm [NAME=name]
#   make clean
#   make help                                       # describe targets and variables

PYTHON         ?= python3
SRC_DIR        := src
OUT_DIR        := out

ELF            ?=
NAME           ?=
DEST           ?=
DISASM_FLAGS   ?=
PROFILER_FLAGS ?= -isa-csv

NAME_FLAG := $(if $(NAME),-o $(NAME))
ASM_NAME  := $(if $(NAME),$(NAME),$(basename $(notdir $(ELF))))
ifneq ($(ASM_NAME),)
	ASM ?= $(OUT_DIR)/$(ASM_NAME).asm
endif

.PHONY: all disasm profiler check test clean help

all: disasm profiler

test:
	$(PYTHON) -m unittest discover -s tests -v

check:
	@$(SRC_DIR)/disasm.sh --check
	@ver="$$($(PYTHON) -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"; \
	if [ -z "$$ver" ]; then \
		echo "Error: '$(PYTHON)' not found or not runnable" >&2; \
		exit 1; \
	fi; \
	if ! $(PYTHON) -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then \
		echo "Error: Python 3.10+ required, found $$ver" >&2; \
		exit 1; \
	fi; \
	echo "Python $$ver found (>= 3.10 required)"

help:
	@echo "Disassembles a RISC-V ELF and profiles/extracts instructions from it."
	@echo ""
	@echo "Targets:"
	@echo "  all (default)  Full pipeline: Disasembler and Profiler"
	@echo "  disasm         Disassemble ELF to out/<name>.asm and out/<name>.mem"
	@echo "  profiler       Parse an .asm file, categorize/count instructions"
	@echo "  check          Check for required RISC-V tools and Python version"
	@echo "  test           Run the test suite for the Profiler"
	@echo "  clean          Remove generated files from out/"
	@echo "  help           Show usage"
	@echo ""
	@echo "Variables:"
	@echo "  ELF             Input ELF file (required for disasm, and all unless ASM is set)"
	@echo "  NAME            Output base name shared by both tools (optional)"
	@echo "  ASM             Input .asm file for Profiler (optional; default: out/<NAME or ELF>.asm)"
	@echo "  DEST            Destination directory to copy output files to (optional; default: no copy)"
	@echo "  DISASM_FLAGS    Flags passed to Disassembler, e.g. -endian big (default: none)"
	@echo "  PROFILER_FLAGS  Flags passed to Profiler (default: -isa-csv)"
	@echo ""
	@echo "Disassembler options (DISASM_FLAGS, or run directly, e.g. src/disasm.sh -h):"
	@echo "  -h, --help          Show usage and exit"
	@echo "  -v, --version       Print the tool's version and exit"
	@echo "  -c, --check         Check required tools are on PATH and exit"
	@echo "  -endian little|big  Byte order for the .mem hex dump (default: little)"
	@echo "                      big only makes sense for a binary with no compressed"
	@echo "                      (RVC) instructions -- warns if the ELF reports C/Zca"
	@echo ""
	@echo "PROFILER_FLAGS options (isa_profiler.py):"
	@echo "  -h, --help                   Show usage and exit"
	@echo "  -o, --output-name NAME       Base name for output files (same as NAME above)"
	@echo "  -csv                         Save raw instruction counts to CSV"
	@echo "  -isa-csv                     Save per-ISA-extension instruction counts to CSV"
	@echo "  -e, --extract I1 I2 ..       Extract given instructions to a separate .asm file"
	@echo "  -es, --extract-set S1 S2 ..  Extract ISA sets/subsets, e.g. rv32I, rv32I_loads, rv32A"
	@echo "  -eh, --extract-hex           Write a hexdump of the extracted instructions"
	@echo "                               Works in conjunction with -e/--extract or -es/--extract-set"
	@echo "  -endian little|big           Byte order for -eh's hex dump (default: little)"
	@echo "                               Works in conjunction with -eh/--extract-hex"
	@echo "  -list-sets                   Print the supported ISA sets/subsets and exit"
	@echo "  -list-instr S1 S2 ..         Print instructions in the given set(s)/subset(s) and exit"
	@echo "  -list-core C1 C2 ..          Print known ISA extensions for the given CPU core(s) and exit"
	@echo "  -v, --version                Print tool's version and exit"
	@echo ""

disasm:
	@if [ -z "$(ELF)" ]; then \
		echo "ELF is required, e.g. make disasm ELF=path/to/test1.out" >&2; \
		exit 1; \
	fi
	@mkdir -p $(OUT_DIR)
	@if [ -n "$(DEST)" ]; then \
		find $(OUT_DIR) -mindepth 1 ! -name README.md -delete; \
	fi
	$(SRC_DIR)/disasm.sh $(ELF) $(NAME) $(DISASM_FLAGS)
	@if [ -n "$(DEST)" ]; then \
		mkdir -p "$(DEST)"; \
		find $(OUT_DIR) -mindepth 1 ! -name README.md -exec cp -p {} "$(DEST)/" \; ; \
		echo "Copied output to '$(DEST)'"; \
	fi

profiler:
	@if [ -z "$(ASM)" ]; then \
		echo "ASM (or ELF) is required, e.g. make profiler ASM=out/test1.asm" >&2; \
		exit 1; \
	fi
	@mkdir -p $(OUT_DIR)
	@if [ -n "$(DEST)" ]; then \
		find $(OUT_DIR) -mindepth 1 ! -name README.md ! -samefile "$(ASM)" -delete 2>/dev/null; \
	fi
	$(PYTHON) $(SRC_DIR)/isa_profiler.py $(ASM) $(NAME_FLAG) $(PROFILER_FLAGS)
	@if [ -n "$(DEST)" ]; then \
		mkdir -p "$(DEST)"; \
		find $(OUT_DIR) -mindepth 1 ! -name README.md ! -samefile "$(ASM)" -exec cp -p {} "$(DEST)/" \; ; \
		echo "Copied output to '$(DEST)'"; \
	fi

clean:
	rm -f $(OUT_DIR)/*.asm $(OUT_DIR)/*.csv $(OUT_DIR)/*.mem
