# Regression Recovery Plan

> Tracking regressions introduced between `ea3bbec8` (last clean CI) and `cc63e13b` (HEAD).

## CI Regression Matrix

All non-munit splits (unit, functional-mvts, functional-other, slow, quality, lint) **pass on every commit**.

| Commit | Description | inmemory munit | yottadb munit | iris munit |
|--------|-------------|---------------|---------------|------------|
| `ea3bbec8` | perf: fast-path checks | **PASS** 24p, 1xf | **PASS** 24p, 1xf | **PASS** 24p, 1xf |
| `3c8f1dc4` | feat: Phase 12 Registration | **FAIL** 1f, 23p, 1xf | **FAIL** 1f, 23p, 1xf | **PASS** 24p, 1xf |
| `5992797f` | fix: rwgs depth limit | **FAIL** 1f, 23p, 1xf | **FAIL** 1f, 23p, 1xf | **PASS** 24p, 1xf |
| `29f451b3` | fix: iterative GotoExternal | **FAIL** 2f, 22p, 1xf | **FAIL** 2f, 21p, 2xf | **FAIL** 1f, 22p, 2xf |
| `cc63e13b` | fix: ZZDGPTCO1 DT=0 + kill | **FAIL** 2f, 22p, 1xf | **KILLED** exit 142 | **FAIL** 1f, 22p, 2xf |

## Two Distinct Regressions

### Regression 1: ZZDGPTCO1 — introduced at `3c8f1dc4`

| Backend | Symptom | Deterministic? |
|---------|---------|----------------|
| inmemory | 9 tests, 0 failures, **1 error** (one entry tag crashes) | Yes |
| yottadb | 15 tests, 8 failures, 5 errors (varies: stale globals) | Yes (count varies) |
| iris | PASS | — |

- **inmemory**: One of the 5 CHKCUR entry tags hits a runtime exception
- **yottadb**: Stale `^DG(45.86)` accumulates + `DT=today` triggers ADDREC
- **IRIS passes**: Likely has cleaner session isolation or handles date logic differently

### Regression 2: DMUFINIT — introduced at `29f451b3`

| Backend | Symptom | Deterministic? |
|---------|---------|----------------|
| inmemory | KeyError: 'DIIENS' at 4217 globals written (82s) | Yes |
| yottadb | KeyError: 'DIIENS' at 4217 globals written (10s) | Yes |
| iris | KeyError: 'DIIENS' at 4217 globals written (22s) | Yes |

Identical crash on all 3 backends at the same point. Root cause is the iterative
GotoExternal change corrupting variable scope during the DMUFINIT execution chain.

### cc63e13b YDB Kill (exit 142)

The YDB process was killed (SIGALRM) after only 8 of ~25 tests, likely due to
`g.kill("DG", ("45.86",))` + re-seeding causing excessive YDB I/O within the
Docker container's timeout.

---

## Recovery Phases

### Phase 1: Fix DMUFINIT — `_pending_new_entries` ordering bug

**Root cause**: When entry functions re-raise `GotoExternal` (iterative approach
from `29f451b3`), NEW entries are saved to `_rt._pending_new_entries` in
**forward** order but unwound via `.pop()` (**LIFO/reverse**). This mismatch
corrupts `_scope` — variables like `DIIENS` get incorrectly cleared.

Three append sites all use forward order:
- `NewScopeManager.__exit__` (`helpers.py`) appends `_restore_actions` forward
- `routine.py` extends with `state._new_stack` forward
- `_unwind_pending_news` (`runtime/__init__.py`): `.pop()` processes reverse

In normal (non-GOTO) execution, `__exit__` processes `reversed(self._restore_actions)`
— correct LIFO. But the pending path appends forward + pops reverse = **wrong order**.

**Fix**: Reverse the pending list before processing in `_unwind_pending_news()`.

**Files**:
- `src/m2py/runtime/__init__.py` — `_unwind_pending_news()`
- `tests/unit/codegen/test_goto_external_reraise.py` — ordering test

**Verification**:
- DMUFINIT test passes on inmemory
- All existing munit tests still pass

### Phase 2: Diagnose and fix ZZDGPTCO1 inmemory error *(depends on Phase 1)*

**Symptom**: 9 tests, 0 failures, 1 error — consistently on inmemory.

**Steps**:
1. Re-test after Phase 1 — the scoping bug may be causing the inmemory error
2. If still failing: run locally with verbose output to identify which entry tag
3. Inspect the failing code path in `DGPTCO1.m`
4. Fix based on diagnosis

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
