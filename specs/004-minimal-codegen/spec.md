# Feature Specification: Minimal Control Flow Foundation

**Feature Branch**: `004-minimal-codegen`  
**Created**: 2026-01-09  
**Status**: Draft  
**Input**: Spec 004 from codegen-plan.md - Minimal Control Flow Foundation

## Overview

This specification establishes the **absolute minimum code generation infrastructure** needed to validate control flow patterns in subsequent specs (005/006). The goal is not comprehensive MUMPS support, but rather just enough syntax to test branching, loops, and jumps work correctly.

Control flow testing doesn't require complex computation—just path verification. Generated code outputs markers to show which branches executed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Python from Simple MUMPS Routine (Priority: P1)

As a developer working on the M2PY transpiler, I can pass a simple MUMPS routine through the code generator and receive valid, executable Python code that produces the same output as YDB.

**Why this priority**: This is the foundational capability. Without Python generation, nothing else works. Even minimal generation proves the architecture is sound.

**Independent Test**: Can be tested by generating Python from a simple SET/WRITE routine and verifying output matches YDB.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine with a label, SET, and WRITE commands (`TEST S X=1 W X Q`), **When** passed to the code generator, **Then** valid Python code is produced that outputs "1"
2. **Given** a MUMPS routine with string literals (`TEST W "PASS" Q`), **When** generated and executed, **Then** output is "PASS"
3. **Given** a MUMPS routine with arithmetic (`TEST W 2+3 Q`), **When** generated and executed, **Then** output is "5"

---

### User Story 2 - IF/ELSE Control Flow (Priority: P1)

As a developer, I can generate Python code from MUMPS IF/ELSE statements that correctly evaluates conditions and executes the appropriate branch.

**Why this priority**: IF/ELSE is the most basic control flow. Spec 005 builds on this with $TEST tracking, so it must work first.

**Independent Test**: Can be tested with simple condition/branch routines verifying correct path taken.

**Acceptance Scenarios**:

1. **Given** `TEST S X=5 I X>3 W "GT" Q E W "LE" Q`, **When** generated and executed, **Then** output is "GT"
2. **Given** `TEST S X=1 I X>3 W "GT" Q E W "LE" Q`, **When** generated and executed, **Then** output is "LE"
3. **Given** `TEST S X=0 I X W "TRUE" Q E W "FALSE" Q`, **When** generated and executed, **Then** output is "FALSE" (zero is false)

---

### User Story 3 - FOR Loop Iteration (Priority: P1)

As a developer, I can generate Python code from MUMPS FOR loops that iterates the correct number of times with the correct loop variable values.

**Why this priority**: FOR loops are fundamental to control flow testing. Spec 005 adds complex variations; basic bounded loops must work first.

**Independent Test**: Can be tested by iterating and outputting loop variable values.

**Acceptance Scenarios**:

1. **Given** `TEST F I=1:1:3 W I Q`, **When** generated and executed, **Then** output is "123"
2. **Given** `TEST F I=5:-1:3 W I Q`, **When** generated and executed, **Then** output is "543" (decrementing)
3. **Given** `TEST F I="A","B","C" W I Q`, **When** generated and executed, **Then** output is "ABC" (string list)

---

### User Story 4 - GOTO to Label (Priority: P2)

As a developer, I can generate Python code from MUMPS GOTO statements that transfer control to a named label.

**Why this priority**: GOTO is essential for testing control flow paths. Simple label-as-function calls prove the infrastructure before Spec 005/006 add restructuring complexity.

**Independent Test**: Can be tested by verifying control transfers to target label.

**Acceptance Scenarios**:

1. **Given** a routine with `G DONE` where `DONE` is a label, **When** generated, **Then** the GOTO translates to a function call followed by return (`DONE(); return`)
2. **Given** `TEST G END Q END W "END" Q`, **When** generated and executed, **Then** output is "END"

**Note**: Intra-label GOTO restructuring (skipping intermediate statements within a label) is deferred to Spec 005. Cross-label variable visibility issues are deferred to Spec 006.

---

### User Story 5 - DO Subroutine Call (Priority: P2)

As a developer, I can generate Python code from MUMPS DO statements that call labels as subroutines and return correctly.

**Why this priority**: DO calls are needed to test scope and return behavior. Spec 005 builds on this with parameter passing.

**Independent Test**: Can be tested by calling a subroutine and verifying execution returns to caller.

**Acceptance Scenarios**:

1. **Given** `TEST D SUB W "END" Q SUB W "SUB" Q`, **When** generated and executed, **Then** output is "SUBEND"
2. **Given** nested calls `TEST D A Q A D B Q B W "B" Q`, **When** generated and executed, **Then** output is "B"

---

### User Story 6 - MUMPS Value Coercion (Priority: P2)

As a developer, the generated Python code correctly implements MUMPS's unusual value coercion rules for numeric conversion, truth evaluation, and comparisons.

**Why this priority**: Incorrect coercion breaks all conditional logic. Must be correct from the start to avoid painful refactoring.

**Independent Test**: Can be tested with edge cases that differ from Python's native behavior.

**Acceptance Scenarios**:

1. **Given** `TEST I "0" W "TRUE" E W "FALSE" Q`, **When** generated and executed, **Then** output is "FALSE" (string "0" is falsy in MUMPS)
2. **Given** `TEST I "1A" W "TRUE" E W "FALSE" Q`, **When** generated and executed, **Then** output is "TRUE" (numeric prefix 1 ≠ 0)
3. **Given** `TEST I "A" W "TRUE" E W "FALSE" Q`, **When** generated and executed, **Then** output is "FALSE" (no numeric prefix = 0)
4. **Given** `TEST I "3A"<5 W "YES" E W "NO" Q`, **When** generated and executed, **Then** output is "YES" ("3A" coerces to 3)

---

### User Story 7 - Name Translation (Priority: P3)

As a developer, the code generator correctly translates MUMPS names (labels, variables) that would be invalid Python identifiers into valid, reversible Python names.

**Why this priority**: Needed for real MUMPS code, but can test with normal names initially.

**Independent Test**: Can be tested with names containing %, numeric-only names, and reserved words.

**Acceptance Scenarios**:

1. **Given** a label named `%START`, **When** generated, **Then** Python function name preserves the meaning (e.g., `_pct_START`)
2. **Given** a variable named `0`, **When** generated, **Then** Python variable name is valid (e.g., `_n_0`)
3. **Given** a variable named `IF`, **When** generated, **Then** Python variable name doesn't conflict with keyword (e.g., `_m_IF`)

---

### Edge Cases

- **Empty string coercion**: `""` must coerce to 0 (falsy)
- **Leading zeros**: `"007"` coerces to 7, but variable name `007` preserves leading zeros
- **Negative step FOR**: `F I=10:-2:0` should count 10,8,6,4,2,0
- **QUIT without value**: Must exit current context correctly
- **Case sensitivity**: `FOO`, `Foo`, `foo` are three different names

**Edge cases deferred to later specs**:
- Zero step FOR (`F I=1:0` infinite loop) → Spec 005
- Open-ended FOR (`F I=1:1` no end) → Spec 005  
- QUIT inside FOR (`Q:I=5` break pattern) → Spec 005
- QUIT with value (extrinsic return) → Spec 008
- Cross-label GOTO variable visibility → Spec 006

## Requirements *(mandatory)*

### Functional Requirements

#### Expression Generation

- **FR-001**: System MUST generate Python code for integer literals (positive, negative)
- **FR-002**: System MUST generate Python code for string literals (including empty strings)
- **FR-003**: System MUST generate Python code for local variable references (simple names only, no subscripts)
- **FR-004**: System MUST generate Python code for comparison operators (`=`, `<`, `>`) with proper MUMPS numeric coercion
- **FR-005**: System MUST generate Python code for arithmetic operators (`+`, `-`) with proper MUMPS numeric coercion
- **FR-006**: System MUST preserve MUMPS left-to-right evaluation order (no operator precedence)

#### Value Model Helpers

- **FR-007**: System MUST provide `m_num()` helper that implements MUMPS numeric coercion (scan left-to-right for longest valid numeric prefix, canonicalize)
- **FR-008**: System MUST provide `m_truth()` helper that implements MUMPS truth evaluation (numeric value 0 is false, all others true)
- **FR-009**: System MUST provide `m_compare()` helper for comparison operations that forces numeric evaluation on both operands

#### Statement Generation

- **FR-010**: System MUST generate Python code for SET command (single assignment only: `S X=1`)
- **FR-011**: System MUST generate Python code for WRITE command (single value: `W X` or `W "text"`)
- **FR-012**: System MUST generate Python code for QUIT command (without value)
- **FR-013**: System MUST generate Python code for IF command (single condition)
- **FR-014**: System MUST generate Python code for ELSE command
- **FR-015**: System MUST generate Python code for FOR command with literal bounded range (`F I=1:1:10`)
- **FR-016**: System MUST generate Python code for FOR command with string list (`F I="A","B","C"`)
- **FR-017**: System MUST generate Python code for DO command (label call within same routine, no parameters)
- **FR-018**: System MUST generate Python code for GOTO command as function call + return (label targets only, no offsets, no intra-label restructuring)

#### Name Translation

- **FR-019**: System MUST translate MUMPS names with `%` prefix to valid Python identifiers (e.g., `%FOO` → `_pct_FOO`)
- **FR-020**: System MUST translate pure numeric MUMPS names to valid Python identifiers (e.g., `01` → `_n_01`)
- **FR-021**: System MUST translate MUMPS names that conflict with Python reserved words (e.g., `IF` → `_m_IF`)
- **FR-022**: Name translation MUST be case-preserving (`FOO` ≠ `Foo` ≠ `foo`)
- **FR-023**: Name translation MUST be injective (no two MUMPS names map to same Python name)

#### Routine Structure

- **FR-024**: System MUST generate a Python module from a single-routine MUMPS file
- **FR-025**: System MUST generate Python functions for each label in the routine
- **FR-026**: System MUST handle labelless preamble code (lines before first label)
- **FR-027**: Generated Python code MUST be syntactically valid (parseable by `ast.parse()`)

#### Code Generation Infrastructure

- **FR-028**: System MUST use `CodeEmitter` class for indent-aware code generation
- **FR-029**: System MUST track `$TEST` state for IF/ELSE sequencing via `_test` variable
- **FR-030**: Local variables MUST be emitted as Python locals (NOT runtime scope access)

### Key Entities

- **MExpr**: Base expression class - literals, variables, operations
- **MLiteral**: Constant values (string, integer)
- **MVariable**: Local variable reference (name only for this spec)
- **MBinaryOp**: Binary operations (comparison, arithmetic)
- **MStatement**: Base statement class with postcondition support
- **MSetStatement**: Variable assignment with target/value
- **MWriteStatement**: Output with arguments list
- **MIfStatement**: Conditional with condition(s) and then_scope
- **MElseStatement**: Alternative with body scope
- **MForStatement**: Loop with parameters and body
- **MDoStatement**: Subroutine call with targets
- **MGotoStatement**: Jump with targets
- **MQuitStatement**: Return from context
- **MLabel**: Named entry point with body statements
- **MRoutine**: Collection of labels

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of test cases in acceptance scenarios produce output matching YDB reference
- **SC-002**: Generated Python code passes `ast.parse()` validation for all test inputs
- **SC-003**: All M coercion edge cases (empty string, "0", "3A", "A") match YDB behavior
- **SC-004**: Name translation correctly handles 100% of special patterns (%, numeric, reserved words)
- **SC-005**: Test suite achieves ≥85% code coverage on new codegen module
- **SC-006**: FOR loops iterate exact correct count (no off-by-one errors)
- **SC-007**: GOTO correctly transfers control to target label (call+return pattern executes target function)

## Assumptions

- The ASG is fully populated by the parser before code generation begins (no parsing in codegen)
- Analysis passes (resolver, for_analysis, goto_analysis) have been run and populated classification fields
- `ScopeStrategy` for all labels in scope is `PURE_FUNCTION` or similar (not `REQUIRES_RUNTIME`)
- Only same-routine labels are targeted by DO/GOTO (external routine calls deferred to Spec 009)
- Argumentless DO blocks and FOR exit patterns are deferred to Spec 005

## Explicitly Deferred

The following are explicitly **out of scope** for Spec 004:

- Intrinsic functions ($PIECE, $LENGTH, $GET, etc.)
- Global variables (^name)
- READ command
- NEW / KILL commands
- Logical operators (&, !)
- String concatenation (_)
- Pattern match (?)
- Negated comparisons ('=, '<, '>)
- Multiple assignments (S X=1,Y=2)
- Format controls (!, #, ?n)
- Postconditions (S:cond X=1)
- Extrinsic functions ($$func)
- Subscripted variables
- DO/GOTO with offsets (G LABEL+5, D SUB+N)
- Complex FOR parameters (F I=$D(I):1:^MAX)
- Decimal literals (covered in Spec 008)
- $TEST stacking for argumentless DO (Spec 005)
- Intra-label GOTO restructuring (forward jumps → if/else) (Spec 005)
- QUIT context awareness (exits_for, exits_do_block) (Spec 005)
- FOR loop variations requiring analysis flags (open-ended, argumentless, mixed, loop_var_modified, has_internal_quit) (Spec 005)
- Cross-label GOTO with variable visibility (Spec 006)
- State machine or trampoline patterns for complex GOTO (Spec 006)
- XECUTE / Indirection (Spec 007)

## Research Phase

Review before implementing:

- **Docs**: `docs/asg/expressions.md`, `docs/asg/statements.md`, `docs/codegen/index.md`
- **Expressions**: `asg/expressions.py` → `MLiteral`, `MVariable`, `MBinaryOp`, `MUnaryOp`
- **Statements**: `asg/statements.py` → `MSetStatement`, `MWriteStatement`, `MIfStatement`, `MForStatement`, `MGotoStatement`
- **Structure**: `asg/elements.py` → `MLabel.body.statements`, `MRoutine.labels`
- **Scope**: `analysis/variables.py` → `ScopeStrategy`, `FunctionSignature.scope_strategy`
- **Emitter**: `codegen/emitter.py` → `CodeEmitter` class
- **ASG dump**: `uv run python utils/validate_asg.py --compact -c "TEST S X=1 W X Q"`
