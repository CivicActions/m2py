# Tasks: Phase 3 — Correctness Fixes & New Features

**Input**: Design documents from `/specs/021-correctness-features/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/runtime-apis.md, quickstart.md

**Tests**: Included — spec mandates unit tests with edge cases (FR-002, FR-003, FR-004).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. User stories are ordered by priority (P1 first, then P2, then P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: New runtime data structures and ISV storage needed by all tracks

- [X] T001 Add StackFrame dataclass to src/m2py/runtime/__init__.py per data-model.md
- [X] T002 Add TransactionLocalSnapshot dataclass to src/m2py/runtime/__init__.py per data-model.md
- [X] T003 Add new ISV fields to MUMPSRuntime.__init__() in src/m2py/runtime/__init__.py: _ztrap, _zstatus, _zposition, _in_error_handler, _etrap_set_level, _zsystem_exit, _zsearch_results, _zsearch_index, _transaction_snapshots, _stack_snapshot

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Error handling infrastructure and stack tracking that MUST be complete before user stories

**⚠️ CRITICAL**: US2, US3, US4 cannot begin until this phase is complete

- [X] T004 Replace _stack_level integer counter with _stack_frames list[StackFrame] in src/m2py/runtime/__init__.py — update push_frame()/pop_frame() to push/pop StackFrame objects instead of incrementing/decrementing
- [X] T005 Update all references to _stack_level throughout src/m2py/runtime/__init__.py to use len(_stack_frames) instead
- [X] T006 Update codegen DO block _stack_level increment/decrement in src/m2py/codegen/statements.py to emit push_stack_frame()/pop_stack_frame() calls with frame_type, routine, label, offset, mcode arguments
- [X] T007 Update codegen routine entry/exit in src/m2py/codegen/routine.py to emit push_stack_frame()/pop_stack_frame() calls for DO, $$, and XECUTE frames
- [X] T008 Implement _append_ecode() method in src/m2py/runtime/__init__.py that accumulates error codes with surrounding commas (`,M6,` format)
- [X] T009 Implement _freeze_stack_snapshot() method in src/m2py/runtime/__init__.py that deep-copies _stack_frames to _stack_snapshot when $ECODE transitions from empty to non-empty
- [X] T010 Implement _format_zstatus() helper in src/m2py/runtime/__init__.py that formats error info as "errorcode,label+offset^routine,%YDB-E-ERRNAME, message"
- [X] T011 [P] Write unit tests for StackFrame, _append_ecode(), _freeze_stack_snapshot(), _format_zstatus() in tests/unit/runtime/test_stack_frame.py

**Checkpoint**: Stack tracking and error code accumulation infrastructure ready

---

## Phase 3: User Story 1 — Regression Safety (Priority: P1) 🎯 MVP

**Goal**: All existing tests continue passing with zero failures, zero xfails, zero skips after foundational infrastructure changes

**Independent Test**: `uv run pytest --tb=short -q` — all 6023+ tests pass

- [ ] T012 [US1] Run full test suite after Phase 2 foundational changes and fix any regressions caused by _stack_level → _stack_frames migration in src/m2py/runtime/__init__.py and src/m2py/codegen/
- [ ] T013 [US1] Verify YDB validation suite still produces matching output by running `uv run python utils/validate.py` on representative routines

**Checkpoint**: All existing tests pass — foundational changes are non-breaking

---

## Phase 4: User Story 2 — $ETRAP/$ECODE Error Trapping (Priority: P1)

**Goal**: $ETRAP fires on error, $ECODE accumulates in `,Merr,` format, QUIT from trap unwinds to setter level

**Independent Test**: Transpile routine with SET $ETRAP, trigger error, verify $ECODE format and stack unwinding. Compare against YDB.

### Tests for User Story 2

- [X] T014 [P] [US2] Write unit tests for $ECODE accumulation format in tests/unit/runtime/test_etrap_ecode.py — test `,M6,`, `,M9,M6,`, SET $ECODE="" clearing
- [X] T015 [P] [US2] Write unit tests for _handle_etrap() level-aware unwinding in tests/unit/runtime/test_etrap_ecode.py — test QUIT unwinds to _etrap_set_level
- [X] T016 [P] [US2] Write unit tests for NEW $ETRAP scoping and NEW $ESTACK in tests/unit/runtime/test_etrap_ecode.py
- [X] T017 [P] [US2] Write unit tests for nested error detection in tests/unit/runtime/test_etrap_ecode.py — error during error processing triggers TROLLBACK:$TLEVEL + QUIT
- [X] T018 [P] [US2] Write integration test that transpiles MUMPS routine using $ETRAP and compares output against YDB in tests/integration/test_error_handling.py

### Implementation for User Story 2

- [X] T019 [US2] Enhance _handle_etrap() in src/m2py/runtime/__init__.py: populate $ZSTATUS/$ZPOSITION via _format_zstatus(), freeze stack snapshot, execute $ETRAP code. This task owns the main error dispatch flow.
- [X] T020 [US2] Implement $ETRAP level tracking in src/m2py/runtime/__init__.py: store _etrap_set_level on SET $ETRAP, implement QUIT-from-trap unwinding to that level. This task owns the _etrap_set_level field and unwind logic.
- [X] T021 [US2] Implement nested error detection in src/m2py/runtime/__init__.py: set/check _in_error_handler flag in _handle_etrap(), execute TROLLBACK:$TLEVEL QUIT:$QUIT "" QUIT on nested error. This task owns the _in_error_handler guard.
- [X] T022 [US2] Wire NEW $ESTACK support in src/m2py/codegen/statements.py for the NEW command handler
- [X] T023 [US2] Add configurable max nesting depth (default 20) for infinite error loop detection in src/m2py/runtime/__init__.py

**Checkpoint**: $ETRAP/$ECODE error handling works end-to-end with level-aware unwinding

---

## Phase 5: User Story 3 — $ZTRAP/$ZSTATUS/$ZPOSITION (Priority: P1)

**Goal**: $ZTRAP fires on error when $ETRAP is empty, $ZSTATUS/$ZPOSITION contain error info

**Independent Test**: Transpile routine with SET $ZTRAP="G ERR", trigger error, read $ZSTATUS and $ZPOSITION. Compare against YDB.

### Tests for User Story 3

- [X] T024 [P] [US3] Write unit tests for $ZTRAP ISV storage, SET/read in tests/unit/runtime/test_ztrap.py
- [X] T025 [P] [US3] Write unit tests for $ZTRAP dispatch (XECUTE vs GOTO label reference) in tests/unit/runtime/test_ztrap.py
- [X] T026 [P] [US3] Write unit tests for $ETRAP↔$ZTRAP mutual exclusion in tests/unit/runtime/test_ztrap.py — SET $ZTRAP implicitly NEWs $ETRAP, and vice versa
- [X] T027 [P] [US3] Write unit tests for $ZSTATUS format and $ZPOSITION format in tests/unit/runtime/test_ztrap.py
- [X] T028 [P] [US3] Write integration test transpiling $ZTRAP routine and comparing against YDB in tests/integration/test_error_handling.py

### Implementation for User Story 3

- [X] T029 [US3] Implement ztrap()/set_ztrap() ISV accessors in src/m2py/runtime/__init__.py per contracts/runtime-apis.md
- [X] T030 [US3] Implement zstatus()/set_zstatus() and zposition()/set_zposition() ISV accessors in src/m2py/runtime/__init__.py
- [X] T031 [US3] Implement _dispatch_ztrap() in src/m2py/runtime/__init__.py — regex match for label reference pattern triggers GOTO, otherwise XECUTE
- [X] T032 [US3] Implement $ETRAP↔$ZTRAP mutual exclusion in src/m2py/runtime/__init__.py: SET one implicitly NEWs the other at current stack level
- [X] T033 [US3] Wire $ZTRAP/$ZSTATUS/$ZPOSITION SET codegen in src/m2py/codegen/statements.py — replace NotImplementedError with _rt.set_ztrap()/_rt.set_zstatus()/_rt.set_zposition() calls
- [X] T034 [US3] Wire $ZTRAP/$ZSTATUS/$ZPOSITION read codegen in src/m2py/codegen/expressions.py — replace NotImplementedError with _rt.ztrap()/_rt.zstatus()/_rt.zposition() calls
- [X] T035 [US3] Add $ZTRAP fallback to _handle_etrap() in src/m2py/runtime/__init__.py: when $ETRAP is empty and $ZTRAP is set, dispatch via _dispatch_ztrap()

**Checkpoint**: Both $ETRAP and $ZTRAP error handling subsystems work. US2 + US3 tests pass together.

---

## Phase 6: User Story 5 — LOCK Indirection (Priority: P1)

**Goal**: LOCK @X resolves the indirected name and acquires/releases the lock instead of silently skipping

**Independent Test**: Transpile `S X="^GLO(1)" L +@X`, verify lock is acquired. Verify $TEST on timeout.

### Tests for User Story 5

- [X] T036 [P] [US5] Write unit tests for lock_indirected() runtime method in tests/unit/runtime/test_lock_indirection.py — basic resolve, multi-level, timeout+$TEST, +/- forms
- [X] T037 [P] [US5] Write codegen tests for generate_lock_indirection() in tests/unit/codegen/test_lock_indirection.py — verify emitted Python code
- [X] T113 [P] [US5] Write integration test transpiling LOCK indirection routines and comparing against YDB in tests/integration/test_lock_indirection.py

### Implementation for User Story 5

- [X] T038 [US5] Implement generate_lock_indirection() in src/m2py/codegen/indirection.py following existing indirection generator pattern
- [X] T039 [US5] Implement lock_indirected() runtime method in src/m2py/runtime/__init__.py per contracts/runtime-apis.md — parse name, resolve indirection, delegate to lock()/unlock()
- [X] T040 [US5] Wire _generate_lock_target() in src/m2py/codegen/statements.py to emit _rt.lock_indirected() call when lock_target.is_indirect is True, replacing the silent comment at L5327-5330
- [X] T041 [US5] Support multi-level indirection, timeout with $TEST update, and +/- lock forms in lock_indirected()

**Checkpoint**: LOCK indirection works end-to-end. `L +@X:0` sets $TEST correctly.

---

## Phase 7: User Story 4 — $STACK Introspection (Priority: P2)

**Goal**: $STACK(n), $STACK(n,"PLACE"), $STACK(n,"MCODE"), $STACK(n,"ECODE"), $STACK(-1) return correct call stack info

**Independent Test**: Transpile routine with nested DO calls, query $STACK at various levels. Compare against YDB.

### Tests for User Story 4

- [X] T042 [P] [US4] Write unit tests for stack_function() in tests/unit/runtime/test_stack_function.py — $STACK no args, $STACK(n), $STACK(n,"PLACE"), $STACK(n,"MCODE"), $STACK(n,"ECODE"), $STACK(-1), n > depth returns ""
- [X] T043 [P] [US4] Write unit tests for $STACK snapshot behavior in tests/unit/runtime/test_stack_function.py — during error ($ECODE non-empty) returns frozen snapshot, reset on SET $ECODE=""
- [X] T044 [P] [US4] Write integration test transpiling nested DO routine with $STACK queries in tests/integration/test_stack_introspection.py

### Implementation for User Story 4

- [X] T045 [US4] Implement stack_function() method in src/m2py/runtime/__init__.py per contracts/runtime-apis.md — level/info dispatch, snapshot vs live stack
- [X] T046 [US4] Wire $STACK(n,info) codegen in src/m2py/codegen/expressions.py — emit _rt.stack_function() call with level and optional info arguments
- [X] T047 [US4] Implement $STACK snapshot reset on SET $ECODE="" in src/m2py/runtime/__init__.py — clear _stack_snapshot and _stack_snapshot_depth

**Checkpoint**: $STACK introspection works. Error handling subsystem (US2+US3+US4) is complete.

---

## Phase 8: User Story 6 — TSTART Restart Variables (Priority: P2)

**Goal**: TSTART (X,Y) snapshots locals; TSTART * snapshots all locals; snapshots discarded on TCOMMIT/TROLLBACK (saved for eventual TRESTART)

**Independent Test**: Transpile routine with TSTART (X), modify X, TCOMMIT. Verify X is NOT restored (TROLLBACK only restores globals per YDB semantics).

### Tests for User Story 6

- [ ] T048 [P] [US6] Write unit tests for snapshot_locals() in tests/unit/runtime/test_tstart_vars.py — named vars, all vars (*), undefined var recorded as sentinel
- [ ] T049 [P] [US6] Write unit tests for discard_local_snapshot() in tests/unit/runtime/test_tstart_vars.py — TCOMMIT and TROLLBACK both discard (no local restore)
- [ ] T050 [P] [US6] Write unit tests for nested transaction snapshots in tests/unit/runtime/test_tstart_vars.py — inner TROLLBACK discards inner snapshot only
- [ ] T051 [P] [US6] Write integration test transpiling TSTART/TCOMMIT/TROLLBACK routine in tests/integration/test_tstart_restart.py

### Implementation for User Story 6

- [ ] T052 [US6] Implement snapshot_locals() in src/m2py/runtime/__init__.py per contracts/runtime-apis.md — deepcopy named MArray vars or all locals
- [ ] T053 [US6] Implement discard_local_snapshot() in src/m2py/runtime/__init__.py — pop from _transaction_snapshots without restoring
- [ ] T054 [US6] Implement restore_locals_from_snapshot() in src/m2py/runtime/__init__.py — for future TRESTART support (pop snapshot, restore each var). Not mapped to a current FR but validates the snapshot design and is trivial to add alongside T052/T053.
- [ ] T055 [US6] Wire TSTART codegen in src/m2py/codegen/statements.py to emit _rt.snapshot_locals() call with var names or all_vars=True, replacing NotImplementedError at L5176-5214
- [ ] T056 [US6] Wire TROLLBACK codegen in src/m2py/codegen/statements.py to emit _rt.discard_local_snapshot() call
- [ ] T057 [US6] Wire TCOMMIT codegen in src/m2py/codegen/statements.py to emit _rt.discard_local_snapshot() call

**Checkpoint**: TSTART with restart vars compiles and runs. Snapshots are created and discarded correctly.

---

## Phase 9: User Story 7 — READ #maxlen + $KEY (Priority: P2)

**Goal**: READ X#5 limits input to 5 characters, $KEY reflects termination character

**Independent Test**: `echo "ABCDEFGH" | uv run python utils/validate.py --code 'TEST R X#5 W X,! Q'` outputs "ABCDE"

### Tests for User Story 7

- [ ] T058 [P] [US7] Write unit tests for m_read_maxlen() in tests/unit/runtime/test_read_maxlen.py — basic limit, early newline, READ #0 returns ""
- [ ] T059 [P] [US7] Write unit tests for m_read_maxlen_timeout() in tests/unit/runtime/test_read_maxlen.py — combined maxlen+timeout
- [ ] T060 [P] [US7] Write unit tests for $KEY population after READ in tests/unit/runtime/test_read_maxlen.py — newline if Enter pressed, "" if maxlen reached
- [ ] T114 [P] [US7] Write integration test transpiling READ #maxlen routines and comparing against YDB in tests/integration/test_read_maxlen.py

### Implementation for User Story 7

- [ ] T061 [US7] Implement m_read_maxlen() in src/m2py/runtime/helpers.py per contracts/runtime-apis.md — read at most maxlen chars from stdin
- [ ] T062 [US7] Implement m_read_maxlen_timeout() in src/m2py/runtime/helpers.py per contracts/runtime-apis.md — combined maxlen+timeout with tuple return
- [ ] T063 [US7] Wire _generate_read_target() in src/m2py/codegen/statements.py to handle target.fixed_length — emit m_read_maxlen() call, replacing ignored fixed_length at L5091-5174
- [ ] T064 [US7] Set $KEY ISV after READ completion in src/m2py/runtime/__init__.py — terminator char or "" if maxlen reached
- [ ] T065 [US7] Handle READ #0 edge case in src/m2py/runtime/helpers.py — immediate empty string, no input read

**Checkpoint**: READ #maxlen works. `READ X#5` limits correctly and $KEY is set.

---

## Phase 10: User Story 8 — $ZDATE (Priority: P2)

**Goal**: $ZDATE formats $HOROLOG values into human-readable date strings matching YDB output

**Independent Test**: `uv run python utils/validate.py --code 'TEST W $ZD(66337,"YYYY-MM-DD"),! Q'` outputs "2022-08-16"

### Tests for User Story 8

- [ ] T066 [P] [US8] Write unit tests for m_zdate() in tests/unit/runtime/test_zdate.py — default format (MM/DD/YY), ISO format (YYYY-MM-DD), DD MON YEAR, time formats (24:60:SS, 12, AM)
- [ ] T067 [P] [US8] Write unit tests for m_zdate() edge cases in tests/unit/runtime/test_zdate.py — invalid $HOROLOG value, custom month/day names, combined date+time, boundary dates
- [ ] T115 [P] [US8] Write integration test transpiling $ZDATE routines and comparing against YDB in tests/integration/test_zdate.py

### Implementation for User Story 8

- [ ] T068 [US8] Implement m_zdate() in src/m2py/runtime/helpers.py per contracts/runtime-apis.md — parse $HOROLOG date component (days since epoch), apply date format codes (MM, DD, YY, YYYY, YEAR, MON, DAY), handle custom month/day names. This task handles date-only formatting.
- [ ] T069 [US8] Wire $ZDATE codegen in src/m2py/codegen/expressions.py — remove $ZDATE from Z_FUNCTIONS_UNIMPLEMENTED at L97, add dispatch to _rt_helpers.m_zdate() call with 1-4 arguments
- [ ] T070 [US8] Extend m_zdate() in src/m2py/runtime/helpers.py to handle $HOROLOG time component — parse "days,seconds" format, add time format codes (24, 12, 60, SS, AM). This task extends T068's implementation with time support.

**Checkpoint**: $ZDATE works for all common format codes. Output matches YDB.

---

## Phase 11: User Story 9 — ZSYSTEM (Priority: P2)

**Goal**: ZSYSTEM executes shell commands, $ZSYSTEM returns exit code. ZLINK already implemented (no work needed).

**Independent Test**: `uv run python utils/validate.py --code 'TEST ZSY "echo hello" W $ZSY,! Q'`

### Tests for User Story 9

- [ ] T071 [P] [US9] Write unit tests for zsystem() and zsystem_exit() in tests/unit/runtime/test_zsystem.py — successful command, failed command exit code, empty string no-op
- [ ] T072 [P] [US9] Write codegen tests for ZSYSTEM in tests/unit/codegen/test_zsystem_codegen.py — verify emitted subprocess.run() call
- [ ] T116 [P] [US9] Write integration test transpiling ZSYSTEM routines and comparing against YDB in tests/integration/test_zsystem.py
- [ ] T117 [P] [US9] Write verification test for existing ZLINK implementation against FR-035 acceptance scenarios (US9 scenarios 3-4) in tests/integration/test_zlink.py

### Implementation for User Story 9

- [ ] T073 [US9] Implement zsystem() in src/m2py/runtime/__init__.py per contracts/runtime-apis.md — subprocess.run(), store exit code in _zsystem_exit
- [ ] T074 [US9] Implement zsystem_exit() accessor in src/m2py/runtime/__init__.py — return _zsystem_exit
- [ ] T075 [US9] Wire ZSYSTEM codegen in src/m2py/codegen/statements.py — replace NotImplementedError at L856-857 with _rt.zsystem() call
- [ ] T076 [US9] Wire $ZSYSTEM read codegen in src/m2py/codegen/expressions.py — emit _rt.zsystem_exit() call

**Checkpoint**: ZSYSTEM works. `ZSY "echo hello"` executes and $ZSYSTEM returns 0.

---

## Phase 12: User Story 10 — Unconditional LVUNDEF (Priority: P2)

**Goal**: Undefined local variable access unconditionally raises LVUNDEFError (M6), no flag/toggle

**Independent Test**: Transpile `WRITE X` (X undefined), verify M6 error raised.

### Tests for User Story 10

- [X] T077 [P] [US10] Write unit tests for unconditional LVUNDEF in tests/unit/core/test_lvundef.py — undefined raises M6, defined returns value, NEW scope exit raises M6
- [X] T078 [P] [US10] Write test verifying no strict_mode parameter exists in CurrentScope in tests/unit/core/test_lvundef.py
- [X] T118 [P] [US10] Write integration test transpiling LVUNDEF scenarios and comparing against YDB in tests/integration/test_lvundef.py

### Implementation for User Story 10

- [X] T079 [US10] Remove strict_mode parameter from CurrentScope.__init__() in src/m2py/core/scope.py — make LVUNDEF check unconditional (always raise LVUNDEFError for undefined locals)
- [X] T080 [US10] Update all callers of CurrentScope() that pass strict_mode argument across src/m2py/
- [X] T081 [US10] Fix existing tests that relied on undefined locals returning empty string — update to either define variables first or expect M6 error
- [x] T082 [US10] Update constitution §IV in .specify/memory/constitution.md: change "Undefined variables return empty string (not exception)" to reflect unconditional M6 error behavior per FR-037 — DONE (v1.2.0 → v1.3.0)

**Checkpoint**: LVUNDEF is unconditional. All tests pass. Constitution updated.

---

## Phase 13: User Story 11 — SSVNs (Priority: P2)

**Goal**: ^$JOB, ^$ROUTINE, ^$SYSTEM return meaningful, queryable results

**Independent Test**: Transpile `W $D(^$J($J))` — returns nonzero for current process

### Tests for User Story 11

- [ ] T083 [P] [US11] Write unit tests for ^$JOB in tests/unit/runtime/test_ssvn.py — current process exists, nonexistent PID returns 0
- [ ] T084 [P] [US11] Write unit tests for ^$ROUTINE in tests/unit/runtime/test_ssvn.py — existing routine found, $ORDER works
- [ ] T085 [P] [US11] Write unit tests for ^$SYSTEM in tests/unit/runtime/test_ssvn.py — returns configurable values
- [ ] T119 [P] [US11] Write integration test transpiling SSVN routines and comparing against YDB in tests/integration/test_ssvn.py

### Implementation for User Story 11

- [ ] T086 [US11] Implement ^$JOB SSVN handler in src/m2py/runtime/__init__.py — os.kill(pid,0) to check process liveness, $DATA/$ORDER support
- [ ] T087 [US11] Implement ^$ROUTINE SSVN handler in src/m2py/runtime/__init__.py — check importable modules, $DATA/$ORDER support
- [ ] T088 [US11] Implement ^$SYSTEM SSVN handler in src/m2py/runtime/__init__.py — return configurable system info
- [ ] T089 [US11] Wire SSVN dispatch in src/m2py/codegen/expressions.py L434-484 — route ^$JOB, ^$ROUTINE, ^$SYSTEM to runtime handlers

**Checkpoint**: SSVNs return real data. `$D(^$J($J))` returns nonzero.

---

## Phase 14: User Story 12 — YDB SVNs ($ZSEARCH, $ZRO, $ZJOB, $ZMESSAGE) (Priority: P3)

**Goal**: YDB-specific SVNs return real values instead of stubs/errors

**Independent Test**: `uv run python utils/validate.py --code 'TEST W $ZSEARCH("*.m"),! Q'`

### Tests for User Story 12

- [ ] T090 [P] [US12] Write unit tests for zsearch() in tests/unit/runtime/test_svn.py — first call returns match, successive calls iterate, empty on exhaustion
- [ ] T091 [P] [US12] Write unit tests for zmessage_text() in tests/unit/runtime/test_svn.py — known error codes return message, unknown code handled
- [ ] T092 [P] [US12] Write unit tests for zro()/zjob() in tests/unit/runtime/test_svn.py — configurable values returned
- [ ] T120 [P] [US12] Write integration test transpiling YDB SVN routines and comparing against YDB in tests/integration/test_svn.py

### Implementation for User Story 12

- [ ] T093 [US12] Implement zsearch() in src/m2py/runtime/__init__.py per contracts/runtime-apis.md — glob.glob() with _zsearch_results/_zsearch_index state
- [ ] T094 [US12] Implement zmessage_text() in src/m2py/runtime/helpers.py per contracts/runtime-apis.md — lookup table of common YDB error codes
- [ ] T095 [US12] Implement zro() in src/m2py/runtime/__init__.py — configurable routine search path
- [ ] T096 [US12] Implement zjob() in src/m2py/runtime/__init__.py — bitmask of process attributes
- [ ] T097 [US12] Wire $ZSEARCH, $ZRO, $ZJOB, $ZMESSAGE codegen in src/m2py/codegen/expressions.py — remove from unimplemented lists, add dispatch to runtime methods

**Checkpoint**: YDB SVNs return real values.

---

## Phase 15: User Story 13 — Extended Global References (Priority: P3)

**Goal**: ^|"env"|NAME and ^[UCI,VOL]NAME resolve to namespace-qualified globals

**Independent Test**: `SET ^|"MYNS"|GLO(1)="val" WRITE ^|"MYNS"|GLO(1)` outputs "val"

### Tests for User Story 13

- [ ] T098 [P] [US13] Write unit tests for namespace-qualified get/set in tests/unit/runtime/test_extended_globals.py — pipe form, bracket form, default namespace fallback
- [ ] T099 [P] [US13] Write unit tests for $DATA/$ORDER/$GET/$QUERY/KILL/MERGE with extended globals in tests/unit/runtime/test_extended_globals.py
- [ ] T100 [P] [US13] Write integration test transpiling extended global routines in tests/integration/test_extended_globals.py

### Implementation for User Story 13

- [ ] T101 [US13] Implement namespace-qualified global storage in src/m2py/runtime/__init__.py — set_ns()/get_ns() methods per contracts/runtime-apis.md, or namespace-prefixed keys in existing global dict
- [ ] T102 [US13] Wire pipe form (^|"env"|NAME) codegen in src/m2py/codegen/expressions.py — extract namespace from ExtendedGlobalPipe ASG node, emit _rt.get_ns()/_rt.set_ns() calls
- [ ] T103 [US13] Wire bracket form (^[UCI,VOL]NAME) codegen in src/m2py/codegen/expressions.py — extract UCI/VOL from ExtendedGlobalBracket ASG node, derive namespace
- [ ] T104 [US13] Wire extended global SET codegen in src/m2py/codegen/statements.py — handle pipe and bracket forms in SET command dispatch
- [ ] T105 [US13] Wire $DATA, $ORDER, $GET, $QUERY, KILL, MERGE for extended globals in src/m2py/codegen/statements.py and src/m2py/codegen/expressions.py — all operations namespace-aware
- [ ] T106 [US13] Handle nonexistent namespace: create on write, return undefined on read in src/m2py/runtime/__init__.py

**Checkpoint**: Extended global references work for all operations. Both pipe and bracket forms resolve correctly.

---

## Phase 16: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and cleanup

- [ ] T107 [P] Update docs/coverage-matrix.md with Phase 3 feature coverage
- [ ] T108 [P] Update docs/limitations.md — remove items now implemented (LOCK indirection, $ZDATE, ZSYSTEM, etc.)
- [ ] T109 Run full test suite: `uv run pytest` — verify zero failures, zero xfails, zero skips
- [ ] T110 Run YDB validation suite on representative VistA routines using `uv run python utils/validate.py`
- [ ] T111 Run quickstart.md validation: execute all commands in specs/021-correctness-features/quickstart.md and verify expected outputs
- [ ] T112 [P] Code cleanup — remove dead code, unused imports, TODO comments from Phase 3 implementation files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 Regression (Phase 3)**: Depends on Foundational — must verify no regressions
- **US2 $ETRAP (Phase 4)**: Depends on Foundational (stack frames, _append_ecode)
- **US3 $ZTRAP (Phase 5)**: Depends on US2 (_handle_etrap enhancement)
- **US5 LOCK (Phase 6)**: Depends on Foundational only — independent of error handling
- **US4 $STACK (Phase 7)**: Depends on US2 (stack snapshot on error)
- **US6 TSTART (Phase 8)**: Depends on Foundational only — independent of error handling
- **US7 READ (Phase 9)**: Depends on Foundational only — independent
- **US8 $ZDATE (Phase 10)**: Depends on Foundational only — independent
- **US9 ZSYSTEM (Phase 11)**: Depends on Foundational only — independent
- **US10 LVUNDEF (Phase 12)**: Depends on US2 ($ETRAP needed to trap M6 errors correctly)
- **US11 SSVNs (Phase 13)**: Independent of all other stories
- **US12 YDB SVNs (Phase 14)**: Independent
- **US13 Extended Globals (Phase 15)**: Independent
- **Polish (Phase 16)**: Depends on all stories being complete

### User Story Dependencies

```
Phase 1: Setup
  └── Phase 2: Foundational (stack frames, _append_ecode, _freeze_snapshot)
        ├── Phase 3: US1 Regression safety ─── GATE (must pass before continuing)
        ├── Phase 4: US2 $ETRAP/$ECODE
        │     ├── Phase 5: US3 $ZTRAP/$ZSTATUS/$ZPOSITION
        │     ├── Phase 7: US4 $STACK introspection
        │     └── Phase 12: US10 LVUNDEF (needs error trap infra)
        ├── Phase 6: US5 LOCK indirection (independent)
        ├── Phase 8: US6 TSTART restart vars (independent)
        ├── Phase 9: US7 READ #maxlen (independent)
        ├── Phase 10: US8 $ZDATE (independent)
        ├── Phase 11: US9 ZSYSTEM (independent)
        ├── Phase 13: US11 SSVNs (independent)
        ├── Phase 14: US12 YDB SVNs (independent)
        └── Phase 15: US13 Extended globals (independent)
              └── Phase 16: Polish
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Runtime methods before codegen wiring
- Codegen before integration tests
- Full suite run after each story checkpoint

### Parallel Opportunities

After Foundational (Phase 2) and US1 gate pass:

- **Worker 1 (Track A)**: US2 → US3 → US4 (sequential, shared infrastructure)
- **Worker 2 (Track B+E)**: US5 || US6 || US7 (all independent)
- **Worker 3 (Track C+D)**: US8 || US9 || US11 || US12 || US13 (all independent)
- **US10 (LVUNDEF)**: After US2 completes (needs error trap for M6)

Within each user story, all test tasks marked [P] can be written in parallel.

---

## Parallel Example: User Story 2 ($ETRAP/$ECODE)

```bash
# All tests can be written in parallel:
T014 [P] [US2] Unit tests for $ECODE accumulation
T015 [P] [US2] Unit tests for _handle_etrap() unwinding
T016 [P] [US2] Unit tests for NEW $ETRAP scoping
T017 [P] [US2] Unit tests for nested error detection
T018 [P] [US2] Integration test against YDB
```

## Parallel Example: Independent User Stories After Foundational

```bash
# These stories can proceed simultaneously on different workers:
US5: LOCK indirection (codegen/indirection.py, runtime/__init__.py lock methods)
US8: $ZDATE (runtime/helpers.py — no overlap with LOCK)
US7: READ #maxlen (runtime/helpers.py m_read_maxlen, codegen/statements.py READ handler)
US9: ZSYSTEM (runtime/__init__.py zsystem, codegen/statements.py ZSYSTEM handler)
```

---

## Implementation Strategy

### MVP First (P1 Stories Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 — **GATE: All tests pass**
4. Complete Phase 4: US2 ($ETRAP/$ECODE)
5. Complete Phase 5: US3 ($ZTRAP/$ZSTATUS/$ZPOSITION)
6. Complete Phase 6: US5 (LOCK indirection)
7. **STOP and VALIDATE**: All P1 stories independently functional
8. Deploy/demo if ready — error handling and LOCK indirection working

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. US1 → Regression gate passed
3. US2 + US3 → Error handling works → **Demo: VistA error trapping**
4. US5 → LOCK indirection → **Demo: Concurrent VistA routines**
5. US4 + US10 → $STACK + LVUNDEF → **Demo: Full error diagnostics**
6. US6 + US7 + US8 + US9 → Transactions, READ, $ZDATE, ZSYSTEM → **Demo: VistA data entry**
7. US11 + US12 + US13 → SSVNs, SVNs, extended globals → **Demo: VistA system management**

### Parallel Team Strategy

With 2 workers after Foundational gate:

- **Worker 1**: US2 → US3 → US4 → US10 (Track A chain + LVUNDEF) ~15 days
- **Worker 2**: US5 → US6 → US7 → US8 → US9 → US11 → US12 → US13 (Tracks B+C+D+E) ~18 days

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- ZLINK (FR-035) is already fully implemented — T117 verifies existing implementation against spec acceptance scenarios
- TSTART restart vars save for TRESTART not TROLLBACK per YDB semantics — snapshots are discarded (not restored) on TROLLBACK
- US10 (LVUNDEF) depends on US2 ($ETRAP) because M6 errors need to be trappable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Full test suite: `uv run pytest` — must pass at every checkpoint
- Total tasks: 120 (T001-T112 + T113-T120), 49 parallelizable
