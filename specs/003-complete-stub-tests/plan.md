# Implementation Plan: Complete Stub Tests

**Branch**: `003-complete-stub-tests` | **Date**: January 4, 2026 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-complete-stub-tests/spec.md`

## Summary

Complete 687 xfail stub tests across parser and ASG test suites (codegen out of scope). Tests are prioritized by code coverage impact to maximize regression protection, grouped into 53 batches of 3-15 tests based on complexity. Implementation follows a MUMPS-spec-driven validation process with emphasis on ASG quality for Python code generation.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: pytest, textX, pytest-cov, pytest-xdist  
**Storage**: N/A (test files only)  
**Testing**: pytest with coverage reports  
**Target Platform**: Local development / CI  
**Project Type**: Single project  
**Performance Goals**: Tests complete in <60s, 95%+ code coverage  
**Constraints**: No codegen tests (out of scope per clarification)  
**Scale/Scope**: 687 xfail stubs → 0 xfails across 53 batches

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | Tests validate MUMPS semantics against ANSI spec |
| II. Test-Driven Validation | ✅ PASS | Core purpose: complete test coverage |
| III. Multi-Phase Architecture | ✅ PASS | Parser and ASG tests are layer-separated |
| IV. Explicit Over Implicit | ✅ PASS | Tests document expected behavior explicitly |
| V. Incremental Validation | ✅ PASS | Batched implementation with verification at each step |

**Gate Status**: PASS - No violations

## Project Structure

### Documentation (this feature)

```text
specs/003-complete-stub-tests/
├── plan.md              # This file
├── spec.md              # Feature specification (with clarifications)
├── research.md          # Batch analysis and prioritization
├── data-model.md        # Entity descriptions
├── quickstart.md        # Implementation guide
├── contracts/
│   ├── test-implementation.md  # Test patterns and standards
│   └── batch-workflow.md       # Per-batch FR-010 workflow
├── tasks.md             # (Created by /speckit.tasks)
└── checklists/
    └── requirements.md  # Spec validation checklist
```

### Source Code (affected paths)

```text
tests/unit/
├── parser/              # 285 xfail stubs to implement
│   ├── s6_routine/
│   ├── s7_expressions/
│   ├── s8_commands/
│   ├── s9_charset/
│   ├── extensions/
│   └── legacy/
├── asg/                 # 269 xfail stubs to implement
│   ├── s6_routine/
│   ├── s7_expressions/
│   ├── s8_commands/
│   ├── s9_charset/
│   ├── extensions/
│   └── legacy/
├── analysis/            # May need fixes discovered during testing
├── cross_cutting/       # 133 xfail stubs to implement
└── meta/                # May need fixes discovered during testing

src/m2py/
├── parser/              # Parser fixes if needed (87% coverage)
├── analysis/            # Semantic analyzer fixes (63% coverage - highest priority gap)
└── asg/                 # ASG element fixes if needed
```

**Structure Decision**: Existing test structure maintained; no new directories needed

## Key Clarifications (from spec.md)

The following decisions were made during specification clarification:

1. **Prioritization**: Coverage-first strategy - prioritize stubs testing currently-untested code paths
2. **Scope**: Codegen tests are OUT OF SCOPE for spec 003
3. **Batch Sizing**: 3-15 stubs per batch based on complexity (smaller for indirection/transactions, larger for routine patterns)
4. **Regression Testing**: Run related test files during batch development; run full suite (`uv run pytest`) at batch completion
5. **Commit Discipline**: Implementation fixes committed before test changes, related fixes batched together
6. **Regression Resolution**: Update old tests only after 100% verification that new behavior is correct AND improves codegen quality
7. **ASG Quality Evaluation**: Developer must READ ASG output and judge if sufficient for codegen; gaps become test assertions
8. **Parser Test Assertions**: Validate textX model object structure (node types, attributes, child nodes)
9. **Test Quality**: Tests must be isolated and deterministic (automatic given unidirectional architecture)
10. **Parallel Execution**: Tests must support pytest-xdist (already configured and applied)
11. **Coverage Matrix Frequency**: Regenerate per-batch (at FR-010 step 8)
12. **Documentation Updates**: When implementation changes address test gaps, update relevant docs (`docs/asg/`, `docs/analysis/`, `docs/codegen/`, `docs/examples/`, plus standalone docs). Auto-generated `docs/coverage-matrix.md` handled by FR-007.

## FR-010: MUMPS-Spec-Driven Validation Process

Each test implementation follows this 8-step process (see [batch-workflow.md](./contracts/batch-workflow.md) for details):

1. **Research**: Read MUMPS reference carefully to understand semantics
2. **Find Examples**: Search MUMPS reference (`mumps-reference/examples__*.md`, `mumps-reference/notes__*.md`) → YDBTest → VistA for real-world examples
3. **Evaluate ASG Quality**: Use `validate_asg.py` to assess if current ASG meets codegen requirements
4. **Check Existing Tests**: Consolidate rather than duplicate
5. **Implement Tests**: Assert CORRECT ASG structure (per step 3 analysis)
6. **Fix Implementation Gaps**: Iterate on code fixes, commit before tests
7. **Verify Complete**: Run batch tests, then full suite at batch end
8. **Mark Complete**: Update task tracking

**Critical**: Tests should assert what the ASG SHOULD contain for quality Python codegen, not just current behavior.

## Implementation Phases

### Phase A: High Coverage Impact (Priority 1)

7 batches, ~49 stubs targeting semantic_analyzer.py coverage gaps

| Batch | File/Section | Count | Complexity |
|-------|-------------|-------|------------|
| A1 | ASG s7_1_3_ssvns | 8 | Medium |
| A2 | ASG s7_1_7_special_variables | 10 | Medium |
| A3 | ASG s8_1_general_rules | 5 | Medium |
| A4 | ASG s7_2_operators | 10 | Medium |
| A5 | ASG s6_2_routine_body | 7 | High |
| A6 | ASG s6_3_1_transaction | 3 | High |
| A7 | ASG s6_3_2_error_processing | 3 | High |

### Phase B: Parser Completion (Priority 2)

17 batches, ~172 stubs - mostly routine parsing tests

See [research.md](./research.md) for detailed batch breakdown (B1-B17).

### Phase C: ASG Medium Complexity (Priority 2)

10 batches, ~128 stubs - ASG semantic assertions

See [research.md](./research.md) for detailed batch breakdown (C1-C10).

### Phase D: High Complexity Cross-Cutting (Priority 3)

19 batches, ~133 stubs - indirection, naked refs, postconditions, timeouts

See [research.md](./research.md) for detailed batch breakdown (D1-D19).

## Handling Implementation Changes

When stub tests reveal implementation gaps:

### Standard Flow
1. Document the gap in test docstring
2. Implement fix in `src/m2py/`
3. Run related tests to verify
4. Commit implementation fix BEFORE test changes
5. Continue with batch

### If Implementation Fix Causes Regression

**Apply highest verification standards before changing any existing test:**

1. STOP - Do not immediately change the old test
2. Re-read MUMPS reference for affected construct
3. Find concrete examples in MUMPS reference (`mumps-reference/examples__*.md`) or YDBTest
4. Confirm new ASG is semantically correct
5. Verify new behavior IMPROVES codegen quality (not just different)
6. Only if 100% confident: Update regressing test
7. If uncertain: Revert and document for later investigation

### High-Risk Changes

For changes to shared code paths (semantic_analyzer.py, textx_classes.py):
- Run full test suite (`uv run pytest`) mid-batch
- Document scope of impact in commit message

## Success Verification

```bash
# Final success command (from spec SC-002)
uv run pytest tests/unit/parser/ tests/unit/asg/ tests/unit/analysis/ tests/unit/meta/ tests/unit/cross_cutting/ -v

# Expected result: ~1876 passed, 93 skipped, 0 xfailed
# (687 stubs converted to passing tests)

# Full suite verification at batch completion
uv run pytest
```

## Complexity Tracking

No constitution violations - no complexity justification needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | - | - |
