# Implementation Plan: Functional Test Suite

**Branch**: `016-functional-test-suite` | **Date**: 2026-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/016-functional-test-suite/spec.md`

## Summary

Build a pytest-based functional test framework that runs MUMPS tests identically to YDBTest/YottaDB CI, comparing transpiled output byte-for-byte against outref reference content. The framework will:

1. Execute MUMPS routines via m2py transpilation (`generate_python()` → `MUMPSRuntime.execute()`)
2. Compare output against normalized outref files (stripping YDB infrastructure markers)
3. Mark known limitations as pytest xfail referencing `limitations.py` IDs
4. Remove obsolete parsing-focused integration tests

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: pytest, textX (existing m2py deps)  
**Storage**: N/A (in-memory global storage via m2py runtime)  
**Testing**: pytest with custom fixtures and parametrization  
**Target Platform**: macOS/Linux development  
**Project Type**: Single project (test infrastructure addition)  
**Performance Goals**: Full test suite < 5 minutes on standard hardware  
**Constraints**: Byte-for-byte output matching with outref after normalization  
**Scale/Scope**: ~1,700 MUMPS test files across 11 test suites

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | Tests validate correct translation by comparing m2py output to YDB reference |
| II. YDB as Reference Implementation | ✅ PASS | outref files ARE YDB output; this feature directly validates against them |
| III. Strict Layer Separation | ✅ PASS | Tests use public API (`generate_python()`, `MUMPSRuntime.execute()`) only |
| IV. Explicit Over Implicit | ✅ PASS | Tests make MUMPS behavior expectations explicit via outref comparison |
| V. Foundational Correctness | ✅ PASS | Test infrastructure enables validating foundational semantics |
| VI. Cross-Cutting Semantics | ✅ PASS | Tests exercise cross-cutting semantics via comprehensive MUMPS test files |
| VII. Minimize Runtime Surface | N/A | Testing infrastructure, not codegen |
| VIII. Research Before Implementation | ✅ PASS | Plan includes research phase for existing infrastructure understanding |

**Gate Result**: ✅ PASS - All applicable principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/016-functional-test-suite/
├── plan.md              # This file
├── research.md          # Phase 0 output (existing infrastructure findings)
├── quickstart.md        # Phase 1 output (usage guide)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
tests/
├── functional/                    # EXISTING - YDBTest structure
│   ├── mugj/
│   │   ├── inref/                 # MUMPS source files (376 files)
│   │   ├── outref/                # Reference output (mugj.txt, etc.)
│   │   └── u_inref/               # Test drivers (mugj.csh)
│   ├── basic/
│   │   ├── inref/                 # 107 files
│   │   └── outref/
│   ├── mvts/                      # 714 files
│   ├── merge/                     # 54 files
│   ├── indirection/               # 9 files
│   ├── m_commands/                # 27 files
│   ├── io/                        # 116 files
│   ├── tp/                        # 109 files
│   ├── triggers/                  # 101 files
│   ├── longname/                  # 34 files
│   └── unicode/                   # 47 files
│
├── functional/
│   ├── conftest.py                # NEW - Functional test fixtures
│   ├── test_mugj.py               # NEW - mugj suite runner
│   ├── test_basic.py              # NEW - basic suite runner
│   └── ...                        # Additional suite runners as needed
│
├── conftest.py                    # EXISTING - Has TEST_SUITES dict
├── helpers/                       # EXISTING - Test utilities
│   └── extraction_helpers.py
│
├── integration/                   # TO BE CLEANED
│   ├── test_ydb_suites.py         # DELETE - Obsolete parsing tests
│   ├── test_mugj.py               # DELETE - Obsolete parsing tests
│   └── ...                        # Keep other integration tests if useful

src/m2py/
├── codegen/__init__.py            # EXISTING - generate_python() API
├── runtime/__init__.py            # EXISTING - MUMPSRuntime.execute() API
└── limitations.py                 # EXISTING - Limitation IDs for xfail
```

**Structure Decision**: Single project structure. Tests live in `tests/functional/` following YDBTest conventions. New test runner files (test_mugj.py, etc.) will be added alongside the existing inref/outref/u_inref directories.

## Complexity Tracking

No constitution violations requiring justification. Implementation uses existing m2py infrastructure.
