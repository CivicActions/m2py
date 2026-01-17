# Feature Specification: Indirection & XECUTE Runtime

**Feature Branch**: `012-indirection-xecute`  
**Created**: 2026-01-16  
**Status**: Draft  
**Input**: User description: "Indirection & XECUTE Runtime (Dynamic Fallback)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Name Indirection (Priority: P1)

As a MUMPS developer transpiling legacy code, I need to translate code that uses name indirection (`@VAR`) so that dynamic variable names work correctly in Python.

**Why this priority**: Name indirection is the most common form of indirection in VistA code, used extensively for dynamic variable access. Without this, most real-world MUMPS codebases cannot be transpiled.

**Independent Test**: Can be fully tested by setting a variable name in another variable and then using `@` to read/write through it. Delivers immediately testable variable name resolution.

**Acceptance Scenarios**:

1. **Given** `S X="VAR",@X=1`, **When** transpiled and executed, **Then** VAR should equal `1`
2. **Given** `S X="VAR",VAR=5,Y=@X`, **When** transpiled and executed, **Then** Y should equal `5`
3. **Given** `S A="B",B="C",C=100,X=@@A`, **When** transpiled and executed, **Then** X should equal `100` (multi-level indirection: A→B→C→100)
4. **Given** `S NAME="ARRAY" S @NAME@(1,2)=5`, **When** transpiled and executed, **Then** ARRAY(1,2) should equal `5` (name indirection with subscripts using `@name@(subs)` syntax)
5. **Given** a routine that sets `@X=10` then later reads `VAR` directly, **When** X contains `"VAR"`, **Then** both access paths should see value `10`

---

### User Story 2 - XECUTE Command with Constant Strings (Priority: P1)

As a MUMPS developer, I need to transpile code using XECUTE with constant string literals so that inline code execution works correctly.

**Why this priority**: XECUTE with constant strings is common in initialization routines and configuration code. This pattern can be optimized by inlining the transpiled code.

**Independent Test**: Can be tested by transpiling `X "S Y=1"` and verifying Y is set correctly. Delivers immediate XECUTE support for the most common pattern.

**Acceptance Scenarios**:

1. **Given** `X "S X=1"`, **When** transpiled and executed, **Then** X should equal `1`
2. **Given** `X "W 42,!"`, **When** transpiled and executed, **Then** output should be `42` followed by newline
3. **Given** `X "S A=2","S B=3"`, **When** transpiled and executed, **Then** A should equal `2` and B should equal `3` (multiple XECUTE arguments)
4. **Given** `S P=1 X:P=1 "S X=5"`, **When** transpiled and executed, **Then** X should equal `5` (postcondition true)
5. **Given** `S P=0 X:P=1 "S X=5"`, **When** transpiled and executed, **Then** X should be undefined (postcondition false)

---

### User Story 3 - XECUTE Command with Dynamic Code (Priority: P2)

As a MUMPS developer, I need to transpile code using XECUTE with dynamically-constructed code strings so that runtime code generation works.

**Why this priority**: Dynamic XECUTE is used in advanced VistA routines for metaprogramming and configuration. Less common than constant XECUTE but critical for complete language support.

**Independent Test**: Can be tested by transpiling `S CODE="W 42,!" X CODE` and verifying output. Requires runtime MUMPS interpreter integration.

**Acceptance Scenarios**:

1. **Given** `S CODE="W 42,!" X CODE`, **When** transpiled and executed, **Then** output should be `42` followed by newline
2. **Given** code where CODE is constructed via concatenation (`S CODE="S X=" S CODE=CODE_"5" X CODE`), **When** transpiled and executed, **Then** X should equal `5`
3. **Given** `S OUTER=10 X "S INNER=OUTER+1"`, **When** transpiled and executed, **Then** INNER should equal `11` (access to outer scope)
4. **Given** `S OUTER=10 X "S OUTER=99"`, **When** transpiled and executed, **Then** OUTER should equal `99` (modification of outer scope)

---

### User Story 4 - XECUTE $TEST Semantics (Priority: P2)

As a MUMPS developer, I need XECUTE to NOT stack $TEST so that IF/ELSE chains work correctly across XECUTE boundaries.

**Why this priority**: XECUTE has specific $TEST semantics that differ from argumentless DO. Getting this wrong breaks IF/ELSE chains in common VistA patterns.

**Independent Test**: Can be tested by setting $TEST via IF, executing code via XECUTE that changes $TEST, then checking ELSE behavior.

**Acceptance Scenarios**:

1. **Given** `I 1=1 X "I 0=1" E  W "ELSE"`, **When** transpiled and executed, **Then** output should be `ELSE` (XECUTE does NOT stack $TEST)
2. **Given** `I 0=1 X "I 1=1" E  W "ELSE"`, **When** transpiled and executed, **Then** no ELSE output (inner IF set $TEST to true)

---

### User Story 5 - Indirect DO Command (Priority: P2)

As a MUMPS developer, I need to transpile code using indirect DO so that dynamic subroutine dispatch works.

**Why this priority**: Indirect DO is used in dispatching logic and plugin systems in VistA. Required for architectural patterns like menu systems.

**Independent Test**: Can be tested with `S CMD="LABEL" D @CMD` and verifying LABEL is called.

**Acceptance Scenarios**:

1. **Given** `S CMD="LABEL" D @CMD`, **When** transpiled and executed where LABEL writes `"CALLED"`, **Then** output should be `CALLED`
2. **Given** `S RTN="ROUTINE" D LABEL^@RTN`, **When** transpiled and executed, **Then** LABEL in external routine ROUTINE should be called
3. **Given** `S LBL="LABEL",RTN="ROUTINE" D @LBL^@RTN`, **When** transpiled and executed, **Then** LABEL in ROUTINE should be called (both parts indirect)

---

### User Story 6 - Indirect GOTO Command (Priority: P2)

As a MUMPS developer, I need to transpile code using indirect GOTO so that dynamic control flow transfer works.

**Why this priority**: Indirect GOTO is used in error handling and state machine implementations in VistA.

**Independent Test**: Can be tested with `S TARGET="DONE" G @TARGET` and verifying control transfers to DONE.

**Acceptance Scenarios**:

1. **Given** `W "START " S TARGET="DONE" G @TARGET W "SKIPPED"` with label DONE writing `"DONE"`, **When** transpiled and executed, **Then** output should be `START DONE` (SKIPPED not printed)
2. **Given** `S RTN="ROUTINE" G LABEL^@RTN`, **When** transpiled and executed, **Then** control should transfer to LABEL in ROUTINE

---

### User Story 7 - Argument Indirection (Priority: P3)

As a MUMPS developer, I need to transpile SET argument indirection so that dynamic assignment patterns work.

**Why this priority**: SET argument indirection like `S @"X=1,Y=2"` is used in VistA for dynamic multi-variable assignment. Less common than name indirection.

**Independent Test**: Can be tested with `S ARG="X=1" S @ARG` and verifying X equals 1.

**Acceptance Scenarios**:

1. **Given** `S A="X=1" S @A`, **When** transpiled and executed, **Then** X should equal `1`
2. **Given** `S A="X=1",B="Y=2" S @A,@B`, **When** transpiled and executed, **Then** X should equal `1` and Y should equal `2`
3. **Given** `S C="@A,@B",A="X=3",B="Y=4" S @C`, **When** transpiled and executed, **Then** X should equal `3` and Y should equal `4` (nested argument indirection)

---

### User Story 8 - Pattern Indirection (Priority: P3)

As a MUMPS developer, I need to transpile pattern indirection so that dynamic pattern matching works.

**Why this priority**: Pattern indirection allows patterns to be constructed at runtime. Less common but used in validation routines.

**Independent Test**: Can be tested with `S PAT="1N.N" I "123"?@PAT W "MATCH"`.

**Acceptance Scenarios**:

1. **Given** `S PAT="1N.N" I "123"?@PAT W "MATCH"`, **When** transpiled and executed, **Then** output should be `MATCH`
2. **Given** `S PAT="1A.A" I "ABC"?@PAT W "MATCH"`, **When** transpiled and executed, **Then** output should be `MATCH`
3. **Given** `S PAT="1N" I "A"?@PAT W "MATCH"`, **When** transpiled and executed, **Then** no output (pattern doesn't match)

---

### Edge Cases

- **Undefined indirection source**: `S X=@UNDEF` should raise undefined variable error at runtime
- **Invalid variable name in indirection**: `S X="123INVALID",@X=1` should raise runtime error (invalid identifier)
- **XECUTE syntax error**: `X "S X="` should raise syntax error with clear message indicating the XECUTE context
- **Circular indirection**: `S A="B",B="A",X=@@A` - @A evaluates to "B" (value of A), then @@A evaluates to value of variable B which is "A", so X="B" (value of A)
- **Deep multi-level indirection**: `S A="B",B="C",C="D",D=100,X=@@@A` should equal `100` (A→B→C→D→100)
- **Indirection to undefined intermediate**: `S A="B",X=@@A` where B is undefined should error on second @ resolution
- **Indirection in KILL**: `S X="VAR",VAR=1 K @X` should kill VAR
- **Indirection in NEW**: `S X="VAR" N @X` should NEW VAR (save and create new local)

## Requirements *(mandatory)*

### Functional Requirements

#### Name Indirection

- **FR-001**: System MUST translate name indirection expressions (`@VAR`) to runtime variable lookups via `_scope` dictionary
- **FR-002**: System MUST support multi-level indirection (`@@VAR`, `@@@VAR`) by recursively resolving each level
- **FR-003**: System MUST allow indirection in read contexts (`W @X`) and write contexts (`S @X=1`)
- **FR-004**: System MUST support combined name indirection with subscripts using `@name@(subs)` syntax
- **FR-005**: System MUST generate runtime error with variable name when indirected name references undefined variable
- **FR-006**: System MUST support indirection to global variables (`S X="^GLO",@X=1` sets ^GLO)
- **FR-006a**: System MUST support FOR loop variable indirection (`F @A=1:1:10` where A contains loop variable name)

#### XECUTE Command

- **FR-006**: System MUST translate XECUTE commands to execute MUMPS code strings at runtime
- **FR-007**: System MUST support multiple XECUTE arguments executed left-to-right (`X expr1,expr2`)
- **FR-008**: System MUST support postconditions on XECUTE (`X:cond code`)
- **FR-009**: System MUST provide XECUTE code access to enclosing scope variables (read and write)
- **FR-010**: System MUST NOT stack $TEST for XECUTE (mutations visible to caller, unlike argumentless DO)

#### Indirect Control Flow

- **FR-007**: System MUST translate indirect DO (`D @VAR`) to dynamic label dispatch
- **FR-008**: System MUST translate indirect GOTO (`G @VAR`) to dynamic control flow transfer
- **FR-009**: System MUST support partial indirection in external calls (`D LABEL^@RTN`, `D @LBL^ROUTINE`, `D @LBL^@RTN`)
- **FR-010**: System MUST parse indirection target at runtime to extract label and optional routine components
- **FR-011**: System MUST support offsets with indirect DO/GOTO (`D @CMD+5` resolves CMD then adds offset via Spec 007 line dispatch)

#### Argument Indirection

- **FR-012**: System MUST support SET argument indirection (`S @"X=1"`)
- **FR-013**: System MUST support nested argument indirection (`S @A` where A contains `"@B"`)

#### Pattern Indirection

- **FR-014**: System MUST support pattern indirection (`X?@PAT` where PAT contains pattern string)
- **FR-015**: System MUST compile pattern string at runtime when pattern indirection is used

#### Runtime Infrastructure

- **FR-016**: System MUST provide runtime MUMPS code execution by reusing the existing m2py pipeline (parse → ASG → generate Python → exec())
- **FR-017**: System MUST ensure runtime-executed code has same semantics as statically transpiled code (guaranteed by reusing same pipeline)
- **FR-018**: System MUST propagate errors from runtime execution with source context in diagnostics
- **FR-019**: System MUST raise Python exceptions immediately on indirection/XECUTE errors (no trapping), matching MUMPS default untrapped error behavior

### Key Entities

- **MIndirection**: ASG node representing `@expr` with `indirection_type` (NAME, SUBSCRIPT, ARGUMENT, PATTERN)
- **MXecuteStatement**: ASG node with `code_expressions` list and optional postconditions
- **RuntimeEvaluator**: Component that parses and executes MUMPS code strings dynamically
- **IndirectionResolver**: Component that evaluates indirection chains at runtime

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All acceptance scenarios in this spec pass when transpiled and executed
- **SC-002**: MUGJ V1IDNM* test suite (name indirection) passes when transpiled
- **SC-003**: MUGJ V1IDDO* test suite (DO indirection) passes when transpiled
- **SC-004**: MUGJ V1IDGO* test suite (GOTO indirection) passes when transpiled  
- **SC-005**: MUGJ V1XECA* and V1XECB* test suites (XECUTE) pass when transpiled
- **SC-006**: Runtime error messages include the indirection source variable name and value
- **SC-007**: XECUTE with constant strings produces readable Python code when inspected

## Assumptions *(optional)*

- Specs 004-011 are already implemented (control flow, external calls, globals, functions, operators)
- Dict-based variable storage (`_scope`) is in use from Spec 008 external calls
- MUMPSRuntime class exists with `_test` tracking from Spec 005
- Parser populates `MIndirection` and `MXecuteStatement` ASG nodes (verified in existing code)
- Analysis passes mark `requires_runtime_eval=True` on routines containing indirection

## Out of Scope *(optional)*

- **Static indirection optimization**: Constant propagation to inline statically-resolvable indirection is deferred (optimization, not correctness)
- **DO/GOTO argument indirection**: `D LABEL(@ARGS)` where ARGS is an argument list string - complex argument parsing deferred
- **XECUTE sandboxing**: Security restrictions on what code can be XECUTEd
- **XECUTE debugging**: Source mapping, breakpoints in dynamically executed code
- **Performance optimization**: JIT compilation or bytecode caching for XECUTE
- **$ECODE/$ETRAP in XECUTE**: Error handling special variables in dynamic code
- **^%ZOSF patterns**: Platform-specific utility routine lookup table (can be added later as optimization)

## Dependencies *(optional)*

- **Spec 005**: $TEST tracking infrastructure (XECUTE must NOT stack $TEST)
- **Spec 006**: Cross-label GOTO infrastructure (indirect GOTO uses same mechanism)
- **Spec 007**: Line dispatch infrastructure (indirect GOTO with offsets)
- **Spec 008**: External routine loading (indirect calls to external routines)
- **Spec 009**: Global variables (indirection can reference globals)
- **Spec 010**: Intrinsic functions (XECUTE code can call any function)
- **Spec 011**: All operators and commands (XECUTE code can use any construct)

## Risks *(optional)*

- **Runtime interpreter complexity**: XECUTE requires embedding a mini-MUMPS interpreter. Mitigation: reuse existing parser/ASG/codegen pipeline.
- **Performance impact**: Dict-based variable access is slower than Python locals. Mitigation: profile hotspots, defer optimization.
- **Error diagnostics quality**: Runtime errors may lack context. Mitigation: capture variable names and values in error messages.
- **Edge case coverage**: MUMPS indirection has many subtle behaviors. Mitigation: extensive MUGJ test suite validation.

## Clarifications

### Session 2026-01-16

- Q: What implementation approach for runtime MUMPS interpreter (FR-019)? → A: Reuse existing m2py pipeline: parse → ASG → generate Python → exec() at runtime
- Q: How should runtime indirection/XECUTE errors be handled? → A: Raise Python exception immediately (no trapping), matching MUMPS default behavior
- Q: Should indirection support global variables (`S X="^GLO",@X=1`)? → A: Yes, indirection to globals is supported
- Q: Should indirect DO/GOTO support offsets (`D @CMD+5`)? → A: Yes, offset applied after resolving indirection
- Q: Should FOR loop variable indirection (`F @A=1:1:10`) be supported? → A: Yes, supported per MUGJ V1IDNM1 test I-489

## Notes *(optional)*

- This is the FINAL codegen spec - after this, all core MUMPS language constructs are covered
- Indirection and XECUTE are the "dynamic escape hatch" - they allow any MUMPS code to be constructed and executed at runtime
- VistA relies heavily on these features for configuration, dispatch, and metaprogramming
- The MUMPS spec states XECUTE is equivalent to `DO UNIQUENAME` where UNIQUENAME is a synthetic subroutine containing the code string followed by QUIT
- Pattern indirection `X?@PAT` requires runtime pattern compilation (reuse Spec 011 pattern compiler)
- Argument indirection in SET (`S @"X=1"`) must parse the argument as a full SET argument including multi-assignment
