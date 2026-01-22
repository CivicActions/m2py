# Implementation Plan: YDB Test Suite Failure Resolution

**Branch**: `017-ydb-test-failures` | **Date**: 2026-01-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/017-ydb-test-failures/spec.md`

## Summary

Resolve all 147 outstanding YDB test suite failures by:
1. Enhancing TRAMPOLINE strategy to support argumentless KILL/NEW (10 tests)
2. Implementing missing operators (sorts-after `]]`) and expression types (1 test)
3. Extending LHS $PIECE to support globals and indirection (3 tests)
4. Fixing codegen syntax errors (1 test)
5. Configuring xfail for LIM-015 Z-extensions (12 tests)
6. Debugging and fixing behavioral mismatches in arithmetic, patterns, FOR loops, and traversal functions (75 tests)
7. Investigating merge suite infrastructure issues (33 tests)

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parser), pytest (testing)  
**Storage**: N/A (transpiler, no persistence except global variables via runtime)  
**Testing**: pytest with YDB validation via Docker  
**Target Platform**: Linux/macOS (development), any Python 3.10+ runtime  
**Project Type**: Single project (transpiler library)  
**Performance Goals**: N/A (correctness over speed for this spec)  
**Constraints**: Generated Python must be syntactically valid; output must match YDB exactly  
**Scale/Scope**: 147 test failures to resolve across 6 categories

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Semantic Correctness First** | ✅ PASS | Primary goal is matching YDB output exactly |
| **II. YDB as Reference Implementation** | ✅ PASS | All fixes validated against YDB outref |
| **III. Strict Layer Separation** | ✅ PASS | Analysis changes in analysis layer; codegen changes in codegen layer |
| **IV. Explicit Over Implicit** | ✅ PASS | New helpers (m_sorts_after) make MUMPS semantics explicit |
| **V. Foundational Correctness** | ✅ PASS | TRAMPOLINE enhancement addresses structural issue |
| **VI. Cross-Cutting Semantics** | ✅ PASS | Variable scoping, NEW semantics are cross-cutting |
| **VII. Minimize Runtime Surface** | ✅ PASS | Sorts-after uses inline helper; argumentless KILL/NEW uses dict pattern |
| **VIII. Research Before Implementation** | ✅ PASS | Phase 0 research required before implementation |

**Gate Result**: PASS - Proceed to Phase 0 research

## Project Structure

### Documentation (this feature)

```text
specs/017-ydb-test-failures/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (N/A - no new data models)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no API contracts)
├── checklists/
│   └── requirements.md  # Quality checklist (complete)
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/m2py/
├── analysis/            # Semantic analysis passes
│   ├── resolver.py      # Reference resolution
│   ├── variables.py     # Variable analysis (NEW/KILL scope tracking)
│   ├── for_analysis.py  # FOR loop analysis
│   └── pattern_compiler.py  # Pattern matching
├── codegen/             # Python code generation
│   ├── emitter.py       # Main code emitter
│   ├── expressions.py   # Expression codegen
│   ├── statements.py    # Statement codegen (TRAMPOLINE, FOR, etc.)
│   ├── shared_state.py  # RoutineState dataclass for TRAMPOLINE
│   └── helpers.py       # Runtime helpers (m_sorts_after location)
├── asg/                 # Abstract Semantic Graph definitions
│   ├── statements.py    # Statement ASG nodes
│   └── expressions.py   # Expression ASG nodes
├── parser/              # textX grammar and parser
└── runtime/             # Runtime library
    ├── globals.py       # Global variable storage
    └── helpers.py       # Runtime functions

tests/
├── functional/          # YDB validation tests
│   ├── basic/           # Basic test suite
│   ├── mugj/            # MUGJ test suite
│   ├── mvts/            # MVTS test suite
│   └── merge/           # Merge test suite
├── conftest.py          # pytest fixtures
└── suite_definitions.py # Test suite configuration

utils/
├── validate.py          # YDB comparison utility
└── limitations.py       # Known limitation markers
```

**Structure Decision**: Single project structure. All changes target existing layers:
- **Analysis layer**: Variable scope tracking enhancements
- **Codegen layer**: TRAMPOLINE enhancement, expression fixes, operator implementation
- **Tests layer**: xfail configuration, infrastructure debugging

## Complexity Tracking

No constitution violations requiring justification.

---

# Phase 0: Research (COMPLETE)

See [research.md](research.md) for full findings.

## Summary

| Topic | Status | Decision |
|-------|--------|----------|
| R1: TRAMPOLINE Architecture | ✅ Resolved | Add `_locals` dict to RoutineState for dynamic variables |
| R2: Variable Analysis | ✅ Resolved | Add flags for argumentless KILL/NEW presence |
| R3: Sorts-After Operator | ✅ Resolved | Already implemented; debug if failures are collation bugs |
| R4: LHS $PIECE Scope | ✅ Resolved | Add MNakedGlobal handling for `S $P(^(sub),"^",1)=Y` and MIndirection handling for `S $P(@X,"^",1)=Y` |
| R5: LIM-015 Z-Extensions | ✅ Resolved | Configure xfail markers for 12 affected tests |
| R6: Merge Infrastructure | ✅ Resolved | Debug outref loading and normalization |

**NEEDS CLARIFICATION: NONE** - All unknowns resolved.

---

# Phase 1: Design (COMPLETE)

## Data Model Changes

No new data models required. Enhancements to existing ASG nodes:

```python
# In src/m2py/asg/elements.py - MRoutine additions
@dataclass
class MRoutine:
    # ... existing fields ...
    has_argumentless_kill: bool = False  # NEW: triggers _locals dict
    has_argumentless_new: bool = False   # NEW: triggers _locals dict
```

```python
# In src/m2py/codegen/shared_state.py - RoutineState enhancement
@dataclass
class RoutineState:
    # ... existing generated fields ...
    _locals: dict[str, Any] = field(default_factory=dict)  # NEW: dynamic variables
    _new_stack: list[dict] = field(default_factory=list)   # NEW: NEW scope stack
```

## Contracts

N/A - No API contracts for this spec. All changes are internal implementation.

## Generated Artifacts

- [research.md](research.md) - Phase 0 research findings
- [quickstart.md](quickstart.md) - Development workflow guide
- `contracts/` - N/A (no API contracts)
- `data-model.md` - N/A (no new models, just ASG enhancements above)

---

# Re-evaluated Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Semantic Correctness First** | ✅ PASS | All fixes target exact YDB output matching |
| **II. YDB as Reference Implementation** | ✅ PASS | Each fix validated via utils/validate.py |
| **III. Strict Layer Separation** | ✅ PASS | Analysis changes stay in analysis/; codegen stays in codegen/ |
| **IV. Explicit Over Implicit** | ✅ PASS | _locals dict explicitly tracks dynamic variables |
| **V. Foundational Correctness** | ✅ PASS | TRAMPOLINE core pattern preserved |
| **VI. Cross-Cutting Semantics** | ✅ PASS | NEW/KILL scoping handled consistently |
| **VII. Minimize Runtime Surface** | ✅ PASS | No new runtime dependencies |
| **VIII. Research Before Implementation** | ✅ PASS | research.md completed before design |

**Post-Design Gate Result**: PASS - Ready for task breakdown (/speckit.tasks)

---

# Next Steps

This plan is complete. To generate implementation tasks:

```
/speckit.tasks
```

Human review required before starting implementation for:
1. Test infrastructure changes (conftest.py)
2. New limitation entries (limitations.py)
3. Any "impossible to fix" determinations
