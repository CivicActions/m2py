# Implementation Plan: Indirection & XECUTE Runtime

**Branch**: `012-indirection-xecute` | **Date**: 2026-01-16 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-indirection-xecute/spec.md`

## Summary

Implement runtime infrastructure for MUMPS indirection (`@`) and XECUTE command — the "dynamic escape hatch" that allows any MUMPS code to be constructed and executed at runtime. This is the **final codegen spec** — after this, all core MUMPS language constructs are covered.

**Technical approach**: Reuse the existing m2py pipeline (parse → ASG → generate Python → exec()) for runtime XECUTE and indirection evaluation. Emit direct `_scope['var']` access for name indirection. For constant XECUTE strings, inline the generated Python code for better debuggability.

**Why last**: XECUTE can execute ANY MUMPS construct dynamically, so all static constructs (Specs 004-011) must be implemented first.

## Technical Context

**Language/Version**: Python 3.10+ (per pyproject.toml)  
**Primary Dependencies**: textX (grammar/parser), existing m2py codegen pipeline  
**Storage**: `_scope` dict for variable access, `_rt` for runtime state  
**Testing**: pytest with YDB Docker validation (`utils/validate.py`)  
**Target Platform**: Any Python 3.10+ environment  
**Project Type**: Single project (transpiler library)  
**Performance Goals**: Correctness first; performance optimization deferred (may be 10x slower than YDB)  
**Constraints**: Generated code must match YottaDB output exactly  
**Scale/Scope**: Support VistA-scale systems with heavy indirection patterns

### Key ASG Nodes (Already Exist)

| Node | Location | Fields |
|------|----------|--------|
| `MIndirection` | [expressions.py#L262](../../src/m2py/asg/expressions.py#L262) | `expression`, `indirection_type`, `subscripts`, `name_indirection_subscripts`, `requires_runtime_eval` |
| `MXecuteStatement` | [statements.py#L547](../../src/m2py/asg/statements.py#L547) | `code_expressions`, `is_constant`, `constant_values` |
| `IndirectionType` | [enums.py#L136](../../src/m2py/asg/enums.py#L136) | `NAME`, `SUBSCRIPT`, `ARGUMENT`, `PATTERN`, `UNKNOWN` |

### Existing Infrastructure to Extend

| Component | Location | Status |
|-----------|----------|--------|
| `MUMPSRuntime` | [runtime/__init__.py](../../src/m2py/runtime/__init__.py) | ✅ Exists - extend with `execute()`, `get_var()`, `set_var()` |
| `_scope` dict | Generated code | ✅ Exists - used for variable access |
| Pattern compiler | [analysis/pattern_compiler.py](../../src/m2py/analysis/pattern_compiler.py) | ✅ Exists - reuse for pattern indirection |
| Line dispatch | [codegen/line_dispatch.py](../../src/m2py/codegen/line_dispatch.py) | ✅ Exists - used by indirect DO/GOTO |
| External calls | [codegen/statements.py](../../src/m2py/codegen/statements.py) | ✅ Exists - indirect calls use same mechanism |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| 1 | **Semantic Correctness First** | ✅ Pass | 8 user stories with YDB-validated acceptance scenarios |
| 2 | **YDB as Reference** | ✅ Pass | All snippets validated against YDB docker image |
| 3 | **Strict Layer Separation** | ✅ Pass | Parser populates MIndirection/MXecuteStatement; codegen emits runtime calls |
| 4 | **Explicit Over Implicit** | ✅ Pass | All indirection uses explicit `_scope` dict access |
| 5 | **Foundational Correctness** | ✅ Pass | Depends on Specs 004-011 (all static constructs) |
| 6 | **Cross-Cutting Semantics** | ✅ Pass | $TEST not stacked for XECUTE (documented in spec) |
| 7 | **Minimize Runtime Surface** | ⚠️ Acceptable | Indirection/XECUTE are inherently dynamic — runtime required per constitution |
| 8 | **Research Before Implementation** | ✅ Pass | This plan documents research phase |

**Gate Status**: PASS - Principle 7 explicitly lists "XECUTE / Indirection" as requiring runtime support.

## Project Structure

### Documentation (this feature)

```text
specs/012-indirection-xecute/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (runtime API contract)
├── checklists/
│   └── requirements.md  # Requirements validation checklist (exists)
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── runtime/
│   └── __init__.py      # Runtime additions:
│                        #   - execute(mumps_code) for XECUTE
│                        #   - get_var(name) for @X read
│                        #   - set_var(name, value) for @X write
│                        #   - resolve_indirection(name) for multi-level @
│                        #   - IndirectionError exception class
│
├── codegen/
│   ├── expressions.py   # Extend generate_expr() for MIndirection:
│   │                    #   - NAME: _scope[resolved_name]
│   │                    #   - SUBSCRIPT: normal evaluation
│   │                    #   - PATTERN: runtime pattern compile
│   │
│   ├── statements.py    # Extend for MXecuteStatement:
│   │                    #   - Constant strings: inline generated code
│   │                    #   - Dynamic strings: _rt.execute(code)
│   │                    #   - Indirect DO/GOTO: resolve then dispatch
│   │
│   └── indirection.py   # NEW: Indirection-specific generators
│                        #   - generate_name_indirection()
│                        #   - generate_subscript_indirection()
│                        #   - generate_argument_indirection()
│                        #   - generate_pattern_indirection()
│
└── analysis/
    └── (no changes)     # Analysis already marks requires_runtime_eval

tests/
├── unit/codegen/
│   ├── s7_expressions/
│   │   └── test_s7_3_indirection.py  # Indirection expression tests
│   │
│   └── s8_commands/
│       └── test_s8_2_26_xecute.py    # XECUTE command tests
│
├── unit/cross_cutting/
│   └── test_indirection.py           # End-to-end indirection tests
│
└── integration/
    └── test_mugj.py                  # V1IDNM*, V1XECA* test suites
```

**Structure Decision**: Single project with extensions to existing runtime and codegen modules. New `indirection.py` codegen module for cleaner organization.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Runtime `execute()` method | XECUTE requires parsing/compiling code at runtime | Compile-time analysis cannot predict dynamic code content |
| Runtime `get_var()/set_var()` | Name indirection requires dynamic variable access | Python locals() is read-only; direct dict access required |
| `IndirectionError` exception | Clear error messages for invalid indirection | Generic exceptions lose context about which indirection failed |

## Dependencies Summary

### Consumes (from earlier specs)
- **Spec 004**: Value model (`m_num()`, `m_truth()`), basic codegen architecture
- **Spec 005**: $TEST tracking (XECUTE does NOT stack $TEST)
- **Spec 006**: Trampoline pattern for cross-label control flow
- **Spec 007**: Line dispatch for offset-based entry (indirect DO/GOTO with offsets)
- **Spec 008**: External routine loading (indirect calls to external routines)
- **Spec 009**: Global variables (indirection can reference globals)
- **Spec 010**: Intrinsic functions (XECUTE code can call any function)
- **Spec 011**: All operators, pattern compiler (XECUTE/indirection can use any construct)

### Produces
- Complete MUMPS language coverage (final spec)
- Runtime infrastructure for truly dynamic cases
- Full MUGJ test suite compatibility

---

## Constitution Check (Post-Design)

*Re-evaluated after Phase 1 design completion.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| 1 | **Semantic Correctness First** | ✅ Pass | All acceptance scenarios validated against YDB |
| 2 | **YDB as Reference** | ✅ Pass | MUGJ V1IDNM*, V1XECA* test suites as validation targets |
| 3 | **Strict Layer Separation** | ✅ Pass | Parser populates ASG nodes; codegen emits runtime calls; no analysis in codegen |
| 4 | **Explicit Over Implicit** | ✅ Pass | `_scope` dict, explicit `_rt.get_var()`/`set_var()` calls |
| 5 | **Foundational Correctness** | ✅ Pass | Final spec - all foundations from Specs 004-011 in place |
| 6 | **Cross-Cutting Semantics** | ✅ Pass | $TEST NOT stacked for XECUTE (documented, tested) |
| 7 | **Minimize Runtime Surface** | ✅ Pass | Indirection/XECUTE are explicitly listed as runtime cases in constitution |
| 8 | **Research Before Implementation** | ✅ Pass | research.md documents all decisions |

**Post-Design Gate**: PASS - All principles satisfied. Design aligns with constitution principles.

---

## Generated Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Implementation Plan | [plan.md](plan.md) | This file |
| Research | [research.md](research.md) | Decision documentation |
| Data Model | [data-model.md](data-model.md) | Entity definitions |
| Runtime API Contract | [contracts/runtime-api.md](contracts/runtime-api.md) | API specifications |
| Quickstart | [quickstart.md](quickstart.md) | Usage guide |

---

## Next Steps

Phase 2 planning command: `/speckit.tasks`

This will generate:
- `tasks.md` with implementation tasks
- Test stubs
- Implementation phases
