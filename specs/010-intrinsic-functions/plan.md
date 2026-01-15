# Implementation Plan: Intrinsic Functions

**Branch**: `010-intrinsic-functions` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-intrinsic-functions/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement all MUMPS intrinsic functions ($LENGTH, $PIECE, $EXTRACT, $FIND, $TRANSLATE, $JUSTIFY, $ASCII, $CHAR, $REVERSE, $FNUMBER, $RANDOM, $DATA, $GET, $ORDER, $QUERY, $NAME, $QLENGTH, $QSUBSCRIPT, $SELECT) and complete extrinsic function ($$label) support.

Technical approach:
- Add `generate_intrinsic_function()` dispatcher to `expressions.py` to handle `MIntrinsicFunction` ASG nodes
- Create function-specific helpers in `runtime/helpers.py` (e.g., `m_piece()`, `m_extract()`, `m_order()`)
- Use inline Python for simple functions ($LENGTH, $CHAR), runtime helpers for complex ones ($ORDER, $QUERY)
- Add `MRuntimeError` exception class for SELECTFALSE, RANDARGNEG errors
- Upgrade offset evaluator to support intrinsic function calls in computed offsets

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textX (parser), pytest (testing), MArray (Spec 009), GlobalStorageBackend (Spec 009)
**Storage**: InMemoryGlobalStorage for tests (Spec 009)
**Testing**: pytest with YottaDB Docker validation
**Target Platform**: Linux/macOS CLI transpiler
**Project Type**: single (transpiler library)
**Performance Goals**: Not performance-critical; correctness is paramount
**Constraints**: Generated Python must match YottaDB output exactly

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | All function semantics validated against YottaDB |
| II. YDB as Reference Implementation | ✅ PASS | All acceptance scenarios validated with `docker run ydb` |
| III. Strict Layer Separation | ✅ PASS | Codegen only; parser already captures MIntrinsicFunction nodes |
| IV. Explicit Over Implicit | ✅ PASS | Using helper functions for M-specific semantics |
| V. Foundational Correctness | ✅ PASS | Building on proven Spec 009 infrastructure |
| VI. Cross-Cutting Semantics | ✅ PASS | Uses existing m_num(), m_truth(), m_compare() helpers |
| VII. Minimize Runtime Surface | ✅ PASS | Inline Python for simple functions; runtime only for dynamic cases |
| VIII. Research Before Implementation | ✅ PASS | Docs, ASG, tests reviewed; research.md produced |

## Project Structure

### Documentation (this feature)

```text
specs/010-intrinsic-functions/
├── plan.md              # This file
├── research.md          # Phase 0 output - function implementation strategies
├── data-model.md        # Phase 1 output - function dispatch table
├── quickstart.md        # Phase 1 output - implementation guide
├── contracts/           # Phase 1 output - function signatures
│   └── intrinsic-functions-api.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── codegen/
│   ├── expressions.py   # Add generate_intrinsic_function() dispatcher
│   └── helpers.py       # May need updates for offset evaluator
├── runtime/
│   ├── helpers.py       # Add m_piece(), m_extract(), m_order(), etc.
│   └── exceptions.py    # Add MRuntimeError class (new file)
└── asg/
    └── expressions.py   # MIntrinsicFunction, MSelectArg already exist

tests/
├── unit/codegen/s7_expressions/
│   ├── test_s7_1_5_intrinsic_functions.py  # Replace stubs with real tests
│   └── test_s7_1_6_extrinsic_functions.py  # Expand extrinsic tests
└── functional/mugj/
    └── inref/V1FN*.m    # Validation test suite
```

**Structure Decision**: Single project structure using existing codegen module. No new modules needed - extend `expressions.py` and `runtime/helpers.py`.

## Complexity Tracking

No violations - plan follows all constitution principles.
