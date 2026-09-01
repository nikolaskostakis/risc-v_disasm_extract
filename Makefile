# Usage:
#   make ELF=path/to/test1.out [NAME=name]        # full pipeline: disasm + parser
#   make disasm ELF=path/to/test1.out [NAME=name]
#   make parser ASM=out/test1.asm [NAME=name]
#   make clean
#   make help                                     # describe targets and variables

PYTHON       ?= python3
SRC_DIR      := src
OUT_DIR      := out

ELF          ?=
NAME         ?=
PARSER_FLAGS ?= -isa-csv

NAME_FLAG := $(if $(NAME),-o $(NAME))
ASM_NAME  := $(if $(NAME),$(NAME),$(basename $(notdir $(ELF))))
ifneq ($(ASM_NAME),)
ASM ?= $(OUT_DIR)/$(ASM_NAME).asm
endif

.PHONY: all disasm parser clean help

all: disasm parser

help:
	@echo "Targets:"
	@echo "  all (default)  Full pipeline: disasm then parser"
	@echo "  disasm         Disassemble ELF to out/<name>.asm and out/<name>.hexdump.asm"
	@echo "  parser         Parse an .asm file, categorize/count instructions"
	@echo "  clean          Remove generated files from out/"
	@echo "  help           Show this message"
	@echo ""
	@echo "Variables:"
	@echo "  ELF           Input ELF file (required for disasm, and all unless ASM is set)"
	@echo "  ASM           Input .asm file for parser (default: out/<NAME or ELF basename>.asm)"
	@echo "  NAME          Output base name shared by both tools (optional; each tool"
	@echo "                falls back to its own default naming if omitted)"
	@echo "  PARSER_FLAGS  Flags passed to asm_parser.py (default: -isa-csv)"
	@echo ""
	@echo "Examples:"
	@echo "  make ELF=path/to/test1.out"
	@echo "  make ELF=path/to/test1.out NAME=myrun PARSER_FLAGS=\"-csv -isa-csv\""
	@echo "  make parser ASM=out/test1.asm"

disasm:
	@if [ -z "$(ELF)" ]; then echo "ELF is required, e.g. make disasm ELF=path/to/test1.out" >&2; exit 1; fi
	$(SRC_DIR)/disasm.sh $(ELF) $(NAME)

parser:
	@if [ -z "$(ASM)" ]; then echo "ASM (or ELF) is required, e.g. make parser ASM=out/test1.asm" >&2; exit 1; fi
	$(PYTHON) $(SRC_DIR)/asm_parser.py $(ASM) $(NAME_FLAG) $(PARSER_FLAGS)

clean:
	rm -f $(OUT_DIR)/*.asm $(OUT_DIR)/*.csv
