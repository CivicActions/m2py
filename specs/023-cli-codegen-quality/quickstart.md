# Quickstart: CLI & Codegen Quality

## Prerequisites

- Python 3.10+
- uv (package manager)
- ruff (installed automatically as project dependency)

## Install

```bash
cd /workspaces/m2py
uv sync
```

After this feature, `m2py` is available as a CLI command:

```bash
uv run m2py --help
```

## Transpile a Single File

```bash
# Output written alongside input (HELLO.m → HELLO.py)
uv run m2py path/to/HELLO.m

# Output to specific directory
uv run m2py path/to/HELLO.m -o output/
```

## Transpile a Directory

```bash
# Recursively transpile all .m files, output alongside inputs
uv run m2py path/to/routines/

# Recursively transpile to a dedicated output directory
uv run m2py path/to/routines/ -o output/
```

## Verbose Mode

```bash
uv run m2py path/to/routines/ -v
```

Shows per-file progress, timing, and full error tracebacks.

## Skip Ruff Processing

```bash
uv run m2py path/to/routines/ --no-format
```

Outputs raw codegen output without lint-fix or formatting. Useful for debugging.

## Multiple Inputs

```bash
uv run m2py file1.m file2.m dir1/ dir2/ -o output/
```

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All files transpiled successfully |
| `1` | One or more files failed |
| `2` | Invalid arguments |

## Verify Generated Code Quality

```bash
# Type check transpiled output
uv run pyright --pythonversion 3.10 -p pyrightconfig.json output/

# Lint check
ruff check output/

# Format check (should report no changes)
ruff format --check output/
```

## Run Tests

```bash
# Run all tests (parallel, skips slow)
uv run pytest

# Run specific test areas
uv run pytest tests/unit/analysis/test_type_inference.py
uv run pytest tests/integration/test_cli.py
uv run pytest tests/unit/codegen/test_code_quality.py

# Coverage report
uv run pytest --cov=m2py --cov-report=term-missing
```
