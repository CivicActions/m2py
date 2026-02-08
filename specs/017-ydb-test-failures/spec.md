# Feature Specification: YDB Test Suite Failure Resolution

**Feature Branch**: `017-ydb-test-failures`  
**Created**: 2026-01-22  
**Updated**: 2026-01-26 (incorporated Spec 018 Unified Variable System)  
**Status**: In Progress  
**Input**: User description: "Comprehensive resolution of all outstanding YDB test suite failures including TRAMPOLINE strategy enhancements for argumentless KILL/NEW, implementation of missing operators and features, codegen bug fixes, and behavioral corrections across arithmetic, patterns, control flow, and variable handling"

## Major Architectural Changes

### Unified Variable System (Merged from Spec 018)

The `018-unified-variable-system` branch was merged into this feature branch, providing a comprehensive redesign of variable access, indirection resolution, subscript handling, and name translation. This change created a new `src/m2py/core/` module with shared components used by both codegen and runtime.

**Key Components**:

- **NameTranslator** (`core/names.py`): Bidirectional MUMPS↔Python identifier translation
  - `%NAME` → `_pct_NAME`, `01` → `_n_01`, `if` → `_m_if`
  - Single source of truth for both codegen and runtime
  
- **SubscriptCanonicalizer** (`core/subscripts.py`): MUMPS-compliant subscript normalization
  - `A(1)`, `A(01)`, `A(1.0)`, `A("1")` all access the same node
  - `A("01")` is distinct from `A(1)` (non-canonical string preserved)

- **CurrentScope** (`core/scope.py`): Unified variable access abstraction
  - Works with `_scope` dict, Python locals, and `state._locals`
  - Automatically extracts `.value` from MArray objects
  - Raises `LVUNDEFError` in strict mode for undefined variables

- **IndirectionResolver** (`core/indirection.py`): Runtime @-expression resolution
  - **IndirectionContext.NAME**: Result must be valid variable name (SET, WRITE, KILL)
  - **IndirectionContext.ARGUMENT**: Result evaluated as MUMPS expression (IF, FOR args)
  - Multi-level indirection with per-level subscript support
  - Recursive @-expression handling

**Critical Bug Fixes**:

1. **Argument Indirection Expression Evaluation**: `I @A` where `A="1=0"` now correctly evaluates the expression as FALSE instead of treating the string as truthy

2. **Multi-Level Subscript Merging**: `@@X@(1,2)@(3,4)` now correctly resolves through multiple levels with subscripts applied at each resolution point

3. **Variable Scope Access**: All variable access (static or indirected) now uses the same lookup path, preventing "variable not found" bugs

### Serial MUGJ Test Execution

The MUGJ test suite was refactored to run as a **single unit** that executes all 72 routines in the exact YDB driver order, preserving shared state ($Y, $X, globals) across routines. This matches how YottaDB executes the suite.

**Benefits**:
- Form feeds and whitespace match naturally (no normalization needed)
- Catches whitespace and wrapping bugs that per-test execution misses
- Fast execution (~15s total including transpilation)

**Trade-offs**:
- Debugging individual test failures requires more investigation
- Cannot run tests in parallel

**Note**: This approach may or may not be needed for other suites (basic, mvts, merge). Those suites are slower and benefit from parallel/granular execution. We may keep the current per-test approach for them with whitespace normalization before comparison.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execute MUMPS Routines with Argumentless KILL/NEW (Priority: P1)

As a developer transpiling MUMPS to Python, I need routines containing argumentless KILL (which clears all local variables) and argumentless NEW (which stacks all local variables) to execute correctly, so that VistA and other production MUMPS applications that use these constructs work properly after transpilation.

**Why this priority**: Argumentless KILL and NEW are used in ~50 VistA files and represent a fundamental MUMPS feature. Without this, significant production code cannot be transpiled correctly. This is an architectural gap, not a simple bug.

**Independent Test**: Run any of the 7 affected MVTS test routines (v1call, v1nst3, v1ov, v1prgd, v1seq, vv2lcc1, vv2vnib) through m2py and verify they produce identical output to YottaDB.

**Note**: Originally scoped for 10 tests. Tests fifo, per02397, setpiece were reclassified to US8 (LIM-015 xfail) due to Z-extension dependencies ($ZVERSION, NEW $ZTRAP).

**Acceptance Scenarios**:

1. **Given** a MUMPS routine containing `KILL` (argumentless), **When** transpiled and executed, **Then** all local variables are cleared and execution continues correctly
2. **Given** a MUMPS routine containing `NEW` (argumentless), **When** transpiled and executed, **Then** all local variables are saved, cleared, and restored at QUIT
3. **Given** a MUMPS routine using both argumentless KILL and cross-label GOTO, **When** transpiled, **Then** the TRAMPOLINE strategy correctly manages variable state across label boundaries

---

### User Story 2 - Execute MUMPS Routines with Missing Operators (Priority: P1)

As a developer transpiling MUMPS to Python, I need all standard MUMPS operators to be implemented so that expressions evaluate correctly.

**Why this priority**: Missing operators cause immediate transpilation failures. The sorts-after operator (`]]`) is part of the ANSI MUMPS standard and prevents the `relation` test from passing.

**Independent Test**: Transpile and execute the `relation` test routine, verifying output matches YottaDB reference.

**Acceptance Scenarios**:

1. **Given** a MUMPS expression using the sorts-after operator (`A]]B`), **When** evaluated, **Then** it returns 1 if A sorts after B using MUMPS collation (empty string < numerics < strings)
2. **Given** MUMPS code comparing numeric strings like `"10"]]"9"`, **When** evaluated, **Then** it returns 1 (numeric comparison, not string)
3. **Given** MUMPS code comparing mixed types like `"ABC"]]"9"`, **When** evaluated, **Then** it returns 1 (strings sort after numerics)

---

### User Story 3 - Execute MUMPS Routines with LHS $PIECE on Non-Local Variables (Priority: P1)

As a developer transpiling MUMPS to Python, I need left-hand side $PIECE assignments to work with naked globals and indirection, not just local variables.

**Why this priority**: LHS $PIECE is fundamental to MUMPS string manipulation. Limiting it to local variables prevents 3 test routines from passing and may break production code.

**Independent Test**: Transpile and execute vv2lhp1, vv2lhp2, and vv2vnic tests, verifying output matches YottaDB.

**Acceptance Scenarios**:

1. **Given** `SET $PIECE(^(subscript),delim,pos)=value`, **When** transpiled and executed, **Then** the naked global reference is updated with the piece replacement
2. **Given** `SET $PIECE(@indirect,delim,pos)=value`, **When** transpiled and executed, **Then** the indirected variable is updated correctly
3. **Given** `SET $PIECE(^GLOBAL(x,y),",",2)="new"`, **When** transpiled, **Then** the global is read, modified, and written back

---

### User Story 4 - Fix Arithmetic and Numeric Handling (Priority: P2)

As a developer transpiling MUMPS to Python, I need numeric operations to produce results matching YottaDB's behavior including scientific notation formatting, large exponents, and precision handling.

**Why this priority**: Arithmetic bugs affect at least 5 test routines (arith, barith, ebmuldiv, largeexp2, largeexp3) and represent visible output differences. However, many of these may require careful debugging rather than new features.

**Independent Test**: Run arith test routine and compare each line of output with YottaDB reference to identify precision/formatting differences.

**Acceptance Scenarios**:

1. **Given** multiplication involving large numbers, **When** formatted as output, **Then** the number format matches YottaDB's conventions
2. **Given** scientific notation numbers like `1.234E+5 * 10`, **When** evaluated, **Then** the result is `1234000` not `12.34`
3. **Given** floating point operations, **When** output, **Then** precision matches MUMPS specification (trailing zeros, decimal places)

---

### User Story 5 - Fix Pattern Matching (Priority: P2)

As a developer transpiling MUMPS to Python, I need the pattern match operator (`?`) to correctly match all MUMPS patterns.

**Why this priority**: Multiple pattern matching tests fail (pattst, v1pat, vv2pat1, vv2pat2, vv2pat3), indicating systemic issues with the pattern_compiler or its integration.

**Independent Test**: Run pattst routine and verify each pattern test produces correct true/false output.

**Acceptance Scenarios**:

1. **Given** a pattern like `?1N.N` (one digit followed by optional digits), **When** matched against "123", **Then** it returns true
2. **Given** a pattern like `?1A.A1N.N` (alpha followed by optional alpha, then digit followed by optional digits), **When** matched against "ABC123", **Then** it returns true
3. **Given** alternation patterns, **When** compiled, **Then** they match the same strings as YottaDB

---

### User Story 6 - Fix FOR Loop Execution (Priority: P2)

As a developer transpiling MUMPS to Python, I need FOR loops to execute with correct iteration behavior including bounds handling and incrementing.

**Why this priority**: FOR loop tests (for, forloop, v1fora, v1forb, v1forc) fail, indicating issues with loop variable handling, bounds computation, or increment logic.

**Independent Test**: Run for routine and verify iteration counts and variable values match YottaDB.

**Acceptance Scenarios**:

1. **Given** `FOR I=1:1:10`, **When** executed, **Then** I takes values 1 through 10 inclusive
2. **Given** `FOR I=10:-1:1`, **When** executed, **Then** I counts down from 10 to 1
3. **Given** nested FOR loops, **When** executed, **Then** inner loop completes fully for each outer iteration

---

### User Story 7 - Fix $ORDER and $QUERY Functions (Priority: P2)

As a developer transpiling MUMPS to Python, I need $ORDER and $QUERY to correctly traverse arrays and globals.

**Why this priority**: Several tests involving order/query traversal fail (order, query, v1nr), indicating iterator function issues.

**Independent Test**: Run order routine with test arrays and verify traversal produces same sequence as YottaDB.

**Acceptance Scenarios**:

1. **Given** an array with subscripts "A", "B", "C", **When** $ORDER is called from "", **Then** it returns "A", then "B", then "C", then ""
2. **Given** reverse $ORDER with -1 direction, **When** called from "C", **Then** it returns "B", then "A", then ""
3. **Given** a multi-level array, **When** $QUERY is called, **Then** it returns fully-qualified references in collation order

---

### User Story 8 - Configure xfail for LIM-015 Z-Extensions (Priority: P3)

As a test maintainer, I need tests using YDB Z-extensions with zero VistA usage to be properly marked as expected failures so CI remains green while documenting known limitations.

**Why this priority**: 12 tests use ZSYSTEM, $ZTRAP, $ZVERSION, or $ZPREVIOUS which are explicitly out of scope per LIM-015. These should not show as failures since they are documented limitations.

**Independent Test**: Run pytest and verify the 12 LIM-015 tests are marked xfail with appropriate reason.

**Acceptance Scenarios**:

1. **Given** a test using ZSYSTEM command, **When** test runs, **Then** it is marked xfail with reason "LIM-015: ZSYSTEM command not supported"
2. **Given** a test using $ZTRAP, **When** test runs, **Then** it is marked xfail with reason "LIM-015"
3. **Given** the full test suite, **When** all LIM-015 tests are configured, **Then** exactly 12 tests change from FAILED to xfail

---

### User Story 9 - Fix Codegen Syntax Errors (Priority: P1)

As a developer transpiling MUMPS to Python, I need generated Python code to always be syntactically valid.

**Why this priority**: The vv2vnia test produces Python with an unmatched parenthesis. This is a critical bug - generated code must be valid.

**Independent Test**: Transpile vv2vnia and verify Python parses without syntax errors.

**Acceptance Scenarios**:

1. **Given** the vv2vnia MUMPS routine, **When** transpiled, **Then** the generated Python is syntactically valid
2. **Given** any MUMPS routine accepted by the parser, **When** transpiled, **Then** the generated Python parses without SyntaxError
3. **Given** the fix is applied, **When** vv2vnia executes, **Then** output matches YottaDB reference

---

### User Story 10 - Implement Missing Expression Types and SET Targets (Priority: P2)

As a developer transpiling MUMPS to Python, I need all MUMPS expression types and SET targets to be handled by codegen.

**Why this priority**: MZWriteSubscriptAll and ExtendedGlobalBracket SET target are not implemented, causing specific test failures.

**Independent Test**: Transpile largeexp1 and per02276, verify no NotImplementedError is raised.

**Acceptance Scenarios**:

1. **Given** MUMPS code using `WRITE *` subscript (MZWriteSubscriptAll), **When** transpiled, **Then** appropriate Python code is generated
2. **Given** `SET ^|env|GLOBAL(sub)=value` (ExtendedGlobalBracket), **When** transpiled, **Then** the extended global reference is handled correctly
3. **Given** either expression type, **When** transpiled and executed, **Then** behavior matches YottaDB

---

### User Story 11 - Review Merge Suite Infrastructure (Priority: P3)

As a test maintainer, I need the merge test suite to correctly load helper routines and produce comparable output.

**Why this priority**: 33 tests fail with "No result for X" suggesting infrastructure issues rather than codegen bugs. These may require test harness updates rather than m2py changes.

**Independent Test**: Verify merge suite helper routines are being loaded and executed before primary test routines.

**Acceptance Scenarios**:

1. **Given** the merge gbl2gbl subtest, **When** helper routines are identified, **Then** they are loaded with the test routine
2. **Given** merge test output, **When** compared against outref, **Then** comparison accounts for infrastructure differences
3. **Given** investigation reveals codegen issues, **Then** those are addressed; if infrastructure issues, **Then** test harness is updated (with human approval)

---

### Edge Cases

- What happens when argumentless KILL is used within a nested scope (DO block inside FOR)? *→ See US1 acceptance scenarios*
- How does argumentless NEW interact with formal parameters? *→ Formal params are separate from NEW scope per ANSI 8.2.16*
- What is the collation order for empty string in sorts-after comparison? *→ Empty string is lowest; see US2 scenario 1*
- How does LHS $PIECE handle null delimiters or positions beyond current string length? *→ See US3; extends string with delimiters per ANSI 7.2.3.4*
- What happens when FOR loop bounds are expressions that change during iteration? *→ Bounds evaluated once at loop start per ANSI 8.2.9; see US6*
- How does $ORDER behave with undefined starting subscript? *→ Returns first subscript per ANSI 7.2.3.1; see US7 scenario 1*

## Requirements *(mandatory)*

### Functional Requirements

#### TRAMPOLINE Strategy Enhancement (10 tests)

- **FR-001**: System MUST detect routines containing argumentless KILL or argumentless NEW during analysis
- **FR-002**: System MUST generate dictionary-based variable storage in RoutineState when FR-001 conditions are met
- **FR-003**: Argumentless KILL MUST clear all entries in the variables dictionary
- **FR-004**: Argumentless NEW MUST push current variables to a stack and clear the dictionary (save+clear phase)
- **FR-005**: On QUIT after argumentless NEW, system MUST restore variables from the stack (restore phase; complements FR-004)

#### Missing Operators (1 test)

- **FR-006**: System MUST implement the sorts-after operator (`]]`) using MUMPS collation order
- **FR-007**: MUMPS collation MUST order: empty string < canonical numerics < non-numeric strings

#### LHS $PIECE Extensions (3 tests)

- **FR-008**: LHS $PIECE MUST support NakedGlobal as the first argument
- **FR-009**: LHS $PIECE MUST support Indirection as the first argument ✅ *Implemented via unified indirection API*
- **FR-010**: LHS $PIECE with globals MUST read, modify, and write back the value

#### Codegen Bug Fixes (1 test)

- **FR-011**: Generated Python MUST always be syntactically valid ✅ *Fixed: f-string trap resolved*
- **FR-012**: System MUST validate generated code can be parsed before returning

#### Expression and SET Target Support (2 tests)

- **FR-013**: System MUST handle MZWriteSubscriptAll expression type (`WRITE *X` outputs ASCII code of X)
- **FR-014**: System MUST handle ExtendedGlobalBracket as a SET target (`SET ^|env|GLOBAL(sub)=value` uses environment-extended global reference; for m2py, environment parameter is ignored and global is accessed normally)

#### LIM-015 xfail Configuration (12 tests)

- **FR-015**: Tests using ZSYSTEM, $ZTRAP, $ZVERSION, $ZPREVIOUS MUST be skipped via limitation mapping
- **FR-016**: ROUTINE_LIMITATIONS dict in tests/functional/conftest.py MUST include all 12 affected routine names mapped to "LIM-015"

#### Unified Variable System Requirements (from Spec 018 - MERGED)

The following requirements were addressed by the Unified Variable System merge:

- **FR-VS-001**: System MUST distinguish between Name Indirection (SET, WRITE, KILL) and Argument Indirection (IF, FOR args) ✅ *Implemented: IndirectionContext enum*
- **FR-VS-002**: Argument Indirection MUST evaluate expression strings, not treat them as truth values ✅ *Implemented: evaluate_expression()*
- **FR-VS-003**: Multi-level indirection MUST resolve with per-level subscript application ✅ *Implemented: per_level_subscripts parameter*
- **FR-VS-004**: Subscripts MUST be canonicalized: `A(1)`, `A(01)`, `A(1.0)`, `A("1")` same node ✅ *Implemented: SubscriptCanonicalizer*
- **FR-VS-005**: Name translation MUST be consistent between codegen and runtime ✅ *Implemented: NameTranslator shared*
- **FR-VS-006**: Variable access MUST use unified scope abstraction ✅ *Implemented: CurrentScope*
- **FR-VS-007**: Name Indirection with invalid result MUST raise VarExpectedError ✅ *Implemented: core/exceptions.py*

#### Behavioral Bug Fixes (75 tests - detailed investigation required)

- **FR-017**: Arithmetic operations MUST produce numeric values matching YottaDB output formatting. *Validation*: arith.m, barith.m outrefs; ANSI 7.1.4 (numeric interpretation)
- **FR-018**: Pattern matching MUST correctly evaluate all MUMPS pattern codes and alternations. *Validation*: pattst.m, v1pat.m, vv2pat*.m outrefs; ANSI 8.4.2 (pattern match)
- **FR-019**: FOR loops MUST iterate with correct bounds, increments, and termination conditions including step=0 edge cases. *Validation*: for.m, forloop.m, v1for*.m outrefs; ANSI 8.2.9 (FOR)
- **FR-020**: $ORDER and $QUERY MUST traverse arrays/globals in correct MUMPS collation order (empty < canonicalnumeric < string). *Validation*: order.m, query.m outrefs; ANSI 7.1.4.5 (collation)
- **FR-021**: Boolean and comparison operations MUST match MUMPS truth semantics (numeric interpretation of strings). *Validation*: ANSI 1.2.4 (truth value); ✅ *Partially addressed by argument indirection fix*
- **FR-022**: Variable storage and retrieval MUST preserve correct values across scopes including cross-routine DO calls. *Validation*: v1prgd.m, v1do.m outrefs; ✅ *Addressed by CurrentScope*

#### Testing Requirements

- **FR-023**: Unit tests MUST be added for each new operator (sorts-after collation edge cases)
- **FR-024**: Unit tests MUST be added for argumentless KILL/NEW with cross-label GOTO
- **FR-025**: Unit tests MUST be added for LHS $PIECE with globals and indirection
- **FR-026**: For complex bug fixes requiring multiple iterations, additional unit tests MUST exercise edge cases beyond the functional tests

#### MUGJ Suite Testing Requirements

- **FR-027**: MUGJ test suite MUST execute all routines serially in YDB driver order ✅ *Implemented*
- **FR-028**: MUGJ test execution MUST preserve shared state ($Y, $X, globals) across routines ✅ *Implemented*
- **FR-029**: MUGJ test output comparison MUST match outref byte-for-byte (no whitespace normalization) ✅ *Implemented*
- **FR-030**: Other test suites (basic, mvts, merge) MAY continue using per-test execution with whitespace normalization

### Key Entities

- **RoutineState**: Dataclass carrying variables across label boundaries in TRAMPOLINE strategy
  - When routine uses argumentless KILL/NEW: uses `_locals: dict` instead of individual fields
  - When routine uses argumentless NEW: adds `_new_stack: list` for save/restore

- **Collation Order**: MUMPS-specific ordering used by sorts-after operator
  - Empty string is lowest
  - Canonical numeric values next (sorted numerically including negatives)
  - Non-numeric strings last (sorted by character code)

- **Core Module Components** (from Spec 018):
  - `NameTranslator` (`core/names.py`): MUMPS↔Python identifier translation
  - `SubscriptCanonicalizer` (`core/subscripts.py`): Subscript normalization
  - `CurrentScope` (`core/scope.py`): Unified variable access abstraction
  - `IndirectionResolver` (`core/indirection.py`): Runtime @-expression resolution
  - `VarRef` (`core/scope.py`): Structured variable reference representation

## Success Criteria *(mandatory)*

### Measurable Outcomes

#### Original Criteria

- **SC-001**: All 10 TRAMPOLINE strategy tests (v1call, v1nst3, v1ov, v1prgd, v1seq, vv2lcc1, vv2vnib, fifo, per02397, setpiece) pass with output matching YottaDB
- **SC-002**: The `relation` test passes (sorts-after operator implemented)
- **SC-003**: Tests vv2lhp1, vv2lhp2, vv2vnic pass (LHS $PIECE with globals/indirection)
- **SC-004**: Test vv2vnia passes with syntactically valid Python generated ✅ *Fixed: f-string trap resolved*
- **SC-005**: Tests largeexp1 and per02276 pass (expression types and SET targets)
- **SC-006**: 12 LIM-015 tests are marked xfail instead of failing (CI remains green)
- **SC-007**: All behavioral bug tests pass (100% of output mismatches resolved)
- **SC-008**: All test failures from the original 147 are resolved (passed, appropriately xfailed with documented limitation, or skipped with infrastructure note), resulting in zero unexpected failures in the YDB test suite
- **SC-009**: No new test regressions - all previously passing tests continue to pass
- **SC-010**: New unit tests provide coverage for edge cases in sorts-after, argumentless KILL/NEW, and LHS $PIECE

#### Unified Variable System Criteria (from Spec 018 - MERGED)

- **SC-VS-001**: All MUGJ indirection tests (V1IDNM1-3, VV2VNI*, V1XECA1, V1IDARG1, V1IDDO1, V1IDGO1) pass ✅ *Implemented*
- **SC-VS-002**: Name translation produces identical results in codegen and runtime ✅ *Implemented*
- **SC-VS-003**: Subscript canonicalization matches YottaDB behavior ✅ *Implemented*
- **SC-VS-004**: Multi-level indirection with per-level subscripts produces YottaDB-identical results ✅ *Implemented*
- **SC-VS-005**: Argument indirection (`I @A` where A="1=0") correctly evaluates expression (returns false) ✅ *Implemented*

#### MUGJ Test Suite Criteria

- **SC-MUGJ-001**: MUGJ test suite runs as single unit with serial execution ✅ *Implemented*
- **SC-MUGJ-002**: MUGJ output matches outref byte-for-byte including whitespace ✅ *Implemented*
- **SC-MUGJ-003**: All 72 MUGJ driver routines transpile successfully except 9 with documented limitations: V1AC (LIM-015 $ZVersion), V1IDGO1/V1IDGOA/V1IDGOB (indirect multi-target GOTO), V1NST1/V1NST2 (UNRESOLVED GOTO per Spec 012), V1OV/V1PC1/V1PCA (external multi-target GOTO)
- **SC-MUGJ-004**: MUGJ full suite execution completes in under 60 seconds

## Assumptions

- The failure-analysis.md document accurately categorizes all 147 test failures
- Behavioral bug fixes may require iterative debugging; some may have shared root causes
- Merge suite "No result" failures may be infrastructure issues requiring human review before changes
- $ZPOSITION special variable is YDB-specific and may be added to LIM-015 if investigation confirms zero VistA usage
- The `$i` special variable error (vv2lcf2) needs investigation - may be $IO device variable
- UNRESOLVED GOTO tests (v1nst1, v1nst2) are NOT part of the 10 TRAMPOLINE tests in SC-001; they reference Spec 012 indirect GOTO which may need its own implementation effort
- The Unified Variable System (Spec 018) resolves most indirection-related test failures; remaining failures are likely due to other bugs
- MUGJ serial execution is necessary for whitespace matching; other suites may not need this approach

## Clarifications

### Session 2026-01-26

- **Spec 018 Merge**: The Unified Variable System from Spec 018 has been merged into this branch, providing shared `core/` components for variable access, indirection, subscripts, and name translation
- **MUGJ Test Approach**: MUGJ tests now run as a single unit to preserve whitespace matching across routines; this approach may not be needed for other suites

## Human Review Required

The following situations MUST stop and request human input before proceeding:

1. **Impossible fixes**: If a test failure cannot be resolved without violating MUMPS semantics or Python constraints
2. **Massive architectural changes**: If a fix would require restructuring core components beyond the TRAMPOLINE enhancement already scoped
3. **Test infrastructure changes**: Any modifications to functional test drivers, suite definitions, or conftest.py
4. **Limitations updates**: Any additions or changes to limitations.py
5. **Unit test modifications**: Any changes to existing unit test cases (new tests are allowed without approval)
6. **Scope expansion**: If investigation reveals the fix requires implementing features explicitly marked as out of scope (e.g., LIM-015 Z-extensions)
7. **Shared root cause discovery**: If multiple failures trace to a fundamental design issue requiring significant rework
