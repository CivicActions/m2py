# Feature Specification: Complete xfail Test Elimination

**Feature Branch**: `014-xfail-elimination`  
**Created**: 2025-01-19  
**Status**: Draft  
**Input**: User description: "Complete xfail test elimination and limitation error verification"
**Reference**: [codegen-plan.md Spec 014 section](../codegen-plan.md)

## Problem Statement

M2PY currently has **163 xfail-marked tests** representing incomplete implementations or missing error handling. This technical debt obscures the true state of the project and allows silent failures.

**Goal**: Eliminate ALL xfail markers by either:
1. **Implementing the feature** (tests pass because code works), or
2. **Raising explicit `NotImplementedError`** with limitation ID (tests pass by verifying the error)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Zero xfail Tests in CI (Priority: P1)

A developer runs `uv run pytest` and sees all tests pass with zero xfail markers remaining. This proves that:
1. All implemented features have complete test coverage
2. All documented limitations properly raise `NotImplementedError` 
3. No silent failures exist in codegen output

**Why this priority**: xfail tests represent technical debt - either incomplete implementations or missing error handling. Eliminating them ensures the codebase accurately reflects what works and what doesn't.

**Independent Test**: Run `uv run pytest --collect-only -m xfail -q` and verify count is 0.

**Acceptance Scenarios**:

1. **Given** the full test suite, **When** running `uv run pytest`, **Then** all tests pass (no xfail, no failures)
2. **Given** a documented limitation (LIM-XXX), **When** code using that feature is transpiled, **Then** codegen raises `NotImplementedError` with the limitation ID in the message
3. **Given** any test currently marked xfail, **When** the underlying implementation is fixed, **Then** the xfail marker is removed (not left as xpass)

---

### User Story 2 - Limitation Errors Are Explicit (Priority: P1)

When a developer writes MUMPS code that uses an unsupported feature (per docs/limitations.md), the transpiler raises a clear `NotImplementedError` instead of silently producing broken Python code.

**Why this priority**: Silent failures are worse than explicit errors. A developer must know immediately when they are using unsupported syntax.

**Independent Test**: For each PARSES_OK limitation, write a test that verifies `NotImplementedError` is raised with the limitation ID.

**Acceptance Scenarios**:

1. **Given** MUMPS code using `^$EVENT` (LIM-003), **When** transpiling, **Then** raises `NotImplementedError` containing "LIM-003"
2. **Given** MUMPS code using `^$LIBRARY` (LIM-011), **When** transpiling, **Then** raises `NotImplementedError` containing "LIM-011"
3. **Given** MUMPS code using `TROLLBACK:n` (LIM-016), **When** transpiling, **Then** raises `NotImplementedError` containing "LIM-016"
4. **Given** MUMPS code using ANSI library functions (LIM-014), **When** transpiling, **Then** raises `NotImplementedError` containing "LIM-014"

---

### User Story 3 - Test Organization Matches Spec Structure (Priority: P2)

Tests are organized in directories matching MUMPS ANSI Standard sections (s6_routine, s7_expressions, s8_commands, s9_charset), making it easy to find tests for any spec section.

**Why this priority**: Clear organization reduces cognitive load and ensures coverage gaps are visible.

**Independent Test**: Run `ls tests/unit/codegen/` and verify directory structure matches expected pattern.

**Acceptance Scenarios**:

1. **Given** a MUMPS spec section (e.g., 8.2.5 FOR), **When** looking for codegen tests, **Then** tests exist at `tests/unit/codegen/s8_commands/test_s8_2_05_for.py`
2. **Given** any test file, **When** reading its module docstring, **Then** it contains a reference to the MUMPS ANSI Standard section it tests

---

### User Story 4 - Deferred Features Have Tracking (Priority: P3)

Features intentionally deferred (zero VistA usage) are documented with limitation IDs and have stub tests that verify the `NotImplementedError` is raised, ensuring they will not be accidentally "implemented" with silent failures.

**Why this priority**: Prevents scope creep while maintaining explicit contracts about what is not supported.

**Independent Test**: For each LIM-015/LIM-016 item, verify a test exists that checks for `NotImplementedError`.

**Acceptance Scenarios**:

1. **Given** a LIM-015 Z-command (e.g., ZBREAK), **When** transpiling, **Then** raises `NotImplementedError` referencing LIM-015
2. **Given** a LIM-016 feature (e.g., $TRESTART), **When** transpiling, **Then** raises `NotImplementedError` referencing LIM-016

---

### Edge Cases

- What happens when a test xpasses (passes when marked xfail)? Remove the xfail marker and verify the implementation is complete
- What happens when an implementation is partially complete? Split into passing tests (implemented parts) and xfail tests (unimplemented parts)
- What happens when a limitation is implemented in the future? Remove xfail markers, update docs/limitations.md, and run full test suite

## Requirements *(mandatory)*

### Functional Requirements

**Reference**: See [codegen-plan.md](../codegen-plan.md) Spec 014 section for detailed task breakdowns.

---

### Phase 1: Core Language Semantics (HIGH PRIORITY) - Tasks 14.1-14.4

**VistA-critical features that must work for real-world MUMPS code.**

*Task 14.1: Special Variables Completion (4 tests)*
- **FR-001**: Codegen MUST implement $TLEVEL special variable for transaction tracking
- **FR-002**: Codegen MUST implement $QUIT context awareness ($QUIT=1 in extrinsic, $QUIT=0 in DO)
- **FR-003**: Codegen MUST implement $TEXT with external routine references

*Task 14.2: Indirection Completion (3 tests)* - **45,271 VistA usages**
- **FR-004**: Codegen MUST implement subscript indirection (@var in subscript position)
- **FR-005**: Codegen MUST implement argument indirection (@var as command argument)
- **FR-006**: Codegen MUST implement runtime resolution of indirection

*Task 14.3: Transaction Commands (4 tests)*
- **FR-007**: Codegen MUST implement TSTART basic transaction start
- **FR-008**: Codegen MUST implement TCOMMIT basic transaction commit
- **FR-009**: Codegen MUST implement TROLLBACK basic rollback (no level argument)
- **FR-010**: Codegen MUST implement TRESTART command
- **Note**: TROLLBACK:n and $TRESTART have zero VistA usage - raise NotImplementedError (LIM-016)

*Task 14.4: Error Processing (1 test)*
- **FR-011**: Codegen MUST implement error propagation across label calls

---

### Phase 2: Control Flow Gaps (MEDIUM PRIORITY) - Tasks 14.5-14.7

**These require cross-label infrastructure (Spec 006/007 dependencies).**

*Task 14.5: DO Command Advanced (6 tests)*
- **FR-012**: Codegen MUST implement DO external routine (D LABEL^ROUTINE)
- **FR-013**: Codegen MUST implement scope strategy selection (PURE_FUNCTION, SUBROUTINE, FUNCTION_WITH_OUTPUTS, REQUIRES_RUNTIME)
- **FR-014**: Codegen MUST implement partial indirection (D @var^ROUTINE)
- **Prerequisite**: Spec 008 ✅ COMPLETE

*Task 14.6: GOTO Advanced (5 tests)*
- **FR-015**: Codegen MUST implement computed GOTO (G LABEL+offset)
- **FR-016**: Codegen MUST implement state machine fallback for has_unstructured_goto
- **FR-017**: Codegen MUST implement state machine variable scope preservation
- **FR-018**: Codegen MUST enforce same-level execution for GOTO targets (M45 error)
- **FR-019**: Codegen MUST implement partial indirection (G @var)
- **Prerequisite**: Spec 006 ✅ COMPLETE

*Task 14.7: Computed Offsets (6 tests)* - **3,643 VistA usages**
- **FR-020**: Codegen MUST implement DO/GOTO with literal offset (D LABEL+1, G LABEL+1)
- **FR-021**: Codegen MUST implement offset with variable (D LABEL+var)
- **FR-022**: Codegen MUST implement offset with global (D LABEL+^GLO)
- **FR-023**: Codegen MUST implement offset with function (D LABEL+$L(x))
- **FR-024**: Codegen MUST implement offset arithmetic (D LABEL+(expr))
- **Prerequisite**: Spec 007 ✅ COMPLETE

---

### Phase 3: Data Operations (MEDIUM PRIORITY) - Tasks 14.8-14.10

*Task 14.8: MERGE Command Globals (2 tests)* - **1,676 VistA usages**
- **FR-025**: Codegen MUST implement MERGE local to global (M ^GLO=LOCAL)
- **FR-026**: Codegen MUST implement MERGE global to global (M ^GLO1=^GLO2)

*Task 14.9: Naked Reference Edge Cases (5 tests)*
- **FR-027**: Codegen MUST raise error for naked reference without prior global
- **FR-028**: Codegen MUST implement naked references in $DATA, $ORDER, MERGE, LOCK

*Task 14.10: KILL Global (1 test)*
- **FR-029**: Codegen MUST implement KILL global (K ^GLO)

---

### Phase 4: Routine Structure (LOW PRIORITY) - Tasks 14.11-14.12

*Task 14.11: Routine Metadata (3 tests)*
- **FR-030**: Codegen MUST generate routine docstring from MUMPS header
- **FR-031**: Codegen MUST implement empty label translation (_preamble)
- **FR-032**: Codegen MUST preserve comments in generated code

*Task 14.12: Extrinsic Functions Advanced (3 tests)*
- **FR-033**: Codegen MUST implement module caching for external routine imports
- **FR-034**: Codegen MUST implement cross-routine variable passing semantics
- **FR-035**: Codegen MUST implement routine name translation (%, numeric prefixes)

---

### Phase 5: Advanced Features (LOW PRIORITY) - Tasks 14.13-14.16

*Task 14.13: Language Semantics Misc (5 tests)*
- **FR-036**: Codegen MUST implement $TEST NOT stacked for label call
- **FR-037**: Codegen MUST implement $TEST NOT stacked for DO with arguments
- **FR-038**: Codegen MUST implement $TEST NOT stacked for XECUTE
- **FR-039**: Codegen MUST implement DO block execution level tracking
- **FR-040**: Codegen MUST implement extrinsic function return semantics

*Task 14.14: Postconditions Advanced (3 tests)*
- **FR-041**: Codegen MUST implement argument postconditions as independent
- **FR-042**: Codegen MUST implement postcondition evaluation order
- **FR-043**: Codegen MUST implement postcondition side effects handling

*Task 14.15: XECUTE Runtime (3 tests)*
- **FR-044**: Codegen MUST implement runtime global access in XECUTE
- **FR-045**: Codegen MUST implement ZOSF lookup table optimization
- **FR-046**: Codegen MUST implement ZOSF fallback to runtime

*Task 14.16: Character Set section 9 (3 tests)*
- **FR-047**: Codegen MUST implement M character encoding
- **FR-048**: Codegen MUST handle graphic characters correctly
- **FR-049**: Codegen MUST handle control characters correctly

---

### Phase 6: Deferred Features - Explicit Error Handling - Tasks 14.17-14.23

**These features are documented in LIM-014/LIM-015/LIM-016 and will NOT be functionally
implemented. Codegen MUST raise explicit `NotImplementedError` with the limitation ID
so tests pass and developers get clear feedback.**

*Task 14.17: Extended Math Library (57 tests) - LIM-014*
- **FR-050**: All ANSI Math library functions ($$%SIN^MATH, etc.) MUST raise `NotImplementedError("LIM-014: ...")`
- Categories: Trigonometric (12), Inverse trig (10), Exponential (8), Angle conversion (4), Complex numbers (13), Matrix (10)

*Task 14.18: String/Character Library (11 tests) - LIM-014*
- **FR-051**: String functions (crc16, crc32, crcccitt, format, produce, replace) MUST raise `NotImplementedError("LIM-014: ...")`
- **FR-052**: Character functions (collate, compare, lower, upper, patcode) MUST raise `NotImplementedError("LIM-014: ...")`

*Task 14.19: YDB Z-Commands (15 tests) - LIM-015*
- **FR-053**: Z-commands (ZALLOCATE, ZBREAK, ZCOMPILE, ZCONTINUE, ZEDIT, ZHELP, ZMESSAGE, ZPRINT, ZSTEP, ZSYSTEM, ZTRIGGER) MUST raise `NotImplementedError("LIM-015: ...")`
- **FR-054**: Z-functions ($ZDATE, $ZMESSAGE, $ZWIDTH) MUST raise `NotImplementedError("LIM-015: ...")`

*Task 14.20: $NEXT Function (3 tests) - MEDIUM PRIORITY*
- **FR-055**: $NEXT function MUST either implement with $ORDER semantics OR raise deprecation error
- **VistA Usage**: 578 files - consider implementing rather than error

*Task 14.21: Legacy Pre-1995 Behavior (2 tests) - LIM-016*
- **FR-056**: Pre-1984 variable scope behavior MUST raise `NotImplementedError("LIM-016: ...")`
- **FR-057**: Pre-1990 array copy behavior MUST raise `NotImplementedError("LIM-016: ...")`

*Task 14.22: Device/IO Commands (3 tests) - LIM-016*
- **FR-058**: Device parameters codegen MUST raise `NotImplementedError("LIM-016: ...")`
- **FR-059**: $KEY subscripts codegen MUST raise `NotImplementedError("LIM-016: ...")`
- **FR-060**: $KEY value codegen MUST raise `NotImplementedError("LIM-016: ...")`

*Task 14.23: Limitation Error Test Coverage (7 tests)*
- **FR-061**: MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY) MUST raise `NotImplementedError("LIM-003: ...")`
- **FR-062**: ^$LIBRARY SSVN MUST raise `NotImplementedError("LIM-011: ...")`
- **FR-063**: TROLLBACK:n (level argument) MUST raise `NotImplementedError("LIM-016: ...")`
- **Note**: $DEXTRACT, $DPIECE (LIM-004) and $TRESTART (LIM-016) already raise correctly

---

### Dependencies

| Prerequisite | Tasks Affected | Status |
|--------------|---------------|--------|
| Spec 006 (Cross-label GOTO) | Task 14.6 | ✅ COMPLETE |
| Spec 007 (Computed offsets) | Task 14.7 | ✅ COMPLETE |
| Spec 008 (External calls) | Task 14.5 | ✅ COMPLETE |
| Database Backend | Tasks 14.3, 14.8, 14.10 | Stub implementation OK |

**Note**: All specs 001-013 are 100% complete. No tasks are blocked.

---

### Test Count Summary

| Phase | Tasks | Tests | Priority |
|-------|-------|-------|----------|
| Phase 1 | 14.1-14.4 | 12 | HIGH |
| Phase 2 | 14.5-14.7 | 17 | MEDIUM |
| Phase 3 | 14.8-14.10 | 8 | MEDIUM |
| Phase 4 | 14.11-14.12 | 6 | LOW |
| Phase 5 | 14.13-14.16 | 14 | LOW |
| Phase 6 | 14.17-14.23 | 99 | ERROR HANDLING |
| Misc | Cross-cutting | 7 | MEDIUM |
| **Total** | | **163** | |

### Key Entities

- **xfail Test**: A pytest test marked with `@pytest.mark.xfail` indicating known-incomplete implementation
- **Limitation**: A documented unsupported feature with ID (LIM-XXX) and type (PARSE_ERROR, PARSES_OK, INFORMATIVE, REDIRECT)
- **PARSES_OK Limitation**: Parser accepts syntax but codegen must raise `NotImplementedError`
- **Spec-Aligned Test**: Test file organized by MUMPS ANSI Standard section number (e.g., s7_1_5 for section 7.1.5)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `uv run pytest --collect-only -m xfail -q | tail -1` returns "0 tests collected"
- **SC-002**: All 163 currently-xfail tests either pass (implementation complete) or are converted to passing tests that verify `NotImplementedError` is raised
- **SC-003**: Every PARSES_OK limitation (LIM-003, LIM-004, LIM-011, LIM-014, LIM-015, LIM-016) has at least one test verifying `NotImplementedError` with limitation ID in message
- **SC-004**: No test duplicates exist - each behavior is tested exactly once in its spec-aligned location
- **SC-005**: `uv run pytest` completes with 0 failures, 0 xfail, 0 xpass
- **SC-006**: Phase 6 tests (99 tests) all use pattern: `pytest.raises(NotImplementedError, match="LIM-XXX")`

## Assumptions

- The 163 xfail tests represent the complete scope of incomplete implementations (see Test Count Summary)
- Implementation gaps are in codegen layer (not parser or ASG analysis)
- Deferred features (LIM-014, LIM-015, LIM-016) should remain deferred but with explicit `NotImplementedError`
- Test organization follows established pattern: `tests/unit/codegen/s{section}_{name}/test_s{section}_{subsection}_{name}.py`
- Spec 006, 007, 008 dependencies may delay Phase 2 tasks

## Out of Scope

- Parser changes (all syntax is already accepted)
- ASG analysis changes (all semantic information is already computed)
- Runtime library implementation (existing runtime is sufficient)
- VistA integration testing (separate suite)
- MUGJ test suite execution (handled separately)

## Constraints

- No new xfail markers should be introduced
- Tests that xpass should have xfail marker removed immediately
- Implementation changes must not break any currently-passing tests
- All error messages must include the limitation ID for traceability
