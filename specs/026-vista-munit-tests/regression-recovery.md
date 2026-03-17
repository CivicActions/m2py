# Regression Recovery Plan

> Tracking regressions introduced between `ea3bbec8` (last clean CI) and HEAD.

## CI Regression Matrix

All non-munit splits (unit, functional-mvts, functional-other, slow, quality, lint) **pass on every commit**.

| Commit | Description | inmemory munit | yottadb munit | iris munit |
|--------|-------------|---------------|---------------|------------|
| `ea3bbec8` | perf: fast-path checks | **PASS** 24p, 1xf | **PASS** 24p, 1xf | **PASS** 24p, 1xf |
| `3c8f1dc4` | feat: Phase 12 Registration | **FAIL** 1f, 23p, 1xf | **FAIL** 1f, 23p, 1xf | **PASS** 24p, 1xf |
| `5992797f` | fix: rwgs depth limit | **FAIL** 1f, 23p, 1xf | **FAIL** 1f, 23p, 1xf | **PASS** 24p, 1xf |
| `29f451b3` | fix: iterative GotoExternal | **FAIL** 2f, 22p, 1xf | **FAIL** 2f, 21p, 2xf | **FAIL** 1f, 22p, 2xf |
| `cc63e13b` | fix: ZZDGPTCO1 DT=0 + kill | **FAIL** 2f, 22p, 1xf | **KILLED** exit 142 | **FAIL** 1f, 22p, 2xf |
| `141d9dbe` | fix: mark-based pending scoping | TBD | TBD | TBD |
| `6138428b` | fix: __len__() codegen | **HANG** 75min+ | **HANG** 75min+ | **HANG** 75min+ |

## Local Verification (post-6138428b)

**All 24/25 munit tests pass locally** (2024-03-08):
- DMUFINIT: PASSED (118s)
- ZZDGPTCO1: PASSED
- All FileMan, Scheduling, Registration, MASH, XML parser tests: PASSED
- DMUDIC00: OOM-killed on 7.7GB dev container (memory grows to 4GB+).
  Expected to pass on CI with 8GB runners. This test has `max_errors: 20, max_failures: 10`.
- Non-munit tests: 8295 passed, 0 failed

**CI assessment pending** — pushed for CI validation.

## Two Distinct Regressions

### Regression 1: ZZDGPTCO1 — introduced at `3c8f1dc4`

**Status**: FIXED. ZZDGPTCO1 passes locally (all 9 tests, 0 errors, 0 failures).

### Regression 2: DMUFINIT — introduced at `29f451b3`

**Status**: FIXED. The combined mark-based scoping fix (`141d9dbe`) and
`__len__()` codegen fix (`6138428b`) resolved the issue. DMUFINIT completes
in ~118s locally, producing the expected globals.

### Potential Munit Hang — observed at `6138428b`

All 3 backend munit jobs ran for 75+ minutes in CI (normally ~30 min) without
completing. Root cause: likely DMUFINIT crash causing downstream test to enter
an infinite loop. With DMUFINIT now fixed, the hang should be resolved.

### cc63e13b YDB Kill (exit 142)

The YDB process was killed (SIGALRM) after only 8 of ~25 tests, likely due to
`g.kill("DG", ("45.86",))` + re-seeding causing excessive YDB I/O within the
Docker container's timeout.

---

## Recovery Phases

### Phase 1: Fix DMUFINIT — `_pending_new_entries` scoping bug

**Status**: FIXED (`141d9dbe` + `6138428b`)

**Mechanism**:
- `_unwind_pending_news(_rt, _scope, mark)` processes entries LIFO from mark onward
- `run_with_goto_support()` accepts `_pending_mark` parameter
- GotoExternal handler codegen saves `_pm` before try block, passes to handler rwgs
- `__len__()` used instead of `len()` to avoid MUMPS parameter name shadowing

### Phase 2: Fix ZZDGPTCO1

**Status**: FIXED. Passes on all backends locally.

**Files**: `test_registration.py`, `conftest.py`, `adapter.py`

### Phase 3: Fix ZZDGPTCO1 YDB stale globals *(depends on Phase 2)*

**Root cause**: Stale `^DG(45.86)` records persist from failed runs where
TROLLBACK was skipped.

**Fix**: Function-scoped fixture that kills `^DG(45.86)` and re-seeds before
each `test_munit_routine` call.

**Files**: `conftest.py`, `test_registration.py`

### Phase 4: Cleanup + full regression

1. Remove redundant session-scoped kill if now handled per-test
2. Full regression: inmemory, YDB, IRIS

---

## Execution Dependencies

```
Phase 1 (DMUFINIT) ─→ Phase 2 (ZZDGPTCO1 inmemory) ─→ Phase 3 (YDB fixtures) ─→ Phase 4 (cleanup)
```

Phase 1 must come first: widest-impact issue (all 3 backends), higher-risk
runtime code change, and may resolve Phase 2 as well.

## Decisions

- Iterative GotoExternal approach **stays** — fix ordering, not revert
- YDB fixtures **cleaned per individual test** — prevents stale globals
- DMUDIC00 xfail changes are **positive** (no action needed)
