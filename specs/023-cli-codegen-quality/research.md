# Research: CLI & Codegen Quality

**Date**: 2026-02-15 | **Feature**: 023-cli-codegen-quality

## R1: CLI Framework & Design

**Decision**: Use `argparse` (stdlib) — zero new dependencies.

**Rationale**: The project has only `textX` and `pyright` as runtime deps. `argparse` covers all requirements (positional paths, `--output`, `--verbose`). `click` adds a dependency without proportional benefit for a single-command CLI.

**Alternatives considered**: click (richer decorator DSL, but unnecessary complexity and supply-chain risk for a simple transpiler CLI).

### CLI Command Design

**Decision**: Single positional `paths` argument accepting one or more file/directory values.

```
m2py FILE_OR_DIR [FILE_OR_DIR ...] [-o OUTPUT_DIR] [-v]
```

- File path → transpile single file
- Directory path → glob `**/*.m` recursively
- No `-o` → write `.py` alongside each `.m` input
- `-o DIR` → mirror input structure into output directory

**Rationale**: This is the established pattern used by `black`, `ruff`, `mypy`, `isort`. No subcommands needed — a transpiler's single job doesn't warrant them.

### Entry Point

```toml
[project.scripts]
m2py = "m2py.cli:main"
```

### Exit Codes

| Situation | Code |
|-----------|------|
| All files succeed | `0` |
| Any file fails | `1` |
| CLI usage error | `2` (argparse default) |

**Rationale**: Binary 0/1 is the dominant convention (`mypy`, `ruff`, `gcc`). The summary message on stderr provides detail for humans.

### Error Handling Pattern

- Collect results (`TranspileResult` dataclass with path, success, error, output_path)
- Continue on error for batch processing
- Print final summary: `"Transpiled 47/50 files (3 failed)"`
- Errors to stderr, transpiled code to files
- `--verbose` adds tracebacks

---

## R2: Ruff Lint Fix Strategy

### F401 (Unused Imports) — 127 instances

**Decision**: Post-generation `ruff check --fix --fix-only` via stdin pipe.

**Rationale**: The codegen currently emits a fixed block of ~8 import lines covering every possible runtime helper. The `ctx.imports: set[str]` field on `GeneratorContext` exists but is never read or written. Three options considered:

| Option | Effort | Pros | Cons |
|--------|--------|------|------|
| Track imports during codegen | High | Architecturally clean | Touches dozens of emitter call sites, brittle to maintain |
| `# noqa: F401` | Low | Quick | Leaves dead code, harder to read |
| `ruff check --fix` post-gen | Low | Zero codegen changes, uses existing tool | Subprocess call per file or batch |

Post-gen fix aligns with the overall pipeline (generate → lint-fix → format → write) and is the lowest-risk approach.

### E501 (Line Too Long) — 14 instances

**Decision**: Rely on `ruff format` to handle long lines; disable E501 in ruff config.

**Rationale**: `ruff format` automatically wraps long import lines. For expressions that can't be wrapped, ruff's FAQ explicitly notes E501 can still fire after formatting. This is standard practice — disable the check and let the formatter do its best.

### E741 (Ambiguous Variable Names) — 2 instances

**Decision**: Disable E741 globally for generated code.

**Rationale**: MUMPS variable `I` is a standard loop counter in the source language. Renaming would break semantic fidelity. Inline `# noqa: E741` on every occurrence would require codegen awareness of name ambiguity — messy.

### Ruff Config

```toml
[tool.ruff.lint]
select = ["E", "F"]
ignore = ["E501", "E741"]
```

---

## R3: Ruff Auto-Formatting Integration

**Decision**: Pipe through `subprocess.run(["ruff", "format", "--stdin-filename", "f.py", "-"])`.

**Rationale**: Ruff has no Python API — it's a Rust binary with CLI only. Stdin/stdout pipe avoids writing unformatted temp files.

**Pipeline order**: generate → `ruff check --fix` (remove unused imports) → `ruff format` (normalize style) → write to disk.

**Scope**: FR-017 — only applies to disk-written CLI output. In-memory test execution and XECUTE skip formatting.

`ruff format` preserves `# noqa` comments (verified).

---

## R4: Expression-Level Type Inference Design

### ExprResultType Enum

```python
class ExprResultType(Enum):
    STRING = auto()         # str — $PIECE, $EXTRACT, concatenation, string literals
    NUMERIC = auto()        # int | Decimal — arithmetic, $LENGTH, $DATA, $RANDOM
    BOOLEAN_INT = auto()    # 0 | 1 — comparisons, logical ops, pattern match
    NUMERIC_STRING = auto() # str (formatted number) — $JUSTIFY, $FNUMBER
    UNKNOWN = auto()        # Cannot determine — variables, $GET, $SELECT, indirection
```

### Type Mapping Summary

| Expression Category | Result Type |
|---|---|
| String literals, `_` concat, `$P`, `$E`, `$C`, `$TR`, `$RE`, `$T`, `$NA`, `$QS`, `$ZD` | `STRING` |
| Integer/decimal literals, `+` `-` `*` `/` `\` `#` `**`, `$L`, `$A`, `$F`, `$R`, `$D`, `$QL` | `NUMERIC` |
| `=` `<` `>` `[` `]` `]]` `?` `&` `!` `'`, pattern match | `BOOLEAN_INT` |
| `$J`, `$FN` | `NUMERIC_STRING` |
| Variables, globals, `$G`, `$S`, `$O`, indirection, extrinsic functions | `UNKNOWN` |

### Pipeline Insertion

After step 6 (`compute_signatures`), as step 7 — the last analysis pass before codegen. Pure read of ASG with no dependencies on other passes.

### Estimated LOC

~250-300 lines for the inference pass + ~200-300 lines of tests.

### Key Edge Cases

- `$STACK` is polymorphic: 1-arg → `NUMERIC`, 2-arg → `STRING`
- `$SELECT` is heterogeneous: always `UNKNOWN`
- `MFormatControl`/`MDeviceControl` are not value expressions: skip or leave `None`
- `result_type` should be `Optional[ExprResultType]` defaulting to `None` for backward compatibility
- No recursive fixpoint needed — MUMPS operator output types depend only on operator, not operand types

---

## R5: Pyright Integration

**Decision**: pyright `basic` mode for generated code.

**Verified**: Generated code already passes `basic` with zero errors, zero changes needed (tested with hello world, complex expressions, and XECUTE/indirection patterns).

**Test strategy**: Transpile representative MUMPS files in test, write to temp dir, run `pyright -p <config>` via subprocess, assert exit code 0.

---

## R6: Coverage Analysis Approach

**Current state**: 87% overall (from HTML report dated 2026-01-20). Key gaps:

| Module | Coverage | Missing |
|---|---|---|
| `runtime/__init__.py` | 78% | 147 stmts |
| `codegen/statements.py` | 81% | 233 stmts |
| `codegen/expressions.py` | 84% | 81 stmts |
| `analysis/semantic_analyzer.py` | 85% | 140 stmts |
| `runtime/globals.py` | 85% | — |

**Decision**: Focus on meaningful gaps (code paths representing real behavioral risk). Stop when remaining uncovered paths are defensive error handling or require exotic system states. No hard numeric target.

**Approach**: Run `uv run pytest --cov=m2py --cov-report=term-missing` to identify uncovered lines, prioritize by behavioral risk, add tests to existing spec-aligned files where possible.
