# Tasks: Complete Stub Tests

**Input**: Design documents from `/specs/003-complete-stub-tests/`
**Prerequisites**: plan.md, spec.md, research.md (53 batch definitions)

**Tests**: Tests are the PRIMARY deliverable of this feature - no separate test tasks needed.

**Organization**: Tasks organized by implementation phase (coverage-first strategy from research.md).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: Parser stub tests (Priority 1)
- **[US2]**: ASG stub tests (Priority 2)  
- **[US4]**: Coverage matrix tracking (Priority 1)

---

## Phase 1: Setup

**Purpose**: Tooling enhancements for efficient test development workflow

- [x] T001 [US4] Enhance utils/validate_asg.py to accept M code from stdin (FR-012)
- [x] T002 [US4] Enhance utils/validate_asg.py to accept M code from command-line argument (FR-012)
- [x] T003 [US4] Verify utils/audit_tests.py correctly identifies xfail stubs vs implemented tests
- [x] T004 [US4] Regenerate baseline coverage matrix in docs/coverage-matrix.md

**Checkpoint**: ✅ Tooling ready for batch implementation

---

## Phase 2: High Coverage Impact - ASG (Priority 1) 🎯 MVP

**Purpose**: Maximize regression protection by testing semantic_analyzer.py uncovered paths (49 stubs, 7 batches)

**Goal**: Cover the most critical code paths first - semantic_analyzer.py has 63% coverage with 418 missed lines

**Independent Test**: `uv run pytest tests/unit/asg/ -v` shows Phase 2 tests passing

### Batch A1: ASG SSVNs (8 stubs, Medium complexity) ✅ COMPLETE

- [X] T005 [US2] Research MUMPS spec §7.1.3 SSVNs in mumps-reference/
- [X] T006 [US2] Find SSVN examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T007 [US2] Evaluate ASG quality for SSVNs using validate_asg.py
- [X] T008 [US2] Implement 8 SSVN tests in tests/unit/asg/s7_expressions/test_s7_1_3_ssvns.py
- [X] T009 [US2] Fix any implementation gaps in src/m2py/analysis/semantic_analyzer.py
- [X] T010 [US2] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Fixed grammar to add ^$LIBRARY SSVN support (was missing from SSVNAME regex)
- Added 2 new tests: test_ssvn_library, test_ssvn_library_abbreviated
- Updated ^$EVENT skip reason with detailed MWAPI explanation
- Documented MWAPI out-of-scope in docs/limitations.md
- Final count: 10 passed, 1 skipped (^$EVENT - MWAPI)

### Batch A2: ASG Special Variables (10 stubs, Medium complexity) ✅ COMPLETE

- [X] T011 [P] [US2] Research MUMPS spec §7.1.4.10 special variables in mumps-reference/
- [X] T012 [US2] Find special variable examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T013 [US2] Evaluate ASG quality for special variables using validate_asg.py
- [X] T014 [US2] Implement special variable tests in tests/unit/asg/s7_expressions/test_s7_1_7_special_variables.py
- [X] T015 [US2] Fix any implementation gaps in src/m2py/
- [X] T016 [US2] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Consolidated stub tests with existing tests into single comprehensive TestSpecialVariablesFull class
- Added full/abbreviated tests for all 18 intrinsic special variables from §7.1.4.10
- Total: 36 tests (18 full names + 18 abbreviations, except X and Y which have no abbreviation)
- Stubs converted: 19, Tests added: 36, Net gain: +29 passing tests
- Final count: 3011 passed, 110 skipped, 911 xfailed

### Batch A3: ASG Command General Rules (5 stubs, Medium complexity) ✅ COMPLETE

- [X] T017 [P] [US2] Research MUMPS spec §8.1 command general rules in mumps-reference/
- [X] T018 [US2] Find command examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T019 [US2] Evaluate ASG quality for commands using validate_asg.py
- [X] T020 [US2] Implement 5 command rule tests in tests/unit/asg/s8_commands/test_s8_1_general_rules.py
- [X] T021 [US2] Fix any implementation gaps in src/m2py/
- [X] T022 [US2] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Tests verify ASG captures: postconditions, timeouts, line references, parameter passing modes, abbreviation normalization
- All 5 stubs converted to passing tests
- Final count: 3016 passed, 110 skipped, 906 xfailed

### Batch A4: ASG Operators (10 stubs, Medium complexity) ✅ COMPLETE

- [X] T023 [P] [US2] Research MUMPS spec §7.2 operators in mumps-reference/
- [X] T024 [US2] Find operator examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T025 [US2] Evaluate ASG quality for operators using validate_asg.py
- [X] T026 [US2] Implement 10 operator tests in tests/unit/asg/s7_expressions/test_s7_2_operators.py
- [X] T027 [US2] Fix any implementation gaps in src/m2py/
- [X] T028 [US2] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Researched §7.2 from spec files: 1977__a107192-199, 1995__a901001, 1995__a101005
- All operators produce correct ASG: MUnaryOp (unary), MBinaryOp (binary)
- 19 stubs converted: 3 unary (+,-,'), 7 arithmetic (+,-,*,/,\,#,**), 1 string (_), 6 relational (=,<,>,[,],]]), 2 logical (&,!)
- Left-to-right evaluation test verifies MUMPS precedence (1+2*3 = 9, not 7)
- No implementation gaps - ASG already correct
- Final count: 3036 passed, 110 skipped, 886 xfailed

### Batch A5: ASG Routine Body (7 stubs, High complexity) ✅ COMPLETE

- [X] T029 [P] [US2] Research MUMPS spec §6.2 routine body in mumps-reference/
- [X] T030 [US2] Find routine body examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T031 [US2] Evaluate ASG quality for routine structure using validate_asg.py
- [X] T032 [US2] Implement 7 routine body tests in tests/unit/asg/s6_routine/test_s6_2_routine_body.py
- [X] T033 [US2] Fix any implementation gaps in src/m2py/
- [X] T034 [US2] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Researched §6.2 spec files: level lines, formal lines, labels, label separator, line body
- All 7 stubs converted + 1 new test (test_formal_line_empty_params)
- Tests verify: level lines with dot blocks, formal parameters, block nesting, comments, label references
- No implementation gaps - ASG already correctly captures routine body structure
- Final count: 3044 passed, 110 skipped, 879 xfailed

### Batch A6: ASG Transaction Processing (3 stubs, High complexity) ✅ COMPLETE

- [X] T035 [P] [US2] Research MUMPS spec §6.3.1 transactions (TSTART/TCOMMIT) in mumps-reference/
- [X] T036 [US2] Find transaction examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T037 [US2] Evaluate ASG quality for transactions using validate_asg.py
- [X] T038 [US2] Implement 3 transaction tests in tests/unit/asg/s6_routine/test_s6_3_1_transaction.py
- [X] T039 [US2] Fix any implementation gaps in src/m2py/
- [X] T040 [US2] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Researched §6.3.1 spec (MDC__a106011.md): transaction boundaries, $TLEVEL tracking, variable isolation
- All 3 stubs converted + 4 additional tests for comprehensive coverage
- Tests verify: TSTART/TCOMMIT boundaries, nested transactions, restart vars, TSTART *, parameters, TROLLBACK, TRESTART
- No implementation gaps - ASG already correctly captures all transaction semantics
- Final count: 3051 passed, 110 skipped, 876 xfailed

### Batch A7: ASG Error Processing (3 stubs, High complexity) ✅ COMPLETE

- [X] T041 [P] [US2] Research MUMPS spec §6.3.2 error processing in mumps-reference/
- [X] T042 [US2] Find error trap examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T043 [US2] Evaluate ASG quality for error handling using validate_asg.py
- [X] T044 [US2] Implement 3 error processing tests in tests/unit/asg/s6_routine/test_s6_3_2_error_processing.py
- [X] T045 [US2] Fix any implementation gaps in src/m2py/
- [X] T046 [US2] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Researched §6.3.2 spec: $ETRAP sets error handler code, $ECODE tracks error conditions
- All 3 stubs converted + 3 additional tests for comprehensive coverage
- Tests verify: $ETRAP/$ECODE SET statements, NEW $ETRAP for stacking, $ESTACK, abbreviated forms
- No implementation gaps - ASG already correctly captures error processing semantics
- Final count: 3057 passed, 110 skipped, 873 xfailed

**Checkpoint**: Phase 2 complete - 49 ASG stubs converted, semantic_analyzer.py coverage significantly improved

---

## Phase 3: Parser Completion (Priority 2)

**Purpose**: Complete parser test coverage - largely routine tests (172 stubs, 17 batches)

**Goal**: All parser stubs converted, parser coverage reaches 95%+

**Independent Test**: `uv run pytest tests/unit/parser/ -v` shows all tests passing with 0 xfails

### Batch B1: Parser Math Library Trig Functions (12 stubs, Low complexity) ✅ COMPLETE

- [X] T047 [P] [US1] Research MUMPS spec §7.1.6.5 library math functions in mumps-reference/
- [X] T048 [P] [US1] Find math function examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T049 [US1] Implement 12 trig function tests (SIN/COS/TAN/COT/SEC/CSC + SINH/COSH/TANH/COTH/SECH/CSCH) in tests/unit/parser/s7_expressions/test_s7_1_6_5_library_functions_math.py

**Additional work completed:**
- All 12 trig stubs converted to passing tests
- Tests verify: ExtrinsicFunction parsing with routine='MATH', function name, NumericLiteral arguments
- No implementation gaps - parser already correctly handles MATH library functions
- Final count: 3069 passed, 110 skipped, 861 xfailed

### Batch B2: Parser Math Library Inverse Trig Functions (10 stubs, Low complexity) ✅ COMPLETE

- [X] T050 [US1] Implement 10 inverse trig function tests (ARCSIN/ARCCOS/ARCTAN/ARCCOT/ARCSEC/ARCCSC + ARCSINH/ARCCOSH/ARCTANH/ARCCOTH)

**Additional work completed:**
- All 10 inverse trig stubs converted to passing tests
- Tests verify: ExtrinsicFunction parsing for inverse functions
- No implementation gaps - parser already correctly handles all MATH library functions
- Final count: 3079 passed, 110 skipped, 851 xfailed

### Batch B3: Parser Math Library Exponential/Logarithmic Functions (8 stubs, Low complexity) ✅ COMPLETE

- [X] T051 [US1] Implement 8 exponential/logarithmic function tests (EXP/LOG/LOG10/E/PI/SQRT/SIGN/ABS)

**Additional work completed:**
- All 8 exponential/logarithmic stubs converted to passing tests
- Tests verify: ExtrinsicFunction parsing with routine='MATH' for each function
- No implementation gaps - parser already correctly handles all MATH library functions
- Final count: 3087 passed, 110 skipped, 843 xfailed

### Batch B4: Parser Math Library Angle/Complex Functions (16 stubs, Low complexity) ✅ COMPLETE

- [X] T052 [US1] Implement 4 angle conversion function tests (DEGRAD/RADDEG/DECDMS/DMSDEC)
- [X] T053 [US1] Implement 12 complex number function tests (COMPLEX/CONJUG/CABS/CADD/CSUB/CMUL/CDIV/CEXP/CLOG/CPOWER/CSIN/CCOS)

**Additional work completed:**
- All 16 angle conversion and complex number stubs converted to passing tests
- Tests verify: ExtrinsicFunction parsing with routine='MATH' for each function
- No implementation gaps - parser already correctly handles all MATH library functions
- Final count: 3103 passed, 110 skipped, 827 xfailed

### Batch B5: Parser Math Library Matrix Functions (11 stubs, Low complexity) ✅ COMPLETE

- [X] T054 [US1] Implement 11 matrix function tests (MTXADD/MTXSUB/MTXMUL/MTXSCA/MTXCOPY/MTXTRP/MTXDET/MTXINV/MTXCOF/MTXEQU/MTXUNIT)
- [X] T055 [US1] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- All 11 matrix function stubs converted to passing tests
- Tests verify: ExtrinsicFunction parsing with routine='MATH' for each function
- No implementation gaps - parser already correctly handles all MATH library matrix functions
- This completes all MATH library parser tests (57 total across B1-B5)
- Final count: 3114 passed, 110 skipped, 816 xfailed

### Batch B6: Parser Intrinsic Functions - String/Numeric/Data (12 stubs, Low complexity) ✅ COMPLETE

- [X] T055 [P] [US1] Research MUMPS spec §7.1.5 intrinsic functions in mumps-reference/
- [X] T056 [US1] Find intrinsic function examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T057 [US1] Implement 12 intrinsic function tests in tests/unit/parser/s7_expressions/test_s7_1_5_intrinsic_functions.py (B6)

**Additional work completed:**
- 12 stubs converted to passing tests: $ASCII, $CHAR, $FIND, $JUSTIFY, $REVERSE, $TRANSLATE (string functions) + $FNUMBER, $RANDOM (numeric) + $DATA, $GET, $ORDER, $QUERY (data functions)
- Tests verify: IntrinsicFunction parsing with correct name and args count
- No implementation gaps - parser already correctly handles all standard intrinsic functions
- Final count: 3126 passed, 110 skipped, 804 xfailed

### Batch B7: Parser Intrinsic Functions - Name/Stack/Text (12 stubs, Low complexity) ✅ COMPLETE

- [X] T058 [US1] Implement 12 remaining intrinsic tests in same file (B7)
- [X] T059 [US1] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- 12 stubs converted to passing tests:
  - Name functions: $NAME, $QLENGTH, $QSUBSCRIPT
  - Stack function: $STACK
  - Text function: $TEXT (uses TextFunction grammar, line_ref dict)
  - Misc functions: $TYPE, $MUMPS, $HOROLOG (special variable)
  - Deprecated (pre-1995): $NEXT, $DEXTRACT, $DPIECE
  - Implementation-defined: $Z... functions ($ZDATE, $ZCONVERT)
- Tests verify: IntrinsicFunction/TextFunction/SpecialVariable parsing with correct type
- No implementation gaps - parser correctly handles all intrinsic function forms
- This completes all §7.1.5 parser intrinsic function tests (B6+B7 = 24 stubs)
- Final count: 3138 passed, 110 skipped, 792 xfailed

### Batch B8-B9: Parser Special Variables (17 stubs, Low complexity) ✅ COMPLETE

- [X] T060 [P] [US1] Research MUMPS spec §7.1.7 special variables in mumps-reference/
- [X] T061 [US1] Find special variable examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T062 [US1] Implement 10 special variable tests in tests/unit/parser/s7_expressions/test_s7_1_7_special_variables.py (B8)
- [X] T063 [US1] Implement 7 remaining special variable tests in same file (B9)
- [X] T064 [US1] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- All 17 stubs converted to passing tests
- Standard special variables: $DEVICE, $ECODE, $ESTACK, $ETRAP, $KEY, $PRINCIPAL, $QUIT, $STACK, $SYSTEM, $TLEVEL, $TRESTART, $Y
- Implementation-specific: $EREF, $IOREFERENCE, $PDISPLAY, $PIOREFERENCE, $REFERENCE (accept IntrinsicFunctionNoArgs or SpecialVariable)
- Tests verify: SpecialVariable class with correct name attribute
- No implementation gaps - parser correctly handles all special variables
- Final count: 3155 passed, 110 skipped, 775 xfailed

### Batch B10: Parser Z-Commands (13 stubs, Low complexity) ✅ COMPLETE

- [X] T065 [P] [US1] Research YDB Z-command extensions
- [X] T066 [US1] Find Z-command examples in YDBTest/
- [X] T067 [US1] Implement 13 Z-command tests in tests/unit/parser/s8_commands/ or tests/unit/parser/extensions/
- [X] T068 [US1] Run full test suite and regenerate coverage matrix

**Additional work completed:**
- Found 13 stubs in test_s8_z_commands.py and 3 stubs in test_s8_2_27_zcommand.py (16 total)
- Converted all 16 stubs to passing tests using command_metamodel fixture
- Z-commands tested: ZCONTINUE, ZHALT, ZWRITE, ZBREAK, ZKILL, ZLINK, ZMESSAGE, ZPRINT, ZSHOW, ZSTEP, ZSYSTEM, ZTSTART, ZTCOMMIT
- Generic Z-command tests verify basic form, with arguments, and with postcondition
- Comprehensive tests already exist in tests/unit/parser/extensions/ydb/
- Final count: 3171 passed, 110 skipped, 759 xfailed

### Batch B11: Parser Command General Rules (10 stubs, Medium complexity) ✅

- [X] T069 [P] [US1] Research MUMPS spec §8.1 command structure in mumps-reference/
- [X] T070 [US1] Find command structure examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T071 [US1] Implement 10 command rule tests in tests/unit/parser/s8_commands/test_s8_1_general_rules.py
- [X] T072 [US1] Run full test suite and regenerate coverage matrix

**Completion Notes B11:**
- Tests converted: test_command_spacing, test_command_comment, test_command_timeout
- Abbreviation parity tests: SET/S, WRITE/W, READ/R, IF/I, FOR/F, DO/D, QUIT/Q
- Grammar attributes: ReadTargetWithTimeout.timeout, IfCommand.conditions, ForCommand.var, LockCommand.targets
- Final count: 3181 passed, 110 skipped, 749 xfailed

### Batch B12-B13: Parser Legacy Pre-1995 Syntax (17 stubs, Medium complexity) ✅

- [X] T073 [P] [US1] Research pre-1995 MUMPS syntax differences
- [X] T074 [US1] Find legacy syntax examples in YDBTest/ or VistA-M/
- [X] T075 [US1] Implement 10 legacy syntax tests in tests/unit/parser/legacy/test_pre1995_syntax.py (B12)
- [X] T076 [US1] Implement 7 remaining legacy tests in same file (B13)
- [X] T077 [US1] Run full test suite and regenerate coverage matrix

**Completion Notes B12-B13:**
- $NEXT function tests: simple, abbreviated ($N), local variable, FOR loop pattern
- 1977 core commands (18): SET, IF, FOR, GOTO, DO, QUIT, WRITE, READ, KILL, LOCK, OPEN, CLOSE, USE, HALT, HANG, BREAK, ELSE, XECUTE
- 1977 intrinsic functions (10): $ASCII, $CHAR, $DATA, $EXTRACT, $FIND, $JUSTIFY, $LENGTH, $PIECE, $RANDOM, $VIEW
- 1984 features: NEW command, $ORDER, $QUERY, $GET, parameter passing
- 1995 features: TSTART, TCOMMIT, TROLLBACK, $TLEVEL
- $NEXT/$ORDER equivalence tests verifying both parse as IntrinsicFunction
- Final count: 3198 passed, 110 skipped, 732 xfailed

### Batch B14: Parser Expressions Misc (15 stubs, Low complexity)

- [X] T078 [P] [US1] Research MUMPS spec §7 expressions in mumps-reference/
- [X] T079 [US1] Find expression examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T080 [US1] Implement 15 misc expression tests (pattern match, operators, ssvns) in tests/unit/parser/s7_expressions/
- [X] T081 [US1] Run full test suite and regenerate coverage matrix

**Completion Notes B14:**
- Implemented 14 expression stubs (values, operators, literals, indirection, extrinsic, pattern match)
- test_s7_1_1_values.py: 4 tests (numeric, string, variable, function values)
- test_s7_2_operators.py: 4 tests (contains, follows, sorts-after, not-contains)
- test_s7_1_4_literals.py: 1 test (exponential literal 1.23E5)
- test_s7_3_indirection.py: 2 tests (subscript/pattern indirection)
- test_s7_1_6_extrinsic_functions.py: 1 test (by-reference passing)
- test_s7_2_5_pattern_match.py: 2 tests (basic pattern, pattern codes)
- Removed invalid stub: extrinsic function label+offset (not supported per MUMPS §8.1.6.2)
- Updated docs/grammar_overview.md to clarify extrinsic functions use labelref (no offset)
- Final count: 3212 passed, 110 skipped, 717 xfailed

### Batch B15: Parser Routine Misc (10 stubs, Medium complexity)

- [X] T082 [P] [US1] Research MUMPS spec §6 routine structure in mumps-reference/
- [X] T083 [US1] Find routine structure examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T084 [US1] Implement 10 routine structure tests in tests/unit/parser/s6_routine/
- [X] T085 [US1] Run full test suite and regenerate coverage matrix

**Completion Notes B15:**
- test_s6_1_routine_head.py: 3 tests (basic, with_label, name_validation)
- test_s6_2_routine_body.py: 4 tests (level_line, formal_line, label, label_separator)
- test_s6_3_1_indirection.py: 1 test (name_indirection)
- test_s6_3_1_transaction.py: 1 test (tstart_basic)
- test_s6_3_2_error_processing.py: 1 test (etrap_setting)
- Final count: 3222 passed, 110 skipped, 707 xfailed

### Batch B16: Parser Commands Misc (15 stubs, Low complexity)

- [X] T086 [P] [US1] Research MUMPS spec §8 commands in mumps-reference/
- [X] T087 [US1] Find command examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T088 [US1] Implement 15 misc command tests in tests/unit/parser/s8_commands/
- [X] T089 [US1] Run full test suite and regenerate coverage matrix

**Completion Notes B16:**
- test_s8_2_04_else.py: 3 tests (basic, abbreviated, with_commands)
- test_s8_2_23_use.py: 4 tests (basic, with_parameters, with_mnemonic, abbreviated)
- test_s8_2_14_new.py: 2 tests (argumentless, abbreviated)
- test_s8_2_07_halt.py: 2 tests (abbreviated, with_postcondition)
- test_s8_2_26_xecute.py: 4 tests (expression, with_postcondition, multiple, abbreviated)
- Final count: 3247 passed, 110 skipped, 682 xfailed

### Batch B17: Parser Character Set (10 stubs, Low complexity) ✅

- [X] T090 [P] [US1] Research MUMPS spec §9 character set in mumps-reference/
- [X] T091 [US1] Find character set examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T092 [US1] Implement 10 character set tests in tests/unit/parser/s9_charset/
- [X] T093 [US1] Run full test suite and regenerate coverage matrix

**Completion Notes (B17)**:
- Commit: `1b40466` - test(parser): Complete character set tests (B17)
- test_s9_1_definitions.py: 4 tests (ascii_characters, control_characters, graphic_characters, special_characters)
- test_s9_character_set.py: 6 tests (graphic_characters, ascii_subset, character_collation, control_characters, char_function_values, ascii_function_values)
- Final count: 3257 passed, 110 skipped, 672 xfailed

**Checkpoint**: Phase 3 complete - 172 parser stubs converted, parser coverage at 95%+

---

## Phase 4: ASG Medium Complexity (Priority 2)

**Purpose**: Complete ASG semantic assertion tests (128 stubs, 10 batches)

**Goal**: All ASG stubs converted, ASG analysis coverage reaches 95%+

**Independent Test**: `uv run pytest tests/unit/asg/ -v` shows all tests passing with 0 xfails

### Batch C1: ASG Intrinsic Functions Part 1 (10 stubs, Medium complexity) ✅

- [X] T094 [P] [US2] Research MUMPS spec §7.1.5 intrinsic function semantics in mumps-reference/
- [X] T095 [US2] Evaluate ASG quality for intrinsic functions using validate_asg.py
- [X] T096 [US2] Implement 10 intrinsic function ASG tests in tests/unit/asg/s7_expressions/test_s7_1_5_intrinsic_functions.py (C1)

**Completion Notes (C1)**:
- Commit: `fc93cd8` - test(asg): Complete intrinsic function ASG tests (C1)
- Tests implemented: $ASCII, $CHAR, $DATA, $EXTRACT, $FIND, $FNUMBER, $GET, $JUSTIFY, $LENGTH, $NAME
- Verified MIntrinsicFunction node structure with name and arguments
- Fixed tests to use MGlobal/GlobalVariable for global variable arguments
- Final count: 3267 passed, 110 skipped, 662 xfailed

### Batch C2: ASG Intrinsic Functions Part 2 (11 stubs, Medium complexity)

- [ ] T097 [US2] Implement 11 remaining intrinsic ASG tests in same file (C2)
- [ ] T098 [US2] Fix any implementation gaps in src/m2py/
- [ ] T099 [US2] Run full test suite and regenerate coverage matrix

### Batch C3-C6: ASG Math Library Functions (57 stubs, Low complexity)

- [ ] T100 [P] [US2] Research MUMPS spec §7.1.6.5 math library semantics in mumps-reference/
- [ ] T101 [US2] Evaluate ASG quality for math functions using validate_asg.py
- [ ] T102 [US2] Implement 15 math lib ASG tests in tests/unit/asg/s7_expressions/test_s7_1_6_5_library_functions_math.py (C3)
- [ ] T103 [US2] Implement 15 more math lib ASG tests in same file (C4)
- [ ] T104 [US2] Implement 15 more math lib ASG tests in same file (C5)
- [ ] T105 [US2] Implement 12 remaining math lib ASG tests in same file (C6)
- [ ] T106 [US2] Run full test suite and regenerate coverage matrix

### Batch C7: ASG Expressions Misc (15 stubs, Medium complexity)

- [ ] T107 [P] [US2] Research MUMPS spec §7 expression semantics (literals, variables, strings)
- [ ] T108 [US2] Evaluate ASG quality for expressions using validate_asg.py
- [ ] T109 [US2] Implement 15 expression ASG tests in tests/unit/asg/s7_expressions/
- [ ] T110 [US2] Fix any implementation gaps in src/m2py/
- [ ] T111 [US2] Run full test suite and regenerate coverage matrix

### Batch C8: ASG Commands Misc (15 stubs, Medium complexity)

- [ ] T112 [P] [US2] Research MUMPS spec §8 command semantics in mumps-reference/
- [ ] T113 [US2] Evaluate ASG quality for commands using validate_asg.py
- [ ] T114 [US2] Implement 15 command ASG tests in tests/unit/asg/s8_commands/
- [ ] T115 [US2] Fix any implementation gaps in src/m2py/
- [ ] T116 [US2] Run full test suite and regenerate coverage matrix

### Batch C9: ASG YDB Extensions (15 stubs, Medium complexity)

- [ ] T117 [P] [US2] Research YDB Z-command semantics
- [ ] T118 [US2] Evaluate ASG quality for Z-commands using validate_asg.py
- [ ] T119 [US2] Implement 15 Z-command ASG tests in tests/unit/asg/extensions/
- [ ] T120 [US2] Fix any implementation gaps in src/m2py/
- [ ] T121 [US2] Run full test suite and regenerate coverage matrix

### Batch C10: ASG Legacy Pre-1995 (5 stubs, Medium complexity)

- [ ] T122 [P] [US2] Research pre-1995 semantic differences
- [ ] T123 [US2] Evaluate ASG quality for legacy constructs using validate_asg.py
- [ ] T124 [US2] Implement 5 legacy ASG tests in tests/unit/asg/legacy/
- [ ] T125 [US2] Fix any implementation gaps in src/m2py/
- [ ] T126 [US2] Run full test suite and regenerate coverage matrix

**Checkpoint**: Phase 4 complete - 128 ASG stubs converted, ASG coverage at 95%+

---

## Phase 5: High Complexity Cross-Cutting (Priority 3)

**Purpose**: Complex cross-cutting tests requiring careful semantic analysis (133 stubs, 19 batches)

**Goal**: All cross-cutting stubs converted, complete feature coverage

**Independent Test**: `uv run pytest tests/unit/cross_cutting/ -v` shows all tests passing with 0 xfails

### Batch D1-D5: Indirection Tests (26 stubs, High complexity)

- [ ] T127 [US2] Research MUMPS spec indirection (@) semantics in mumps-reference/
- [ ] T128 [US2] Find indirection examples in mumps-reference/ (examples__*.md, notes__*.md)
- [ ] T129 [US2] Evaluate ASG quality for indirection using validate_asg.py
- [ ] T130 [US2] Implement 4 name indirection tests in tests/unit/cross_cutting/test_indirection.py (D1)
- [ ] T131 [US2] Implement 4 argument indirection tests in same file (D2)
- [ ] T132 [US2] Implement 4 pattern indirection tests in same file (D3)
- [ ] T133 [US2] Implement 7 indirection semantics tests in same file (D4)
- [ ] T134 [US2] Implement 7 nested indirection tests in same file (D5)
- [ ] T135 [US2] Fix any implementation gaps in src/m2py/
- [ ] T136 [US2] Run full test suite and regenerate coverage matrix

### Batch D6-D8: Naked Reference Tests (24 stubs, High complexity)

- [ ] T137 [US2] Research MUMPS spec naked references (^) in mumps-reference/
- [ ] T138 [US2] Find naked reference examples in mumps-reference/ (examples__*.md, notes__*.md)
- [ ] T139 [US2] Evaluate ASG quality for naked references using validate_asg.py
- [ ] T140 [US2] Implement 8 naked reference state tracking tests in tests/unit/cross_cutting/test_naked_references.py (D6)
- [ ] T141 [US2] Implement 8 naked in expressions tests in same file (D7)
- [ ] T142 [US2] Implement 8 naked edge case tests in same file (D8)
- [ ] T143 [US2] Fix any implementation gaps in src/m2py/
- [ ] T144 [US2] Run full test suite and regenerate coverage matrix

### Batch D9-D11: Postcondition Tests (21 stubs, Medium complexity)

- [ ] T145 [US2] Research MUMPS spec postconditions (:) in mumps-reference/
- [ ] T146 [US2] Find postcondition examples in mumps-reference/ (examples__*.md, notes__*.md)
- [ ] T147 [US2] Evaluate ASG quality for postconditions using validate_asg.py
- [ ] T148 [US2] Implement 7 conditional gate tests in tests/unit/cross_cutting/test_postconditions.py (D9)
- [ ] T149 [US2] Implement 7 argument postcondition tests in same file (D10)
- [ ] T150 [US2] Implement 7 ASG postcondition tests in same file (D11)
- [ ] T151 [US2] Fix any implementation gaps in src/m2py/
- [ ] T152 [US2] Run full test suite and regenerate coverage matrix

### Batch D12-D14: Timeout Tests (27 stubs, Medium complexity)

- [ ] T153 [US2] Research MUMPS spec timeout parameters in mumps-reference/
- [ ] T154 [US2] Find timeout examples in mumps-reference/ (examples__*.md, notes__*.md)
- [ ] T155 [US2] Evaluate ASG quality for timeouts using validate_asg.py
- [ ] T156 [US2] Implement 9 timeout parameter tests in tests/unit/cross_cutting/test_timeouts.py (D12)
- [ ] T157 [US2] Implement 9 timeout ASG tests in same file (D13)
- [ ] T158 [US2] Implement 9 timeout codegen-related tests in same file (D14)
- [ ] T159 [US2] Fix any implementation gaps in src/m2py/
- [ ] T160 [US2] Run full test suite and regenerate coverage matrix

### Batch D15-D19: Language Semantics Tests (35 stubs, High complexity)

- [ ] T161 [US2] Research MUMPS spec language semantics in mumps-reference/
- [ ] T162 [US2] Find language semantics examples in mumps-reference/ (examples__*.md, notes__*.md)
- [ ] T163 [US2] Evaluate ASG quality for language semantics using validate_asg.py
- [ ] T164 [US2] Implement 7 $TEST tracking tests in tests/unit/cross_cutting/test_language_semantics.py (D15)
- [ ] T165 [US2] Implement 7 evaluation order tests in same file (D16)
- [ ] T166 [US2] Implement 7 NEW scoping tests in same file (D17)
- [ ] T167 [US2] Implement 7 transaction semantics tests in same file (D18)
- [ ] T168 [US2] Implement 7 misc semantics tests in same file (D19)
- [ ] T169 [US2] Fix any implementation gaps in src/m2py/
- [ ] T170 [US2] Run full test suite and regenerate coverage matrix

**Checkpoint**: Phase 5 complete - 133 cross-cutting stubs converted

---

## Phase 6: Polish & Verification

**Purpose**: Final verification and documentation updates

- [ ] T171 [US4] Regenerate final coverage matrix in docs/coverage-matrix.md
- [ ] T172 [US4] Verify SC-002 success command passes with 0 xfails
- [ ] T173 [US4] Verify SC-004 parser code coverage reaches 95%+
- [ ] T174 [US4] Verify SC-005 ASG analysis code coverage reaches 95%+
- [ ] T175 [US4] Verify SC-006 all YDBTest functional tests parse successfully
- [ ] T176 Run quickstart.md validation workflow
- [ ] T177 Update README.md test status documentation if needed

**Checkpoint**: Feature complete - 687 stubs converted to implemented tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (High Coverage ASG)**: Depends on Phase 1 - 🎯 **MVP target**
- **Phase 3 (Parser)**: Can start after Phase 1, parallel with Phase 2
- **Phase 4 (ASG Medium)**: Can start after Phase 2
- **Phase 5 (Cross-Cutting)**: Can start after Phase 4 (complex tests may need earlier ASG work)
- **Phase 6 (Polish)**: Depends on all phases complete

### User Story Independence

- **US1 (Parser)**: Phase 3 only - can be completed independently
- **US2 (ASG)**: Phases 2, 4, 5 - sequential dependency within ASG work
- **US4 (Tracking)**: Integrated throughout - coverage matrix regenerated per-batch

### Within Each Batch (FR-010 Workflow)

1. Research (can parallel with other batch research tasks marked [P])
2. Find examples
3. Evaluate ASG quality
4. Implement tests
5. Fix implementation gaps (commit before tests)
6. Run full suite and regenerate coverage matrix

### Parallel Opportunities

- All research tasks marked [P] can run in parallel
- Parser Phase 3 can run in parallel with ASG Phase 2 (different test files)
- Within large batches (B1-B5, C3-C6), sub-tasks are sequential per-file

---

## Implementation Strategy

### MVP Scope

**Phase 1 + Phase 2** constitute the MVP:
- Setup tooling (4 tasks)
- 7 high-coverage ASG batches (42 tasks)
- **Total MVP**: 46 tasks, 49 stubs converted
- **Value**: Maximizes regression protection by covering semantic_analyzer.py gaps first

### Incremental Delivery

Each batch completion provides value:
- Reduced xfail count
- Updated coverage matrix
- Improved code coverage
- More robust regression protection

### Suggested Order for Single Developer

1. **Phase 1**: Setup (T001-T004)
2. **Phase 2**: High coverage ASG batches A1-A7 (T005-T046)
3. **Phase 3**: Parser batches B1-B17 (T047-T093) - routine, high throughput
4. **Phase 4**: ASG medium batches C1-C10 (T094-T126)
5. **Phase 5**: Cross-cutting D1-D19 (T127-T170) - most complex, save for last
6. **Phase 6**: Final verification (T171-T177)

---

## Success Command

```bash
# Final success verification (SC-002)
uv run pytest tests/unit/parser/ tests/unit/asg/ tests/unit/analysis/ tests/unit/meta/ tests/unit/cross_cutting/ -v

# Expected: ~1876 passed, 93 skipped, 0 xfailed
```
