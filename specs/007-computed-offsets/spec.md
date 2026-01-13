# Feature Specification: Computed Offsets & Line Dispatch

**Feature Branch**: `007-computed-offsets`  
**Created**: 2026-01-12  
**Status**: Draft  
**Input**: Spec 007 from codegen-plan.md - Computed Offsets & Line Dispatch

## Overview

This specification tackles the **highest-risk architectural problem** in the codegen plan: implementing computed offsets for DO and GOTO commands (`G LABEL+N`, `D SUB+expr`). The risk stems from requiring **line-indexed execution** rather than label-based dispatch.

MUMPS uses source line numbers as execution targets. A GOTO like `G STAR+3` means "jump to the 3rd line after label STAR's line". This requires:

1. **Statement line number tracking** - Ensuring each statement knows its source line
2. **Line-to-entry mapping** - Building a dispatch table keyed by source line numbers
3. **Offset expression evaluation** - Computing the target line from `label_line + offset_value`
4. **Line-based dispatch** - Executing from a specific source line, not just a label

**Parser status**: The parser **already captures** offsets in `MCall.offset` as full `MExpr` objects (verified). This spec focuses on **codegen only**.

**Current behavior**: The codegen ignores offsets entirely, jumping to the label without offset consideration.

## Pre-requisites from Spec 005/006

The following infrastructure is available:

- Trampoline pattern for cross-label GOTO (returns `(next_label, state)` tuple)
- `RoutineState` dataclass for cross-label variable visibility
- `MCall.offset` field populated by parser (can be any `MExpr`)
- `MCall.call_type` = `CallType.OFFSET_CALL` for calls with offsets
- `MLabel.line_number` - source line of each label (set by parser)
- `MStatement.line_number` - source line of each statement (set by parser)
- `MRoutine.source_lines` - original source for $TEXT support

### Infrastructure Verified as Existing

| Component | Status | Details |
|-----------|--------|---------|
| `MCall.offset` | ✅ Parsed | Full MExpr (literals, variables, binary ops) |
| `MLabel.line_number` | ✅ Populated | 1-indexed source line |
| `MStatement.line_number` | ✅ Populated | Set recursively by parser |
| `MRoutine.source_lines` | ✅ Stored | List of original source lines |
| Offset expression parsing | ✅ Working | `G STAR+X+1` → `MBinaryOp('+', LocalVariable('X'), NumericLiteral(1))` |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Literal Offset GOTO (Priority: P1)

As a developer, when I generate Python from MUMPS code with GOTO statements that have literal integer offsets (`G LABEL+3`), the code generator produces correct control transfer to the line that is `offset` lines after the label's line.

**Why this priority**: Literal offsets are the simplest case and most common in real code. They establish the line dispatch infrastructure that all other stories depend on. The V1GO2.m test suite specifically tests `G label+integer` patterns.

**Independent Test**: Can be tested by generating and executing code with literal offset GOTOs and verifying correct line is reached.

**MUMPS Offset Semantics**: `LABEL+N` targets source line `LABEL.line_number + N` (0-indexed from label). So `G STAR+0` executes STAR's line, `G STAR+1` executes the line after STAR, etc.

**Acceptance Scenarios**:

1. **Given** `TEST G STAR+2 Q` / `STAR W "0"` / ` W "1"` / ` W "2"` / ` Q`, **When** generated and executed, **Then** output is "2" (skips to line STAR+2)
2. **Given** `TEST G STAR+0 Q` / `STAR W "X" Q`, **When** generated and executed, **Then** output is "X" (offset 0 executes label line)
3. **Given** `TEST S N=3 D SUB+N W "done" Q` / `SUB W "0"` / ` W "1"` / ` W "2"` / ` W "3"` / ` Q`, **When** generated and executed, **Then** output is "3done" (DO with offset returns after QUIT)

---

### User Story 2 - Variable Offset GOTO (Priority: P1)

As a developer, when I generate Python from MUMPS code with GOTO statements where the offset is a variable (`G LABEL+N`), the code generator evaluates the variable at runtime and dispatches to the correct line.

**Why this priority**: Variable offsets are common in data-driven dispatch patterns. They require runtime evaluation but still use the same line dispatch infrastructure.

**Independent Test**: Can be tested by setting a variable and executing GOTO with variable offset.

**Acceptance Scenarios**:

1. **Given** `TEST S N=2 G STAR+N Q` / `STAR W "0"` / ` W "1"` / ` W "2"` / ` Q`, **When** generated and executed, **Then** output is "2"
2. **Given** `TEST S N=0 G STAR+N Q` / `STAR W "X" Q`, **When** generated and executed, **Then** output is "X"
3. **Given** `TEST F N=0:1:2 D LINE+N Q` / `LINE W "A"` / ` W "B"` / ` W "C"` / ` Q`, **When** generated and executed, **Then** output is "ABCBCC" (DO starts at LINE+N, continues to QUIT; N=0→"ABC", N=1→"BC", N=2→"C")

---

### User Story 3 - Arithmetic Offset Expressions (Priority: P2)

As a developer, when I generate Python from MUMPS code with GOTO/DO where the offset is an arithmetic expression (`G LABEL+A-B`, `G LABEL+1+1`), the code generator correctly evaluates the expression and dispatches to the computed line.

**Why this priority**: Arithmetic expressions in offsets appear in the MUGJ V1GO2.m test suite. Supporting basic arithmetic completes the minimal evaluator.

**Independent Test**: Can be tested with offset expressions using `+`, `-`, `*`, `/` operators.

**Acceptance Scenarios**:

1. **Given** `TEST S A=3,B=1 G STAR+A-B Q` / `STAR W "0"` / ` W "1"` / ` W "2"` / ` Q`, **When** generated and executed, **Then** output is "2" (3-1=2)
2. **Given** `TEST G STAR+1+1 Q` / `STAR W "0"` / ` W "1"` / ` W "2"` / ` Q`, **When** generated and executed, **Then** output is "2" (1+1=2)
3. **Given** `TEST G STAR+6/3 Q` / `STAR W "0"` / ` W "1"` / ` W "2"` / ` Q`, **When** generated and executed, **Then** output is "2" (6/3=2)

---

### User Story 4 - Line-to-Entry Mapping Generation (Priority: P1)

As a developer, the code generator builds a line-to-entry-point mapping (`_line_map`) that enables dispatch by source line number rather than just label name.

**Why this priority**: This is the core infrastructure that all offset-based dispatch depends on. Without it, no offset GOTOs work.

**Independent Test**: Can be tested by verifying generated Python contains `_line_map` with correct entries.

**Acceptance Scenarios**:

1. **Given** routine with offset calls, **When** generated, **Then** Python contains `_line_map` dict mapping source line numbers to entry point functions
2. **Given** routine with comment lines, **When** generated, **Then** `_line_map` excludes non-executable lines (comment-only lines)
3. **Given** offset GOTO to line 5, **When** executed, **Then** dispatch uses `_line_map[5]` to find and execute entry point

---

### User Story 5 - Invalid Offset Error Handling (Priority: P2)

As a developer, when I generate Python from MUMPS code where a computed offset would target a non-existent line (past end of routine), the generated code raises an appropriate error at runtime, matching YottaDB semantics.

**Why this priority**: Error handling is important for correctness but doesn't block basic functionality.

**Independent Test**: Can be tested by executing GOTO with offset that exceeds routine length.

**YottaDB Reference**: `%YDB-E-OFFSETINV, Entry point STAR+100 not valid`

**Acceptance Scenarios**:

1. **Given** `TEST G STAR+100 Q` / `STAR W "X" Q`, **When** executed, **Then** raises error indicating invalid offset (e.g., "Entry point STAR+100 not valid")
2. **Given** `TEST S N=99 G STAR+N Q` / `STAR W "X" Q`, **When** executed, **Then** raises error at runtime (not compile time)

---

### User Story 6 - Non-Integer Offset Coercion (Priority: P3)

As a developer, when GOTO offset expression evaluates to a non-integer, it is truncated to integer using MUMPS numeric coercion rules (floor toward zero).

**Why this priority**: Edge case behavior for numeric correctness.

**Independent Test**: Can be tested with floating-point offset values.

**Acceptance Scenarios**:

1. **Given** `TEST G STAR+2.7 Q` / `STAR W "0"` / ` W "1"` / ` W "2"` / ` Q`, **When** executed, **Then** output is "2" (2.7 truncated to 2)
2. **Given** `TEST G STAR+2.999 Q` / `STAR W "0"` / ` W "1"` / ` W "2"` / ` Q`, **When** executed, **Then** output is "2" (2.999 truncated to 2)

---

### User Story 7 - Comment/Blank Line Handling (Priority: P3)

As a developer, when GOTO offset lands on a comment-only or blank line, execution continues to the next executable line (matching YottaDB behavior).

**Why this priority**: Edge case behavior for completeness. Most code doesn't intentionally target non-executable lines.

**Independent Test**: Can be tested by verifying execution continues past comments.

**Note**: YottaDB verified behavior - offset landing on comment/blank skips to next executable line.

**Acceptance Scenarios**:

1. **Given** `TEST G STAR+1 Q` / `STAR W "0"` / ` ; comment` / ` W "2" Q`, **When** executed, **Then** output is "2" (comment line skipped, continues to next executable)
2. **Given** `TEST G STAR+1 Q` / `STAR W "0"` / `` / ` W "2" Q`, **When** executed, **Then** output is "2" (blank line skipped)

---

### Edge Cases

- What happens when offset expression evaluates to non-integer (e.g., `G STAR+2.5`)? → MUMPS truncates to integer (2)
- What happens when offset expression evaluates to string (e.g., `G STAR+"ABC"`)? → MUMPS coerces to 0 (standard numeric coercion)
- What happens when offset targets middle of a multi-statement line? → Executes all statements on that line (line is execution unit)
- What happens with nested DO+offset that modifies offset variable? → Uses variable value at dispatch time

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate line-to-entry mapping (`_line_map`) for routines containing offset calls
- **FR-002**: System MUST evaluate offset expressions at dispatch time using existing expression codegen
- **FR-003**: System MUST support literal integer offsets (`G LABEL+5`)
- **FR-004**: System MUST support variable offsets (`G LABEL+N`)
- **FR-005**: System MUST support arithmetic expression offsets (`G LABEL+A-B`, `G LABEL+1+1`)
- **FR-006**: System MUST coerce offset expression results to integer using Python `int()` (drops fractional part, matching MUMPS truncation) before dispatch
- **FR-007**: System MUST raise runtime error for offsets that target non-existent lines
- **FR-008**: System MUST skip comment-only and blank lines when offset targets them (continue to next executable)
- **FR-009**: System MUST track which lines are executable vs non-executable for dispatch
- **FR-010**: System MUST work with both GOTO and DO commands that have offsets
- **FR-011**: DO with offset MUST return to caller after QUIT (unlike GOTO which transfers permanently)
- **FR-012**: System MUST integrate with trampoline pattern from Spec 006 (modify dispatch to support line-based targets)

### Key Entities

- **Line Map**: Dictionary mapping source line numbers to entry point functions/callables
- **Offset Expression**: Any `MExpr` that computes the line offset from a label
- **Entry Point**: A callable that executes code starting from a specific source line
- **Executable Line**: A source line that contains at least one MUMPS command (not comment-only or blank)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All V1GO2.m offset-related tests (I-385 through I-392, I-827, I-828) pass when executed against generated Python
- **SC-002**: Literal offset GOTO (`G LABEL+N`) produces correct output for any valid N from 0 to routine length
- **SC-003**: Variable offset GOTO (`G LABEL+VAR`) produces correct output matching YottaDB
- **SC-004**: Arithmetic offset expressions evaluate correctly using MUMPS left-to-right semantics
- **SC-005**: Invalid offset (past end of routine) raises error with descriptive message
- **SC-006**: Generated Python remains syntactically valid (passes `ast.parse()`)
- **SC-007**: Performance: Routine with offset calls transpiles in <1 second

## Assumptions

1. Statement line numbers are correctly populated by parser (verified)
2. Offset expressions use existing expression types (MExpr subtypes) - no new ASG nodes needed
3. Line dispatch infrastructure can coexist with trampoline pattern (extends it)
4. Non-executable lines can be identified by checking if source line is comment-only or blank
5. MUMPS integer truncation for non-integer offsets follows standard numeric coercion rules

## Explicitly Out of Scope (Deferred to Later Specs)

**Spec 008** (External Calls):
- Cross-routine offsets (`G LABEL+N^ROUTINE`)
- $TEXT function with external routine reference (`$T(LABEL+N^ROUTINE)`)
- $TEXT function implementation (uses line dispatch infrastructure built here)

**Spec 009** (LHS Functions & Globals):
- Global variables in offset expressions (`G LABEL+^VAR`)
- Subscripted globals in offsets (`G LABEL+^VAR(1)`)

**Spec 010** (Intrinsic Functions):
- Function calls in offset expressions (`G LABEL+$L(X)`, `G LABEL+$D(VAR)`)
- $DATA, $ORDER, $LENGTH etc. in offsets

**Spec 011** (Operators & Commands):
- Postconditioned offset GOTOs (`G:cond LABEL+N`) - postcondition codegen is Spec 011
- Pattern match operators in offset expressions

**Spec 012** (Indirection & XECUTE):
- Indirect offset computation (`G LABEL+@VAR`)
- XECUTE with offset targets

## Dependencies

### This Spec Produces (for later specs):

- Line-to-entry mapping infrastructure (used by Spec 008 for $TEXT)
- Offset expression evaluation pattern (extended by Spec 009/010 for globals/functions)
- Line-based dispatch mechanism (foundation for all line-indexed operations)

### This Spec Consumes (from earlier specs):

- Trampoline dispatcher from Spec 006 (modified to support line-based dispatch)
- Expression codegen from Spec 004 (used for offset evaluation)
- Statement line numbers from parser (already populated)
- RoutineState dataclass from Spec 006 (unchanged, for variable visibility)
