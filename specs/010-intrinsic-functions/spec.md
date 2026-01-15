# Feature Specification: Intrinsic Functions

**Feature Branch**: `010-intrinsic-functions`  
**Created**: 2026-01-14  
**Status**: Draft  
**Input**: Spec 010 from codegen-plan.md - Intrinsic Functions

## Overview

This specification implements **all MUMPS intrinsic functions** — a large volume of well-defined functions with clear ANSI semantics. Now that globals and MArray are available from Spec 009, implement all intrinsic functions used in MUMPS code.

Intrinsic functions are built-in functions prefixed with `$` (e.g., `$LENGTH`, `$PIECE`, `$GET`). Each function has both a full name and an abbreviation (e.g., `$L` for `$LENGTH`, `$P` for `$PIECE`).

**Scope**: This spec covers:
1. **String Functions** - Text manipulation ($PIECE, $LENGTH, $EXTRACT, $FIND, $TRANSLATE, $JUSTIFY, $CHAR, $ASCII, $REVERSE, $FNUMBER)
2. **Numeric Functions** - Random number generation ($RANDOM)
3. **Data Functions** - Variable existence and retrieval ($DATA, $GET, $ORDER, $QUERY)
4. **Array Utility Functions** - Name manipulation ($NAME, $QLENGTH, $QSUBSCRIPT)
5. **Conditional Functions** - Value selection ($SELECT)
6. **Extrinsic Functions** - User-defined function calls ($$label, $$label^routine)
7. **Upgrade offset evaluator** - Add intrinsic function support to computed offsets

**Note**: $TEXT is already implemented in Spec 008. Extrinsic function support is partially implemented but needs completion.

## Pre-requisites from Spec 009

The following infrastructure is required:

- **MArray class**: MUMPS array structure where nodes can have both value AND children
- **Global variable infrastructure**: `^name` and `^name(sub1,sub2,...)` access
- **Subscripted local variables**: `X(1,2)` using MArray
- **GlobalStorageBackend protocol**: Abstraction for global storage (InMemory, YottaDB, IRIS)

### Infrastructure Expected from Spec 009

| Component | Description |
|-----------|-------------|
| `MArray` | MUMPS array class with `value` and `children` at each node |
| `GlobalStorageBackend` | Protocol for global variable storage |
| `InMemoryGlobalStorage` | Test/sandbox global storage using MArray |
| `_rt.get_global()` | Runtime global variable read |
| `_rt.set_global()` | Runtime global variable write |
| Subscripted local variables | `_scope['A'].get(1,2)` or `state.A.get(1,2)` pattern |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - String Length and Piece Count (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$LENGTH` / `$L`, the code generator produces working Python that returns string length or piece count.

**Why this priority**: $LENGTH is one of the most commonly used functions. Without it, basic string processing is impossible.

**Independent Test**: Can be tested with simple string length and piece count operations.

**YottaDB Verified Behavior**:
```
$L("HELLO") → 5
$L("A^B^C","^") → 3
$L("^A^B^","^") → 4
$L("") → 0
```

**Acceptance Scenarios**:

1. **Given** `TEST W $L("HELLO"),! Q`, **When** generated and executed, **Then** output is "5\n"
2. **Given** `TEST W $L("A^B^C","^"),! Q`, **When** generated and executed, **Then** output is "3\n" (piece count)
3. **Given** `TEST W $L(""),! Q`, **When** generated and executed, **Then** output is "0\n" (empty string)
4. **Given** `TEST W $L("^A^B^","^"),! Q`, **When** generated and executed, **Then** output is "4\n" (leading/trailing delimiters count)

---

### User Story 2 - Piece Extraction (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$PIECE` / `$P`, the code generator produces working Python that extracts delimited pieces.

**Why this priority**: $PIECE is the primary data parsing function in MUMPS. VistA stores data as delimited strings, making $PIECE essential.

**Independent Test**: Extract individual pieces and ranges from delimited strings.

**YottaDB Verified Behavior**:
```
$P("A^B^C","^",2) → "B"
$P("A^B^C","^",2,3) → "B^C"
$P("","^",2) → ""
$P("A","^",3) → ""
```

**Acceptance Scenarios**:

1. **Given** `TEST W $P("A^B^C","^",2),! Q`, **When** generated and executed, **Then** output is "B\n"
2. **Given** `TEST W $P("A^B^C","^",2,3),! Q`, **When** generated and executed, **Then** output is "B^C\n" (piece range)
3. **Given** `TEST W $P("A^B^C","^",1),! Q`, **When** generated and executed, **Then** output is "A\n" (first piece)
4. **Given** `TEST W $P("A","^",3),! Q`, **When** generated and executed, **Then** output is "\n" (piece beyond last returns empty)
5. **Given** `TEST W $P("","^",2),! Q`, **When** generated and executed, **Then** output is "\n" (empty string returns empty)

---

### User Story 3 - Substring Extraction (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$EXTRACT` / `$E`, the code generator produces working Python that extracts substrings.

**Why this priority**: $EXTRACT is fundamental for character-level string manipulation.

**Independent Test**: Extract single characters and character ranges.

**YottaDB Verified Behavior**:
```
$E("HELLO") → "H"
$E("HELLO",2) → "E"
$E("HELLO",2,4) → "ELL"
$E("HELLO",0) → ""
$E("HELLO",100) → ""
$E("",1) → ""
```

**Acceptance Scenarios**:

1. **Given** `TEST W $E("HELLO"),! Q`, **When** generated and executed, **Then** output is "H\n" (first char default)
2. **Given** `TEST W $E("HELLO",2),! Q`, **When** generated and executed, **Then** output is "E\n" (2nd char)
3. **Given** `TEST W $E("HELLO",2,4),! Q`, **When** generated and executed, **Then** output is "ELL\n" (range)
4. **Given** `TEST W $E("HELLO",0),! Q`, **When** generated and executed, **Then** output is "\n" (position 0 returns empty)
5. **Given** `TEST W $E("HELLO",100),! Q`, **When** generated and executed, **Then** output is "\n" (beyond string returns empty)
6. **Given** `TEST W $E("HELLO",-1),! Q`, **When** generated and executed, **Then** output is "\n" (negative position returns empty)

---

### User Story 4 - Find Substring (Priority: P2)

As a developer, when I generate Python from MUMPS code with `$FIND` / `$F`, the code generator produces working Python that finds substrings and returns position after match.

**Why this priority**: $FIND is used for string searching. Returns position AFTER the match, not the match position.

**Independent Test**: Find substrings with and without start position.

**YottaDB Verified Behavior**:
```
$F("HELLO","LL") → 5 (position after "LL")
$F("HELLO","X") → 0 (not found)
$F("HELLO","L",4) → 5 (start searching at position 4)
```

**Acceptance Scenarios**:

1. **Given** `TEST W $F("HELLO","LL"),! Q`, **When** generated and executed, **Then** output is "5\n" (position after match)
2. **Given** `TEST W $F("HELLO","X"),! Q`, **When** generated and executed, **Then** output is "0\n" (not found)
3. **Given** `TEST W $F("HELLO","L",4),! Q`, **When** generated and executed, **Then** output is "5\n" (start at position 4)
4. **Given** `TEST W $F("HELLO",""),! Q`, **When** generated and executed, **Then** output is "1\n" (empty string found at start)

---

### User Story 5 - Character Translation (Priority: P2)

As a developer, when I generate Python from MUMPS code with `$TRANSLATE` / `$TR`, the code generator produces working Python that performs character-by-character translation or deletion.

**Why this priority**: $TRANSLATE is used for character set transformations and cleanup.

**Independent Test**: Translate characters and delete characters.

**YottaDB Verified Behavior**:
```
$TR("HELLO","EL","123") → "H122O"
$TR("HELLO","L") → "HEO" (delete L's)
```

**Acceptance Scenarios**:

1. **Given** `TEST W $TR("HELLO","EL","123"),! Q`, **When** generated and executed, **Then** output is "H122O\n" (translate E→1, L→2, extra 3 ignored)
2. **Given** `TEST W $TR("HELLO","L"),! Q`, **When** generated and executed, **Then** output is "HEO\n" (delete all L's)
3. **Given** `TEST W $TR("HELLO","HO","XY"),! Q`, **When** generated and executed, **Then** output is "XELLY\n"

---

### User Story 6 - ASCII/Character Conversion (Priority: P2)

As a developer, when I generate Python from MUMPS code with `$ASCII` / `$A` and `$CHAR` / `$C`, the code generator produces working Python for ASCII value conversion.

**Why this priority**: ASCII manipulation is used for character encoding and control character handling.

**Independent Test**: Convert characters to/from ASCII values.

**YottaDB Verified Behavior**:
```
$A("ABC") → 65
$A("ABC",2) → 66
$A("") → -1
$A("A",0) → -1
$A("A",5) → -1
$C(65) → "A"
$C(65,66,67) → "ABC"
```

**Acceptance Scenarios**:

1. **Given** `TEST W $A("ABC"),! Q`, **When** generated and executed, **Then** output is "65\n" (first char ASCII)
2. **Given** `TEST W $A("ABC",2),! Q`, **When** generated and executed, **Then** output is "66\n" (position 2)
3. **Given** `TEST W $A(""),! Q`, **When** generated and executed, **Then** output is "-1\n" (empty string)
4. **Given** `TEST W $A("A",0),! Q`, **When** generated and executed, **Then** output is "-1\n" (position 0)
5. **Given** `TEST W $A("A",5),! Q`, **When** generated and executed, **Then** output is "-1\n" (beyond string)
6. **Given** `TEST W $C(65),! Q`, **When** generated and executed, **Then** output is "A\n"
7. **Given** `TEST W $C(65,66,67),! Q`, **When** generated and executed, **Then** output is "ABC\n" (multiple codes)
8. **Given** `TEST W $C(-1),! Q`, **When** generated and executed, **Then** output is "\n" (negative code returns empty string)
9. **Given** `TEST W $C(256),! Q`, **When** generated and executed, **Then** output is "Ā\n" (Unicode chr(256))

---

### User Story 7 - Random Number Generation (Priority: P2)

As a developer, when I generate Python from MUMPS code with `$RANDOM` / `$R`, the code generator produces working Python that generates random integers.

**Why this priority**: $RANDOM is used for temporary file names, session IDs, and randomized selection.

**Independent Test**: Generate random numbers and verify range.

**YottaDB Verified Behavior**:
```
$R(10) → integer 0-9 (varies each call)
```

**Acceptance Scenarios**:

1. **Given** `TEST S X=$R(10) W X>=0&(X<10),! Q`, **When** generated and executed, **Then** output is "1\n" (in range 0-9)
2. **Given** `TEST W $R(1),! Q`, **When** generated and executed, **Then** output is "0\n" ($R(1) always returns 0)

---

### User Story 8 - Variable Existence Check (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$DATA` / `$D`, the code generator produces working Python that checks variable existence status.

**Why this priority**: $DATA is fundamental for checking if variables/globals exist before accessing them.

**Independent Test**: Check various variable states (undefined, value only, descendants only, both).

**YottaDB Verified Behavior**:
```
S A=1 W $D(A) → 1 (value only)
S B(1)=2 W $D(B) → 10 (descendants only)
S C=1,C(1)=2 W $D(C) → 11 (value and descendants)
W $D(UNDEF) → 0 (undefined)
```

**Acceptance Scenarios**:

1. **Given** `TEST W $D(UNDEF),! Q`, **When** generated and executed, **Then** output is "0\n" (undefined)
2. **Given** `TEST S A=1 W $D(A),! Q`, **When** generated and executed, **Then** output is "1\n" (value only)
3. **Given** `TEST S B(1)=2 W $D(B),! Q`, **When** generated and executed, **Then** output is "10\n" (descendants only)
4. **Given** `TEST S C=1,C(1)=2 W $D(C),! Q`, **When** generated and executed, **Then** output is "11\n" (value and descendants)

---

### User Story 9 - Safe Variable Retrieval (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$GET` / `$G`, the code generator produces working Python that safely retrieves variable values with defaults.

**Why this priority**: $GET prevents errors when accessing potentially undefined variables.

**Independent Test**: Get defined, undefined, and empty variables with and without defaults.

**YottaDB Verified Behavior**:
```
S X="" W $G(X,"DEF") → "" (empty string is defined, returns it)
K Y W $G(Y,"DEF") → "DEF" (undefined uses default)
S Z="VAL" W $G(Z,"DEF") → "VAL"
```

**Acceptance Scenarios**:

1. **Given** `TEST K X W $G(X),! Q`, **When** generated and executed, **Then** output is "\n" (undefined, empty default)
2. **Given** `TEST K X W $G(X,"DEF"),! Q`, **When** generated and executed, **Then** output is "DEF\n" (undefined with default)
3. **Given** `TEST S X="" W $G(X,"DEF"),! Q`, **When** generated and executed, **Then** output is "\n" (empty string is defined)
4. **Given** `TEST S X="VAL" W $G(X,"DEF"),! Q`, **When** generated and executed, **Then** output is "VAL\n" (defined value)

---

### User Story 10 - Array Traversal with $ORDER (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$ORDER` / `$O`, the code generator produces working Python that traverses array subscripts in collation order.

**Why this priority**: $ORDER is the primary mechanism for iterating through arrays and globals.

**Independent Test**: Traverse array subscripts forward and backward.

**YottaDB Verified Behavior**:
```
S A(1)="X",A(3)="Y",A(2)="Z"
$O(A("")) → "1" (first key)
$O(A(1)) → "2"
$O(A(3)) → "" (no more keys)
$O(A(""),-1) → "3" (last key, reverse)
```

**Acceptance Scenarios**:

1. **Given** `TEST S A(1)=1,A(3)=3,A(2)=2 W $O(A("")),! Q`, **When** generated and executed, **Then** output is "1\n" (first subscript)
2. **Given** `TEST S A(1)=1,A(3)=3,A(2)=2 W $O(A(1)),! Q`, **When** generated and executed, **Then** output is "2\n" (next after 1)
3. **Given** `TEST S A(1)=1,A(3)=3 W $O(A(3)),! Q`, **When** generated and executed, **Then** output is "\n" (no more keys)
4. **Given** `TEST S A(1)=1,A(3)=3 W $O(A(""),-1),! Q`, **When** generated and executed, **Then** output is "3\n" (reverse order)

---

### User Story 11 - Tree Traversal with $QUERY (Priority: P2)

As a developer, when I generate Python from MUMPS code with `$QUERY` / `$Q`, the code generator produces working Python that returns the full reference of the next node.

**Why this priority**: $QUERY traverses multi-level arrays depth-first, returning full subscript paths.

**Independent Test**: Traverse multi-level array and get full references.

**YottaDB Verified Behavior**:
```
S A(1,1)="X",A(1,2)="Y",A(2,1)="Z"
$Q(A("")) → "A(1,1)"
$Q(A(1,1)) → "A(1,2)"
$Q(A(2,1)) → "" (no more nodes)
```

**Acceptance Scenarios**:

1. **Given** `TEST S A(1,1)=1,A(1,2)=2,A(2,1)=3 W $Q(A("")),! Q`, **When** generated and executed, **Then** output is "A(1,1)\n"
2. **Given** `TEST S A(1,1)=1,A(1,2)=2 W $Q(A(1,1)),! Q`, **When** generated and executed, **Then** output is "A(1,2)\n"
3. **Given** `TEST S A(1)=1 W $Q(A(1)),! Q`, **When** generated and executed, **Then** output is "\n" (no more nodes)

---

### User Story 12 - Conditional Selection (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$SELECT` / `$S`, the code generator produces working Python that evaluates conditions left-to-right and returns the value for the first true condition.

**Why this priority**: $SELECT is the MUMPS equivalent of conditional expressions, heavily used throughout VistA.

**Independent Test**: Select based on various conditions.

**YottaDB Verified Behavior**:
```
$S(1=1:"ONE",1:"DEFAULT") → "ONE"
$S(1=0:"ONE",2=2:"TWO",1:"DEFAULT") → "TWO"
$S(0:"A") → ERROR (no true condition)
```

**Acceptance Scenarios**:

1. **Given** `TEST W $S(1=1:"ONE",1:"DEF"),! Q`, **When** generated and executed, **Then** output is "ONE\n" (first true)
2. **Given** `TEST W $S(1=0:"ONE",2=2:"TWO",1:"DEF"),! Q`, **When** generated and executed, **Then** output is "TWO\n" (second true)
3. **Given** `TEST W $S(0=0:"ZERO",1:"DEF"),! Q`, **When** generated and executed, **Then** output is "ZERO\n" (0=0 is true)
4. **Given** `TEST W $S(0:"A"),! Q`, **When** generated and executed, **Then** raises SELECTFALSE error (no true condition)

---

### User Story 13 - Extrinsic Functions (Priority: P1)

As a developer, when I generate Python from MUMPS code with `$$label` or `$$label^routine`, the code generator produces working Python that calls user-defined functions and returns values.

**Why this priority**: Extrinsic functions are user-defined functions, essential for code organization and reuse.

**Independent Test**: Call local and external extrinsic functions with parameters.

**YottaDB Verified Behavior**:
```
W $$DOUBLE(21) → 42 (where DOUBLE(N) Q N*2)
W $$ADD(3,5) → 8 (where ADD(A,B) Q A+B)
```

**Acceptance Scenarios**:

1. **Given** routine with `TEST W $$DBL(21),! Q` and `DBL(N) Q N*2`, **When** generated and executed, **Then** output is "42\n"
2. **Given** routine with `TEST W $$ADD(3,5),! Q` and `ADD(A,B) Q A+B`, **When** generated and executed, **Then** output is "8\n"
3. **Given** `TEST S X=$$EXT^helper(10) W X,! Q` with helper routine, **When** generated and executed, **Then** returns correct value from external routine

---

### User Story 14 - Array Name Functions (Priority: P3)

As a developer, when I generate Python from MUMPS code with `$NAME` / `$NA`, `$QLENGTH` / `$QL`, and `$QSUBSCRIPT` / `$QS`, the code generator produces working Python for manipulating array name strings.

**Why this priority**: Less commonly used but needed for dynamic array manipulation in VistA.

**Independent Test**: Convert array references to/from string names.

**YottaDB Verified Behavior**:
```
S A(1,2,3)=1
$NA(A) → "A"
$NA(A(1,2,3)) → "A(1,2,3)"
$NA(A(1,2,3),2) → "A(1,2)"
$QL("A(1,2,3)") → 3
$QS("A(1,2,3)",2) → "2"
$QS("A(1,2,3)",0) → "A"
```

**Acceptance Scenarios**:

1. **Given** `TEST W $NA(A),! Q`, **When** generated and executed, **Then** output is "A\n"
2. **Given** `TEST S A(1,2,3)=1 W $NA(A(1,2,3)),! Q`, **When** generated and executed, **Then** output is "A(1,2,3)\n"
3. **Given** `TEST S A(1,2,3)=1 W $NA(A(1,2,3),2),! Q`, **When** generated and executed, **Then** output is "A(1,2)\n" (truncate to depth 2)
4. **Given** `TEST W $QL("A(1,2,3)"),! Q`, **When** generated and executed, **Then** output is "3\n" (subscript count)
5. **Given** `TEST W $QS("A(1,2,3)",2),! Q`, **When** generated and executed, **Then** output is "2\n" (2nd subscript)
6. **Given** `TEST W $QS("A(1,2,3)",0),! Q`, **When** generated and executed, **Then** output is "A\n" (variable name)

---

### User Story 15 - String Formatting Functions (Priority: P3)

As a developer, when I generate Python from MUMPS code with `$JUSTIFY` / `$J`, `$FNUMBER` / `$FN`, and `$REVERSE` / `$RE`, the code generator produces working Python for string formatting.

**Why this priority**: Used for report formatting and display.

**Independent Test**: Format numbers and strings for display.

**YottaDB Verified Behavior**:
```
$J(12,5) → "   12" (right-justify in 5 chars)
$J(12.345,8,2) → "   12.35" (2 decimal places)
$J("X",3) → "  X" (string right-justify)
$FN(12345.67,",") → "12,345.67" (comma grouping)
$FN(-12345.67,"-") → "12345.67" (suppress minus sign)
$RE("HELLO") → "OLLEH"
```

**Acceptance Scenarios**:

1. **Given** `TEST W $J(12,5),! Q`, **When** generated and executed, **Then** output is "   12\n" (right-justify)
2. **Given** `TEST W $J(12.345,8,2),! Q`, **When** generated and executed, **Then** output is "   12.35\n" (with decimals)
3. **Given** `TEST W $J("X",3),! Q`, **When** generated and executed, **Then** output is "  X\n" (string justify)
4. **Given** `TEST W $FN(12345.67,","),! Q`, **When** generated and executed, **Then** output is "12,345.67\n"
5. **Given** `TEST W $RE("HELLO"),! Q`, **When** generated and executed, **Then** output is "OLLEH\n"

---

### Edge Cases

- What happens with `$P(X,D,0)`? → Returns empty string (piece 0 doesn't exist)
- What happens with `$E(X,5,3)` where start > end? → Returns empty string
- What happens with `$S` when no condition is true? → Raises SELECTFALSE error
- What happens with `$A("")`? → Returns -1
- What happens with `$C(-1)` or `$C(256)`? → $C(-1) returns empty string; $C(256) returns chr(256) (Unicode Ā)
- What happens with `$O(A(""),-1)` on empty array? → Returns empty string
- What happens with `$G(^UNDEFINED)`? → Returns empty string (globals can use $G too)
- What happens with `$R(0)`? → Raises RANDARGNEG error (argument must be >= 1)
- What happens with `$F("X","")`? → Returns 1 (empty substring found at position 1)

## Requirements *(mandatory)*

### Functional Requirements

**String Functions:**
- **FR-001**: System MUST implement `$LENGTH(string)` returning character count
- **FR-002**: System MUST implement `$LENGTH(string,delimiter)` returning piece count
- **FR-003**: System MUST implement `$PIECE(string,delimiter,start[,end])` returning delimited pieces
- **FR-004**: System MUST implement `$EXTRACT(string[,start[,end]])` returning substring
- **FR-005**: System MUST implement `$FIND(string,substring[,start])` returning position after match (0 if not found)
- **FR-006**: System MUST implement `$TRANSLATE(string,from[,to])` for character translation/deletion
- **FR-007**: System MUST implement `$JUSTIFY(value,width[,decimals])` for right-justification
- **FR-008**: System MUST implement `$ASCII(string[,position])` returning ASCII code (-1 for invalid)
- **FR-009**: System MUST implement `$CHAR(code,...)` returning characters from ASCII codes
- **FR-010**: System MUST implement `$REVERSE(string)` returning reversed string
- **FR-011**: System MUST implement `$FNUMBER(number,codes[,decimals])` for formatted numeric output

**Numeric Functions:**
- **FR-012**: System MUST implement `$RANDOM(limit)` returning integer 0 to limit-1

**Data Functions:**
- **FR-013**: System MUST implement `$DATA(variable)` returning 0/1/10/11 existence status
- **FR-014**: System MUST implement `$GET(variable[,default])` returning value or default
- **FR-015**: System MUST implement `$ORDER(array(subscripts)[,direction])` returning next/prev subscript
- **FR-016**: System MUST implement `$QUERY(array)` returning full reference of next node

**Array Utility Functions:**
- **FR-017**: System MUST implement `$NAME(variable[,depth])` returning name string
- **FR-018**: System MUST implement `$QLENGTH(name)` returning subscript count
- **FR-019**: System MUST implement `$QSUBSCRIPT(name,position)` returning subscript or name

**Conditional Functions:**
- **FR-020**: System MUST implement `$SELECT(cond1:val1,cond2:val2,...)` with left-to-right evaluation
- **FR-021**: System MUST raise error if no $SELECT condition is true

**Extrinsic Functions:**
- **FR-022**: System MUST support `$$label` calling user-defined functions within routine
- **FR-023**: System MUST support `$$label^routine` calling external routine functions
- **FR-024**: System MUST support by-value and by-reference parameter passing for extrinsics
- **FR-025**: System MUST save/restore $TEST around extrinsic calls (per MUMPS spec)

**Function Name Handling:**
- **FR-026**: System MUST accept both full names and abbreviations (e.g., $L for $LENGTH)
- **FR-027**: System MUST be case-insensitive for function names ($l = $L = $LENGTH)

**Offset Evaluator Upgrade:**
- **FR-028**: Computed offset expressions MUST support intrinsic function calls (e.g., `G LABEL+$L(X)`)

### Key Entities

- **Intrinsic Function**: Built-in MUMPS function prefixed with `$`
- **Extrinsic Function**: User-defined function prefixed with `$$`
- **Function Argument**: Expression passed to function
- **MSelectArg**: Condition:value pair for $SELECT function

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All string functions produce output matching YottaDB for test cases
- **SC-002**: $DATA correctly identifies variable existence states (0, 1, 10, 11)
- **SC-003**: $GET safely retrieves variables with correct default handling
- **SC-004**: $ORDER correctly traverses arrays in forward and reverse collation order
- **SC-005**: $SELECT correctly evaluates conditions and raises error when none true
- **SC-006**: Extrinsic functions correctly call, pass parameters, and return values
- **SC-007**: Function abbreviations work identically to full names
- **SC-008**: MUGJ V1FN* test series produces output matching YottaDB
- **SC-009**: Computed offsets with function calls work correctly (e.g., `G LABEL+$L(X)`)
- **SC-010**: Generated Python remains syntactically valid (`ast.parse()` succeeds)

## Clarifications

### Session 2025-01-14

- Q: How should the generated Python handle MUMPS runtime errors like SELECTFALSE and RANDARGNEG? → A: Raise custom m2py runtime exception (e.g., `MRuntimeError("SELECTFALSE")`)
- Q: How should $CHAR handle invalid ASCII codes like -1 or 256? → A: Match YottaDB behavior exactly: $C(-1) returns empty string, $C(256) returns Unicode chr(256)

## Assumptions

1. Spec 009 infrastructure (MArray, GlobalStorageBackend) is available
2. Basic extrinsic function infrastructure from Spec 008 is available
3. All function semantics follow ANSI MUMPS 1995 standard
4. YottaDB is the reference implementation for edge case behavior
5. Function names are stored in ASG without the `$` prefix (already implemented)
6. $TEXT function is already implemented in Spec 008
7. MUMPS runtime errors are raised as custom `MRuntimeError` exceptions with the error code (e.g., `SELECTFALSE`, `RANDARGNEG`)
8. $CHAR accepts any integer: negative values return empty string, values ≥256 return Unicode characters via Python's chr()

## Explicitly Out of Scope (Deferred to Later Specs)

**Already Implemented (Spec 008):**
- $TEXT function (source line access)

**Spec 011** (Operators, Commands & Completion):
- Special variables ($HOROLOG, $JOB, $IO, $X, $Y, $STACK, $STORAGE, $QUIT)
- Additional commands (READ, NEW, KILL, MERGE, HANG, HALT)
- Extended operators (pattern match, contains, follows)
- Postconditions

**Spec 012** (Indirection & XECUTE):
- Indirect function arguments (`$L(@X)`)
- Function name indirection (`@FN(args)`)
- XECUTE with function calls

## Dependencies

### This Spec Produces (for later specs):

- Complete intrinsic function library (used throughout VistA)
- Extrinsic function call infrastructure (completes Spec 008 partial)
- Offset evaluator with function support (enables complex computed offsets)

### This Spec Consumes (from earlier specs):

- MArray class from Spec 009 (for $DATA, $ORDER, $QUERY on arrays)
- GlobalStorageBackend from Spec 009 (for $DATA, $GET, $ORDER on globals)
- External call infrastructure from Spec 008 (for $$label^routine)
- $TEST save/restore from Spec 005 (for extrinsic function semantics)
- Variable analysis from Spec 005 (for identifying defined vs undefined)
- MIntrinsicFunction ASG node from parser (already exists)
- MSelectArg ASG node from parser (already exists for $SELECT)
