# Research: Complete Stub Tests

**Feature**: 003-complete-stub-tests  
**Date**: January 4, 2026  
**Status**: Complete

## Overview

This research analyzed 687 xfail stub tests to determine optimal batching strategy, prioritization by code coverage impact, and implementation complexity.

## Current State Analysis

### Test Distribution Summary

| Category | Xfail Stubs | % of Total |
|----------|-------------|------------|
| Parser tests | 285 | 41.5% |
| ASG tests | 269 | 39.2% |
| Cross-cutting tests | 133 | 19.4% |
| **Total** | **687** | **100%** |

### Top Files by Stub Count

| File | Stubs | Complexity | Notes |
|------|-------|------------|-------|
| test_s7_1_6_5_library_functions_math.py (parser) | 57 | Low | Routine extrinsic function calls |
| test_s7_1_6_5_library_functions_math.py (asg) | 57 | Low | Same - all follow identical pattern |
| test_language_semantics.py | 35 | High | Cross-cutting $TEST, scoping, transactions |
| test_timeouts.py | 27 | Medium | Timeout parameters across commands |
| test_indirection.py | 26 | High | Complex @ dereferencing semantics |
| test_s7_1_5_intrinsic_functions.py (parser) | 24 | Low | Built-in function parsing |
| test_naked_references.py | 24 | High | Global reference tracking state |
| test_postconditions.py | 21 | Medium | Conditional execution gates |
| test_s7_1_5_intrinsic_functions.py (asg) | 21 | Medium | Function ASG representation |
| test_s7_2_operators.py (asg) | 20 | Medium | Operator semantics |

### Code Coverage Gaps

Current overall coverage: **77%** (3808 stmts, 688 missed)

| Module | Coverage | Missing Lines | Priority |
|--------|----------|---------------|----------|
| semantic_analyzer.py | 63% | 418 lines | **HIGH** - most gaps |
| textx_classes.py | 74% | 63 lines | HIGH |
| variables.py | 89% | 31 lines | Medium |
| parser.py | 87% | 33 lines | Medium |
| dead_code_analysis.py | 5% | 36 lines | Low - not in scope |

## Prioritization Strategy

### Coverage-First Approach

Tests are prioritized by their potential to increase code coverage (regression protection):

1. **Priority 1 - High Coverage Impact**: Tests that exercise semantic_analyzer.py uncovered paths
2. **Priority 2 - Medium Coverage Impact**: Tests for textx_classes.py, parser.py, variables.py
3. **Priority 3 - Low Coverage Impact**: Already-covered functionality needing test assertions

### Complexity Classification

| Complexity | Characteristics | Recommended Batch Size |
|------------|-----------------|----------------------|
| **Low** | Routine parsing, straightforward ASG assertions, well-documented spec | 10-15 |
| **Medium** | Multiple code paths, some semantic analysis, spec interpretation needed | 6-10 |
| **High** | Cross-cutting concerns, state tracking, indirection, complex control flow | 3-5 |

## Batch Plan

### Phase A: High Coverage Impact (Priority 1)

**Focus**: Maximize regression protection by testing currently-uncovered code paths in semantic_analyzer.py

| Batch | Tests | Count | Complexity | Rationale |
|-------|-------|-------|------------|-----------|
| A1 | ASG s7_1_3_ssvns | 8 | Medium | SSVN analysis paths uncovered |
| A2 | ASG s7_1_7_special_variables | 10 | Medium | Special var analysis uncovered |
| A3 | ASG s8_commands general rules | 5 | Medium | Command analysis base paths |
| A4 | ASG s7_2_operators | 10 | Medium | Operator analysis paths |
| A5 | ASG s6_2_routine_body | 7 | High | Body structure analysis |
| A6 | ASG s6_3_1_transaction | 3 | High | TSTART/TCOMMIT analysis |
| A7 | ASG s6_3_2_error_processing | 3 | High | Error trap analysis |

### Phase B: Parser Completion (Priority 2)

**Focus**: Complete parser test coverage - these are largely routine

| Batch | Tests | Count | Complexity | Rationale |
|-------|-------|-------|------------|-----------|
| B1 | Parser s7_1_6_5 library_math (trig) | 12 | Low | SIN/COS/TAN functions |
| B2 | Parser s7_1_6_5 library_math (hyp) | 12 | Low | SINH/COSH hyperbolic |
| B3 | Parser s7_1_6_5 library_math (inv) | 12 | Low | ASIN/ACOS inverse |
| B4 | Parser s7_1_6_5 library_math (misc) | 12 | Low | LOG/EXP/SQRT etc |
| B5 | Parser s7_1_6_5 library_math (other) | 9 | Low | Remaining math funcs |
| B6 | Parser s7_1_5_intrinsic_functions | 12 | Low | Built-in $FUNC parsing |
| B7 | Parser s7_1_5_intrinsic_functions | 12 | Low | Remaining intrinsics |
| B8 | Parser s7_1_7_special_variables | 10 | Low | $VARIABLE parsing |
| B9 | Parser s7_1_7_special_variables | 7 | Low | Remaining specials |
| B10 | Parser s8_z_commands | 13 | Low | Z-command syntax |
| B11 | Parser s8_1_general_rules | 10 | Medium | Command structure |
| B12 | Parser legacy pre1995_syntax | 10 | Medium | Deprecated syntax |
| B13 | Parser legacy pre1995_syntax | 7 | Medium | Remaining legacy |
| B14 | Parser s7_expressions misc | 15 | Low | Pattern match, operators, ssvns |
| B15 | Parser s6_routine misc | 10 | Medium | Routine structure |
| B16 | Parser s8_commands misc | 15 | Low | Various commands |
| B17 | Parser s9_charset | 10 | Low | Character set tests |

### Phase C: ASG Medium Complexity (Priority 2)

| Batch | Tests | Count | Complexity | Rationale |
|-------|-------|-------|------------|-----------|
| C1 | ASG s7_1_5_intrinsic_functions | 10 | Medium | Function semantics |
| C2 | ASG s7_1_5_intrinsic_functions | 11 | Medium | Remaining intrinsics |
| C3 | ASG s7_1_6_5 library_math | 15 | Low | Math lib ASG - routine |
| C4 | ASG s7_1_6_5 library_math | 15 | Low | Math lib ASG continued |
| C5 | ASG s7_1_6_5 library_math | 15 | Low | Math lib ASG continued |
| C6 | ASG s7_1_6_5 library_math | 12 | Low | Math lib ASG final |
| C7 | ASG s7_expressions misc | 15 | Medium | Literals, variables, strings |
| C8 | ASG s8_commands misc | 15 | Medium | Command ASG representations |
| C9 | ASG extensions (YDB) | 15 | Medium | Z-command semantics |
| C10 | ASG legacy pre1995 | 5 | Medium | Deprecated semantics |

### Phase D: High Complexity Cross-Cutting (Priority 3)

| Batch | Tests | Count | Complexity | Rationale |
|-------|-------|-------|------------|-----------|
| D1 | cross_cutting/indirection (name) | 4 | High | @ name dereferencing |
| D2 | cross_cutting/indirection (arg) | 4 | High | @ argument indirection |
| D3 | cross_cutting/indirection (pattern) | 4 | High | @ pattern indirection |
| D4 | cross_cutting/indirection (semantics) | 7 | High | Runtime resolution |
| D5 | cross_cutting/indirection (nesting) | 7 | High | Nested @ handling |
| D6 | cross_cutting/naked_references | 8 | High | ^ state tracking |
| D7 | cross_cutting/naked_references | 8 | High | Naked in expressions |
| D8 | cross_cutting/naked_references | 8 | High | Naked edge cases |
| D9 | cross_cutting/postconditions | 7 | Medium | : conditional gates |
| D10 | cross_cutting/postconditions | 7 | Medium | Argument postconds |
| D11 | cross_cutting/postconditions | 7 | Medium | ASG/codegen postconds |
| D12 | cross_cutting/timeouts | 9 | Medium | Timeout parameters |
| D13 | cross_cutting/timeouts | 9 | Medium | Timeout ASG |
| D14 | cross_cutting/timeouts | 9 | Medium | Timeout codegen |
| D15 | cross_cutting/language_semantics | 7 | High | $TEST tracking |
| D16 | cross_cutting/language_semantics | 7 | High | Evaluation order |
| D17 | cross_cutting/language_semantics | 7 | High | NEW scoping |
| D18 | cross_cutting/language_semantics | 7 | High | Transactions |
| D19 | cross_cutting/language_semantics | 7 | High | Misc semantics |

## Implementation Notes

### Test Implementation Process (FR-010)

Each batch follows the MUMPS-spec-driven validation process. The goal is ensuring ASG quality for Python code generation.

For each batch:

1. **Research**: Read MUMPS spec section CAREFULLY - understand what semantic information codegen needs
2. **Find Examples**: Search MUMPS reference (`mumps-reference/examples__*.md`, `mumps-reference/notes__*.md`) → YDBTest → VistA for real-world examples to validate spec understanding
3. **Evaluate ASG Quality**: Use `validate_asg.py` then READ the output with developer judgment. Assess if current ASG meets codegen requirements. Gaps identified become test assertions.
4. **Check Existing Tests**: Search for existing test content to consolidate rather than duplicate
5. **Implement**: Write/refine test assertions:
   - **Parser tests**: Assert on textX model object structure (node types, attributes, child nodes)
   - **ASG tests**: Assert CORRECT ASG structure (per step 3 analysis)
6. **Fix Gaps**: Address implementation gaps in `src/m2py/`. Commit fixes BEFORE test changes.
7. **Verify**: Run batch tests; run FULL suite (`uv run pytest`) at batch completion (parallel via pytest-xdist)
8. **Update**: Mark tasks complete, regenerate coverage matrix (required per-batch)

### Handling Implementation Changes

When fixes cause regressions in existing tests:
- **Apply highest verification standards** before changing any existing test
- Re-read MUMPS reference, find concrete examples
- Confirm new ASG is semantically correct AND improves codegen quality
- Only update old test if 100% confident; otherwise revert

### Key Resources

- **MUMPS Spec**: `mumps-reference/` (local mirror)
- **YDB Tests**: `YDBTest/` (functional validation)
- **ASG Validator**: `utils/validate_asg.py`
- **Coverage Audit**: `utils/audit_tests.py`

### Estimated Effort

- **Phase A** (7 batches): ~49 stubs - High effort, high coverage value
- **Phase B** (17 batches): ~172 stubs - Medium effort, routine patterns
- **Phase C** (10 batches): ~128 stubs - Medium effort, ASG assertions
- **Phase D** (19 batches): ~133 stubs - High effort, complex semantics

**Total**: 53 batches covering 687 stubs

## Decisions Made

1. **Coverage-first strategy** selected over section-by-section to maximize regression protection
2. **Batch sizes 3-15** based on complexity classification
3. **Codegen tests excluded** - out of scope for spec 003
4. **Math library functions** grouped in large batches (12-15) due to identical patterns
5. **Indirection tests** split into small batches (4-7) due to high complexity
6. **Cross-cutting tests** saved for Phase D as they often reveal implementation gaps

## Alternatives Considered

1. **Section-by-section**: Would complete one spec section fully before moving on - rejected because it doesn't prioritize coverage gaps
2. **File-by-file**: One batch per file - rejected because some files are too large (57 stubs) and others too small (1-2 stubs)
3. **Equal batch sizes**: Fixed 10 stubs per batch - rejected because complexity varies significantly
