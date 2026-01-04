# Quickstart: Complete Stub Tests

**Feature**: 003-complete-stub-tests  
**Date**: January 4, 2026

## Prerequisites

- Python 3.10+
- uv package manager
- Repository cloned with all submodules

## Quick Verification

```bash
# Check current state
uv run pytest tests/unit/parser/ tests/unit/asg/ tests/unit/analysis/ tests/unit/meta/ tests/unit/cross_cutting/ -v 2>&1 | tail -5
# Expected: 1189 passed, 93 skipped, 687 xfailed

# Run coverage audit
uv run python utils/audit_tests.py
```

## Implementation Workflow (FR-010)

Each batch follows the MUMPS-spec-driven validation process. The goal is ensuring ASG quality for Python code generation.

### 1. Pick a Batch

Reference `research.md` for batch assignments. Start with Phase A for maximum coverage impact.

Example: Start with batch A1 (ASG s7_1_3_ssvns, 8 tests)

### 2. Research the MUMPS Spec

**Read the spec CAREFULLY** - understand what semantic information code generation will need.

```bash
# Find relevant spec section
ls mumps-reference/ | grep -i "s7_1_3\|ssvn"

# Read spec
cat mumps-reference/1995__a107XXX.md  # Find correct file
```

### 3. Find Test Examples

Search for real-world examples to **validate your understanding** of the spec:

```bash
# Search MUMPS reference (authoritative) first
grep -r "^\$DEVICE\|^\$IO\|^\$JOB" mumps-reference/examples__*.md mumps-reference/notes__*.md | head -20

# Fallback to YDBTest suite
grep -r "pattern" YDBTest/*/inref/ | head -10

# Fallback to VistA
grep -r "pattern" VistA-M/ | head -10
```

### 4. Evaluate Current ASG Quality

**Critical step**: Assess if the ASG meets codegen requirements. This requires **developer judgment** - not just pass/fail.

```bash
# Create test file with example from step 3
cat > /tmp/ssvn_test.m << 'EOF'
SSVNTEST ;Test SSVNs
 W $DEVICE
 W $IO
 Q
EOF

# Validate ASG (full detail for thorough review)
uv run python utils/validate_asg.py /tmp/ssvn_test.m

# READ the output and ask:
# 1. Does the ASG capture ALL semantic information from source?
# 2. Is it structured for easy Python code generation?
# 3. Are variable references, types, scopes correct?
# 4. What's MISSING that codegen would need?
```

**Important**: Gaps become test assertions. Tests should assert the CORRECT structure (driving implementation fixes).

**Note**: validate_asg.py may need enhancement (FR-012) to accept stdin/argument input.

### 5. Check for Existing Tests

```bash
# Search by feature name
grep -r "SSVN\|special_variable" tests/unit/

# Consolidate rather than duplicate
```

### 6. Implement Tests

Edit the test file, converting stubs to real assertions:

```bash
code tests/unit/asg/s7_expressions/test_s7_1_3_ssvns.py
```

Convert from:
```python
@pytest.mark.stub
@pytest.mark.xfail(reason="Not yet implemented: $DEVICE SSVN")
def test_device_ssvn_analyzed(self):
    pytest.fail("Stub - implement test")
```

To (ASG test - assert semantic properties):
```python
def test_device_ssvn_analyzed(self):
    """$DEVICE SSVN is correctly analyzed (§7.1.3)."""
    code = "ROUTINE\n W $DEVICE"
    routine = parse_and_analyze(code)
    stmt = routine.labels[0].lines[0].statements[0]
    assert isinstance(stmt.arguments[0], MSpecialVariable)
    assert stmt.arguments[0].name == "$DEVICE"
```

Parser tests assert textX model structure (node types, attributes, child nodes):
```python
def test_device_ssvn_parsed(self):
    """$DEVICE SSVN parses correctly (§7.1.3)."""
    code = "W $DEVICE"
    result = parse_line(code)
    assert result.__class__.__name__ == "Line"
    assert result.statements[0].command == "W"
    arg = result.statements[0].arguments[0]
    assert arg.__class__.__name__ == "SpecialVariable"
    assert arg.name == "DEVICE"
```

### 6. Run and Verify

```bash
# Run batch tests
uv run pytest tests/unit/asg/s7_expressions/test_s7_1_3_ssvns.py -v

# Check no xfails
uv run pytest tests/unit/asg/s7_expressions/test_s7_1_3_ssvns.py -v 2>&1 | grep -c XFAIL

# Update matrix
uv run python utils/audit_tests.py --output docs/coverage-matrix.md
```

### 7. Run Batch Tests and Fix Gaps

```bash
# Run batch tests
uv run pytest tests/unit/asg/s7_expressions/test_s7_1_3_ssvns.py -v

# If implementation gaps found:
# 1. Fix in src/m2py/
# 2. Update documentation (see FR-016 scope below)
# 3. Commit implementation fix BEFORE test changes
# 4. Re-run tests
```

**Documentation Updates (FR-016)**: When implementation changes address test gaps:
- `docs/asg/` - ASG node types, new fields, code generation notes
- `docs/analysis/` - Analysis pass behavior changes
- `docs/codegen/` - Translation strategies affected by changes
- `docs/examples/` - MUMPS-to-ASG mappings if affected
- `docs/architecture.md`, `docs/grammar_overview.md`, `docs/limitations.md` - as applicable

### 8. Verify Batch Complete (FULL SUITE)

```bash
# REQUIRED: Regenerate coverage matrix (per-batch)
uv run python utils/audit_tests.py --output docs/coverage-matrix.md

# CRITICAL: Run FULL test suite (parallel via pytest-xdist)
uv run pytest

# For high-risk changes to shared code, run full suite mid-batch too
```

## Success Criteria

The feature is complete when:

```bash
uv run pytest tests/unit/parser/ tests/unit/asg/ tests/unit/analysis/ tests/unit/meta/ tests/unit/cross_cutting/ -v
# Shows: ~1876 passed, 93 skipped, 0 xfailed

# AND full suite passes
uv run pytest
```

## Handling Regressions

If your implementation fix causes a previously-passing test to fail:

1. **STOP** - Don't immediately change the old test
2. Re-read MUMPS reference for affected construct
3. Find concrete examples in MUMPS reference (`mumps-reference/examples__*.md`) or YDBTest
4. Confirm new ASG is semantically correct
5. Verify new behavior **IMPROVES** codegen quality (not just different)
6. Only if 100% confident: Update the regressing test
7. If uncertain: **Revert** and document for later investigation

## Common Issues

### Test Fails After Removing xfail

The stub placeholder was masking a real issue. Debug:

```bash
uv run pytest tests/unit/path/to/test.py::TestClass::test_method -v --tb=long
```

### Parser Returns None

The grammar doesn't match the input. Check:
- Correct grammar rule name in metamodel
- Input syntax matches grammar expectations

### ASG Missing Attribute

The semantic analyzer doesn't populate the field. Check:
- `src/m2py/analysis/semantic_analyzer.py` for analysis code
- `src/m2py/asg/statements.py` for field definitions

## Key Files

| File | Purpose |
|------|---------|
| `specs/003-complete-stub-tests/research.md` | Batch assignments and prioritization |
| `specs/003-complete-stub-tests/contracts/batch-workflow.md` | Detailed FR-010 workflow |
| `specs/003-complete-stub-tests/tasks.md` | Progress tracking (created by /speckit.tasks) |
| `utils/validate_asg.py` | ASG structure validation |
| `utils/audit_tests.py` | Coverage matrix generation |
| `docs/coverage-matrix.md` | Test coverage status |
