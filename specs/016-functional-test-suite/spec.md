# Feature Specification: Functional Test Suite

**Feature Branch**: `016-functional-test-suite`  
**Created**: 2026-01-21  
**Status**: Draft  
**Input**: User description: "Build a pytest-based functional test framework that runs MUMPS tests the same way as YDBTest/YottaDB CI, comparing transpiled output byte-for-byte against outref content"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Complete Test Suite (Priority: P1)

As a developer, I want to run the full functional test suite to validate that m2py transpilation produces byte-for-byte identical output to YottaDB reference output, so I can confirm semantic correctness of the transpiler.

**Why this priority**: This is the core value of the feature - validating transpiler correctness against authoritative reference output.

**Independent Test**: Run `uv run pytest tests/functional/ -v` and verify tests pass/fail with clear comparison against outref content.

**Acceptance Scenarios**:

1. **Given** the functional test suite is configured, **When** I run `uv run pytest tests/functional/`, **Then** each test compares m2py output against corresponding outref content
2. **Given** a test suite has multiple entry-point routines (like mugj calling V1WR, V1CMT, etc.), **When** the test runs, **Then** all routines execute in the same order as the original test driver
3. **Given** m2py output exactly matches outref content, **When** the test completes, **Then** the test passes
4. **Given** m2py output differs from outref content, **When** the test completes, **Then** the test fails with a clear diff showing the discrepancy

---

### User Story 2 - Run Individual Test Suites (Priority: P2)

As a developer, I want to run individual test suites (mugj, basic, mvts, etc.) independently, so I can focus debugging efforts on specific areas.

**Why this priority**: Enables focused development and faster iteration when working on specific MUMPS features.

**Independent Test**: Run `uv run pytest tests/functional/mugj/ -v` and see only mugj-related tests execute.

**Acceptance Scenarios**:

1. **Given** multiple test suites exist, **When** I run `uv run pytest tests/functional/mugj/`, **Then** only mugj tests execute
2. **Given** a test suite directory, **When** I examine its structure, **Then** it follows YDBTest conventions (inref/, outref/, u_inref/)

---

### User Story 3 - Clean Legacy Integration Tests (Priority: P3)

As a developer, I want the obsolete parser/ASG integration tests removed, so the test suite reflects the current testing strategy and doesn't confuse future contributors.

**Why this priority**: Cleanup task that removes technical debt and confusion, but doesn't block core functionality.

**Independent Test**: Verify `tests/integration/` no longer contains the old parsing-focused tests; the directory may remain if other integration tests are needed.

**Acceptance Scenarios**:

1. **Given** the old integration tests exist in tests/integration/, **When** the migration completes, **Then** parsing-focused tests (test_ydb_suites.py, test_mugj.py) are removed
2. **Given** test helpers exist that are still useful, **When** cleanup occurs, **Then** reusable helpers are preserved or migrated

---

### User Story 4 - Handle Known Limitations Gracefully (Priority: P2)

As a developer, I want tests for known m2py limitations to be clearly marked as expected failures (xfail), so the test suite distinguishes between bugs and documented limitations.

**Why this priority**: Essential for a usable test suite that doesn't produce noise from known issues.

**Independent Test**: Run a test for a known limitation and verify it's marked xfail with appropriate reason.

**Acceptance Scenarios**:

1. **Given** a test exercises a known m2py limitation, **When** the test runs, **Then** it is marked as xfail with a reference to the limitation documentation
2. **Given** limitations are documented in docs/limitations.md (sourced from limitations.py data), **When** marking tests as xfail, **Then** the xfail reason references the specific limitation

---

### Edge Cases

- What happens when outref contains YDB infrastructure markers?
  - **Path placeholders** (`##TEST_PATH##`, `##SOURCE_PATH##`, `##REMOTE_TEST_PATH##`, `##REMOTE_SOURCE_PATH##`, `##IN_TEST_PATH##`): Strip lines containing these as they reference YDB installation paths
  - **Conditional output blocks** (`##SUSPEND_OUTPUT ...`, `##ALLOW_OUTPUT ...`): Strip these directives and their conditional content (e.g., replication setup, collation warnings)
  - **Preamble content**: Strip everything before first `YDB>` prompt (database creation, GDE setup, replication initialization)
- How does the system handle tests that use global variables (which require a YDB database)?
  - Most mugj tests (248 files) and basic tests (60 files) use globals (`^variable`)
  - m2py's in-memory global storage should handle these without a real database
  - If database-specific behavior causes failures, mark as xfail with appropriate limitation reference
- How does the system handle tests that depend on interactive input or non-deterministic behavior?
  - Tests using READ command (V1READA, V1READB, VV2READ): already commented out in mugj driver
  - Tests using HANG command (V1HANG): already commented out in mugj driver  
  - Tests using $RANDOM (V1RANDA, V1RANDB, VVERAND): already commented out in mugj driver
  - Any remaining non-deterministic tests: mark as xfail
- What happens when a routine calls external routines that don't exist?
  - Execution should continue to subsequent commands (matching MUMPS behavior), and missing routines should be tracked
- How are whitespace differences handled?
  - Byte-for-byte matching is required; whitespace differences are genuine failures

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST execute MUMPS routines via m2py transpilation and capture output
- **FR-002**: System MUST compare transpiled output byte-for-byte against outref reference files
- **FR-003**: System MUST preserve execution order matching the original YDBTest driver scripts (u_inref/*.csh)
- **FR-004**: System MUST support running complete test suites or individual suites via pytest selection
- **FR-005**: System MUST strip YDB infrastructure from outref before comparison:
  - Path placeholders: `##TEST_PATH##`, `##SOURCE_PATH##`, `##REMOTE_TEST_PATH##`, `##REMOTE_SOURCE_PATH##`, `##IN_TEST_PATH##`
  - Conditional directives: `##SUSPEND_OUTPUT`, `##ALLOW_OUTPUT`, `##TEST_AWK`
  - Preamble: All content before first `YDB>` prompt (dbcreate, GDE, mupip output)
- **FR-006**: System MUST mark tests for known limitations as pytest xfail, referencing `src/m2py/limitations.py` IDs:
  - LIM-003: MWAPI SSVNs (`^$EVENT`, `^$WINDOW`, `^$DISPLAY`)
  - LIM-005: VIEW command implementation-specific keywords
  - LIM-012: Unknown Z-extensions from other MUMPS implementations
  - LIM-015: Zero-VistA-usage YDB Z-commands (ZBREAK, ZCOMPILE, etc.)
- **FR-007**: System MUST report clear diffs when output doesn't match expected
- **FR-008**: System MUST handle multi-routine test sequences where one driver calls multiple routines
- **FR-009**: System MUST remove obsolete parsing-focused integration tests from tests/integration/
- **FR-010**: System MUST preserve test directory structure compatible with YDBTest (inref/, outref/, u_inref/)
- **FR-011**: System MUST support global variable operations using m2py's in-memory global storage (no external database required)

### Key Entities

- **Test Suite**: A collection of related tests (mugj, basic, mvts, etc.) following YDBTest directory structure
- **Reference Output (outref)**: Expected output from YottaDB execution, used as the source of truth
- **Test Driver (u_inref)**: Shell script defining execution order and routine invocations
- **Routine (inref)**: MUMPS source files to be transpiled and executed
- **Limitation Registry** (`src/m2py/limitations.py`): Canonical source of limitation IDs for xfail markers

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All test suites in tests/functional/ can be discovered and run via pytest
- **SC-002**: Tests that pass produce output matching outref content byte-for-byte (after stripping YDB infrastructure)
- **SC-003**: Tests for known limitations are marked xfail with limitation ID from limitations.py
- **SC-004**: Developer can run full suite in under 5 minutes on standard hardware
- **SC-005**: Individual suite tests can be run independently via pytest -k or path selection
- **SC-006**: Test failure messages clearly show expected vs actual output differences
- **SC-007**: Legacy integration tests (test_ydb_suites.py, test_mugj.py) are removed
- **SC-008**: Test suite provides clear pass/fail status without manual interpretation
- **SC-009**: Tests using global variables work without requiring an external YDB database

## Assumptions

- YottaDB outref files are the authoritative source of truth for expected output
- Tests requiring interactive input (READ), timing (HANG), or randomness ($RANDOM) are already excluded in test drivers or will be marked xfail
- The m2py transpiler can execute all routines needed by the test suites (gaps will be marked as xfail with limitation IDs)
- m2py's in-memory global storage provides sufficient database functionality for test suites
- UTF-8 encoding is used consistently for all source and output files
- Line ending normalization (CRLF vs LF) may be needed for cross-platform compatibility
