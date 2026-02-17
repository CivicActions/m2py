# Implementation Plan: CLI & Codegen Quality

**Branch**: `023-cli-codegen-quality` | **Date**: 2026-02-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/023-cli-codegen-quality/spec.md`

## Summary

Add a CLI (`m2py`) to transpile MUMPS `.m` files (single or directory) to Python. Improve generated code quality with expression-level type inference on the ASG, pyright `basic` validation, ruff `E`+`F` lint compliance, and ruff auto-formatting. Fill meaningful test coverage gaps and deduplicate tests with overlapping coverage.

## Technical Context

**Language/Version**: Python 3.10+ (constitution constraint; runtime uses 3.10)
**Primary Dependencies**: textX 4.0+ (parser), argparse (CLI, stdlib), ruff 0.15+ (lint/format), pyright 1.1.408+ (type check)
**Storage**: File system (`.m` input → `.py` output)
**Testing**: pytest + pytest-cov + pytest-xdist, via `uv run pytest`
**Target Platform**: Linux (dev container), cross-platform Python
**Project Type**: Single project, existing `src/m2py/` + `tests/` layout
**Performance Goals**: <5s single file, 100+ files in single batch invocation
**Constraints**: uv exclusively for all Python commands; no `# pragma: no cover` additions
**Scale/Scope**: CLI for individual developers and CI/CD pipelines; ~12K LOC codebase

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | CLI wraps existing `generate_python()` — no semantic changes. Type inference is read-only on ASG. |
| II. YDB as Reference | ✅ PASS | No behavioral changes to codegen output for existing tests. |
| III. Strict Layer Separation | ✅ PASS | Type inference is an analysis pass (not codegen). CLI is a separate layer consuming codegen output. |
| IV. Explicit Over Implicit | ✅ PASS | Type hints make generated code more explicit, not less. |
| V. Foundational Correctness | ✅ PASS | Expression-level type inference is foundational for future type tracking. |
| VI. Cross-Cutting Semantics | ✅ PASS | No changes to cross-cutting semantics. |
| VII. Minimize Runtime Surface | ✅ PASS | No new runtime calls. Type inference may enable *removing* unnecessary coercion calls. |
| VIII. Research Before Implementation | ✅ PASS | Plan includes Phase 0 research. |

**Gate result: PASS** — no violations.

### Post-Design Re-Evaluation (Phase 1 Complete)

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | Type inference is read-only on ASG; CLI wraps `generate_python()` without modifying codegen semantics. Post-gen ruff lint/format changes only whitespace and import ordering — no semantic impact. |
| II. YDB as Reference | ✅ PASS | No behavioral changes to generated output. ExprResultType annotations are metadata only. |
| III. Strict Layer Separation | ✅ PASS | Type inference is a new analysis pass (`src/m2py/analysis/type_inference.py`), not codegen. CLI is a separate presentation layer. Ruff integration is post-codegen I/O processing. |
| IV. Explicit Over Implicit | ✅ PASS | ExprResultType makes previously implicit type semantics explicit. Type hints on generated code increase explicitness. |
| V. Foundational Correctness | ✅ PASS | Expression-level type inference is foundational infrastructure for future variable-level tracking. |
| VI. Cross-Cutting Semantics | ✅ PASS | Value model, $TEST, array model unchanged. Type inference respects existing coercion semantics. |
| VII. Minimize Runtime Surface | ✅ PASS | Type information may enable *removing* unnecessary coercion calls in future. No new runtime surface added. |
| VIII. Research Before Implementation | ✅ PASS | Phase 0 research complete with 6 decision areas documented in research.md. |

**Post-design gate result: PASS** — all principles still satisfied after design decisions.

## Project Structure

### Documentation (this feature)

```text
specs/023-cli-codegen-quality/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI contract)
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── cli/
│   ├── __init__.py      # Currently empty placeholder — will contain CLI entry point
│   └── transpile.py     # NEW: transpile command implementation
├── analysis/
│   └── type_inference.py  # NEW: expression-level type inference pass
├── asg/
│   ├── expressions.py   # MODIFY: add result_type field to MExpr
│   └── enums.py         # MODIFY: add ExprResultType enum
├── codegen/
│   ├── __init__.py      # MODIFY: integrate type inference pass, prune unused imports
│   ├── routine.py       # MODIFY: emit type hints on function signatures
│   ├── expressions.py   # MODIFY: use result_type for type annotations
│   └── statements.py    # MODIFY: fix lint issues in generated code
└── pyproject.toml       # MODIFY: add [project.scripts], ruff dep, [tool.ruff] config

tests/
├── unit/
│   ├── codegen/
│   │   └── test_code_quality.py  # NEW: pyright basic + ruff E,F validation
│   └── analysis/
│       └── test_type_inference.py  # NEW: expression-level type inference tests
├── integration/
│   └── test_cli.py      # NEW: CLI integration tests
└── conftest.py          # MODIFY if needed: add CLI fixtures
```

**Structure Decision**: Single project, extending existing `src/m2py/` layout. CLI goes into the existing `cli/` placeholder package. Type inference is a new analysis pass following the established pattern.

## Complexity Tracking

No constitution violations to justify.
