# Feature Specification: Test Suite Consolidation & VistA Compatibility

**Feature Branch**: `013-test-consolidation`  
**Created**: 2026-01-17  
**Status**: Draft  
**Input**: Resolve all 286 xfail test stubs through deletion (redundant stubs), conversion (working features to real tests), and implementation (all VistA-utilized features). Goal: zero xfail tests with complete VistA compatibility.

---

## User Scenarios & Testing

### User Story 1 - Developer Runs Test Suite with Clear Results (Priority: P1)

As a developer working on m2py, I run the test suite and see clear pass/fail results without misleading xfail markers. Every test represents a real assertion about working functionality. No test duplicates exist, and I can trust that passing tests represent verified behavior.

**Why this priority**: The current 286 xfail stubs create noise and confusion. Many mark features that already work, making it hard to know the true state of the codebase. This is the foundation for all other work.

**Independent Test**: Run `uv run pytest` and verify xfail count reaches zero. Run specific test files and verify no duplicate tests exist across files.

**Acceptance Scenarios**:

1. **Given** a developer runs the test suite, **When** tests complete, **Then** zero xfail tests remain - all features are either implemented with passing tests or explicitly documented in limitations.md.

2. **Given** a test stub was marked DELETE in the audit, **When** I check the corresponding spec-aligned test file, **Then** I find equivalent or more comprehensive coverage of that functionality.

3. **Given** a test stub was marked CONVERT in the audit, **When** the conversion completes, **Then** the test uses `execute_mumps` fixture and validates actual runtime behavior against expected output.

---

### User Story 2 - Label Fall-Through Behavior Works (Priority: P2)

As a MUMPS developer migrating code to Python via m2py, I expect implicit label fall-through to work correctly. When I call a label that does not end with QUIT/GOTO/HALT, execution should continue to the next label automatically, matching MUMPS semantics.

**Why this priority**: Fall-through is a fundamental MUMPS control flow pattern used extensively in production code (e.g., VistA). Without it, many real routines will not execute correctly.

**Independent Test**: Execute a routine with multiple labels where only the last ends with QUIT. Verify output shows all labels executed in sequence.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine with labels TEST, FOR, END where only END has QUIT, **When** I call `D TEST`, **Then** all three labels execute in sequence outputting A, B, C.

2. **Given** a MUMPS routine where a middle label does return a value via QUIT, **When** I call the first label, **Then** execution stops at that QUIT and returns the value correctly.

3. **Given** external entry via `D FOR^ROUTINE` (starting at FOR), **When** executed, **Then** fall-through continues from FOR to END as expected.

---

### User Story 3 - Working Features Have Real Tests (Priority: P3)

As a maintainer, I want every implemented feature to have tests that assert actual runtime behavior (not just code generation shape). When I modify codegen, the tests catch regressions by executing MUMPS code and comparing against expected YDB output.

**Why this priority**: Tests using `generate_python` only check code structure, not correctness. Converting these to `execute_mumps` creates real regression protection.

**Independent Test**: Pick a CONVERT stub, run `uv run python utils/validate.py` to verify the feature works, then check the converted test asserts actual output.

**Acceptance Scenarios**:

1. **Given** a stub marked CONVERT (e.g., `test_division`), **When** the conversion completes, **Then** the test calls `execute_mumps` with MUMPS code and asserts the result equals expected output.

2. **Given** 49 stubs marked CONVERT in the audit, **When** all conversions complete, **Then** all 49 tests pass using `execute_mumps` fixture with real output assertions.

---

### User Story 4 - All VistA Features Implemented (Priority: P4)

As a project maintainer, I want all MUMPS features used in the VistA codebase to be fully implemented, enabling m2py to transpile real VistA routines. Every feature with any VistA usage must work correctly.

**Why this priority**: VistA compatibility is the project's primary goal. Analysis of 33,951 VistA routine files identified specific features that MUST work: $ASCII/$CHAR (31%), transactions (29%), READ (13%), $JUSTIFY (13%), LOCK (10%), and many others.

**Independent Test**: After implementation, run `uv run python utils/validate.py` against sample VistA routines using each feature category.

**Acceptance Scenarios**:

1. **Given** a VistA routine using $ASCII or $CHAR functions, **When** transpiled and executed, **Then** output matches YottaDB reference output exactly.

2. **Given** a VistA routine using transaction processing (TSTART/TCOMMIT), **When** transpiled and executed, **Then** transaction semantics are correctly implemented.

3. **Given** any feature with confirmed VistA usage (including Z-commands like ZWRITE, ZLINK), **When** the feature is tested, **Then** it produces correct output matching YottaDB behavior.

---

### Edge Cases

- What happens when fall-through depth exceeds normal limits? (VistA worst case is 197 frames, Python limit is 1000 - verified safe)
- What happens when deleting a stub that has no spec-aligned equivalent? (Must verify coverage exists first - this spec requires that check)
- What happens when a CONVERT stub fails unexpectedly? (Run validate.py first to verify feature actually works before converting)
- What happens when QUIT returns a value through fall-through chain? (Use return statement to propagate values correctly)
- What happens with duplicate Z-command test stubs across files? (Delete duplicates, keep one canonical version)

---

## Requirements

### Functional Requirements - Stub Cleanup

- **FR-001**: System MUST delete approximately 44 redundant test stubs (36 explicit + 8 Z-command duplicates) that duplicate functionality covered by existing spec-aligned tests.
- **FR-002**: Before deleting any stub, the equivalent spec-aligned test MUST be verified to exist and provide equal or better coverage.
- **FR-003**: System MUST convert approximately 49 test stubs from `generate_python` fixture to `execute_mumps` fixture with real output assertions. The actual count from the gaps audit is ~39-49 depending on how partial implementations are categorized.
- **FR-004**: Before converting any stub, the feature MUST be verified working via `uv run python utils/validate.py`.
- **FR-005**: System MUST NOT create duplicate tests - each behavior should be tested in exactly one place.
- **FR-006**: All remaining xfail tests MUST document what implementation is missing and what spec section applies.

### Functional Requirements - Label Fall-Through

- **FR-007**: System MUST detect when a label body does not end with unconditional exit (QUIT, GOTO, HALT).
- **FR-008**: System MUST generate explicit fall-through calls to the next label when needed.
- **FR-009**: Fall-through calls MUST propagate return values correctly via return statement.
- **FR-010**: External entry points (e.g., `D LABEL^ROUTINE`) MUST support fall-through from their entry point.
- **FR-011**: Fall-through MUST NOT cause stack overflow for realistic MUMPS programs (VistA max depth approximately 197).

### Functional Requirements - High-Priority Implementation Gaps

- **FR-012**: System MUST implement the exponentiation operator for expressions like `W 2**3` producing output 8.

### Functional Requirements - VistA Critical Features (>10% usage)

- **FR-013**: System MUST implement $ASCII function returning ASCII code of first character.
- **FR-014**: System MUST implement $CHAR function returning character for ASCII code(s).
- **FR-015**: System MUST implement transaction processing commands (TSTART, TCOMMIT, TROLLBACK) via database abstraction layer using native support: YottaDB uses yottadb.tp(), IRIS uses native transaction API, Memory backend simulates for testing.
- **FR-016**: System MUST implement READ command for terminal input operations.
- **FR-017**: System MUST implement $JUSTIFY function for right-justified string formatting.
- **FR-018**: System MUST implement USE command for device selection.
- **FR-019**: System MUST implement LOCK command via database abstraction layer with three backends: (a) Memory backend using in-process lock table for unit tests, (b) YottaDB backend using native lock_incr()/lock_decr(), (c) IRIS backend as stub.
- **FR-020**: System MUST implement $TRANSLATE function for character translation.
- **FR-021**: System MUST implement $TEXT function returning source code text for labels (9,050 VistA files, 26.7% usage). Requires line mapping infrastructure from Spec 007.

### Functional Requirements - VistA High-Priority Features (1-10% usage)

- **FR-022**: System MUST implement OPEN and CLOSE commands for device I/O.
- **FR-023**: System MUST implement exclusive NEW syntax (NEW except for named variables).
- **FR-024**: System MUST implement JOB command using subprocess/multiprocessing to spawn separate Python processes that connect to the same database backend.
- **FR-025**: System MUST implement $FNUMBER function for numeric formatting.
- **FR-026**: System MUST implement error processing ($ECODE, $ETRAP) for structured error handling.

### Functional Requirements - VistA Medium-Priority Features (<1% but used)

- **FR-027**: System MUST implement $REVERSE function for string reversal.
- **FR-028**: System MUST implement timeout infrastructure for LOCK, READ, OPEN, and JOB commands (sets $TEST on success/failure per MUMPS spec). 8 related test stubs.
- **FR-029**: System MUST implement SSVNs ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE for querying system state (15 VistA files). Uses database abstraction layer where applicable.
- **FR-030**: System MUST implement pattern match alternation syntax (e.g., `X?1(1N,1A)2N`) (37 VistA files).
- **FR-031**: System MUST implement $NEXT function (deprecated but still used) returning next subscript (42 VistA files). May emit deprecation warning.
- **FR-032**: System MUST implement VIEW command for implementation-defined operations (6 VistA files). Keywords may vary by backend.
- **FR-033**: System MUST implement BREAK command for debugger interface (2 VistA files).

### Functional Requirements - Math Functions (language completeness)

- **FR-034**: System MUST implement $EXP function (exponential).
- **FR-035**: System MUST implement $LOG function (natural logarithm).
- **FR-036**: System MUST implement $SQRT function (square root).
- **FR-037**: System MUST implement trigonometric functions ($SIN, $COS, $TAN).
- **FR-038**: System MUST implement inverse trigonometric functions ($ARCSIN, $ARCCOS, $ARCTAN).

### Functional Requirements - Z-Commands with VistA Usage

- **FR-039**: System MUST implement ZWRITE command for variable display (54 VistA files).
- **FR-040**: System MUST implement ZLINK command for routine linking (20 VistA files).
- **FR-041**: System MUST implement ZSHOW command for system information display (9 VistA files).
- **FR-042**: System MUST implement ZKILL command for alias killing (5 VistA files).
- **FR-043**: System MUST implement ZGOTO command for stack unwinding (2 VistA files).
- **FR-044**: System MUST implement ZHALT command for process termination (1 VistA file).
- **FR-045**: System MUST implement $ZERROR special variable for YDB error information (121 VistA files).

### Key Entities

- **xfail stub**: A pytest test marked with `@pytest.mark.xfail` indicating expected failure. Has disposition (DELETE/CONVERT/IMPLEMENT) based on audit.
- **Spec-aligned test**: A test in file matching pattern `test_sX_X_X_*.py` or `test_spec_*.py` with MUMPS spec section references in docstrings.
- **execute_mumps fixture**: Pytest fixture that transpiles MUMPS, executes generated Python, and returns output for assertion.
- **Fall-through label**: A label whose body does not end with unconditional exit, causing implicit continuation to next label.
- **VistA-utilized feature**: Any MUMPS feature with confirmed usage in the VistA codebase (33,951 routine files analyzed).
- **Parser limitation**: A feature explicitly unsupported by design, documented in limitations.md with LIM-XXX ID.
- **Database backend**: Abstraction layer for globals storage and locking. Implementations: MemoryBackend (testing), YottaDBBackend (production), IRISBackend (future).

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: xfail test count reaches zero (all 286 stubs resolved through DELETE, CONVERT, or IMPLEMENT).
- **SC-002**: Zero test duplicates exist across the test suite (verified via test name search).
- **SC-003**: All CONVERT stubs produce tests that execute MUMPS code and assert actual output (not code structure).
- **SC-004**: Fall-through test case TEST to FOR to END produces output ABC when calling D TEST.
- **SC-005**: Exponentiation expression `W 2**3` produces output 8.
- **SC-006**: Test suite execution time does not increase by more than 20 percent (implementation adds tests).
- **SC-007**: All VistA-utilized features pass validation against YottaDB reference output.
- **SC-008**: No stub is deleted without verified spec-aligned coverage existing.
- **SC-009**: $ASCII("A") returns 65, $CHAR(65) returns "A".
- **SC-010**: Transaction TSTART/TCOMMIT sequence completes without error on all database backends (Memory simulated, YottaDB native, IRIS stub).
- **SC-011**: LOCK command works correctly with all three database backends (Memory for tests, YottaDB for production, IRIS stub exists). JOB spawns separate processes.
- **SC-012**: All math functions return correct values (e.g., $SQRT(4)=2, $LOG(1)=0).
- **SC-013**: Z-commands with VistA usage (ZWRITE, ZLINK, ZSHOW, ZKILL, ZGOTO, ZHALT) all function correctly.
- **SC-014**: $TEXT(LABEL) returns first line of label's source code. $TEXT(LABEL+n) returns nth line after label.
- **SC-015**: Timeout syntax for LOCK, READ, OPEN, and JOB commands sets $TEST correctly (1 on success, 0 on timeout).
- **SC-016**: SSVNs ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE return correct system state information.
- **SC-017**: Pattern alternation `"AB"?1(1A,1N)1(1A,1N)` returns 1 (matches).
- **SC-018**: $NEXT(^A("")) returns first subscript of ^A (deprecated function works).
- **SC-019**: VIEW command executes without error (implementation-defined behavior).
- **SC-020**: BREAK command triggers debugger or no-op depending on environment.

---

## Assumptions

1. **validate.py accuracy**: The `utils/validate.py` script correctly compares m2py output against YottaDB reference output.
2. **Spec-aligned test completeness**: Existing spec-aligned tests (test_spec_009_*.py, test_s7_2_logical_operators.py, etc.) provide complete coverage for features they test.
3. **Fall-through safety**: Python 1000-frame stack limit is sufficient for realistic MUMPS programs (VistA worst case approximately 197 verified).
4. **Fixture availability**: The `execute_mumps` and `execute_expr` fixtures are available and working for runtime test assertions.
5. **Gap audit accuracy**: The gaps-stubs.md audit correctly categorizes DELETE/CONVERT/IMPLEMENT dispositions.
6. **VistA usage accuracy**: The VistA-M repository (33,951 files) is representative of production VistA usage patterns.
7. **YottaDB compatibility**: YottaDB behavior is the reference standard for all feature implementations.
8. **Single-usage verification**: Features with very low usage (1-5 files) will be verified against source to rule out false positives.
9. **Database abstraction compatibility**: IRIS locking and transaction semantics are compatible with YottaDB's (research required to validate abstraction interface design).

---

## Dependencies

**Completed Prerequisites** (Specs 004-012 are complete):
- **Spec 006 (Cross-Label GOTO)**: ✅ TRAMPOLINE infrastructure available for GOTO-related stubs.
- **Spec 007 (Computed Offsets)**: ✅ Line dispatch infrastructure available for `D LABEL+N` patterns.
- **Spec 008 (External Calls)**: ✅ Cross-routine infrastructure available for fall-through with external entry.

---

## VistA Usage Reference

Implementation priority is based on **complexity and related groupings** rather than usage percentage (since 100% must be completed). VistA usage data informs validation priority but not implementation order.

### Usage Statistics (for reference only)

| Feature | Files | Usage % |
|---------|-------|---------|
| $ASCII/$CHAR | 10,564 | 31.1% |
| TSTART/TCOMMIT | 9,967 | 29.4% |
| $TEXT | 9,050 | 26.7% |
| READ | 4,556 | 13.4% |
| $JUSTIFY | 4,487 | 13.2% |
| USE | 3,598 | 10.6% |
| LOCK | 3,457 | 10.2% |
| $TRANSLATE | 2,962 | 8.7% |
| OPEN/CLOSE | 2,452 | 7.2% |
| Exclusive NEW | 1,812 | 5.3% |
| $ETRAP/$ECODE | 837 | 2.5% |
| JOB | 508 | 1.5% |
| $FNUMBER | 460 | 1.4% |
| TROLLBACK | 134 | 0.4% |
| Exponentiation (**) | 125 | 0.4% |
| $ZERROR | 121 | 0.4% |
| ZWRITE | 54 | 0.16% |
| $NEXT (deprecated) | 42 | 0.12% |
| $REVERSE | 39 | 0.11% |
| Pattern alternation | 37 | 0.11% |
| Math functions | ~24 | 0.07% |
| ZLINK | 20 | 0.06% |
| SSVNs (^$GLOBAL etc) | 15 | 0.04% |
| ZSHOW | 9 | 0.03% |
| VIEW | 6 | 0.02% |
| ZKILL | 5 | 0.01% |
| ZGOTO | 2 | <0.01% |
| BREAK | 2 | <0.01% |
| ZHALT | 1 | <0.01% |

---

## Out of Scope

Based on VistA codebase analysis (33,951 routine files) and documented parser limitations:

### Z-Commands with Zero VistA Usage

The following YDB Z-commands have **confirmed zero usage** in VistA and are excluded:
- ZBREAK - debugging breakpoints (0 files)
- ZCOMPILE - routine compilation (0 files)
- ZHELP - help system (0 files)
- ZMESSAGE - message handling (0 files)
- ZPRINT - routine printing (0 files)
- ZSTEP - single-step debugging (0 files)
- ZSYSTEM - system command execution (0 files)
- ZTRIGGER - trigger management (0 files)
- ZALLOCATE - resource allocation (0 files)
- ZDEALLOCATE - resource deallocation (0 files)

These may be implemented on demand if encountered in real codebases.

### Parser Limitations (documented in limitations.md)

The following features are explicitly unsupported per parser design decisions and have no test stubs:

- **LIM-001**: Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER) - zero VistA usage
- **LIM-002**: THEN command - zero VistA usage
- **LIM-003**: MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY) - 3 VistA files, but requires X11.6 windowing system not feasible in Python transpiler
- **LIM-004**: Deprecated functions ($DEXTRACT, $DPIECE) - never standardized
- **LIM-009**: RLOAD/RSAVE commands - zero VistA usage
- **LIM-011**: ^$LIBRARY SSVN - zero VistA usage
- **LIM-012**: Unknown Z-extensions from other implementations (Caché/IRIS, MicroM, DSM)
- **LIM-013**: ASSIGN command - zero VistA usage

### Library Functions (§7.1.6.5) - Zero VistA Usage

The 68 §7.1.6.5 standard library function stubs (character, string, math, matrix operations) have **confirmed zero VistA usage** of the standard form. VistA uses custom extrinsic functions instead. These are excluded from this spec but may be implemented on demand.

These raise `MUMPSParseError` or have undefined codegen behavior as documented.

---

## Clarifications

### Session 2026-01-17

- Q: For ~190 IMPLEMENT stubs requiring new feature work (FR-012 through FR-045), what is the preferred phasing strategy relative to DELETE/CONVERT cleanup? → A: Implement incrementally by feature category, converting related stubs as each feature is implemented. Group by related work and size phases by complexity rather than VistA criticality (since 100% must be completed).
- Q: The 7 Z-commands with VistA usage (FR-039 to FR-044 plus $ZERROR FR-045) have very low usage (0.01%-0.4%). What implementation depth is required? → A: Fully implement all 7 Z-commands with VistA usage (ZWRITE, ZLINK, ZSHOW, ZKILL, ZGOTO, ZHALT, $ZERROR). No stubs or NotImplementedError - complete working implementations.
- Q: What is the relationship between this spec (013) and prior specs (004-012)? → A: Specs 004-012 are already complete. This spec (013) builds on that completed foundation and focuses on remaining gaps, test consolidation, and achieving zero xfail.
- Q: VistA uses LOCK for real multi-user record protection. What approach for LOCK/JOB implementation? → A: LOCK is part of the database abstraction layer. Implementations needed: (1) Memory backend - simple in-process lock table for unit tests, (2) YottaDB backend - uses native yottadb.lock_incr()/lock_decr() via YDBPython, (3) IRIS backend - stub for future. JOB uses subprocess/multiprocessing to spawn separate Python processes connecting to the same database backend.
- Q: Should transactions (TSTART/TCOMMIT/TROLLBACK) use native database support or custom Python logic? → A: Transactions go through the database abstraction layer using native support: YottaDB uses yottadb.tp(), IRIS uses its native transaction API. Memory backend simulates transactions for testing. Research IRIS semantics for locking and transactions to ensure the abstraction interface is correct for both backends.
- Q: Are there additional database primitives beyond LOCK and transactions that need database abstraction? → A: Yes, based on YottaDB/IRIS doc research: (1) $INCREMENT - atomic increment without locking (YottaDB: yottadb.incr(), IRIS: iris.IRIS.increment()), (2) SSVNs ^$LOCK and ^$JOB - may query lock/process state from database (research needed), (3) $TLEVEL special variable - returns transaction nesting level from database (YottaDB: part of transaction state, IRIS: iris.IRIS.getTLevel()). These should use database abstraction where the backend provides native support.
- Q: Cross-check verification: Does spec cover all ~205 KEEP gaps from gaps-stubs.md audit? → A: Yes, verified. All items with VistA usage now have FRs: Exponentiation (FR-012), Transactions (FR-015), Error processing (FR-026), I/O (FR-022), LOCK (FR-019), JOB (FR-024), Exclusive NEW (FR-023), $TEXT (FR-021), Timeouts (FR-028), Z-commands with VistA usage (FR-039-044, $ZERROR FR-045), Math functions (FR-034-038), SSVNs (FR-029, 15 files), Pattern alternation (FR-030, 37 files), $NEXT (FR-031, 42 files), VIEW (FR-032, 6 files), BREAK (FR-033, 2 files). Computed offsets covered by completed Spec 007. Library functions (68 stubs) have zero VistA usage of standard §7.1.6.5 forms. Exception: MWAPI SSVNs (3 files) excluded - requires X11 windowing not feasible in transpiler.
