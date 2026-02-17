# CLI Contract: m2py

**Type**: Command-line interface  
**Entry point**: `m2py.cli:main`  
**Installable as**: `m2py` (via `[project.scripts]`)

## Synopsis

```
m2py <PATH> [PATH ...] [-o OUTPUT_DIR] [-v] [--no-format]
```

## Arguments

### Positional

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PATH` | file or directory | Yes (1+) | MUMPS `.m` files or directories to transpile. Directories are searched recursively for `*.m` files. |

### Optional Flags

| Flag | Short | Type | Default | Description |
|------|-------|------|---------|-------------|
| `--output` | `-o` | directory path | `None` | Output directory. If omitted, `.py` files are written alongside `.m` inputs. If specified, input directory structure is mirrored. |
| `--verbose` | `-v` | boolean | `False` | Print detailed progress (file names, timing, tracebacks on error). |
| `--no-format` | | boolean | `False` | Skip ruff lint-fix and formatting on generated output. Useful for debugging raw codegen output or when ruff is unavailable. |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All files transpiled successfully |
| `1` | One or more files failed to transpile |
| `2` | CLI usage error (invalid arguments) — argparse default |

## Output Behavior

### Default (no `--output`)

```
input/
  HELLO.m      →  input/HELLO.py
  sub/
    WORLD.m    →  input/sub/WORLD.py
```

### With `--output /out`

```
input/
  HELLO.m      →  /out/HELLO.py
  sub/
    WORLD.m    →  /out/sub/WORLD.py
```

Output directories are created automatically if they don't exist.

### Stderr Output

- Errors: `"ERROR: HELLO.m — ParseError: unexpected token on line 5"`
- Summary (always): `"Transpiled 47/50 files (3 failed)"`
- Verbose: file-by-file progress, timing, full tracebacks

### Stdout

No output to stdout. All feedback goes to stderr so that the CLI can be composed in pipelines.

## Post-Processing Pipeline

Each successfully generated Python file goes through this pipeline before being written to disk:

```
generate_python(source) → ruff check --fix (stdin) → ruff format (stdin) → write to disk
```

1. **Generate**: `generate_python(source, routine_name=name)` → Python source string
2. **Lint fix**: `ruff check --fix --fix-only --stdin-filename X.py -` removes unused imports (F401)
3. **Format**: `ruff format --stdin-filename X.py -` normalizes formatting
4. **Write**: Write final bytes to output path

Steps 2-3 are enabled by default and skipped when `--no-format` is passed.

## Internal API

### `transpile_file(input_path, output_path, no_format=False) -> TranspileResult`

Transpile a single `.m` file. Handles the full pipeline (generate → lint → format → write). When `no_format=True`, skips ruff lint-fix and formatting steps. Returns a `TranspileResult` regardless of success/failure.

### `transpile_paths(paths, output_dir=None, no_format=False) -> TranspileSummary`

Resolve a list of paths (files and/or directories), discover all `.m` files, transpile each with the given `no_format` setting, and return an aggregate `TranspileSummary`.

### `main(argv=None) -> int`

CLI entry point. Parses arguments, calls `transpile_paths()`, prints summary to stderr, returns exit code (0 or 1).

## Error Handling

| Error | Behavior |
|-------|----------|
| Path not found | Report error, mark file as failed, continue |
| Permission denied (read) | Report error, mark file as failed, continue |
| Permission denied (write) | Report error, mark file as failed, continue |
| Parse failure | Report error with file/line info, mark as failed, continue |
| Unsupported feature | Report warning, mark as failed, continue |
| ruff not found | Raise configuration error at startup (ruff is a required dependency) |
| All files fail | Exit code 1, summary shows 0 successes |

Batch processing never aborts early — all files are attempted.
