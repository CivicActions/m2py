# Quickstart: Phase 3 — Correctness Fixes & New Features

## Prerequisites

- Phase 2 (020-codegen-refactoring) merged and passing
- Python 3.10+
- `uv` installed
- Docker running (for YDB validation)

## Setup

```bash
# Ensure you're on the feature branch
git checkout 021-correctness-features

# Sync dependencies
uv sync

# Verify baseline — ALL 6023+ tests must pass
uv run pytest --tb=short -q

# Verify YDB is available
uv run python utils/run_mumps_ydb.py --code 'TEST W "Hello" Q'
```

## Per-Track Development Workflow

### Track A: Error Handling ($ETRAP/$ZTRAP/$ECODE/$STACK)

**Start here** — foundational for all other tracks.

```bash
# 1. Run existing error-handling tests
uv run pytest tests/ -k "etrap or ecode or error" -v

# 2. After implementing StackFrame dataclass, run
uv run pytest tests/test_runtime.py -v

# 3. Validate $ZTRAP semantics against YDB
uv run python utils/validate.py --code 'TEST S $ZT="ERR^test" W 1/0 Q
ERR W $ZS,! Q'

# 4. Validate $STACK
uv run python utils/validate.py --code 'TEST D SUB Q
SUB W $ST,! W $ST(1),! W $ST(1,"PLACE"),! Q'
```

### Track B: LOCK Indirection + TSTART Variables

```bash
# 1. Existing LOCK tests
uv run pytest tests/ -k "lock" -v

# 2. Validate LOCK indirection semantics
uv run python utils/validate.py --code 'TEST S X="^GLO" L @X W "locked" L  Q'

# 3. TSTART snapshot (saves for TRESTART, NOT for TROLLBACK)
uv run python utils/validate.py --code 'TEST S X=1 TS (X) S X=99 TC W X,! Q'
```

### Track C: $ZDATE + ZSYSTEM + LVUNDEF

```bash
# 1. Validate $ZDATE formats against YDB
uv run python utils/validate.py --code 'TEST W $ZD($H),! W $ZD($H,"YYYY-MM-DD"),! Q'

# 2. ZSYSTEM
uv run python utils/validate.py --code 'TEST ZSY "echo hello" W $ZSY,! Q'

# 3. LVUNDEF — must error unconditionally
uv run python utils/validate.py --code 'TEST W X Q'
```

### Track D: SVNs, SSVNs, Extended Globals

```bash
# 1. $ZSEARCH
uv run python utils/validate.py --code 'TEST W $ZSEARCH("/tmp/*"),! Q'

# 2. $ZMESSAGE
uv run python utils/validate.py --code 'TEST W $ZM(150373850),! Q'

# 3. Extended global references (bracket form)
uv run python utils/validate.py --code 'TEST S ^|"DEFAULT"|GLO=1 W ^|"DEFAULT"|GLO,! Q'
```

### Track E: READ #maxlen

```bash
# Test READ with character limit
echo "Hello World" | uv run python utils/validate.py --code 'TEST R X#5 W X,! Q'

# Test $KEY set after READ
echo "abc" | uv run python utils/validate.py --code 'TEST R X W $K,! Q'
```

## Key Commands

```bash
# Full test suite
uv run pytest

# Run only Phase 3 tests (once they exist)
uv run pytest tests/ -k "phase3 or correctness" -v

# Run with coverage
uv run pytest --cov=src/m2py --cov-report=term-missing

# Validate specific MUMPS code against YDB
uv run python utils/validate.py --code 'ROUTINE W "test" Q'

# Debug mode — shows AST and generated Python
uv run python utils/validate.py --debug --code 'ROUTINE W "test" Q'

# Run MUMPS through YDB only (reference output)
uv run python utils/run_mumps_ydb.py --code 'ROUTINE W "test" Q'
```

## Implementation Order

Recommended sequence within a track:

1. Add/update ASG node types if needed (src/m2py/asg/)
2. Update grammar rules if needed (src/m2py/parser/)
3. Implement runtime methods (src/m2py/runtime/)
4. Implement codegen (src/m2py/codegen/)
5. Write tests — unit + integration + YDB validation
6. Run full suite: `uv run pytest`

## Important Notes

- **TSTART restart vars**: Save locals for TRESTART, NOT TROLLBACK. TROLLBACK only restores globals.
- **ZLINK**: Already fully implemented — no Phase 3 work needed.
- **$ZTRAP/$ETRAP mutual exclusion**: Setting one implicitly NEWs the other at the current stack level.
- **Constitution §IV update**: Remove "treat as empty string" for undefined variables — change to unconditional M6 error (aligns with §I and §II).
- **Zero regression tolerance**: Every commit must pass all 6023+ existing tests.
