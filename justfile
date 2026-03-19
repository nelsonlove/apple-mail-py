# apple-mail-py development commands

default:
    @just --list

install:
    pip install -e ".[dev]"

lint: format-check lint-ruff type-check

format:
    ruff format src tests

format-check:
    ruff format --check src tests

lint-ruff:
    ruff check src tests

fix:
    ruff check --fix src tests
    ruff format src tests

type-check:
    mypy src/clawmail src/apple_mail

test:
    pytest -v

test-cov:
    pytest --cov=clawmail --cov=apple_mail --cov-report=term-missing

run *ARGS:
    python -m clawmail.cli {{ARGS}}

clean:
    rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .ruff_cache/ htmlcov/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} +

check: lint type-check test
