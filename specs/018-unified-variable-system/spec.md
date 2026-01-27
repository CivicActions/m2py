# Feature Specification: Unified Variable/Expression/Indirection/Subscript System

**Feature Branch**: `018-unified-variable-system`  
**Created**: 2025-01-10  
**Status**: Draft  
**Input**: Architectural simplification of variable access, indirection (@expressions), subscripts, and name translation across codegen and runtime.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consistent Variable Access Semantics (Priority: P1)

As a developer transpiling MUMPS code, I need variable access (reads and writes) to produce identical behavior regardless of whether the variable reference is resolved at compile time or runtime, so that indirection semantics match YottaDB exactly.

**Why this priority**: Variable access is fundamental to every MUMPS program. Incorrect semantics break everything.

**Independent Test**: Transpile `S A=1 W A` through all code paths (static, dynamic, indirection) and verify output matches YDB.

**Acceptance Scenarios**:

1. **Given** a simple variable read `W X`, **When** transpiled and executed, **Then** returns empty string if undefined (not Python error)
2. **Given** a subscripted variable `S A(1,2,3)=5`, **When** transpiled, **Then** creates nested MArray structure accessible as `A.get((1,2,3))`
3. **Given** indirection `S @"A(1)"=5`, **When** transpiled, **Then** produces identical result to `S A(1)=5`
4. **Given** global reference `S ^GLO(1)=1`, **When** transpiled, **Then** accesses shared global state (not local scope)

---

### User Story 2 - Name Indirection vs Argument Indirection (Priority: P1)

As a developer, I need the system to correctly distinguish between Name Indirection (used in SET, WRITE, etc.) and Argument Indirection (used in IF, FOR conditions, etc.), because they have fundamentally different semantics.

**Why this priority**: Treating these identically causes incorrect behavior. Name indirection requires a valid variable name as result; argument indirection evaluates the result as a complete MUMPS expression.

**Independent Test**: Execute `S A="1=0" I @A` - must evaluate "1=0" as expression (false), NOT convert string "1=0" to truth value (which would incorrectly be true).

**Acceptance Scenarios**:

1. **Given** `S A="B",B=5`, **When** executing `W @A` (name indirection), **Then** output is `5` ("B" used as variable name)
2. **Given** `S A="1=0"`, **When** executing `I @A` (argument indirection), **Then** condition is FALSE (evaluates expression "1=0")
3. **Given** `S A="X>5",X=10`, **When** executing `I @A`, **Then** condition is TRUE (evaluates "X>5" with X=10)
4. **Given** `S A="1+1", @A=5`, **When** executing (name indirection), **Then** error `VAREXPECTED` (result "2" is not a valid variable name)
5. **Given** `S A="$E(""ABC"",3)",C=99`, **When** executing `W @A`, **Then** output is `99` (evaluates $EXTRACT->"C", then uses "C" as variable name)

---

### User Story 3 - Multi-Level Indirection Resolution (Priority: P1)

As a developer, I need multi-level indirection (`@@VAR`, `@@@VAR`) to resolve each level sequentially, with subscripts applied at the correct resolution points, matching MUMPS specification exactly.

**Why this priority**: Multi-level indirection is a core MUMPS feature that existing code relies on heavily.

**Independent Test**: Execute `S A="B",B="C",C=99 W @@A` and verify output is `99`.

**Acceptance Scenarios**:

1. **Given** `S A="B",B=5`, **When** executing `W @@A`, **Then** output is `5` (resolves A->"B"->5)
2. **Given** `S A="B(1)",B(1)="C",C=7`, **When** executing `W @@@A`, **Then** output is `7`
3. **Given** `S X="A",A(1,2)="B(3,4)"`, **When** executing `S @@X@(1,2)@(5,6)=1`, **Then** `B(3,4,5,6)=1`
4. **Given** `S A="@B",B="C",C=1`, **When** executing `W @@A`, **Then** output is `1` (recursive @-expression evaluation)
5. **Given** `S A="B",B="C",C="1=0"`, **When** executing `I @@@A` (argument indirection), **Then** condition is FALSE (final level evaluated as expression)

---

### User Story 4 - Subscript Canonicalization (Priority: P1)

As a developer, I need subscripts to be canonicalized according to MUMPS rules where numeric values have a single canonical form, so that `A(1)`, `A(01)`, `A(1.0)`, and `A("1")` all reference the same node.

**Why this priority**: Incorrect subscript handling causes data corruption and lookup failures.

**Independent Test**: Set `A(1)="v"` then access via `A(01)`, `A(1.0)`, `A("1")` - all must return `"v"`.

**Acceptance Scenarios**:

1. **Given** `S A(1)="one"`, **When** accessing `A(01)`, **Then** returns `"one"` (leading zeros stripped)
2. **Given** `S A(1)="x"`, **When** accessing `A(1.0)`, **Then** returns `"x"` (trailing zeros stripped)
3. **Given** `S A(1)="y"`, **When** accessing `A("1")`, **Then** returns `"y"` (numeric string canonicalized)
4. **Given** `S A("1X")="z"`, **When** accessing `A("1X")`, **Then** returns `"z"` (non-numeric preserved as-is)
5. **Given** `S A("01")="w"` (string context), **When** accessing, **Then** preserves `"01"` distinctly from `1`

---

### User Story 5 - Name Translation Consistency (Priority: P2)

As a developer, I need MUMPS identifiers to be translated to valid Python identifiers consistently across codegen and runtime, so that generated code and runtime lookups reference the same variables.

**Why this priority**: Inconsistent name translation causes variables to "disappear" between compile and runtime.

**Independent Test**: Verify `%FOO` generates `_pct_FOO` in both codegen and runtime string parsing.

**Acceptance Scenarios**:

1. **Given** variable `%ABC`, **When** translated, **Then** produces `_pct_ABC` everywhere
2. **Given** numeric label `01`, **When** translated, **Then** produces `_n_01` everywhere
3. **Given** Python keyword `if`, **When** used as MUMPS variable, **Then** produces `_m_if` everywhere
4. **Given** runtime parses `"@%FOO"`, **When** resolving, **Then** looks up `_pct_FOO` (not `%FOO`)

---

### User Story 6 - Naked Global Indicator (Priority: P2)

As a developer, I need the naked indicator (`^(subs)`) to reference the most recently accessed global, including when that access occurred through indirection.

**Why this priority**: Naked indicator is a common MUMPS idiom that must work correctly with indirection.

**Independent Test**: Execute `S A="^V(1)",@A@(1,2)=2 W ^(2)` and verify output is `2`.

**Acceptance Scenarios**:

1. **Given** `S ^GLO(1,2)=1`, **When** executing `W ^(3)`, **Then** accesses `^GLO(1,3)`
2. **Given** `S A="^V(1,2)",@A=5`, **When** executing `W ^(3)`, **Then** accesses `^V(1,3)`
3. **Given** subscript indirection updates global, **When** naked reference follows, **Then** uses updated naked indicator

---

### User Story 7 - Static Pre-Resolution in Codegen (Priority: P3)

As a developer, I want codegen to pre-resolve statically-determinable variable references at compile time while falling back to runtime resolution for dynamic cases, optimizing generated code without sacrificing correctness.

**Why this priority**: Performance optimization that does not affect correctness.

**Independent Test**: Verify `S A(1)=5` generates direct Python assignment, not runtime `set_var()` call.

**Acceptance Scenarios**:

1. **Given** static variable `S X=1`, **When** codegen runs, **Then** generates direct assignment (no runtime call)
2. **Given** indirection `S @"X"=1` with constant string, **When** codegen runs, **Then** may pre-resolve to direct assignment
3. **Given** dynamic indirection `S @Y=1`, **When** codegen runs, **Then** generates runtime resolution call
4. **Given** mixed expression `S A(@X)=1`, **When** codegen runs, **Then** generates partial resolution (A is static, subscript is dynamic)

---

### Edge Cases

- What happens when indirection resolves to invalid variable name? Runtime error `VAREXPECTED`
- What happens when indirection string is empty in name context? Error `VAREXPECTED`
- What happens when indirection string is empty in argument context? Succeeds (YDB-specific behavior)
- How does `@$E("ABC",3)` work? Evaluates `$EXTRACT`, then uses result "C" as variable name
- What happens with `@@` where intermediate value contains `@`? Recursive evaluation of @-expression
- How are subscripts applied in `@@A@(1)@(2)`? After first resolution, before second
- What if subscript contains indirection: `A(1,@B,3)`? Subscript indirection evaluated during subscript building
- What is evaluation order for `S @A@(@B)=1`? Left-to-right: resolve @A first, then evaluate @B, then combine
- What about `m_truth("1=0")`? Returns true (string->number->1). This is WRONG for argument indirection which must evaluate as expression->0->false

## Requirements *(mandatory)*

### Functional Requirements

#### Core Variable Reference Model

- **FR-001**: System MUST represent all variable references (local, global, subscripted, indirected) using a single unified data structure
- **FR-002**: System MUST support local variables, global variables (^), subscripted variables, and indirection (@) in any combination
- **FR-003**: System MUST canonicalize numeric subscripts: `1`, `01`, `1.0`, `"1"` MUST all access the same node
- **FR-004**: System MUST preserve non-numeric string subscripts exactly: `"1X"` is distinct from `"1"`

#### Name Translation

- **FR-005**: System MUST translate MUMPS names to Python identifiers using consistent rules across all components
- **FR-006**: System MUST translate `%NAME` to `_pct_NAME`
- **FR-007**: System MUST translate numeric-prefixed labels (e.g., `01`) to `_n_01`
- **FR-008**: System MUST translate Python keywords used as MUMPS names (e.g., `if`) to `_m_if`
- **FR-009**: System MUST share name translation logic between codegen and runtime (single implementation)

#### Indirection Resolution

- **FR-010**: System MUST distinguish between Name Indirection (SET, WRITE, KILL, MERGE, READ) and Argument Indirection (IF, FOR args, XECUTE)
- **FR-011**: For Name Indirection, system MUST evaluate the indirection source and use result as a variable identifier (must be valid variable name)
- **FR-012**: For Argument Indirection, system MUST evaluate the indirection source as a complete MUMPS expression (result used as expression value, not variable name)
- **FR-013**: System MUST resolve multi-level indirection `@@VAR` by resolving outer level first, then resolving result
- **FR-014**: System MUST support arbitrary indirection depth (`@@@VAR`, `@@@@VAR`, etc.)
- **FR-015**: System MUST apply subscripts at correct resolution points: `@@A@(1)` applies (1) after first resolution
- **FR-016**: System MUST support per-level subscripts: `@@X@(1,2)@(5,6)` applies (1,2) to first resolution, (5,6) to second
- **FR-017**: System MUST support recursive indirection where resolved value contains @-expression
- **FR-018**: System MUST support subscript indirection: `A(1,@B,3)` evaluates @B during subscript construction
- **FR-019**: System MUST evaluate indirection operands left-to-right with side effects completing before next operand

#### Runtime Expression Evaluation

- **FR-020**: System MUST provide runtime capability to evaluate arbitrary MUMPS expression strings (similar to XECUTE but returning values)
- **FR-021**: Runtime expression evaluation MUST have access to current variable scope
- **FR-022**: Runtime expression evaluation MUST support all MUMPS operators, functions, and variable references

#### Error Handling

- **FR-023**: Name Indirection resolving to non-variable-name MUST raise `VAREXPECTED` error
- **FR-024**: Name Indirection with empty string MUST raise `VAREXPECTED` error
- **FR-025**: Indirection referencing undefined variable MUST raise `LVUNDEF` error
- **FR-026**: Error messages MUST include original indirection source and resolved value for debugging

#### Global and Naked Indicator

- **FR-027**: System MUST maintain naked indicator state that tracks most recently accessed global reference
- **FR-028**: System MUST update naked indicator when global is accessed through indirection
- **FR-029**: System MUST resolve `^(subs)` using stored naked indicator with new subscripts replacing last subscript level
- **FR-030**: Naked indicator MUST store base global name and all but the last subscript level

#### Codegen Integration

- **FR-031**: System MUST allow codegen to determine if a variable reference is statically resolvable
- **FR-032**: System MUST allow codegen to generate direct variable access for static references
- **FR-033**: System MUST allow codegen to generate runtime resolution calls for dynamic references
- **FR-034**: System MUST support partial static resolution (e.g., static base variable with dynamic subscripts)
- **FR-035**: Codegen MUST NOT use f-string interpolation for subscript expressions (use explicit concatenation or structured arguments)

#### Scope and MArray Handling

- **FR-036**: System MUST provide unified "Current Scope" abstraction that works regardless of storage mechanism (Python locals, state._locals, _scope dict)
- **FR-037**: All variable access (static or indirected) MUST use the same scope lookup path
- **FR-038**: All helper functions (m_str, m_num, m_truth, etc.) MUST recursively extract .value from MArray objects before processing

### Key Entities

- **VarRef**: A structured representation of a variable reference containing:
  - Name (or indirection source)
  - Is-global flag
  - Subscript list (each subscript may be static or dynamic)
  - Indirection level count
  - Per-level subscript attachments
  - Indirection context (NAME or ARGUMENT)

- **NameTranslator**: Shared component for MUMPS to Python identifier translation

- **SubscriptCanonicalizer**: Shared component for normalizing subscript values

- **IndirectionResolver**: Component that evaluates @-expressions at runtime, aware of context (name vs argument)

- **ExpressionEvaluator**: Component that parses and executes MUMPS expression strings at runtime (similar to XECUTE but for expressions)

- **CurrentScope**: Abstraction over variable storage that unifies Python locals, state._locals, and _scope dict access patterns

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All MUGJ indirection tests (V1IDNM1-3, VV2VNI*, V1XECA1, V1IDARG1, V1IDDO1, V1IDGO1) pass without modification
- **SC-002**: Name translation produces identical results in codegen and runtime for all test cases
- **SC-003**: Subscript canonicalization matches YottaDB behavior for all numeric formats
- **SC-004**: Multi-level indirection with per-level subscripts produces YottaDB-identical results
- **SC-005**: Generated code for static variable references contains no runtime resolution calls
- **SC-006**: Runtime variable access performance does not regress vs. current implementation
- **SC-007**: New unified implementation has 90%+ test coverage from MUGJ-extracted test cases
- **SC-008**: Argument indirection (`I @A` where A="1=0") correctly evaluates expression (returns false, not true)
- **SC-009**: Name indirection with invalid result (e.g., A="1+1") raises appropriate VAREXPECTED error
- **SC-010**: All indirection contexts use unified scope lookup (no "variable not found" bugs between codegen and runtime)

## Assumptions

1. **Single truth source**: YottaDB behavior is the definitive reference for MUMPS semantics
2. **MUGJ completeness**: MUGJ test suite covers all critical indirection patterns
3. **Progressive migration**: New code will be built alongside existing code, migrating incrementally per-command (SET, WRITE, IF, etc.) with aggressive dead code cleanup after each migration step
4. **Dead code hygiene**: Remove superseded code immediately after each command migration; perform periodic dead code scans during development and a terminal scan before feature completion
5. **Shared module location**: New shared code will live in `src/m2py/core/` or similar neutral location
6. **MArray compatibility**: Unified system will continue to use MArray for variable storage

## Clarifications

### Session 2025-01-25

- Q: When and how will old code be deprecated during progressive migration? → A: Migrate incrementally per-command, aggressively clean up dead code as we go, plus periodic and terminal dead code rescans
