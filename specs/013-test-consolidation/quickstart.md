# Quickstart Guide: Test Suite Consolidation & VistA Compatibility

**Spec**: 013-test-consolidation  
**Phase**: 1 - Design  
**Date**: 2026-01-17

## Overview

This spec resolves 286 xfail test stubs through three operations:
1. **DELETE** (~44 stubs) - Remove redundant stubs with existing coverage
2. **CONVERT** (~39 stubs) - Change to `execute_mumps` with real assertions
3. **IMPLEMENT** (~200 features) - Build missing functionality

## Prerequisites

- Python 3.10+
- uv package manager
- Docker (for YDB validation)

```bash
# Verify environment
uv run pytest --version
docker run --rm ydb echo "YDB OK"
```

## Workflow Summary

### Step 1: Verify DELETE Candidates

Before deleting any stub, verify spec-aligned coverage exists:

```bash
# Find existing tests for a feature
rg "execute_mumps.*multiplication" tests/
rg "W 3\*4" tests/

# Verify the feature works
uv run python utils/validate.py --code 'TEST W 3*4 Q'
```

### Step 2: Convert CONVERT Candidates

Change fixture from `generate_python` to `execute_mumps`:

**Before**:
```python
@pytest.mark.xfail(reason="placeholder")
def test_division(generate_python):
    code = generate_python("TEST\n W 10/4\n Q")
    assert "10 / 4" in code  # ❌ Checks code structure
```

**After**:
```python
def test_division(execute_mumps):
    result = execute_mumps("TEST\n W 10/4\n Q")
    assert result == "2.5"  # ✅ Checks actual output
```

### Step 3: Implement Missing Features

For each IMPLEMENT category, follow this pattern:

1. **Research**: Check ASG structure in `docs/asg/`
2. **Parse**: Verify grammar supports the construct
3. **Analyze**: Add any needed analysis passes
4. **Generate**: Implement codegen
5. **Test**: Create tests using `execute_mumps`
6. **Validate**: Verify against YDB

## Implementation Order

### Phase A: Stub Cleanup (DELETE + CONVERT)

**Goal**: Reduce xfail count by ~83 (44 DELETE + 39 CONVERT)

1. Process DELETE candidates first (no code changes needed)
2. Convert working features one category at a time
3. Run full test suite after each batch

### Phase B: High-Impact Features

**Goal**: Implement features with >10% VistA usage

| Feature | FR | Files | Notes |
|---------|-------|-------|-------|
| $ASCII/$CHAR | FR-013/14 | 10,564 | String intrinsics |
| Transactions | FR-015 | 9,967 | DB abstraction |
| READ | FR-016 | 4,556 | Input operations |
| $JUSTIFY | FR-017 | 4,487 | Formatting |
| USE | FR-018 | 3,598 | Device selection |
| LOCK | FR-019 | 3,457 | DB abstraction |
| $TRANSLATE | FR-020 | 2,962 | String intrinsic |
| $TEXT | FR-021 | 9,050 | Line mapping |

### Phase C: Medium-Impact Features

**Goal**: Implement features with 1-10% VistA usage

| Feature | FR | Files |
|---------|-------|-------|
| OPEN/CLOSE | FR-022 | 2,452 |
| Exclusive NEW | FR-023 | 1,812 |
| JOB | FR-024 | 508 |
| $FNUMBER | FR-025 | 460 |
| Error processing | FR-026 | 837 |

### Phase D: Low-Impact Features

**Goal**: Implement remaining VistA-used features

- $REVERSE (FR-027)
- Timeouts (FR-028)
- SSVNs (FR-029)
- Pattern alternation (FR-030)
- $NEXT (FR-031)
- VIEW (FR-032)
- BREAK (FR-033)

### Phase E: Math Functions & Z-Commands

- Math functions (FR-034 through FR-038)
- Z-commands with VistA usage (FR-039 through FR-044)
- $ZERROR (FR-045)

### Phase F: Fall-Through Semantics

**Goal**: Implement label fall-through (FR-007 through FR-011)

This is a cross-cutting change that affects codegen for all labels.

## Testing Commands

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/codegen/test_spec_009_globals.py

# Run with xfail summary
uv run pytest --tb=no -q | grep -E "xfail|XFAIL"

# Count xfail tests
uv run pytest --collect-only | grep xfail | wc -l

# Validate against YDB
uv run python utils/validate.py --code 'TEST W 2**3 Q'
uv run python utils/validate.py --debug --code 'TEST S X=1 W X Q'
```

## Database Backend Testing

```bash
# Test with Memory backend (default)
M2PY_GLOBAL_BACKEND=inmemory uv run pytest tests/unit/runtime/

# Test with YottaDB (requires yottadb package)
M2PY_GLOBAL_BACKEND=yottadb uv run pytest tests/integration/
```

## File Locations

| Artifact | Location |
|----------|----------|
| Test stubs | `tests/unit/codegen/test_gaps_*.py` |
| Spec-aligned tests | `tests/unit/codegen/test_spec_*.py` |
| ASG definitions | `src/m2py/asg/` |
| Codegen | `src/m2py/codegen/` |
| Runtime | `src/m2py/runtime/` |
| DB backends | `src/m2py/runtime/globals.py` |

## Success Metrics

- [ ] Zero xfail tests (SC-001)
- [ ] Zero test duplicates (SC-002)
- [ ] All CONVERT tests use `execute_mumps` (SC-003)
- [ ] Fall-through outputs "ABC" (SC-004)
- [ ] `W 2**3` outputs "8" (SC-005)
- [ ] Test time increase <20% (SC-006)
- [ ] All VistA features pass validation (SC-007)

## Common Issues

### "NAKEDERR: Naked reference without prior global access"
- Ensure global is accessed before using naked reference `^(subscripts)`
- Check test setup initializes globals

### Import errors for yottadb/iris
- These backends are stubs until integration specs
- Use `M2PY_GLOBAL_BACKEND=inmemory` for testing

### ZGOTO stack unwinding
- Complex feature requiring exception-based implementation
- See contracts/z-commands.md for design
