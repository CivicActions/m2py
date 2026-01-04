# Contract: Batch Workflow

**Feature**: 003-complete-stub-tests  
**Date**: January 4, 2026

## Batch Implementation Workflow

Each batch follows the FR-010 MUMPS-spec-driven validation process. The goal is to ensure tests validate the CORRECT ASG structure for Python code generation, not just the current implementation behavior.

### Step 1: Research (MUMPS Spec)

Read the relevant MUMPS specification section **carefully**:
- Check `mumps-reference/` for local spec mirror
- Online reference: https://71.174.62.16/Demo/AnnoStd
- Note key behaviors, edge cases, and examples
- **Key insight**: Understand what semantic information code generation will need

### Step 2: Find Examples

Search for example code in order of preference. Use these to **validate your understanding** of the spec:

1. **MUMPS reference examples/notes** (most authoritative):
   ```bash
   grep -r "PATTERN" mumps-reference/examples__*.md mumps-reference/notes__*.md
   ```

2. **YDBTest suite** (fallback 1):
   ```bash
   grep -r "PATTERN" YDBTest/*/inref/
   ```

3. **VistA codebase** (fallback 2):
   ```bash
   grep -r "PATTERN" VistA-M/
   ```

### Step 3: Evaluate ASG Quality

Use validate_asg.py to assess if the **current ASG meets quality requirements for Python code generation**:

```bash
# Create temp test file with example from Step 2
echo "TESTLAB^TEST\n S X=1" > /tmp/test.m

# Validate ASG (full detail - read output carefully)
uv run python utils/validate_asg.py /tmp/test.m

# CRITICAL: Developer must READ the ASG output and evaluate:
# 1. Does the ASG capture ALL semantic information from the source?
# 2. Is the information structured for easy Python code generation?
# 3. Are variable references, types, and scopes correctly represented?
# 4. Are control flow constructs (FOR, GOTO) properly classified?
```

**Important**: ASG quality requires **developer judgment**, not just pass/fail. Read the output and decide:
- Is this sufficient for Python codegen, or are there gaps?
- What semantic information is missing that codegen would need?
- Document gaps - they become test assertions driving implementation fixes

**Note**: validate_asg.py may need enhancement (FR-012) to accept M code from stdin/argument.

### Step 4: Check for Existing Tests

Search for tests that may already cover this functionality:

```bash
# Search by feature name
grep -r "feature_name" tests/unit/

# Search by MUMPS construct
grep -r "SET.*=" tests/unit/parser/

# Check if tests need consolidation vs new implementation
```

**If existing tests found**: Consolidate into spec-aligned test function rather than duplicating.

### Step 5: Implement Tests

For each stub in the batch:

1. Remove `@pytest.mark.stub` marker
2. Remove `@pytest.mark.xfail` marker
3. Replace `pytest.fail("Stub - implement test")` with actual assertions
4. **Parser tests**: Assert on textX model object structure (node types, attribute values, child nodes)
5. **ASG tests**: Assert the CORRECT ASG structure (from Step 3 analysis), not just current behavior
6. Use patterns from contracts/test-implementation.md

### Step 6: Fix Implementation Gaps

If tests fail due to missing/incorrect functionality:

1. Document the gap in the test docstring
2. Implement the fix in `src/m2py/`
3. **Update documentation** for any changed behavior (see FR-016 scope below)
4. Re-run related tests to verify fix
5. **Commit implementation fix BEFORE test changes** (batch related fixes together)
6. For high-risk changes (shared code paths), run full test suite mid-batch

**Documentation Scope (FR-016)**: When implementation changes affect behavior, update relevant docs:
- `docs/asg/` - ASG node types, fields, code generation notes
- `docs/analysis/` - Analysis pass behavior, new fields populated
- `docs/codegen/` - Translation strategies, Python patterns
- `docs/examples/` - MUMPS-to-ASG mappings if affected
- `docs/architecture.md`, `docs/grammar_overview.md`, `docs/limitations.md`, `docs/testing.md` - as applicable

Note: `docs/coverage-matrix.md` is auto-generated in Step 7 (FR-007).

### Step 7: Verify Batch Complete

```bash
# Run batch tests
uv run pytest tests/unit/path/to/batch/files.py -v

# Verify no xfails
uv run pytest tests/unit/path/to/batch/files.py -v 2>&1 | grep XFAIL
# Should show nothing

# REQUIRED: Regenerate coverage matrix (per-batch frequency)
uv run python utils/audit_tests.py --output docs/coverage-matrix.md

# CRITICAL: Run FULL test suite (including integration/functional)
# Tests must pass in parallel (pytest-xdist automatically applied)
uv run pytest
```

### Step 8: Mark Complete

Update task tracking before moving to next batch. This ensures clear progress visibility.

## Batch Tracking

Update tasks.md after each batch:

```markdown
### Batch A1: ASG s7_1_3_ssvns
- [x] Research SSVN spec (§7.1.3)
- [x] Find examples in MUMPS reference
- [x] Evaluate ASG quality for codegen
- [x] Check for existing tests
- [x] Implement 8 tests
- [x] All tests passing
- [x] Full test suite passing
- [x] Coverage matrix updated
```

## Error Handling

### Parser Bug Discovered

1. Document in test with TODO comment
2. Create minimal reproduction case
3. Fix parser before completing test
4. **Update documentation** if parser behavior changes (FR-016): `docs/grammar_overview.md`, `docs/limitations.md`
5. Commit parser fix first, then test
6. Run full suite if fix touches shared code

### ASG Analysis Gap

1. Document what ASG field/analysis is missing
2. Implement in semantic_analyzer.py
3. Add any needed ASG fields to statements.py or expressions.py
4. **Update documentation** (FR-016): `docs/asg/` for new fields, `docs/analysis/` for analyzer changes
5. Re-run tests

### Spec Ambiguity

1. Check MUMPS reference examples/notes as authoritative reference
2. Check YDBTest implementation behavior
3. Document interpretation in test docstring
4. Proceed with MUMPS reference-aligned behavior

### Implementation Fix Causes Regression (Previously-Passing Test Fails)

**This requires the highest verification standards before proceeding.**

1. **STOP** - Do not immediately change the old test
2. **Verify new behavior is correct**:
   - Re-read MUMPS reference for the affected construct
   - Find concrete examples in MUMPS reference or YDBTest
   - Confirm the new ASG structure is semantically correct
3. **Verify new behavior improves codegen quality**:
   - Does the new ASG contain MORE useful information?
   - Is the structure EASIER to generate Python from?
   - Document WHY the change is an improvement
4. **Only if 100% confident**: Update the regressing test to expect improved behavior
5. **If uncertain**: Revert the change and document the conflict for later investigation
6. **Document the decision** in commit message and/or test docstring
