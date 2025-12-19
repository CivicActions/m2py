# Feature Specification: MUMPS Semantic Graph Parser (textX-based)

**Feature Branch**: `001-textx-semantic-graph`  
**Created**: 2025-12-19  
**Status**: Draft  
**Input**: User description: "MUMPS semantic graph transpiler using textX parser - build an Abstract Semantic Graph that captures semantic meaning (especially flow control) to enable natural Python translation with proper variable scope tracking"

---

## Executive Summary

This specification defines a **parser and semantic analyzer** for MUMPS that produces a complete, correct Abstract Semantic Graph (ASG). The ASG will serve as the foundation for a future Python code generation phase (separate specification).

This phase delivers:

1. A **textX-based parser** with a complete MUMPS grammar
2. An **Abstract Semantic Graph (ASG)** that captures program meaning, not just syntax
3. **Complete control flow resolution** (labels, GOTO targets, loop structures, nested scopes)
4. **Variable scope analysis** that tracks variable usage, NEW boundaries, and call chains

**Eventual Goal**: The ASG produced by this phase will enable natural Python code generation in a follow-up effort. By building a complete semantic model first, code generation becomes a straightforward traversal rather than complex state machine processing.

**Not In Scope**: Python code generation is explicitly deferred to a subsequent specification. This phase focuses exclusively on parsing and semantic analysis.

This approach replaces the current YottaDB opcode-based approach, which struggled with sequential processing of compiler IR, constant folding, and complex control flow reconstruction.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Parse and Analyze Simple MUMPS Routines (Priority: P1)

As a developer building a MUMPS transpiler, I want to parse MUMPS routines and produce a semantic graph that correctly represents SET, WRITE, basic IF, and simple FOR constructs with all their relationships resolved.

**Why this priority**: This establishes the foundational parsing and ASG infrastructure. Without this, no other features can be built. Simple routines represent the majority of MUMPS code by line count.

**Independent Test**: Parse a MUMPS file containing SET, WRITE, IF, and bounded FOR commands. Verify the ASG correctly represents all statements, their scopes, variable references, and control flow.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine with sequential SET and WRITE commands, **When** parsed, **Then** the ASG contains statement nodes with correct variable references and literal values
2. **Given** a MUMPS routine with a bounded FOR loop (`F I=1:1:10 W I`), **When** parsed, **Then** the ASG contains a FOR node classified as "bounded" with start/step/end values and body statements as children
3. **Given** a MUMPS routine with a simple IF condition, **When** parsed, **Then** the ASG contains an IF node with condition expression and a nested scope containing the conditional statements

---

### User Story 2 - Handle Complex FOR Loop Patterns (Priority: P2)

As a developer, I want the parser to correctly model FOR loops with multiple forparameters (string lists, mixed patterns, nested loops), classifying each loop type and capturing all parameters accurately.

**Why this priority**: FOR loops are one of the most challenging constructs in MUMPS. The previous approach failed specifically on complex FOR patterns. Getting this right validates the semantic graph approach.

**Independent Test**: Parse the MUGJ FOR loop test files (V1FORA, V1FORB, V1FORC series). Verify the ASG correctly classifies each FOR loop type and captures all forparameters.

**Acceptance Scenarios**:

1. **Given** a string list FOR (`F I="A","B","C" W I`), **When** parsed, **Then** the ASG contains a FOR node classified as "string-list" with the list of values captured
2. **Given** a mixed forparameter FOR (`F I="A",1:1:3`), **When** parsed, **Then** the ASG contains a FOR node classified as "mixed" with both string values and numeric range parameters
3. **Given** nested FOR loops, **When** parsed, **Then** the ASG correctly represents parent-child scope relationships between the loops
4. **Given** an open-ended FOR with QUIT condition (`F I=1:1 Q:I>10`), **When** parsed, **Then** the ASG contains a FOR node classified as "open-ended" with the QUIT condition linked as a loop exit point

---

### User Story 3 - Handle GOTO Across Control Boundaries (Priority: P2)

As a developer, I want the semantic graph to fully classify GOTO statements—identifying their targets, the control structures they exit, and whether they jump forward, backward, or across labels.

**Why this priority**: GOTO inside loops was the primary failure mode of the previous approach. The semantic graph must classify GOTO types completely so that code generation (future phase) can select appropriate strategies.

**Independent Test**: Parse MUGJ GOTO test files (V1GO1, V1GO2, V1FORC2). Verify the ASG correctly resolves all GOTO targets and classifies each GOTO's relationship to enclosing control structures.

**Acceptance Scenarios**:

1. **Given** a GOTO that exits a single FOR loop, **When** parsed, **Then** the ASG links the GOTO to its target label and flags it as "exits-for-loop" with the specific loop identified
2. **Given** a GOTO that exits nested FOR loops, **When** parsed, **Then** the ASG identifies all enclosing loops that would be exited
3. **Given** a backward GOTO to a label (creating a loop), **When** parsed, **Then** the ASG classifies it as "backward-jump" with the target label resolved
4. **Given** a GOTO to a label in a different routine, **When** parsed, **Then** the ASG captures the external routine reference

---

### User Story 4 - Variable Scope and Data Flow Analysis (Priority: P3)

As a developer, I want the semantic graph to track variable usage across scopes, identifying which variables are read, written, shadowed by NEW, and passed between subroutines, to enable "clean" Python function generation.

**Why this priority**: This analysis enables future code generation to produce clean Python with proper function signatures (arguments and return values) instead of relying on a global runtime variable store (`get_local`/`set_local`).

**Independent Test**: Parse a routine with subroutine calls and NEW commands. Verify the ASG correctly identifies variable flow (inputs/outputs) between callers and callees.

**Acceptance Scenarios**:

1. **Given** a subroutine that reads variables defined by its caller, **When** parsed, **Then** the ASG identifies those variables as "inputs" (arguments) for that scope
2. **Given** a subroutine that modifies variables visible to its caller, **When** parsed, **Then** the ASG identifies those variables as "outputs" (return values)
3. **Given** a NEW command that shadows a variable, **When** parsed, **Then** the ASG marks a scope boundary where the variable is shadowed and tracks the inner variable separately
4. **Given** variables only used within a single label, **When** parsed, **Then** the ASG identifies those as "local-only" with no external visibility
5. **Given** a complex call chain, **When** analyzed, **Then** the ASG computes the transitive closure of variable requirements (e.g., if A calls B, and B needs X, then A needs X)

---

### User Story 5 - Parse Special MUMPS Features (Priority: P3)

As a developer, I want the parser to correctly represent special MUMPS features (indirection, pattern matching, $SELECT, $PIECE, naked globals, $TEST) in the semantic graph.

**Why this priority**: These features appear less frequently but are critical for correctness when they do appear. The ASG must capture them accurately for future code generation.

**Independent Test**: Parse MUGJ test files covering intrinsic functions, pattern matching, and special variables. Verify the ASG correctly represents each construct.

**Acceptance Scenarios**:

1. **Given** a pattern match expression (`X?1A.N`), **When** parsed, **Then** the ASG contains a pattern match node with the full pattern specification captured
2. **Given** $PIECE/$EXTRACT operations, **When** parsed, **Then** the ASG contains function call nodes with all arguments correctly represented
3. **Given** $SELECT with multiple conditions, **When** parsed, **Then** the ASG represents all condition/value pairs in order
4. **Given** $TEST special variable usage, **When** parsed, **Then** the ASG identifies the reference and links it to the IF statements that set $TEST

---

### Edge Cases

- **Forward reference in GOTO**: What happens when GOTO targets a label defined later in the file? (Resolved by multi-pass ASG construction)
- **Recursive routine calls**: How are mutually recursive routines handled? (Each label becomes a callable function)
- **Naked global references**: How is `^(subscript)` handled when it depends on runtime state? (Runtime tracking of last global reference)
- **Indirection at runtime**: How is `@variable` handled when the variable value determines the code? (May require runtime eval or limited interpretation)
- **Multiple forparameters with QUIT**: How is `F I="A","B" Q:I="A" W I` handled? (FOR body includes conditional exit)
- **GOTO inside IF inside FOR**: Complex nesting of control structures (Semantic graph captures nesting hierarchy completely)
- **Empty FOR body with postcondition**: `F I=1:1:10 Q:I>5` with nothing after (Valid MUMPS, generates empty loop body with break)

---

## Requirements *(mandatory)*

### Functional Requirements

#### Parser Requirements

- **FR-001**: System MUST parse MUMPS source code using a textX grammar definition
- **FR-002**: System MUST handle all MUMPS commands defined in the 1995 ANSI standard (SET, WRITE, READ, IF, ELSE, FOR, DO, GOTO, QUIT, HALT, NEW, KILL, MERGE, LOCK, OPEN, CLOSE, USE, XECUTE, JOB, HANG, VIEW)
- **FR-003**: System MUST parse MUMPS intrinsic functions ($ASCII, $CHAR, $DATA, $EXTRACT, $FIND, $FNUMBER, $GET, $JUSTIFY, $LENGTH, $ORDER, $PIECE, $QLENGTH, $QSUBSCRIPT, $QUERY, $RANDOM, $REVERSE, $SELECT, $STACK, $TEXT, $TRANSLATE)
- **FR-004**: System MUST parse MUMPS special variables ($DEVICE, $ECODE, $ESTACK, $ETRAP, $HOROLOG, $IO, $JOB, $KEY, $PRINCIPAL, $QUIT, $REFERENCE, $STACK, $STORAGE, $SYSTEM, $TEST, $X, $Y, $ZLEVEL)
- **FR-005**: System MUST parse MUMPS operators (arithmetic: +, -, *, /, \, #, **; comparison: =, <, >, '=, '<, '>; logical: &, !, '; string: _, [, ], ]], ?; unary: +, -)
- **FR-006**: System MUST handle line labels with optional formal parameter lists (`LABEL(param1,param2)`)
- **FR-007**: System MUST handle postconditioned commands (`W:X>0 "positive"`)
- **FR-008**: System MUST handle argument postconditions (`W X:X>0`)
- **FR-009**: System MUST handle multiple arguments in single commands (`S X=1,Y=2,Z=3`)
- **FR-010**: System MUST handle dotted block syntax (`. S X=1`)
- **FR-011**: System MUST handle line continuation with proper scope
- **FR-012**: System MUST parse comments (`;` to end of line)
- **FR-013**: System MUST handle subscripted local variables (`X(1,2,3)`)
- **FR-014**: System MUST handle global variable references (`^GLOBAL(subscripts)`)
- **FR-015**: System MUST handle naked global references (`^(subscripts)`)
- **FR-016**: System MUST handle indirection (`@variable`)
- **FR-017**: System MUST handle routine references (`LABEL^ROUTINE`)
- **FR-018**: System MUST handle extrinsic functions (`$$FUNC^ROUTINE(args)`)
- **FR-019**: System MUST handle extrinsic variables (`$$VAR`)

#### Semantic Graph Requirements

- **FR-020**: System MUST build an Abstract Semantic Graph (ASG) that represents program semantics, not just syntax
- **FR-021**: System MUST resolve all label references before code generation (no forward reference issues)
- **FR-022**: System MUST capture routine structure (labels as entry points, statements within labels)
- **FR-023**: System MUST model scopes explicitly (routine scope, IF block scope, FOR loop scope, DO block scope)
- **FR-024**: System MUST link GOTO/DO statements to their target labels
- **FR-025**: System MUST classify FOR loops by type (bounded, open-ended, string-list, mixed, argumentless)
- **FR-026**: System MUST identify QUIT statements and their enclosing context (FOR loop, DO block, routine)
- **FR-027**: System MUST track which labels call which other labels
- **FR-028**: System MUST model IF/ELSE as explicit scope containers with condition expressions
- **FR-029**: System MUST handle nested control structures to arbitrary depth
- **FR-030**: System MUST preserve source location information for error reporting
- **FR-053**: System MUST identify unreachable code segments (e.g., code following an unconditional GOTO/QUIT within a block) to prevent invalid graph connections

#### GOTO Classification Requirements

- **FR-031**: System MUST classify GOTO statements as: forward-jump, backward-jump, loop-exit, cross-label-jump
- **FR-032**: System MUST identify when GOTO can be replaced with Python `break` (single loop exit)
- **FR-033**: System MUST identify when GOTO can be replaced with Python `continue`
- **FR-034**: System MUST identify when GOTO requires structured transformation (backward jump → while loop)
- **FR-035**: System MUST identify GOTO that exits multiple nested loops
- **FR-036**: System MUST identify GOTO that jumps to different labels (potential function call transformation)

#### Variable Scope and Data Flow Analysis Requirements

- **FR-037**: System MUST track all local variables used within each label/subroutine
- **FR-038**: System MUST identify variables read but not defined in a scope (must be passed in as arguments)
- **FR-039**: System MUST identify variables defined and potentially used by callers (must be returned/updated)
- **FR-040**: System MUST respect NEW command semantics (variable shadowing)
- **FR-041**: System MUST handle exclusive NEW (`N (except)`) which creates new variables for all except listed
- **FR-042**: System MUST propagate variable requirements through call chains (transitive closure of inputs/outputs)
- **FR-043**: System SHOULD produce metadata suitable for generating Python function signatures (args, returns)
- **FR-044**: System MUST continue to support runtime variable access for cases that cannot be statically analyzed (indirection)
- **FR-051**: System MUST analyze "Def-Use" chains to determine variable lifetime and scope
- **FR-052**: System MUST handle "Argumentless DO" which creates a new stack frame (scope) but continues execution flow sequentially

#### ASG Output Requirements

- **FR-045**: System MUST produce an ASG that can be serialized and inspected for debugging
- **FR-046**: System MUST produce an ASG that is complete (all constructs represented) and correct (semantics preserved)
- **FR-047**: System SHOULD provide ASG traversal utilities for downstream consumers (future code generator)
- **FR-048**: System MUST annotate ASG nodes with source location information (file, line, column)
- **FR-049**: System MUST flag constructs that require runtime support (indirection, naked globals) in the ASG
- **FR-050**: System MUST capture MUMPS evaluation order in expression trees (left-to-right with side effects)

### Key Entities

- **Routine**: A MUMPS source file containing one or more labels
- **Label**: A named entry point with optional formal parameters and a sequence of statements
- **Statement**: A command with optional arguments and postconditions
- **Scope**: A container for statements (label body, IF body, FOR body, DO block)
- **Expression**: A value computation (literal, variable, function call, binary operation)
- **Reference**: A variable or global reference (local, global, subscripted)
- **Call**: A reference to another label (DO, GOTO, extrinsic function)
- **ForParameter**: A component of a FOR loop specification (value, start:step:end)
- **VariableBinding**: Association of a variable name with its scope and usage pattern

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parser successfully parses 100% of MUGJ test suite files without errors
- **SC-002**: ASG correctly classifies FOR loops in V1FORA, V1FORB, V1FORC test files (all forparameter types represented)
- **SC-003**: ASG correctly resolves all GOTO targets in V1GO1, V1GO2, V1FORC2 (no unresolved references)
- **SC-004**: ASG correctly identifies GOTO-exits-loop relationships for all GOTO statements inside FOR loops
- **SC-005**: Parse time for a 500-line MUMPS routine is under 2 seconds
- **SC-006**: Variable scope analysis correctly identifies read/write/shadow relationships for all NEW commands in test files
- **SC-007**: Error messages include source file location (line number, column) for parse failures
- **SC-008**: The textX grammar covers all MUMPS constructs found in the MUGJ test suite

---

## Assumptions

- **A-001**: Python 3.10+ is the target execution environment
- **A-002**: textX library is suitable for MUMPS grammar complexity
- **A-003**: Global variables will continue to use runtime library for database operations
- **A-004**: Indirection (`@variable`) may require limited runtime interpretation for fully dynamic cases
- **A-005**: The MUGJ test suite provides sufficient coverage of MUMPS language features
- **A-006**: Performance is secondary to correctness in initial implementation

---

## Known Challenging Constructs

The following MUMPS constructs proved particularly difficult in the previous opcode-based implementation and must be carefully considered in the design:

### 1. GOTO Inside Nested FOR Loops

**Challenge**: When GOTO appears inside nested FOR loops, all enclosing loops must be exited. The previous exception-based approach failed because inner exception handlers cleared the goto context before outer loops could handle it.

**MUMPS Example (V1FORC2 I-374)**:
```mumps
F I=1:1:3 S VCOMP=VCOMP_I_"*" F J=1:1:4 S VCOMP=VCOMP_J_" " I I>1,J>1 G G3741
S VCOMP=VCOMP_"---"
G3741 S VCOMP=VCOMP_I_" "_J
```

**Consideration**: The semantic graph must capture the complete nesting hierarchy and GOTO targets to enable a structured transformation (possibly using nested function definitions or state machines).

### 2. Multiple Forparameters (Mixed FOR Patterns)

**Challenge**: FOR loops can have multiple comma-separated parameters mixing string values and numeric ranges. These compile to complex opcode patterns with dispatch tables.

**MUMPS Example**:
```mumps
F I="A","B",1:1:3 W I  ; outputs A B 1 2 3
```

**Consideration**: The parser must model forparameters as a list, and the semantic graph must represent each type. Code generation should unroll or combine iterations appropriately.

### 3. Argumentless FOR with Implicit QUIT

**Challenge**: FOR without arguments (`F  command`) loops forever until QUIT. The loop body may be on the same line with dotted continuation, or the loop may be terminated by conditions within the body.

**MUMPS Example**:
```mumps
F  R X Q:X=""  W X
```

**Consideration**: The semantic graph must identify the loop termination condition (QUIT with condition) and model it as part of the FOR construct.

### 4. $TEST Special Variable and IF Without Condition

**Challenge**: The `$TEST` special variable retains the result of the most recent IF condition. IF without an argument uses `$TEST`. ELSE depends on `$TEST` being false.

**MUMPS Example**:
```mumps
I X>0 W "positive"
E  W "not positive"   ; uses $TEST = 0
```

**Consideration**: The semantic graph should track `$TEST` state changes and model IF/ELSE pairs as a single conditional construct where possible.

### 5. Postconditioned Commands and Arguments

**Challenge**: Commands and arguments can have postconditions that are evaluated at runtime. The postcondition affects whether the command/argument is executed.

**MUMPS Example**:
```mumps
W:X>0 "X is positive"    ; write only if X>0
W A:A>0,B:B>0,C           ; write A if A>0, write B if B>0, always write C
```

**Consideration**: Postconditions should be modeled as conditional wrappers around commands/arguments in the semantic graph.

### 6. Naked Global References

**Challenge**: Naked global references (`^(subscripts)`) reuse the global name and prefix subscripts from the most recent global reference. This is inherently runtime-dependent.

**MUMPS Example**:
```mumps
S ^PATIENT(123,"NAME")="Smith"
S ^("DOB")="1990-01-01"   ; actually sets ^PATIENT(123,"DOB")
```

**Consideration**: Naked global references cannot be fully resolved at compile time. Runtime tracking of "last global reference" is required.

### 7. MUMPS Evaluation Order vs Python

**Challenge**: MUMPS evaluates expressions strictly left-to-right, including side effects. Python has different evaluation rules for function arguments.

**MUMPS Example**:
```mumps
F I=^X:1:^X S ^X=^X+1  ; subscript, start, step, end evaluated in specific order
```

**Consideration**: Code generation may need to introduce temporary variables to preserve MUMPS evaluation order.

### 8. NEW Command Variable Shadowing

**Challenge**: NEW creates a new instantiation of variables that shadows the caller's values. Upon return, original values are restored. This is like a call-stack-based scope but applies selectively to named variables.

**MUMPS Example**:
```mumps
CALLER S X=1 D SUB W X  ; X is still 1 after SUB returns
SUB N X S X=99 Q        ; X is 99 only inside SUB
```

**Consideration**: The semantic graph should model NEW as a scope boundary. Variable analysis must respect NEW when determining what variables a subroutine can access from its caller.

### 9. Indirection (`@variable`)

**Challenge**: Indirection allows runtime construction of variable names, command arguments, or even entire commands. This defeats static analysis.

**MUMPS Examples**:
```mumps
S @("X"_N)=value        ; name indirection
D @routinename          ; command indirection  
S X=@Y@(1,2)            ; subscript indirection
```

**Consideration**: Some indirection can be resolved statically (constant strings). Dynamic indirection requires runtime support. The semantic graph should flag indirection for special handling.

### 10. Pattern Matching with Alternation and Repetition

**Challenge**: MUMPS pattern matching (`?`) is its own mini-language with counts, alternation, and pattern codes. Indirect patterns (`?@X`) add complexity.

**MUMPS Example**:
```mumps
I SSN?3N1"-"2N1"-"4N   ; social security number pattern
```

**Consideration**: Pattern matching should translate to Python regex or a custom runtime function. The parser must capture the full pattern specification.

### 11. Argumentless DO

**Challenge**: The `DO` command without arguments (`D`) initiates a new scope (stack frame) for variable isolation (via `NEW`) but does *not* jump to a new label. Execution continues on the next line. When the block finishes (implicit or explicit QUIT), the scope is popped.

**MUMPS Example**:
```mumps
S X=1
D
. N X S X=2  ; New scope, X is shadowed
. W X        ; Prints 2
W X          ; Prints 1 (scope restored)
```

**Consideration**: The parser must recognize this as a scope creation event. The ASG must model this as a "Block Scope" similar to a function call but inline.

---

## Dependencies

- **textX library**: For grammar definition and parsing
- **Python 3.10+**: For code generation target
- **MUGJ test suite**: For validation against known-correct MUMPS behavior

---

## Out of Scope

- **Python code generation** - This is the primary deferral. Code generation will be a follow-up specification that consumes the ASG produced by this phase.
- **Runtime library implementation** - The existing runtime library may be reused or updated in the code generation phase
- Database/persistence layer for global variables
- Network/distributed MUMPS features (JOB on remote)
- Device I/O beyond basic READ/WRITE
- Performance optimization
- Source-to-source debugging tools
- GUI or IDE integration

## Future Work (Next Specification)

The following will be addressed in a follow-up "Code Generation" specification:

1. **Python AST generation** from the semantic graph
2. **Code generation strategies** for GOTO (break, continue, nested functions, state machines)
3. **Function signature generation** based on variable scope analysis
4. **Runtime library integration** for constructs requiring runtime support
5. **Output formatting and post-processing**
