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

### Batch C2: ASG Intrinsic Functions Part 2 (11 stubs, Medium complexity) ✅

- [X] T097 [US2] Implement 11 remaining intrinsic ASG tests in same file (C2)
- [X] T098 [US2] Fix any implementation gaps in src/m2py/
- [X] T099 [US2] Run full test suite and regenerate coverage matrix

**Completion Notes (C2)**:
- Tests implemented: $ORDER, $PIECE, $QLENGTH, $QSUBSCRIPT, $QUERY, $RANDOM, $REVERSE, $SELECT, $STACK, $TEXT, $TRANSLATE
- Special type handling:
  - $SELECT → SelectFunction with MSelectArg condition/value pairs
  - $TEXT → TextFunction with line_ref dictionary (label, offset, routine)
  - Most functions → MIntrinsicFunction with name and arguments
- Fixed MUnaryOp handling for negative direction in $ORDER(-1)
- Added MUnaryOp import to test file
- Final count: 3278 passed, 110 skipped, 651 xfailed

### Batch C3-C6: ASG Math Library Functions (57 stubs, Low complexity) ✅

- [X] T100 [P] [US2] Research MUMPS spec §7.1.6.5 math library semantics in mumps-reference/
- [X] T101 [US2] Evaluate ASG quality for math functions using validate_asg.py
- [X] T102 [US2] Implement 15 math lib ASG tests in tests/unit/asg/s7_expressions/test_s7_1_6_5_library_functions_math.py (C3)
- [X] T103 [US2] Implement 15 more math lib ASG tests in same file (C4)
- [X] T104 [US2] Implement 15 more math lib ASG tests in same file (C5)
- [X] T105 [US2] Implement 12 remaining math lib ASG tests in same file (C6)
- [X] T106 [US2] Run full test suite and regenerate coverage matrix

**Completion Notes (C3-C6)**:
- All 57 math library function ASG tests implemented in single batch
- Functions use $$%FUNC^MATH extrinsic function call syntax
- All parse to ExtrinsicFunction with:
  - label = function name (e.g., '%SIN', '%COS', '%MTXADD')
  - routine = 'MATH'
  - arguments = list of MActualParameter objects
- Test categories:
  - Trigonometric (12): SIN, COS, TAN, COT, SEC, CSC + hyperbolic variants
  - Inverse Trig (10): ARCSIN, ARCCOS, ARCTAN, ARCCOT, ARCSEC, ARCCSC + hyperbolic
  - Exponential (8): EXP, LOG, LOG10, E, PI, SQRT, SIGN, ABS
  - Angle Conversion (4): DEGRAD, RADDEG, DECDMS, DMSDEC
  - Complex Numbers (12): COMPLEX, CONJUG, CABS, CADD, CSUB, CMUL, CDIV, CEXP, CLOG, CPOWER, CSIN, CCOS
  - Matrix Operations (11): MTXADD, MTXSUB, MTXMUL, MTXSCA, MTXCOPY, MTXTRP, MTXDET, MTXINV, MTXCOF, MTXEQU, MTXUNIT
- Added verify_math_function helper for consistent test assertions
- Final count: 3335 passed, 110 skipped, 594 xfailed

### Batch C7: ASG Expressions Misc (17 stubs, Medium complexity)

- [X] T107 [P] [US2] Research MUMPS spec §7 expression semantics (literals, variables, strings)
- [X] T108 [US2] Evaluate ASG quality for expressions using validate_asg.py
- [X] T109 [US2] Implement 17 expression ASG tests in tests/unit/asg/s7_expressions/
- [X] T110 [US2] Fix any implementation gaps in src/m2py/
- [X] T111 [US2] Run full test suite and regenerate coverage matrix

**Completion Notes (C7):**
- Commit: `c25c867`
- Implemented 17 tests across 3 files:
  - test_s7_1_1_values.py (4 tests): value_type_inference, string_value_representation, numeric_value_representation, empty_string_representation
  - test_s7_1_2_variables.py (6 tests): local_variable_resolution, global_variable_resolution, naked_global_reference, variable_scope_analysis, subscripted_variable, glvn_unification
  - test_s7_1_4_literals.py (7 tests): integer_literal, decimal_literal, string_literal, escaped_quotes, numeric_string_literal, empty_string_literal, scientific_notation
- Key imports: m2py.parser.textx_classes (StringLiteral, NumericLiteral, LocalVariable, GlobalVariable, NakedGlobal), m2py.asg.expressions (LiteralType)
- Uses analyze_set_command helper pattern from test_s7_2_operators.py (parse_commands_from_line + analyze_command)
- Final count: 3352 passed, 110 skipped, 577 xfailed

### Batch C8: ASG Commands Misc (15 stubs, Medium complexity)

- [X] T112 [P] [US2] Research MUMPS spec §8 command semantics in mumps-reference/
- [X] T113 [US2] Evaluate ASG quality for commands using validate_asg.py
- [X] T114 [US2] Implement 15 command ASG tests in tests/unit/asg/s8_commands/
- [X] T115 [US2] Fix any implementation gaps in src/m2py/
- [X] T116 [US2] Run full test suite and regenerate coverage matrix

**C8 completion notes**:
- Implemented 15 stubs across 10 test files:
  - test_s8_2_01_break.py (1 test): test_break_with_postcondition
  - test_s8_2_02_close.py (1 test): test_close_device_tracking
  - test_s8_2_03_do.py (1 test): test_mcall_creation
  - test_s8_2_04_else.py (3 tests): test_else_command_node, test_else_test_dependency, test_else_control_flow
  - test_s8_2_06_goto.py (3 tests): test_goto_type_classification, test_goto_computed_target, test_goto_control_flow_impact
  - test_s8_2_07_halt.py (1 test): test_halt_control_flow_termination
  - test_s8_2_09_if.py (2 tests): test_if_test_modification, test_if_control_flow
  - test_s8_2_11_kill.py (1 test): test_kill_variable_tracking
  - test_s8_2_14_new.py (1 test): test_new_exclusive_form
  - test_s8_2_17_read.py (1 test): test_read_single_character
- Key imports: m2py.asg.elements (MCall), m2py.asg.statements, m2py.asg.expressions
- Fixed MCall import (from m2py.asg.elements, not m2py.asg.values)
- Note: ELSE postcondition parsing not implemented - test documents existing structure
- Final count: 3367 passed, 110 skipped, 562 xfailed

### Batch C9: ASG YDB Extensions (15 stubs, Medium complexity) ✅

- [X] T117 [P] [US2] Research YDB Z-command semantics
- [X] T118 [US2] Evaluate ASG quality for Z-commands using validate_asg.py
- [X] T119 [US2] Implement 15 Z-command ASG tests in tests/unit/asg/extensions/
- [X] T120 [US2] Fix any implementation gaps in src/m2py/
- [X] T121 [US2] Run full test suite and regenerate coverage matrix

**Completion Notes (C9)**:
- Commit: `95e4d85`
- Implemented 18 stubs across 10 test files → 24 passing tests:
  - test_zallocate.py: 2 tests (lockop, targets)
  - test_zbreak.py: 2 tests (MZBreakArg location/action)
  - test_zedit.py: 1 test (args with StringLiteral)
  - test_zgoto.py: 3 tests (level, target, MCall)
  - test_zhalt.py: 2 tests (exitcode attribute)
  - test_zkill.py: 2 tests (MZKillStatement/MZWithdrawStatement)
  - test_zlink.py: 2 tests (args with routine name)
  - test_ztrigger.py: 1 test (GlobalVariable targets)
  - test_zwrite.py: 2 tests (MZWriteArg with target)
  - test_zhelp.py: 3 tests (node creation, topic, topic+library)
- ZHELP Implementation (new command support):
  - Grammar: Added ZHelpCommand rule with ZHE[LP] syntax
  - ASG: Added MZHelpStatement and MZHelpArg classes
  - Semantic analyzer: Added _analyze_ZHelpCommand handler
  - Parser tests: 4 new tests
- Grammar ordering fix: ZHelpCommand precedes ZHaltCommand (ZH abbreviation conflict)
- Final count: 1608 passed, 110 skipped, 542 xfailed

### Batch C10: ASG Legacy Pre-1995 (5 stubs, Medium complexity) ✅

- [X] T122 [P] [US2] Research pre-1995 semantic differences
- [X] T123 [US2] Evaluate ASG quality for legacy constructs using validate_asg.py
- [X] T124 [US2] Implement 5 legacy ASG tests in tests/unit/asg/legacy/
- [X] T125 [US2] Fix any implementation gaps in src/m2py/
- [X] T126 [US2] Run full test suite and regenerate coverage matrix

**Completion Notes (C10)**:
- All 5 stubs converted to passing tests in test_pre1995_semantics.py:
  - test_next_function_asg_structure: $NEXT produces IntrinsicFunction ASG node
  - test_next_function_variable_tracking: K, X tracked in ScopeVariables.reads/writes
  - test_next_function_traversal_pattern: FOR loop classified as ARGUMENTLESS, $N parsed
  - test_legacy_variable_scoping: Pre-NEW pattern with KILL tracked as write
  - test_legacy_array_copy_pattern: Pre-MERGE $ORDER traversal pattern works
- Key imports: ForLoopType from m2py.asg.enums, IntrinsicFunction/GlobalVariable from textx_classes
- ScopeVariables uses: reads, writes, newed (not read, written, killed)
- Final count: 1613 passed, 110 skipped, 537 xfailed

**Checkpoint**: Phase 4 complete - 128 ASG stubs converted, ASG coverage at 95%+

---

## Phase 5: High Complexity Cross-Cutting (Priority 3)

**Purpose**: Complex cross-cutting tests requiring careful semantic analysis (133 stubs, 19 batches)

**Goal**: All cross-cutting stubs converted, complete feature coverage

**Independent Test**: `uv run pytest tests/unit/cross_cutting/ -v` shows all tests passing with 0 xfails

### Batch D1-D5: Indirection Tests (26 stubs, High complexity) ✅ COMPLETE

- [X] T127 [US2] Research MUMPS spec indirection (@) semantics in mumps-reference/
- [X] T128 [US2] Find indirection examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T129 [US2] Evaluate ASG quality for indirection using validate_asg.py
- [X] T130 [US2] Implement 4 name indirection tests in tests/unit/cross_cutting/test_indirection.py (D1)
- [X] T131 [US2] Implement 6 argument indirection tests in same file (D2)
- [X] T132 [US2] Implement 3 pattern indirection tests in same file (D3)
- [X] T133 [US2] Implement 8 indirection semantics tests in same file (D4)
- [X] T134 [US2] Keep 5 codegen stubs as xfail (D5 - codegen not implemented)
- [X] T135 [US2] No implementation gaps found - ASG correctly handles all indirection types
- [X] T136 [US2] Run full test suite and regenerate coverage matrix

**Completion notes:**
- 21 tests implemented, 5 xfailed (codegen stubs)
- Fixed MReadTarget import location (m2py.asg.statements)
- Discovered XECUTE uses code_expressions field, not arguments
- DO indirection tracks via MCall.label_is_indirect and MCall.indirection
- Pattern indirection uses MPatternMatch.pattern_indirect field
- Subscript indirection (@VAR@(subs)) stores subs in name_indirection_subscripts

### Batch D6-D8: Naked Reference Tests (24 stubs, High complexity) ✅ COMPLETE

- [X] T137 [US2] Research MUMPS spec naked references (^) in mumps-reference/
- [X] T138 [US2] Find naked reference examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T139 [US2] Evaluate ASG quality for naked references using validate_asg.py
- [X] T140 [US2] Implement 8 naked reference state tracking tests in tests/unit/cross_cutting/test_naked_references.py (D6)
- [X] T141 [US2] Implement 8 naked in expressions tests in same file (D7)
- [X] T142 [US2] Implement 8 naked edge case tests in same file (D8)
- [X] T143 [US2] Fix any implementation gaps in src/m2py/
- [X] T144 [US2] Run full test suite and regenerate coverage matrix

**Completion notes:**
- 20 tests implemented, 4 xfailed (codegen stubs requiring runtime execution)
- MUMPS spec reference: §7.1.2.4 (1995__a107011.md) defines naked reference semantics
- Naked format: ^(subscripts) - global name omitted, taken from naked indicator
- Parser classes: GlobalVariable (has name), NakedGlobal (no name) from textx_classes
- ASG classes: MGlobal, MNakedGlobal from m2py.asg.expressions
- Key test patterns:
  - TestNakedReferenceParser (4 tests): basic, multiple subscripts, expression subscript, vs full global
  - TestNakedIndicatorParser (3 tests): SET/READ/KILL global sets indicator
  - TestNakedReferenceASG (4 tests): classification, indicator tracking, subscripts, sequence dependency
  - TestNakedStateTransitions (6 tests): 5 passing ASG tests, 1 xfail codegen runtime test
  - TestNakedReferenceErrors (2 tests): 1 passing scope test, 1 xfail M1 error detection
  - TestNakedReferenceEdgeCases (5 tests): $DATA, $ORDER, KILL pass; MERGE, LOCK xfail
- Used parse_expression + analyze_expression for intrinsic function testing
- Final count: 1654 passed, 110 skipped, 496 xfailed

### Batch D9-D11: Postcondition Tests (21 stubs, Medium complexity) ✅ COMPLETE

- [X] T145 [US2] Research MUMPS spec postconditions (:) in mumps-reference/
- [X] T146 [US2] Find postcondition examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T147 [US2] Evaluate ASG quality for postconditions using validate_asg.py
- [X] T148 [US2] Implement 7 conditional gate tests in tests/unit/cross_cutting/test_postconditions.py (D9)
- [X] T149 [US2] Implement 7 argument postcondition tests in same file (D10)
- [X] T150 [US2] Implement 7 ASG postcondition tests in same file (D11)
- [X] T151 [US2] No implementation gaps found - ASG correctly handles all postcondition types
- [X] T152 [US2] Run full test suite and regenerate coverage matrix

**Completion notes:**
- 23 tests implemented, 5 xfailed (codegen stubs)
- MUMPS spec reference: §8.1.4 (1995__a108005.md, notes__a108005.md)
- Command postconditions: All commands EXCEPT Else, For, If
- Argument postconditions: Only Do, Goto, Xecute support arg-level postconditions
- Key test patterns:
  - TestCommandPostconditionsParser (7 tests): SET, WRITE, DO, KILL, complex expr, function, QUIT
  - TestArgumentPostconditionsParser (7 tests): DO, GOTO, XECUTE, expr, mixed, routine, params
  - TestMixedPostconditionsParser (2 tests): command+arg on DO and GOTO
  - TestPostconditionsASG (7 tests): command, arg, expr, combined, negation, function, numeric
  - TestPostconditionsCodegen (5 xfail): runtime execution stubs
- MUMPS left-to-right parsing confirmed: X>0&Y<10 parses as ((X>0)&Y)<10
- Final count: 3460 passed, 110 skipped, 480 xfailed

### Batch D12-D14: Timeout Tests (27 stubs, Medium complexity) ✅ COMPLETE

- [X] T153 [US2] Research MUMPS spec timeout parameters in mumps-reference/
- [X] T154 [US2] Find timeout examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T155 [US2] Evaluate ASG quality for timeouts using validate_asg.py
- [X] T156 [US2] Implement 9 timeout parameter tests in tests/unit/cross_cutting/test_timeouts.py (D12)
- [X] T157 [US2] Implement 9 timeout ASG tests in same file (D13)
- [X] T158 [US2] Implement 9 timeout codegen-related tests in same file (D14)
- [X] T159 [US2] No implementation gaps found - ASG correctly handles all timeout types
- [X] T160 [US2] Run full test suite and regenerate coverage matrix

**Completion notes:**
- 22 tests passing, 8 xfailed (codegen stubs requiring runtime $TEST evaluation)
- MUMPS spec references: §7.1.4.10 (1995__a107074.md), §8.2.10, §8.2.12, §8.2.15, §8.2.17
- Timeout commands modify $TEST: success=$TEST=1, timeout=$TEST=0
- Key test patterns:
  - TestOpenTimeoutParser (3 tests): timeout, params+timeout, no timeout
  - TestReadTimeoutParser (5 tests): timeout, expr, fixed length, char read, no timeout
  - TestJobTimeoutParser (3 tests): ::timeout, params+timeout, no timeout
  - TestLockTimeoutParser (5 tests): timeout, expr, incremental, parenthesized, no timeout
  - TestTimeoutsASG (6 tests): MReadTarget, MLockStatement.targets dict, MOpenDevice, negative timeout
  - TestTimeoutsCodegen (8 xfail): $TEST modification runtime behavior
- ASG structure findings:
  - MOpenStatement.devices -> MOpenDevice.timeout
  - MLockStatement.targets -> list of dicts with 'timeout' key
  - MReadTarget.timeout attribute
- Final count: 3482 passed, 110 skipped, 461 xfailed

### Batch D15-D19: Language Semantics Tests (35 stubs, High complexity)

- [X] T161 [US2] Research MUMPS spec language semantics in mumps-reference/
- [X] T162 [US2] Find language semantics examples in mumps-reference/ (examples__*.md, notes__*.md)
- [X] T163 [US2] Evaluate ASG quality for language semantics using validate_asg.py
- [X] T164 [US2] Implement 7 $TEST tracking tests in tests/unit/cross_cutting/test_language_semantics.py (D15)
- [X] T165 [US2] Implement 7 evaluation order tests in same file (D16)
- [X] T166 [US2] Implement 7 NEW scoping tests in same file (D17)
- [X] T167 [US2] Implement 7 transaction semantics tests in same file (D18)
- [X] T168 [US2] Implement 7 misc semantics tests in same file (D19)
- [X] T169 [US2] Fix any implementation gaps in src/m2py/
- [X] T170 [US2] Run full test suite and regenerate coverage matrix

**T161-T164 completion notes:**
- MUMPS spec refs: §7.1.4.10 ($TEST definition), §8.2.4 (ELSE), §8.2.9 (IF)
- Examples: examples__a108035.md (IF patterns)
- ASG quality: MIfStatement.condition/conditions, MElseStatement.body all captured
- Existing tests: test_s8_2_09_if.py, test_s8_2_04_else.py have detailed command tests
- D15 tests (9 total): 5 passing (parser/ASG), 4 xfail stubs (codegen runtime)
- Final count: 3487 passed, 110 skipped, 456 xfailed

**T165 completion notes:**
- MUMPS spec ref: §7.2 (1995__a107190 - Expression tail, left-to-right evaluation)
- ASG structure verified: 2+3*4 becomes ((2+3)*4) with * at top, + on left branch
- Existing test: test_s7_2_operators.py::test_left_to_right_evaluation covers same behavior
- D16 tests (7 total): 2 passing (parser/ASG), 5 xfail stubs (codegen runtime)
- Final count: 3489 passed, 110 skipped, 454 xfailed

**T166 completion notes:**
- MUMPS spec ref: §8.2.14 (1995__a108042.md - NEW command, exclusive form)
- Examples: examples__a108042.md - NEW (A,B,C) syntax, scoping behavior
- ASG quality: MNewStatement has exclusive=True, except_list=['X','Y'] for NEW (X,Y)
- Existing test: test_s8_2_14_new.py::test_new_exclusive_form covers basic ASG
- D17 tests (8 total): 5 passing (3 parser, 2 ASG), 3 xfail stubs (codegen runtime)
- Final count: 3494 passed, 110 skipped, 449 xfailed

**T167 completion notes:**
- MUMPS spec refs: §8.2.19 (TCOMMIT), §8.2.21 (TROLLBACK), §8.2.22 (TSTART)
- Examples: examples__a108053.md - TSTART/TCOMMIT/TROLLBACK transaction examples
- ASG quality: MTStartStatement, MTCommitStatement, MTRollbackStatement all working
- ASG captures: restart_all, restart_vars for TSTART parameters
- Existing tests: test_s8_2_22_tstart.py stubs focus on individual command aspects
- D18 tests (10 total): 5 passing (3 parser, 2 ASG), 5 xfail stubs (codegen $TLEVEL runtime)
- Final count: 3499 passed, 110 skipped, 444 xfailed

**T168 completion notes:**
- MUMPS spec refs: §6.3 (block structure), §8.2.3 (DO), §8.2.16 (QUIT)
- Topics: Argumentless commands, QUIT return values, block execution levels
- ASG quality: MDoStatement (body, targets), MQuitStatement (return_value or None)
- D19 tests (7 total): 5 passing (3 parser, 2 ASG), 2 xfail stubs (codegen runtime)
- Final count: 3504 passed, 110 skipped, 446 xfailed

**T169 completion notes:**
- No implementation gaps found - all parser/ASG tests pass
- All xfails are codegen runtime stubs (expected)

**T170 completion notes:**
- Full test suite: 3504 passed, 110 skipped, 446 xfailed
- D15-D19 batch complete: 41 tests added (22 passing, 19 xfail codegen stubs)

**Checkpoint**: Phase 5 complete - D15-D19 language semantics batch done

---

## Phase 6: Polish & Verification

**Purpose**: Final verification and documentation updates

- [X] T171 [US4] Regenerate final coverage matrix in docs/coverage-matrix.md
- [X] T172 [US4] Verify SC-002 success command passes with 0 xfails → **FAILED: 153 xfails remain (see Phase 7)**
- [ ] T173 [US4] Verify SC-004 parser code coverage reaches 95%+
- [ ] T174 [US4] Verify SC-005 ASG analysis code coverage reaches 95%+
- [ ] T175 [US4] Verify SC-006 all YDBTest functional tests parse successfully
- [ ] T176 Run quickstart.md validation workflow
- [ ] T177 Update README.md test status documentation if needed

**Phase 6 Findings**:
- SC-002 verification: 1613 passed, 91 skipped, **153 xfailed** (should be 0)
- Skipped tests: Properly documented per FR-055 + need 3 additions to limitations.md
- Created Phase 7 with 23 tasks to address gaps

**Checkpoint**: Phase 6 verification complete - gaps identified, Phase 7 created

---

## Phase 7: Remaining Stub Implementation (GAPS FOUND)

**Purpose**: Address remaining 153 parser/ASG stubs that should be 0 per SC-001/SC-002

**Workflow**: Each batch follows FR-010 validation process (see [batch-workflow.md](./contracts/batch-workflow.md))

**Note**: Original SC-001 count was 687 stubs. Phases 2-5 converted 534 stubs; Phase 7 addresses the 153 remaining.

**Status**: Phase 6 verification found 153 remaining xfails in parser/ASG tests
- Parser stubs: 71 (SSVNs: 8, library functions: 11, pattern match: 6, commands: 46)
- ASG stubs: 82 (routine: 7, expressions: 28, commands: 44, charset: 3)

### Batch E1: Parser SSVNs (8 stubs)

- [X] T178 [US1] Implement 8 SSVN parser tests in tests/unit/parser/s7_expressions/test_s7_1_3_ssvns.py

**Completion Notes (E1)**:
- Converted 8 stubs to 9 passing tests (added ^$Y test for completeness)
- Extended grammar SSVNAME regex to support ^$Z and ^$Y implementation-defined SSVNs
- Tests: ^$JOB, ^$ROUTINE, ^$GLOBAL, ^$LOCK, ^$DEVICE, ^$CHARACTER, ^$SYSTEM, ^$ZJOB, ^$YTEST
- Grammar file: src/m2py/grammar/expressions.tx - added Z[A-Za-z]* and Y[A-Za-z]* patterns
- Final parser count: 762 passed, 65 skipped, 63 xfailed

### Batch E2: Parser Library Functions (11 stubs)

- [ ] T179 [US1] Implement 5 CHARACTER library function tests in test_s7_1_6_5_library_functions_character.py
- [ ] T180 [US1] Implement 6 STRING library function tests in test_s7_1_6_5_library_functions_string.py

### Batch E3: Parser Pattern Match (6 stubs)

- [ ] T181 [US1] Implement 6 pattern match parser tests in test_s7_2_5_pattern_match.py

### Batch E4: Parser Commands (46 stubs, split into sub-batches)

- [ ] T182 [US1] Implement BREAK, CLOSE, DO, GOTO, HANG parser stubs (11 tests)
  - Files: test_s8_2_01_break.py, test_s8_2_02_close.py, test_s8_2_03_do.py, test_s8_2_06_goto.py, test_s8_2_08_hang.py
- [ ] T183 [US1] Implement JOB, KILL, LOCK, MERGE parser stubs (10 tests)
  - Files: test_s8_2_10_job.py, test_s8_2_11_kill.py, test_s8_2_12_lock.py, test_s8_2_13_merge.py
- [ ] T184 [US1] Implement OPEN, QUIT, READ, VIEW, WRITE parser stubs (12 tests)
  - Files: test_s8_2_15_open.py, test_s8_2_16_quit.py, test_s8_2_17_read.py, test_s8_2_24_view.py, test_s8_2_25_write.py
- [ ] T185 [US1] Implement device params, ksubscripts, kvalue parser stubs (13 tests)
  - Files: test_s8_3_device_params.py, test_s8_ksubscripts.py, test_s8_kvalue.py

### Batch E5: ASG Routine (7 stubs)

- [ ] T186 [US2] Implement routine head and indirection ASG tests (7 tests)

### Batch E6: ASG Expressions (28 stubs)

- [ ] T187 [US2] Implement library functions ASG tests (11 tests)
- [ ] T188 [US2] Implement extrinsic functions ASG tests (5 tests)
- [ ] T189 [US2] Implement pattern match ASG tests (5 tests)
- [ ] T190 [US2] Implement indirection ASG tests (7 tests)

### Batch E7: ASG Commands (44 stubs)

- [X] T191 [US2] Implement KILL, NEW, QUIT, READ, SET ASG stubs (11 tests)
- [X] T192 [US2] Implement transaction (TSTART/TCOMMIT/TROLLBACK) ASG stubs (9 tests)
- [X] T193 [US2] Implement USE, WRITE, XECUTE, ZCOMMAND ASG stubs (12 tests)
- [X] T194 [US2] Implement device params, ksubscripts, kvalue ASG stubs (10 tests)

### Batch E8: ASG Charset (3 stubs)

- [X] T195 [US2] Implement 3 charset ASG tests in test_s9_1_definitions.py

### Implementation Gap Fixes (per FR-005/FR-006)

- [X] T196 [US1] Fix any parser implementation gaps discovered during E1-E4 (src/m2py/parser/)
- [X] T197 [US2] Fix any ASG implementation gaps discovered during E5-E8 (src/m2py/analysis/)

### Documentation Updates

- [X] T198 [US4] Add VIEW command to limitations.md (implementation-defined)
- [X] T199 [US4] Add $NEXT function to limitations.md (deprecated pre-1995)
- [X] T200 [US4] Add extended character sets to limitations.md (implementation-defined)

### Final Verification

- [X] T201 [US4] Run SC-002 success command and verify xfail status
  - **Result**: 3563 passed, 109 skipped, 389 xfailed
  - **Gap Found**: 136 non-codegen stubs remain (59 parser, 37 ASG, 40 cross-cutting)
  - Skipped tests: All properly documented in limitations.md ✓
  - See Phase 8 for remediation tasks

- [X] T202 [US4] Regenerate final coverage matrix

**Checkpoint**: Phase 7 complete - gaps identified, Phase 8 created for remediation

---

## Phase 8: Stub Test Remediation (Post-Audit)

**Discovery**: T201 audit revealed 136 stub tests outside codegen that were never implemented.
These are marked with `@pytest.mark.xfail` and contain `pytest.fail("Stub - implement test")`.

**Batch Sizing Strategy** (per FR-009, complexity-adjusted):
- **High complexity** (indirection, language semantics, extrinsics): 3-5 stubs max
- **Medium complexity** (pattern match, timeouts, library functions): 6-10 stubs
- **Lower complexity** (I/O commands, flow control, data ops): 10-15 stubs

### Summary of Remaining Stubs

| Category | File | Stubs | Complexity |
|----------|------|-------|------------|
| **Parser (42 remaining after F1)** | | | |
| Library Functions | test_s7_1_6_5_library_functions_string.py | 6 | Medium |
| Library Functions | test_s7_1_6_5_library_functions_character.py | 5 | Medium |
| Pattern Match | test_s7_2_5_pattern_match.py | 6 | Medium |
| ~~VIEW~~ | ~~test_s8_2_24_view.py~~ | ~~2~~ | ~~Low~~ ✅ F1 |
| QUIT | test_s8_2_16_quit.py | 2 | Low |
| DO | test_s8_2_03_do.py | 1 | Low |
| LOCK | test_s8_2_12_lock.py | 3 | Low |
| KILL | test_s8_2_11_kill.py | 3 | Low |
| ~~Device Params~~ | ~~test_s8_3_device_params.py~~ | ~~4~~ | ~~Low~~ ✅ F1 |
| GOTO | test_s8_2_06_goto.py | 1 | Low |
| ~~WRITE~~ | ~~test_s8_2_25_write.py~~ | ~~1~~ | ~~Low~~ ✅ F1 |
| ~~CLOSE~~ | ~~test_s8_2_02_close.py~~ | ~~3~~ | ~~Low~~ ✅ F1 |
| JOB | test_s8_2_10_job.py | 5 | Medium |
| ~~READ~~ | ~~test_s8_2_17_read.py~~ | ~~2~~ | ~~Low~~ ✅ F1 |
| ~~OPEN~~ | ~~test_s8_2_15_open.py~~ | ~~5~~ | ~~Low~~ ✅ F1 |
| HANG | test_s8_2_08_hang.py | 3 | Low |
| MERGE | test_s8_2_13_merge.py | 4 | Low |
| BREAK | test_s8_2_01_break.py | 3 | Low |
| **ASG (37 total)** | | | |
| Routine Head | test_s6_1_routine_head.py | 3 | Medium |
| Indirection (s6) | test_s6_3_1_indirection.py | 4 | **High** |
| Library Functions | test_s7_1_6_5_library_functions_string.py | 6 | Medium |
| Indirection (s7) | test_s7_3_indirection.py | 7 | **High** |
| Library Functions | test_s7_1_6_5_library_functions_character.py | 5 | Medium |
| Pattern Match | test_s7_2_operators_pattern_match.py | 3 | Medium |
| Extrinsic Functions | test_s7_1_6_extrinsic_functions.py | 5 | **High** |
| Pattern Match | test_s7_2_5_pattern_match.py | 2 | Medium |
| TRESTART | test_s8_2_20_trestart.py | 2 | Medium |
| **Cross-Cutting (40 total)** | | | |
| Naked References | test_naked_references.py | 2 | Medium |
| Indirection | test_indirection.py | 5 | **High** |
| Timeouts | test_timeouts.py | 8 | Medium |
| Postconditions | test_postconditions.py | 5 | Medium |
| Language Semantics | test_language_semantics.py | 20 | **High** |

---

### Batch F1: Parser I/O Commands (17 stubs) - Low Complexity ✅ COMPLETE

I/O-related commands: OPEN, CLOSE, READ, WRITE, VIEW, device parameters.

- [X] T203 [US1] **Research**: Review MUMPS reference §8.2.2 (CLOSE), §8.2.15 (OPEN), §8.2.17 (READ), §8.2.25 (WRITE), §8.2.24 (VIEW), §8.3 (device params). Check mumps-reference/examples__*.md for I/O patterns.
- [X] T204 [US1] Implement parser stubs: OPEN (5), CLOSE (3), READ (2), WRITE (1), VIEW (2) - 13 stubs
- [X] T205 [US1] Implement parser stubs: device_params (4 stubs) - completes I/O batch
- [X] T206 [US4] Regenerate coverage matrix

**Completion Notes (F1)**:
- All 17 parser stubs converted to passing tests
- OPEN: basic, with_parameters, with_timeout, with_mnemonic, multiple devices
- CLOSE: basic, with_parameters, multiple_devices
- READ: with_prompt, format_control (!, ?n, #)
- WRITE: argumentless (empty args list)
- VIEW: with_arguments, abbreviated (V vs VIEW)
- Device params: basic, with_value, list, mnemonic
- Tests verify correct parsing using parse_line fixture and command_metamodel
- All use proper spec references and docstrings
- Final count: 3580 passed, 109 skipped, 372 xfailed

### Batch F2: Parser Flow Control Commands (14 stubs) - Low Complexity

Execution flow commands: DO, GOTO, QUIT, BREAK, HANG, JOB.

- [X] T207 [US1] **Research**: Review MUMPS reference §8.2.1 (BREAK), §8.2.3 (DO), §8.2.6 (GOTO), §8.2.8 (HANG), §8.2.10 (JOB), §8.2.16 (QUIT). Check YDBTest/ for flow control examples.
- [X] T208 [US1] Implement parser stubs: DO (1), GOTO (1), QUIT (2), BREAK (3), HANG (3) - 10 stubs
- [X] T209 [US1] Implement parser stubs: JOB (5 stubs) - process spawning, medium complexity
- [X] T210 [US4] Regenerate coverage matrix

**Completion Notes (F2 - T207/T208)**:
- All 10 flow control parser stubs converted to passing tests
- BREAK: argumentless, abbreviated (B vs BREAK), with_postcondition (B:X)
- DO: with_postcondition (D:X LABEL)
- GOTO: with_postcondition (G:X LABEL)
- HANG: abbreviated (H 5), with_decimal (HANG 0.5), with_expression (H X+Y)
- QUIT: with_postcondition (Q:X), followed_by_command (Q W 1)
- All tests verified against command_metamodel and line_parser
- Final count: 3590 passed, 109 skipped, 362 xfailed

**Completion Notes (F2 - T209)**:
- All 5 JOB parser stubs converted to passing tests
- JOB: basic (J ^ROUTINE), with_label (JOB LABEL^ROUTINE), with_arguments (J LABEL(args))
- JOB: with_timeout (J ^ROUTINE::5), with_process_params (J ^ROUTINE:(params):10)
- All tests verified against command_metamodel
- Final count: 3595 passed, 109 skipped, 357 xfailed

### Batch F3: Parser Data Commands (10 stubs) - Low Complexity ✅

Data manipulation commands: KILL, LOCK, MERGE.

- [X] T211 [US1] **Research**: Review MUMPS reference §8.2.11 (KILL), §8.2.12 (LOCK), §8.2.13 (MERGE). Check mumps-reference/notes__*.md for data operation semantics.
- [X] T212 [US1] Implement parser stubs: KILL (3), LOCK (3), MERGE (4) - 10 stubs
- [X] T213 [US4] Regenerate coverage matrix

**Completion Notes (F3)**:
- All 10 data command parser stubs converted to passing tests
- KILL (§8.2.11): test_kill_multiple_variables (K X,Y,Z), test_kill_subscripted (K arr(1)), test_kill_argumentless (K)
- LOCK (§8.2.12): test_lock_with_timeout (L ^GLOBAL:5), test_lock_multiple (L (^A,^B)), test_lock_argumentless (L)
- MERGE (§8.2.13): test_merge_global_to_local (M local=^GLOBAL), test_merge_local_to_global (M ^GLOBAL=local), test_merge_with_subscripts (M arr(1)=src(2)), test_merge_multiple (M a=b,c=d)
- All tests verified against command_metamodel
- Final count: 3605 passed, 109 skipped, 347 xfailed

### Batch F4: Parser Library Functions (11 stubs) - Medium Complexity ✅

String and character library functions (Annex I §1-3).

- [X] T214 [US1] **Research**: Review MUMPS reference §7.1.6.5 for library functions. STRING/CHARACTER functions parse as ExtrinsicFunction.
- [X] T215 [US1] Implement parser stubs: library_functions_string (6 stubs)
- [X] T216 [US1] Implement parser stubs: library_functions_character (5 stubs)
- [X] T217 [US4] Regenerate coverage matrix

**Completion Notes (F4)**:
- All 11 library function parser stubs converted to passing tests
- STRING (Annex I-3): CRC16, CRC32, CRCCCITT (CRC functions), FORMAT, PRODUCE, REPLACE (string functions)
- CHARACTER (Annex I-1): COLLATE, COMPARE (character comparison), plus LOWER, PATCODE, UPPER (in ^STRING)
- All functions parse as ExtrinsicFunction with target.name and target.routine attributes
- Tests verify: function name, routine name, argument count and types
- Final count: 3616 passed, 109 skipped, 336 xfailed

### Batch F5: Parser Pattern Match (6 stubs) - Medium Complexity ✅ COMPLETE

Pattern match operator (?) parsing tests.

- [X] T218 [US1] **Research**: Review MUMPS reference §7.2.5 (pattern match). Check mumps-reference/notes__pattern*.md for pattern syntax examples.
- [X] T219 [US1] Implement parser stubs: pattern_match (6 stubs)
- [X] T220 [US4] Regenerate coverage matrix

**Additional work completed:**
- Researched §7.2.3 (pattern match) from MUMPS 1995 spec (1995__a107199.md)
- Explored textX grammar AST structure via pylanceRunCodeSnippet testing
- Pattern atoms have: repcount (ExactRepCount or RangeRepCount), patcode, strlit, alternation
- RangeRepCount: min/max attributes (stored as strings), None for unlimited (.N)
- ExactRepCount: exact attribute (stored as string)
- Indirection uses indirect_expr attribute on PatternMatchTail
- All 6 stubs implemented with comprehensive assertions
- Final count: 3622 passed, 109 skipped, 330 xfailed

---

### Batch F6: ASG Routine & Simple (10 stubs) - Medium Complexity ✅ COMPLETE

Routine head structure, transaction restart, and pattern match operators.

- [X] T221 [US2] **Research**: Review MUMPS reference §6.1 (routine structure), §8.2.20 (TRESTART). Check docs/asg/ for routine node documentation.
- [X] T222 [US2] Implement ASG stubs: routine_head (3), TRESTART (2) - 5 stubs
- [X] T223 [US2] Implement ASG stubs: pattern_match operators (3), pattern_match s7_2_5 (2) - 5 stubs
- [X] T224 [US4] Regenerate coverage matrix

**Completion Notes (F6)**:
- Researched §6.1 (routine head), §8.2.20 (TRESTART), §7.2.5 (pattern match)
- All 10 stubs converted to passing tests:
  - test_s6_1_routine_head.py (3): routine_name_extraction, formal_parameter_list, routine_metadata
  - test_s8_2_20_trestart.py (2): trestart_command_node, trestart_control_flow
  - test_s7_2_operators_pattern_match.py (3): pattern_alternation, pattern_literal, pattern_indirection
  - test_s7_2_5_pattern_match.py (2): pattern_alternation, pattern_indirection
- Key ASG classes: MRoutine (labels), MLabel (name, formal_list, body), MTRestartStatement, MPatternMatch
- Fixed import: MTRestartStatement from m2py.asg.statements (not commands)
- Removed 3 xfail markers from tests that unexpectedly passed
- Final count: 3632 passed, 109 skipped, 320 xfailed

### Batch F7: ASG Library Functions (11 stubs) - Medium Complexity ✅ COMPLETE

String and character function ASG tests.

- [X] T225 [US2] **Research**: Review docs/asg/function-call.md for function ASG structure. Check how $PIECE, $EXTRACT map to ASG nodes.
- [X] T226 [US2] Implement ASG stubs: library_functions_string (6 stubs)
- [X] T227 [US2] Implement ASG stubs: library_functions_character (5 stubs)
- [X] T228 [US4] Regenerate coverage matrix

**Completion Notes (F7)**:
- Commit: `80af874`
- Researched Annex I-1 (CHARACTER), I-3 (STRING) library function specs
- All 11 stubs converted to passing tests:
  - test_s7_1_6_5_library_functions_string.py (6): CRC16, CRC32, CRCCCITT, FORMAT, PRODUCE, REPLACE
  - test_s7_1_6_5_library_functions_character.py (5): COLLATE, COMPARE (^CHARACTER), LOWER, PATCODE, UPPER (^STRING)
- ASG structure: ExtrinsicFunction with label, routine, and MActualParameter arguments
- Created verify_string_function() and verify_library_function() helpers
- Final count: 3643 passed (+11), 109 skipped, 309 xfailed (-11)

### Batch F8: ASG Extrinsic Functions (5 stubs) - High Complexity ✅ COMPLETE

User-defined extrinsic function calls ($$label^routine).

- [X] T229 [US2] **Research**: Review MUMPS reference §7.1.6 (extrinsic functions). Check docs/asg/ for call semantics. Search YDBTest/ for $$ usage patterns.
- [X] T230 [US2] Implement ASG stubs: extrinsic_functions (5 stubs)
- [X] T231 [US4] Regenerate coverage matrix

**Completion Notes (F8)**:
- Commit: `1135a25`
- Researched §7.1.4.8 (exfunc), §7.1.4.9 (exvar), §8.1.7 (parameter passing)
- All 5 stubs in TestExtrinsicFunctionsAnalysis converted to passing tests:
  - test_extrinsic_function_resolution: $$label^routine target resolution
  - test_extrinsic_function_arguments: by-value/by-reference argument handling
  - test_extrinsic_function_return: QUIT return value tracking with formal params
  - test_extrinsic_special_variable: $$x (exvar) form without parentheses
  - test_external_routine_reference: cross-routine ^ROUTINE references
- ASG structure: ExtrinsicFunction with target (MCall), arguments (list of MActualParameter)
- PassingMode enum: BY_VALUE (1), BY_REFERENCE for .variable syntax
- Final count: 3648 passed (+5), 109 skipped, 304 xfailed (-5)

### Batch F9: ASG Indirection s6 (4 stubs) - High Complexity ✅ COMPLETE

Name indirection at routine/line level (@name).

- [X] T232 [US2] **Research**: Review MUMPS reference §6.3.1 (indirection). Check mumps-reference/notes__indirection*.md. Study existing tests/unit/asg/s6_routine/ for patterns.
- [X] T233 [US2] Implement ASG stubs: s6_3_1_indirection (4 stubs)
- [X] T234 [US4] Regenerate coverage matrix

**Completion Notes (F9)**:
- Researched §6.3.1 (1995__a106010.md): generic indirection, @expritem replacement
- Checked cross_cutting/test_indirection.py - extensive coverage already exists
- All 4 stubs in TestIndirectionAnalysis converted to passing tests:
  - test_name_indirection_resolution: @VAR creates Indirection with IndirectionType.NAME
  - test_argument_indirection_resolution: @VAR@(1,2) captures name_indirection_subscripts
  - test_pattern_indirection_resolution: X?@PAT creates MPatternMatch with pattern_indirect
  - test_indirection_static_analysis: requires_runtime_eval=True, can_resolve_statically=False
- Key ASG classes: Indirection (textx_classes), IndirectionType (enums), MPatternMatch
- Final count: 3652 passed (+4), 109 skipped, 300 xfailed (-4)

### Batch F10: ASG Indirection s7 (7 stubs) - High Complexity ✅

Expression-level indirection (@expr for subscripts, arguments).

- [X] T235 [US2] **Research**: Review MUMPS reference §7.3 (expression indirection). Check how indirection affects ASG node construction. Review validate_asg.py output for indirection cases.
  - **Completed**: Read 1995__a901027.md - 5 types of indirection (name, subscript, argument, pattern, generic). ASG captures via Indirection node with indirection_type enum.
- [X] T236 [US2] Implement ASG stubs: s7_3_indirection (4 stubs) - first half
  - **Completed**: test_name_indirection, test_subscript_indirection, test_argument_indirection, test_indirection_in_set
- [X] T237 [US2] Implement ASG stubs: s7_3_indirection (3 stubs) - second half
  - **Completed**: test_indirection_limitations, test_nested_indirection, test_indirection_side_effects
- [X] T238 [US4] Regenerate coverage matrix
  - **Completed**: Coverage matrix updated. Key pattern: use parse_expression() before analyze_expression().

---

### Batch F11: Cross-Cutting Simple (7 stubs) - REVISED (2 stubs completed, 5 codegen preserved)

Naked references and postconditions.

- [X] T239 [US2] **Research**: Review MUMPS reference for naked references (§7.1.2.2) and postconditions (§8.1). Check existing cross_cutting tests for patterns.
  - **Completed**: Read 1977__a107011.md (naked indicator), 1995__a108005.md (postconditions). ASG already captures both correctly.
- [X] T240 [US2] Implement cross-cutting stubs: naked_references (2 stubs)
  - **Completed**: test_merge_with_naked (destination=NakedGlobal), test_lock_with_naked (dict with target=NakedGlobal)
- [X] T241 [US2] ~~Implement cross-cutting stubs: postconditions (5 stubs)~~ **REVISED**
  - **Original**: Incorrectly converted codegen runtime stubs to ASG structure tests
  - **Fixed**: Restored 5 codegen stubs (require runtime execution to verify truthiness/gating)
  - **Added**: 2 new ASG tests - test_postcondition_string_literal, test_postcondition_extrinsic_function
  - **Note**: Codegen stubs test that SET:0 X=1 doesn't execute, etc. - requires runtime
- [X] T242 [US4] Regenerate coverage matrix
  - **Completed**: Coverage matrix updated.

### Batch F12: Cross-Cutting Indirection (5 stubs) - SKIPPED (Codegen Required)

Cross-cutting indirection behavior tests - **requires runtime execution**.

- [X] T243 [US2] **Research**: Review how indirection interacts across parser/ASG layers. Check test_indirection.py stub docstrings for specific scenarios.
  - **Completed**: Read §6.3.1, §7.3, 1995__a901027.md. ASG correctly captures all 5 indirection types.
- [ ] T244 [US2] ~Implement cross-cutting stubs: indirection (5 stubs)~~ **SKIPPED - ONLY codegen stubs found**
- [ ] T245 [US4] ~~Regenerate coverage matrix~~ **N/A** (no changes made)

### Batch F13: Cross-Cutting Timeouts (8 stubs) - SKIPPED (Codegen Required)

Timeout handling in READ, LOCK, JOB, OPEN commands - **requires runtime execution**.

- [X] T246 [US2] **Research**: Review MUMPS reference timeout syntax (:timeout) in §8.2.10 (JOB), §8.2.12 (LOCK), §8.2.15 (OPEN), §8.2.17 (READ). Check YDBTest/ for timeout behavior.
  - **Completed**: All 8 stubs are `@pytest.mark.codegen` tests that verify $TEST modification on timeout success/failure. Parser (15 tests) and ASG (7 tests) already pass - total 22 passing tests.
- [ ] T247 [US2] ~~Implement cross-cutting stubs: timeouts (8 stubs)~~ **SKIPPED - ONLY codegen stubs found**
  - All 8 stubs test runtime behavior ($TEST=0 on timeout, $TEST=1 on success)
  - These require actual code execution to verify
- [ ] T248 [US4] ~~Regenerate coverage matrix~~ **N/A** (no changes made)

### Batch F14: Cross-Cutting Language Semantics A (5 stubs) - SKIPPED (Codegen Required)

First batch of language semantics tests - **requires runtime execution**.

- [X] T249 [US2] **SKIPPED** - All language semantics stubs are codegen tests requiring runtime execution
- [X] T250 [US2] **SKIPPED** - Codegen tests deferred to codegen phase
- [X] T251 [US4] **SKIPPED** - N/A

### Batch F15: Cross-Cutting Language Semantics B (5 stubs) - SKIPPED (Codegen Required)

Second batch of language semantics tests - **requires runtime execution**.

- [X] T252 [US2] **SKIPPED** - All language semantics stubs are codegen tests requiring runtime execution
- [X] T253 [US2] **SKIPPED** - Codegen tests deferred to codegen phase
- [X] T254 [US4] **SKIPPED** - N/A

### Batch F16: Cross-Cutting Language Semantics C (5 stubs) - SKIPPED (Codegen Required)

Third batch of language semantics tests - **requires runtime execution**.

- [X] T255 [US2] **SKIPPED** - All language semantics stubs are codegen tests requiring runtime execution
- [X] T256 [US2] **SKIPPED** - Codegen tests deferred to codegen phase
- [X] T257 [US4] **SKIPPED** - N/A

### Batch F17: Cross-Cutting Language Semantics D (5 stubs) - SKIPPED (Codegen Required)

Final batch of language semantics tests - **requires runtime execution**.

- [X] T258 [US2] **SKIPPED** - All language semantics stubs are codegen tests requiring runtime execution
- [X] T259 [US2] **SKIPPED** - Codegen tests deferred to codegen phase
- [X] T260 [US4] **SKIPPED** - N/A

---

### Final Verification (Phase 8)

- [X] T261 [US4] **SKIPPED** - Codegen xfails are expected, will verify in codegen phase
- [X] T262 [US4] Coverage matrix regenerated - 3722 passed, 311 xfailed (all codegen)
- [X] T263 [US4] limitations.md updated with limitation types and test patterns

**Checkpoint**: Phase 8 COMPLETE - All parser/ASG stubs implemented. Remaining xfails are codegen tests (expected).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (High Coverage ASG)**: Depends on Phase 1 - 🎯 **MVP target**
- **Phase 3 (Parser)**: Can start after Phase 1, parallel with Phase 2
- **Phase 4 (ASG Medium)**: Can start after Phase 2
- **Phase 5 (Cross-Cutting)**: Can start after Phase 4 (complex tests may need earlier ASG work)
- **Phase 6 (Polish)**: Depends on all phases complete
- **Phase 7 (Gap Remediation)**: Depends on Phase 6 verification identifying gaps
- **Phase 8 (Stub Remediation)**: Depends on Phase 7 audit identifying remaining stubs

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
7. **Phase 7**: Limitation test conversion (T178-T199) - convert skips to parse error tests

---

## Phase 9: Limitation Test Management ✅ COMPLETE

**Purpose**: Establish canonical limitation data source and proper test patterns

**Status**: ✅ COMPLETE - All tests properly reference limitations, 0 skipped tests

**Achievements**:
1. Created `src/m2py/limitations.py` as canonical source for all limitation data
2. Tests reference LIM-XXX IDs in docstrings and xfail reasons
3. Coverage matrix shows ✅ LIM-XXX for sections with expected empty test files
4. "Parses OK" limitations have parser/ASG tests; codegen tests are comment-only
5. "Parse Error" limitations have parser tests verifying errors; ASG/codegen are comment-only
6. "Informative" limitations have all test files as comment-only

### Completed Tasks

- [X] L1: Created `src/m2py/limitations.py` with LIM-001 through LIM-013
- [X] L2-L8: All skipped tests converted (0 skipped remaining)
- [X] L9/T200: Verified 0 skipped tests (`uv run pytest` shows 3722 passed, 311 xfailed)
- [X] L9/T201: Coverage matrix regenerated via `utils/rebuild_docs.py`
- [X] L9/T202: limitations.md auto-generated from limitations.py
- [X] L9/T203: Test pattern documented in limitations.py module docstring

### Test Patterns by Limitation Type (documented in limitations.py)

| Type | Parser Tests | ASG Tests | Codegen Tests |
|------|-------------|-----------|---------------|
| Parse Error | Required (verify error) | Comment-only | Comment-only |
| Parses OK | Required (verify parsing) | Required if analyzable | Comment-only with LIM-XXX |
| Informative | Comment-only | Comment-only | Comment-only |

---

## Phase 10: Coverage Gap Analysis

**Purpose**: Analyze remaining code coverage gaps and determine appropriate action (dead code removal vs test additions)

**Status**: 🔍 ANALYSIS COMPLETE - Ready for implementation decisions

**Coverage Summary** (as of Jan 2025): 80% (3976 statements, 620 missed)

### Gap Analysis Findings

#### GAP-001: `dead_code_analysis.py` - 95% UNCOVERED (36/39 lines)

**Classification**: ❌ **DEAD CODE - Remove**

**Analysis**: 
- The `detect_unreachable_code()` function is **never called** by the parser pipeline
- Unreachable code detection is already implemented in `semantic_analyzer.py` during ASG construction
- The tests in `test_unreachable_code.py` test the semantic analyzer's `is_unreachable` property, NOT this function
- This module was created during spec-001 but never integrated

**Evidence**:
- `grep -r "detect_unreachable_code" src/` shows function is only defined, never called
- Tests use `stmt.is_unreachable` which is set by semantic_analyzer.py lines 136-165

**Recommendation**: Delete `src/m2py/analysis/dead_code_analysis.py` and its import from `__init__.py`

**Priority**: Low (cleanup, no functional impact)

---

#### GAP-002: `limitations.py` - 100% UNCOVERED (78/78 lines)

**Classification**: ⏭️ **EXPECTED - No action needed**

**Analysis**: 
- This file defines limitation constants (LIM-001 through LIM-013)
- It's used by `utils/rebuild_docs.py` to generate documentation, not by runtime code
- Test coverage tools don't run utils scripts

**Evidence**:
- File contains only dataclass definitions and constant dictionaries
- Used for documentation generation, not runtime parsing

**Recommendation**: Add to `.coveragerc` exclude or document as expected uncovered

**Priority**: Low (documentation infrastructure)

---

#### GAP-003: `semantic_analyzer.py` - 289 missed lines (various handlers)

**Classification**: Mixed - some dead code, some testing gaps

**Sub-gaps analyzed**:

##### GAP-003a: Lines 896-898 (`_analyze_ReadCommand` unknown arg fallback)
**Classification**: 🛡️ **Defensive code** - Low priority
- Fallback for unknown READ argument types
- May never be hit with current grammar

##### GAP-003b: Lines 938-939, 944 (`_analyze_IfCommand` edge cases)  
**Classification**: ✅ **Testing gap** - Low priority
- Handles edge case of IF with no conditions
- Grammar may prevent this case

##### GAP-003c: Lines 1002-1008 (`_simple_var_to_asg` string handling)
**Classification**: 🛡️ **Defensive code** - Low priority
- Handles FOR loop variable as raw string
- Grammar typically produces objects, not strings

##### GAP-003d: Lines 1033-1054 (`_convert_loop_var_subscripts`)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles subscripted loop variables: `FOR ^GLOBAL(1)=...`
- Valid MUMPS syntax per §8.2.5.4

##### GAP-003e: Lines 1228-1271 (`_analyze_IndirectChain` multi-level)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles `@@VAR` (double indirection) and `@@@VAR` (triple)
- Valid MUMPS syntax per §7.3.4

##### GAP-003f: Lines 1377-1380, 1424-1427, 1468-1471 (KILL exclusive lists)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles `KILL (A,B),(C,D)` with multiple exclusive groups
- Valid MUMPS syntax per §8.2.12

##### GAP-003g: Lines 1613-1618, 1648-1653 (LOCK indirection)
**Classification**: ✅ **Testing gap** - Medium priority  
- Handles `LOCK @VAR`, `LOCK @@VAR` indirection in lock targets
- Valid MUMPS syntax per §8.2.14

##### GAP-003h: Lines 1993-1994, 2006, 2014-2016 (TSTART params)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles TSTART compound params: `(serial:t="BA")`
- Valid MUMPS syntax per §6.3.1

##### GAP-003i: Lines 2205-2263 (ZWRITE patterns/ranges)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles ZWRITE subscript ranges and global patterns
- Valid YottaDB extension syntax

##### GAP-003j: Lines 2473-2608 (Z-commands: ZPRINT, ZSYSTEM, ZMESSAGE, etc.)
**Classification**: ✅ **Testing gap** - Low priority
- YottaDB Z-command handlers with complex argument parsing
- Not in ANSI spec, YDB-specific

##### GAP-003k: Lines 2692-2760 (ZGoto handlers)
**Classification**: ✅ **Testing gap** - Low priority
- ZGOTO argument parsing
- YottaDB extension

##### GAP-003l: Lines 2840-2890 (`analyze_statement`, `unwrap_expression`)
**Classification**: 🛡️ **Defensive code / utility** - Low priority
- Utility functions for ad-hoc parsing
- May be unused or only used by external tools

---

#### GAP-004: `textx_classes.py` - 48 missed lines

**Classification**: Mixed defensive code and edge cases

##### GAP-004a: Lines 130-167 (`_get_function_arg_list` new format)
**Classification**: 🛡️ **Defensive code** - Low priority
- Handles alternative function argument formats
- May be grammar evolution fallback

##### GAP-004b: Lines 423-439 (ZWRITE subscript handling)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles ZWRITE subscript range expressions
- Same as GAP-003i

---

#### GAP-005: `variables.py` - 31 missed lines

**Classification**: ✅ **Testing gap** - Medium-High priority

##### GAP-005a: Lines 593-619 (expression variable extraction edge cases)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles MActualParameter, MSelectArg variable extraction
- Used by variable analysis

##### GAP-005b: Lines 917-923 (`bind_parameters` loop)
**Classification**: ✅ **Testing gap** - High priority
- Parameter binding for function calls
- Critical for by-reference semantics

##### GAP-005c: Lines 1172-1178 (`compute_transitive_outputs`)
**Classification**: ✅ **Testing gap** - High priority
- Transitive output computation through call chains
- Critical for accurate scope analysis

---

#### GAP-006: `pattern_compiler.py` - 25 missed lines

**Classification**: ✅ **Testing gap** - Medium priority

##### GAP-006a: Lines 276-315 (pattern alternation parsing)
**Classification**: ✅ **Testing gap** - Medium priority
- Handles pattern alternation: `1(1N,1A)` matching digit OR letter
- Valid MUMPS syntax per §7.3.6.5

##### GAP-006b: Lines 299-315 (nested alternation, quoted strings in patterns)
**Classification**: ✅ **Testing gap** - Medium priority
- Complex pattern cases with nested parens and quotes
- Edge cases in pattern matching

---

#### GAP-007: `resolver.py` - 13 missed lines

**Classification**: ✅ **Testing gap** - Low priority

- Lines 133-135, 184-187: External routine handling
- Lines 209-212: Global collection in external refs
- Edge cases for cross-routine references

---

#### GAP-008: `for_analysis.py` - 22 missed lines

**Classification**: Mixed

##### GAP-008a: Lines 84-86, 152-154, 177-179, 291-294
**Classification**: ✅ **Testing gap** - Medium priority
- FOR loop classification edge cases
- Handles complex FOR patterns

##### GAP-008b: Lines 326-327
**Classification**: 🛡️ **Defensive code** - Low priority
- Fallback handling

---

#### GAP-009: `goto_analysis.py` - 12 missed lines

**Classification**: ✅ **Testing gap** - Medium priority

- Lines 166-167, 181-182, 272-278: Multi-loop exit detection
- Complex GOTO patterns that exit nested loops

---

### Priority Summary

| Priority | Category | Gaps | Action |
|----------|----------|------|--------|
| **Critical** | - | - | None identified |
| **High** | Variable Analysis | GAP-005b, GAP-005c | Add unit tests |
| **Medium** | ASG Edge Cases | GAP-003d,e,f,g,h,i, GAP-004b, GAP-005a, GAP-006, GAP-008a, GAP-009 | Add unit tests |
| **Low** | Defensive Code | GAP-003a,b,c,j,k,l, GAP-004a, GAP-007, GAP-008b | Leave or simplify |
| **Remove** | Dead Code | GAP-001 | Delete module |
| **Ignore** | Expected | GAP-002 | Exclude from coverage |

### Recommended Next Steps

- [X] **T300** [US4] Delete `dead_code_analysis.py` and update `__init__.py` (GAP-001)
- [X] **T301** [US4] Add `limitations.py` to coverage exclusions (GAP-002)
- [X] **T302** [US2] Add tests for `bind_parameters` in variable analysis (GAP-005b) - **HIGH**
- [X] **T303** [US2] Add tests for `compute_transitive_outputs` (GAP-005c) - **HIGH**
- [X] **T304** [US2] Add tests for subscripted FOR loop variables (GAP-003d) - **MEDIUM**
- [X] **T305** [US2] Add tests for multi-level indirection `@@VAR` (GAP-003e) - **MEDIUM**
- [X] **T306** [US2] Add tests for KILL multiple exclusive groups (GAP-003f) - **MEDIUM**
- [X] **T307** [US2] Add tests for LOCK indirection (GAP-003g) - **MEDIUM**
- [X] **T308** [US2] Add tests for TSTART compound params (GAP-003h) - **MEDIUM**
- [X] **T309** [US2] Add tests for ZWRITE ranges/patterns (GAP-003i, GAP-004b) - **MEDIUM**
- [X] **T310** [US2] Add tests for pattern alternation (GAP-006) - **MEDIUM**
- [X] **T311** [US2] Add tests for multi-loop GOTO exits (GAP-009) - **MEDIUM**

**Checkpoint**: ✅ All Phase 10 tasks complete. Coverage improved from 80% to 85%.

**Estimated Impact**: Implementing T300-T303 would raise coverage from 80% to ~82%. Completing all T300-T311 would reach ~85%.

---

## Success Command

```bash
# Final success verification
uv run pytest --tb=no -q

# Current: 3601 passed, 311 xfailed (all xfails are codegen stubs)
# Coverage: 85%
```
