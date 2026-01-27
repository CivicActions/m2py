# Implementation Plan: YDB Test Suite Failure Resolution

**Branch**: `017-ydb-test-failures` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-ydb-test-failures/spec.md`

## Summary

Resolve all outstanding YDB test suite failures through targeted bug fixes, codegen enhancements, and proper limitation marking. Primary focus on MUGJ test failures including subscript indirection context bugs, argument indirection command lists, and multi-target GOTO limitations.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parser), pytest (testing), uv (package management)  
**Storage**: In-memory globals (MArray), filesystem for test routines  
**Testing**: pytest with YDB Docker validation (`docker run ydb`)  
**Target Platform**: macOS/Linux development, transpiled MUMPS→Python  
**Project Type**: Single project (transpiler)
**Performance Goals**: Test suite execution <60s, transpilation <1s per routine  
**Constraints**: Must match YDB output exactly, no runtime behavior differences  
**Scale/Scope**: 188 MUGJ routines, 72 drivers, ~500 test cases

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | All fixes target YDB compatibility |
| II. YDB as Reference Implementation | ✅ PASS | Test validation uses YDB Docker |
| III. Strict Layer Separation | ✅ PASS | Fixes in correct layers (codegen/runtime) |
| IV. Explicit Over Implicit | ✅ PASS | Indirection contexts made explicit |
| V. Foundational Correctness | ✅ PASS | Fixes core indirection behavior |
| VI. Cross-Cutting Semantics | ✅ PASS | Subscript handling affects all commands |
| VII. Minimize Runtime Surface | ⚠️ WATCH | New runtime function for subscript indirection |
| VIII. Research Before Implementation | ✅ PASS | R8 documents complete analysis |

## Project Structure

### Documentation (this feature)

```text
specs/017-ydb-test-failures/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output with R1-R8 findings
├── tasks.md             # Implementation tasks (Phases 1-16)
└── learnings.md         # Accumulated learnings
```

### Source Code (repository root)

```text
src/m2py/
├── core/                # Shared components (Spec 018)
│   ├── indirection.py   # IndirectionResolver with subscript support
│   ├── names.py         # NameTranslator
│   ├── scope.py         # CurrentScope
│   └── subscripts.py    # SubscriptCanonicalizer
├── codegen/
│   ├── expressions.py   # Expression generation with subscript context
│   ├── statements.py    # Command codegen (KILL, FOR, GOTO)
│   └── indirection.py   # Indirection codegen helpers
├── runtime/
│   ├── __init__.py      # Runtime with get_indirected, kill_indirected
│   └── helpers.py       # m_str, m_num, m_format_output
└── analysis/
    └── for_analysis.py  # FOR loop analysis

tests/
├── functional/
│   ├── test_mugj.py     # MUGJ serial execution
│   ├── test_mvts.py     # MVTS tests
│   ├── test_basic.py    # Basic tests
│   └── conftest.py      # ROUTINE_LIMITATIONS, ROUTINE_HELPERS
└── unit/
    └── codegen/         # Unit tests for codegen fixes
```

**Structure Decision**: Single project structure with `src/m2py/core/` module for shared codegen/runtime components established by Spec 018.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| New `resolve_subscript_indirection` runtime function | Subscript context requires VALUE resolution instead of NAME validation | Inline in codegen would duplicate logic across all subscript sites |
| `subscript_context` parameter threading | Indirection context must flow from subscript generation through to codegen | Global state would break concurrent execution |
