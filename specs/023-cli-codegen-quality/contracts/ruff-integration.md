# Ruff Integration Contract

**Type**: Post-generation processing (subprocess)  
**Location**: Integrated into CLI transpile pipeline (`src/m2py/cli/transpile.py`)

## Configuration

Added to `pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "F"]
ignore = ["E501", "E741"]
```

No per-file overrides. Configuration applies to both source and generated code.

## Pipeline Functions

### `lint_fix(source: str, filename: str) -> str`

Run `ruff check --fix --fix-only --stdin-filename {filename} -` on the source string. Returns the fixed source.

**Purpose**: Remove unused imports (F401) and fix other auto-fixable lint issues.

**Subprocess**: `["ruff", "check", "--fix", "--fix-only", "--stdin-filename", filename, "-"]`  
**stdin**: source code  
**stdout**: fixed source code  
**Exit code**: 0 (fixed) or non-zero (unfixable issues — logged but not fatal)

### `format_code(source: str, filename: str) -> str`

Run `ruff format --stdin-filename {filename} -` on the source string. Returns the formatted source.

**Subprocess**: `["ruff", "format", "--stdin-filename", filename, "-"]`  
**stdin**: source code  
**stdout**: formatted source code  
**Exit code**: 0 always (format never fails on valid Python)

## Scope

- **Applied to**: Files written to disk by CLI
- **Not applied to**: In-memory test execution, runtime XECUTE code
- **Deterministic**: Same input always produces same output (ruff is deterministic)
