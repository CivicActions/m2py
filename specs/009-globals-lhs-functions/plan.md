# Implementation Plan: LHS Functions & Global Variables

**Branch**: `009-globals-lhs-functions` | **Date**: 2025-01-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-globals-lhs-functions/spec.md`

## Summary

Implement SET assignment targets for LHS $PIECE, LHS $EXTRACT, subscripted local variables, global variables, and naked references. Add $DATA function and KILL command. Introduce GlobalStorageBackend protocol with InMemoryGlobalStorage default implementation.

**Technical Approach**: Extend codegen `_generate_set()` to handle GlobalVariable, NakedGlobal, and IntrinsicFunction targets. Add runtime helpers `m_set_piece()`, `m_set_extract()`, `m_data()`. Implement GlobalStorageBackend protocol with in-memory storage.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parsing), pytest (testing)  
**Storage**: InMemoryGlobalStorage (default), YottaDB/IRIS backends (future)  
**Testing**: pytest with YDB docker validation  
**Target Platform**: Cross-platform (Python)  
**Project Type**: Single project (transpiler library)  
**Performance Goals**: N/A for this spec (correctness focus)  
**Constraints**: Generated code must match YDB output exactly  
**Scale/Scope**: 8 user stories, 32 requirements, extends existing codegen

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Semantic Correctness First** | ✅ PASS | All acceptance criteria validated against YDB output |
| **II. YDB as Reference** | ✅ PASS | Used validate.py with YDB docker to capture expected outputs |
| **III. Strict Layer Separation** | ✅ PASS | Parser unchanged, only codegen + runtime changes |
| **IV. Explicit Over Implicit** | ✅ PASS | Runtime helpers make LHS function semantics explicit |
| **V. Foundational Correctness** | ✅ PASS | Builds on MArray (already implemented) and _scope dict (spec 008) |
| **VI. Cross-Cutting Semantics** | ✅ PASS | Array model with value+children already in MArray |
| **VII. Minimize Runtime Surface** | ✅ PASS | Only dynamic cases (globals, LHS functions) use runtime |
| **VIII. Research Before Implementation** | ✅ PASS | Documented in research.md |

## Project Structure

### Documentation (this feature)

```text
specs/009-globals-lhs-functions/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output (complete)
├── data-model.md        # Phase 1 output (complete)
├── quickstart.md        # Phase 1 output (complete)
├── contracts/           # Phase 1 output (complete)
│   ├── global_storage_backend.md
│   └── runtime_helpers.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (files to modify/create)

```text
src/m2py/
├── runtime/
│   ├── __init__.py      # MArray extensions (data() method)
│   ├── globals.py       # NEW: GlobalStorageBackend, InMemoryGlobalStorage
│   └── helpers.py       # NEW: m_set_piece, m_set_extract, m_data
└── codegen/
    ├── statements.py    # MODIFY: _generate_set() for new targets, add _generate_kill()
    └── expressions.py   # MODIFY: generate_expr() for $DATA

tests/
├── test_spec_009_lhs_piece.py       # LHS $PIECE tests
├── test_spec_009_lhs_extract.py     # LHS $EXTRACT tests
├── test_spec_009_subscripted.py     # Subscripted locals tests
├── test_spec_009_globals.py         # Global variable tests
├── test_spec_009_naked.py           # Naked reference tests
├── test_spec_009_data.py            # $DATA tests
└── test_spec_009_kill.py            # KILL command tests
```

**Structure Decision**: Single project structure - m2py is a transpiler library with codegen and runtime modules.

## Complexity Tracking

> No Constitution Check violations requiring justification. All principles pass.

## Implementation Summary

### Parser Changes
**None required.** Parser already captures:
- `IntrinsicFunction` for LHS $PIECE/$EXTRACT
- `GlobalVariable` for `^NAME(subscripts)`
- `NakedGlobal` for `^(subscripts)`
- `LocalVariable` with subscripts for `X(1,2)`

### Runtime Additions (new files)

1. **`src/m2py/runtime/globals.py`**
   - `GlobalStorageBackend` protocol
   - `InMemoryGlobalStorage` class with naked indicator tracking

2. **`src/m2py/runtime/helpers.py`**
   - `m_set_piece()` - LHS $PIECE implementation
   - `m_set_extract()` - LHS $EXTRACT implementation
   - `m_data()` - $DATA function for locals
   - `m_data_global()` - $DATA function for globals

### Codegen Changes (modifications)

1. **`src/m2py/codegen/statements.py`**
   - Extend `_generate_set()` to handle:
     - `GlobalVariable` targets → `_rt.globals.set()`
     - `NakedGlobal` targets → `_rt.globals.set_naked()`
     - `IntrinsicFunction` targets ($PIECE, $EXTRACT) → `m_set_piece()`, `m_set_extract()`
     - Subscripted `LocalVariable` → MArray auto-vivification
   - Add `_generate_kill()` handler for MKillStatement

2. **`src/m2py/codegen/expressions.py`**
   - Handle `IntrinsicFunction` for $DATA → `m_data()` or `m_data_global()`

### MArray Extensions

Add `data()` method to return $DATA code (0, 1, 10, 11).

## YDB Reference Outputs

| MUMPS | YDB Output |
|-------|------------|
| `S X="A^B^C" S $P(X,"^",2)="NEW" W X,!` | `A^NEW^C` |
| `S X="HELLO" S $E(X,2,3)="XX" W X,!` | `HXXLO` |
| `S X(1)=1 W X(1),!` | `1` |
| `S ^G("a")=1 W ^G("a"),!` | `1` |
| `S ^G(1)=1,^(2)=2 W ^(2),!` | `2` |
| `S X(1)=1,X(1,2)=3 W $D(X),"-",$D(X(1)),"-",$D(X(1,2)),!` | `10-11-1` |
| `S X=1,X(1)=2 K X(1) W $D(X),"-",$D(X(1)),!` | `1-0` |

## Next Steps

Run `/speckit.tasks` to generate detailed task breakdown in `tasks.md`.
