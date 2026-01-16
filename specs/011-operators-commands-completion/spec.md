# Feature Specification: Extended Operators, Commands & Completion

**Feature Branch**: `011-operators-commands-completion`  
**Created**: 2026-01-15  
**Status**: Draft  
**Input**: Spec 011 from codegen-plan.md - Extended Operators, Commands & Completion

## Overview

This specification completes the remaining operators, statements, and edge cases for MUMPS-to-Python code generation. This is cleanup work that fills in the remaining gaps after the core infrastructure (globals, intrinsic functions, control flow) has been established.

**Scope**: This spec covers:
1. **Extended Operators** - Negated comparisons, logical operators, string concatenation, contains/follows, modulo, integer division, pattern match
2. **Extended Statements** - Multiple SET, format controls, READ, NEW (selective), KILL (selective), MERGE, HANG, HALT, postconditions
3. **Exclusive NEW/KILL** - Runtime scope manipulation
4. **Special Variables** - $HOROLOG, $JOB, $IO, $X, $Y, $STORAGE, $STACK, $QUIT
5. **Decimal Numeric Literals** - Codegen support (already parsed)

**Note**: $TEST is covered in Spec 005; this spec adds remaining special variables only.

## Pre-requisites from Specs 009/010

The following infrastructure is required:

- **MArray class**: MUMPS array structure for MERGE, NEW/KILL semantics
- **Intrinsic functions**: All functions implemented for validation tests
- **Global variables**: For MERGE operations

### Infrastructure Expected from Spec 009/010

| Component | Description |
|-----------|-------------|
| `MArray` | MUMPS array class with `value` and `children` at each node |
| `GlobalStorageBackend` | Protocol for global variable storage |
| `_rt.globals` | Runtime global storage access |
| `generate_expr()` | Full expression generation including intrinsics |
| Pattern compiler | `compile_pattern_to_regex()` for pattern match (already implemented in analysis) |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Logical Operators (Priority: P1)

As a developer, when I generate Python from MUMPS code with logical operators (`&`, `!`, `'`), the code generator produces working Python with correct boolean logic.

**Why this priority**: Logical operators are fundamental for conditional logic in IF statements and postconditions.

**Independent Test**: Verify AND, OR, NOT operators produce correct boolean results.

**YottaDB Verified Behavior**:
```
1&1 → 1 (true AND true)
1&0 → 0 (true AND false)
1!0 → 1 (true OR false)
0!0 → 0 (false OR false)
'1 → 0 (NOT true)
'0 → 1 (NOT false)
```

**Acceptance Scenarios**:

1. **Given** `TEST W 1&1,! Q`, **When** generated and executed, **Then** output is "1\n"
2. **Given** `TEST W 1&0,! Q`, **When** generated and executed, **Then** output is "0\n"
3. **Given** `TEST W 1!0,! Q`, **When** generated and executed, **Then** output is "1\n"
4. **Given** `TEST W 0!0,! Q`, **When** generated and executed, **Then** output is "0\n"
5. **Given** `TEST W '1,! Q`, **When** generated and executed, **Then** output is "0\n" (NOT operator)
6. **Given** `TEST W '0,! Q`, **When** generated and executed, **Then** output is "1\n"
7. **Given** `TEST W 1&1!0,! Q`, **When** generated and executed, **Then** output is "1\n" (left-to-right: (1&1)!0)

---

### User Story 2 - String Concatenation (Priority: P1)

As a developer, when I generate Python from MUMPS code with the concatenation operator (`_`), the code generator produces working Python that joins strings correctly.

**Why this priority**: String concatenation is essential for building output strings and data manipulation.

**Independent Test**: Verify string concatenation joins multiple values.

**YottaDB Verified Behavior**:
```
"A"_"B"_"C" → "ABC"
"X"_1_"Y" → "X1Y" (numbers coerced to strings)
```

**Acceptance Scenarios**:

1. **Given** `TEST W "A"_"B"_"C",! Q`, **When** generated and executed, **Then** output is "ABC\n"
2. **Given** `TEST W "X"_1_"Y",! Q`, **When** generated and executed, **Then** output is "X1Y\n"
3. **Given** `TEST S X="Hello" W X_" World",! Q`, **When** generated and executed, **Then** output is "Hello World\n"

---

### User Story 3 - Negated Comparison Operators (Priority: P1)

As a developer, when I generate Python from MUMPS code with negated comparisons (`'=`, `'<`, `'>`), the code generator produces correct comparison logic.

**Why this priority**: Negated comparisons are frequently used for "not equal", "greater than or equal", and "less than or equal" conditions.

**Independent Test**: Verify negated comparisons produce correct boolean results.

**YottaDB Verified Behavior**:
```
5'=5 → 0 (not equal is false when equal)
5'=6 → 1 (not equal is true when different)
10'<5 → 1 (not less than is true: 10 >= 5)
5'>10 → 1 (not greater than is true: 5 <= 10)
```

**Acceptance Scenarios**:

1. **Given** `TEST W 5'=5,! Q`, **When** generated and executed, **Then** output is "0\n" (equal, so not-equal is false)
2. **Given** `TEST W 5'=6,! Q`, **When** generated and executed, **Then** output is "1\n" (not equal)
3. **Given** `TEST W 10'<5,! Q`, **When** generated and executed, **Then** output is "1\n" (10 >= 5)
4. **Given** `TEST W 5'>10,! Q`, **When** generated and executed, **Then** output is "1\n" (5 <= 10)

---

### User Story 4 - Contains and Follows Operators (Priority: P2)

As a developer, when I generate Python from MUMPS code with contains (`[`) and follows (`]`, `]]`) operators, the code generator produces correct string comparison logic.

**Why this priority**: Contains is used for substring checking. Follows is used for collation ordering.

**Independent Test**: Verify contains and follows operators produce correct results.

**YottaDB Verified Behavior**:
```
"ABC"["B" → 1 (contains)
"ABC"["X" → 0 (does not contain)
"B"]"A" → 1 (B follows A in collation)
"A"]"B" → 0 (A does not follow B)
```

**Acceptance Scenarios**:

1. **Given** `TEST W "ABC"["B",! Q`, **When** generated and executed, **Then** output is "1\n"
2. **Given** `TEST W "ABC"["X",! Q`, **When** generated and executed, **Then** output is "0\n"
3. **Given** `TEST W "B"]"A",! Q`, **When** generated and executed, **Then** output is "1\n"
4. **Given** `TEST W "A"]"B",! Q`, **When** generated and executed, **Then** output is "0\n"
5. **Given** `TEST W "B"]]"A",! Q`, **When** generated and executed, **Then** output is "1\n" (B sorts after A)
6. **Given** `TEST W "A"]]"A",! Q`, **When** generated and executed, **Then** output is "0\n" (not after itself)
7. **Given** `TEST W ""]]"A",! Q`, **When** generated and executed, **Then** output is "0\n" (empty never strictly follows)

---

### User Story 5 - Modulo and Integer Division (Priority: P2)

As a developer, when I generate Python from MUMPS code with modulo (`#`) and integer division (`\`) operators, the code generator produces correct arithmetic results.

**Why this priority**: These operators are used for date calculations, array indexing, and numeric formatting.

**Independent Test**: Verify modulo and integer division produce correct results.

**YottaDB Verified Behavior**:
```
7#3 → 1 (7 mod 3)
7\3 → 2 (7 integer-divide 3)
10#4 → 2
10\4 → 2
```

**Acceptance Scenarios**:

1. **Given** `TEST W 7#3,! Q`, **When** generated and executed, **Then** output is "1\n"
2. **Given** `TEST W 7\3,! Q`, **When** generated and executed, **Then** output is "2\n"
3. **Given** `TEST W 10#4,! Q`, **When** generated and executed, **Then** output is "2\n"
4. **Given** `TEST W 10\4,! Q`, **When** generated and executed, **Then** output is "2\n"

---

### User Story 6 - Pattern Match Operator (Priority: P2)

As a developer, when I generate Python from MUMPS code with the pattern match operator (`?`), the code generator produces working Python using regex matching.

**Why this priority**: Pattern matching is used for input validation and data parsing.

**Independent Test**: Verify pattern matching validates strings correctly.

**YottaDB Verified Behavior**:
```
"ABC"?1A.A → 1 (one letter, any letters)
"A1B"?1A.A → 0 (fails because of digit)
"123"?1N.N → 1 (one or more digits)
"AB12"?2A2N → 1 (exactly 2 letters, 2 digits)
```

**Acceptance Scenarios**:

1. **Given** `TEST W "ABC"?1A.A,! Q`, **When** generated and executed, **Then** output is "1\n"
2. **Given** `TEST W "A1B"?1A.A,! Q`, **When** generated and executed, **Then** output is "0\n"
3. **Given** `TEST W "123"?1N.N,! Q`, **When** generated and executed, **Then** output is "1\n"
4. **Given** `TEST W "AB12"?2A2N,! Q`, **When** generated and executed, **Then** output is "1\n"

---

### User Story 7 - Multiple SET Assignments (Priority: P1)

As a developer, when I generate Python from MUMPS code with multiple SET assignments (`S X=1,Y=2,Z=3`), the code generator produces multiple Python assignment statements.

**Why this priority**: Multiple assignments on one line are extremely common in MUMPS code.

**Independent Test**: Verify multiple assignments set all variables correctly.

**YottaDB Verified Behavior**:
```
S X=1,Y=2,Z=3 W X,Y,Z → 123
```

**Acceptance Scenarios**:

1. **Given** `TEST S X=1,Y=2,Z=3 W X,Y,Z,! Q`, **When** generated and executed, **Then** output is "123\n"
2. **Given** `TEST S A="X",B="Y" W A,B,! Q`, **When** generated and executed, **Then** output is "XY\n"

---

### User Story 8 - WRITE Format Controls (Priority: P1)

As a developer, when I generate Python from MUMPS code with WRITE format controls (`!`, `#`, `?n`, `*n`), the code generator produces Python that formats output correctly.

**Why this priority**: Format controls are essential for readable output and report generation.

**Independent Test**: Verify format controls produce correct output formatting.

**YottaDB Verified Behavior**:
```
W "A",!,"B" → "A\nB"
W "X",?10,"Y" → "X         Y" (Y at column 10)
W *65,*66,*67 → "ABC" (ASCII codes)
```

**Acceptance Scenarios**:

1. **Given** `TEST W "A",!,"B",! Q`, **When** generated and executed, **Then** output is "A\nB\n"
2. **Given** `TEST W "X",?10,"Y",! Q`, **When** generated and executed, **Then** output is "X         Y\n" (Y at column 10)
3. **Given** `TEST W *65,*66,*67,! Q`, **When** generated and executed, **Then** output is "ABC\n" (chr(65), chr(66), chr(67))
4. **Given** `TEST W "Line1",#,"Page2",! Q`, **When** generated and executed, **Then** output contains form feed character

---

### User Story 9 - Postconditions (Priority: P1)

As a developer, when I generate Python from MUMPS code with postconditions (`S:cond X=1`), the code generator produces conditional Python statements that only execute when the condition is true.

**Why this priority**: Postconditions are used throughout MUMPS for concise conditional execution.

**Independent Test**: Verify postconditions control statement execution correctly.

**YottaDB Verified Behavior**:
```
S:1 X=1 → X is set to 1 (condition true)
S:0 Y=2 → Y is not set (condition false)
```

**Acceptance Scenarios**:

1. **Given** `TEST S:1 X=1 W X,! Q`, **When** generated and executed, **Then** output is "1\n"
2. **Given** `TEST S:0 X=1 W $G(X,"none"),! Q`, **When** generated and executed, **Then** output is "none\n" (X not set)
3. **Given** `TEST S A=5 S:A>3 B=1 W $G(B,"none"),! Q`, **When** generated and executed, **Then** output is "1\n"
4. **Given** `TEST S A=2 S:A>3 B=1 W $G(B,"none"),! Q`, **When** generated and executed, **Then** output is "none\n"

---

### User Story 10 - NEW Command (Selective) (Priority: P2)

As a developer, when I generate Python from MUMPS code with NEW commands, the code generator produces Python that creates proper variable scope boundaries.

**Why this priority**: NEW is essential for proper variable scoping in subroutines.

**Independent Test**: Verify NEW creates local scope and restores on exit.

**YottaDB Verified Behavior**:
```
S X=5 N X W $G(X,"empty") → "empty" (X is undefined after NEW)
```

**Acceptance Scenarios**:

1. **Given** `TEST S X=5 N X W $G(X,"empty"),! Q`, **When** generated and executed, **Then** output is "empty\n"
2. **Given** `TEST S X=1,Y=2 N X,Y W $G(X,"x"),$G(Y,"y"),! Q`, **When** generated and executed, **Then** output is "xy\n"

---

### User Story 11 - KILL Command (Selective) (Priority: P2)

As a developer, when I generate Python from MUMPS code with KILL commands, the code generator produces Python that deletes variables correctly.

**Why this priority**: KILL is essential for memory management and variable cleanup.

**Independent Test**: Verify KILL deletes variables and their descendants.

**YottaDB Verified Behavior**:
```
S X=5 K X W $G(X,"gone") → "gone"
```

**Acceptance Scenarios**:

1. **Given** `TEST S X=5 K X W $G(X,"gone"),! Q`, **When** generated and executed, **Then** output is "gone\n"
2. **Given** `TEST S X=1,Y=2 K X,Y W $G(X,"x"),$G(Y,"y"),! Q`, **When** generated and executed, **Then** output is "xy\n"
3. **Given** `TEST S A(1)=1,A(2)=2 K A(1) W $G(A(1),"k"),$G(A(2),"k"),! Q`, **When** generated and executed, **Then** output is "k2\n"

---

### User Story 12 - Exclusive NEW and KILL (Priority: P3)

As a developer, when I generate Python from MUMPS code with exclusive NEW/KILL (`N (X,Y)`, `K (X,Y)`), the code generator produces Python that operates on all variables except the specified ones.

**Why this priority**: Exclusive forms are less common but used in utility routines for scope isolation.

**Independent Test**: Verify exclusive operations affect all except listed variables.

**YottaDB Verified Behavior**:
```
S X=1,Y=2 N (X) W $G(X,"x"),$G(Y,"y") → "1y" (X kept, Y NEW'd)
S X=1,Y=2,Z=3 K (X) W $G(X,"x"),$G(Y,"y"),$G(Z,"z") → "1yz" (X kept, Y,Z killed)
```

**Acceptance Scenarios**:

1. **Given** `TEST S X=1,Y=2 N (X) S Z=3 W $G(X,"none"),$G(Y,"none"),$G(Z,"none"),! Q`, **When** generated and executed, **Then** output is "1none3\n"
2. **Given** `TEST S X=1,Y=2,Z=3 K (X) W $G(X,"none"),$G(Y,"none"),$G(Z,"none"),! Q`, **When** generated and executed, **Then** output is "1nonenone\n"

---

### User Story 13 - MERGE Command (Priority: P2)

As a developer, when I generate Python from MUMPS code with MERGE command, the code generator produces Python that copies variable subtrees correctly.

**Why this priority**: MERGE is used for efficient array copying and data structure manipulation.

**Independent Test**: Verify MERGE copies array structure including all descendants.

**YottaDB Verified Behavior**:
```
S A(1)=1,A(2)=2,A(3)=3 M B=A W B(1),B(2),B(3) → "123"
```

**Acceptance Scenarios**:

1. **Given** `TEST S A(1)=1,A(2)=2,A(3)=3 M B=A W B(1),B(2),B(3),! Q`, **When** generated and executed, **Then** output is "123\n"
2. **Given** `TEST S ^G(1)=1,^G(2)=2 M L=^G W L(1),L(2),! Q`, **When** generated and executed, **Then** output is "12\n" (global to local)

---

### User Story 14 - HANG Command (Priority: P3)

As a developer, when I generate Python from MUMPS code with HANG command, the code generator produces Python that pauses execution for the specified time.

**Why this priority**: HANG is used for timed delays in interactive applications.

**Independent Test**: Verify HANG pauses execution (timing not critical for functional test).

**YottaDB Verified Behavior**:
```
H 0.1 W "done" → pauses briefly, then outputs "done"
```

**Acceptance Scenarios**:

1. **Given** `TEST H 0.1 W "done",! Q`, **When** generated and executed, **Then** output is "done\n" (after brief pause)
2. **Given** `TEST S T=$H H 0.5 W "ok",! Q`, **When** generated and executed, **Then** output is "ok\n"

---

### User Story 15 - HALT Command (Priority: P3)

As a developer, when I generate Python from MUMPS code with HALT command, the code generator produces Python that terminates execution.

**Why this priority**: HALT is used for clean program termination.

**Independent Test**: Verify HALT terminates program execution.

**Acceptance Scenarios**:

1. **Given** `TEST W "before",! H W "after",! Q`, **When** generated and executed, **Then** output is "before\n" only (HALT prevents "after")

---

### User Story 16 - Special Variables (Priority: P2)

As a developer, when I generate Python from MUMPS code with special variables ($HOROLOG, $JOB, $IO, $X, $Y, $STORAGE, $STACK, $QUIT), the code generator produces Python that provides correct values.

**Why this priority**: Special variables are used for system information, timestamps, and I/O tracking.

**Independent Test**: Verify each special variable returns appropriate values.

**YottaDB Verified Behavior**:
```
$H → "67585,77643" (days since epoch,seconds since midnight)
$J → process ID (integer)
$IO → current device name
$X → current column position
$Y → current line position
$STORAGE → available memory (large integer)
$STACK → call stack level (0 at main)
$Q → 0 in main context, 1 in extrinsic
```

**Acceptance Scenarios**:

1. **Given** `TEST W $H,! Q`, **When** generated and executed, **Then** output matches "NNNNN,NNNNN" format (comma-separated integers)
2. **Given** `TEST W $J,! Q`, **When** generated and executed, **Then** output is a positive integer
3. **Given** `TEST W $IO,! Q`, **When** generated and executed, **Then** output is a valid device name (e.g., "0" or "/dev/tty")
4. **Given** `TEST W "ABC" W $X,! Q`, **When** generated and executed, **Then** output is "ABC3\n" ($X = 3 after writing 3 chars)
5. **Given** `TEST W $STACK,! Q`, **When** generated and executed, **Then** output is "0\n" (at main level)
6. **Given** `TEST W $STORAGE,! Q`, **When** generated and executed, **Then** output is a large positive integer
7. **Given** `TEST W $Q,! Q`, **When** generated and executed, **Then** output is "0\n" (not in extrinsic)
8. **Given** `TEST W $$SUB,! Q` with `SUB() Q $Q`, **When** generated and executed, **Then** output is "1\n" ($QUIT=1 in extrinsic)

---

### User Story 17 - Decimal Numeric Literals (Priority: P1)

As a developer, when I generate Python from MUMPS code with decimal numeric literals, the code generator produces correct Python floating-point values.

**Why this priority**: Decimal literals are parsed but need codegen support for correct representation.

**Independent Test**: Verify decimal literals work in arithmetic operations.

**YottaDB Verified Behavior**:
```
1.5+2.7 → 4.2
3.14*2 → 6.28
```

**Acceptance Scenarios**:

1. **Given** `TEST W 1.5+2.7,! Q`, **When** generated and executed, **Then** output is "4.2\n"
2. **Given** `TEST W 3.14*2,! Q`, **When** generated and executed, **Then** output is "6.28\n"
3. **Given** `TEST S X=.5 W X+X,! Q`, **When** generated and executed, **Then** output is "1\n"

---

### User Story 18 - READ Command (Priority: P3)

As a developer, when I generate Python from MUMPS code with READ command, the code generator produces Python that reads input from the user.

**Why this priority**: READ is essential for interactive applications but requires I/O infrastructure.

**Independent Test**: Verify READ reads input into variables.

**Acceptance Scenarios**:

1. **Given** `TEST R X W X,! Q` with stdin "hello", **When** generated and executed, **Then** output includes "hello"
2. **Given** `TEST R X:1 W $G(X,"timeout"),! Q` with no input, **When** generated and executed, **Then** output is "timeout\n" and $TEST is set to 0 (X remains undefined on timeout)

---

### Edge Cases

- **Left-to-right evaluation**: `1&1!0` evaluates as `(1&1)!0 = 1`, not `1&(1!0)`
- **Empty string truth value**: `""&1` evaluates as `0&1 = 0` (empty string is falsy)
- **Pattern match with negation**: `X'?1N` is NOT (pattern match)
- **KILL of undefined variable**: Should not error, just no-op
- **NEW of undefined variable**: Creates new local undefined variable
- **Column position tracking**: $X must track actual output position including newlines
- **MERGE overwrites existing**: Target subtree is replaced, not merged

## Requirements *(mandatory)*

### Functional Requirements

#### Extended Operators

- **FR-001**: System MUST generate Python code for logical AND (`&`) that produces MUMPS-compatible boolean results
- **FR-002**: System MUST generate Python code for logical OR (`!`) that produces MUMPS-compatible boolean results
- **FR-003**: System MUST generate Python code for logical NOT (`'`) as unary prefix operator
- **FR-004**: System MUST generate Python code for string concatenation (`_`) that joins operands as strings
- **FR-005**: System MUST generate Python code for contains operator (`[`) that checks substring presence
- **FR-006**: System MUST generate Python code for follows operator (`]`) that compares string collation (ASCII byte ordering; numeric strings compare as strings, not numbers)
- **FR-007**: System MUST generate Python code for modulo (`#`) that produces correct remainder
- **FR-008**: System MUST generate Python code for integer division (`\`) that produces truncated quotient
- **FR-009**: System MUST generate Python code for negated comparison operators (`'=`, `'<`, `'>`)
- **FR-010**: System MUST generate Python code for pattern match operator (`?`) using regex translation

#### Extended Statements

- **FR-011**: System MUST generate Python code for SET with multiple assignments on one line
- **FR-012**: System MUST generate Python code for WRITE with format control `!` (newline)
- **FR-013**: System MUST generate Python code for WRITE with format control `#` (form feed)
- **FR-014**: System MUST generate Python code for WRITE with format control `?n` (tab to column)
- **FR-015**: System MUST generate Python code for WRITE with format control `*n` (ASCII character)
- **FR-016**: System MUST generate Python code for postconditions on all commands (`S:cond X=1`)
- **FR-017**: System MUST generate Python code for selective NEW command (`N X,Y`)
- **FR-018**: System MUST generate Python code for selective KILL command (`K X,Y`)
- **FR-019**: System MUST generate Python code for exclusive NEW command (`N (X,Y)`)
- **FR-020**: System MUST generate Python code for exclusive KILL command (`K (X,Y)`)
- **FR-021**: System MUST generate Python code for MERGE command that copies variable subtrees
- **FR-022**: System MUST generate Python code for HANG command using Python sleep
- **FR-023**: System MUST generate Python code for HALT command (argumentless H) that terminates execution
- **FR-024**: System MUST generate Python code for READ command with optional timeout

#### Special Variables

- **FR-025**: System MUST generate Python code for $HOROLOG that returns days,seconds format
- **FR-026**: System MUST generate Python code for $JOB that returns process ID
- **FR-027**: System MUST generate Python code for $IO that returns current device name
- **FR-028**: System MUST generate Python code for $X that returns current column position
- **FR-029**: System MUST generate Python code for $Y that returns current line position
- **FR-030**: System MUST generate Python code for $STORAGE that returns available memory indication
- **FR-031**: System MUST generate Python code for $STACK that returns call stack level
- **FR-032**: System MUST generate Python code for $QUIT that returns 1 in extrinsic, 0 otherwise

#### Numeric Literals

- **FR-033**: System MUST generate Python code for decimal numeric literals (e.g., 3.14, .5, 1.0)

### Key Entities

- **FormatControlType**: Enum (NEWLINE, FORMFEED, TAB, CHARCODE) for WRITE format controls
- **MFormatControl**: ASG node for format control elements in WRITE/READ
- **Special Variable**: Runtime-tracked values like $X, $Y, $STACK for I/O and call state

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All extended operators produce output matching YottaDB reference for the same input expressions
- **SC-002**: All format controls produce correctly formatted output matching YottaDB behavior
- **SC-003**: NEW and KILL commands correctly manage variable scope and visibility
- **SC-004**: Special variables return values consistent with MUMPS semantics (platform constraints: $IO returns "0" as principal device instead of YDB's device path; $STORAGE returns Python max int)
- **SC-005**: All acceptance scenarios pass with 100% success rate
- **SC-006**: Existing test suite continues to pass (no regressions)
- **SC-007**: Pattern match operator correctly translates MUMPS patterns to Python regex

## Scope Boundaries

### In Scope

1. **Extended operators**: `&`, `!`, `'`, `_`, `[`, `]`, `]]`, `#`, `\`, `?`, `'=`, `'<`, `'>`
2. **Multiple SET assignments**: `S X=1,Y=2,Z=3`
3. **WRITE format controls**: `!`, `#`, `?n`, `*n`
4. **Postconditions**: `:condition` on any command
5. **Selective NEW/KILL**: `N X,Y` and `K X,Y`
6. **Exclusive NEW/KILL**: `N (X,Y)` and `K (X,Y)`
7. **MERGE command**: `M dest=src`
8. **HANG command**: `H seconds`
9. **HALT command**: Argumentless `H`
10. **READ command**: Basic `R X` and `R X:timeout`
11. **Special variables**: $HOROLOG, $JOB, $IO, $X, $Y, $STORAGE, $STACK, $QUIT
12. **Decimal numeric literals**: Codegen for parsed decimals

### Out of Scope

1. **Indirection** - Covered in Spec 012
2. **XECUTE command** - Covered in Spec 012
3. **$TEST special variable** - Already covered in Spec 005
4. **Global variables** - Already covered in Spec 009
5. **Intrinsic functions** - Already covered in Spec 010
6. **External calls** - Already covered in Spec 008
7. **LOCK, OPEN, CLOSE, USE** - I/O device management (future spec)
8. **JOB command** - Process spawning (future spec)
9. **TSTART/TCOMMIT/TROLLBACK** - Transaction processing (future spec)
10. **$ZVERSION, $ZSYSTEM** - Implementation-specific special variables (future spec)
11. **READ with fixed length** - `R X#n` (may be added later)
12. **READ single character** - `R *X` (may be added later)

## Assumptions

1. **Pattern compiler exists**: The `compile_pattern_to_regex()` function in `analysis/pattern_compiler.py` already translates MUMPS patterns to Python regex strings (supports A, C, E, L, N, P, U pattern codes)
2. **MArray infrastructure**: From Spec 009, MArray class handles tree structure for MERGE
3. **Format control ASG**: `MFormatControl` and `FormatControlType` exist in the ASG (verified in asg/expressions.py)
4. **Postcondition ASG**: `stmt.postcondition` field exists on MStatement (verified in semantic analyzer)
5. **Special variable handling**: May require runtime (`_rt`) support for dynamic values like $X, $Y
6. **$HOROLOG calculation**: Will use Python datetime with epoch offset for compatibility
7. **$STORAGE returns max int**: Python doesn't have fixed memory limits; return large value for compatibility

## Dependencies

1. **Spec 009** (MArray, globals) must be complete for MERGE command
2. **Spec 010** (intrinsic functions) must be complete for validation tests using $GET
3. **Pattern compiler** in `analysis/pattern_compiler.py` must be functional
4. **Runtime infrastructure** for $X, $Y column/line tracking
