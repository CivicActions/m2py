# Implementation Plan: Spec 005 - Structured Control Flow Codegen

**Branch**: `005-structured-control-flow` | **Date**: 2025-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-structured-control-flow/spec.md`

## Summary

Implement Python code generation for MUMPS structured control flow constructs. This spec extends the basic codegen from Spec 004 to handle:

- **FOR loop variations**: Bounded, open-ended, argumentless, value-list, and mixed parameter loops with proper break/while handling when loop variables are modified
- **Intra-label GOTO (forward only)**: Generate `continue`, `break`, and exception patterns for loop exits; restructure forward jumps to if/else. Backward intra-label GOTO deferred to Spec 006
- **Context-aware QUIT**: Generate `break` in FOR context, `return` in DO context
- **By-reference parameters**: Generate return tuples and call-site destructuring for modified by-ref params
- **$TEST stack**: Save/restore $TEST around argumentless DO and extrinsic function calls

**Explicitly out of scope** (handled in later specs):
- Cross-label GOTO of any kind (`is_cross_label=True`) → Spec 006
- Backward intra-label GOTO (creates implicit loops) → Spec 006
- `REQUIRES_RUNTIME` scope strategy → Spec 006/007
- Postcondition codegen (`S:cond X=1`, `Q:cond`) → Spec 008
- Full extrinsic functions (`$$label^routine`) → Spec 008

All patterns leverage existing analysis infrastructure (for_analysis, goto_analysis, variables) - no new ASG types needed.

## Technical Context

**Language/Version**: Python 3.10+ (target output); textX for parser  
**Primary Dependencies**: textX (parsing), itertools (FOR codegen), pytest (testing)  
**Storage**: N/A (transpiler, no persistence)  
**Testing**: pytest with YDB Docker fixture for reference output comparison  
**Target Platform**: Any Python runtime  
**Project Type**: Single project (transpiler library)  
**Performance Goals**: Transpile typical routine (<1000 lines) in <1 second  
**Constraints**: Generated code must be syntactically valid Python (ast.parse)  
**Scale/Scope**: Handle full MUMPS control flow subset defined in spec

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Semantic Correctness First** | ✅ PASS | Generated Python must match YDB output exactly |
| **II. YDB is Reference** | ✅ PASS | All test cases validated against YDB |
| **III. Strict Layer Separation** | ✅ PASS | Codegen consumes analysis, doesn't modify ASG |
| **IV. Explicit Over Implicit** | ✅ PASS | All patterns documented in research.md |
| **V. Foundational Correctness** | ✅ PASS | Basic control flow before optimization |
| **VI. Cross-Cutting Semantics** | ✅ PASS | $TEST handled consistently |
| **VII. Minimize Runtime Surface** | ✅ PASS | No new runtime infrastructure; save/restore pattern for $TEST |
| **VIII. Research Before Implementation** | ✅ PASS | research.md complete with all decisions |

**Re-check after Phase 1**: All principles still satisfied. By-ref return tuple is explicit and requires no runtime. $TEST save/restore uses simple Python assignment.

## Project Structure

### Documentation (this feature)

```text
specs/005-structured-control-flow/
├── plan.md              # This file
├── research.md          # Phase 0 output - research findings
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - implementation guide
├── contracts/           # Phase 1 output - API contracts
│   ├── README.md
│   ├── codegen_contracts.py
│   └── analysis_requirements.md
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── analysis/
│   ├── for_analysis.py      # FOR loop classification (existing)
│   ├── goto_analysis.py     # GOTO classification (existing)
│   └── variables.py         # Scope strategy (existing)
├── asg/
│   ├── enums.py             # ForLoopType, GotoType, ScopeStrategy (existing)
│   └── statements.py        # MForStatement, MGotoStatement, MQuitStatement (existing)
└── codegen/
    ├── emitter.py           # Code emission utilities (existing)
    ├── expressions.py       # Expression codegen (existing, extend for $$)
    ├── helpers.py           # Runtime helpers (existing, maybe add m_for_range)
    ├── names.py             # Name translation (existing)
    ├── routine.py           # Module/label generation (modify for signatures)
    └── statements.py        # Statement codegen (major changes)

tests/
├── unit/
│   └── codegen/
│       ├── test_for_loops.py        # NEW: FOR loop patterns
│       ├── test_goto_patterns.py    # NEW: GOTO patterns
│       ├── test_quit_context.py     # NEW: QUIT context
│       ├── test_signatures.py       # NEW: Function signatures
│       ├── test_byref.py            # NEW: By-ref returns
│       └── test_test_stack.py       # NEW: $TEST save/restore
└── functional/
    └── control_flow/
        └── *.m                      # MUMPS test cases
```

**Structure Decision**: Single project structure. Spec 005 modifies existing `src/m2py/codegen/` modules and adds new unit tests. No new packages needed.

## Complexity Tracking

No constitution violations to justify.
