# M2PY Copilot Instructions

M2PY is a MUMPS-to-Python transpiler using textX to build an Abstract Semantic Graph (ASG).

## Critical: Use uv Exclusively

**All Python commands MUST use `uv`** for package management, running scripts, and testing:

```bash
uv run pytest                    # Run tests (parallel + skip slow by default)
uv run pytest -n0                # Run tests sequentially (for debugging)
uv run pytest -m slow            # Run only slow tests
uv run python <script>           # Run any Python script
uv add <package>                 # Add dependencies
uv sync                          # Sync environment
```

- Never use bare `python`, `pip`, or `pytest` commands.
- **Never use `-o "addopts="`** — smart defaults in `tests/conftest.py` auto-inject
  `-n auto` and `-m 'not slow'` only when the user hasn't passed `-n` or `-m`. Avoid -n0 unless debugging issues with parallel test execution.
- Run short Python snippets with pylanceRunCodeSnippet or create a permanent helper script in `/utils`. *Don't* use `uv python -c` or cat to /tmp files.
- If you need to use a tmp directory for m files, use the one in the workspace - do not use `/tmp`.
- Avoid `2> /dev/null` and `&> /dev/null` redirection.
- Prefer `rg` over `grep` for searching code.

## Key Reference Materials

- `docs/` - **Project documentation** (architecture, ASG reference, examples, codegen strategies)
- **MUMPS Specification**: https://71.174.62.16/Demo/AnnoStd (local mirror in `mumps-reference/` with examples and notes)
- **textX Documentation**: https://textx.github.io/textX/ (local mirror may be available in `textX-reference/`)
- `YDBTest/` - YDB test suite (runtime validation)
- `.specify/memory/constitution.md` - Project principles and constraints

## Architecture

```
MUMPS Source → textX Parser → ASG (Semantic Graph) → Python Code
```

Core implementation in `src/m2py/`. Feature specs in `specs/<number>-<name>/`.

## Development Workflow

Uses **Speckit** for spec-driven development via `.github/prompts/speckit.*.prompt.md` agents.

## Validation Utility

The `utils/validate.py` script compares m2py output against YottaDB and/or IRIS for runtime verification:

```bash
# Compare output against YottaDB (requires Docker)
uv run python utils/validate.py --code 'TEST W "Hello" Q'
uv run python utils/validate.py myprogram.m

# Compare against both YDB and IRIS
uv run python utils/validate.py --iris --code 'TEST W "Hello" Q'

# Compare against IRIS only (skip YDB)
uv run python utils/validate.py --no-ydb --iris --code 'TEST W $ZCONVERT("hello","U") Q'

# Debug mode: show AST and generated Python
uv run python utils/validate.py --debug --code 'TEST S X=1 W X Q'

# Skip all comparisons (m2py only)
uv run python utils/validate.py --no-ydb --code 'TEST W 1+2 Q'
```

## Generating YDB Reference Output

Use `utils/run_mumps_ydb.py` or `utils/validate.py` to run MUMPS through YottaDB. Do NOT use docker commands directly.

```bash
# Run MUMPS file through YDB
uv run python utils/run_mumps_ydb.py routine.m

# Run inline MUMPS
uv run python utils/run_mumps_ydb.py --code 'TEST W 1+2 Q'

# Run from stdin
echo -e 'TEST\n write 1+2,!' | uv run python utils/run_mumps_ydb.py -
```

**⚠️ Never use `-t` for testing** — TTY mangles control characters (form feed `\x0c` → ANSI escapes), breaking output comparison.

## Generating IRIS Reference Output

Use `utils/run_mumps_iris.py` to run MUMPS through InterSystems IRIS. Uses a persistent Docker container (auto-started on first use) to avoid slow IRIS startup on each invocation.

```bash
# Run MUMPS file through IRIS
uv run python utils/run_mumps_iris.py routine.m

# Run inline MUMPS
uv run python utils/run_mumps_iris.py --code 'TEST W 1+2 Q'

# Run from stdin
echo -e 'TEST\n write 1+2,!' | uv run python utils/run_mumps_iris.py -

# Container management
uv run python utils/run_mumps_iris.py --start   # Pre-start the container
uv run python utils/run_mumps_iris.py --stop    # Stop and remove the container
```

This is useful for testing IRIS/Caché-specific functions (e.g., `$ZCONVERT`, `$LISTBUILD`) that are not available in YottaDB.

## Running with IRIS Container

Use `utils/iris.sh` to auto-start the IRIS Docker container and run commands with connection env vars exported. Unlike `ydb.sh`, commands run locally (IRIS SDK connects over TCP).

```bash
# Run tests with IRIS container available
bash utils/iris.sh uv run pytest tests/ -x -n0

# Container management
bash utils/iris.sh --start    # Start container only
bash utils/iris.sh --stop     # Stop and remove container
bash utils/iris.sh --status   # Show container status
```

Exported env vars: `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USER`, `IRIS_PASSWORD`.

## Running with YottaDB Python SDK

Use `utils/ydb.sh` to run any command inside a YottaDB Docker container with the workspace mounted. The image is auto-built on first use from `Dockerfile.yottadb`.

```bash
# Run tests with yottadb Python package available
bash utils/ydb.sh uv run pytest tests/ -x -n0

# Import test
bash utils/ydb.sh uv run python -c "import yottadb; print('ok')"

# Interactive shell (YDB env pre-configured)
bash utils/ydb.sh bash
```

## Core Principles

1. **Semantic Correctness First** - Generated Python must match MUMPS behavior exactly
2. **Test-Driven Validation** - MUMPS reference and YDBTest are the sources of truth
3. **Multi-Phase Architecture** - Parse → Analyze → Generate (all references resolved before codegen)
4. **Incremental Validation** - Start simple, prove correct, then add complexity
