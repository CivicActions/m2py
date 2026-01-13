# Implementation Plan: External Calls & Cross-Routine Infrastructure

**Branch**: `008-external-calls` | **Date**: 2025-01-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-external-calls/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement cross-routine coordination and module loading for MUMPS-to-Python transpilation. This enables:
- External DO calls (`D ^ROUTINE`, `D LABEL^ROUTINE`) with return semantics
- External GOTO (`G ^ROUTINE`) with permanent control transfer  
- External extrinsic functions (`$$FUNC^ROUTINE`) with $TEST isolation
- `$TEXT` function for source line retrieval (current and external routines)
- Shared variable scope across routine boundaries
- Module caching to avoid redundant translation

**Technical approach**: Use standard Python `import` statements for module loading (leveraging `sys.modules` caching). Codegen generates direct function calls (`import ext2; ext2.LABEL(_rt, _scope)`). Shared `_scope` dict passed to all functions.

## Technical Context

**Language/Version**: Python 3.10+ (per pyproject.toml)  
**Primary Dependencies**: textX (grammar/parser), standard `import` (module loading)  
**Storage**: `_source_lines` embedded in each generated module, Python's `sys.modules` cache  
**Testing**: pytest with YDB Docker validation (`utils/validate.py`)  
**Target Platform**: Any Python 3.10+ environment  
**Project Type**: Single project (transpiler library)  
**Performance Goals**: Standard Python import caching (negligible overhead)  
**Constraints**: Generated code must be syntactically valid, behavior must match YottaDB  
**Scale/Scope**: Support VistA-scale systems (thousands of routines, millions of LOC)

### Implementation Status (Complete)

| Component | Location | Status |
|-----------|----------|--------|
| `MCall.routine` | [elements.py](../../src/m2py/asg/elements.py#L374) | ✅ Parsed |
| `CallType.ROUTINE_CALL` | [enums.py](../../src/m2py/asg/enums.py#L101) | ✅ Set |
| `get_external_calls()` | [resolver.py](../../src/m2py/analysis/resolver.py#L192) | ✅ Available |
| `MUMPSRuntime` | [runtime/__init__.py](../../src/m2py/runtime/__init__.py) | ✅ Extended |
| External DO | [statements.py](../../src/m2py/codegen/statements.py) | ✅ Implemented |
| External GOTO | [statements.py](../../src/m2py/codegen/statements.py) | ✅ Implemented |
| External extrinsic | [expressions.py](../../src/m2py/codegen/expressions.py) | ✅ Implemented |
| $TEXT function | [expressions.py](../../src/m2py/codegen/expressions.py) | ✅ Implemented |
| GotoExternal exception | [runtime/__init__.py](../../src/m2py/runtime/__init__.py) | ✅ Added |
| run_with_goto_support | [runtime/__init__.py](../../src/m2py/runtime/__init__.py) | ✅ Added |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| 1 | **Semantic Correctness First** | ✅ Pass | All behaviors YDB-validated in spec |
| 2 | **YDB as Reference** | ✅ Pass | 8 user stories with YDB acceptance scenarios; MDC 8.2.6 relaxed per YDB behavior |
| 3 | **Strict Layer Separation** | ✅ Pass | Runtime handles loading; codegen emits calls |
| 4 | **Explicit Over Implicit** | ✅ Pass | Module paths explicit, caching observable |
| 5 | **Foundational Correctness** | ✅ Pass | Builds on Spec 007 line dispatch |
| 6 | **Cross-Cutting Semantics** | ✅ Pass | Shared scope is explicit design goal |
| 7 | **Minimize Runtime Surface** | ✅ Pass | Uses Python stdlib `import`/`sys.modules`; only `get_text()` helper added to runtime |
| 8 | **Research Before Implementation** | ✅ Pass | This plan documents research phase |

**Gate Status**: PASS - All principles satisfied. Minimal runtime surface achieved via stdlib.

**MDC Deviation Note**: Principle 2 justifies intentional deviation from MDC 8.2.6 (GOTO same-routine restriction). VistA contains 11,474 cross-routine GOTOs across 3,177 files; YDB allows these, so we follow YDB behavior.

## Project Structure

### Documentation (this feature)

```text
specs/008-external-calls/
├── plan.md              # This file
├── research.md          # Module loading patterns research
├── data-model.md        # Module cache, shared scope structures
├── quickstart.md        # Getting started with external calls
├── contracts/           # N/A (no API contracts for transpiler)
├── checklists/
│   └── requirements.md  # Requirements validation checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── runtime/
│   └── __init__.py      # Runtime additions:
│                        #   - get_text(offset, label, module) for $TEXT
│                        #   - GotoExternal exception class
│                        #   - LabelNotFoundError exception class
│                        #   - run_with_goto_support() for external GOTO chains
│                        #   (module loading uses standard Python import)
│
├── codegen/
│   ├── routine.py       # Module constants: _source_lines, _routine_name, _label_lines
│   ├── statements.py    # External DO: import + routine.LABEL(_scope=_scope)
│   │                    # External GOTO: raise GotoExternal(module, label, offset)
│   └── expressions.py   # External extrinsic: import + routine.FUNC(_scope=_scope, args)
│                        # $TEXT: _rt.get_text() with module constants
│
└── parser/
    └── (no changes)     # Parser already captures MCall.routine

tests/
├── fixtures/
│   └── external/        # Test routine files (ext1.m, ext2.m, etc.)
├── integration/
│   └── test_external_calls.py  # Cross-routine integration tests
└── conftest.py              # sys.path fixture for external modules
```

**Structure Decision**: Single project with extensions to existing runtime and codegen modules. Test fixtures directory for multi-routine test cases.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Runtime gains `get_text()` | $TEXT needs runtime context (current routine, label resolution) | Pure codegen would bloat every generated file |
| Runtime gains `run_with_goto_support()` | External GOTO chains require loop-based dispatch | Alternative: nested imports - but breaks return semantics |
| GotoExternal exception | Stack unwinding for external GOTO semantics | Alternative: return codes - but breaks MUMPS semantics |

**Simplifications achieved**: Standard Python `import`/`sys.modules` replaces custom module loading. No `call_routine()`, `goto_routine()`, or module cache code needed. The `_scope` dictionary provides cross-routine variable visibility with minimal overhead.

## Dependencies Summary

### Consumes (from earlier specs)
- **Spec 005**: $TEST save/restore for extrinsics (`_call_extrinsic` pattern)
- **Spec 006**: Trampoline pattern for cross-label control flow
- **Spec 007**: Line dispatch (`_line_map`) for offset-based entry, `MRoutine.source_lines`

### Produces (for later specs)
- Module loading infrastructure (used by all subsequent specs)
- Shared scope pattern (foundation for globals in Spec 009)
- $TEXT implementation (complete)
