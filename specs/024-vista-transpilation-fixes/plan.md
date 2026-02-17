# Implementation Plan: VistA-VEHU-M Complete Transpilation

**Branch**: `024-vista-transpilation-fixes` | **Date**: 2026-02-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/024-vista-transpilation-fixes/spec.md`

## Summary

Resolve all 2,592 VistA-VEHU-M transpilation failures (13 root causes) to achieve ≥99% transpilation success (from 93.4%). Fixes span three layers: semantic analyzer (ParenExpr unwrapping), codegen (f-strings, empty blocks, operators, special variables, GOTO dispatch), and runtime (IRIS vendor functions, special variables, stubs). The only accepted remaining limitation is MWAPI SSVNs (LIM-003, X11.6 standard). A new limitation entry documents partial IRIS/Caché support.

## Technical Context

**Language/Version**: Python 3.10+ (generated code must be valid on 3.10; transpiler itself runs on 3.10+)
**Primary Dependencies**: textX (parser), pytest (testing), uv (package management)
**Storage**: SQLite-backed global storage (existing `sqlite_storage.py`)
**Testing**: pytest with `uv run pytest`; YDB Docker validation via `utils/validate.py`
**Target Platform**: Linux (dev container), generated Python runs cross-platform
**Project Type**: Single project — monorepo with `src/m2py/` source tree
**Performance Goals**: Transpile all 39,304 VistA routines; no individual routine takes >30s
**Constraints**: Python 3.10 f-string compatibility; no new external dependencies for runtime
**Scale/Scope**: 39,304 MUMPS routines; 2,592 currently failing; 13 distinct root causes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | All fixes match MUMPS/YDB/IRIS reference behavior. Test snippets validated against YDB and IRIS. |
| II. YDB as Reference Implementation | ✅ PASS | Standard MUMPS fixes validated against YDB. IRIS functions validated against IRIS 2025.2. |
| III. Strict Layer Separation | ✅ PASS | ParenExpr fix: codegen fallback handler (defensive) + analyzer audit (root cause). Operator fixes in codegen. Vendor functions in runtime. No analysis in codegen. |
| IV. Explicit Over Implicit | ✅ PASS | All new behaviors use explicit runtime calls (m_replace, m_zboolean, etc.) or explicit codegen patterns. |
| V. Foundational Correctness | ✅ PASS | Fixes foundational gaps (ParenExpr unwrapping, TRAMPOLINE empty blocks) before adding features. |
| VI. Cross-Cutting Semantics | ✅ PASS | $X/$Y, $ZR, $NAMESPACE implemented in shared runtime, not per-command. |
| VII. Minimize Runtime Surface | ✅ PASS | Operators (>=, <=) emit inline Python. Only truly dynamic features (computed GOTO, indirected NEW, vendor functions) use runtime calls. |
| VIII. Research Before Implementation | ✅ PASS | Full codebase research completed — all modification points identified with exact file/line references. |

**Gate Result**: PASS — no violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/024-vista-transpilation-fixes/
├── plan.md              # This file
├── research.md          # Phase 0 output (failure analysis + codebase mapping)
├── data-model.md        # Phase 1 output (entity/function catalog)
├── quickstart.md        # Phase 1 output (implementation guide)
├── contracts/           # Phase 1 output (test contracts per fix)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── analysis/
│   └── semantic_analyzer.py   # ParenExpr/UnaryPrefixedExpr unwrapping audit
├── codegen/
│   ├── expressions.py         # >= <= operators, ParenExpr fallback, UnaryPrefixedExpr fallback
│   ├── statements.py          # SET $X/$Y, LHS $E 1-arg, tuple SET $P/$E, NEW indirection,
│   │                          #   TRAMPOLINE empty blocks, ZLOAD handler, computed GOTO,
│   │                          #   WRITE /cmd, SET $ZINTERRUPT/$ZERR/$ZSOURCE, $& stubs
│   └── indirection.py         # f-string → string concatenation fix
├── runtime/
│   ├── __init__.py            # $X/$Y setters, $ZA, $ZR, $NAMESPACE, $ZV, $DEVICE, $REFERENCE,
│   │                          #   $ZGBLDIR, computed GOTO dispatch
│   └── helpers.py             # m_replace(), m_zboolean(), m_zu(), m_zf(), m_zcall_stub(),
│   │                          #   m_view_stub()
│   └── devices.py             # Device control mnemonics handler
├── limitations.py             # New LIM-017 (IRIS partial support), update LIM-012/LIM-015
└── cli/                       # Encoding fallback for file reading

tests/
├── unit/
│   ├── codegen/               # Tests for each codegen fix
│   └── runtime/               # Tests for each runtime function
├── integration/               # VistA routine transpilation tests
└── functional/                # End-to-end MUMPS→Python→output tests
```

**Structure Decision**: All changes are within the existing `src/m2py/` structure. No new directories needed beyond possibly `contracts/` in the spec folder. Runtime vendor functions go in `helpers.py` alongside existing helpers.

## Complexity Tracking

No constitution violations — this section is empty.

