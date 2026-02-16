NAME = fl_main.py

RM = rm -fr

RUN_ARGS = ""

TARGETS_WITH_ARGS := run debug

ifeq ($(filter $(firstword $(MAKECMDGOALS)),$(TARGETS_WITH_ARGS)),$(firstword $(MAKECMDGOALS)))
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  $(eval $(RUN_ARGS):;@:)
endif

run: 
	python3 ./$(NAME) $(RUN_ARGS)

debug:
	python3 -m pdb ./$(NAME) $(RUN_ARGS)

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

install:
	pip install matplotlib
#	python3 -m pip install --user --upgrade matplotlib

.PHONY:	clean run debug install $(RUN_ARGS) 