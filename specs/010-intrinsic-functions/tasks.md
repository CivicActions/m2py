# Tasks: Intrinsic Functions

**Input**: Design documents from `/specs/010-intrinsic-functions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests included as implementation verification (stubs already exist to replace).

**Organization**: Tasks grouped by user story to enable independent implementation and testing. Complex foundational work prioritized first (dispatcher, runtime helpers) before individual functions.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Core Infrastructure)

**Purpose**: Create foundational infrastructure needed by ALL intrinsic functions

- [ ] T001 Create MRuntimeError exception class in src/m2py/runtime/exceptions.py
- [ ] T002 Export MRuntimeError from src/m2py/runtime/__init__.py
- [ ] T003 Add INTRINSIC_GENERATORS dispatch table in src/m2py/codegen/expressions.py
- [ ] T004 Add generate_intrinsic_function() dispatcher in src/m2py/codegen/expressions.py
- [ ] T005 Update generate_expr() to dispatch MIntrinsicFunction to generate_intrinsic_function() in src/m2py/codegen/expressions.py

---

## Phase 2: Complex Data Functions (P1 - Most Complex First)

**Purpose**: Implement $ORDER and $QUERY first - these are the most complex functions requiring tree traversal algorithms. $DATA already exists from Spec 009.

### User Story 10 - Array Traversal with $ORDER (Priority: P1)

**Goal**: Traverse array subscripts in collation order (forward and reverse)

**Complexity**: High - requires MUMPS collation order, direction parameter, empty-string start convention

- [ ] T006 [US10] Add m_order() helper function in src/m2py/runtime/helpers.py
- [ ] T007 [US10] Add m_order_global() helper for global variables in src/m2py/runtime/helpers.py
- [ ] T008 [US10] Add _gen_order() generator in src/m2py/codegen/expressions.py
- [ ] T009 [US10] Register ORDER/O in INTRINSIC_GENERATORS dispatch table
- [ ] T010 [US10] Replace stub test_function_order in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $ORDER works for local and global arrays, forward and reverse

---

### User Story 11 - Tree Traversal with $QUERY (Priority: P2)

**Goal**: Return full reference of next node in depth-first traversal

**Complexity**: High - requires depth-first tree walk, full reference string construction

- [ ] T011 [US11] Add m_query() helper function in src/m2py/runtime/helpers.py
- [ ] T012 [US11] Add m_query_global() helper for global variables in src/m2py/runtime/helpers.py
- [ ] T013 [US11] Add _gen_query() generator in src/m2py/codegen/expressions.py
- [ ] T014 [US11] Register QUERY/Q in INTRINSIC_GENERATORS dispatch table
- [ ] T015 [US11] Replace stub test_function_query in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $QUERY returns full variable references like "A(1,2)"

---

## Phase 3: $SELECT Function (P1 - Complex Conditional)

### User Story 12 - Conditional Selection (Priority: P1)

**Goal**: Evaluate conditions left-to-right, return value for first true, raise error if none true

**Complexity**: High - requires MSelectArg handling, short-circuit evaluation, SELECTFALSE error

- [ ] T016 [US12] Add _gen_select() generator handling MSelectArg list in src/m2py/codegen/expressions.py
- [ ] T017 [US12] Register SELECT/S in INTRINSIC_GENERATORS dispatch table
- [ ] T018 [US12] Replace stub test_function_select in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [ ] T019 [US12] Add test for SELECTFALSE error when no condition true

**Checkpoint**: $SELECT evaluates conditions and raises MRuntimeError("SELECTFALSE") when none true

---

## Phase 4: Extrinsic Functions (P1 - By-Reference Completion)

### User Story 13 - Extrinsic Functions (Priority: P1)

**Goal**: Complete $$label and $$label^routine support including by-reference parameters

**Complexity**: Medium - extend existing infrastructure, add by-ref parameter handling, $TEST save/restore (FR-025)

- [ ] T020 [US13] Extend _generate_extrinsic_arguments() to handle PassingMode.BY_REFERENCE and ensure $TEST save/restore per FR-025 in src/m2py/codegen/expressions.py
- [ ] T021 [US13] Add tests for by-reference extrinsic parameters in tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py
- [ ] T022 [US13] Add test for internal extrinsic $$label returning value
- [ ] T023 [US13] Add test for external extrinsic $$label^routine

**Checkpoint**: Extrinsic functions work with both by-value and by-reference parameters

---

## Phase 5: Core String Functions (P1)

### User Story 1 - String Length and Piece Count (Priority: P1)

**Goal**: $LENGTH returns character count or piece count

**Complexity**: Low - simple len() and count() operations

- [ ] T024 [P] [US1] Add _gen_length() generator in src/m2py/codegen/expressions.py
- [ ] T025 [P] [US1] Register LENGTH/L in INTRINSIC_GENERATORS dispatch table
- [ ] T026 [US1] Replace stub test_function_length in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $L("HELLO") → 5, $L("A^B^C","^") → 3

---

### User Story 2 - Piece Extraction (Priority: P1)

**Goal**: $PIECE extracts delimited pieces from strings

**Complexity**: Medium - edge cases for out-of-range pieces, ranges

- [ ] T027 [US2] Add m_piece() helper function in src/m2py/runtime/helpers.py
- [ ] T028 [US2] Add _gen_piece() generator in src/m2py/codegen/expressions.py
- [ ] T029 [US2] Register PIECE/P in INTRINSIC_GENERATORS dispatch table
- [ ] T030 [US2] Replace stub test_function_piece in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $P("A^B^C","^",2) → "B", $P("A^B^C","^",2,3) → "B^C"

---

### User Story 3 - Substring Extraction (Priority: P1)

**Goal**: $EXTRACT extracts substrings by position

**Complexity**: Medium - 1-based indexing, edge cases for out-of-range

- [ ] T031 [US3] Add m_extract() helper function in src/m2py/runtime/helpers.py
- [ ] T032 [US3] Add _gen_extract() generator in src/m2py/codegen/expressions.py
- [ ] T033 [US3] Register EXTRACT/E in INTRINSIC_GENERATORS dispatch table
- [ ] T034 [US3] Replace stub test_function_extract in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $E("HELLO",2,4) → "ELL"

---

## Phase 6: Data Functions (P1)

### User Story 8 - Variable Existence Check (Priority: P1)

**Goal**: Integrate existing $DATA with new dispatcher

**Complexity**: Low - $DATA already implemented in Spec 009, just wire to dispatcher

- [ ] T035 [US8] Move _generate_data() logic into _gen_data() following new pattern in src/m2py/codegen/expressions.py
- [ ] T036 [US8] Register DATA/D in INTRINSIC_GENERATORS dispatch table
- [ ] T037 [US8] Replace stub test_function_data in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $D(X) → 0/1/10/11 correctly

---

### User Story 9 - Safe Variable Retrieval (Priority: P1)

**Goal**: $GET retrieves variable with default for undefined

**Complexity**: Medium - must distinguish undefined from empty string

- [ ] T038 [US9] Add m_get() helper function in src/m2py/runtime/helpers.py
- [ ] T039 [US9] Add m_get_global() helper for global variables in src/m2py/runtime/helpers.py
- [ ] T040 [US9] Add _gen_get() generator in src/m2py/codegen/expressions.py
- [ ] T041 [US9] Register GET/G in INTRINSIC_GENERATORS dispatch table
- [ ] T042 [US9] Replace stub test_function_get in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $G(UNDEF,"DEF") → "DEF", $G(DEFINED,"DEF") → actual value

---

## Phase 7: String Search and Transform Functions (P2)

### User Story 4 - Find Substring (Priority: P2)

**Goal**: $FIND locates substring and returns position AFTER match

**Complexity**: Medium - returns position after match, not match position

- [ ] T043 [P] [US4] Add m_find() helper function in src/m2py/runtime/helpers.py
- [ ] T044 [US4] Add _gen_find() generator in src/m2py/codegen/expressions.py
- [ ] T045 [US4] Register FIND/F in INTRINSIC_GENERATORS dispatch table
- [ ] T046 [US4] Replace stub test_function_find in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $F("HELLO","LL") → 5 (position AFTER "LL")

---

### User Story 5 - Character Translation (Priority: P2)

**Goal**: $TRANSLATE performs character-by-character replacement or deletion

**Complexity**: Low - uses Python str.translate()

- [ ] T047 [P] [US5] Add _gen_translate() generator in src/m2py/codegen/expressions.py
- [ ] T048 [US5] Register TRANSLATE/TR in INTRINSIC_GENERATORS dispatch table
- [ ] T049 [US5] Replace stub test_function_translate in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $TR("HELLO","L") → "HEO"

---

### User Story 6 - ASCII/Character Conversion (Priority: P2)

**Goal**: $ASCII and $CHAR convert between characters and codes

**Complexity**: Low - inline ord()/chr() with edge case handling

- [ ] T050 [P] [US6] Add _gen_ascii() generator in src/m2py/codegen/expressions.py
- [ ] T051 [P] [US6] Add _gen_char() generator in src/m2py/codegen/expressions.py
- [ ] T052 [US6] Register ASCII/A and CHAR/C in INTRINSIC_GENERATORS dispatch table
- [ ] T053 [US6] Replace stub test_function_ascii in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [ ] T054 [US6] Replace stub test_function_char in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $A("ABC") → 65, $C(65,66,67) → "ABC"

---

## Phase 8: Numeric Functions (P2)

### User Story 7 - Random Number Generation (Priority: P2)

**Goal**: $RANDOM generates random integers with RANDARGNEG error for invalid input

**Complexity**: Low - inline random.randint() with error check

- [ ] T055 [P] [US7] Add _gen_random() generator in src/m2py/codegen/expressions.py
- [ ] T056 [US7] Register RANDOM/R in INTRINSIC_GENERATORS dispatch table
- [ ] T057 [US7] Replace stub test_function_random in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py
- [ ] T058 [US7] Add test for RANDARGNEG error when limit <= 0

**Checkpoint**: $R(10) → 0-9, $R(0) raises MRuntimeError("RANDARGNEG")

---

## Phase 9: Array Utility Functions (P3)

### User Story 14 - Array Name Functions (Priority: P3)

**Goal**: $NAME, $QLENGTH, $QSUBSCRIPT manipulate array name strings

**Complexity**: Medium - string parsing for name components

- [ ] T059 [P] [US14] Add m_name() helper function in src/m2py/runtime/helpers.py
- [ ] T060 [P] [US14] Add m_qlength() helper function in src/m2py/runtime/helpers.py
- [ ] T061 [P] [US14] Add m_qsubscript() helper function in src/m2py/runtime/helpers.py
- [ ] T062 [US14] Add _gen_name() generator in src/m2py/codegen/expressions.py
- [ ] T063 [US14] Add _gen_qlength() generator in src/m2py/codegen/expressions.py
- [ ] T064 [US14] Add _gen_qsubscript() generator in src/m2py/codegen/expressions.py
- [ ] T065 [US14] Register NAME/NA, QLENGTH/QL, QSUBSCRIPT/QS in INTRINSIC_GENERATORS dispatch table
- [ ] T066 [US14] Add tests for $NAME, $QLENGTH, $QSUBSCRIPT in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $NA(A(1,2,3)) → "A(1,2,3)", $QL("A(1,2,3)") → 3, $QS("A(1,2,3)",2) → "2"

---

## Phase 10: Formatting Functions (P3)

### User Story 15 - String Formatting Functions (Priority: P3)

**Goal**: $JUSTIFY, $FNUMBER, $REVERSE for display formatting

**Complexity**: Medium - $FNUMBER has complex formatting codes

- [ ] T067 [P] [US15] Add _gen_justify() generator in src/m2py/codegen/expressions.py
- [ ] T068 [P] [US15] Add _gen_reverse() generator in src/m2py/codegen/expressions.py
- [ ] T069 [US15] Add m_fnumber() helper function in src/m2py/runtime/helpers.py
- [ ] T070 [US15] Add _gen_fnumber() generator in src/m2py/codegen/expressions.py
- [ ] T071 [US15] Register JUSTIFY/J, FNUMBER/FN, REVERSE/RE in INTRINSIC_GENERATORS dispatch table
- [ ] T072 [US15] Add tests for $JUSTIFY, $FNUMBER, $REVERSE in tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py

**Checkpoint**: $J(12,5) → "   12", $FN(12345.67,",") → "12,345.67", $RE("HELLO") → "OLLEH"

---

## Phase 11: Offset Evaluator Upgrade (Cross-Cutting)

**Purpose**: Enable intrinsic functions in computed offsets like G LABEL+$L(X)

- [ ] T073 Identify offset expression evaluation code in src/m2py/codegen/
- [ ] T074 Update offset evaluator to use generate_expr() for complex expressions
- [ ] T075 Add test for G LABEL+$L(X) computed offset in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py
- [ ] T076 Add test for D LABEL+$P(X,"^",1) computed offset

**Checkpoint**: Computed offsets with function calls produce correct line dispatch

---

## Phase 12: Validation & Polish

**Purpose**: Full validation against YottaDB and documentation updates

- [ ] T077 Run MUGJ V1FNL.m tests and compare with YottaDB output
- [ ] T078 Run MUGJ V1FNE1.m, V1FNE2.m tests for $EXTRACT
- [ ] T079 Run MUGJ V1FNP1.m, V1FNP2.m tests for $PIECE
- [ ] T080 Run MUGJ V1FNF1.m, V1FNF2.m, V1FNF3.m tests for $FIND
- [ ] T081 [P] Update docs/codegen/functions.md with implementation details
- [ ] T082 [P] Remove all @pytest.mark.xfail markers from intrinsic function tests
- [ ] T083 Run full test suite and verify no regressions
- [ ] T084 Validate generated Python with ast.parse() for all test cases

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - blocks everything else
- **Phase 2-4 (Complex P1)**: Depend on Phase 1 - most complex work first
- **Phase 5-6 (Core P1)**: Depend on Phase 1 - can parallel with Phase 2-4
- **Phase 7-8 (P2)**: Depend on Phase 1 - lower priority
- **Phase 9-10 (P3)**: Depend on Phase 1 - lowest priority functions
- **Phase 11 (Offset)**: Depends on Phase 1 and at least one function working
- **Phase 12 (Validation)**: Depends on all phases complete

### Parallel Opportunities

Within Phase 5-6:
- T024-T026 (US1 $LENGTH) can run parallel with T027-T030 (US2 $PIECE)
- T031-T034 (US3 $EXTRACT) can run parallel with T035-T037 (US8 $DATA)

Within Phase 7-8:
- T043-T046 (US4 $FIND) parallel with T047-T049 (US5 $TR)
- T050-T054 (US6 $A/$C) parallel with T055-T058 (US7 $R)

Within Phase 9-10:
- All helpers (T059-T061) can run parallel
- T067-T068 ($J/$RE inline) parallel with T069-T070 ($FN helper)

### User Story Independence

Each user story is independently testable once Phase 1 is complete. Suggested MVP:
1. Phase 1 (Setup) → T001-T005
2. Phase 5 (US1-US3) → Core string functions working
3. Phase 6 (US8-US9) → Data functions working
4. **MVP Checkpoint**: Basic intrinsic functions operational

---

## Implementation Strategy

### Complexity-First Approach (Recommended)

1. **Phase 1**: Create infrastructure (T001-T005)
2. **Phase 2**: Implement $ORDER first (T006-T010) - most complex algorithm
3. **Phase 3**: Implement $SELECT (T016-T019) - complex conditional with error
4. **Phase 4**: Complete extrinsics (T020-T023) - completes partial Spec 008 work
5. **Phase 5-6**: Core P1 functions - high usage, simpler implementation
6. **Phase 7-10**: Remaining functions by priority
7. **Phase 11**: Offset evaluator - cross-cutting concern
8. **Phase 12**: Validation and polish

### Why Complexity First?

- $ORDER and $QUERY require tree traversal algorithms that are harder to get right
- $SELECT has special MSelectArg handling and error semantics
- Simpler functions ($LENGTH, $CHAR) are straightforward once infrastructure exists
- Failing early on complex functions avoids rework

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story can be tested independently after Phase 1
- Verify tests match YottaDB output before marking complete
- Commit after each task or logical group
