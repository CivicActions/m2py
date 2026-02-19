# Testing Guide

## Running Tests

```bash
uv run pytest                        # Default: parallel, skip slow tests
uv run pytest -n0                    # Sequential (for debugging)
uv run pytest -m slow                # Run only slow tests
uv run pytest -m "parser"            # Run only parser-level tests
uv run pytest --backend sqlite       # Use SQLite global storage
uv run pytest tests/unit/codegen/    # Run one directory
```

**Smart defaults** are applied automatically by `tests/conftest.py`:
- `-n auto` (parallel via pytest-xdist) unless you pass `-n`
- `-m 'not slow'` unless you pass `-m`

No need for `-o "addopts="` — the smart defaults detect your CLI flags and stay out of the way.

## Test Organization

~380 test files across ~7,400 tests, organized in four tiers:

```
tests/
├── unit/                    # Isolated component tests
│   ├── parser/              # textX grammar / parser tests
│   │   ├── s5_metalanguage/ # § 5 tests
│   │   ├── s6_routine/      # § 6 tests
│   │   ├── s7_expressions/  # § 7 tests
│   │   ├── s8_commands/     # § 8 tests (~38 files, one per command)
│   │   ├── s9_charset/      # § 9 tests
│   │   ├── extensions/ydb/  # YottaDB-specific extensions
│   │   └── legacy/          # Pre-1995 syntax tests
│   ├── asg/                 # ASG semantic analysis tests (same structure)
│   ├── codegen/             # Code generation tests (same structure)
│   ├── analysis/            # Internal algorithm tests
│   ├── runtime/             # MUMPSRuntime, globals, devices, JOB, LOCK
│   ├── core/                # Value semantics, subscripts, indirection, scope
│   ├── cross_cutting/       # Multi-feature behaviors ($TEST, postconditions)
│   └── meta/                # Package setup, regressions, performance
├── integration/             # Full transpile-and-execute pipeline (~21 files)
└── functional/              # MUMPS test suites vs YDB reference output
    ├── mugj/                # MUMPS User Group Japan suite
    ├── mvts/                # MUMPS Validation Test Suite
    ├── basic/               # Core language features
    ├── merge/               # MERGE command tests
    ├── indirection/         # Indirection operator tests
    ├── m_commands/          # M commands + Z-commands
    ├── io/                  # I/O operations
    ├── tp/                  # Transaction processing
    ├── triggers/            # Trigger tests
    ├── longname/            # Long variable names
    └── unicode/             # Unicode handling
```

### Spec-Aligned Structure

The `parser/`, `asg/`, and `codegen/` directories mirror the MUMPS 1995 ANSI Standard sections (§5–§9). File naming convention: `test_s8_2_05_for.py` = Section 8.2.5 (FOR command). Each `s8_commands/` directory contains ~37-42 files covering all MUMPS commands.

Tests in these directories are validated by `pytest_collection_modifyitems` — if a test lacks a `@pytest.mark.parser`, `@pytest.mark.asg`, or `@pytest.mark.codegen` marker, a warning is emitted.

## Key Fixtures

Fixtures are layered — each test directory has its own `conftest.py` providing level-appropriate fixtures.

### Parser Fixtures (`tests/unit/parser/conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `parse_mumps` | Parse MUMPS source → `MRoutine` ASG |
| `parse_line` | Wrap a single line in a routine and parse |
| `parse_expression` | Parse a MUMPS expression directly |
| `mumps_parser` | Raw `MUMPSParser()` instance |

### ASG Fixtures (`tests/unit/asg/conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `analyze_routine` | Parse + full semantic analysis → enriched `MRoutine` |
| `analyze_expression` | Analyze a single expression |
| `analyze_statement` | Wrap in routine, parse, return first statement ASG node |
| `resolve_refs` | The `resolve_references()` function |

### Codegen Fixtures (`tests/unit/codegen/conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `generate_python` | Generate Python source from MUMPS source |
| `execute_mumps` | Full pipeline: parse → generate → execute → `ExecutionResult` |
| `execute_expr` | Wrap a command, execute, return output string |
| `eval_mumps` | Evaluate a MUMPS expression, return value |
| `validate_python_syntax` | Validate generated code via `ast.parse()` |

### Analysis Fixtures (`tests/unit/analysis/conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `classify_for` | FOR loop classification function |
| `classify_goto` | GOTO classification function |
| `analyze_variables` | Variable scope analysis function |
| `resolve_references` | Reference resolution function |

### Runtime Fixtures (`tests/unit/runtime/conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `sqlite_storage` | `SQLiteGlobalStorage` instance (temp DB) |
| `sqlite_rt` | `MUMPSRuntime` with SQLite backend |
| `job_routine_dir` | Temp directory for JOB subprocess test routines |

### Functional Fixtures (`tests/functional/conftest.py`)

| Fixture | Purpose |
|---------|---------|
| `mumps_runner` | Execute MUMPS via m2py in isolated subprocess (60s timeout) |
| `outref_normalizer` | Strip YDB infrastructure from reference output |
| `output_comparator` | Unified diff comparison |

### Root Fixtures (`tests/conftest.py`)

Suite-loading fixtures are auto-generated for 11 test suites. Each suite gets three fixtures:
- `{suite}_inref_dir` → `Path` to the suite's `.m` file directory
- `{suite}_file` → `Callable[[str], str]` to load a specific file
- `{suite}_files` → `Callable[[], Iterator]` to iterate all files

## Markers

| Marker | Purpose |
|--------|---------|
| `parser` | textX grammar/parser level |
| `asg` | ASG semantic analysis level |
| `codegen` | Python code generation level |
| `analysis` | Analysis module tests |
| `runtime` | Runtime module tests |
| `integration` | Full transpilation pipeline |
| `functional` | YDB outref comparison |
| `stub` | Placeholder expected to fail |
| `slow` | Long-running (skipped by default) |
| `ydb` | YottaDB-specific extensions |
| `pre1995` | Pre-1995 MUMPS syntax |
| `mugj` / `basic` / `mvts` / `merge` | Functional suite markers |

## Backend Pluggability

The `--backend` option switches global storage across all tests:

```bash
uv run pytest --backend inmemory     # Default: fast in-process storage
uv run pytest --backend sqlite       # SQLite: tests cross-process JOB/LOCK
```

`yottadb` and `iris` backends are defined but require external packages.

## Functional Test Suites

Functional tests execute real MUMPS routines from YDBTest through m2py in **isolated `multiprocessing.Process` instances** (preventing infinite loops from killing the test runner) and compare output against YDB reference output (outref files).

Two validation strategies:

- **Pattern-based** (MUGJ): counts PASS markers, checks visual "should be identical" pairs, flags unexpected FAILs
- **Output comparison** (basic, merge, etc.): byte-for-byte diff against normalized outref content

The `normalize_outref()` function strips YDB infrastructure (prompts, marker placeholders, infrastructure messages, SUSPEND/ALLOW blocks) for clean comparison.

Suite routine definitions (labels, expected pass/fail counts) are maintained in `tests/functional/suite_definitions.py`.

## Validation Utilities

| Script | Purpose |
|--------|---------|
| `utils/validate.py` | Compare m2py output against YottaDB and/or IRIS via Docker |
| `utils/ydb.py` | Run MUMPS through YottaDB via Docker |
| `utils/iris.py` | Run MUMPS through InterSystems IRIS via Docker (persistent container) |
| `utils/scan_vista.py` | Scan VistA-VEHU-M routines, report transpilation metrics, and detect regressions against a reference baseline |
| `utils/validate_asg.py` | Inspect ASG structure for a MUMPS file |
| `utils/rebuild_docs.py` | Regenerate `docs/limitations.md` |

```bash
# Compare output against YDB
uv run python utils/validate.py --code 'TEST W "Hello" Q'

# Compare against both YDB and IRIS
uv run python utils/validate.py --iris --code 'TEST W "Hello" Q'

# Compare against IRIS only
uv run python utils/validate.py --no-ydb --iris --code 'TEST W $ZCV("hello","U") Q'

# Debug mode: show ASG and generated Python
uv run python utils/validate.py --debug --code 'TEST S X=1 W X Q'

# Run MUMPS through YDB only
uv run python utils/ydb.py --code 'TEST W 1+2 Q'

# Run MUMPS through IRIS only
uv run python utils/iris.py --code 'TEST W 1+2 Q'

# Scan VistA-VEHU-M transpilation (parallel, with regression check)
uv run python utils/scan_vista.py

# Update the reference baseline after fixes
uv run python utils/scan_vista.py --update-reference
```
