# Implementation Plan: Phase 1 — Foundation & Cleanup

**Branch**: `019-foundation-cleanup` | **Date**: 2026-02-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/019-foundation-cleanup/spec.md`

## Summary

Phase 1 creates foundational modules (`core/values.py`, `core/parsing.py`,
`core/tokenizer.py`) that centralize duplicated MUMPS value semantics, subscript
parsing, and string tokenization. It eliminates 18 backward imports from runtime/core
into codegen, fixes the exclusive KILL/NEW detection gap, and deduplicates analysis-layer
code. All changes are behavior-preserving refactoring — existing tests must pass
with zero failures, xfails, or skips.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textX ≥ 4.0 (parser), Decimal (stdlib, value model)
**Storage**: N/A (no persistence changes)
**Testing**: pytest with `uv run pytest` (5682 tests, 0 xfails, 0 skips at baseline)
**Target Platform**: Any Python 3.10+ (transpiler tool)
**Project Type**: Single Python package (`src/m2py/`)
**Performance Goals**: No regression — transpiler throughput unchanged
**Constraints**: All existing tests pass; no user-facing behavior changes
**Scale/Scope**: ~18 deferred imports to fix, 3 formatters → 1, 3 parsers → 1, 13+ state machines → 1

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | Unifying formatters ensures consistent canonical formatting. No behavioral changes. |
| II. YDB as Reference Implementation | ✅ PASS | Unified `mumps_canonical_str` applies exponent guard consistently, matching YDB. |
| III. Strict Layer Separation | ✅ PASS | **This is the primary goal.** Moving value-model functions from codegen → core resolves runtime→codegen violations. Moving `contains_naked_global` from codegen → analysis fixes analysis-in-codegen violation. |
| IV. Explicit Over Implicit | ✅ PASS | No change to explicit coercion model. |
| V. Foundational Correctness | ✅ PASS | Phase 1 IS the foundational work that enables later phases. |
| VI. Cross-Cutting Semantics | ✅ PASS | Value model functions become truly shared via `core/values.py`. |
| VII. Minimize Runtime Surface | ✅ PASS | No new runtime calls added. Value model functions moved to core but still called the same way. |
| VIII. Research Before Implementation | ✅ PASS | Research phase completed — see [research.md](research.md). Key findings: C-04 already done, NameTranslator already moved, 18 imports (not 15), C-06 root cause is exclusive forms missing from detection. |

**Post-design re-check**: All gates still pass. No violations introduced.

## Project Structure

### Documentation (this feature)

```text
specs/019-foundation-cleanup/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Module entity definitions
├── quickstart.md        # Quick verification guide
├── contracts/
│   └── module-contracts.md  # Public API contracts for new modules
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── core/
│   ├── values.py          # NEW — mumps_canonical_str, m_num, m_str, m_truth, m_compare, m_add, m_sub, m_mul
│   ├── parsing.py         # NEW — parse_subscripted_name, canonicalize_subscript
│   ├── tokenizer.py       # NEW — split_at_toplevel
│   ├── names.py           # EXISTING — NameTranslator, translate_name (already canonical home)
│   ├── subscripts.py      # MODIFIED — delegates to core/values.py
│   ├── scope.py           # MODIFIED — delegates to core/parsing.py
│   ├── indirection.py     # MODIFIED — delegates to core/parsing.py, core/tokenizer.py, core/values.py
│   └── exceptions.py      # EXISTING — unchanged
├── asg/
│   ├── elements.py        # MODIFIED — MRoutine gains has_exclusive_kill, has_exclusive_new
│   └── ...                # unchanged
├── analysis/
│   ├── variables.py       # MODIFIED — new exclusive detection, receives contains_naked_global
│   ├── for_analysis.py    # MODIFIED — delegates write-detection to variables.py
│   ├── semantic_analyzer.py  # MODIFIED — _analyze_kill_like, _analyze_call_arguments, unwrap assertion
│   └── ...                # unchanged
├── codegen/
│   ├── helpers.py         # MODIFIED — re-exports from core/values.py, retains m_div/m_mod/m_range
│   ├── names.py           # EXISTING — re-export shim (unchanged)
│   ├── exceptions.py      # EXISTING — already correct (unchanged)
│   ├── expressions.py     # MODIFIED — contains_naked_global removed, reads ASG annotation
│   ├── shared_state.py    # MODIFIED — routine_uses_dynamic_locals adds exclusive flags
│   ├── indirection.py     # MODIFIED — dead XECUTE stubs removed
│   ├── statements.py      # NOT MODIFIED in Phase 1 (Phase 2 target)
│   └── ...                # unchanged
├── runtime/
│   ├── __init__.py        # MODIFIED — 12 deferred imports replaced, generate_python via callback
│   ├── helpers.py         # MODIFIED — docstring fix, _is_canonical_numeric removed, delegates to core/values
│   ├── globals.py         # MODIFIED — 1 deferred import replaced
│   └── ...                # unchanged
└── parser/
    └── ...                # unchanged

tests/
├── unit/
│   ├── core/
│   │   ├── test_values.py     # NEW — tests for mumps_canonical_str, m_num, m_str, etc.
│   │   ├── test_parsing.py    # NEW — tests for parse_subscripted_name
│   │   └── test_tokenizer.py  # NEW — tests for split_at_toplevel
│   └── ...                    # existing tests updated for import paths
└── ...                        # all existing tests must pass
```

**Structure Decision**: Single project structure. New files are all under `src/m2py/core/`.
Test files added under `tests/unit/core/`. No new top-level directories.

## Research Findings (Phase 0 Summary)

Key discoveries that modify the spec's original assumptions:

| Finding | Impact |
|---------|--------|
| C-04 already done | FR-001 is a no-op — skip it |
| NameTranslator already in `core/names.py` | FR-017 is a no-op — skip it |
| 18 backward imports (not 15) | FR-015 scope is larger: 7 NameTranslator/translate_name sites need path change, 10 value-model sites need path change, 1 generate_python via callback |
| C-06: exclusive KILL/NEW not detected | Need new `has_exclusive_kill`/`has_exclusive_new` flags on MRoutine |
| `walk_statements()` exists on MScope | S-10 needs to audit/extend existing walker, not create new module |
| `m_format_output` docstring has wrong example | S-17 fix confirmed — last example line is incorrect |
| Functional test `pytest.xfail()` calls are dynamic guards | FR-025 "zero xfails" applies to markers, not runtime guards |

## Implementation Tracks

### Track A — Quick Wins & Analysis Cleanup (~2.5 days)

Sequential within track. All analysis/ and codegen/ files (non-overlapping with other tracks).

| Step | Item | Files | Effort |
|------|------|-------|--------|
| A1 | ~~C-04~~ (already done) | — | Skip |
| A2 | S-17: Fix `m_format_output` docstring | `runtime/helpers.py` | 15 min |
| A3 | S-18: Remove dead XECUTE stubs | `codegen/indirection.py` | 15 min |
| A4 | S-08: Kill analyzer deduplication | `analysis/semantic_analyzer.py` | 0.5 day |
| A5 | S-09: DO/GOTO/JOB argument helper | `analysis/semantic_analyzer.py` | 0.5 day |
| A6 | S-15: `unwrap_expression` assertion | `analysis/semantic_analyzer.py` | 0.5 day |
| A7 | C-06: Exclusive KILL/NEW detection | `asg/elements.py`, `analysis/variables.py`, `codegen/shared_state.py` | 0.5 day |

### Track B — Analysis Infrastructure (~2 days)

Sequential within track. Only touches `analysis/` and `codegen/expressions.py`.

| Step | Item | Files | Effort |
|------|------|-------|--------|
| B1 | S-20: `_check_var_modified_in_scope` delegates to `variables.py` | `analysis/for_analysis.py`, `analysis/variables.py` | 0.5 day |
| B2 | C-08: Move `contains_naked_global` to analysis | `codegen/expressions.py`, `analysis/variables.py` | 0.5 day |
| B3 | S-10: Audit/extend `MScope.walk_statements()` | `asg/elements.py`, analysis consumers | 1 day |

### Track C — Core Value Abstractions (~3 days)

The critical-path track. Creates `core/values.py`, moves value-model functions,
updates 18 import sites.

| Step | Item | Files | Effort |
|------|------|-------|--------|
| C1 | C-01: Create `core/values.py` with `mumps_canonical_str` | `core/values.py` (new) | 0.5 day |
| C2 | C-01: Wire `m_str` and `m_format_output` to delegate | `codegen/helpers.py`, `runtime/helpers.py` | 0.5 day |
| C3 | C-01: Wire `SubscriptCanonicalizer` to delegate | `core/subscripts.py` | 0.25 day |
| C4 | C-02: Move `m_num`, `m_str`, `m_truth`, `m_compare` to `core/values.py` | `core/values.py`, `codegen/helpers.py` | 0.5 day |
| C5 | C-02: Update 17 deferred imports in runtime/core | `runtime/__init__.py`, `runtime/helpers.py`, `runtime/globals.py`, `core/indirection.py` | 0.5 day |
| C6 | C-02: Inject `generate_python` as callback | `runtime/__init__.py`, call sites that construct runtime | 0.5 day |
| C7 | S-11: Remove `_is_canonical_numeric` duplicate | `runtime/helpers.py` | 0.25 day |
| C8 | S-06: Extract `_decimal_binop` | `core/values.py` (or `codegen/helpers.py` if m_add/m_sub/m_mul stay there) | 0.25 day |

**Note**: C4 depends on C1. C5 depends on C4. C6 is independent. C7 depends on C1+C4.

### Track D — Core Parsing Utilities (~2 days)

Independent of Tracks A and B. Slight dependency on Track C (if tokenizer needs
value functions, but it shouldn't).

| Step | Item | Files | Effort |
|------|------|-------|--------|
| D1 | S-07: Create `core/tokenizer.py` with `split_at_toplevel` | `core/tokenizer.py` (new) | 0.5 day |
| D2 | C-03: Create `core/parsing.py` with `parse_subscripted_name` | `core/parsing.py` (new) | 0.5 day |
| D3 | C-03+S-07: Update runtime `_parse_subscripted_name` to delegate | `runtime/__init__.py` | 0.5 day |
| D4 | C-03+S-07: Update `core/scope.py` and `core/indirection.py` to delegate | `core/scope.py`, `core/indirection.py` | 0.5 day |

### Cross-Track: Tests & Validation

After each track completes:
- Run `uv run pytest` — all 5682 tests must pass
- Update test imports as needed for moved functions
- Add new tests for `core/values.py`, `core/parsing.py`, `core/tokenizer.py`
- Write integration test: import runtime without codegen

## Parallelism

```
Track A ─────────────────── (analysis/semantic_analyzer.py, analysis/variables.py, codegen/)
Track B ─────────────────── (analysis/for_analysis.py, analysis/variables.py, codegen/expressions.py)
Track C ─────────────────── (core/values.py, codegen/helpers.py, runtime/*)
Track D ─────────────────── (core/parsing.py, core/tokenizer.py, core/scope.py, core/indirection.py)
```

**Conflict zones**:
- `analysis/variables.py`: Tracks A (C-06) and B (S-20, C-08) both touch this file.
  Resolve by doing A7 and B1/B2 sequentially if on same worker.
- `runtime/__init__.py`: Tracks C (import updates) and D (parse delegation) both touch this.
  Resolve by doing C5 before D3.
- `core/indirection.py`: Tracks C (import update) and D (parse delegation) both touch this.
  Resolve similarly.

**With 2 workers**: Worker 1 takes A+B (analysis focus), Worker 2 takes C+D (core focus).
~3–4 days. **Solo**: ~5–6 days.

## Complexity Tracking

No constitution violations. No complexity justifications needed.

## Phase 2 Gate

Phase 2 (Codegen Refactoring) is blocked until:
- [ ] `core/values.py` exists and all value-model functions are moved (Track C complete)
- [ ] `MScope.walk_statements()` is audited and extended if needed (Track B3 complete)
- [ ] All 5682+ tests pass with zero failures/xfails/skips
- [ ] Zero deferred codegen imports remain in runtime/core
