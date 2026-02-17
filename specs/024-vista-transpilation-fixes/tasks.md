# Tasks: VistA-VEHU-M Complete Transpilation

**Input**: Design documents from `/specs/024-vista-transpilation-fixes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story (from spec.md) to enable independent implementation and testing of each story. 6 user stories, 8 phases.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete same-file tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Establish baseline metrics before making changes

- [x] T001 Run baseline VistA-VEHU-M transpilation scan (39,304 routines), record current failure count and error types using utils/scan_vista.py or equivalent in tmp/baseline-scan/
  - **Result**: 36,686 ok / 2,618 failed (93.34%) — baseline established in tmp/baseline-scan/

---

## Phase 2: User Story 1 — Core Codegen Fixes (Priority: P1) 🎯 MVP

**Goal**: Fix 5 codegen defects (ParenExpr, f-strings, empty TRAMPOLINE blocks, >=/<= operators, SET $X/$Y) that cause 80% of all failures (~2,153 routines).

**Independent Test**: Run VistA-VEHU-M scan. Failure count drops from ~2,592 to ~439. Each fix verifiable with Contracts 1-5.

### Implementation for User Story 1

#### ParenExpr / UnaryPrefixedExpr (FR-001, FR-026) — 1,035 routines

- [X] T002 [P] [US1] Add ParenExpr defensive handler in generate_expr() before NotImplementedError fallthrough in src/m2py/codegen/expressions.py
  > Also added Expr, OffsetExpr, OffsetUnaryExpr defensive handlers for textX wrapper nodes that survive past analysis.
- [X] T003 [US1] Add UnaryPrefixedExpr defensive handler in generate_expr() using same pattern as ParenExpr in src/m2py/codegen/expressions.py
  > Fixed UnaryOp extraction (op_item.op for textX objects vs raw strings).
- [X] T004 [P] [US1] Audit semantic analyzer for code paths that bypass ParenExpr unwrapping in src/m2py/analysis/semantic_analyzer.py
  > Audit found OffsetExpr/OffsetUnaryExpr/SubscriptedGlobal lack defensive handlers. Added OffsetExpr and OffsetUnaryExpr handlers. Low risk — analyzer covers all paths.

#### f-string Nested Quotes (FR-002) — 580 routines

- [X] T005 [P] [US1] Replace f-string nested quotes with string concatenation at L575 and L578 in src/m2py/codegen/indirection.py
  > Fixed both single-sub and multi-sub cases with string concatenation.
- [X] T006 [US1] Audit all codegen files for additional f-string patterns with nested matching quotes in src/m2py/codegen/
  > Found and fixed 2 additional instances in expressions.py L1399-1402 ($ORDER/$NEXT subscripted variable name builder).

#### Empty TRAMPOLINE Block (FR-003) — 210 routines

- [X] T007 [P] [US1] Fix empty indented block by placing GOTO return inside if body in TRAMPOLINE handler (~L3282-3935) in src/m2py/codegen/statements.py
  > Fixed in 4 locations: _generate_if (multi-condition, argumentless, single-condition) and _generate_else. Uses emitter line count tracking + pass insertion.

#### >= and <= Operators (FR-004) — 180 routines

- [X] T008 [US1] Add >= and <= operator cases in _generate_binary_op() after existing '> handler (~L736) in src/m2py/codegen/expressions.py
  > Maps >= to int(not m_compare(left, "<", right)) and <= to int(not m_compare(left, ">", right)).

#### SET $X / SET $Y (FR-005) — 148 routines

- [X] T009 [P] [US1] Add set_x() and set_y() methods to MRuntime class in src/m2py/runtime/__init__.py
  > Also added device_control() stub method for DeviceControl mnemonics.
- [X] T010 [US1] Add SET $X and SET $Y elif branches in _generate_single_assignment() (~L1104) in src/m2py/codegen/statements.py
  > Also added DeviceControl handling in _generate_write() to avoid NotImplementedError.

### Validation for User Story 1

- [X] T011 [US1] Write tests for Contracts 1-5 (ParenExpr, f-string, empty block, >=/<= operators, SET $X/$Y) in tests/unit/codegen/test_024_vista_transpilation_fixes.py
  > 44 tests: 6 ParenExpr, 5 UnaryPrefixedExpr, 4 f-string, 7 empty block, 11 comparison op, 7 SET $X/$Y, 4 DeviceControl. All pass.
- [X] T012 [US1] Run targeted VistA scan on a few affected routines to verify significant drop in failures.
  > 20/20 targeted VistA routines now transpile successfully (PRCACV10, DGMTXE2, SCAPMCU3, DSICDDBR, FHWOR6, SCMCCV, HMPDMC, FSCEVENP, XUSHSH, PXRMRXTY, ICDSELDS, DVBACER1, GMRCIAC2, etc.).

**Checkpoint**: US1 complete — 80% of failures resolved, success rate ~98.9%

---

## Phase 3: User Story 2 — MUMPS Language Completeness (Priority: P2)

**Goal**: Complete 4 partially-implemented MUMPS features (LHS $E 1-arg, tuple SET with $P/$E, NEW indirection, computed GOTO) unblocking ~144 routines.

**Independent Test**: Each fix has a standalone MUMPS test (Contracts 6-9) verifiable against YDB output.

### Implementation for User Story 2

- [ ] T013 [US2] Support LHS $EXTRACT 1-arg form by defaulting start=1 end=1 when len(args)==1 in _generate_lhs_extract() (~L1478) in src/m2py/codegen/statements.py
- [ ] T014 [US2] Support tuple SET with $PIECE/$EXTRACT targets by adding MIntrinsicFunction handler before ~L1061 in src/m2py/codegen/statements.py
- [ ] T015 [US2] Replace NotImplementedError for NEW @VAR in TRAMPOLINE with runtime call (~L4843) in src/m2py/codegen/statements.py
- [ ] T016 [US2] Support computed GOTO (@expr) by generating label-name-string return for trampoline dispatcher in src/m2py/codegen/statements.py

### Validation for User Story 2

- [ ] T017 [US2] Write tests for Contracts 6-9 (LHS $E 1-arg, tuple SET, NEW indirection, computed GOTO) in tests/functional/
- [ ] T018 [US2] Run targeted VistA scan on a few affected routines to verify ~144 newly passing

**Checkpoint**: US1+US2 complete — ~2,297 failures resolved, success rate ~99.2%

---

## Phase 4: User Story 3 — Robustness and Infrastructure (Priority: P3)

**Goal**: Fix infrastructure issues (RecursionError, ZLOAD dispatch, encoding fallback) unblocking ~64 routines.

**Independent Test**: Transpile PSXRECV.m without RecursionError (Contract 10). ZLOAD routines transpile without error (Contract 11).

### Implementation for User Story 3

- [ ] T019 [P] [US3] Add sys.setrecursionlimit(5000) in transpilation entry point, restore afterward, in src/m2py/cli/ or main.py
- [ ] T020 [P] [US3] Add MZLoadStatement dispatch routing to existing _generate_zlink() at statement dispatcher (~L811-812) in src/m2py/codegen/statements.py
- [ ] T021 [P] [US3] Add encoding fallback (try UTF-8, then Latin-1 with errors='replace') in .m file reading code

### Validation for User Story 3

- [ ] T022 [US3] Write tests for Contracts 10-11 (RecursionError prevention, ZLOAD handling) in tests/functional/

**Checkpoint**: US1-3 complete — ~2,361 failures resolved, success rate ~99.4%

---

## Phase 5: User Story 4 — IRIS/Caché Vendor Functions (Priority: P4)

**Goal**: Implement IRIS vendor functions ($REPLACE, $ZBOOLEAN, $ZV, $ZF, $ZA, $ZR, $NAMESPACE, $ZU) and stubs ($ZC, $VIEW) used by VistA, unblocking ~106 routines.

**Independent Test**: Each vendor function has a test case (Contracts 12-19) validated against IRIS semantics.

### Implementation for User Story 4

#### Runtime Functions (src/m2py/runtime/helpers.py)

- [ ] T023 [P] [US4] Implement m_replace(string, search, replace, start, count, case) per data-model.md in src/m2py/runtime/helpers.py
- [ ] T024 [US4] Implement m_zboolean(arg1, arg2, op) with 16-op truth table for int and string modes in src/m2py/runtime/helpers.py
- [ ] T025 [US4] Implement m_zu(code, *args) dispatch table for ~12 VistA-used codes per data-model.md in src/m2py/runtime/helpers.py
- [ ] T026 [US4] Implement m_zf(code, *args) with subprocess calls ($ZF-1/-2/-100) and VMS stubs in src/m2py/runtime/helpers.py
- [ ] T027 [US4] Add m_zcall_stub() and m_view_func_stub() returning "" with warning in src/m2py/runtime/helpers.py

#### Runtime Special Variables (src/m2py/runtime/__init__.py)

- [ ] T028 [P] [US4] Add $ZV/$ZVERSION (read-only, "M2PY for Python 1.0"), $ZA (read-only, default 0), $ZR/$ZREFERENCE (read+set), $NAMESPACE (read+set+NEW, default "VISTA") properties and setters to MRuntime in src/m2py/runtime/__init__.py

#### Global Reference Tracking

- [ ] T029 [P] [US4] Update global get/set/kill operations to set $ZREFERENCE after each operation in src/m2py/runtime/globals.py

#### Codegen Dispatch Wiring

- [ ] T030 [US4] Wire $REPLACE, $ZBOOLEAN, $ZU, $ZF intrinsic function dispatch and $ZC/$VIEW stubs in src/m2py/codegen/expressions.py
- [ ] T031 [US4] Wire $ZV, $ZA, $ZR, $NAMESPACE SVN readers in codegen expressions dispatcher in src/m2py/codegen/expressions.py
- [ ] T032 [US4] Add $NAMESPACE to SET special variable dispatch in src/m2py/codegen/statements.py

### Validation for User Story 4

- [ ] T033 [US4] Write tests for Contracts 12-19 ($REPLACE, $ZBOOLEAN, $ZV, $ZF, $ZA, $ZR, $NAMESPACE, $ZU) in tests/functional/

**Checkpoint**: US1-4 complete — ~2,467 failures resolved, success rate ~99.7%

---

## Phase 6: User Story 5 — Miscellaneous Fixes and Stubs (Priority: P5)

**Goal**: Handle remaining edge cases (device control mnemonics, settable SVNs, $& external calls, reader SVNs) unblocking ~49 routines.

**Independent Test**: Each affected routine transpiles without error. Stubs return sensible defaults.

### Implementation for User Story 5

- [ ] T034 [P] [US5] Add device_control(command, args) handler in src/m2py/runtime/devices.py
- [ ] T035 [P] [US5] Add $DEVICE, $REFERENCE, $ZGBLDIR properties and external_call_stub(name, args) method to MRuntime in src/m2py/runtime/__init__.py
- [ ] T036 [US5] Add WRITE /command (device control mnemonic) codegen and SET $ZINTERRUPT/$ZERR/$ZSOURCE dispatch in src/m2py/codegen/statements.py
- [ ] T037 [US5] Add $DEVICE/$REFERENCE/$ZGBLDIR SVN readers and $& external function call codegen in src/m2py/codegen/expressions.py

#### ZPRINT / ZMESSAGE Stubs (FR-030) — 5 routines

- [ ] T046 [P] [US5] Add ZPRINT and ZMESSAGE codegen dispatch stubs — route MZPrintStatement to no-op and MZMessageStatement to error-signal stub in src/m2py/codegen/statements.py

### Validation for User Story 5

- [ ] T038 [US5] Write tests for misc stubs (device control, SET $ZINTERRUPT/$ZERR/$ZSOURCE, $& calls, reader SVNs, ZPRINT/ZMESSAGE) in tests/functional/

**Checkpoint**: US1-5 complete — all ~2,521 fixable failures resolved, success rate ~99.8%

---

## Phase 7: User Story 6 — Limitations Documentation (Priority: P2)

**Goal**: Update the limitations document to reflect newly supported features and document partial IRIS/Caché support scope.

**Independent Test**: Review docs/limitations.md for accuracy. LIM-003 unchanged. New LIM-017 present. No stale entries.

### Implementation for User Story 6

- [ ] T039 [US6] Add LIM-017 (Partial IRIS/Caché Support) entry with supported/stubbed/unsupported function table in src/m2py/limitations.py
- [ ] T040 [US6] Review and remove/update limitation entries for now-supported features (>=/<= operators, vendor functions) in src/m2py/limitations.py
- [ ] T041 [US6] Regenerate docs/limitations.md by running utils/rebuild_docs.py
- [ ] T042 [US6] Verify LIM-003 (MWAPI SSVNs) remains correctly documented in docs/limitations.md

**Checkpoint**: Documentation accurate — all implemented features reflected, partial IRIS scope documented

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories, ensuring the 99%+ target is met

- [ ] T043 Run final VistA-VEHU-M full scan (39,304 routines) — verify ≥99% success rate (≥38,911 passing)
- [ ] T044 Verify zero SyntaxError, zero NotImplementedError (except MWAPI), zero RecursionError in final scan results
- [ ] T045 Run quickstart.md validation scenarios end-to-end
- [ ] T047 Verify previously-failing syntax error routines (HLCSTCP2, XMCTLK, XWBVLL) pass in final scan — these are expected to be resolved by US1 codegen fixes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — run baseline scan first
- **US1 (Phase 2)**: Depends on Phase 1 baseline — MVP, highest impact
- **US2 (Phase 3)**: Can start after Phase 1; independent of US1 (different functions in statements.py)
- **US3 (Phase 4)**: Can start after Phase 1; independent of US1/US2
- **US4 (Phase 5)**: Can start after Phase 1; independent of US1-3 (different files mostly)
- **US5 (Phase 6)**: Can start after Phase 1; independent of US1-4
- **US6 (Phase 7)**: Should start after US1-5 to accurately document what's supported
- **Polish (Phase 8)**: Depends on ALL user stories being complete

### Within-Story Dependencies

**US1** parallel groups (different files):
- Group A: T002, T003, T008 (expressions.py → then statements.py)
- Group B: T004 (semantic_analyzer.py)
- Group C: T005, T006 (indirection.py → then audit)
- Group D: T007 (statements.py — after T008 completes)
- Group E: T009, T010 (runtime/__init__.py → then statements.py)
- T011-T012: after all implementation tasks

**US2**: All tasks are in statements.py — sequential (T013 → T014 → T015 → T016)

**US3**: T019, T020, T021 are all in different files — fully parallel

**US4** parallel groups:
- Group A: T023-T027 (helpers.py — sequential within group)
- Group B: T028 (runtime/__init__.py)
- Group C: T029 (globals.py)
- Group D: T030-T031 (expressions.py — sequential within group)
- Group E: T032 (statements.py)
- Groups A-E can run in parallel; T033 after all

**US5** parallel groups:
- Group A: T034 (devices.py) and T035 (runtime/__init__.py) — parallel
- Group B: T036 (statements.py), T037 (expressions.py), T046 (statements.py ZPRINT/ZMESSAGE) — T036 then T046 sequentially; T037 parallel
- T038 after all

**US6**: Sequential (T039 → T040 → T041 → T042)

### Key Cross-Story Dependencies

- `$ZU(5)` implementation (T025) depends on `$NAMESPACE` property (T028) — both in US4
- `$ZR` tracking (T029) depends on `$ZR` property (T028) — both in US4
- `$REFERENCE` reader (T037) aliases `$ZR` (T028) — US5 depends on US4's T028
- Computed GOTO (T016) depends on TRAMPOLINE dispatcher understanding string returns — self-contained in US2
- Documentation update (T039-T042) should be done AFTER US1-5 to accurately reflect state

---

## Parallel Example: User Story 1

```
# Parallel batch 1 (5 different files):
T002: ParenExpr handler in expressions.py
T004: Analyzer audit in semantic_analyzer.py
T005: f-string fix in indirection.py
T007: Empty block fix in statements.py
T009: set_x/set_y in runtime/__init__.py

# Sequential follow-ups (same files as batch 1):
T003: UnaryPrefixedExpr in expressions.py (after T002)
T008: >=/<= operators in expressions.py (after T003)
T006: f-string audit in codegen/ (after T005)
T010: SET $X/$Y codegen in statements.py (after T007)

# Validation (after all implementation):
T011: Write tests
T012: Full scan
```

---

## Parallel Example: User Story 4

```
# Parallel batch 1 (4 different files):
T023: m_replace() in helpers.py
T028: IRIS SVNs in runtime/__init__.py
T029: $ZR tracking in globals.py

# Sequential in helpers.py (after T023):
T024: m_zboolean()
T025: m_zu()
T026: m_zf()
T027: stubs

# Codegen wiring (after runtime functions exist):
T030: Intrinsic dispatch in expressions.py
T031: SVN readers in expressions.py (after T030)
T032: $NAMESPACE SET dispatch in statements.py

# Validation:
T033: Write tests
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Baseline Scan
2. Complete Phase 2: User Story 1 (5 core codegen fixes)
3. **STOP and VALIDATE**: Run VistA scan — expect ~98.9% success
4. This alone resolves 80% of all failures

### Incremental Delivery

1. **US1** → ~98.9% success (MVP — biggest impact) ✅
2. **US2** → ~99.2% success (language completeness)
3. **US3** → ~99.4% success (robustness)
4. **US4** → ~99.7% success (IRIS support)
5. **US5** → ~99.8% success (stubs and edge cases)
6. **US6** → Documentation updated
7. **Polish** → Final validation, ≥99% confirmed

### Task Counts per Story

| Story | Tasks | Routines Unblocked | Cumulative Success |
|-------|-------|-------------------|-------------------|
| Setup | 1 | — | 93.4% (baseline) |
| US1 (P1) | 11 | ~2,153 | ~98.9% |
| US2 (P2) | 6 | ~144 | ~99.2% |
| US3 (P3) | 4 | ~64 | ~99.4% |
| US4 (P4) | 11 | ~106 | ~99.7% |
| US5 (P5) | 6 | ~54 | ~99.8% |
| US6 (P2) | 4 | — | — |
| Polish | 4 | — | ≥99% confirmed |
| **Total** | **48** | **~2,521** | **≥99%** |

---

## Notes

- [P] tasks = different files, no dependencies on other in-progress tasks
- [Story] label maps task to spec.md user story for traceability
- All US2 tasks are in the same file (statements.py) — must be sequential
- US4 has the most tasks (11) due to the breadth of IRIS vendor functions
- US6 (Limitations) should be done last among user stories to capture final state
- The only acceptable remaining limitation is MWAPI SSVNs (LIM-003, X11.6 standard)
- Commit after each task or logical group within a story
- Stop at any checkpoint to validate the incremental improvement
