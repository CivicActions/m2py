# Feature Specification: Minimal Control Flow Foundation

**Feature Branch**: `004-codegen-foundation`  
**Created**: 2026-01-08  
**Status**: Draft  
**Input**: Spec 004 from codegen-plan.md - Minimal control flow foundation for Python code generation

## User Scenarios & Testing

### User Story 1 - Generate Valid Python from Basic MUMPS (Priority: P1)

As a developer transpiling MUMPS to Python, I need generated Python code that executes and produces correct output for basic MUMPS constructs (literals, variables, SET, WRITE, QUIT).

**Why this priority**: Foundation for all other code generation. Without basic expressions and statements working, nothing else can be validated.

**Independent Test**: Execute `S X=5 W X Q` and verify output is "5".

**Acceptance Scenarios**:

1. **Given** MUMPS `W "Hello"`, **When** transpiled and executed, **Then** output is "Hello"
2. **Given** MUMPS `S X=5 W X Q`, **When** transpiled and executed, **Then** output is "5"
3. **Given** MUMPS `W 1+2`, **When** transpiled and executed, **Then** output is "3"

---

### User Story 2 - M Value Coercion Helpers (Priority: P1)

As a developer, I need `m_num()`, `m_truth()`, and `m_compare()` helper functions that implement MUMPS coercion semantics so that arithmetic, comparisons, and conditionals work correctly.

**Why this priority**: All arithmetic, comparisons, and IF conditions depend on correct M coercion. This must be correct from day one to avoid refactoring later.

**Independent Test**: Verify `m_num("3A")` returns `3` and `m_truth("A3")` returns `False`.

**Acceptance Scenarios**:

1. **Given** `m_num("3A")`, **When** called, **Then** returns `3` (numeric prefix extraction)
2. **Given** `m_num("A3")`, **When** called, **Then** returns `0` (no leading numeric)
3. **Given** `m_truth("3A")`, **When** called, **Then** returns `True` (coerces to 3)
4. **Given** `m_truth("")`, **When** called, **Then** returns `False` (coerces to 0)
5. **Given** `m_compare(5, "<", 10)`, **When** called, **Then** returns `1`

---

### User Story 3 - IF/ELSE Control Flow (Priority: P2)

As a developer, I need IF and ELSE statements to generate correct Python conditionals that use M truth evaluation.

**Why this priority**: Branching is essential for any non-trivial program. Depends on P1 (m_truth).

**Independent Test**: Execute `S X=5 I X>3 W "GT" Q` and verify output is "GT".

**Acceptance Scenarios**:

1. **Given** `I X>3 W "GT"` with X=5, **When** executed, **Then** output is "GT"
2. **Given** `I X=1 W "Y" E  W "N"` with X=2, **When** executed, **Then** output is "N"
3. **Given** `I "3A" W "T"`, **When** executed, **Then** output is "T" (string truth)

---

### User Story 4 - FOR Loops with Literal Parameters (Priority: P2)

As a developer, I need FOR loops with literal start:increment:stop parameters to generate correct Python loops.

**Why this priority**: Iteration is fundamental. Bounded loops are simplest and most common.

**Independent Test**: Execute `F I=1:1:3 W I` and verify output is "123".

**Acceptance Scenarios**:

1. **Given** `F I=1:1:3 W I`, **When** executed, **Then** output is "123"
2. **Given** `F I="A","B","C" W I`, **When** executed, **Then** output is "ABC"
3. **Given** `F I=3:-1:1 W I`, **When** executed, **Then** output is "321" (negative increment)

---

### User Story 5 - DO Subroutine Calls (Priority: P2)

As a developer, I need DO to call labels as subroutines and return correctly.

**Why this priority**: Subroutines are essential for structured code. No cross-label complexity yet.

**Independent Test**: Execute `D SUB W "After" Q` with `SUB W "Sub " Q` and verify output is "Sub After".

**Acceptance Scenarios**:

1. **Given** `D SUB` followed by `SUB W "X" Q`, **When** executed, **Then** "X" is output and control returns
2. **Given** nested `D A` where A calls `D B`, **When** executed, **Then** both execute and return correctly

---

### User Story 6 - Simple GOTO (Priority: P3)

As a developer, I need GOTO to label targets (no offsets) to transfer control within a routine.

**Why this priority**: Forward jumps are common for error handling. Foundation for Spec 006's cross-label GOTO.

**Independent Test**: Execute `S X=1 G DONE S X=2` with `DONE W X Q` and verify output is "1".

**Acceptance Scenarios**:

1. **Given** `G DONE` with code after it, **When** executed, **Then** code after GOTO is skipped
2. **Given** forward GOTO, **When** executed, **Then** jumps to target label

---

### User Story 7 - Name Translation (Priority: P3)

As a developer, I need label and variable names translated to valid Python identifiers while preserving MUMPS semantics (case-sensitive, %-prefix, numeric labels).

**Why this priority**: Required for any routine with non-Python-compatible names.

**Independent Test**: Verify `%ROUTINE` translates to `_pct_ROUTINE` and `01` to `_n_01`.

**Acceptance Scenarios**:

1. **Given** label `%UTIL`, **When** translated, **Then** Python name is `_pct_UTIL`
2. **Given** label `123`, **When** translated, **Then** Python name is `_n_123`
3. **Given** labels `FOO` and `foo`, **When** translated, **Then** distinct Python names
4. **Given** label `for` (Python keyword), **When** translated, **Then** Python name is `_m_for`

---

### Edge Cases

- What happens when variable is undefined? → M returns empty string, Python should too via runtime
- What happens with negative loop increment? → `F I=3:-1:1` should count down (output: "321")
- What happens with left-to-right evaluation? → `2+3*4` should be 20, not 14 (requires `*` operator)
- What happens with empty string in comparison? → `"" < 1` uses numeric coercion (0 < 1 = true)

## Requirements

### Functional Requirements

- **FR-001**: System MUST generate syntactically valid Python 3.10+ code from MUMPS source
- **FR-002**: System MUST provide `m_num(value)` that extracts numeric prefix per ANSI 7.1.4.5
- **FR-003**: System MUST provide `m_truth(value)` that returns bool based on numeric interpretation per ANSI 1.2.4
- **FR-004**: System MUST provide `m_compare(a, op, b)` for M comparison semantics
- **FR-005**: Generated Python MUST execute with output matching YDB for equivalent MUMPS
- **FR-006**: System MUST translate SET to Python assignment
- **FR-007**: System MUST translate WRITE to output operation (print or buffer)
- **FR-008**: System MUST translate QUIT to function return
- **FR-009**: System MUST translate IF conditions using `m_truth()`
- **FR-010**: System MUST translate ELSE based on prior IF result
- **FR-011**: System MUST translate bounded FOR (`F I=1:1:10`) to Python loop
- **FR-012**: System MUST translate string-list FOR (`F I="A","B"`) to Python iteration
- **FR-013**: System MUST translate DO label to function call
- **FR-014**: System MUST translate GOTO label to control flow transfer
- **FR-015**: System MUST translate MUMPS names with `%` prefix to valid Python identifiers
- **FR-016**: System MUST translate pure numeric labels to valid Python identifiers
- **FR-017**: System MUST preserve case distinction in name translation (FOO ≠ foo)
- **FR-017a**: System MUST translate Python reserved words to valid identifiers (for → _m_for)
- **FR-018**: System MUST evaluate expressions left-to-right without operator precedence

### Key Entities

- **MUMPSRuntime**: Execution context holding variables, output buffer, $TEST state
- **CodeGenerator**: Transforms ASG to Python source code
- **NameTranslator**: Converts MUMPS names to Python identifiers (injective, reversible)

## Success Criteria

### Measurable Outcomes

- **SC-001**: All 7 user story acceptance scenarios pass with YDB-verified expected output
- **SC-002**: Generated Python executes without exceptions for all valid Spec 004 MUMPS input
- **SC-003**: Output matches YDB for all test cases (character-for-character)
- **SC-004**: Name translation is injective (no collisions) for all test inputs
- **SC-005**: Left-to-right evaluation verified: `2+3*4` outputs `20`, not `14`
- **SC-006**: Coercion verified: `"3A"+0` outputs `3`, `"A3"+0` outputs `0`

## YDB Reference Outputs

The following outputs were verified against YDB and serve as acceptance criteria:

| MUMPS Input | YDB Output |
|-------------|------------|
| `W "Hello"` | `Hello` |
| `W 1+2` | `3` |
| `S X=5 W X` | `5` |
| `W 2+3*4` | `20` |
| `W (2+3)*4` | `20` |
| `W 10-3` | `7` |
| `W "3A"+0` | `3` |
| `W "A3"+0` | `0` |
| `W 5<10` | `1` |
| `W 10<5` | `0` |
| `W 5=5` | `1` |
| `I "3A" W "true"` + `E W "false"` | `true` |
| `I "A3" W "true"` + `E W "false"` | `false` |
| `I "" W "true"` + `E W "false"` | `false` |
| `W ""<1` | `1` |
| `S X=5 I X>3 W "GT"` | `GT` |
| `S X=2 I X=1 W "one" E W "not one"` | `not one` |
| `F I=1:1:3 W I` | `123` |
| `F I=3:-1:1 W I` | `321` |
| `F I="A","B","C" W I` | `ABC` |
| `D SUB W "After" ... SUB W "Sub " Q` | `Sub After` |
| `S X=1 G DONE S X=2 ... DONE W X` | `1` |

## Scope Boundaries

### In Scope (Spec 004)

- Numeric literals (integers: `1`, `10`, `-5`)
- String literals (`"A"`, `"PASS"`)
- Local variables - simple names only (`X`, `I`, `COUNT`)
- Comparison operators: `=`, `<`, `>`
- Arithmetic operators: `+`, `-`, `*` (multiplication needed for left-to-right validation)
- Statements: SET (single assignment), WRITE (single value), QUIT (with/without value), DO (label call), IF, ELSE, FOR (bounded and string-list only), GOTO (label only)
- Left-to-right evaluation with parentheses
- M coercion helpers: `m_num()`, `m_truth()`, `m_compare()`
- Name translation for labels and variables

### Explicitly Deferred

- Open-ended FOR (`F I=1:1`), argumentless FOR, and QUIT postcondition (`Q:cond`) → Spec 005
- Intrinsic functions ($PIECE, $LENGTH, $GET, etc.) → Spec 008
- Global variables (^name) → Spec 007/008
- READ command → Spec 008
- NEW / KILL commands → Spec 008
- Logical operators (&, !) → Spec 008
- String concatenation (_) → Spec 008
- Pattern match (?) → Spec 008
- Negated comparisons ('=, '<, '>') → Spec 008
- Multiple assignments (S X=1,Y=2) → Spec 008
- Format controls (!, #, ?n) → Spec 008
- Postconditions on other commands (S:cond X=1) → Spec 008
- Extrinsic functions ($$func) → Spec 005
- Subscripted variables → Spec 008
- DO/GOTO with offsets → Spec 008
- Complex FOR parameters (expressions) → Spec 008
- Cross-label GOTO patterns → Spec 006
- $TEST stack semantics → Spec 005

## Clarifications

### Session 2026-01-08

- Q: Is multiplication (`*`) in scope? → A: Yes, required for left-to-right validation (`2+3*4` = 20)
- Q: Are postconditions in scope? → A: Only `Q:cond` for FOR loop exit; other postconditions deferred to Spec 008
- Q: Is negative FOR increment in scope? → A: Yes, `F I=3:-1:1` outputs "321"
- Q: Are parenthesized expressions in scope? → A: Yes, `(2+3)*4` is valid

