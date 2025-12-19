# Tasks: MUMPS Semantic Graph Parser

**Input**: Design documents from `/specs/001-textx-semantic-graph/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/parser-api.md ✅

**Tests**: Tests are included as they are fundamental to the MUGJ validation approach defined in the specification (Constitution Principle II: Test-Driven Validation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md: src/m2py/{grammar,asg,parser,analysis,cli}/, tests/{unit,integration}/
- [X] T002 Add textX dependency (4.0+) to pyproject.toml
- [X] T003 [P] Create src/m2py/__init__.py with version and public API exports
- [X] T004 [P] Create src/m2py/grammar/__init__.py (empty placeholder)
- [X] T005 [P] Create src/m2py/asg/__init__.py with ASG element exports
- [X] T006 [P] Create src/m2py/parser/__init__.py with MUMPSParser export
- [X] T007 [P] Create src/m2py/analysis/__init__.py with analysis function exports
- [X] T008 [P] Create tests/unit/__init__.py (empty placeholder)
- [X] T009 [P] Create tests/integration/__init__.py (empty placeholder)
- [X] T010 Create pytest fixture for MUGJ file loading in tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### ASG Base Classes (from data-model.md)

- [ ] T011 Implement ASGElement base dataclass with source tracking in src/m2py/asg/elements.py
- [ ] T012 [P] Implement enumerations (ForLoopType, ForParamType, GotoType, CallType, LiteralType) in src/m2py/asg/enums.py
- [ ] T013 [P] Implement MExpr base and literal types (MLiteral, MVariable, MGlobal, MNakedGlobal) in src/m2py/asg/expressions.py
- [ ] T014 [P] Implement MBinaryOp, MUnaryOp, MIntrinsicFunction, MExtrinsicFunction in src/m2py/asg/expressions.py
- [ ] T015 [P] Implement MPatternMatch, MIndirection, MSpecialVariable in src/m2py/asg/expressions.py
- [ ] T016 Implement MStatement base, MScope container, MSetStatement in src/m2py/asg/statements.py
- [ ] T017 [P] Implement MWriteStatement, MReadStatement, MQuitStatement, MHaltStatement in src/m2py/asg/statements.py
- [ ] T018 [P] Implement MNewStatement, MKillStatement, MHangStatement in src/m2py/asg/statements.py
- [ ] T019 [P] Implement MXecuteStatement, MLockStatement, MMergeStatement, MViewStatement in src/m2py/asg/statements.py
- [ ] T020 Implement MRoutine, MLabel with back-reference support in src/m2py/asg/elements.py
- [ ] T021 Implement MCall with resolution tracking in src/m2py/asg/elements.py

### Parser Foundation (from contracts/parser-api.md)

- [ ] T022 Implement MUMPSSyntaxError exception class in src/m2py/parser/exceptions.py
- [ ] T023 Create minimal textX grammar skeleton in src/m2py/grammar/mumps.tx (routine, label, comment rules)
- [ ] T024 Implement MUMPSParser.__init__() with grammar loading in src/m2py/parser/parser.py
- [ ] T025 Implement MUMPSParser.parse() stub returning MRoutine in src/m2py/parser/parser.py
- [ ] T026 Implement MUMPSParser.parse_file() with file reading in src/m2py/parser/parser.py
- [ ] T027 Write unit test for MUMPSParser initialization in tests/unit/test_parser.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Parse and Analyze Simple MUMPS Routines (Priority: P1) 🎯 MVP

**Goal**: Parse MUMPS routines with SET, WRITE, IF, and simple bounded FOR constructs

**Independent Test**: Parse V1FORA.m and verify ASG contains correct labels, statements, and FOR loop classification

### Tests for User Story 1

- [ ] T028 [P] [US1] Unit test for SET statement parsing in tests/unit/test_grammar.py
- [ ] T029 [P] [US1] Unit test for WRITE statement parsing in tests/unit/test_grammar.py
- [ ] T030 [P] [US1] Unit test for bounded FOR parsing in tests/unit/test_grammar.py
- [ ] T031 [P] [US1] Unit test for simple IF parsing in tests/unit/test_grammar.py
- [ ] T032 [US1] Integration test: parse V1FORA.m in tests/integration/test_mugj.py

### Grammar Implementation for User Story 1

- [ ] T033 [US1] Add SET command grammar rule (S|SET target=expr, assignments) in src/m2py/grammar/mumps.tx
- [ ] T034 [P] [US1] Add WRITE command grammar rule (W|WRITE arguments) in src/m2py/grammar/mumps.tx
- [ ] T034a [P] [US1] Add READ command grammar rule (R|READ arguments with timeout) per FR-002 in src/m2py/grammar/mumps.tx
- [ ] T035 [P] [US1] Add QUIT command grammar rule (Q|QUIT return_value?) in src/m2py/grammar/mumps.tx
- [ ] T036 [US1] Add expression grammar (literals, local variables, subscripted variables per FR-013, globals ^NAME per FR-014, all operators per FR-005: +,-,*,/,\,#,**,=,<,>,',&,!,_,[,],]],?, unary +/-, strict L-to-R eval per FR-050) in src/m2py/grammar/mumps.tx
- [ ] T037 [US1] Add simple IF command grammar rule (I|IF condition?) in src/m2py/grammar/mumps.tx
- [ ] T038 [US1] Add bounded FOR command grammar rule (F|FOR var=start:step:end) in src/m2py/grammar/mumps.tx
- [ ] T039 [US1] Add postcondition grammar rule (: condition) in src/m2py/grammar/mumps.tx
- [ ] T040 [US1] Add line structure grammar (label, commands, dot blocks) in src/m2py/grammar/mumps.tx

### Statement ASG Mapping for User Story 1

- [ ] T041 [US1] Wire textX custom classes for MSetStatement in src/m2py/parser/parser.py
- [ ] T042 [P] [US1] Wire textX custom classes for MWriteStatement, MQuitStatement in src/m2py/parser/parser.py
- [ ] T043 [US1] Wire textX custom classes for MIfStatement with scope in src/m2py/parser/parser.py
- [ ] T044 [US1] Implement MForStatement with MForParameter capture in src/m2py/asg/statements.py
- [ ] T045 [US1] Wire textX custom classes for MForStatement in src/m2py/parser/parser.py

### Basic FOR Classification for User Story 1

- [ ] T046 [US1] Implement classify_for_loops() for BOUNDED type in src/m2py/analysis/classifier.py
- [ ] T047 [US1] Add MUMPSParser.classify_patterns() method calling classifier in src/m2py/parser/parser.py
- [ ] T048 [US1] Verify V1FORA.m FOR loops classified as BOUNDED in tests/integration/test_mugj.py

**Checkpoint**: User Story 1 complete - V1FORA.m parses with bounded FOR classification

---

## Phase 4: User Story 2 - Handle Complex FOR Loop Patterns (Priority: P2)

**Goal**: Correctly model FOR loops with multiple forparameters (string lists, mixed patterns, nested loops)

**Independent Test**: Parse V1FORB and V1FORC series files and verify all 5 FOR loop types are correctly classified

### Tests for User Story 2

- [ ] T049 [P] [US2] Unit test for string-list FOR (F I="A","B","C") in tests/unit/test_grammar.py
- [ ] T050 [P] [US2] Unit test for open-ended FOR (F I=1:1) in tests/unit/test_grammar.py
- [ ] T051 [P] [US2] Unit test for mixed FOR (F I="A",1:1:3) in tests/unit/test_grammar.py
- [ ] T052 [P] [US2] Unit test for argumentless FOR (F) in tests/unit/test_grammar.py
- [ ] T053 [US2] Integration test: parse V1FORB.m with multiple forparameters in tests/integration/test_mugj.py
- [ ] T054 [US2] Integration test: parse V1FORC.m with all FOR types in tests/integration/test_mugj.py

### Grammar Extensions for User Story 2

- [ ] T055 [US2] Extend FOR grammar for string-list forparameter (value list) in src/m2py/grammar/mumps.tx
- [ ] T056 [US2] Extend FOR grammar for open-ended forparameter (start:step without end) in src/m2py/grammar/mumps.tx
- [ ] T057 [US2] Extend FOR grammar for argumentless FOR (no var or params) in src/m2py/grammar/mumps.tx
- [ ] T058 [US2] Extend FOR grammar for nested FOR body scope in src/m2py/grammar/mumps.tx

### FOR Classification Complete for User Story 2

- [ ] T059 [US2] Extend classify_for_loops() for OPEN_ENDED type in src/m2py/analysis/classifier.py
- [ ] T060 [P] [US2] Extend classify_for_loops() for STRING_LIST type in src/m2py/analysis/classifier.py
- [ ] T061 [P] [US2] Extend classify_for_loops() for MIXED type in src/m2py/analysis/classifier.py
- [ ] T062 [P] [US2] Extend classify_for_loops() for ARGUMENTLESS type in src/m2py/analysis/classifier.py
- [ ] T063 [US2] Identify internal QUIT as loop exit points in classify_for_loops() in src/m2py/analysis/classifier.py
- [ ] T064 [US2] Verify V1FORC series FOR loops have correct types in tests/integration/test_mugj.py

**Checkpoint**: User Story 2 complete - All 5 FOR loop types correctly classified

---

## Phase 5: User Story 3 - Handle GOTO Across Control Boundaries (Priority: P2)

**Goal**: Fully classify GOTO statements by target, control structures exited, and jump direction

**Independent Test**: Parse V1GO1, V1GO2, V1FORC2 and verify all GOTO types classified with exit information

### Tests for User Story 3

- [ ] T065 [P] [US3] Unit test for GOTO to local label in tests/unit/test_grammar.py
- [ ] T066 [P] [US3] Unit test for GOTO to label+offset in tests/unit/test_grammar.py
- [ ] T067 [P] [US3] Unit test for GOTO to external routine (label^routine) in tests/unit/test_grammar.py
- [ ] T068 [US3] Integration test: parse V1GO1.m with simple GOTOs in tests/integration/test_mugj.py
- [ ] T069 [US3] Integration test: parse V1GO2.m with offset GOTOs in tests/integration/test_mugj.py
- [ ] T070 [US3] Integration test: parse V1FORC2.m with nested FOR+GOTO in tests/integration/test_mugj.py

### Grammar Extensions for User Story 3

- [ ] T071 [US3] Add GOTO command grammar rule (G|GOTO targets with postconditions) in src/m2py/grammar/mumps.tx
- [ ] T072 [US3] Add label reference grammar (name, name+offset, name^routine) in src/m2py/grammar/mumps.tx
- [ ] T073 [US3] Implement MGotoStatement ASG element with target list in src/m2py/asg/statements.py

### Reference Resolution for User Story 3

- [ ] T074 [US3] Implement resolve_references() scanning for MCall objects in src/m2py/analysis/resolver.py
- [ ] T075 [US3] Implement label lookup by name in resolve_references() in src/m2py/analysis/resolver.py
- [ ] T076 [US3] Populate MCall.target with resolved MLabel in src/m2py/analysis/resolver.py
- [ ] T077 [US3] Populate MLabel.callers and MLabel.goto_sources back-references in src/m2py/analysis/resolver.py
- [ ] T078 [US3] Add MUMPSParser.resolve_references() method in src/m2py/parser/parser.py
- [ ] T079 [US3] Verify V1GO1 GOTO targets resolved in tests/integration/test_mugj.py

### GOTO Classification for User Story 3

- [ ] T080 [US3] Implement classify_gotos() for FORWARD_JUMP detection in src/m2py/analysis/classifier.py
- [ ] T081 [P] [US3] Extend classify_gotos() for BACKWARD_JUMP detection in src/m2py/analysis/classifier.py
- [ ] T082 [P] [US3] Extend classify_gotos() for LOOP_EXIT detection (single FOR) in src/m2py/analysis/classifier.py
- [ ] T083 [US3] Extend classify_gotos() for MULTI_LOOP_EXIT detection (nested FORs) in src/m2py/analysis/classifier.py
- [ ] T084 [P] [US3] Extend classify_gotos() for CROSS_LABEL detection in src/m2py/analysis/classifier.py
- [ ] T085 [P] [US3] Extend classify_gotos() for EXTERNAL detection (^routine) in src/m2py/analysis/classifier.py
- [ ] T086 [US3] Populate exits_loops list with enclosing MForStatements in src/m2py/analysis/classifier.py
- [ ] T087 [US3] Verify V1FORC2 GOTO exits nested loops correctly in tests/integration/test_mugj.py

**Checkpoint**: User Story 3 complete - All 6 GOTO types classified with loop exit info

---

## Phase 6: User Story 4 - Variable Scope and Data Flow Analysis (Priority: P3)

**Goal**: Track variable usage across scopes, identify inputs/outputs, respect NEW boundaries

**Independent Test**: Parse a routine with NEW and subroutine calls, verify input/output variable sets

### Tests for User Story 4

- [ ] T088 [P] [US4] Unit test for NEW command parsing in tests/unit/test_grammar.py
- [ ] T089 [P] [US4] Unit test for exclusive NEW (N (X)) in tests/unit/test_grammar.py
- [ ] T090 [P] [US4] Unit test for DO command parsing in tests/unit/test_grammar.py
- [ ] T091 [US4] Integration test: parse V1NX1.m with NEW commands in tests/integration/test_mugj.py
- [ ] T092 [US4] Integration test: parse V1DO1.m with subroutine calls in tests/integration/test_mugj.py

### Grammar Extensions for User Story 4

- [ ] T093 [US4] Add NEW command grammar rule (N|NEW vars or exclusive) in src/m2py/grammar/mumps.tx
- [ ] T094 [US4] Add DO command grammar rule (D|DO targets with arguments) in src/m2py/grammar/mumps.tx
- [ ] T095 [US4] Add argumentless DO (inline block) grammar in src/m2py/grammar/mumps.tx
- [ ] T096 [US4] Implement MDoStatement ASG element in src/m2py/asg/statements.py
- [ ] T097 [US4] Implement MDoBlockStatement (argumentless DO) in src/m2py/asg/statements.py

### Variable Analysis for User Story 4

- [ ] T098 [US4] Implement analyze_variables() collecting variable reads in src/m2py/analysis/variables.py
- [ ] T099 [US4] Extend analyze_variables() collecting variable writes in src/m2py/analysis/variables.py
- [ ] T100 [US4] Extend analyze_variables() respecting NEW boundaries in src/m2py/analysis/variables.py
- [ ] T101 [US4] Compute input_variables (read before first write) in src/m2py/analysis/variables.py
- [ ] T102 [US4] Compute output_variables (written and visible to caller) in src/m2py/analysis/variables.py
- [ ] T103 [US4] Implement Def-Use chain analysis per FR-051 in src/m2py/analysis/variables.py
- [ ] T104 [US4] Implement transitive closure for call chain variable propagation per FR-042 in src/m2py/analysis/variables.py
- [ ] T105 [US4] Add MUMPSParser.analyze_variables() method in src/m2py/parser/parser.py
- [ ] T106 [US4] Implement unreachable code detection after unconditional GOTO/QUIT per FR-053 in src/m2py/analysis/classifier.py
- [ ] T107 [US4] Verify V1NX1 variable scope respects NEW in tests/integration/test_mugj.py

**Checkpoint**: User Story 4 complete - Variable inputs/outputs computed correctly

---

## Phase 7: User Story 5 - Parse Special MUMPS Features (Priority: P3)

**Goal**: Correctly represent pattern matching, intrinsic functions, $TEST, indirection in ASG

**Independent Test**: Parse MUGJ files covering intrinsic functions, pattern matching, verify ASG representation

### Tests for User Story 5

- [ ] T108 [P] [US5] Unit test for pattern match expression (X?1A.N) in tests/unit/test_grammar.py
- [ ] T109 [P] [US5] Unit test for $PIECE intrinsic function in tests/unit/test_grammar.py
- [ ] T110 [P] [US5] Unit test for $SELECT intrinsic function in tests/unit/test_grammar.py
- [ ] T111 [P] [US5] Unit test for $TEST special variable in tests/unit/test_grammar.py
- [ ] T112 [P] [US5] Unit test for indirection (@variable) in tests/unit/test_grammar.py
- [ ] T113 [US5] Integration test: parse V1PAT.m with patterns in tests/integration/test_mugj.py
- [ ] T114 [US5] Integration test: parse V1FN* files with functions in tests/integration/test_mugj.py

### Grammar Extensions for User Story 5

- [ ] T115 [US5] Add intrinsic function grammar ($fn(args)) in src/m2py/grammar/mumps.tx
- [ ] T116 [US5] Add all intrinsic function names per FR-003 in src/m2py/grammar/mumps.tx
- [ ] T117 [US5] Add special variable grammar ($TEST, $HOROLOG, etc.) per FR-004 in src/m2py/grammar/mumps.tx
- [ ] T118 [US5] Add pattern match expression grammar (X?pattern) in src/m2py/grammar/mumps.tx
- [ ] T119 [US5] Add indirection grammar (@expr) in src/m2py/grammar/mumps.tx
- [ ] T120 [US5] Add extrinsic function/variable grammar ($$func^routine with args per FR-018, $$VAR without args per FR-019) in src/m2py/grammar/mumps.tx

### Special Feature ASG Mapping for User Story 5

- [ ] T121 [US5] Wire textX custom classes for MIntrinsicFunction in src/m2py/parser/parser.py
- [ ] T122 [P] [US5] Wire textX custom classes for MExtrinsicFunction in src/m2py/parser/parser.py
- [ ] T123 [P] [US5] Wire textX custom classes for MPatternMatch in src/m2py/parser/parser.py
- [ ] T124 [P] [US5] Wire textX custom classes for MIndirection in src/m2py/parser/parser.py
- [ ] T125 [P] [US5] Wire textX custom classes for MSpecialVariable in src/m2py/parser/parser.py
- [ ] T126 [US5] Flag indirection for runtime evaluation (requires_runtime_eval) in src/m2py/analysis/classifier.py
- [ ] T127 [US5] Verify V1PAT patterns captured correctly in tests/integration/test_mugj.py

**Checkpoint**: User Story 5 complete - All special MUMPS features represented in ASG

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Full MUGJ validation, performance, and cleanup

### Full MUGJ Validation (SC-001)

- [ ] T128 Add MUGJ parse loop test for all ~280 files in tests/integration/test_mugj.py
- [ ] T129 Create list of files failing parse for triage in tests/integration/test_mugj.py
- [ ] T130 [P] Add missing command grammars (BREAK, HALT, HANG, LOCK, MERGE, VIEW, JOB, OPEN, CLOSE, USE) in src/m2py/grammar/mumps.tx
- [ ] T131 [P] Add ELSE command grammar (E|ELSE body) in src/m2py/grammar/mumps.tx
- [ ] T132 [P] Add XECUTE command grammar (X|XECUTE expr) in src/m2py/grammar/mumps.tx
- [ ] T133 [P] Add KILL command grammar (K|KILL vars) in src/m2py/grammar/mumps.tx
- [ ] T134 Fix failing MUGJ files iteratively until 100% parse rate
- [ ] T135 Verify SC-001: 100% MUGJ parse rate in tests/integration/test_mugj.py

### Performance Validation (SC-005)

- [ ] T136 Add benchmark test for 500-line routine parse time in tests/unit/test_parser.py
- [ ] T137 Verify SC-005: parse time <2s for 500 lines
- [ ] T138 Profile and optimize grammar if needed

### Error Handling (SC-007)

- [ ] T139 Verify MUMPSSyntaxError includes line/column in tests/unit/test_parser.py
- [ ] T140 Add source position propagation to all ASG elements

### Serialization & Debugging

- [ ] T141 Implement to_dict() serialization for ASG per data-model.md in src/m2py/asg/elements.py
- [ ] T142 Add ASG JSON dump for debugging in src/m2py/parser/parser.py

### Documentation

- [ ] T143 [P] Update README.md with parser usage examples
- [ ] T144 [P] Add inline docstrings to all public API methods
- [ ] T145 Run quickstart.md validation steps to ensure setup works

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (P1): Can start immediately after Foundation
  - US2 (P2): Can start after US1 (builds on FOR grammar)
  - US3 (P2): Can start in parallel with US2 (independent GOTO feature)
  - US4 (P3): Can start after US1 (needs basic parsing)
  - US5 (P3): Can start after US1 (needs basic parsing)
- **Polish (Phase 8)**: Depends on all user stories for full validation

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 | Foundation | None (MVP first) |
| US2 | US1 (FOR grammar base) | US3 |
| US3 | US1 (basic parsing) | US2 |
| US4 | US1 (basic parsing) | US3, US5 |
| US5 | US1 (basic parsing) | US3, US4 |

### Within Each User Story

1. Tests written FIRST (should fail before implementation)
2. Grammar rules before ASG wiring
3. ASG wiring before analysis passes
4. Integration test verification at end

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T003, T004, T005, T006, T007, T008, T009 can run in parallel
```

**Phase 2 (Foundation)**:
```
After T011 (base): T012, T013, T014, T015 can run in parallel
After T016 (statements base): T017, T018, T019 can run in parallel
```

**User Stories**:
```
After US1 complete:
  - US2 and US3 can run in parallel
  - US4 and US5 can run in parallel with US3
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (~10 tasks)
2. Complete Phase 2: Foundational (~17 tasks)
3. Complete Phase 3: User Story 1 (~21 tasks)
4. **STOP and VALIDATE**: V1FORA.m parses with bounded FOR classification
5. Deploy/demo if ready

### Incremental Delivery

| Increment | Stories | Validation |
|-----------|---------|------------|
| MVP | US1 | V1FORA.m parses |
| Iteration 2 | US1 + US2 | V1FORC series passes |
| Iteration 3 | US1-3 | V1FORC2 GOTO+FOR works |
| Iteration 4 | US1-4 | V1NX variable scope works |
| Iteration 5 | US1-5 | All special features |
| Final | All + Polish | 100% MUGJ |

### Risk Mitigation

- **GOTO in nested FOR (High Risk)**: Address in US3 early; V1FORC2 is the key test
- **Grammar complexity (Medium Risk)**: Build incrementally; validate each command
- **Performance (Low Risk)**: Defer optimization to Polish phase

---

## Summary

| Phase | Tasks | Story |
|-------|-------|-------|
| Setup | T001-T010 (10) | Infrastructure |
| Foundational | T011-T027 (17) | Core ASG + Parser |
| User Story 1 | T028-T048 (21) | Simple MUMPS (P1 MVP) |
| User Story 2 | T049-T064 (16) | Complex FOR (P2) |
| User Story 3 | T065-T087 (23) | GOTO Classification (P2) |
| User Story 4 | T088-T107 (20) | Variable Scope (P3) |
| User Story 5 | T108-T127 (20) | Special Features (P3) |
| Polish | T128-T145 (18) | Full Validation |
| **Total** | **145 tasks** | |

### Parallel Opportunities Summary

- **Phase 1**: 7 tasks parallelizable
- **Phase 2**: 11 tasks parallelizable (after dependencies)
- **User Stories**: US2||US3, US4||US5 (after US1)
- **Per-story tests**: All unit tests within a story are parallelizable

### Independent Test Criteria

| Story | Test Criteria |
|-------|---------------|
| US1 | V1FORA.m parses, FOR classified BOUNDED |
| US2 | V1FORC series passes, all 5 FOR types classified |
| US3 | V1FORC2 GOTOs resolved, exits nested loops |
| US4 | V1NX1 variable scope respects NEW |
| US5 | V1PAT patterns captured, functions parsed |

### Suggested MVP Scope

**User Story 1 only** (48 tasks through Phase 3)
- Validates core architecture
- Proves textX grammar approach
- Demonstrates ASG structure
- Provides foundation for remaining stories
