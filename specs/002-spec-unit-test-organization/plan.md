# Implementation Plan: MUMPS Spec-Aligned Unit Test Organization

**Branch**: `002-spec-unit-test-organization` | **Date**: 2026-01-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-spec-unit-test-organization/spec.md`

## Summary

Reorganize M2PY's unit tests to systematically map to MUMPS 1995 ANSI spec sections (§5-§9), establishing three-level testing (parser, ASG, codegen) with stub-first coverage using xfail markers. This enables verifiable, gap-free coverage tracking against the standard.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: pytest, textX 4.0+  
**Storage**: N/A (test reorganization only)  
**Testing**: pytest with custom markers (@pytest.mark.parser, @pytest.mark.asg, @pytest.mark.codegen, @pytest.mark.stub); validation against YDBTest functional suites (`tests/functional/*_inref/`, `tests/functional/mugj/`)  
**Target Platform**: Cross-platform (Linux, macOS, Windows)  
**Project Type**: Single project - test suite restructuring  
**Performance Goals**: N/A (structural change, not performance)  
**Constraints**: Must maintain green CI throughout migration (xfail for stubs)  
**Scale/Scope**: ~20 existing test files → ~50+ spec-aligned test files across 3 categories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Semantic Correctness First** | ✅ PASS | Test structure maps directly to MUMPS spec sections, ensuring all semantic behaviors are testable |
| **II. Test-Driven Validation** | ✅ PASS | This IS a testing feature - establishes systematic coverage tracking |
| **III. Multi-Phase Architecture** | ✅ PASS | Three-level testing (parser/ASG/codegen) mirrors multi-phase transpiler architecture |
| **IV. Explicit Over Implicit** | ✅ PASS | Explicit markers and coverage matrix make test status visible |
| **V. Incremental Validation** | ✅ PASS | Stub-first approach with xfail allows incremental implementation while keeping CI green |

**Gate Result**: ✅ PASS - All principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/002-spec-unit-test-organization/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── test-markers.md  # pytest marker contract
│   └── test-naming.md   # test file and function naming conventions
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
tests/
├── unit/
│   ├── parser/                    # FR-003: Parser-level tests
│   │   ├── s6_routine/            # §6 Routine Structure
│   │   │   ├── test_s6_1_routine_head.py
│   │   │   ├── test_s6_2_routine_body.py
│   │   │   └── test_s6_3_execution.py
│   │   ├── s7_expressions/        # §7 Expressions
│   │   │   ├── test_s7_1_1_values.py
│   │   │   ├── test_s7_1_2_variables.py      # §7.1.2 Variable names (lvn, gvn, glvn)
│   │   │   ├── test_s7_1_3_ssvns.py          # §7.1.3 Structured System Variables (^$JOB, ^$ROUTINE, etc.)
│   │   │   ├── test_s7_1_5_intrinsic_functions.py
│   │   │   ├── test_s7_1_6_extrinsic_functions.py
│   │   │   ├── test_s7_1_7_special_variables.py
│   │   │   ├── test_s7_2_operators.py
│   │   │   └── test_s7_3_indirection.py
│   │   ├── s8_commands/           # §8 Commands
│   │   │   ├── test_s8_1_general_rules.py
│   │   │   ├── test_s8_2_01_break.py
│   │   │   ├── test_s8_2_02_close.py
│   │   │   ├── test_s8_2_03_do.py
│   │   │   ├── ... (all 27 commands)
│   │   │   └── test_s8_3_device_params.py
│   │   ├── s9_charset/            # §9 Character Set
│   │   │   └── test_s9_1_definitions.py
│   │   └── extensions/            # FR-023: YottaDB Z-commands
│   │       └── ydb/
│   │           ├── test_zbreak.py
│   │           ├── test_zwrite.py
│   │           └── ...
│   ├── asg/                       # FR-003: ASG-level tests
│   │   ├── s6_routine/
│   │   ├── s7_expressions/
│   │   ├── s8_commands/
│   │   └── extensions/
│   ├── codegen/                   # FR-003: Codegen-level tests
│   │   ├── s6_routine/
│   │   ├── s7_expressions/
│   │   ├── s8_commands/
│   │   └── extensions/
│   ├── cross_cutting/             # FR-003: Cross-cutting features
│   │   ├── test_indirection.py
│   │   ├── test_postconditions.py
│   │   ├── test_timeouts.py
│   │   ├── test_naked_references.py   # FR-046: Naked global reference state tracking
│   │   └── test_language_semantics.py  # FR-046-051
│   ├── analysis/                  # FR-003: Unit tests for analysis functions (not spec-aligned)
│   │   ├── test_for_classifier.py     # ForLoopType classification logic
│   │   ├── test_goto_classifier.py    # GotoType classification logic
│   │   └── test_resolver.py           # Reference resolution logic
│   ├── meta/                      # FR-003: Tooling/infrastructure tests (not spec-aligned)
│   │   ├── test_textx_classes.py      # textX metamodel integration
│   │   └── test_parse_result_tracking.py
│   └── conftest.py                # Shared fixtures, marker registration
├── integration/
│   ├── test_mugj.py               # MUGJ integration tests
│   └── test_ydb_suites.py         # All YDBTest suite validation
└── functional/                    # YDBTest functional suites (expected behavior baselines)
    ├── mugj/                      # MUMPS User Group Japan (376 files)
    ├── mvts_inref/                # MUMPS Validation Test Suite (714 files)
    ├── basic_inref/               # Core language tests (107 files)
    ├── merge_inref/               # MERGE command tests (54 files)
    ├── indirection_inref/         # Indirection operator tests (9 files)
    ├── m_commands_inref/          # M command tests incl. Z-commands (27 files)
    ├── io_inref/                  # I/O operation tests (116 files)
    ├── tp_inref/                  # Transaction processing tests (109 files)
    ├── triggers_inref/            # Trigger tests (101 files)
    ├── longname_inref/            # Long variable name tests (34 files)
    └── unicode_inref/             # Unicode handling tests (47 files)

docs/
├── testing.md                     # FR-041-044: Updated testing documentation
└── coverage-matrix.md             # FR-045: Spec section coverage tracking
```

**Structure Decision**: Single project with reorganized `tests/unit/` into spec-aligned subdirectories. Three top-level categories (parser/, asg/, codegen/) with parallel MUMPS spec section subdirectories. Cross-cutting concerns in dedicated directory.

## Complexity Tracking

No constitution violations requiring justification.

---

## Phase Completion Status

| Phase | Status | Artifacts |
|-------|--------|-----------|
| Phase 0: Research | ✅ Complete | [research.md](research.md) |
| Phase 1: Design | ✅ Complete | [data-model.md](data-model.md), [quickstart.md](quickstart.md), [contracts/](contracts/) |
| Phase 2: Tasks | ✅ Complete | [tasks.md](tasks.md) |

### Post-Design Constitution Re-Check

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Semantic Correctness** | ✅ PASS | Data model maps entities to spec sections 1:1 |
| **II. Test-Driven** | ✅ PASS | Test marker contract enables systematic validation |
| **III. Multi-Phase** | ✅ PASS | Three TestCategory entities mirror transpiler phases |
| **IV. Explicit Over Implicit** | ✅ PASS | Marker contracts make test status explicit |
| **V. Incremental** | ✅ PASS | Quickstart shows stub→implemented workflow |

**Post-Design Gate**: ✅ PASS - Ready for Phase 2 task generation.
