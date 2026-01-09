# Implementation Plan: Minimal Control Flow Foundation

**Branch**: `004-codegen-foundation` | **Date**: 2026-01-08 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-codegen-foundation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement the minimal Python code generation foundation for the M2PY transpiler. This includes:
- M value coercion helpers (`m_num()`, `m_truth()`, `m_compare()`) implementing ANSI MUMPS semantics
- Code generators for basic statements (SET, WRITE, QUIT, IF, ELSE, FOR, DO, GOTO)
- Case-preserving, injective name translation for labels and variables
- A minimal runtime context for execution

This is the first codegen spec—all generated Python must match YDB output exactly.

## Technical Context

**Language/Version**: Python 3.10+ (target), textX for parsing  
**Primary Dependencies**: textX (parsing), pytest (testing), uv (package management)  
**Storage**: N/A (in-memory transpilation)  
**Testing**: pytest with `@pytest.mark.codegen` markers, YDB Docker for reference outputs  
**Target Platform**: Any Python 3.10+ environment  
**Project Type**: Single project - Python library with CLI entry point  
**Performance Goals**: N/A for this spec (correctness over performance)  
**Constraints**: Generated code must be valid Python 3.10+ syntax; output must match YDB character-for-character  
**Scale/Scope**: ~24 acceptance test cases, 7 user stories, 21 functional requirements

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Semantic Correctness First** | ✅ PASS | All 24 acceptance scenarios have YDB-verified expected outputs |
| **II. YDB as Reference Implementation** | ✅ PASS | Reference outputs already generated and embedded in spec.md |
| **III. Strict Layer Separation** | ✅ PASS | Codegen consumes ASG only; no parsing in codegen module |
| **IV. Explicit Over Implicit** | ✅ PASS | Coercion helpers (`m_num`, `m_truth`, `m_compare`) make M semantics explicit |
| **V. Foundational Correctness** | ✅ PASS | Value model is day-one requirement; scope bounded to avoid premature complexity |
| **VI. Cross-Cutting Semantics** | ✅ PASS | Helpers handle value model; $TEST deferred to Spec 005 |

**Gate Result**: PASS - no violations require justification.

## Project Structure

### Documentation (this feature)

```text
specs/004-codegen-foundation/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (Python API contracts)
├── checklists/
│   └── requirements.md  # Quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/m2py/
├── codegen/                  # NEW: Code generation module
│   ├── __init__.py           # Public API: generate_python()
│   ├── helpers.py            # M coercion helpers: m_num, m_truth, m_compare
│   ├── names.py              # Name translation: NameTranslator class
│   ├── expressions.py        # Expression codegen
│   ├── statements.py         # Statement codegen (SET, WRITE, etc.)
│   └── routine.py            # Routine → Python module translation
├── runtime/                  # NEW: Runtime support
│   ├── __init__.py
│   └── runtime.py            # MUMPSRuntime class
├── asg/                      # (existing) ASG elements consumed by codegen
├── analysis/                 # (existing) Analysis passes run before codegen
├── parser/                   # (existing) Parser produces ASG
└── grammar/                  # (existing) textX grammar files

tests/unit/codegen/
├── conftest.py               # (existing) Test fixtures
├── s6_routine/               # Routine structure tests
├── s7_expressions/           # Expression codegen tests
│   ├── test_s7_1_1_values.py # Value coercion tests
│   └── test_s7_1_4_literals.py
└── s8_commands/              # Statement codegen tests
    ├── test_s8_2_03_do.py
    ├── test_s8_2_05_for.py
    ├── test_s8_2_06_goto.py
    ├── test_s8_2_09_if.py
    ├── test_s8_2_16_quit.py
    ├── test_s8_2_18_set.py
    └── test_s8_2_25_write.py
```

**Structure Decision**: Single project extending existing M2PY structure. The `codegen/` module is new; all other modules exist. Test structure mirrors spec sections per project conventions.

## Complexity Tracking

> No constitution violations - this section is empty.
