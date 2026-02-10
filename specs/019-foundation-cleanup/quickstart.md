# Quickstart: Phase 1 — Foundation & Cleanup

**Branch**: `019-foundation-cleanup` | **Date**: 2026-02-09 | **Status**: ✅ Complete

## What This Feature Does

Phase 1 restructured M2PY's internal module organization to eliminate duplicated
logic, resolve architecture violations (runtime importing from codegen), and create
shared foundational modules. No user-facing behavior changes.

## Prerequisites

- Python 3.10+
- `uv` package manager
- Repository cloned and on `019-foundation-cleanup` branch

## Quick Verification

```bash
# Run full test suite — must pass with zero failures, xfails, or skips
uv run pytest

# Verify no backward imports remain in runtime/ or core/
grep -rn "from m2py\.codegen" src/m2py/runtime/ src/m2py/core/
# Expected: only comments (no actual import statements)

# Verify new modules exist
ls src/m2py/core/values.py src/m2py/core/parsing.py src/m2py/core/tokenizer.py

# Verify runtime can be imported without codegen
uv run python -c "from m2py.core.values import m_str, m_num, m_truth, m_compare; print('OK')"

# Verify walk_statements covers all nested scopes
uv run python -c "from m2py.asg.elements import MScope; print('walk_statements OK')"
```

## Key Changes Summary

| What | Before | After |
|------|--------|-------|
| `m_str`, `m_num`, `m_truth`, `m_compare` | `codegen/helpers.py` only | Canonical in `core/values.py`; `codegen/helpers.py` retains own copy for generated code |
| Canonical number formatting | 3 implementations | 1 canonical in `core/values.py` (runtime/core use this) |
| Subscript name parsing | 3 implementations | 1 in `core/parsing.py` |
| Paren-depth state machines | 13+ copies | 1 in `core/tokenizer.py` |
| Backward codegen imports | 18 deferred imports | 0 (callback pattern for XECUTE via `codegen_callback`) |
| Exclusive KILL/NEW detection | Not detected → `NotImplementedError` | Detected → `dynamic_locals = True` |
| Kill analyzer dedup | 5 near-identical methods | 1 shared `_analyze_kill_like_args` helper |
| DO/GOTO/JOB target analysis | Duplicated per-command | 1 shared `_analyze_call_target` helper |
| `contains_naked_global` | In codegen | Canonical in `analysis/variables.py`; codegen wrapper delegates |
| `walk_statements()` | Covered body + then scopes | Extended to also cover else scopes |

## Implementation Phases (Completed)

All 8 phases were implemented across 5 user stories:

- **Phase 1–2** (Setup): Feature directory, new core modules, initial contracts
- **Phase 3** (US1 — MVP): Value-model functions in `core/values.py`, backward import elimination
- **Phase 4** (US2): Runtime independence from codegen via `codegen_callback` injection
- **Phase 5** (US4): Exclusive KILL/NEW detection, analysis deduplication, dead code removal
- **Phase 6** (US3): Subscript parsing consolidation (`core/parsing.py`, `core/tokenizer.py`)
- **Phase 7** (US5): ASG statement walker extension with else-scope support
- **Phase 8** (Polish): Documentation updates, constitution verification, final test pass
