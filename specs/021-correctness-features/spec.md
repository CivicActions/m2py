# Feature Specification: Phase 3 — Correctness Fixes & New Features

**Feature Branch**: `021-correctness-features`  
**Created**: 2026-02-10  
**Status**: Draft  
**Input**: User description: "Phase 3 Correctness Fixes and New Features — Implement error handling (ETRAP/ECODE, ZTRAP/ZSTATUS/ZPOSITION), LOCK indirection, TSTART restart variables, READ maxlen, SSVNs, ZDATE, ZLINK/ZSYSTEM, strict LVUNDEF, STACK introspection, extended global references, and YDB I/O SVNs"  
**Source**: [refactoring-plan.md](../refactoring-plan.md) — Phase 3 section

## Overview

Phase 3 implements correctness fixes and new MUMPS/YDB features on top of the refactored foundation (Phase 1) and codegen (Phase 2). Unlike the prior phases, which restructured existing code, Phase 3 is primarily **new functionality**: new runtime methods, new codegen handlers, new intrinsic special variable (ISV) implementations, and new command support. The items address real gaps that affect VistA compatibility and MUMPS standard compliance.

The deliverables span 5 independent tracks:

- **Track A (Error Handling):** Full `$ETRAP`/`$ECODE` stack-unwinding semantics, YDB-specific `$ZTRAP`/`$ZSTATUS`/`$ZPOSITION`, and `$STACK` per-level introspection
- **Track B (LOCK + Transactions):** LOCK indirection implementation (C-05, 222 VistA files) and TSTART restart variable support (F-05, 193 VistA files)
- **Track C (Standalone Functions + Compliance):** `$ZDATE` date formatting, ZLINK/ZSYSTEM commands, and unconditional LVUNDEF error enforcement (MUMPS standard M6 compliance)
- **Track D (SVNs, SSVNs, Globals):** Structured special variable nodes (`^$JOB`, `^$ROUTINE`, etc.), YDB I/O environment SVNs (`$ZSEARCH`, `$ZRO`, `$ZJOB`, `$ZMESSAGE`), and extended global references (`^|"env"|NAME`, `^[UCI,VOL]NAME`)
- **Track E (READ):** READ with `#maxlen` and `$KEY` termination character support

All tracks touch distinct subsystems and are highly parallelizable. Tracks A, B, C, and E each touch different command handlers within `codegen/statements.py`, minimizing conflict risk.

## Clarifications

### Session 2026-02-10

- Q: Should LVUNDEF (undefined local variable access) require a `--strict-lvundef` CLI flag, or should it always raise an M6 error with no flag? → A: Always error, no flag needed. MUMPS standard (ANSI 1995 §7.2) mandates M6 errors, YDB defaults to LVUNDEF errors, and VistA expects this (0 of 33,951 VistA files use VIEW "NOUNDEF" to suppress it). The constitution entry "Undefined variables return empty string" must be updated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Transpiled MUMPS programs continue producing identical output for existing functionality (Priority: P1)

A developer transpiles any MUMPS routine through m2py. All previously working functionality produces identical output. The full test suite passes with zero failures, zero xfails, and zero skips.

**Why this priority**: New features must not break existing behavior. This is the foundational invariant for the entire phase.

**Independent Test**: Run the full test suite (`uv run pytest`). Every test passes. YDB validation suite produces matching output.

**Acceptance Scenarios**:

1. **Given** the complete m2py test suite, **When** all Phase 3 changes are applied and `uv run pytest` is executed, **Then** 100% of tests pass with zero failures, zero xfails, and zero skips.
2. **Given** a set of MUMPS routines from the YDBTest suite that do not exercise Phase 3 features, **When** transpiled and executed, **Then** the output matches YottaDB reference output exactly as it did before Phase 3.

---

### User Story 2 — MUMPS error trapping with `$ETRAP` and `$ECODE` works correctly (Priority: P1)

A developer transpiles a MUMPS routine that uses `$ETRAP`/`$ECODE` for error handling (as VistA's Kernel error handler `^%ZTER` does). When an error occurs, the error trap fires, `$ECODE` contains the error code in the correct `,Merr,` format, and QUIT from the error trap unwinds to the stack level where `$ETRAP` was set.

**Why this priority**: Error handling is foundational infrastructure. ~500 VistA files depend on `$ETRAP`/`$ECODE`. Without correct error trapping, VistA Kernel error handling cannot function.

**Independent Test**: Transpile and run a MUMPS routine that sets `$ETRAP`, triggers an undefined variable error, and verifies `$ECODE` format and stack unwinding behavior. Compare output against YottaDB.

**Acceptance Scenarios**:

1. **Given** a routine that sets `SET $ETRAP="D ERR^ROUTINE"`, **When** a MUMPS error occurs (e.g., undefined variable access with strict mode), **Then** the `$ETRAP` code is executed in the error context.
2. **Given** an error occurs, **When** `$ECODE` is read, **Then** it contains the error code surrounded by commas (e.g., `,M6,` for undefined local variable).
3. **Given** an error trap fires at call depth 3 where `$ETRAP` was set at depth 1, **When** the trap code executes QUIT, **Then** execution unwinds to depth 1 (the level where `$ETRAP` was set).
4. **Given** `NEW $ETRAP` in a subroutine, **When** an error occurs in that subroutine, **Then** the inner `$ETRAP` handles the error. If the inner trap does not clear `$ECODE`, the outer trap fires after the subroutine returns.
5. **Given** an error during error trap execution (nested error), **When** the nested error occurs, **Then** `$ECODE` accumulates both error codes and the error propagates up the stack correctly.

---

### User Story 3 — YDB error handling with `$ZTRAP`, `$ZSTATUS`, `$ZPOSITION` works correctly (Priority: P1)

A developer transpiles VistA Kernel routines that use YDB-specific error handling. `$ZTRAP` fires on error, `$ZSTATUS` contains the error message, and `$ZPOSITION` identifies the error location.

**Why this priority**: 45 VistA files use `$ZTRAP`, 42 use `$ZSTATUS`, 17 use `$ZPOSITION`. These form a cohesive subsystem used alongside `$ETRAP`/`$ECODE` in VistA Kernel error handling. Implementing F-03 and F-09 together is most efficient since they share infrastructure.

**Independent Test**: Transpile a routine that sets `$ZTRAP`, triggers an error, and reads `$ZSTATUS` and `$ZPOSITION`. Compare against YottaDB.

**Acceptance Scenarios**:

1. **Given** a routine that sets `SET $ZTRAP="GOTO ERR"`, **When** a MUMPS error occurs, **Then** execution transfers to the `ERR` label.
2. **Given** `$ZTRAP` is set and `$ETRAP` is not, **When** an error occurs, **Then** `$ZTRAP` is used for error handling (ZTRAP takes precedence only when ETRAP is empty).
3. **Given** an error has occurred, **When** `$ZSTATUS` is read, **Then** it contains the full error message string from the last error.
4. **Given** an error at label `MAIN+5^MYROUTINE`, **When** `$ZPOSITION` is read, **Then** it contains `"MAIN+5^MYROUTINE"` identifying the error location.

---

### User Story 4 — `$STACK` per-level introspection returns call stack information (Priority: P2)

A developer transpiles VistA error handling routines that use `$STACK(n)` and `$STACK(n,"PLACE")` to build stack traces. The runtime provides correct call stack information.

**Why this priority**: 21 VistA files use `$STACK(` for error diagnostics. This completes the error handling subsystem from Stories 2–3.

**Independent Test**: Transpile a routine with nested DO calls, query `$STACK`, `$STACK(n,"PLACE")`, and `$STACK(n,"MCODE")`. Compare against YottaDB.

**Acceptance Scenarios**:

1. **Given** a routine at call depth 3, **When** `$STACK` is read (no arguments), **Then** it returns `3`.
2. **Given** the same routine, **When** `$STACK(2,"PLACE")` is read, **Then** it returns the `routine+label+offset` at stack level 2.
3. **Given** the same routine, **When** `$STACK(2,"MCODE")` is read, **Then** it returns the MUMPS source line at stack level 2.
4. **Given** an error has occurred, **When** `$STACK(-1)` is read, **Then** it returns the error context information.

---

### User Story 5 — LOCK indirection resolves and acquires locks correctly (Priority: P1)

A developer transpiles a VistA routine that uses `LOCK @X` where X contains a lock name. The lock is correctly resolved and acquired at runtime instead of being silently skipped.

**Why this priority**: LOCK indirection is silently skipped today (C-05). 222 VistA files use LOCK with indirection. This is a correctness fix — silent data corruption risk in concurrent scenarios.

**Independent Test**: Transpile `S X="^GLO(1)" L +@X` and verify the lock is acquired. Verify `$TEST` is set correctly for timeout forms.

**Acceptance Scenarios**:

1. **Given** `SET X="^GLO(1)" LOCK +@X`, **When** transpiled and run, **Then** the lock on `^GLO(1)` is acquired.
2. **Given** `SET X="^GLO(1)" LOCK +@X:0`, **When** transpiled and run and the lock is unavailable, **Then** `$TEST` is set to 0.
3. **Given** `SET X="^GLO(1)" LOCK -@X`, **When** transpiled and run, **Then** the lock on `^GLO(1)` is released.
4. **Given** multi-level indirection (`SET Y="X" SET X="^GLO" LOCK +@(@Y)`), **When** transpiled and run, **Then** the lock on `^GLO` is acquired after resolving both indirection levels.
5. **Given** the codegen source, **When** inspected at the `_generate_lock_target()` handler for indirection, **Then** it emits a call to `_rt.lock_indirected()` instead of a comment.

---

### User Story 6 — TSTART with restart variables snapshots locals for transaction support (Priority: P2)

A developer transpiles a VistA routine that uses `TSTART (X,Y)` to snapshot specific variables at transaction start. Per YDB semantics, TROLLBACK reverses global database changes but does NOT restore local variables — the snapshot is retained for future TRESTART support. TCOMMIT and TROLLBACK both discard the local snapshot.

**Why this priority**: 193 VistA files use `TS (vars)` and 28 use `TS *`. This is essential for VistA database update routines that depend on transaction semantics.

**Independent Test**: Transpile a routine that sets variables, starts a transaction with restart vars, modifies the variables, then rolls back. Verify globals are restored but local variables are NOT restored (YDB-verified behavior).

**Acceptance Scenarios**:

1. **Given** `SET X=1,Y=2 TSTART (X) SET X=99,Y=99 TROLLBACK`, **When** transpiled and run, **Then** both X and Y remain 99 — TROLLBACK does NOT restore local variables per YDB semantics. The snapshot of X is discarded.
2. **Given** `SET X=1 TSTART * SET X=99 TROLLBACK`, **When** transpiled and run, **Then** X remains 99. TROLLBACK reverses global changes only; local snapshot is discarded without restoring.
3. **Given** `SET X=1 TSTART (X) SET X=99 TCOMMIT`, **When** transpiled and run, **Then** X remains 99 and the snapshot is discarded on TCOMMIT (snapshot is only useful for future TRESTART).
4. **Given** nested transactions `TSTART (X) ... TSTART (Y) ... TROLLBACK`, **When** the inner TROLLBACK executes, **Then** the inner snapshot (Y) is discarded. Locals are NOT restored.

---

### User Story 7 — READ with `#maxlen` limits input length and sets `$KEY` (Priority: P2)

A developer transpiles a VistA routine using `READ X#5` to accept up to 5 characters of input. The input is correctly limited and `$KEY` reflects the termination character.

**Why this priority**: 88 VistA files use `READ X#n` for menu prompts and fixed-length field input. This is a user interaction feature essential for VistA menu navigation.

**Independent Test**: Transpile a routine with `READ X#5`, provide input, and verify X contains at most 5 characters and `$KEY` is set.

**Acceptance Scenarios**:

1. **Given** `READ X#5` with piped input `"ABCDEFGH"`, **When** transpiled and run, **Then** X contains `"ABCDE"` (first 5 characters only).
2. **Given** `READ X#5` with piped input `"AB\n"` (newline before maxlen), **When** transpiled and run, **Then** X contains `"AB"` (newline terminates early).
3. **Given** `READ X#5:3` combining maxlen with timeout, **When** transpiled and run with input arriving within the timeout, **Then** X contains at most 5 characters and `$TEST` is set to 1.
4. **Given** `READ X#5` completes, **When** `$KEY` is read, **Then** it contains the character that terminated the read (newline if Enter was pressed, or empty string if maxlen was reached without a terminator).

---

### User Story 8 — `$ZDATE` formats `$HOROLOG` values into human-readable dates (Priority: P2)

A developer transpiles a VistA routine using `$ZDATE($H,"MM/DD/YYYY")` to format the current date. The function returns a correctly formatted date string.

**Why this priority**: 26 VistA files use `$ZDATE` directly. Well-defined semantics with standard date arithmetic — low risk, high VistA compatibility value.

**Independent Test**: Transpile a routine that calls `$ZDATE` with various format strings and compare output against YottaDB.

**Acceptance Scenarios**:

1. **Given** `WRITE $ZDATE(66337)`, **When** transpiled and run, **Then** the output is `"08/16/22"` (default MM/DD/YY format for August 16, 2022).
2. **Given** `WRITE $ZDATE(66337,"DD MON YEAR")`, **When** transpiled and run, **Then** the output matches YDB's format for that date with the given format string.
3. **Given** `WRITE $ZDATE(66337,"YYYY-MM-DD")`, **When** transpiled and run, **Then** the output is `"2022-08-16"` (ISO date format).
4. **Given** `WRITE $ZDATE("66337,45296","YYYY-MM-DD 24:60:SS")`, **When** transpiled and run, **Then** the output includes both date and time components.

---

### User Story 9 — ZLINK and ZSYSTEM commands execute correctly (Priority: P2)

A developer transpiles VistA Kernel routines that use ZLINK to reload routines and ZSYSTEM to execute shell commands.

**Why this priority**: ZLINK (16 VistA files) and ZSYSTEM (6 files) are used in system administration and routine management. Straightforward to implement.

**Independent Test**: Transpile routines using ZLINK and ZSYSTEM. Verify ZLINK reloads a module and ZSYSTEM executes a shell command.

**Acceptance Scenarios**:

1. **Given** `ZSYSTEM "echo hello"`, **When** transpiled and run, **Then** `hello` is printed to standard output.
2. **Given** `ZSYSTEM ""` (empty command), **When** transpiled and run, **Then** no action is taken and no error occurs.
3. **Given** `ZLINK "ROUTINE"`, **When** transpiled and run with the routine available, **Then** the routine module is reloaded (via `importlib.reload()`).
4. **Given** `ZLINK "NONEXISTENT"`, **When** transpiled and run, **Then** an appropriate error is raised.

---

### User Story 10 — Undefined local variable access raises LVUNDEF error (Priority: P2)

A developer transpiles a MUMPS routine that reads an undefined local variable. The transpiled code raises an `LVUNDEFError` (M6 error), matching both the MUMPS standard (ANSI Section 7.2) and YottaDB's default behavior. This is unconditional — no flag or toggle is needed.

**Why this priority**: The MUMPS standard mandates M6 errors for undefined local access. YDB defaults to LVUNDEF errors. VistA expects this behavior (zero VistA files use VIEW "NOUNDEF" to suppress it). The current m2py behavior (returning empty string) contradicts the standard and YDB. The implementation already exists in `core/scope.py` but is dead code due to `strict_mode` defaulting to False; this change makes it unconditional.

**Independent Test**: Transpile and run a MUMPS routine that reads an undefined variable. Verify it raises an error. Transpile and run a routine where the variable is defined first; verify no error.

**Acceptance Scenarios**:

1. **Given** a routine with `WRITE X` where X is not defined, **When** transpiled and run, **Then** an `LVUNDEFError` (M6) is raised.
2. **Given** `SET X=1 WRITE X`, **When** transpiled and run, **Then** X is defined, no error is raised, and `1` is written.
3. **Given** `NEW X SET X=1 WRITE X`, **When** transpiled and run after NEW scope exits, **Then** accessing X raises `LVUNDEFError` since NEW restores its prior (undefined) state.
4. **Given** existing tests that previously relied on undefined locals returning empty string, **When** Phase 3 is complete, **Then** those tests are updated to either define the variable first or expect the M6 error.

---

### User Story 11 — SSVNs return meaningful information (Priority: P2)

A developer transpiles VistA routines that query structured system variables (`^$JOB`, `^$ROUTINE`, `^$SYSTEM`). The SSVNs return real information instead of stubs.

**Why this priority**: 81 VistA files use SSVNs across 6 types. `^$JOB` (13 files) is used to check if processes are alive; `^$ROUTINE` (12 files) checks if routines exist. Essential for VistA system management.

**Independent Test**: Transpile a routine that queries `^$JOB`, `^$ROUTINE`, and `^$SYSTEM`. Verify meaningful results are returned.

**Acceptance Scenarios**:

1. **Given** `WRITE $DATA(^$JOB($JOB))`, **When** transpiled and run, **Then** it returns a nonzero value (current process exists).
2. **Given** `WRITE $DATA(^$JOB(99999999))`, **When** transpiled and run, **Then** it returns `0` (nonexistent process).
3. **Given** `WRITE $DATA(^$ROUTINE("EXISTINGROUTINE"))`, **When** transpiled and run with that routine loaded, **Then** it returns a nonzero value.
4. **Given** `WRITE ^$SYSTEM("VOL")`, **When** transpiled and run, **Then** it returns a configured volume identifier string.

---

### User Story 12 — YDB I/O and environment SVNs provide real values (Priority: P3)

A developer transpiles VistA Kernel routines that use `$ZSEARCH`, `$ZRO`, `$ZJOB`, and `$ZMESSAGE`. These SVNs return real values instead of stubs or errors.

**Why this priority**: Lower priority — collectively ~50 VistA files. `$ZSEARCH` and `$ZRO` are independent and straightforward. `$ZEOF` is blocked on Phase 4 (I/O device management).

**Independent Test**: Transpile routines using each SVN and verify correct behavior.

**Acceptance Scenarios**:

1. **Given** `WRITE $ZSEARCH("*.m")`, **When** transpiled and run in a directory containing .m files, **Then** it returns the path of the first matching file.
2. **Given** subsequent calls to `$ZSEARCH("")`, **When** transpiled and run, **Then** it returns subsequent matching files, then empty string when exhausted.
3. **Given** `WRITE $ZRO`, **When** transpiled and run, **Then** it returns a configurable routine search path string.
4. **Given** `WRITE $ZJOB`, **When** transpiled and run, **Then** it returns a bitmask reflecting process attributes.
5. **Given** `WRITE $ZMESSAGE(150373210)`, **When** transpiled and run, **Then** it returns the error message text for that YDB error code.

---

### User Story 13 — Extended global references access namespace-qualified globals (Priority: P3)

A developer transpiles VistA Kernel TaskMan routines that use `^[UCI,VOL]%ZTSK(...)` for cross-namespace global access. The extended global reference resolves to the correct namespace.

**Why this priority**: 9–21 VistA files use extended global references. The parser already has textX classes (`ExtendedGlobalPipe`, `ExtendedGlobalBracket`) — the work is in wiring them through analysis, codegen, and runtime.

**Independent Test**: Transpile a routine using both pipe-form and bracket-form extended globals. Verify the correct namespace is applied to global storage.

**Acceptance Scenarios**:

1. **Given** `SET ^|"MYNS"|GLO(1)="val"`, **When** transpiled and run, **Then** the global is stored under namespace `MYNS`.
2. **Given** `WRITE ^|"MYNS"|GLO(1)`, **When** transpiled and run, **Then** `"val"` is returned from the `MYNS` namespace.
3. **Given** `SET ^[UCI,VOL]%ZTSK(1)="data"`, **When** transpiled and run, **Then** the global is stored under the namespace derived from UCI and VOL.
4. **Given** `$DATA(^|"MYNS"|GLO)`, **When** transpiled and run, **Then** it correctly queries the namespaced global.
5. **Given** an extended global reference with the current/default namespace, **When** transpiled and run, **Then** it behaves identically to a non-extended reference.

---

### Edge Cases

- What happens when `$ETRAP` code itself triggers an error? `$ECODE` accumulates both error codes, and the error propagates up the stack. An infinite error loop is detected and terminated after a configurable maximum depth.
- What happens when `$ZTRAP` and `$ETRAP` are both set? `$ETRAP` takes precedence per MUMPS standard. If `$ETRAP` is empty, `$ZTRAP` is used.
- What happens when `$STACK(n)` is called with n greater than current depth? It returns empty string.
- What happens when LOCK indirection resolves to an invalid lock name? An appropriate runtime error is raised.
- What happens when `TSTART (X)` is called but X doesn't exist? The variable is recorded as undefined in the snapshot. On TROLLBACK, the snapshot is discarded (locals are NOT restored per YDB semantics). On future TRESTART, undefined variables in the snapshot would be KILLed if they were SET during the transaction.
- What happens when `READ X#0` is called (maxlen of 0)? X is set to empty string immediately, no input is read.
- What happens when `$ZDATE` receives an invalid `$HOROLOG` value? An appropriate error is raised.
- What happens when ZSYSTEM receives a command that fails? The exit code is available via `$ZSYSTEM` and execution continues.
- What happens when `$ZSEARCH` is called with a pattern matching no files? It returns empty string.
- What happens when an extended global reference uses a nonexistent namespace? The runtime creates the namespace on first write, or returns undefined on read.

## Requirements *(mandatory)*

### Functional Requirements

#### Test Suite Integrity

- **FR-001**: The full test suite MUST pass with zero failures, zero xfails, and zero skips after all Phase 3 changes are applied. Tests MAY be updated to reflect new module paths or restructured internals, but test intent and coverage MUST NOT be reduced.
- **FR-002**: Each new feature or correctness fix MUST include new unit tests covering the implementation in isolation, including edge cases documented in this specification.
- **FR-003**: Each new feature MUST include integration tests that transpile representative MUMPS routines exercising the feature and compare output against YottaDB reference output where applicable.
- **FR-004**: New tests MUST cover edge cases explicitly: empty inputs, boundary values, error conditions, and combinations of features (e.g., `READ X#5:3` combining maxlen with timeout).

#### Track A — Error Handling (F-03, F-09, F-08)

- **FR-010**: The runtime MUST properly accumulate `$ECODE` with surrounding commas in the format `,Merr,` (e.g., `,M6,` for LVUNDEF, `,M9,` for undefined global). Multiple errors accumulate: `,M6,M9,`.
- **FR-011**: When an error occurs and `$ETRAP` is set, the runtime MUST execute the `$ETRAP` code in the error context. QUIT from the error trap MUST unwind execution to the stack level where `$ETRAP` was set.
- **FR-012**: `NEW $ETRAP` MUST be supported. When `$ETRAP` is NEWed in a subroutine, the new value applies within that scope. If the inner trap does not clear `$ECODE`, the outer `$ETRAP` fires after the subroutine returns.
- **FR-013**: `NEW $ESTACK` MUST be supported, resetting the error stack counter for the current scope.
- **FR-014**: `$ZTRAP` MUST be implemented as a settable ISV. When an error occurs and `$ZTRAP` is set but `$ETRAP` is empty, the `$ZTRAP` code is XECUTEd (if it contains an expression) or execution transfers to the specified label (if it contains a label reference like `"ERR^ROUTINE"`).
- **FR-015**: `$ZSTATUS` MUST be populated with the full error message string on every trapped error.
- **FR-016**: `$ZPOSITION` MUST be populated with the `routine+offset` location string on every trapped error, in the format `"LABEL+offset^ROUTINE"`.
- **FR-017**: The runtime MUST maintain a call stack list recording `(routine, label, offset)` at each DO/XECUTE entry. `$STACK` with no arguments MUST return the current call depth. `$STACK(n,"PLACE")` MUST return the location at stack level n. `$STACK(n,"MCODE")` MUST return the source line at stack level n. `$STACK(n,"ECODE")` MUST return the error code at stack level n if one was active. `$STACK(-1)` MUST return the error context.
- **FR-018**: Error trap execution MUST detect infinite error loops (an error trap that repeatedly triggers the same error) and terminate with an appropriate error after a configurable maximum depth (default: 20 nesting levels). Configuration is via the `max_error_depth` parameter on `MUMPSRuntime.__init__()`.

#### Track B — LOCK Indirection + TSTART Restart Variables (C-05, F-05)

- **FR-020**: `generate_lock_indirection()` MUST be added to `codegen/indirection.py` following the pattern of existing indirection functions (or using the shared `_build_indirection_call()` template from Phase 2 if available).
- **FR-021**: `lock_indirected()` MUST be added to `runtime/__init__.py` that resolves the indirected name and delegates to the existing `lock()`/`unlock()` methods.
- **FR-022**: The `_generate_lock_target()` codegen handler MUST emit a call to `_rt.lock_indirected()` when the lock target is indirected, replacing the current silent comment.
- **FR-023**: LOCK indirection MUST support multi-level indirection, lock timeout with `$TEST` update, and both incremental lock (`+`) and unlock (`-`) forms.
- **FR-024**: `TSTART (var1,var2,...)` MUST snapshot (deep copy) the specified local variables' MArray trees at transaction start. The snapshot is retained for future TRESTART support. On `TROLLBACK` and `TCOMMIT`, the snapshot MUST be discarded without restoring locals (YDB-verified: TROLLBACK does NOT restore local variables).
- **FR-025**: `TSTART *` MUST snapshot all current local variables. The snapshot MUST be discarded on `TROLLBACK` and `TCOMMIT` — locals are NOT restored.
- **FR-026**: For nested transactions, each `TSTART` MUST create its own snapshot of the specified variables. `TROLLBACK` discards only the innermost transaction's snapshot without restoring any locals.
- **FR-027**: If a variable in the restart list does not exist at `TSTART` time, it MUST be recorded as undefined in the snapshot. The snapshot is discarded on TROLLBACK/TCOMMIT. (Restoration from snapshot is reserved for future TRESTART support.)

#### Track C — Standalone Functions + Config (F-10, F-11, F-14)

- **FR-030**: `$ZDATE(horolog, format, months, days)` MUST be implemented as a runtime function that formats `$HOROLOG` values into human-readable date strings. Format codes MUST include at least: `MM`, `DD`, `YY`, `YYYY`, `YEAR`, `MON`, `DAY`, `24:60:SS`, and the standard separators.
- **FR-031**: `$ZDATE` with a single argument MUST use the default format `"MM/DD/YY"`.
- **FR-032**: `$ZDATE` MUST handle combined date and time `$HOROLOG` values (format: `"days,seconds"`) when time format codes are included.
- **FR-033**: `ZSYSTEM command` MUST execute the command string as an OS shell command via `subprocess.run()`. The exit code MUST be available via `$ZSYSTEM` after execution.
- **FR-034**: `ZSYSTEM` with an empty string or no argument MUST be a no-op.
- **FR-035**: `ZLINK routine` MUST reload the specified routine module at runtime using `importlib.reload()` or equivalent. If the routine does not exist, an appropriate error MUST be raised.
- **FR-036**: Accessing an undefined local variable MUST unconditionally raise `LVUNDEFError` (M6 error), matching the MUMPS standard (ANSI 1995 Section 7.2) and YottaDB's default behavior. No CLI flag or toggle is needed.
- **FR-037**: The existing `strict_mode` conditional in `core/scope.py` MUST be removed. The LVUNDEF check MUST always be active. The `LVUNDEFError` exception class MUST be retained. The `.specify/memory/constitution.md` entry "Undefined variables return empty string" MUST be updated to reflect M6 error behavior.

#### Track D — SVNs, SSVNs, Extended Globals (F-07, F-12, F-13)

- **FR-040**: `^$JOB(pid)` MUST query the process table (via `os.kill(pid, 0)` or equivalent) and return whether the specified process is alive. `$DATA(^$JOB($JOB))` MUST return nonzero for the current process.
- **FR-041**: `^$ROUTINE(name)` MUST check whether the specified routine exists as a loaded or loadable module. `$ORDER(^$ROUTINE(""))` and `$DATA(^$ROUTINE(name))` MUST work.
- **FR-042**: `^$SYSTEM("VOL")` and other `^$SYSTEM` subscript values MUST return configurable system information. Defaults: `^$SYSTEM("VOL")` returns `"DEFAULT"`. Configuration is via `MUMPSRuntime.__init__()` kwargs (e.g., `system_vol="DEFAULT"`).
- **FR-043**: `$ZSEARCH(pattern)` MUST search the file system using the specified pattern (mapping to Python's `glob.glob()` or `pathlib.Path.glob()`). Successive calls with empty string MUST return subsequent matches. An empty string return signals exhaustion.
- **FR-044**: `$ZRO` / `$ZROUTINES` MUST return a configurable routine search path string. Default: current working directory (`os.getcwd()`). Configuration is via `MUMPSRuntime.__init__()` kwarg `zro_path`.
- **FR-045**: `$ZJOB` MUST return a bitmask reflecting process attributes. Default: `0` (no special attributes). Configuration is via `MUMPSRuntime.__init__()` kwarg `zjob_bitmask`. Bit values follow YDB documentation (bit 0: principal device is not a terminal, bit 2: direct mode, etc.).
- **FR-046**: `$ZMESSAGE(code)` MUST return the error message text for a given YDB error code. A lookup table MUST include at minimum: M1 (naked reference), M4 (invalid function), M6 (LVUNDEF), M7 (maxstring), M9 (undefined global), M13 (divide by zero), M26 (nesting), M28 (math overflow), and the Z150373XXX-series codes used by `_exception_to_ecode()`.
- **FR-047**: Extended global references in pipe form (`^|"env"|NAME`) and bracket form (`^[UCI,VOL]NAME`) MUST be wired through the parser (existing textX classes), semantic analysis (new ASG representation), codegen (emitting `_rt.get_global_ns()` or similar), and runtime (namespace-qualified global storage).
- **FR-048**: `$DATA`, `$ORDER`, `$GET`, `$QUERY`, `KILL`, `SET`, and `MERGE` MUST all work correctly with extended global references.

#### Track E — READ with #maxlen (F-06)

- **FR-050**: `READ X#n` MUST limit input to at most n characters. If n characters are received before a line terminator, the read completes without waiting for a terminator.
- **FR-051**: `READ X#n:t` (maxlen with timeout) MUST combine both limits correctly. The read completes when whichever occurs first: n characters received, timeout expires, or line terminator entered.
- **FR-052**: `$KEY` MUST be set to the character that terminated the read: the newline/enter character if a line terminator was entered, or empty string if the maxlen was reached without a terminator.
- **FR-053**: For non-interactive (piped) input, `READ X#n` MUST read at most n characters from stdin.
- **FR-054**: `READ X#0` MUST set X to empty string immediately without reading any input.

### Key Entities

- **`$ETRAP`**: Settable ISV containing MUMPS code to execute on error. Supports `NEW $ETRAP` for scoped error handling.
- **`$ECODE`**: Maintained ISV accumulating error codes in `,Merr,` format. Setting `$ECODE=""` clears the error state.
- **`$ZTRAP`**: YDB-specific settable ISV for legacy error trapping. Contains either an XECUTE string or a label reference.
- **`$ZSTATUS`**: YDB-specific read ISV containing the full error message from the last error.
- **`$ZPOSITION`**: YDB-specific read ISV containing the `routine+offset` of the last error.
- **`$STACK`**: Intrinsic function returning call depth (no args) or per-level information (with args).
- **`$ZDATE`**: Intrinsic function formatting `$HOROLOG` values into date/time strings.
- **`$ZSEARCH`**: Intrinsic function performing file system pattern searches with stateful iteration.
- **`$KEY`**: ISV reflecting the termination character of the most recent READ.
- **`MLockTarget` (indirected)**: Runtime representation of a lock target resolved from indirection.
- **Extended Global Reference**: A global reference qualified by namespace — `^|"env"|NAME` (pipe form) or `^[UCI,VOL]NAME` (bracket form).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing tests pass with zero failures, zero xfails, and zero skips after all Phase 3 changes.
- **SC-002**: New unit tests are added for every new feature and correctness fix. Each test module covers at least the acceptance scenarios and edge cases listed in this specification.
- **SC-003**: MUMPS routines using `$ETRAP`/`$ECODE` produce output matching YottaDB when transpiled and run — including error trap firing, `$ECODE` format, and stack unwinding.
- **SC-004**: `$ZTRAP`, `$ZSTATUS`, and `$ZPOSITION` produce output matching YottaDB for error scenarios.
- **SC-005**: `$STACK(n,"PLACE")` and `$STACK(n,"MCODE")` return correct call stack information at any depth.
- **SC-006**: LOCK indirection (`L +@X`, `L -@X`, `L @X:timeout`) resolves and acquires/releases locks correctly — no silent skipping.
- **SC-007**: `TSTART (X,Y)` and `TSTART *` correctly snapshot local variables at transaction start. Snapshots are discarded (not restored) on TROLLBACK and TCOMMIT per YDB semantics. Nested transaction snapshots are maintained independently.
- **SC-008**: `READ X#5` correctly limits input to 5 characters and `$KEY` reflects the termination character.
- **SC-009**: `$ZDATE` correctly formats dates matching YottaDB output for all documented format codes.
- **SC-010**: ZSYSTEM executes shell commands and ZLINK reloads routine modules.
- **SC-011**: Accessing an undefined local variable unconditionally raises `LVUNDEFError` (M6). No flag required — this is the default and only behavior, matching the MUMPS standard and YDB.
- **SC-012**: SSVNs (`^$JOB`, `^$ROUTINE`, `^$SYSTEM`) return meaningful, queryable results.
- **SC-013**: `$ZSEARCH`, `$ZRO`, `$ZJOB`, and `$ZMESSAGE` return real values.
- **SC-014**: Extended global references (`^|"env"|NAME`, `^[UCI,VOL]NAME`) resolve to the correct namespace for all global operations.

## Assumptions

- Phase 1 (foundation cleanup) and Phase 2 (codegen refactoring) are complete before Phase 3 begins. Phase 3 uses modules from those phases: `core/values.py`, `core/parsing.py`, `core/tokenizer.py`, the shared `_build_indirection_call()` template, `codegen/var_access.py`, etc.
- The existing error handling infrastructure (Python try/except) in generated code provides the hooks needed for `$ETRAP`/`$ZTRAP` implementation. Error traps will be implemented as try/except wrappers emitted around subroutine entry points.
- The `$ECODE` format follows the MUMPS standard: codes are surrounded by commas, e.g., `,M6,`. Multiple errors accumulate, e.g., `,M6,M9,`.
- `$ZTRAP` semantics follow YDB behavior: if the value is a label reference (e.g., `"ERR^ROUTINE"`), execution transfers via GOTO; if it's an expression without a label pattern, it's XECUTEd.
- LOCK indirection follows the same patterns established by the existing indirection functions (or the Phase 2 shared `_build_indirection_call()` template).
- TSTART restart variable snapshots use Python's `copy.deepcopy()` on MArray objects, consistent with the existing transaction mechanism for global snapshots.
- `$ZDATE` format codes follow YDB documentation. The implementation covers the most commonly used codes in VistA; exotic format codes may be deferred with documented limitations.
- ZSYSTEM uses `subprocess.run()` in the default shell. Security implications are accepted — MUMPS's ZSYSTEM has the same unrestricted shell access.
- ZLINK maps to `importlib.reload()`. Routines must be importable Python modules for ZLINK to work.
- `$ZSEARCH` maps to Python's `glob.glob()` with state tracking for successive calls (an iterator pattern).
- LVUNDEF (M6) errors are unconditional — no CLI flag or runtime toggle exists. This matches the MUMPS standard (ANSI 1995 Section 7.2) and YDB's default behavior. VistA expects this (zero VistA files use VIEW "NOUNDEF" to suppress LVUNDEF). The constitution entry "Undefined variables return empty string" will be updated as part of this work.
- `$ZEOF` implementation is deferred to Phase 4 (blocked on I/O device management).
- Extended global namespace storage uses a prefix or separate dict key scheme in the runtime global storage (e.g., `"MYNS:GLOBALNAME"` or a parallel namespace dict).

## Dependencies

- **Blocked by**: Phase 1 (019-foundation-cleanup) and Phase 2 (020-codegen-refactoring) must be complete.
- **Blocks**: Phase 4 (Large Architecture — I/O device management, JOB as real processes, inter-process LOCK) builds on Phase 3's error handling and lock infrastructure.

## Scope Boundaries

### In Scope

- All items from the refactoring plan's Phase 3: C-05, F-03, F-05, F-06, F-07, F-08, F-09, F-10, F-11, F-12 (excluding `$ZEOF`), F-13, F-14
- New runtime methods, codegen handlers, and ISV implementations
- Unconditional LVUNDEF error enforcement (M6 compliance) and constitution update
- Unit tests and integration tests for all new features, including edge cases
- YDB validation for features with well-defined YDB reference behavior

### Out of Scope

- Phase 4 items: I/O device management (F-02), JOB as real processes (F-04), inter-process LOCK (F-01), `$ZEOF` (part of F-12 blocked on F-02)
- Deferred items: `TROLLBACK:n`, `$TRESTART`, VIEW behavioral keywords, user-defined pattern tables, ANSI library functions, zero-usage Z-commands
- Interactive terminal raw mode for READ (character-at-a-time input with `termios`/`tty`) — only piped/line-buffered input is in scope for READ `#maxlen`
- `^%G` (YDB global display utility) — requires interactive terminal infrastructure
- Changes to global storage backend (remains in-memory; no persistence layer changes)
