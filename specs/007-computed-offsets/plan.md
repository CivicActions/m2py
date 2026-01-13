# Implementation Plan: Computed Offsets & Line Dispatch

**Branch**: `007-computed-offsets` | **Date**: 2026-01-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-computed-offsets/spec.md`

## Summary

Implement computed offsets for DO/GOTO commands (`G LABEL+N`, `D SUB+expr`) to enable line-indexed execution. The parser already captures offsets in `MCall.offset` as full `MExpr` objects. This spec focuses on **codegen only**: generating a line-to-entry mapping (`_line_map`) and modifying the trampoline dispatcher to support line-based dispatch in addition to label-based dispatch.

**Technical approach**: Extend the trampoline pattern from Spec 006 to return `(target_line, state)` tuples for offset calls. Generate `_line_map: Dict[int, Tuple[str, int]]` mapping source line numbers to (label_name, offset_within_label) tuples. At runtime, evaluate offset expression, compute `target_line = label_line + offset`, and dispatch via `_line_map[target_line]`.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parser), pytest (testing), dataclasses (ASG/codegen)  
**Storage**: N/A (transpiler, no persistence)  
**Testing**: pytest with YDB validation via `utils/validate.py`  
**Target Platform**: macOS/Linux development  
**Project Type**: Single project - transpiler  
**Performance Goals**: Routine transpilation <1 second  
**Constraints**: Generated Python must pass `ast.parse()`, match YDB output exactly  
**Scale/Scope**: VistA codebase (~50M lines MUMPS)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | Generated Python must match YDB output exactly. All acceptance scenarios validated against YDB. |
| II. YDB as Reference Implementation | ✅ PASS | All edge cases (offset=0, variable offset, arithmetic, truncation, invalid offset) validated against YDB docker. |
| III. Strict Layer Separation | ✅ PASS | Parser already captures offsets in MCall.offset. This spec is **codegen-only**. No parser changes needed. |
| IV. Explicit Over Implicit | ✅ PASS | Offset coercion uses existing `m_num()` helper. Line dispatch is explicit via `_line_map`. |
| V. Foundational Correctness | ✅ PASS | Building line dispatch infrastructure now enables $TEXT (Spec 008) and advanced offset expressions (Spec 009/010). |
| VI. Cross-Cutting Semantics | ✅ PASS | Uses existing value coercion helpers. No new cross-cutting concerns introduced. |
| VII. Minimize Runtime Surface | ✅ PASS | Line map is compile-time generated. Offset evaluation uses inline Python (m_num for coercion). No new runtime calls. |
| VIII. Research Before Implementation | ✅ PASS | Research phase completed: ASG structure verified, existing codegen patterns understood, YDB semantics validated. |

## Project Structure

### Documentation (this feature)

```text
specs/007-computed-offsets/
├── plan.md              # This file
├── spec.md              # Feature specification (created)
├── research.md          # Phase 0 output (below)
├── data-model.md        # Phase 1 output (below)
├── quickstart.md        # Phase 1 output (below)
├── contracts/           # N/A - no API contracts for transpiler
├── checklists/
│   └── requirements.md  # Specification quality validation (created)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/m2py/
├── codegen/
│   ├── routine.py       # MODIFY: Add _line_map generation, update trampoline dispatcher
│   ├── statements.py    # MODIFY: Update _generate_goto for offset dispatch
│   └── line_dispatch.py # NEW: Line map generation and offset evaluation helpers
├── asg/
│   └── elements.py      # READ-ONLY: MCall.offset, MLabel.line_number already exist
└── parser/
    └── parser.py        # READ-ONLY: Statement line numbers already populated

tests/
├── unit/codegen/s8_commands/
│   └── test_s8_2_06_goto.py  # ADD: TestComputedOffsetCodegen, TestLineMapGeneration
└── functional/mugj/inref/
    └── V1GO2.m               # VALIDATE: Offset-related tests I-385 through I-392
```

**Structure Decision**: Existing single-project structure. New module `line_dispatch.py` keeps offset-specific logic isolated. Main changes in `routine.py` (trampoline) and `statements.py` (GOTO generation).

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | — | — |
