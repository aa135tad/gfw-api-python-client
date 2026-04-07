.DEFAULT_GOAL := help
sources = src tests
notebooks-sources = notebooks
PYTHON ?= env/Scripts/python.exe

.PHONY: install  ## Install the package, dependencies, and pre-commit for local development
install:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .[lint,test,dev,build,docs,notebooks]
	$(PYTHON) -m pre_commit install --install-hooks
	$(PYTHON) -m pre_commit install --hook-type commit-msg

.PHONY: format  ## Auto-format python source files
format:
	python -m black $(sources)
	python -m ruff check --fix $(sources)
	python -m ruff format $(sources)

.PHONY: format-notebooks  ## Auto-format Jupyter Notebooks
format-notebooks:
	python -m black $(notebooks-sources)
	python -m ruff check --fix $(notebooks-sources)
	python -m ruff format $(notebooks-sources)

.PHONY: lint  ## Lint python source files
lint:
	$(PYTHON) -m ruff check $(sources)
	$(PYTHON) -m ruff format --check $(sources)
	$(PYTHON) -m black $(sources) --check --diff

.PHONY: lint-notebooks  ## Lint Jupyter Notebooks
lint-notebooks:
	$(PYTHON) -m ruff check $(notebooks-sources)
	$(PYTHON) -m ruff format --check $(notebooks-sources)
	$(PYTHON) -m black $(notebooks-sources) --check --diff

.PHONY: codespell  ## Use Codespell to do spellchecking
codespell:
	$(PYTHON) -m codespell_lib

.PHONY: typecheck  ## Perform type-checking
typecheck:
	$(PYTHON) -m mypy

.PHONY: audit  ## Use pip-audit to scan for known vulnerabilities
audit:
	$(PYTHON) -m pip_audit .

.PHONY: test  ## Run all unit tests and generate a coverage report
test:
	$(PYTHON) -m pytest -m "not integration" --cov-report term --cov-report=xml --cov=$(sources)

.PHONY: test-integration  ## Run only integration tests (if configured) without generate a coverage report
test-integration:
	$(PYTHON) -m pytest -m "integration" -rs -n auto --dist=loadscope --maxfail=5 --durations=10 --tb=short

.PHONY: pre-commit  ## Run all pre-commit hooks
pre-commit:
	$(PYTHON) -m pre_commit run --all-files

.PHONY: all  ## Run the standard set of checks performed in CI
all: lint codespell typecheck audit test

.PHONY: clean  ## Clear local caches and build artifacts
clean:
	# remove Python file artifacts
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]'`
	rm -f `find . -type f -name '*~'`
	rm -f `find . -type f -name '.*~'`
	rm -rf .cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	# remove build artifacts
	rm -rf build
	rm -rf dist
	rm -rf `find . -name '*.egg-info'`
	rm -rf `find . -name '*.egg'`
	# remove test and coverage artifacts
	rm -rf .tox/
	rm -f .coverage
	rm -f .coverage.*
	rm -rf coverage.*
	rm -rf htmlcov/
	rm -rf .pytest_cache
	rm -rf htmlcov

.PHONY: docs  ## Generate HTML documentation
docs:
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

.PHONY: servedocs  ## Build, watch and serve documentation with live reload in the browser
servedocs:
	$(MAKE) -C docs livehtml

.PHONY: notebooks  ## Run notebooks
notebooks:
	PYTHONHASHSEED=42 $(PYTHON) -m jupyterlab

.PHONY: build  ## Build source and wheel distributions
build: all clean
	$(PYTHON) -m build

.PHONY: distcheck  ## Validate built distributions
distcheck: build
	gunzip -tv dist/*.tar.gz
	zip -T dist/*.whl
	pyroma --min=10 dist/*.tar.gz
	python -m twine check dist/* --strict
	check-wheel-contents dist/*.whl
	pydistcheck dist/*

.PHONY: publish  ## Publish the built distributions to PyPI
publish: distcheck
	$(PYTHON) -m twine upload dist/* --verbose

.PHONY: help  ## Display this message
help:
	@grep -E \
		'^.PHONY: .*?## .*$$' $(MAKEFILE_LIST) | \
		sort | \
		awk 'BEGIN {FS = ".PHONY: |## "}; {printf "\033[36m%-19s\033[0m %s\n", $$2, $$3}'
