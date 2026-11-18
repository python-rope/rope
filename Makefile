VENV := $(shell dirname "$(CURDIR)")/.rope-venvs/$(shell basename "$(CURDIR)")
PYTHON := $(VENV)/bin/python
UV ?= uv
BOOTSTRAP_PYTHON ?= 3.13
TEST_PROFILE ?=
TEST_WORKERS ?= 2
EDITABLE_MODE ?=
export PYTHONDONTWRITEBYTECODE :=
export PYTHONPYCACHEPREFIX := $(VENV)/pycache
export COVERAGE_FILE := $(VENV)/.coverage

.PHONY: setup test test-file check check-codecov fmt build artifact-check source-ancestry source-fixture

source-fixture:
	"$(PYTHON)" -m ropetest.source_ancestry_fixtures

source-ancestry:
	test -n "$(REQUEST)"
	"$(PYTHON)" -m ropetest.source_ancestry_probe "$(REQUEST)"

setup:
	@set -eu; \
	expected_python="$$( $(UV) python find --no-project --system "$(BOOTSTRAP_PYTHON)" )"; \
	if [ -e "$(VENV)" ] || [ -L "$(VENV)" ]; then \
		if [ -L "$(VENV)" ] || [ ! -x "$(PYTHON)" ] || [ ! -f "$(VENV)/pyvenv.cfg" ]; then \
			printf 'ERROR: existing environment is not a physical venv: %s\n' "$(VENV)" >&2; \
			exit 2; \
		fi; \
		if ! "$(PYTHON)" -c 'from pathlib import Path; import sys; sys.exit(0 if Path(sys.executable).resolve() == Path(sys.argv[1]).resolve() else 2)' "$$expected_python"; then \
			printf 'ERROR: existing environment uses another Python interpreter: %s\n' "$(VENV)" >&2; \
			exit 2; \
		fi; \
	else \
		$(UV) venv --python "$$expected_python" "$(VENV)"; \
	fi
	$(UV) pip install --python "$(PYTHON)" $(if $(EDITABLE_MODE),--config-setting 'editable_mode=$(EDITABLE_MODE)') -e '$(CURDIR)[doc,dev]'

test:
	@set -- --cov -v -ra -o cache_dir="$(VENV)/pytest-cache" \
		--numprocesses="$(TEST_WORKERS)" --dist=loadscope --max-worker-restart=0; \
	if [ -n "$(TEST_PROFILE)" ]; then \
		"$(PYTHON)" -c 'import cProfile, pstats, runpy, sys, traceback; exec("\n\
profiler = cProfile.Profile()\n\
profile_path = sys.argv.pop(1)\n\
original = None\n\
try:\n\
    profiler.runcall(runpy.run_module, \"pytest\", run_name=\"__main__\", alter_sys=True)\n\
except BaseException as error:\n\
    original = error\n\
    raise\n\
finally:\n\
    try:\n\
        profiler.dump_stats(profile_path)\n\
        with open(profile_path + \".txt\", \"w\", encoding=\"utf-8\") as report:\n\
            pstats.Stats(profile_path, stream=report).sort_stats(\"cumulative\").print_stats()\n\
    except BaseException as publication:\n\
        if original is None or (isinstance(original, SystemExit) and original.code in (None, 0)):\n\
            raise\n\
        traceback.print_exception(type(publication), publication, publication.__traceback__)\n\
")' "$(TEST_PROFILE)" "$$@"; \
	else \
		"$(PYTHON)" -m pytest "$$@"; \
	fi

test-file:
	test -n "$(FILE)"
	"$(PYTHON)" -m pytest -v -ra -o cache_dir="$(VENV)/pytest-cache" "$(FILE)"

check:
	"$(PYTHON)" -m pre_commit run --all-files

check-codecov:
	curl --fail-with-body --data-binary @.github/codecov.yml https://api.codecov.io/validate

fmt:
	"$(PYTHON)" -m pre_commit run black --all-files
	"$(PYTHON)" -m pre_commit run isort --all-files

build:
	"$(PYTHON)" -m build "$(CURDIR)"
	$(MAKE) artifact-check

artifact-check:
	"$(PYTHON)" "$(CURDIR)/ropetest/package_artifact_contract.py"
