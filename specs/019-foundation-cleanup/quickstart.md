# Quickstart: Phase 1 — Foundation & Cleanup

**Branch**: `019-foundation-cleanup` | **Date**: 2026-02-09

## What This Feature Does

Phase 1 restructures M2PY's internal module organization to eliminate duplicated
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

# Verify no backward imports remain
rg "from m2py\.codegen" src/m2py/runtime/ src/m2py/core/
# Expected: zero results (except the generate_python callback pattern)

# Verify new modules exist
ls src/m2py/core/values.py src/m2py/core/parsing.py src/m2py/core/tokenizer.py

# Verify runtime can be imported without codegen
uv run python -c "from m2py.core.values import m_str, m_num, m_truth, m_compare; print('OK')"
```

## Key Changes Summary

| What | Before | After |
|------|--------|-------|
| `m_str`, `m_num`, `m_truth`, `m_compare` | `codegen/helpers.py` | `core/values.py` (re-exported from codegen for compat) |
| Canonical number formatting | 3 implementations | 1 in `core/values.py` |
| Subscript name parsing | 3 implementations | 1 in `core/parsing.py` |
| Paren-depth state machines | 13+ copies | 1 in `core/tokenizer.py` |
| Backward codegen imports | 18 deferred imports | 0 (callback for XECUTE) |
| Exclusive KILL/NEW detection | Not detected → `NotImplementedError` | Detected → `dynamic_locals = True` |

## Implementation Tracks

Work is organized into 4 independent tracks that can run in parallel:

- **Track A** (analysis cleanup): Trivial fixes, kill analyzer dedup, call-arg dedup, unwrap assertion, C-06 flag detection
- **Track B** (analysis infrastructure): Variable-write dedup, move `contains_naked_global`, audit `walk_statements`
- **Track C** (core values): Create `core/values.py`, move value-model functions, update 18 import sites, `_decimal_binop` extraction
- **Track D** (core parsing): Create `core/parsing.py` + `core/tokenizer.py`, consolidate 3 parsers + 13 state machines

All 4 tracks touch different files. Merge conflicts are unlikely.
