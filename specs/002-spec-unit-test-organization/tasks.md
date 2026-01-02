# Tasks: MUMPS Spec-Aligned Unit Test Organization

**Input**: Design documents from `/specs/002-spec-unit-test-organization/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅, contracts/test-markers.md ✅

**Tests**: This feature IS about tests - stub tests are the deliverable, not optional.

**Organization**: Tasks are grouped by user story to enable independent implementation and validation of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and register pytest markers

- [X] T001 Create parser test directory structure: tests/unit/parser/{s5_metalanguage,s6_routine,s7_expressions,s8_commands,s9_charset,extensions/ydb}/
- [X] T002 [P] Create asg test directory structure: tests/unit/asg/{s5_metalanguage,s6_routine,s7_expressions,s8_commands,s9_charset,extensions/ydb}/
- [X] T003 [P] Create codegen test directory structure: tests/unit/codegen/{s5_metalanguage,s6_routine,s7_expressions,s8_commands,s9_charset,extensions/ydb}/
- [X] T004 [P] Create cross_cutting test directory: tests/unit/cross_cutting/
- [X] T005 [P] Create analysis test directory: tests/unit/analysis/ (Note: most analysis/ files are created during Phase 8 migration, not as empty stubs—this creates the directory only)
- [X] T006 [P] Create meta test directory: tests/unit/meta/ (Note: most meta/ files are created during Phase 8 migration, not as empty stubs—this creates the directory only)
- [X] T007 Register pytest markers in tests/conftest.py (parser, asg, codegen, stub, slow, pre1995, ydb)
- [X] T008 [P] Create __init__.py files in all new directories

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish marker validation and shared fixtures before creating stub tests

**⚠️ CRITICAL**: No stub creation can begin until markers are registered and validated

- [X] T009 Add marker validation hook to tests/conftest.py (warn on missing category marker during migration)
- [X] T010 Create shared parser fixture in tests/unit/parser/conftest.py
- [X] T011 [P] Create shared ASG analysis fixture in tests/unit/asg/conftest.py
- [X] T011a [P] Create shared analysis fixture in tests/unit/analysis/conftest.py (if needed for classifier/resolver tests)
- [X] T012 [P] Create shared codegen execution fixture in tests/unit/codegen/conftest.py
- [X] T012a [P] Create shared codegen validation helper in tests/unit/codegen/conftest.py: `compare_output_to_functional_suite(routine_name, output)` that compares against tests/functional/ baselines (satisfies FR-029)
- [X] T013 Verify markers work: `uv run pytest --markers | grep -E "parser|asg|codegen|stub|slow|pre1995|ydb"` (all 7 markers from T007)
- [X] T013a Verify test naming convention document exists at specs/002-spec-unit-test-organization/contracts/test-naming.md (created during design phase)
- [X] T014 Create stub test template file at tests/unit/STUB_TEMPLATE.py for copy-paste reuse (MUST include spec section docstring per FR-004)

**Checkpoint**: Foundation ready - stub creation can now begin

---

## Phase 3: User Story 8 - Stub Management Infrastructure (Priority: P1) 🎯 MVP

**Goal**: Establish xfail stub pattern so CI stays green throughout migration

**Independent Test**: Run `uv run pytest tests/unit/parser/s8_commands/test_s8_2_18_set.py` and verify stubs show as xfail with exit code 0

### Implementation for US8

- [X] T015 [US8] Create first stub file tests/unit/parser/s8_commands/test_s8_2_18_set.py with 3 xfail stubs (include single and multiple argument forms per edge case requirement)
- [X] T016 [US8] Verify stub runs as xfail: `uv run pytest tests/unit/parser/s8_commands/test_s8_2_18_set.py -v`
- [X] T016a [US8] Verify xfail/skip reasons visible: `uv run pytest tests/unit/parser/s8_commands/test_s8_2_18_set.py -v 2>&1 | grep -E "xfail|skip"` (FR-019, depends on T015)
- [X] T017 [US8] Verify `pytest -m "not stub"` excludes the stub tests
- [X] T018 [US8] Verify `pytest -m stub --collect-only` lists only stub tests

**Checkpoint**: Stub infrastructure validated - bulk stub creation can proceed

---

## Phase 4: User Story 1 - Parser Test Stubs (Priority: P1)

**Goal**: Create stub test files for all parser-level spec sections

**Independent Test**: `uv run pytest tests/unit/parser/ --collect-only` shows all spec sections covered

### §5 Metalanguage (parser) - Out-of-Scope

- [X] T018a [P] [US1] Create tests/unit/parser/s5_metalanguage/test_s5_1_bnf_notation.py with skip (out-of-scope per FR-055: informative, no executable semantics)

### §6 Routine Structure (parser)

- [X] T019 [P] [US1] Create tests/unit/parser/s6_routine/test_s6_1_routine_head.py with stubs
- [X] T020 [P] [US1] Create tests/unit/parser/s6_routine/test_s6_2_routine_body.py with stubs (covers §6.2.1-6.2.5: levelline, formalline, label, label separator, linebody)
- [X] T021 [P] [US1] Create tests/unit/parser/s6_routine/test_s6_3_1_indirection.py with stubs (§6.3.1 Generic Indirection)
- [X] T021b [P] [US1] Create tests/unit/parser/s6_routine/test_s6_3_1_transaction.py with stubs (§6.3.1 Transaction processing - cross-reference TSTART/TCOMMIT/TROLLBACK)
- [X] T021c [P] [US1] Create tests/unit/parser/s6_routine/test_s6_3_2_error_processing.py with stubs (§6.3.2 Error processing - cross-reference $ETRAP/$ECODE)
- [X] T021d [P] [US1] Create tests/unit/parser/s6_routine/test_s6_3_4_event_processing.py with skip (§6.3.4 out-of-scope per FR-055)
- [X] T021a [P] [US1] Create tests/unit/parser/s6_routine/test_s6_4_embedded_programs.py with skip (out-of-scope per FR-055)

### §7 Expressions (parser)

- [X] T022 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_1_values.py with stubs
- [X] T023 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_2_variables.py with stubs (lvn, gvn, glvn)
- [X] T024 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_3_ssvns.py with stubs (per-SSVN per SSVN_LIST in contracts/test-naming.md; skip-marked: ^$LIBRARY, ^$EVENT per FR-055) [Cross-ref: T066 ASG, T107 codegen - keep SSVN lists synchronized]
- [X] T025 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_4_literals.py with stubs
- [X] T026 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_5_intrinsic_functions.py with stubs (per-function: $ASCII, $CHAR, $DATA, $DEXTRACT [deprecated—@pytest.mark.pre1995], $DPIECE [deprecated—@pytest.mark.pre1995], $EXTRACT, $FIND, $FNUMBER, $GET, $HOROLOG [function form], $JUSTIFY, $LENGTH, $MUMPS, $NAME, $NEXT [deprecated—@pytest.mark.pre1995], $ORDER, $PIECE, $QLENGTH, $QSUBSCRIPT, $QUERY, $RANDOM, $REVERSE, $SELECT, $STACK, $TEXT, $TRANSLATE, $TYPE, $VIEW, $Z [implementation-defined])
- [X] T027 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_6_extrinsic_functions.py with stubs
- [X] T028 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_7_special_variables.py with stubs (per-variable: $DEVICE, $ECODE, $EREF, $ESTACK, $ETRAP, $HOROLOG, $IO, $IOREFERENCE, $JOB, $KEY, $PDISPLAY, $PIOREFERENCE, $PRINCIPAL, $QUIT, $REFERENCE, $STACK, $STORAGE, $SYSTEM, $TEST, $TLEVEL, $TRESTART, $X, $Y)
- [X] T029 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_2_operators.py with stubs
- [X] T030 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_2_5_pattern_match.py with stubs (quantifiers, alternation, pattern indirection)
- [X] T031 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_3_indirection.py with stubs

### §8 Commands (parser) - General Rules

- [X] T032 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_1_general_rules.py with stubs (spaces, comments, postconditions, timeouts, **abbreviated vs full command keywords per FR-009**: e.g., `S` vs `SET`, `W` vs `WRITE`). MUST include abbreviation parity tests verifying `S X=1` and `SET X=1` produce identical ASG structure for each implemented command

### §8 Commands (parser) - Individual Commands

- [X] T033 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_01_break.py with stubs
- [X] T034 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_02_close.py with stubs
- [X] T035 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_03_do.py with stubs
- [X] T036 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_04_else.py with stubs
- [X] T037 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_05_for.py with stubs
- [X] T038 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_06_goto.py with stubs
- [X] T039 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_07_halt.py with stubs
- [X] T040 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_08_hang.py with stubs
- [X] T041 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_09_if.py with stubs
- [X] T042 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_10_job.py with stubs
- [X] T043 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_11_kill.py with stubs (include single and multiple argument forms)
- [X] T044 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_12_lock.py with stubs
- [X] T045 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_13_merge.py with stubs
- [X] T046 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_14_new.py with stubs
- [X] T047 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_15_open.py with stubs
- [X] T048 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_16_quit.py with stubs
- [X] T049 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_17_read.py with stubs
- [X] T050 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_18_set.py with stubs
- [X] T051 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_19_tcommit.py with stubs
- [X] T052 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_20_trestart.py with stubs
- [X] T052a [P] [US1] Create tests/unit/parser/s8_commands/test_s8_ksubscripts.py with stubs (shares §8.2.20 numbering with TRESTART)
- [X] T053 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_21_trollback.py with stubs
- [X] T053a [P] [US1] Create tests/unit/parser/s8_commands/test_s8_kvalue.py with stubs (shares §8.2.21 numbering with TROLLBACK)
- [X] T054 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_22_tstart.py with stubs
- [X] T055 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_23_use.py with stubs
- [X] T056 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_24_view.py with skip (implementation-defined)
- [X] T057 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_25_write.py with stubs (include single and multiple argument forms)
- [X] T058 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_26_xecute.py with stubs
- [X] T058a [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_27_zcommand.py with stubs (Z-commands)
- [X] T059 [P] [US1] Create tests/unit/parser/s8_commands/test_s8_3_device_params.py with stubs
- [X] T059a [P] [US1] Create tests/unit/parser/s8_commands/test_s8_event_processing.py with skip (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER - out-of-scope per FR-055)
- [X] T059b [P] [US1] Create tests/unit/parser/s8_commands/test_s8_then_command.py with skip (THEN §8.2.32 - out-of-scope per FR-055, zero real-world usage)
- [X] T059c [P] [US1] Create tests/unit/parser/s8_commands/test_s8_assign.py with skip (out-of-scope per FR-055: ASSIGN command)
- [X] T059d [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_28_rload.py with skip (out-of-scope per FR-055: RLOAD command)
- [X] T059e [P] [US1] Create tests/unit/parser/s8_commands/test_s8_2_29_rsave.py with skip (out-of-scope per FR-055: RSAVE command)

### §9 Character Set (parser)

- [X] T060 [P] [US1] Create tests/unit/parser/s9_charset/test_s9_1_definitions.py with stubs

**Checkpoint**: All parser-level spec sections have stub files

---

## Phase 5: User Story 2 - ASG Test Stubs (Priority: P1)

**Goal**: Create stub test files for all ASG-level spec sections (parallel structure to parser)

**Independent Test**: `uv run pytest tests/unit/asg/ --collect-only` shows all spec sections covered

### §5 Metalanguage (ASG) - Out-of-Scope

- [X] T060a [P] [US2] Create tests/unit/asg/s5_metalanguage/test_s5_1_bnf_notation.py with skip (out-of-scope per FR-055: informative, no executable semantics)

### §6 Routine Structure (ASG)

- [X] T061 [P] [US2] Create tests/unit/asg/s6_routine/test_s6_1_routine_head.py with stubs
- [X] T062 [P] [US2] Create tests/unit/asg/s6_routine/test_s6_2_routine_body.py with stubs (covers §6.2.1-6.2.5)
- [X] T063 [P] [US2] Create tests/unit/asg/s6_routine/test_s6_3_1_indirection.py with stubs (§6.3.1 Generic Indirection)
- [X] T063b [P] [US2] Create tests/unit/asg/s6_routine/test_s6_3_1_transaction.py with stubs (§6.3.1 Transaction processing)
- [X] T063c [P] [US2] Create tests/unit/asg/s6_routine/test_s6_3_2_error_processing.py with stubs (§6.3.2 Error processing)
- [X] T063d [P] [US2] Create tests/unit/asg/s6_routine/test_s6_3_4_event_processing.py with skip (§6.3.4 out-of-scope per FR-055)
- [X] T063a [P] [US2] Create tests/unit/asg/s6_routine/test_s6_4_embedded_programs.py with skip (out-of-scope per FR-055)

### §7 Expressions (ASG)

- [X] T064 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_1_values.py with stubs
- [X] T065 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_2_variables.py with stubs (lvn, gvn, glvn resolution)
- [X] T066 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_3_ssvns.py with stubs (per-SSVN per SSVN_LIST in contracts/test-naming.md; skip-marked: ^$LIBRARY, ^$EVENT per FR-055) [Cross-ref: T024 parser, T107 codegen - keep SSVN lists synchronized]
- [X] T067 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_4_literals.py with stubs
- [X] T068 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_5_intrinsic_functions.py with stubs (per-function: $ASCII, $CHAR, $DATA, $DEXTRACT [deprecated—@pytest.mark.pre1995], $DPIECE [deprecated—@pytest.mark.pre1995], $EXTRACT, $FIND, $FNUMBER, $GET, $HOROLOG [function form], $JUSTIFY, $LENGTH, $MUMPS, $NAME, $NEXT [deprecated—@pytest.mark.pre1995], $ORDER, $PIECE, $QLENGTH, $QSUBSCRIPT, $QUERY, $RANDOM, $REVERSE, $SELECT, $STACK, $TEXT, $TRANSLATE, $TYPE, $VIEW, $Z [implementation-defined])
- [X] T069 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_6_extrinsic_functions.py with stubs
- [X] T070 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_7_special_variables.py with stubs (per-variable: $DEVICE, $ECODE, $EREF, $ESTACK, $ETRAP, $HOROLOG, $IO, $IOREFERENCE, $JOB, $KEY, $PDISPLAY, $PIOREFERENCE, $PRINCIPAL, $QUIT, $REFERENCE, $STACK, $STORAGE, $SYSTEM, $TEST, $TLEVEL, $TRESTART, $X, $Y)
- [X] T071 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_2_operators.py with stubs
- [X] T072 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_2_5_pattern_match.py with stubs (quantifiers, alternation)
- [X] T073 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_3_indirection.py with stubs (name, argument, pattern)

### §8 Commands (ASG) - General Rules

- [X] T074 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_1_general_rules.py with stubs (postconditions, timeouts, line refs, param passing)

### §8 Commands (ASG) - Individual Commands

- [X] T075 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_01_break.py with stubs
- [X] T076 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_02_close.py with stubs
- [X] T077 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_03_do.py with stubs (MCall resolution)
- [X] T078 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_04_else.py with stubs
- [X] T079 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_05_for.py with stubs (ForLoopType classification)
- [X] T080 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_06_goto.py with stubs (GotoType classification)
- [X] T081 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_07_halt.py with stubs
- [X] T082 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_08_hang.py with stubs
- [X] T083 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_09_if.py with stubs ($TEST modification)
- [X] T084 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_10_job.py with stubs
- [X] T085 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_11_kill.py with stubs
- [X] T086 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_12_lock.py with stubs
- [X] T087 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_13_merge.py with stubs
- [X] T088 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_14_new.py with stubs (variable scoping, Exclusive NEW)
- [X] T089 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_15_open.py with stubs
- [X] T090 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_16_quit.py with stubs
- [X] T091 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_17_read.py with stubs
- [X] T092 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_18_set.py with stubs (variable tracking)
- [X] T093 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_19_tcommit.py with stubs
- [X] T094 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_20_trestart.py with stubs
- [X] T094a [P] [US2] Create tests/unit/asg/s8_commands/test_s8_ksubscripts.py with stubs (shares §8.2.20 numbering with TRESTART)
- [X] T095 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_21_trollback.py with stubs
- [X] T095a [P] [US2] Create tests/unit/asg/s8_commands/test_s8_kvalue.py with stubs (shares §8.2.21 numbering with TROLLBACK)
- [X] T096 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_22_tstart.py with stubs ($TLEVEL tracking)
- [X] T097 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_23_use.py with stubs
- [X] T098 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_24_view.py with skip (implementation-defined)
- [X] T099 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_25_write.py with stubs
- [X] T100 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_26_xecute.py with stubs
- [X] T100a [P] [US2] Create tests/unit/asg/s8_commands/test_s8_2_27_zcommand.py with stubs (Z-commands)
- [X] T101 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_3_device_params.py with stubs
- [X] T102 [P] [US2] Create tests/unit/asg/s8_commands/test_s8_event_processing.py with skip (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER - out-of-scope per FR-055)
- [X] T102a [P] [US2] Create tests/unit/asg/s8_commands/test_s8_then_command.py with skip (THEN command - out-of-scope per FR-055)
- [X] T102b [P] [US2] Create tests/unit/asg/s8_commands/test_s8_assign.py with skip (out-of-scope per FR-055: ASSIGN command)
- [X] T102c [P] [US2] Create tests/unit/asg/s8_commands/test_s8_rload.py with skip (out-of-scope per FR-055: RLOAD command)
- [X] T102d [P] [US2] Create tests/unit/asg/s8_commands/test_s8_rsave.py with skip (out-of-scope per FR-055: RSAVE command)

### §9 Character Set (ASG)

- [X] T103 [P] [US2] Create tests/unit/asg/s9_charset/test_s9_1_definitions.py with stubs

### FR-010-014 Validation Tasks

- [X] T103a [US2] Verify ASG stubs include assertions for `loop_type`, `goto_type` fields per FR-012 (spot-check 5 files)
- [X] T103b [US2] Verify ASG stubs include assertions for reference resolution per FR-013 (spot-check MCall.target linked to MLabel)
- [X] T103c [US2] Verify ASG stubs include assertions for variable scope analysis per FR-014 (spot-check input_variables, output_variables)

**Checkpoint**: All ASG-level spec sections have stub files; FR-010-014 compliance verified

---

## Phase 6: User Story 7 - Codegen Test Stubs (Priority: P2)

**Goal**: Create stub test files for codegen-level spec sections

**Independent Test**: `uv run pytest tests/unit/codegen/ --collect-only` shows all spec sections covered

### §5 Metalanguage (Codegen) - Out-of-Scope

- [X] T103d [P] [US7] Create tests/unit/codegen/s5_metalanguage/test_s5_1_bnf_notation.py with skip (out-of-scope per FR-055: informative, no executable semantics)

### §6 Routine Structure (Codegen)

- [X] T104 [P] [US7] Create tests/unit/codegen/s6_routine/test_s6_1_routine_head.py with stubs
- [X] T104a [P] [US7] Create tests/unit/codegen/s6_routine/test_s6_2_routine_body.py with stubs (covers §6.2.1-6.2.5)
- [X] T104b [P] [US7] Create tests/unit/codegen/s6_routine/test_s6_3_1_indirection.py with stubs (§6.3.1 Generic Indirection)
- [X] T104c [P] [US7] Create tests/unit/codegen/s6_routine/test_s6_3_1_transaction.py with stubs (§6.3.1 Transaction processing)
- [X] T104d [P] [US7] Create tests/unit/codegen/s6_routine/test_s6_3_2_error_processing.py with stubs (§6.3.2 Error processing)
- [X] T104e [P] [US7] Create tests/unit/codegen/s6_routine/test_s6_3_4_event_processing.py with skip (§6.3.4 out-of-scope per FR-055)
- [X] T104f [P] [US7] Create tests/unit/codegen/s6_routine/test_s6_4_embedded_programs.py with skip (out-of-scope per FR-055)

### §7 Expressions (Codegen)

- [X] T105 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_1_values.py with stubs
- [X] T106 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py with stubs (local/global access)
- [X] T107 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py with stubs (per-SSVN per SSVN_LIST in contracts/test-naming.md; skip-marked: ^$LIBRARY, ^$EVENT per FR-055) [Cross-ref: T024 parser, T066 ASG - keep SSVN lists synchronized]
- [X] T108 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_4_literals.py with stubs
- [X] T109 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py with stubs (per-function: $ASCII, $CHAR, $DATA, $DEXTRACT [deprecated—@pytest.mark.pre1995], $DPIECE [deprecated—@pytest.mark.pre1995], $EXTRACT, $FIND, $FNUMBER, $GET, $HOROLOG [function form], $JUSTIFY, $LENGTH, $MUMPS, $NAME, $NEXT [deprecated—@pytest.mark.pre1995], $ORDER, $PIECE, $QLENGTH, $QSUBSCRIPT, $QUERY, $RANDOM, $REVERSE, $SELECT, $STACK, $TEXT, $TRANSLATE, $TYPE, $VIEW, $Z [implementation-defined])
- [X] T110 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py with stubs
- [X] T111 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py with stubs (per-variable: $DEVICE, $ECODE, $EREF, $ESTACK, $ETRAP, $HOROLOG, $IO, $IOREFERENCE, $JOB, $KEY, $PDISPLAY, $PIOREFERENCE, $PRINCIPAL, $QUIT, $REFERENCE, $STACK, $STORAGE, $SYSTEM, $TEST, $TLEVEL, $TRESTART, $X, $Y)
- [X] T112 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_2_operators.py with stubs (L-to-R evaluation)
- [X] T113 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_2_5_pattern_match.py with stubs
- [X] T114 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_3_indirection.py with stubs

### §8 Commands (Codegen) - General Rules

- [X] T115 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_1_general_rules.py with stubs (postconditions, timeouts behavior)

### §8 Commands (Codegen) - Individual Commands

- [X] T116 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_01_break.py with stubs
- [X] T117 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_02_close.py with stubs
- [X] T118 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_03_do.py with stubs
- [X] T119 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_04_else.py with stubs
- [X] T120 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_05_for.py with stubs
- [X] T121 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_06_goto.py with stubs
- [X] T122 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_07_halt.py with stubs
- [X] T123 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_08_hang.py with stubs
- [X] T124 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_09_if.py with stubs
- [X] T125 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_10_job.py with stubs
- [X] T126 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_11_kill.py with stubs
- [X] T127 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_12_lock.py with stubs
- [X] T128 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_13_merge.py with stubs
- [X] T129 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_14_new.py with stubs (Exclusive NEW behavior)
- [X] T130 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_15_open.py with stubs
- [X] T131 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_16_quit.py with stubs
- [X] T132 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_17_read.py with stubs
- [X] T133 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_18_set.py with stubs
- [X] T134 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_19_tcommit.py with stubs
- [X] T135 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_20_trestart.py with stubs
- [X] T135a [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_ksubscripts.py with stubs (shares §8.2.20 numbering with TRESTART)
- [X] T136 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_21_trollback.py with stubs (nested rollback)
- [X] T136a [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_kvalue.py with stubs (shares §8.2.21 numbering with TROLLBACK)
- [X] T137 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_22_tstart.py with stubs ($TLEVEL behavior)
- [X] T138 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_23_use.py with stubs
- [X] T139 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_24_view.py with skip (implementation-defined)
- [X] T140 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_25_write.py with stubs
- [X] T141 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py with stubs
- [X] T141a [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_27_zcommand.py with stubs (Z-commands)
- [X] T142 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_3_device_params.py with stubs
- [X] T143 [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_event_processing.py with skip (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER - out-of-scope per FR-055)
- [X] T143a [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_then_command.py with skip (THEN §8.2.32 - out-of-scope per FR-055)
- [X] T143b [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_assign.py with skip (out-of-scope per FR-055: ASSIGN command)
- [X] T143c [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_28_rload.py with skip (out-of-scope per FR-055: RLOAD command)
- [X] T143d [P] [US7] Create tests/unit/codegen/s8_commands/test_s8_2_29_rsave.py with skip (out-of-scope per FR-055: RSAVE command)

### §9 Character Set (Codegen)

- [X] T144 [P] [US7] Create tests/unit/codegen/s9_charset/test_s9_1_definitions.py with stubs

**Checkpoint**: All codegen-level spec sections have stub files

---

## Phase 7: User Story 5 - YottaDB Z-Command Stubs (Priority: P2)

**Goal**: Create stub test files for implemented YottaDB Z-commands

**Independent Test**: `uv run pytest tests/unit/parser/extensions/ydb/ --collect-only` shows Z-commands covered

### Z-Command Parser Stubs

- [X] T145 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zbreak.py with stubs
- [X] T146 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zcompile.py with stubs
- [X] T147 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zcontinue.py with stubs
- [X] T148 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zgoto.py with stubs
- [X] T149 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zlink.py with stubs
- [X] T150 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zmessage.py with stubs
- [X] T151 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zprint.py with stubs
- [X] T152 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zshow.py with stubs
- [X] T153 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zstep.py with stubs
- [X] T154 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zsystem.py with stubs
- [X] T155 [P] [US5] Create tests/unit/parser/extensions/ydb/test_zwrite.py with stubs
- [X] T155a [P] [US5] Create tests/unit/parser/extensions/ydb/test_zhelp.py with stubs
- [X] T155b [P] [US5] Create tests/unit/parser/extensions/ydb/test_zkill.py with stubs (ZKILL, ZWITHDRAW)
- [X] T155c [P] [US5] Create tests/unit/parser/extensions/ydb/test_zhalt.py with stubs
- [X] T155d [P] [US5] Create tests/unit/parser/extensions/ydb/test_zallocate.py with stubs (ZALLOCATE, ZDEALLOCATE)
- [X] T155e [P] [US5] Create tests/unit/parser/extensions/ydb/test_ztrigger.py with stubs
- [X] T155f [P] [US5] Create tests/unit/parser/extensions/ydb/test_zedit.py with stubs

### Z-Command ASG Stubs

- [X] T156 [P] [US5] Create tests/unit/asg/extensions/ydb/test_zbreak.py with stubs
- [X] T157 [P] [US5] Create tests/unit/asg/extensions/ydb/test_zgoto.py with stubs (ZGotoType classification)
- [X] T158 [P] [US5] Create tests/unit/asg/extensions/ydb/test_zlink.py with stubs
- [X] T159 [P] [US5] Create tests/unit/asg/extensions/ydb/test_zwrite.py with stubs
- [X] T159a [P] [US5] Create tests/unit/asg/extensions/ydb/test_zkill.py with stubs (ZKILL, ZWITHDRAW)
- [X] T159b [P] [US5] Create tests/unit/asg/extensions/ydb/test_zhalt.py with stubs
- [X] T159c [P] [US5] Create tests/unit/asg/extensions/ydb/test_zallocate.py with stubs (ZALLOCATE, ZDEALLOCATE)
- [X] T159d [P] [US5] Create tests/unit/asg/extensions/ydb/test_ztrigger.py with stubs
- [X] T159e [P] [US5] Create tests/unit/asg/extensions/ydb/test_zedit.py with stubs
- [X] T159f [P] [US5] Create tests/unit/asg/extensions/ydb/test_zhelp.py with stubs

### Z-Command Codegen Stubs

- [X] T160 [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zbreak.py with stubs
- [X] T161 [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zgoto.py with stubs
- [X] T162 [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zlink.py with stubs
- [X] T163 [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zsystem.py with stubs
- [X] T164 [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zwrite.py with stubs
- [X] T164a [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zhelp.py with stubs
- [X] T164e [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zkill.py with stubs (ZKILL, ZWITHDRAW)
- [X] T164f [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zhalt.py with stubs
- [X] T164g [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zallocate.py with stubs (ZALLOCATE, ZDEALLOCATE)
- [X] T164h [P] [US5] Create tests/unit/codegen/extensions/ydb/test_ztrigger.py with stubs
- [X] T164i [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zedit.py with stubs
- [X] T164j [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zcompile.py with stubs
- [X] T164k [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zcontinue.py with stubs
- [X] T164l [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zmessage.py with stubs
- [X] T164m [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zprint.py with stubs
- [X] T164n [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zshow.py with stubs
- [X] T164o [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zstep.py with stubs

**Checkpoint**: All implemented Z-commands have parser/ASG/codegen stub files

### Z-Function Parser Stubs (YottaDB implementation-defined $Z... functions)

- [X] T164b [P] [US5] Create tests/unit/parser/extensions/ydb/test_zfunctions.py with skip markers (per FR-017: implementation-defined) for Z-functions: $ZASCII, $ZBITAND, $ZBITCOUNT, $ZBITFIND, $ZBITGET, $ZBITNOT, $ZBITOR, $ZBITSET, $ZBITSTR, $ZBITXOR, $ZCHAR, $ZCOLLATE, $ZCONVERT, $ZDATA, $ZDATE, $ZDIRECTORY, $ZEDIT, $ZEXTRACT, $ZFF, $ZFIND, $ZGETJPI, $ZINCR, $ZIO, $ZJOB, $ZJOBEXAM, $ZLENGTH, $ZLEVEL, $ZMESSAGE, $ZMODE, $ZNAME, $ZNEXT, $ZORDER, $ZPARSE, $ZPEEK, $ZPID, $ZPIECE, $ZPOSITION, $ZPREVIOUS, $ZPREFERREDLANG, $ZPRINT, $ZQGBLMOD, $ZQSUB, $ZSEARCH, $ZSOCKET, $ZSTATUS, $ZSUB, $ZSUFFIX, $ZSUPERMASK, $ZSYSLOG, $ZTRAP, $ZTRANSLATE, $ZTRIGGER, $ZTRNLNM, $ZVERSION, $ZWIDTH, $ZWRITE

### Z-Function ASG Stubs

- [X] T164c [P] [US5] Create tests/unit/asg/extensions/ydb/test_zfunctions.py with skip markers for Z-functions (ASG analysis and resolution)

### Z-Function Codegen Stubs

- [X] T164d [P] [US5] Create tests/unit/codegen/extensions/ydb/test_zfunctions.py with skip markers for Z-functions (Python codegen and execution)

**Checkpoint**: All implemented Z-commands AND Z-functions have parser/ASG/codegen stub files

---

## Phase 8: User Story 6 - Migrate Existing Tests (Priority: P2)

**Goal**: Move existing test content from flat structure to spec-aligned structure, aligning test names with naming conventions and merging into stub files where they exist

**⚠️ DEPENDENCY**: Phase 8 cannot start until Phases 4-7 complete (stub files must exist before migration merges into them)

**Independent Test**: `uv run pytest tests/unit/ --collect-only | tail -1` shows count ≥ 1280 (current baseline)

### Pre-Migration Setup

- [X] T165 [US6] Capture pre-migration test baseline: `uv run pytest tests/unit/ --collect-only -q | tail -1` → record count in research.md
- [X] T165a [US6] Verify test naming convention exists at specs/002-spec-unit-test-organization/contracts/test-naming.md (created in T013a)
- [X] T165b [US6] Enumerate ALL test files: `find tests/unit -name 'test_*.py' -type f | sort` and verify each file has a corresponding migration task in Phase 8. Document any unmapped files in research.md "### Migration File Inventory" section

### Migration Tasks - Parser Tests (to parser/)

#### From test_command_grammar.py (parser-level grammar tests)

- [X] T166 [US6] Migrate test_command_grammar.py TestSetCommand → parser/s8_commands/test_s8_2_18_set.py, merge into stubs, add @pytest.mark.parser
- [X] T166a [US6] Migrate test_command_grammar.py TestWriteCommand → parser/s8_commands/test_s8_2_27_write.py
- [X] T166b [US6] Migrate test_command_grammar.py TestReadCommand, TestReadTargets → parser/s8_commands/test_s8_2_17_read.py
- [X] T166c [US6] Migrate test_command_grammar.py TestIfElseCommands → parser/s8_commands/test_s8_2_09_if.py and test_s8_2_04_else.py
- [X] T166d [US6] Migrate test_command_grammar.py TestForCommand → parser/s8_commands/test_s8_2_05_for.py
- [X] T166e [US6] Migrate test_command_grammar.py TestGotoCommand → parser/s8_commands/test_s8_2_06_goto.py
- [X] T166f [US6] Migrate test_command_grammar.py TestDoCommand, TestDoExternalCommand → parser/s8_commands/test_s8_2_03_do.py
- [X] T166g [US6] Migrate test_command_grammar.py TestQuitCommand, TestQuitFollowedBySet, TestQuitFollowedByTransaction → parser/s8_commands/test_s8_2_16_quit.py
- [X] T166h [US6] Migrate test_command_grammar.py TestNewKillCommands → parser/s8_commands/test_s8_2_14_new.py and test_s8_2_11_kill.py
- [X] T166i1 [US6] Migrate test_command_grammar.py TestOtherCommands (test_hang*, test_halt, test_break, test_xecute) → parser/s8_commands/test_s8_2_07_halt.py, test_s8_2_08_hang.py, test_s8_2_01_break.py, test_s8_2_28_xecute.py
- [X] T166i2 [US6] Migrate test_command_grammar.py TestOtherCommands (test_lock*, test_merge*) → parser/s8_commands/test_s8_2_12_lock.py, test_s8_2_13_merge.py
- [X] T166j [US6] Migrate test_command_grammar.py TestPostconditions, TestArgumentPostconditions → parser/s8_commands/test_s8_1_general_rules.py
- [X] T166k [US6] Migrate test_command_grammar.py TestIndirection, TestByRefIndirection → parser/s7_expressions/test_s7_3_indirection.py
- [X] T166l1 [US6] Migrate test_command_grammar.py TestZShowCommand → parser/extensions/ydb/test_zshow.py
- [X] T166l2 [US6] Migrate test_command_grammar.py TestZWriteCommand, TestZWriteArgumentless → parser/extensions/ydb/test_zwrite.py
- [X] T166l3 [US6] Migrate test_command_grammar.py TestZBreakCommand, TestZBreakLabelOffset → parser/extensions/ydb/test_zbreak.py
- [X] T166l4 [US6] Migrate test_command_grammar.py TestZGotoCommand → parser/extensions/ydb/test_zgoto.py
- [X] T166l5 [US6] Migrate test_command_grammar.py TestZLoadCommand, TestZLinkCommand → parser/extensions/ydb/test_zlink.py
- [X] T166l6 [US6] Migrate test_command_grammar.py TestZKillCommand, TestZWithdrawCommand → parser/extensions/ydb/test_zkill.py (new)
- [X] T166l7 [US6] Migrate test_command_grammar.py TestZHaltCommand → parser/extensions/ydb/test_zhalt.py (new)
- [X] T166l8 [US6] Migrate test_command_grammar.py TestZAllocateCommand, TestZDeallocateCommand → parser/extensions/ydb/test_zallocate.py (new)
- [X] T166l9 [US6] Migrate test_command_grammar.py TestZPrintCommand → parser/extensions/ydb/test_zprint.py
- [X] T166l10 [US6] Migrate test_command_grammar.py TestZSystemCommand → parser/extensions/ydb/test_zsystem.py
- [X] T166l11 [US6] Migrate test_command_grammar.py TestZMessageCommand → parser/extensions/ydb/test_zmessage.py
- [X] T166l12 [US6] Migrate test_command_grammar.py TestZTriggerCommand → parser/extensions/ydb/test_ztrigger.py (new)
- [X] T166l13 [US6] Migrate test_command_grammar.py TestZCompileCommand → parser/extensions/ydb/test_zcompile.py
- [X] T166l14 [US6] Migrate test_command_grammar.py TestZContinueCommand → parser/extensions/ydb/test_zcontinue.py
- [X] T166l15 [US6] Migrate test_command_grammar.py TestZEditCommand → parser/extensions/ydb/test_zedit.py (new)
- [X] T166l16 [US6] Migrate test_command_grammar.py TestZStepCommand → parser/extensions/ydb/test_zstep.py
- [X] T166m [US6] Migrate test_command_grammar.py TestTextFunctionGrammar → parser/s7_expressions/test_s7_1_5_intrinsic_functions.py ($TEXT)
- [X] T166n [US6] Migrate test_command_grammar.py TestExternalFunction → parser/s7_expressions/test_s7_1_6_extrinsic_functions.py
- [X] T166o [US6] Migrate test_command_grammar.py TestPartOEdgeCases, TestUnknownCommand, TestFunctionArgsEmpty → tests/unit/meta/test_parser_edge_cases.py (new)

#### From test_expression_grammar.py (expression-level grammar tests)

- [X] T167 [US6] Migrate test_expression_grammar.py TestNumericLiterals, TestStringLiterals → parser/s7_expressions/test_s7_1_4_literals.py
- [X] T167a [US6] Migrate test_expression_grammar.py TestLocalVariables, TestGlobalVariables → parser/s7_expressions/test_s7_1_2_variables.py
- [X] T167b [US6] Migrate test_expression_grammar.py TestBinaryOperators, TestUnaryOperators → parser/s7_expressions/test_s7_2_operators.py
- [X] T167c [US6] Migrate test_expression_grammar.py TestIntrinsicFunctions → parser/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [X] T167d [US6] Migrate test_expression_grammar.py TestSpecialVariables → parser/s7_expressions/test_s7_1_7_special_variables.py
- [X] T167e [US6] Migrate test_expression_grammar.py TestSelectFunction → parser/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [X] T167f [US6] Migrate test_expression_grammar.py TestIndirection → parser/s7_expressions/test_s7_3_indirection.py
- [X] T167g [US6] Migrate test_expression_grammar.py TestExtrinsicFunctions → parser/s7_expressions/test_s7_1_6_extrinsic_functions.py
- [X] T167h [US6] Migrate test_expression_grammar.py TestExternalFunctions → parser/s7_expressions/test_s7_1_6_extrinsic_functions.py

#### From test_grammar.py (full-routine grammar acceptance tests)

- [X] T168a [US6] Migrate test_grammar.py TestSetStatementGrammar → parser/s8_commands/test_s8_2_18_set.py
- [X] T168b [US6] Migrate test_grammar.py TestWriteStatementGrammar → parser/s8_commands/test_s8_2_27_write.py
- [X] T168c [US6] Migrate test_grammar.py TestBoundedForGrammar, TestStringListForGrammar, TestOpenEndedForGrammar, TestMixedForGrammar, TestArgumentlessForGrammar → parser/s8_commands/test_s8_2_05_for.py
- [X] T168d [US6] Migrate test_grammar.py TestSimpleIfGrammar → parser/s8_commands/test_s8_2_09_if.py
- [X] T168e [US6] Migrate test_grammar.py TestPatternMatchGrammar, TestIndirectPatternMatchGrammar → parser/s7_expressions/test_s7_2_5_pattern_match.py
- [X] T168f [US6] Migrate test_grammar.py TestIntrinsicFunctionGrammar → parser/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [X] T168g [US6] Migrate test_grammar.py TestSpecialVariableGrammar, TestIORefSpecialVariableGrammar → parser/s7_expressions/test_s7_1_7_special_variables.py
- [X] T168h [US6] Migrate test_grammar.py TestIndirectionGrammar, TestDoIndirectionGrammar → parser/s7_expressions/test_s7_3_indirection.py
- [X] T168i [US6] Migrate test_grammar.py TestReadFormatControlGrammar → parser/s8_commands/test_s8_2_17_read.py
- [X] T168j [US6] Migrate test_grammar.py TestOpenDeviceParametersGrammar, TestOpenMnemonicGrammar → parser/s8_commands/test_s8_2_15_open.py
- [X] T168k [US6] Migrate test_grammar.py TestNotContainsOperatorGrammar → parser/s7_expressions/test_s7_2_operators.py
- [X] T168l [US6] Migrate test_grammar.py TestSetSpecialVariableGrammar → parser/s8_commands/test_s8_2_18_set.py
- [X] T168m [US6] Migrate test_grammar.py TestTStartEmptyRestartGrammar → parser/s8_commands/test_s8_2_24_tstart.py
- [X] T168n [US6] Migrate test_grammar.py TestStructuredSystemVariableGrammar → parser/s7_expressions/test_s7_1_3_ssvns.py

#### From test_line_parser.py (line-level parsing)

- [X] T168o [US6] Migrate test_line_parser.py TestParseLineContent, TestParseCommand, TestGetLineComment → tests/unit/meta/test_line_parser.py (new)
- [X] T168p [US6] Migrate test_line_parser.py TestParseCommandsFromLine → tests/unit/meta/test_line_parser.py
- [X] T168q [US6] Migrate test_line_parser.py TestParseExpression → parser/s7_expressions/test_s7_1_1_values.py
- [X] T168r [US6] Migrate test_line_parser.py TestParseSetCommand → parser/s8_commands/test_s8_2_18_set.py
- [X] T168s [US6] Migrate test_line_parser.py TestParseWriteCommand → parser/s8_commands/test_s8_2_27_write.py
- [X] T168t [US6] Migrate test_line_parser.py TestParseQuitCommand → parser/s8_commands/test_s8_2_16_quit.py
- [X] T168u [US6] Migrate test_line_parser.py TestParseIfCommand, TestArgumentlessIfFollowedByCommand → parser/s8_commands/test_s8_2_09_if.py
- [X] T168v [US6] Migrate test_line_parser.py TestParseForCommand, TestParseForCommandToAsg, TestExtractForCommands, TestClassifyForFromTextx, TestDetectQuitAfterFor → parser/s8_commands/test_s8_2_05_for.py
- [X] T168w [US6] Migrate test_line_parser.py TestExtractFunctionErrorPaths → tests/unit/meta/test_line_parser.py

#### From other parser test files

- [X] T168x [US6] Migrate test_special_constructs.py TestIntrinsicFunctions → parser/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [X] T168y [US6] Migrate test_special_constructs.py TestPatternMatch → parser/s7_expressions/test_s7_2_5_pattern_match.py
- [X] T168z [US6] Migrate test_special_constructs.py TestIndirection → parser/s7_expressions/test_s7_3_indirection.py
- [X] T168aa [US6] Migrate test_special_constructs.py TestExtrinsicFunctions → parser/s7_expressions/test_s7_1_6_extrinsic_functions.py
- [X] T168ab [US6] Migrate test_special_constructs.py TestSpecialVariables → parser/s7_expressions/test_s7_1_7_special_variables.py
- [X] T168ac [US6] Migrate test_special_constructs.py TestComplexExpressions → parser/s7_expressions/test_s7_2_operators.py
- [X] T168ad [US6] Migrate test_if_comma_conditions.py → parser/s8_commands/test_s8_2_09_if.py
- [X] T168ae [US6] Migrate test_quit_then_command.py TestQuitThenCommand → parser/s8_commands/test_s8_2_16_quit.py
- [X] T168af [US6] Migrate test_quit_then_command.py TestV1CALL1Line3 → parser/s8_commands/test_s8_2_16_quit.py
- [X] T169 [US6] Migrate test_pattern_compiler.py → parser/s7_expressions/test_s7_2_5_pattern_match.py

#### From test_io_commands.py (I/O command parser tests)

- [X] T169a1 [US6] Migrate test_io_commands.py TestMergeCommand → parser/s8_commands/test_s8_2_13_merge.py
- [X] T169a2 [US6] Migrate test_io_commands.py TestViewCommand → parser/s8_commands/test_s8_2_26_view.py
- [X] T169a3 [US6] Migrate test_io_commands.py TestLockCommand → parser/s8_commands/test_s8_2_12_lock.py
- [X] T169a4 [US6] Migrate test_io_commands.py TestJobIndirection, TestJobTimeoutAndProcessParameters → parser/s8_commands/test_s8_2_10_job.py

#### From test_multi_arg_commands.py (multi-argument parser tests)

- [X] T169b1 [US6] Migrate test_multi_arg_commands.py TestMultiMerge → parser/s8_commands/test_s8_2_13_merge.py
- [X] T169b2 [US6] Migrate test_multi_arg_commands.py TestMultiOpen → parser/s8_commands/test_s8_2_15_open.py
- [X] T169b3 [US6] Migrate test_multi_arg_commands.py TestMultiClose, TestCloseUseWithParams → parser/s8_commands/test_s8_2_02_close.py
- [X] T169b4 [US6] Migrate test_multi_arg_commands.py TestMultiUse → parser/s8_commands/test_s8_2_25_use.py
- [X] T169b5 [US6] Migrate test_multi_arg_commands.py TestMultiJob → parser/s8_commands/test_s8_2_10_job.py
- [X] T169b6 [US6] Migrate test_multi_arg_commands.py TestIndirectionSubscriptAnalysis → asg/s7_expressions/test_s7_3_indirection.py

#### From test_parser.py (core MUMPSParser class tests) - CRITICAL

- [X] T169c1 [US6] Migrate test_parser.py TestMUMPSParserInit → tests/unit/meta/test_parser_api.py (new)
- [X] T169c2 [US6] Migrate test_parser.py TestMUMPSParserParse → tests/unit/meta/test_parser_api.py
- [X] T169c3 [US6] Migrate test_parser.py TestMUMPSParserParseFile → tests/unit/meta/test_parser_api.py
- [X] T169c4 [US6] Migrate test_parser.py TestMUMPSParserMUGJ → tests/unit/meta/test_parser_api.py
- [X] T169c5 [US6] Migrate test_parser.py TestMUMPSParserGrammarIntegration → tests/unit/meta/test_parser_api.py
- [X] T169c6 [US6] Migrate test_parser.py TestMUMPSParserClassifyPatterns → tests/unit/analysis/test_for_classifier.py
- [X] T169c7 [US6] Migrate test_parser.py TestParserPerformance → tests/unit/meta/test_parser_performance.py (new, @pytest.mark.slow)
- [X] T169c8 [US6] Migrate test_parser.py TestParserErrorHandling → tests/unit/meta/test_parser_errors.py (new)
- [X] T169c9 [US6] Migrate test_parser.py TestParseErrorCollection → tests/unit/meta/test_parser_errors.py
- [X] T169c10 [US6] Migrate test_parser.py TestTransactionCommands → parser/s8_commands/test_s8_2_19_tcommit.py, test_s8_2_24_tstart.py, test_s8_2_23_trollback.py
- [X] T169c11 [US6] Migrate test_parser.py TestASGSerialization → tests/unit/meta/test_asg_serialization.py (new)
- [X] T169c12 [US6] Migrate test_parser.py TestControlFlowBodyPopulation → asg/s8_commands/test_s8_2_05_for.py (FOR body), asg/s8_commands/test_s8_2_09_if.py (IF body)
- [X] T169c13 [US6] Migrate test_parser.py TestPhase74Fixes → tests/unit/meta/test_regression_fixes.py (new)

### Migration Tasks - ASG Tests (to asg/)

#### From test_semantic_analyzer.py

- [X] T170 [US6] Migrate test_semantic_analyzer.py TestAnalyzeExpression → asg/s7_expressions/test_s7_1_1_values.py and test_s7_1_2_variables.py
- [X] T170a [US6] Migrate test_semantic_analyzer.py TestPatternMatchASG, TestPatternMatchCompilation → asg/s7_expressions/test_s7_2_5_pattern_match.py
- [X] T170b [US6] Migrate test_semantic_analyzer.py TestIntrinsicFunctionASG → asg/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [X] T170c [US6] Migrate test_semantic_analyzer.py TestExtrinsicFunctionASG → asg/s7_expressions/test_s7_1_6_extrinsic_functions.py
- [X] T170d [US6] Migrate test_semantic_analyzer.py TestIndirectionASG, TestIndirectionClassification → asg/s7_expressions/test_s7_3_indirection.py
- [X] T170e [US6] Migrate test_semantic_analyzer.py TestSpecialVariableASG → asg/s7_expressions/test_s7_1_7_special_variables.py
- [X] T170f [US6] Migrate test_semantic_analyzer.py TestFormatControlASG → asg/s8_commands/test_s8_2_27_write.py
- [X] T170g [US6] Migrate test_semantic_analyzer.py TestXecuteConstantDetection → asg/s8_commands/test_s8_2_28_xecute.py
- [X] T170h [US6] Migrate test_semantic_analyzer.py TestUnwrapExpression → tests/unit/meta/test_semantic_analyzer_internals.py (new)
- [X] T170i [US6] Migrate test_semantic_analyzer.py TestReadFixedLength → asg/s8_commands/test_s8_2_17_read.py
- [X] T170j [US6] Migrate test_semantic_analyzer.py TestMActualParameterAnalysis → asg/s8_commands/test_s8_2_03_do.py
- [X] T170k [US6] Migrate test_semantic_analyzer.py TestZGotoLabelRefAnalysis → asg/extensions/ydb/test_zgoto.py

#### From test_command_analysis.py

- [X] T171 [US6] Migrate test_command_analysis.py TestSetStatementAnalysis → asg/s8_commands/test_s8_2_18_set.py
- [X] T171a [US6] Migrate test_command_analysis.py TestWriteStatementAnalysis → asg/s8_commands/test_s8_2_27_write.py
- [X] T171b [US6] Migrate test_command_analysis.py TestQuitStatementAnalysis → asg/s8_commands/test_s8_2_16_quit.py
- [X] T171c [US6] Migrate test_command_analysis.py TestIfStatementAnalysis → asg/s8_commands/test_s8_2_09_if.py
- [X] T171d [US6] Migrate test_command_analysis.py TestForStatementAnalysis → asg/s8_commands/test_s8_2_05_for.py
- [X] T171e [US6] Migrate test_command_analysis.py TestGotoStatementAnalysis → asg/s8_commands/test_s8_2_06_goto.py
- [X] T171f [US6] Migrate test_command_analysis.py TestDoStatementAnalysis → asg/s8_commands/test_s8_2_03_do.py
- [X] T171g [US6] Migrate test_command_analysis.py TestNewStatementAnalysis → asg/s8_commands/test_s8_2_14_new.py
- [X] T171h [US6] Migrate test_command_analysis.py TestKillStatementAnalysis → asg/s8_commands/test_s8_2_11_kill.py
- [X] T171i1 [US6] Migrate test_command_analysis.py TestOtherStatementAnalysis (test_hang, test_halt*) → asg/s8_commands/test_s8_2_07_halt.py, test_s8_2_08_hang.py
- [X] T171i2 [US6] Migrate test_command_analysis.py TestOtherStatementAnalysis (test_break) → asg/s8_commands/test_s8_2_01_break.py
- [X] T171i3 [US6] Migrate test_command_analysis.py TestOtherStatementAnalysis (test_zallocate, test_zdeallocate*) → asg/extensions/ydb/test_zallocate.py
- [X] T171j [US6] Migrate test_command_analysis.py TestMultipleCommandsAnalysis → tests/unit/meta/test_command_analysis_integration.py (new)
- [X] T171k [US6] Migrate test_command_analysis.py TestExpressionAnalysis → asg/s7_expressions/test_s7_2_operators.py

#### From other ASG test files

- [X] T172 [US6] Migrate test_complex_expressions_analysis.py → asg/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [X] T172a [US6] Migrate test_text_function_analysis.py → asg/s7_expressions/test_s7_1_5_intrinsic_functions.py ($TEXT)
- [X] T172b [US6] Migrate test_external_calls.py → asg/s8_commands/test_s8_2_03_do.py (external routine calls)
- [X] T172c1 [US6] Migrate test_io_commands.py (ASG-level MERGE tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_13_merge.py
- [X] T172c2 [US6] Migrate test_io_commands.py (ASG-level VIEW tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_26_view.py
- [X] T172c3 [US6] Migrate test_io_commands.py (ASG-level LOCK tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_12_lock.py
- [X] T172c4 [US6] Migrate test_io_commands.py (ASG-level JOB tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_10_job.py
- [X] T172d1 [US6] Migrate test_multi_arg_commands.py (ASG-level multi-MERGE tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_13_merge.py
- [X] T172d2 [US6] Migrate test_multi_arg_commands.py (ASG-level multi-OPEN tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_15_open.py
- [X] T172d3 [US6] Migrate test_multi_arg_commands.py (ASG-level multi-CLOSE tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_02_close.py
- [X] T172d4 [US6] Migrate test_multi_arg_commands.py (ASG-level multi-USE tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_25_use.py
- [X] T172d5 [US6] Migrate test_multi_arg_commands.py (ASG-level multi-JOB tests: tests importing analyze_* or asserting M*Statement types) → asg/s8_commands/test_s8_2_10_job.py
- [X] T173 [US6] Migrate test_variables.py TestScopeVariables, TestFormalParameters, TestScopeStrategy → asg/s8_commands/test_s8_2_14_new.py
- [X] T173a [US6] Migrate test_variables.py TestExtractExpressionVariables, TestExtractStatementVariables, TestAnalyzeVariables, TestGetDefUseChains, TestComputeTransitiveInputs → tests/unit/analysis/test_variable_analysis.py
- [X] T173b [US6] Migrate test_variables.py TestFunctionSignature, TestQuitAnalysis, TestParameterBinding → tests/unit/analysis/test_variable_analysis.py
- [X] T173c [US6] Migrate test_variables.py TestVariableInfo, TestEdgeCases → tests/unit/analysis/test_variable_analysis.py
- [X] T174 [US6] Migrate test_unreachable_code.py TestUnreachableCodeDetection, TestHasExplicitExit, TestMUGJUnreachableCodeExamples → asg/s6_routine/test_s6_3_execution.py

### Migration Tasks - Analysis Tests (to analysis/)

- [X] T175 [US6] Migrate test_classifier.py → tests/unit/analysis/test_for_classifier.py
- [X] T175a [US6] Migrate test_goto_for_analysis.py TestClassifyGotos → tests/unit/analysis/test_goto_classifier.py
- [X] T175b [US6] Migrate test_goto_for_analysis.py TestAnalyzeForLoops → tests/unit/analysis/test_for_analysis.py
- [X] T175c [US6] Migrate test_resolver.py TestResolveReferences, TestGetUnresolvedCalls, TestGetExternalCalls, TestCallTypePopulation, TestGlobalRefsCollection → tests/unit/analysis/test_resolver.py

### Migration Tasks - Cross-Cutting Tests (to cross_cutting/)

- [X] T176 [US6] Migrate test_indirection_detection.py → tests/unit/cross_cutting/test_indirection.py (merge into stubs from T183)

### Migration Tasks - Meta Tests (to meta/)

- [X] T177 [US6] Migrate test_textx_classes.py TestTextXCustomClasses, TestSelectFunctionCustomClass, TestClassRegistry → tests/unit/meta/test_textx_classes.py
- [X] T177a [US6] Migrate test_parse_result_tracking.py TestParseResult, TestSuiteParseResults, TestParseSuite → tests/unit/meta/test_parse_result_tracking.py
- [X] T177b [US6] Migrate test_setup.py TestPackageSetup, TestMUGJFixtures, TestASGModuleExports, TestASGSubComponentTypes, TestMIndirectionTyping → tests/unit/meta/test_setup.py
- [X] T177c [US6] Migrate test_asg_type_annotations.py → tests/unit/meta/test_asg_type_annotations.py

### Test Naming and Marker Alignment

- [ ] T177d [US6] For each migrated file: rename test functions to follow `test_{command}_{variant}_{detail}` pattern per contracts/test-naming.md
- [ ] T177e [US6] For each migrated file: add spec section reference to test class/function docstrings per FR-004
- [ ] T177f [US6] For each migrated parser test: ensure @pytest.mark.parser marker present
- [ ] T177g [US6] For each migrated ASG test: ensure @pytest.mark.asg marker present
- [ ] T177h [US6] For each migrated test: if stub file exists, merge implementation into stub (remove @pytest.mark.stub and @pytest.mark.xfail per FR-040)

### Validation Tasks

- [ ] T177i [US6] Run marker validation: `uv run pytest --collect-only 2>&1 | grep -c "missing category marker"` should be 0
- [ ] T177j [US6] Verify test count: `uv run pytest tests/unit/ --collect-only | tail -1` shows ≥ baseline from T165
- [ ] T177j2 [US6] Verify no unaccounted removals: diff pre/post migration test function names, document any removed tests with rationale
- [ ] T177k [US6] Verify all tests pass: `uv run pytest tests/unit/` exit code 0
- [ ] T177k2 [US6] **CI CHECKPOINT**: Commit migration changes, push to branch, verify CI pipeline passes before archiving (FR-028 compliance)
- [ ] T177m [US6] Verify no stub/xfail markers remain on implemented tests per FR-040/FR-057: `uv run pytest tests/unit/ -v 2>&1 | grep -c "PASSED.*stub"` should be 0 (MUST pass before archiving)
- [ ] T177l [US6] Archive original flat test files to tests/unit/_archived/ (do not delete yet) — depends on T177k2 and T177m passing

**Checkpoint**: All existing tests migrated, markers applied, names aligned, count verified ≥ baseline

---

## Phase 9: User Story 3 - Coverage Matrix (Priority: P1)

**Goal**: Create documentation tracking coverage status for every spec section

**Independent Test**: docs/coverage-matrix.md exists and lists all §5-§9 sections with status

### Coverage Documentation

- [ ] T178 [US3] Create file docs/coverage-matrix.md with §5-§9 section listing (FR-045 requirement)
- [ ] T179 [US3] Add status column (stub/implemented/skip) for each section
- [ ] T180 [US3] Add test file path column linking to actual test files
- [ ] T181 [US3] Mark out-of-scope sections per FR-055 with skip reason: §5 Metalanguage (informative), §6.3.4 Event Processing (ABLOCK/AUNBLOCK/ASTART/ASTOP/ESTART/ESTOP/ETRIGGER), §6.4 Embedded Programs, THEN command, ASSIGN command, RLOAD/RSAVE commands, ^$LIBRARY/^$EVENT SSVNs
- [ ] T182 [US3] Add summary counts: total sections, implemented, stub, skip

**Checkpoint**: Coverage matrix complete and accurate

---

## Phase 10: Cross-Cutting Concern Tests (Priority: P1)

**Goal**: Create dedicated tests for language features that span multiple commands

**Independent Test**: `uv run pytest tests/unit/cross_cutting/ -v` shows all cross-cutting features covered

### Cross-Cutting Stubs

- [ ] T183 [P] Create tests/unit/cross_cutting/test_indirection.py with stubs (name, argument, pattern indirection) - Note: T176 migrates existing content INTO this file
- [ ] T184 [P] Create tests/unit/cross_cutting/test_postconditions.py with stubs (command-level vs argument-level)
- [ ] T185 [P] Create tests/unit/cross_cutting/test_timeouts.py with stubs (OPEN, READ, JOB, LOCK timeout syntax)
- [ ] T186 [P] Create tests/unit/cross_cutting/test_naked_references.py with stubs (naked indicator state)
- [ ] T187 [P] Create tests/unit/cross_cutting/test_language_semantics.py with stubs ($TEST, L-to-R eval, Exclusive NEW, transaction nesting)

**Checkpoint**: All FR-046-051 language semantic requirements have stub tests

---

## Phase 11: User Story 4 - Backward Compatibility (Priority: P2)

**Goal**: Ensure parser handles pre-1995 syntax variations from legacy MUMPS code

**Independent Test**: VistA codebase parses without syntax errors due to standard version differences (SC-012)

### Research & Documentation

- [ ] T188 [US4] Research 1977/1984/1990 spec differences vs 1995: append new "## Backward Compatibility Research" section to research.md with markdown table (columns: Feature, 1977, 1984, 1990, 1995, Breaking?). Consult mumps-reference files: `1977__*.md`, `1984__*.md`, `1990__*.md`, `1995__*.md` for version-specific syntax
- [ ] T189 [US4] Identify pre-1995 syntax in VistA-M/ and YDBTest functional suites (`tests/functional/*_inref/`, `tests/functional/mugj/`): append grep results with file:line to research.md "### Legacy Patterns Found" subsection
- [ ] T190 [US4] Extract concrete syntax diffs from mumps-reference/: append changed BNF productions to research.md "### BNF Changes" subsection. Key files: compare `1977__a107*.md` vs `1995__a107*.md` for function/operator changes
- [ ] T191 [US4] Document identified backward-compatible syntax in docs/testing.md "Backward Compatibility" section. For deprecated constructs (e.g., $NEXT), document: (a) the deprecated syntax, (b) the modern replacement, (c) whether M2PY emits a Python warning via `warnings.warn()` or silently accepts. If warnings are emitted, use format: `MUMPSDeprecationWarning: $NEXT is deprecated per 1995 spec §7.1.5; use $ORDER instead`

### Tests for Identified Differences

- [ ] T192 [P] [US4] Create tests/unit/parser/legacy/test_pre1995_syntax.py with @pytest.mark.pre1995 marker
- [ ] T193 [P] [US4] Create tests/unit/asg/legacy/test_pre1995_semantics.py with stubs
- [ ] T194 [P] [US4] Create tests/unit/codegen/legacy/test_pre1995_behavior.py with stubs
- [ ] T195 [US4] Add test cases for each identified syntax difference (FR-022)
- [ ] T196 [US4] Verify VistA parsing: create utils/verify_vista_parse.py script that imports m2py.parse and parses VistA-M/sample.m; run via `uv run python utils/verify_vista_parse.py`
- [ ] T197 [US4] Update coverage-matrix.md with backward-compat section status

**Checkpoint**: All identified pre-1995 syntax variations have test coverage

---

## Phase 12: Polish & Documentation

**Purpose**: Update documentation to reflect new test organization

- [ ] T198 Update docs/testing.md with new spec-aligned test structure description
- [ ] T199 [P] Add three-level testing explanation (parser/asg/codegen) to docs/testing.md
- [ ] T200 [P] Add stub/xfail workflow documentation to docs/testing.md
- [ ] T201 [P] Add marker usage table and common pytest commands to docs/testing.md
- [ ] T202 Run quickstart.md validation: verify all documented commands work
- [ ] T203 Final verification: `uv run pytest` produces exit code 0 (green CI)
- [ ] T204 Final verification: `uv run pytest -m "not stub"` runs only implemented tests

---

## Phase 13: Library Function Stubs (Priority: P1)

**Goal**: Add parser/ASG/codegen coverage for ANSI M Appendix I library functions (normative)

**Independent Test**: `uv run pytest tests/unit/*/s7_expressions/ -k "library" --collect-only` lists library stub files with correct markers

### Parser Library Functions (US1)

- [ ] T205 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_6_5_library_functions_math.py with stubs (57 MATH library functions listed in Annex I-2)
- [ ] T206 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_6_5_library_functions_string.py with stubs (6 STRING library functions: CRC16, CRC32, CRCCCITT, FORMAT, PRODUCE, REPLACE)
- [ ] T207 [P] [US1] Create tests/unit/parser/s7_expressions/test_s7_1_6_5_library_functions_character.py with stubs (5 CHARACTER library functions: COLLATE, COMPARE, LOWER, PATCODE, UPPER)

### ASG Library Functions (US2)

- [ ] T208 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_6_5_library_functions_math.py with stubs (57 MATH library functions)
- [ ] T209 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_6_5_library_functions_string.py with stubs (6 STRING library functions)
- [ ] T210 [P] [US2] Create tests/unit/asg/s7_expressions/test_s7_1_6_5_library_functions_character.py with stubs (5 CHARACTER library functions)

### Codegen Library Functions (US7)

- [ ] T211 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py with stubs (57 MATH library functions)
- [ ] T212 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py with stubs (6 STRING library functions)
- [ ] T213 [P] [US7] Create tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py with stubs (5 CHARACTER library functions)

### Library Function Validation

- [ ] T214 [US7] Verify library function stub files contain individual test stubs for all 68 functions: `uv run pytest tests/unit/*/s7_expressions/test_s7_1_6_5_library_functions_*.py --collect-only | grep -c "test_"` should be ≥ 68×3=204

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - create directories first
- **Phase 2 (Foundational)**: Depends on Phase 1 - markers must exist before stubs
- **Phase 3 (US8 - Stub Infrastructure)**: Depends on Phase 2 - validate stub pattern works
- **Phase 4-7 (Stub Creation)**: Depends on Phase 3 - bulk stub creation
- **Phase 8 (Migration)**: Depends on Phases 4-7 - stub files must exist before migration merges into them
- **Phase 9-10 (Coverage/Cross-Cutting)**: Can parallel with Phase 8
- **Phase 11 (US4 - Backward Compatibility)**: Can parallel with Phase 8-10 - research-driven
- **Phase 12 (Polish)**: Depends on all previous phases

### Parallel Opportunities

All tasks marked [P] within a phase can run in parallel. Additionally:
- Phases 4-7 (US1, US2, US7, US5) can all run in parallel once Phase 3 completes
- Phase 9 and Phase 10 can run in parallel with Phase 8

---

## Implementation Strategy

### MVP First (Phases 1-4)

1. Complete Setup + Foundational + US8 validation
2. Complete US1 (Parser stubs) - this establishes the full spec section inventory
3. **STOP and VALIDATE**: `uv run pytest tests/unit/parser/ --collect-only` shows all sections
4. CI should be green with all stubs as xfail

### Incremental Delivery

1. Parser stubs → ASG stubs → Codegen stubs (each phase adds a test level)
2. Migration can happen incrementally - one file at a time
3. Coverage matrix tracks progress explicitly

---

## Notes

- Total tasks: ~365 (T001-T214 plus sub-tasks for comprehensive migration mapping, Z-command stubs, and §5/ZHELP/validation tasks)
- **Phase 8 expansion**: Migration tasks now have explicit source-class-to-destination-file mappings (no "appropriate files" ambiguity)
- **Phase 8 dependency**: Cannot start until Phases 4-7 complete (stub files must exist first)
- Total existing tests: baseline captured at T165 (must maintain or exceed)
- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- All stub files must include @pytest.mark.stub and @pytest.mark.xfail
- Out-of-scope features use @pytest.mark.skip(reason="out-of-scope: ...") per FR-016
- Implementation-defined features (VIEW) use @pytest.mark.skip(reason="implementation-defined: ...") per FR-017
- Verify CI stays green after each phase
- Per-symbol granularity: Intrinsic functions (22+$NEXT deprecated), special variables (19), and SSVNs (7 in-scope + 2 out-of-scope) are explicitly enumerated in stub task descriptions
- **Marker policy**: Tests in `analysis/` and `meta/` directories do NOT require `@pytest.mark.parser|asg|codegen` markers—these test internal algorithms and tooling, not spec compliance
- **Migration strategy**: Existing tests are merged INTO stub files (not vice versa) to preserve stub coverage tracking
- **Codegen validation**: Tests MUST reference YDBTest functional suites (`tests/functional/*_inref/`, `tests/functional/mugj/`) or cite MUMPS spec sections
- **New meta/ files**: test_parser_api.py, test_parser_performance.py, test_parser_errors.py, test_asg_serialization.py, test_regression_fixes.py, test_line_parser.py, test_parser_edge_cases.py, test_semantic_analyzer_internals.py, test_command_analysis_integration.py
- **New YDB files**: test_zkill.py, test_zhalt.py, test_zallocate.py, test_ztrigger.py, test_zedit.py, test_zhelp.py
- **New §5 skip files**: test_s5_1_bnf_notation.py in parser/asg/codegen s5_metalanguage directories
