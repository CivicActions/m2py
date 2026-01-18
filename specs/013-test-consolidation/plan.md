# Implementation Plan: Test Suite Consolidation & VistA Compatibility

**Branch**: `013-test-consolidation` | **Date**: 2026-01-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/013-test-consolidation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Resolve all 286 xfail test stubs through deletion (~44 redundant), conversion (~39 to execute_mumps), and implementation (~200 remaining features). Achieve zero xfail tests with complete VistA compatibility across 45 functional requirements. Key implementations include: fall-through semantics, $ASCII/$CHAR, transactions (via database abstraction), READ/USE/LOCK/JOB, $TEXT, Z-commands with VistA usage, timeouts, and math functions.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parser), pytest (testing), yottadb (YDB backend via YDBPython)  
**Storage**: Database abstraction layer with Memory (testing), YottaDB (production), IRIS (future) backends  
**Testing**: pytest with `execute_mumps` fixture validating against YottaDB reference output  
**Target Platform**: Linux/macOS (Docker for YDB validation)  
**Project Type**: Single (transpiler with src/m2py, tests/, utils/)  
**Performance Goals**: Test suite execution time increase <20% (SC-006)  
**Constraints**: Zero xfail tests (SC-001), VistA compatibility (33,951 routines)  
**Scale/Scope**: 286 test stubs to resolve, 45 FRs, 20 SCs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | All implementations validated against YDB reference output via validate.py |
| II. YDB as Reference Implementation | ✅ PASS | Test conversions use `execute_mumps` fixture comparing to YDB output |
| III. Strict Layer Separation | ✅ PASS | New features follow Parse → Analyze → Generate pattern. No codegen workarounds. |
| IV. Explicit Over Implicit | ✅ PASS | MUMPS implicit behaviors (fall-through, NEW, etc.) made explicit in generated code |
| V. Foundational Correctness | ✅ PASS | Builds on completed Specs 004-012 (GOTO, offsets, external calls). DB abstraction layer. |
| VI. Cross-Cutting Semantics | ✅ PASS | Shared helpers for value coercion, $TEST, scoping. DB abstraction for LOCK/transactions. |
| VII. Minimize Runtime Surface | ✅ PASS | Only globals, SVs, XECUTE use runtime. Local vars, FOR, params emit inline Python. |
| VIII. Research Before Implementation | ✅ PASS | Phase 0 research required before implementation. Review ASG/docs first. |

**Gate Status**: ✅ All principles satisfied. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/013-test-consolidation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/m2py/
├── analysis/              # Semantic analysis passes
│   ├── semantic_analyzer.py
│   ├── resolver.py
│   └── variables.py       # NEW/LOCK/scope handling
├── codegen/               # Python code generation
│   └── ...                # Fall-through, Z-commands, etc.
├── parser/                # textX grammar and parsing
│   └── ...
├── asg/                   # ASG node definitions
│   ├── statements.py      # LOCK, JOB, OPEN, BREAK, VIEW, etc.
│   ├── expressions.py     # $TEXT, $ASCII, $CHAR, $NEXT, etc.
│   └── ...
└── runtime/               # Runtime helpers
    ├── __init__.py        # m_num, m_truth, m_compare
    └── db/                # Database abstraction layer
        ├── __init__.py    # Backend interface
        ├── memory.py      # MemoryBackend (testing)
        ├── yottadb.py     # YottaDBBackend (production)
        └── iris.py        # IRISBackend (future stub)

tests/
├── test_spec_*.py         # Spec-aligned tests (DELETE targets live here)
├── test_gaps_*.py         # Gaps tests (CONVERT/IMPLEMENT stubs)
└── conftest.py            # execute_mumps, execute_expr fixtures

utils/
├── validate.py            # YDB comparison tool
└── ...
```

**Structure Decision**: Single project with existing `src/m2py/` structure. Database abstraction layer in `src/m2py/runtime/db/` for LOCK, transactions, SSVNs.

## Complexity Tracking

> **No violations requiring justification.** Constitution Check passed all principles.

---

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Design Validation |
|-----------|--------|-------------------|
| I. Semantic Correctness | ✅ PASS | Contracts specify exact MUMPS behavior; all validated against YDB |
| II. YDB Reference | ✅ PASS | All contracts reference YDB output; validate.py used throughout |
| III. Layer Separation | ✅ PASS | DB abstraction protocol extends existing GlobalStorageBackend cleanly |
| IV. Explicit Over Implicit | ✅ PASS | Fall-through generates explicit calls; LOCK/transactions use explicit methods |
| V. Foundational Correctness | ✅ PASS | Builds on Spec 007 line mapping ($TEXT), existing ASG infrastructure |
| VI. Cross-Cutting Semantics | ✅ PASS | Timeout behavior sets $TEST uniformly; DB abstraction for all backends |
| VII. Minimize Runtime | ✅ PASS | Math functions emit inline `math.X()`; only DB ops use runtime |
| VIII. Research First | ✅ PASS | research.md documents existing infrastructure before implementation |

**Post-Design Gate Status**: ✅ Design aligns with all constitution principles.

---

## Phase 1 Deliverables

| Artifact | Location | Status |
|----------|----------|--------|
| Research notes | [research.md](research.md) | ✅ Complete |
| Data model | [data-model.md](data-model.md) | ✅ Complete |
| Intrinsic functions contract | [contracts/intrinsic-functions.md](contracts/intrinsic-functions.md) | ✅ Complete |
| Database abstraction contract | [contracts/database-abstraction.md](contracts/database-abstraction.md) | ✅ Complete |
| Z-commands contract | [contracts/z-commands.md](contracts/z-commands.md) | ✅ Complete |
| Math functions contract | [contracts/math-functions.md](contracts/math-functions.md) | ✅ Complete |
| Quickstart guide | [quickstart.md](quickstart.md) | ✅ Complete |

---

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks (Phase 2)
2. Tasks will be organized by implementation phases:
   - Phase A: Stub Cleanup (DELETE + CONVERT)
   - Phase B: High-Impact Features (>10% VistA usage)
   - Phase C: Medium-Impact Features (1-10% VistA usage)
   - Phase D: Low-Impact Features (<1% but used)
   - Phase E: Math Functions & Z-Commands
   - Phase F: Fall-Through Semantics
