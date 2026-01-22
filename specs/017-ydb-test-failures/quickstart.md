# Quickstart: YDB Test Suite Failure Resolution

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Research**: [research.md](research.md)

## Overview

This spec resolves 147 YDB test suite failures across 6 categories:
1. TRAMPOLINE enhancement for argumentless KILL/NEW (10 tests)
2. Missing operators and expression types (1 test)
3. LHS $PIECE extensions for globals/indirection (3 tests)
4. Codegen syntax error fixes (1 test)
5. LIM-015 Z-extension xfails (12 tests)
6. Behavioral bug fixes (75 tests)
7. Merge suite infrastructure (33 tests)

## Prerequisites

```bash
# Verify environment
uv run pytest --version
docker run --rm ydb echo "YDB ready"

# Run current test baseline
uv run pytest tests/functional/ -v --tb=no | tee baseline.txt
```

## Development Workflow

### 1. Fix a Single Test

```bash
# Identify failing test
uv run pytest tests/functional/test_mugj.py::test_v1nst1 -v

# Check YDB expected output
cat tests/functional/mugj/outref/mugj.txt | grep -A10 "V1NST1"

# Debug transpiled output
uv run python utils/validate.py --debug tests/functional/mugj/inref/V1NST1.m

# Run after fix
uv run pytest tests/functional/test_mugj.py::test_v1nst1 -v
```

### 2. Configure xfail for LIM-015

```python
# In tests/functional/suite_definitions.py
RoutineDefinition("V1SVH", "V1SVH", skip_reason="LIM-015: $ZHOROLOG not supported"),
```

### 3. Validate Against YDB

```bash
# Compare m2py output to YDB
uv run python utils/validate.py --code 'TEST S X=1 K W X Q'

# Run through Docker
echo -e 'TEST\n set X=1 kill write X' | docker run --rm -i ydb
```

## Key Files

| Purpose | File |
|---------|------|
| TRAMPOLINE state | `src/m2py/codegen/shared_state.py` |
| Statement codegen | `src/m2py/codegen/statements.py` |
| Expression codegen | `src/m2py/codegen/expressions.py` |
| Runtime helpers | `src/m2py/runtime/helpers.py` |
| Variable analysis | `src/m2py/analysis/variables.py` |
| Test fixtures | `tests/functional/conftest.py` |
| Suite definitions | `tests/functional/suite_definitions.py` |
| Limitations registry | `src/m2py/limitations.py` |

## Human Review Gates

**STOP and request human review when**:
1. Marking a test as "impossible to fix"
2. Proposing architectural changes beyond spec scope
3. Modifying test infrastructure (conftest.py fixtures)
4. Adding new entries to limitations.py
5. Changing existing unit tests
6. Discovering scope expansion needs
7. Finding shared root cause across 5+ tests

## Validation Checklist

- [ ] All 147 tests addressed (pass, xfail, or human-reviewed)
- [ ] No new test failures introduced
- [ ] Each fix validated against YDB
- [ ] Constitution principles maintained (semantic correctness first)
- [ ] Documentation updated for any new limitations
