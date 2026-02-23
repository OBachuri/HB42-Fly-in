.ONESHELL:
SHELL := /bin/bash

NAME = fl_main.py

RM = rm -fr

VENV_DIR := .mz-venv
PYTHON := python3
PIP := pip
C_DIR := pwd

RUN_ARGS = ""

BUILD_SOURCE_DIR := "flmap"

TARGETS_WITH_ARGS := run debug

define ACTIVATE_VENV
if [ -z "$$VIRTUAL_ENV" ]; then \
	echo "No virtual environment detected."; \
	$(MAKE) venv; \
	. "$(VENV_DIR)/bin/activate"; \
fi
endef


ifeq ($(filter $(firstword $(MAKECMDGOALS)),$(TARGETS_WITH_ARGS)),$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(RUN_ARGS):;@:)
endif


help:
	@echo "Start:"
	@echo "                 $$ make install"
	@echo "                 $$ make run map.txt"
	@echo ""
	@echo "Available targets:"
	@echo "  install        Install dependencies and set up the virtual environment"
	@echo "  run            Run the application"
	@echo "                 $$ make run map.txt"
	@echo "  lint           Run flake8 and mypy checks"
	@echo "  lint-strict    Run flake8 and strict mypy checks"
	@echo "  clean          Remove caches and temporary files"
	@echo "  fclean         clean + remove folder of virtual environment"
	@echo "  debug          Run the debugger "

run:
	@$(ACTIVATE_VENV)
	@$(PYTHON) ./$(NAME) $(RUN_ARGS)

debug:
	@$(ACTIVATE_VENV)
	$(PYTHON) -m pdb ./$(NAME) $(RUN_ARGS)


check-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "No virtual environment detected."; \
		$(MAKE) venv; \
		. "$(VENV_DIR)/bin/activate"; \
		echo "Virtual environment in $(VENV_DIR)."; \
	else \
		echo "Using virtual environment: $$VIRTUAL_ENV"; \
	fi

venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
		chmod +x "$(VENV_DIR)/bin/activate" ; \
	else \
		echo "Virtual environment already exists."; \
	fi

# Clean temporary files
clean:
	@$(RM) .mypy_cache
	@$(RM) __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -name .pytest_cache -exec rm -rf {} +
	find . -name .ruff_cache -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

fclean: clean
	@$(RM) $(VENV_DIR)
	@$(RM) *.whl

lint:
	@$(ACTIVATE_VENV)
	echo "--- flake8 test :"
	flake8 ./*.py $(BUILD_SOURCE_DIR)/
	echo "--- mypy test :"
	mypy ./*.py $(BUILD_SOURCE_DIR)/ \
		--warn-return-any \
		--warn-unused-ignores  \
		--ignore-missing-imports  \
		--disallow-untyped-defs \
		--check-untyped-defs \
		--exclude '(^\.mz-venv/|^test/|^subject/)'

lint-strict:
	@$(ACTIVATE_VENV)
	echo "--- flake8 test :"
	flake8 ./*.py $(BUILD_SOURCE_DIR)/
	echo "--- mypy strict test :"
	mypy . \
	--strict \
	--exclude '(^\.mz-venv/|^test/|^subject/)'

install:
	@$(ACTIVATE_VENV)
	@$(PIP) install matplotlib pydantic flake8 mypy

.PHONY:	clean run debug install $(RUN_ARGS) lint-strict lint venv check-venv fclean
