# Implementation Plan: Transpilation Coverage Completion

**Branch**: `015-transpilation-coverage-completion` | **Date**: 2026-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/015-transpilation-coverage-completion/spec.md`

## Summary

Achieve 100% transpilation readiness metric (85% raw coverage) by systematically addressing parser/asg/analysis coverage gaps through pragma exclusions for debugging code and targeted codegen tests for untested MUMPS patterns.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parser), pytest (testing), coverage.py  
**Storage**: N/A  
**Testing**: `uv run python utils/coverage_check.py transpile`  
**Target Platform**: Linux/macOS CLI  
**Project Type**: Single project  
**Performance Goals**: N/A (one-time refactoring)  
**Constraints**: Must maintain at least 85% overall test coverage  
**Scale/Scope**: ~150 lines to modify (pragmas) + ~50 lines new tests + ~20 lines codegen optimization

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | PASS | No behavioral changes |
| II. YDB as Reference Implementation | PASS | New tests will validate against YDB |
| III. Strict Layer Separation | PASS | No layer boundary changes |
| IV. Explicit Over Implicit | PASS | N/A |
| V. Foundational Correctness | PASS | Cleaning up tech debt, not adding features |
| VI. Cross-Cutting Semantics | PASS | N/A |
| VII. Minimize Runtime Surface | PASS | N/A |
| VIII. Research Before Implementation | PASS | Research phase completed |

## Project Structure

### Documentation (this feature)

```text
specs/015-transpilation-coverage-completion/
├── plan.md              # This file
├── research.md          # Research findings with categorizations
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code Changes

```text
src/m2py/
├── parser/
│   ├── exceptions.py      # Add pragma exclusions
│   ├── parser.py          # Add pragma exclusions OR remove classify_for_patterns
│   ├── line_parser.py     # Add pragma exclusions
│   └── textx_classes.py   # Add pragma exclusions to __repr__
├── asg/
│   └── elements.py        # Add pragma exclusions to to_dict()
└── analysis/
    ├── variables.py       # Add pragma exclusions to RoutineAnalysisCache
    └── resolver.py        # Add pragma exclusions to unused utilities

tests/unit/codegen/
└── test_coverage_gaps.py  # New file with targeted tests for Category A gaps
```

**Structure Decision**: Single project - modifications to existing files only

## Implementation Phases

### Phase 1: Category C - Pragma Exclusions (~100 lines)

Add `# pragma: no cover` to code with debugging/intrinsic value that codegen will never call:

1. **parser/exceptions.py**
   - Lines 32-55: MUMPSSyntaxError.__init__ formatting
   - Lines 85-90: MUMPSUnknownCommandError.__init__
   - Rationale: Error formatting only runs during parse failures, not normal codegen

2. **asg/elements.py**
   - Lines 84-117: to_dict() method
   - Lines 123-150: _serialize_value() helper
   - Rationale: Debugging/inspection utility, not used by codegen

3. **parser/textx_classes.py**
   - All __repr__ methods (~15 occurrences)
   - Rationale: Debugging only

4. **analysis/variables.py**
   - Lines 174-339: RoutineAnalysisCache class
   - Rationale: IDE-like incremental caching, not batch codegen

5. **parser/parser.py**
   - Lines 569-609, 848-933: classify_for_patterns() and related
   - Rationale: Test-only API, not part of transpilation pipeline
   - Alternative: Remove entirely if no external usage found

6. **parser/line_parser.py**
   - Lines 168-182: detect_quit_after_for()
   - Lines 197-212: extract_for_commands()  
   - Lines 216-260: classify_for_command()
   - Rationale: Only used by tests, not codegen

7. **analysis/resolver.py**
   - Lines 184-187: get_all_labels()
   - Lines 209-214: get_all_routines()
   - Rationale: Utility functions exported but unused by codegen

### Phase 2: Category A - Codegen Tests (~50 lines)

Create targeted MUMPS tests in tests/unit/codegen/test_coverage_gaps.py:

1. **Indirect GOTO/DO patterns** (semantic_analyzer.py coverage)
   - TEST S X="LABEL" G @X
   - TEST2 S Y="^ROUTINE" D @Y

2. **FOR loops with READ/KILL** (for_analysis.py coverage)
   - TEST F I=1:1:10 R X K I Q

3. **External routine calls** (resolver.py coverage)
   - TEST D ^EXTERNAL
   - TEST2 G ^ROUTINE

4. **MULTI_LOOP_EXIT patterns** (goto_analysis.py coverage)
   - TEST F I=1:1:10 F J=1:1:5 G:J>3 END
   - END Q

### Phase 3: Category B - Codegen Optimization

Update codegen to use pre-compiled patterns from analysis instead of re-compiling at runtime:

1. **pattern_compiler.py optimization**
   - Currently: `compiled_pattern` stored at analysis time but codegen ignores it
   - Currently: Runtime helper re-imports and re-compiles pattern
   - Fix: Codegen should use the pre-compiled regex directly
   - Files: `src/m2py/codegen/expressions.py`, `src/m2py/runtime/helpers.py`

### Phase 4: Verification

1. Run `uv run python utils/coverage_check.py transpile`
2. Verify progress reaches 100% (85% raw)
3. Ensure overall test coverage remains at least 85%
4. Run full test suite to verify no regressions

## Complexity Tracking

No constitution violations - straightforward exclusions and test additions.
