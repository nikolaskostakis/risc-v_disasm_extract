# Author:  Nikolaos Kostakis
# Version: 1.1
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
PROFILER_FLAGS ?= -isa-csv

NAME_FLAG := $(if $(NAME),-o $(NAME))
ASM_NAME  := $(if $(NAME),$(NAME),$(basename $(notdir $(ELF))))
ifneq ($(ASM_NAME),)
ASM ?= $(OUT_DIR)/$(ASM_NAME).asm
endif

.PHONY: all disasm profiler check clean help

all: disasm profiler

check:
	@$(SRC_DIR)/disasm.sh --check
	@ver="$$($(PYTHON) -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)"; if [ -z "$$ver" ]; then echo "Error: '$(PYTHON)' not found or not runnable" >&2; exit 1; fi; if ! $(PYTHON) -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then echo "Error: Python 3.10+ required, found $$ver" >&2; exit 1; fi; echo "Python $$ver found (>= 3.10 required)"

help:
	@echo "Disassembles a RISC-V ELF and profiles/extracts instructions from it."
	@echo ""
	@echo "Targets:"
	@echo "  all (default)  Full pipeline: disasm then profiler"
	@echo "  disasm         Disassemble ELF to out/<name>.asm and out/<name>.hexdump.asm"
	@echo "  profiler       Parse an .asm file, categorize/count instructions"
	@echo "  check          Check disasm.sh's required tools and the Python version"
	@echo "  clean          Remove generated files from out/"
	@echo "  help           Show this message"
	@echo ""
	@echo "Variables:"
	@echo "  ELF             Input ELF file (required for disasm, and all unless ASM is set)"
	@echo "  ASM             Input .asm file for profiler (default: out/<NAME or ELF basename>.asm)"
	@echo "  NAME            Output base name shared by both tools (optional; each tool"
	@echo "                  falls back to its own default naming if omitted)"
	@echo "  DEST            If set, also copy whatever files a target newly wrote to"
	@echo "                  out/ into this directory (created if missing)"
	@echo "  PROFILER_FLAGS  Flags passed to isa_profiler.py (default: -isa-csv)"
	@echo ""
	@echo "disasm.sh options (run directly, e.g. src/disasm.sh -h):"
	@echo "  -h, --help     Show usage and exit"
	@echo "  -v, --version  Print the tool's version and exit"
	@echo "  -c, --check    Check required tools are on PATH and exit"
	@echo "                 (make check runs this, then also checks the Python version)"
	@echo ""
	@echo "PROFILER_FLAGS options (isa_profiler.py):"
	@echo "  -o, --output-name NAME       Base name for output files (same as NAME above)"
	@echo "  -csv                         Save raw instruction counts to CSV"
	@echo "  -isa-csv                     Save per-ISA-extension instruction counts to CSV"
	@echo "  -e, --extract I1 I2 ..       Extract given instructions to a separate .asm file"
	@echo "  -es, --extract-set S1 S2 ..  Extract ISA sets/subsets, e.g. rv32I, rv32I_loads, rv32A"
	@echo "  -list-sets                   Print the known ISA sets/subsets and exit"
	@echo "  --version                    Print the tool's version and exit"
	@echo ""
	@echo "Examples:"
	@echo "  make ELF=path/to/test1.out"
	@echo "  make ELF=path/to/test1.out NAME=myrun PROFILER_FLAGS=\"-csv -isa-csv\""
	@echo "  make ELF=path/to/test1.out PROFILER_FLAGS=\"-es rv32I rv32A\""
	@echo "  make disasm ELF=path/to/test1.out"
	@echo "  make profiler ASM=out/test1.asm"
	@echo "  make check"
	@echo "  make ELF=path/to/test1.out DEST=/tmp/results"

disasm:
	@if [ -z "$(ELF)" ]; then echo "ELF is required, e.g. make disasm ELF=path/to/test1.out" >&2; exit 1; fi
	@mkdir -p $(OUT_DIR); ls $(OUT_DIR) 2>/dev/null | grep -v '^\.dest_' | sort > $(OUT_DIR)/.dest_before
	$(SRC_DIR)/disasm.sh $(ELF) $(NAME)
	@if [ -n "$(DEST)" ]; then mkdir -p "$(DEST)"; ls $(OUT_DIR) | grep -v '^\.dest_' | sort > $(OUT_DIR)/.dest_after; comm -13 $(OUT_DIR)/.dest_before $(OUT_DIR)/.dest_after | while read -r f; do cp -p "$(OUT_DIR)/$$f" "$(DEST)/"; done; echo "Copied new output to '$(DEST)'"; fi
	@rm -f $(OUT_DIR)/.dest_before $(OUT_DIR)/.dest_after

profiler:
	@if [ -z "$(ASM)" ]; then echo "ASM (or ELF) is required, e.g. make profiler ASM=out/test1.asm" >&2; exit 1; fi
	@mkdir -p $(OUT_DIR); ls $(OUT_DIR) 2>/dev/null | grep -v '^\.dest_' | sort > $(OUT_DIR)/.dest_before
	$(PYTHON) $(SRC_DIR)/isa_profiler.py $(ASM) $(NAME_FLAG) $(PROFILER_FLAGS)
	@if [ -n "$(DEST)" ]; then mkdir -p "$(DEST)"; ls $(OUT_DIR) | grep -v '^\.dest_' | sort > $(OUT_DIR)/.dest_after; comm -13 $(OUT_DIR)/.dest_before $(OUT_DIR)/.dest_after | while read -r f; do cp -p "$(OUT_DIR)/$$f" "$(DEST)/"; done; echo "Copied new output to '$(DEST)'"; fi
	@rm -f $(OUT_DIR)/.dest_before $(OUT_DIR)/.dest_after

clean:
	rm -f $(OUT_DIR)/*.asm $(OUT_DIR)/*.csv
