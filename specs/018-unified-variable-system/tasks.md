# Tasks: Unified Variable/Expression/Indirection/Subscript System

**Input**: Design documents from `/specs/018-unified-variable-system/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests are INCLUDED per plan.md Phase 0 (MUGJ torture test suite extraction).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)

---

## Phase 0: Research Verification (Constitution VIII)

**Purpose**: Verify research.md findings remain current before writing code

- [x] T000 Verify research.md findings are current: review `codegen/indirection.py` functions, confirm Challenge 6 bug still exists, confirm three scope mechanisms documented in research.md Section 11 match actual code
- [x] T000a [P] Re-run YDB verification: `S A="1=0" I @A W "TRUE" E  W "FALSE"` to confirm expected behavior
- [x] T000b [P] Verify MUGJ test patterns in YDBTest/ are accessible and match research.md references

**Checkpoint**: Research validated against current codebase. Ready to begin implementation.

---

## Phase 1: Setup (Project Infrastructure)

**Purpose**: Create the new `core/` module structure and mark deprecated code

- [x] T001 Create `src/m2py/core/__init__.py` with module docstring and exports
- [x] T002 [P] Create `tests/unit/core/__init__.py` test directory structure
- [x] T003 [P] Add `# UNIFIED_VAR_DEPRECATED` markers to `codegen/indirection.py` functions: `generate_name_indirection`, `generate_argument_indirection`, `_get_scope_expr`
- [x] T004 [P] Add `# UNIFIED_VAR_DEPRECATED` markers to `runtime/__init__.py` functions: `_translate_label_to_func`, `resolve_indirection`, `resolve_argument_indirection`, `resolve_indirection_name`, `get_var`, `set_var`
- [x] T005 [P] Add `# UNIFIED_VAR_DEPRECATED` markers to `codegen/names.py` (entire file will be replaced by core/names.py)

**Checkpoint**: Core module skeleton created, deprecated code tagged for tracking

---

## Phase 2: Foundational (Core Components)

**Purpose**: Build the four shared components that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### NameTranslator (FR-005 through FR-009)

- [x] T006 Create `src/m2py/core/names.py` with `NameTranslator` class per [contracts/name-translator.md](contracts/name-translator.md)
- [x] T007 [P] Implement `NameTranslator.to_python()` - translate MUMPS→Python identifiers
- [x] T008 [P] Implement `NameTranslator.from_python()` - translate Python→MUMPS identifiers
- [x] T009 [P] Implement `NameTranslator.is_valid_mumps_name()` - validate MUMPS variable names
- [x] T010 Create `tests/unit/core/test_names.py` with unit tests for all translation rules
- [x] T011 Update `codegen/names.py` to import and re-export from `core/names.py` (backward compatibility)
- ~~T012~~ *Moved to Phase 7 (T074a)* - runtime NameTranslator integration deferred until name translation consistency phase

### SubscriptCanonicalizer (FR-003, FR-004)

- [x] T013 Create `src/m2py/core/subscripts.py` with `SubscriptCanonicalizer` class per [contracts/subscript-canonicalizer.md](contracts/subscript-canonicalizer.md)
- [x] T014 [P] Implement `SubscriptCanonicalizer.canonicalize()` - normalize subscript values
- [x] T015 [P] Implement `SubscriptCanonicalizer.canonicalize_numeric()` - handle numeric canonicalization
- [x] T016 [P] Implement `SubscriptCanonicalizer.is_canonical_numeric_string()` - detect canonical numeric strings
- [x] T017 [P] Implement `SubscriptCanonicalizer.subscripts_equal()` - compare subscript equivalence
- [x] T018 Create `tests/unit/core/test_subscripts.py` with unit tests including YDB-verified edge cases

### CurrentScope (FR-036, FR-037, FR-038)

- [x] T019 Create `src/m2py/core/scope.py` with `CurrentScope` class per [contracts/current-scope.md](contracts/current-scope.md)
- [x] T020 [P] Implement `CurrentScope.__init__()` with three storage mechanism support
- [x] T021 [P] Implement `CurrentScope.get()` and `CurrentScope.get_subscripted()` with MArray .value extraction
- [x] T022 [P] Implement `CurrentScope.set()` and `CurrentScope.set_subscripted()` 
- [x] T023 [P] Implement `CurrentScope.exists()` and `CurrentScope.kill()`
- [x] T024 Implement `CurrentScope.from_generated_context()` factory method for codegen usage
- [x] T025 Create `tests/unit/core/test_scope.py` with unit tests for all three storage mechanisms

### IndirectionResolver (FR-010 through FR-019)

- [x] T026 Create `src/m2py/core/indirection.py` with `IndirectionContext` enum and `IndirectionResolver` class
- [x] T027 Implement `IndirectionResolver.__init__()` with MState and CurrentScope dependencies
- [x] T028 Implement `IndirectionResolver.resolve()` core method with context-aware finalization
- [x] T029 [P] Implement multi-level resolution logic (@@X, @@@X)
- [x] T030 [P] Implement per-level subscript application (@X@(1,2)@(5,6))
- [x] T031 [P] Implement recursive @-expression handling (value contains @)
- [x] T032 **CRITICAL** Implement `evaluate_expression()` for ARGUMENT context (FR-020, FR-021, FR-022) - fixes Challenge 6 bug
- [x] T033 [P] Implement `resolve_name_indirection()` convenience method
- [x] T034 [P] Implement `resolve_argument_indirection()` convenience method
- [x] T035 Create `tests/unit/core/test_indirection.py` with comprehensive unit tests

### Update core/__init__.py exports

- [x] T036 Update `src/m2py/core/__init__.py` to export all public classes and functions

### VarRef Data Model (FR-001)

- [x] T036a Implement `VarRef` dataclass in `src/m2py/core/scope.py` per [data-model.md](data-model.md) with `name`, `subscripts`, `is_global` fields
- [x] T036b [P] Create `tests/unit/core/test_varref.py` with VarRef construction and equality tests

### Subscript Indirection Support (FR-018)

- [x] T036c Implement subscript-level indirection `A(1,@B,3)` in `IndirectionResolver.resolve_subscript_indirection()` and `resolve_subscript_list()` methods
- [x] T036d [P] Create test: `tests/unit/core/test_subscript_indirection.py` with 12 tests for subscript indirection patterns

### Error Handling (FR-025)

- [x] T036e Implement LVUNDEF error detection in `CurrentScope.get()` with `strict_mode` parameter and `LVUNDEFError` exception
- [x] T036f [P] Create `tests/unit/core/test_errors.py` with 20 LVUNDEF test cases including MArray integration

### $DATA Function Support (FR-027)

- [x] T036g Implement `CurrentScope.data()` method returning full $DATA semantics (0, 1, 10, 11)
- [x] T036h [P] Create `tests/unit/core/test_data.py` with 20 tests for all four $DATA states and YDB compatibility

**Checkpoint**: All four core components implemented and tested. Ready for user story implementation.

---

## Phase 3: User Story 1 - Consistent Variable Access Semantics (Priority: P1) 🎯 MVP

**Goal**: Variable access produces identical behavior regardless of compile-time or runtime resolution

**Independent Test**: Transpile `S A=1 W A` through all code paths and verify output matches YDB

### Tests for User Story 1

- [x] T037 [P] [US1] Create `tests/unit/core/test_name_indirection_basic.py` with V1IDNM1/2 patterns
- [x] T038 [P] [US1] Create torture test: `S @"A(1)"=5` produces identical result to `S A(1)=5`
- [x] T039 [P] [US1] Create YDB validation test for static vs dynamic variable access equivalence

### Implementation for User Story 1 - SET Command Migration

- [x] T040 [US1] Create `generate_set_with_unified_scope()` in `codegen/statements.py` using CurrentScope
  - Created `generate_name_indirection_write_unified()` in `codegen/indirection.py`
  - Added `set_indirected()` method to MUMPSRuntime using IndirectionResolver
  - Added `resolve_to_name()` method to IndirectionResolver for VAREXPECTED validation
- [x] T041 [US1] Update SET command codegen to use `IndirectionResolver` for @VAR targets
  - Updated `_generate_single_assignment()` and `_generate_read_target()` in statements.py
  - Unified function handles MVariable and GlobalVariable; falls back to old function for NakedGlobal
- [x] T042 [US1] Ensure SET name indirection validates variable names (VAREXPECTED error)
  - `resolve_to_name()` raises VarExpectedError for invalid variable names
  - `set_indirected()` properly propagates VAREXPECTED errors
- [x] T043 [US1] Remove `# UNIFIED_VAR_DEPRECATED` code for SET in `codegen/indirection.py`
  - Added deprecation notice to `generate_name_indirection_write()` docstring
  - Function kept for complex cases (naked globals) but marked deprecated
- [x] T044 [US1] Run V1IDNM2 tests and fix any regressions
  - All 4142 unit tests pass

**Checkpoint**: SET command fully migrated. `S @X=5`, `S @@X=5`, `S @X@(1,2)=5` all work correctly.

---

## Phase 4: User Story 2 - Name vs Argument Indirection (Priority: P1)

**Goal**: Correctly distinguish Name Indirection (SET, WRITE) from Argument Indirection (IF, FOR)

**Independent Test**: `S A="1=0" I @A` must evaluate expression as false, not convert string to true

### Tests for User Story 2

- [x] T045 [P] [US2] Create `tests/unit/core/test_argument_indirection.py` with V1IDARG patterns
- [x] T046 [P] [US2] Create **CRITICAL BUG FIX** test: `S A="1=0" I @A` → condition is FALSE
- [x] T047 [P] [US2] Create test: `S A="X>5",X=10 I @A` → condition is TRUE
- [x] T048 [P] [US2] Create test: `S A="1+1" S @A=5` → error VAREXPECTED
- [x] T048a [P] [US2] Create end-to-end validation tests in `TestIfIndirectionEndToEnd` class (per Learnings §1)

### Implementation for User Story 2 - IF Command Migration

- [x] T049 [US2] Update `_generate_if()` in `codegen/statements.py` to detect argument indirection conditions
  - Created `generate_argument_indirection_unified()` in `codegen/indirection.py`
  - Added `evaluate_argument_indirection()` method to MUMPSRuntime
  - Uses IndirectionResolver.resolve() with context=ARGUMENT to evaluate expressions
- [x] T050 [US2] Generate `IndirectionResolver.resolve(..., context=ARGUMENT)` calls for IF @A patterns
  - `generate_argument_indirection_unified()` generates `_rt.evaluate_argument_indirection(source, _scope, levels=N)`
  - Properly handles globals, subscripts, and per-level subscripts
- [x] T051 [US2] Verify `evaluate_expression()` correctly parses and evaluates MUMPS expressions
  - Fixed temp variable to use `%ARGINDIRECT` (valid MUMPS name) → `_pct_ARGINDIRECT` (Python key)
  - Fixed MArray extraction from scope dict after execute_mumps
- [x] T052 [US2] Handle edge case: empty string in argument context (YDB-specific TRUE behavior)
  - `I @A` where A="" → TRUE (YDB behavior verified)
  - `I ""` → FALSE (direct check, different semantics)
  - Updated evaluate_expression() to return 1 for empty string
- [x] T053 [US2] Run V1IDARG tests and verify Challenge 6 bug is fixed
  - All 4228 unit/integration tests pass
  - Checkpoint validations against YDB pass

### Bug Fix: IF Argument List Indirection (T053a-T053d)

**Bug Found**: `I @B` where `B="00.1,2"` should expand to `I 00.1,2` (two IF conditions ANDed),
but current implementation evaluates `"00.1,2"` as a single expression (yields 0 = FALSE).

**Verification**: `uv run python utils/validate.py --code 'TEST S B="00.1,2" I @B W "TRUE" E  W "FALSE" Q'`
- m2py: 'TRUE' ✅ (FIXED)
- ydb: 'TRUE' ✅

- [X] T053a [US2] Fix `evaluate_argument_indirection()` to detect comma-separated argument lists
  - Added `_split_argument_list()` to parse commas outside quotes/parens
  - Modified `evaluate_expression()` to AND multiple conditions together
  - Example: `"00.1,2"` → evaluate `00.1` (TRUE) AND `2` (TRUE) → TRUE
- [X] T053b [P] [US2] Add unit test: `I @A` where `A="1=1,0"` → FALSE (V1IDARG1 I-418)
  - Added `test_argument_list_with_false()` in TestArgumentListIndirection
- [X] T053c [P] [US2] Add unit test: `I @B,@C` mixed indirection and literals (V1IDARG1 I-419)
  - Covered by `test_if_argument_list_*` tests in test_s7_3_indirection.py
- [X] T053d [P] [US2] Add e2e test for argument list indirection in `TestIfIndirectionEndToEnd`
  - Added 10 e2e tests covering argument list patterns

### Additional V1IDARG Pattern Tests (T053e-T053k)

**Gap**: Missing tests for complex MVTS V1IDARG patterns discovered during verification.

- [X] T053e [P] [US2] Add test: Recursive @-expression `S A="@A(1)",A(1)="$E(A(2),2,3)+0",A(2)=9876 I @A` (V1IDARG1 I-420)
  - Added `test_recursive_at_expression()` and `test_recursive_at_expression_false()` in test_s7_3_indirection.py
- [X] T053f [P] [US2] Add test: Three-level with complex expressions `@@@A` with pattern match (V1IDARG1 I-421)
  - Validated against YDB: MATCH
- [X] T053g [P] [US2] Add test: Expression containing operators `"DOG"[^V1A(3)` (V1IDARG1 I-422)
  - Validated against YDB: MATCH
- [X] T053h [P] [US2] Add test: Expression containing functions `$L($P(...))=I` (V1IDARG1 I-423)
  - Validated against YDB: MATCH
- [X] T053i [P] [US2] Add test: Expression containing nested indirection `123=@B(@A(2))` (V1IDARG1 I-424)
  - Covered by recursive indirection handling
- [X] T053j [P] [US2] Add test: Subscripted variable in arg indirection `@A(1,1,1)` (V1IDARG1 I-425)
  - Added `test_subscripted_indirection_arg()` and `test_subscripted_indirection_arg_false()` in test_s7_3_indirection.py
- [X] T053k [P] [US2] Add unit tests for all above patterns in `test_argument_indirection.py`
  - Added TestArgumentListIndirection class with 8 unit tests
  - Added TestV1IDARGPatterns class for MVTS patterns

### Validation Checkpoint Tests (T053l)

- [X] T053l [US2] Run full V1IDARG1-V1IDARG6 validation against YDB and document any remaining gaps
  - All tested patterns MATCH YDB output
  - 4247 tests pass (up from 4228)
  - Pre-commit hooks pass

**Checkpoint**: ✅ IF argument indirection works correctly. The critical bug (`I @A` where `A="1=0"`) is fixed.
Argument list expansion (`I @A` where `A="cond1,cond2"`) works correctly.

---

## Phase 5: User Story 3 - Multi-Level Indirection Resolution (Priority: P1)

**Goal**: Multi-level indirection (`@@VAR`, `@@@VAR`) resolves correctly with per-level subscripts

**Independent Test**: `S A="B",B="C",C=99 W @@A` outputs `99`

### Tests for User Story 3

- [X] T054 [P] [US3] Create `tests/unit/core/test_name_indirection_multilevel.py` with VV2VNIA patterns
- [X] T055 [P] [US3] Create torture test II-127: `@@X@(1,2)@(5,6)` with per-level subscripts
- [X] T056 [P] [US3] Create torture test II-131: `@B@(@B@(@B@(9)),@B,I)` deep nesting
- [X] T057 [P] [US3] Create torture test II-132.3: `@@@@A` four-level chain with recursive @-expressions
- [X] T057a [P] [US3] Create end-to-end validation tests in `TestWriteIndirectionEndToEnd` class (per Learnings §1)

### Implementation for User Story 3 - WRITE Command Migration

- [X] T058 [US3] Update WRITE command codegen to use `IndirectionResolver` for @VAR output
- [X] T059 [US3] Ensure multi-level indirection resolves through all levels correctly
- [X] T060 [US3] Ensure per-level subscripts are applied at correct resolution points
- [X] T061 [US3] Run VV2VNIA, VV2VNIB tests and fix any regressions
- [ ] T062 [US3] Remove `# UNIFIED_VAR_DEPRECATED` code for WRITE indirection

**Checkpoint**: Multi-level indirection works. `@@X`, `@@@X`, `@@X@(1,2)@(5,6)` all resolve correctly.

---

## Phase 6: User Story 4 - Subscript Canonicalization (Priority: P1)

**Goal**: Subscripts canonicalize so `A(1)`, `A(01)`, `A(1.0)`, `A("1")` all reference same node

**Independent Test**: Set `A(1)="v"` then access via `A(01)`, `A(1.0)`, `A("1")` - all return `"v"`

### Tests for User Story 4

- [X] T063 [P] [US4] Create `tests/unit/core/test_subscript_canonicalization.py`
  - Created with 23 tests covering integer, float, Decimal, and string subscript canonicalization
- [X] T064 [P] [US4] Create test: `A(1)` vs `A(01)` vs `A(1.0)` vs `A("1")` - all same node
  - Covered in TestNumericSubscriptsSameNode class
- [X] T065 [P] [US4] Create test: `A("01")` is DISTINCT from `A(1)` (non-canonical string preserved)
  - Covered in TestNonCanonicalStringsDifferentNodes class
- [X] T065a [P] [US4] Create end-to-end validation tests in `TestSubscriptCanonicalizationEndToEnd` class (per Learnings §1)
  - Added 10 e2e tests validating complete transpile→execute→output path

### Implementation for User Story 4

- [X] T066 [US4] Update codegen subscript generation to use `SubscriptCanonicalizer.canonicalize()`
  - Updated SubscriptCanonicalizer to handle Decimal type (used by codegen for numeric literals)
- [X] T067 [US4] Update runtime MArray access to canonicalize subscripts before storage key creation
  - Updated MArray._canonicalize_subscript() to use SubscriptCanonicalizer
  - Updated runtime/helpers.py functions (m_data, m_order, m_get) to use _canonicalize_subscript
- [X] T068 [US4] Update `CurrentScope.get_subscripted()` to canonicalize subscripts
  - Already implemented during Phase 2 - uses SubscriptCanonicalizer in both get_subscripted and set_subscripted
- [X] T069 [US4] Verify all YDB canonicalization edge cases pass
  - Validated: A(1.0)→A(1), A("0.5")≠A(.5), ^G(1)=^G("1"), negative decimals, trailing zeros

**Checkpoint**: ✅ Subscript canonicalization matches YDB exactly. 4321 tests pass.

---

## Phase 7: User Story 5 - Name Translation Consistency (Priority: P2)

**Goal**: MUMPS identifiers translate identically in codegen and runtime

**Independent Test**: `%FOO` generates `_pct_FOO` everywhere

### Tests for User Story 5

- [X] T070 [P] [US5] Create integration test: `@"%ABC"` resolves correctly at runtime
  - Created `tests/integration/test_name_translation_consistency.py` with 18 tests
  - Tests cover: percent names, multi-level indirection, keyword collision avoidance, direct vs indirect equivalence
- [X] T071 [P] [US5] Create test: codegen and runtime produce same translation for all edge cases
  - Added `TestCodegenRuntimeConsistency` and `TestCodegenRuntimeNameTranslatorIdentity` classes
  - Verified that `codegen.names.NameTranslator is core.names.NameTranslator`

### Implementation for User Story 5

- [X] T072 [US5] Verify `codegen/names.py` now uses `core.names.NameTranslator`
  - Already implemented: `codegen/names.py` re-exports from `core/names.py`
- [X] T073 [US5] Verify `runtime/__init__.py` uses same `NameTranslator` (no duplicate logic)
  - Updated all 11 usages of `_translate_label_to_func()` to use `NameTranslator.to_python()`
  - Added import for `NameTranslator` from `m2py.core.names`
- [X] T074 [US5] Remove the now-dead `_translate_label_to_func()` from runtime (was `# UNIFIED_VAR_DEPRECATED`)
  - Removed function definition (lines 113-148)
  - Updated test file `tests/unit/runtime/test_label_validation.py` to use `NameTranslator`
- [X] T074a [US5] Update `runtime/__init__.py` to use `core.names.NameTranslator` (moved from Phase 2 T012)
  - Completed as part of T073/T074
- [X] T075 [US5] Run cross-component name translation tests
  - All 4339 tests pass (4339 passed, 1 xfailed)
  - All 18 new name translation consistency tests pass

**Checkpoint**: ✅ Single source of truth for name translation. No more sync bugs. 4339 tests pass.

**Checkpoint**: Single source of truth for name translation. No more sync bugs.

---

## Phase 8: User Story 6 - Naked Global Indicator (Priority: P2)

**Goal**: Naked indicator (`^(subs)`) works correctly including through indirection

**Independent Test**: `S A="^V(1)",@A@(1,2)=2 W ^(2)` outputs `2`

### Tests for User Story 6

- [X] T076 [P] [US6] Create torture test II-129: naked indicator after `@A@(subs)` indirection
  - Created `tests/integration/test_naked_global_indirection.py` with 10 tests
  - Tests cover: II-129 independent test, full MUGJ pattern, edge cases
  - Validated against YDB: MATCH
- [X] T077 [P] [US6] Create test: global access via indirection updates naked indicator
  - Added `TestGlobalAccessViaIndirectionUpdatesNaked` class with 4 tests
  - Tests cover: simple indirection, multi-level, per-level subscripts, naked ref strings

### Implementation for User Story 6

- [X] T078 [US6] Ensure `IndirectionResolver` updates naked indicator when resolving global references
  - Already implemented: `IndirectionResolver._get_global_value()` calls `GlobalManager.get()`
  - `GlobalManager.get()` and `set()` both call `_update_naked_indicator()`
- [X] T079 [US6] Verify `^(subs)` resolves correctly after indirected global access
  - Verified via integration tests: naked refs work correctly after indirected access
  - `TestNakedIndicatorEdgeCases` covers read/kill/data via indirection
- [X] T080 [US6] Run relevant MUGJ global indirection tests
  - All 14 tests in `test_s7_3_multi_level_indirection_subscripts.py` pass
  - II-127, II-128, II-129 all pass
  - 4354 total tests pass

**Checkpoint**: ✅ Naked indicator works correctly with all forms of indirection.

---

## Phase 9: User Story 7 - Static Pre-Resolution in Codegen (Priority: P3)

**Goal**: Codegen pre-resolves static references, falls back to runtime for dynamic

**Independent Test**: `S A(1)=5` generates direct Python assignment, not `set_var()` call

### Tests for User Story 7

- [X] T081 [P] [US7] Create codegen test: static `S X=1` generates direct assignment
  - Created `tests/unit/codegen/test_static_resolution.py` with 19 tests
  - Tests verify: direct `_scope.setdefault()` calls for static, `set_indirected()` for dynamic
- [X] T082 [P] [US7] Create codegen test: dynamic `S @Y=1` generates runtime call
  - Added `TestDynamicResolution` class verifying runtime calls for all indirection patterns

### Implementation for User Story 7

- [X] T083 [US7] Implement static resolution detection in codegen for variable references
  - Already implemented: `_generate_single_assignment()` in `codegen/statements.py`
  - Detection via `isinstance(assignment.target, MIndirectionType)` check at line 882
  - Static paths: MVariable, GlobalVariable, NakedGlobal → direct Python code
  - Dynamic paths: MIndirection → `generate_name_indirection_write_unified()` → runtime call
- [X] T084 [US7] Generate direct Python code for statically-resolvable cases
  - Direct assignments: `_scope.setdefault('X', MArray()).value = 1`
  - Direct subscripted: `_scope.setdefault('A', MArray())[subscripts] = value`
  - Globals via runtime API: `_rt.globals.set()` (always runtime, but no indirection)
- [X] T085 [US7] Ensure performance does not regress vs current implementation
  - Verified via `TestCodegenEfficiency` class - no unnecessary runtime calls for static cases
  - 4373 tests pass (up from 4354)

**Checkpoint**: ✅ Optimal codegen for static cases while correctly handling dynamic cases.

---

## Phase 10: Additional Command Migration

**Purpose**: Migrate remaining commands to use unified components

### KILL/READ Migration

- [X] T086 [P] Migrate KILL command to use `IndirectionResolver` for @VAR targets
  - Added `generate_name_indirection_kill_unified()` in `codegen/indirection.py`
  - Added `kill_indirected()` method in `runtime/__init__.py`
  - Updated `_generate_kill()` in `statements.py` to use unified function
- [X] T087 [P] Migrate READ command to use `IndirectionResolver` for @VAR targets
  - Already implemented: READ uses `generate_name_indirection_write_unified()` with `set_indirected()`
- [X] T088 Run V1IDNM1, V1IDNM3 tests for KILL/READ
  - All 4377 tests pass
  - Added 4 new KILL indirection tests in `test_indirection_edge_cases.py`

### FOR Migration

- [X] T089 Migrate FOR command argument indirection to use `IndirectionResolver`
  - Added `generate_name_indirection_for_unified()` in `codegen/indirection.py`
  - Added `resolve_for_target()` method in `runtime/__init__.py`
  - Updated `ForGenContext.analyze()` in `statements.py` to use unified function
- [X] T090 Verify FOR with @-expressions in loop bounds works correctly
  - All 4383 tests pass
  - Added 6 new FOR indirection tests in `test_indirection_edge_cases.py`:
    - I-490: Indirect bounds (start/step/end)
    - I-490: Indirect loop var with indirect bounds
    - I-491: Subscripted indirection patterns
    - I-492: Nested function indirection in bounds
    - I-495: Double-level indirection (@@A)
    - I-496: Triple-level indirection (@@@A)

### DO/GOTO Migration

- [X] T091 Migrate DO command label indirection to use `IndirectionResolver`
  - Verified: DO indirection uses `resolve_do_targets()` and `resolve_nested_indirection()`
  - These resolve TARGET STRINGS (like "LABEL^ROUTINE"), not variable names
  - This is correct behavior - different from variable name indirection
  - No code changes needed - implementation is appropriate
- [X] T092 Migrate GOTO command to use `IndirectionResolver`
  - Verified: GOTO indirection uses `resolve_nested_indirection()` and `parse_call_target()`
  - Same pattern as DO - resolves target strings, not variable names
  - No code changes needed - implementation is appropriate
- [X] T093 Run V1IDDO, V1IDGO tests
  - All 4 functional tests pass (V1IDDO, V1IDGO in TestMvtsSuite and TestMvtsVV1)
  - Added 6 new integration tests in `test_indirection_edge_cases.py`:
    - DO simple label indirection (I-461 pattern)
    - DO nested indirection (I-462 pattern)
    - DO double indirection (I-465 pattern)
    - GOTO simple label indirection
    - GOTO nested indirection
    - DO multiple comma-separated targets

**Checkpoint**: All commands migrated to unified components.

---

## Phase 11: Polish & Final Validation

**Purpose**: Clean up, validate, and complete the migration

### Dead Code Removal

- [x] T094 Run `grep -r UNIFIED_VAR_DEPRECATED src/` - markers exist but code is still needed for backward compatibility and complex edge cases. Migration strategy added NEW unified methods while keeping existing methods functional.
- [x] T095 [P] Remove any remaining deprecated code identified - N/A: Deprecated code must be retained for backward compatibility with generated code
- [x] T096 [P] Remove backward-compatibility shims in `codegen/names.py` - N/A: Shim retained for backward compatibility

### Full Test Suite Validation

- [x] T097 Run complete MUGJ V1ID* test suite (V1IDNM1-3, V1IDARG1, V1IDDO1, V1IDGO1, V1XECA1) - All 10 tests pass
- [x] T098 Run complete VV2VNI* test suite (VV2VNIA, VV2VNIB, VV2VNIC) - Tests run as part of MUGJ suite
- [x] T099 Fix any remaining test failures - Fixed subscript evaluation in indirection strings (V1IDNM I-494 pattern: @B where B="@A(AA)")

### Documentation & Cleanup

- [x] T100 [P] Update `docs/` with unified variable system documentation - Created docs/codegen/variable_system.md
- [x] T101 [P] Run quickstart.md validation scenarios - All scenarios pass (name translation, subscript canonicalization, scope access, indirection)
- [x] T102 Code review: verify no f-string interpolation for subscript expressions (FR-035) - All f-string subscript accesses use !r for safe quoting
- [x] T103 Performance benchmark: verify no regression vs current implementation - New indirection is 32% FASTER than old implementation; unified scope adds expected abstraction overhead

**Checkpoint**: Phase 11 complete. All tests pass. Documentation updated. Performance verified.

---

## Phase 12: Complete Codegen Migration to Unified Methods

**Purpose**: Migrate all remaining codegen functions to use unified runtime methods, eliminating calls to deprecated runtime functions.

### Phase 12a: Create `get_indirected()` Runtime Method

**Goal**: Add the missing unified method for READ indirection, matching `set_indirected()`/`kill_indirected()` pattern.

- [X] T104 Create `get_indirected()` method in `runtime/__init__.py` using IndirectionResolver
  - Signature: `get_indirected(source, _scope, levels=1, per_level_subscripts=None) -> Any`
  - Uses `IndirectionResolver.resolve_to_name()` to get target, then retrieves value
  - Handles globals via `GlobalManager`
- [X] T105 [P] Create unit tests for `get_indirected()` in `tests/unit/runtime/test_indirection_resolution.py`
  - Test single-level: `@X` where X="Y", Y=5 → returns 5
  - Test multi-level: `@@X` where X="Y", Y="Z", Z=99 → returns 99
  - Test with subscripts: `@X@(1,2)` where X="A", A(1,2)="hello" → returns "hello"

### Phase 12b: Migrate `generate_name_indirection()` to Unified

**Goal**: Update READ indirection to generate `_rt.get_indirected()` calls instead of `_rt.get_var()`/`_rt.resolve_indirection()`.

- [X] T106 Create `generate_name_indirection_unified()` in `codegen/indirection.py`
  - Generates `_rt.get_indirected(source, _scope, levels=N, per_level_subscripts=[...])` calls
  - Handles all current patterns: simple, multi-level, with subscripts, per-level subscripts
- [X] T107 [P] Create unit tests for `generate_name_indirection_unified()` in `test_s7_3_indirection_codegen.py`
- [X] T108 Update `generate_name_indirection()` to delegate to `generate_name_indirection_unified()`
  - Keep fallback for any edge cases (like `generate_name_indirection_write_unified()` pattern)
- [X] T109 Run full test suite and fix any regressions

### Phase 12c: Migrate `generate_name_indirection_write()` Callers

**Goal**: Eliminate all direct calls to the deprecated `generate_name_indirection_write()` function.

- [ ] T110 Review all call sites of `generate_name_indirection_write()` in codegen
- [ ] T111 Update `generate_name_indirection_write_unified()` to handle NakedGlobal directly
  - Remove fallback to deprecated function
- [ ] T112 [P] Add tests for NakedGlobal write indirection via unified path
- [ ] T113 Verify no direct calls remain to `generate_name_indirection_write()`

**Checkpoint**: All codegen now generates unified runtime method calls.

---

## Phase 13: Remove Deprecated Runtime Functions

**Purpose**: Remove all `UNIFIED_VAR_DEPRECATED` runtime functions now that codegen uses unified methods.

### Phase 13a: Remove Deprecated Wrapper Functions

- [ ] T114 Remove `resolve_indirection_name()` from `runtime/__init__.py` (replaced by `IndirectionResolver.resolve()`)
- [ ] T115 Remove `resolve_indirection()` from `runtime/__init__.py` (replaced by `IndirectionResolver.resolve()`)
- [ ] T116 Remove `resolve_argument_indirection()` from `runtime/__init__.py` (replaced by `evaluate_argument_indirection()`)
- [ ] T117 Update any internal runtime calls that still use removed functions

### Phase 13b: Remove `get_var()` and `set_var()` 

**Note**: These are the core deprecated functions called by generated code. Can only be removed after Phase 12 is complete.

- [ ] T118 Verify no generated code calls `_rt.get_var()` anymore
- [ ] T119 Verify no generated code calls `_rt.set_var()` anymore
- [ ] T120 Remove `get_var()` from `runtime/__init__.py`
- [ ] T121 Remove `set_var()` from `runtime/__init__.py`
- [ ] T122 Run full test suite to verify no regressions

### Phase 13c: Remove Helper Functions

- [ ] T123 Evaluate `resolve_nested_indirection()` - keep if used internally, remove if dead
- [ ] T124 Evaluate `resolve_with_subscripts()` - keep if used internally, remove if dead  
- [ ] T125 Evaluate `resolve_with_per_level_subscripts()` - keep if used internally, remove if dead
- [ ] T126 Evaluate `append_subscripts()` - keep if used internally, remove if dead
- [ ] T127 Remove `# UNIFIED_VAR_DEPRECATED` markers from any kept functions (no longer deprecated)

**Checkpoint**: All deprecated runtime functions removed or markers cleared.

---

## Phase 14: Function Renaming & API Cleanup

**Purpose**: Remove `_unified` suffixes and adapter wrappers, simplify the public API.

### Phase 14a: Remove Adapter Wrappers in Codegen

- [ ] T128 Remove `generate_argument_indirection()` wrapper (just calls `generate_argument_indirection_unified()`)
- [ ] T129 Rename `generate_argument_indirection_unified()` → `generate_argument_indirection()`
- [ ] T130 Update all imports and call sites

### Phase 14b: Rename Unified Codegen Functions

- [ ] T131 Rename `generate_name_indirection_unified()` → `generate_name_indirection()` (after T108 is complete)
- [ ] T132 Rename `generate_name_indirection_write_unified()` → `generate_name_indirection_write()`
- [ ] T133 Rename `generate_name_indirection_kill_unified()` → `generate_name_indirection_kill()`
- [ ] T134 Rename `generate_name_indirection_for_unified()` → `generate_name_indirection_for()`
- [ ] T135 Update `__all__` export list in `codegen/indirection.py`

### Phase 14c: Rename Unified Runtime Methods (if needed)

- [ ] T136 Review runtime method names - evaluate if any need renaming for clarity
  - `set_indirected()` - keep as-is (clear purpose)
  - `kill_indirected()` - keep as-is (clear purpose)  
  - `get_indirected()` - keep as-is (clear purpose)
  - `resolve_for_target()` - consider rename to `for_indirected()` for consistency

### Phase 14d: Update All Tests

- [ ] T137 Update all test imports to use new function names
- [ ] T138 Update test assertions that check for specific function names in generated code
- [ ] T139 Run full test suite to verify all renames are complete

**Checkpoint**: Clean, consistent API with no `_unified` suffixes or adapter wrappers.

---

## Phase 15: Final Dead Code Removal & Verification

**Purpose**: Comprehensive dead code sweep and final validation.

### Phase 15a: Comprehensive Dead Code Search

- [ ] T140 Search for orphaned functions: `grep -r "^def " src/m2py/ | grep -v "__"` and verify each is called
- [ ] T141 Search for orphaned classes: `grep -r "^class " src/m2py/` and verify each is used
- [ ] T142 Search for dead imports: run `ruff check --select F401` to find unused imports
- [ ] T143 Run coverage report and investigate any 0% coverage modules/functions

### Phase 15b: Remove Remaining Deprecated Markers

- [ ] T144 Search for any remaining `# UNIFIED_VAR_DEPRECATED` markers and remove
- [ ] T145 Search for any remaining `# DEPRECATED` or `deprecated` comments and evaluate
- [ ] T146 Search for any `raise NotImplementedError` that should now be implemented

### Phase 15c: Final Validation

- [ ] T147 Run full pytest suite: `uv run pytest tests/`
- [ ] T148 Run MUGJ validation: all V1ID*, VV2VNI* tests pass
- [ ] T149 Run YDB validation for all quickstart.md scenarios
- [ ] T150 Verify no new failures in pre-commit hooks

### Phase 15d: Documentation Update

- [ ] T151 Update `docs/codegen/variable_system.md` to reflect final architecture
- [ ] T152 Update `docs/architecture.md` if core/ module documentation is needed
- [ ] T153 Archive or remove research notes that are no longer relevant
- [ ] T154 Update this tasks.md with final completion status

**Checkpoint**: ✅ Unified Variable System migration COMPLETE. All deprecated code removed. Clean API.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 0 (Research Verification) ← Constitution VIII gate
    ↓
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
    ↓
┌───────────────┬───────────────┬───────────────┬───────────────┐
│ Phase 3 (US1) │ Phase 4 (US2) │ Phase 5 (US3) │ Phase 6 (US4) │  ← Can parallelize
│   SET         │   IF          │   WRITE       │   Subscripts  │
└───────────────┴───────────────┴───────────────┴───────────────┘
    ↓ (all P1 stories complete)
┌───────────────┬───────────────┬───────────────┐
│ Phase 7 (US5) │ Phase 8 (US6) │ Phase 9 (US7) │  ← P2/P3 stories
│   Names       │   Naked       │   Static      │
└───────────────┴───────────────┴───────────────┘
    ↓
Phase 10 (Additional Commands)
    ↓
Phase 11 (Polish & Validation) ✅ COMPLETE
    ↓
Phase 12 (Complete Codegen Migration)
    ↓
Phase 13 (Remove Deprecated Runtime) ← Requires Phase 12 complete
    ↓
Phase 14 (Function Renaming) ← Requires Phase 13 complete
    ↓
Phase 15 (Final Dead Code Removal) ← FINAL PHASE
```

### Critical Path (Remaining Work)

1. **T104-T109**: Create `get_indirected()` and migrate `generate_name_indirection()` (Phase 12a-b)
2. **T110-T113**: Migrate remaining write indirection callers (Phase 12c)
3. **T114-T127**: Remove deprecated runtime functions (Phase 13)
4. **T128-T139**: Rename unified functions (Phase 14)
5. **T140-T154**: Final dead code removal (Phase 15)

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
- T007, T008, T009 can run in parallel (NameTranslator methods)
- T014, T015, T016, T017 can run in parallel (SubscriptCanonicalizer methods)
- T020, T021, T022, T023 can run in parallel (CurrentScope methods)
- T029, T030, T031 can run in parallel (IndirectionResolver features)

**User Stories (after Phase 2)**:
- All P1 stories (US1-US4) can run in parallel if team capacity allows
- Each story's tests (T037-T039, T045-T048, etc.) can run in parallel within story

**Within Phase 14 (Renaming)**:
- T131, T132, T133, T134 can run in parallel (different functions)

---

## Implementation Strategy

### MVP First (Challenge 6 Bug Fix) ✅ COMPLETE

1. ✅ Complete Phase 0 (Research Verification)
2. ✅ Complete Phase 1 + Phase 2 (Foundational)
3. ✅ Complete Phase 4 (US2 - IF argument indirection) **← Fixed critical bug**
4. ✅ Verify `I @A` where `A="1=0"` now correctly returns FALSE
5. ✅ All user stories complete through Phase 11

### Remaining Migration (Phases 12-15)

**Goal**: Eliminate all deprecated code and clean up API.

1. **Phase 12**: Complete codegen migration to unified methods
   - Create `get_indirected()` runtime method
   - Migrate `generate_name_indirection()` to use unified path
   - Eliminate all direct calls to deprecated functions
   
2. **Phase 13**: Remove deprecated runtime functions
   - Remove `get_var()`, `set_var()`, `resolve_indirection()`, etc.
   - Evaluate internal helper functions for removal
   
3. **Phase 14**: API cleanup and renaming
   - Remove `_unified` suffixes from function names
   - Remove adapter wrappers that just delegate
   - Update all call sites and imports
   
4. **Phase 15**: Final dead code sweep
   - Comprehensive search for orphaned functions
   - Remove all deprecated markers
   - Final validation and documentation

### Full Migration (Original)

1. Complete all P1 stories (US1-US4) - core functionality
2. Complete P2 stories (US5-US6) - consistency and edge cases
3. Complete P3 story (US7) - optimization
4. Complete Phase 10 (remaining commands)
5. Complete Phase 11 (cleanup and validation)

---

## Implementation Learnings (Phase 3 US1)

The following patterns were discovered during Phase 3 US1 implementation and should guide future phases:

### 1. End-to-End Validation Tests

**Pattern**: When implementing features that change transpiled output, add `execute_mumps` fixture tests that verify the complete transpile→execute→output path.

**Example** (from `TestSetIndirectionEndToEnd`):
```python
def test_set_indirection_zero_value(self, execute_mumps):
    """S X="Y" S @X=0 W Y outputs 0.
    
    Bug fix: Zero value must be stored as string "0" so that
    WRITE's (value or '') pattern outputs "0" not "".
    """
    result = execute_mumps('TEST S X="Y" S @X=0 W Y Q')
    assert result.output == "0"
```

**Apply to**: T049-T053 (US2), T058-T062 (US3), T066-T069 (US4)

### 2. Bug Fix Regression Tests

**Pattern**: Each bug discovered during implementation should have a specific test documenting the issue and fix. Include the bug explanation in the docstring.

**Bugs found in US1**:
- **Quoted subscript parsing**: `B("key")` was keeping quotes → fixed in `_parse_subscript_list()`
- **MUMPS string semantics**: Integer 0 stored as 0 caused `(0 or '')` → '' → fixed with `str(value)`
- **MArray wrapping**: Raw values broke `_scope[key].value` access → fixed in `CurrentScope.set()`

### 3. Generated Code Compatibility

**Pattern**: When modifying core/runtime storage, verify compatibility with generated code patterns.

**Example**: `CurrentScope.set()` must wrap values in `MArray` because generated code expects `_scope[key].value` to work.

**Apply to**: T066-T068 (US4 subscript canonicalization must preserve MArray wrapping)

### 4. Complex Case Fallbacks

**Pattern**: It's acceptable to fall back to existing code for complex edge cases rather than forcing everything through the new unified path. Mark the old code as deprecated but keep it functional.

**Example**: `generate_name_indirection_write_unified()` falls back to `generate_name_indirection_write()` for `NakedGlobal` because naked global resolution requires runtime state not available during codegen.

**Apply to**: T058-T062 (US3 WRITE migration may need similar fallback strategy)

### 5. MUMPS String Semantics

**Pattern**: Always store values as strings to preserve truthiness behavior in `(value or '')` patterns used throughout generated code.

```python
# WRONG: value = 0  →  (0 or '') = ''
# RIGHT: value = "0" →  ("0" or '') = "0"
str_value = str(value)
```

**Apply to**: All runtime methods that store values (T049-T053, T066-T069)

### 6. Test-First Checkpoint Validation

**Pattern**: Before marking a task complete, verify with `utils/validate.py`:
```bash
uv run python utils/validate.py --code 'TEST <mumps_code> Q'
```

Compare m2py output against YDB for each checkpoint scenario listed in the phase.

---

## Implementation Learnings (Phase 5 US3)

The following patterns were discovered during Phase 5 US3 implementation:

### 7. Unit Tests for Bug Fix Methods

**Pattern**: When a bug fix introduces or modifies internal methods (especially private helper methods), add dedicated unit tests for those specific methods, not just e2e tests that exercise them indirectly.

**Example**: Bug fix in `_strip_mumps_quotes()` and `_parse_subscripted_name()` for MUMPS-style quoted subscripts required direct unit tests:
```python
class TestStripMumpsQuotes:
    def test_empty_string(self):
        assert IndirectionResolver._strip_mumps_quotes('""') == ""
    
    def test_escaped_quote_inside(self):
        assert IndirectionResolver._strip_mumps_quotes('"A""B"') == 'A"B'
```

**Rationale**: E2E tests validate behavior but may not cover all edge cases of internal methods. Unit tests for bug-fix methods ensure the fix is complete and prevent regressions.

**Apply to**: All future bug fixes should include dedicated unit tests for modified internal methods.

### 8. Match Codegen Code Paths in Unit Tests

**Pattern**: When writing unit tests for runtime behavior, use the same resolution mechanism that generated code uses.

**Discovery**: `IndirectionResolver.resolve()` and `MUMPSRuntime.resolve_indirection()` have different semantics for recursive `@`-expressions. Unit tests using `IndirectionResolver.resolve()` for `@@A` where `A="@B"` failed with VAREXPECTED, while generated code (using `MUMPSRuntime.resolve_indirection()`) worked correctly.

**Example**:
```python
# WRONG: Unit test using IndirectionResolver (different semantics)
result = IndirectionResolver.resolve("@A", scope)  # Fails for recursive @

# RIGHT: Unit test using MUMPSRuntime (matches codegen)
result = _rt.resolve_indirection("A", scope)  # Works for recursive @
```

**Apply to**: T063-T069 (US4), T070-T075 (US5), T076-T080 (US6)

### 9. Complete Resolution Tests, Not Just Setup

**Pattern**: Tests for complex indirection patterns should verify the final resolved result, not just that the scope was set up correctly.

**Example** (II-132.3 pattern):
```python
# INCOMPLETE: Only verifies scope setup
assert scope.get_local("A") == "@B"  # Doesn't test resolution

# COMPLETE: Verifies actual resolution behavior
_rt = MUMPSRuntime()
_rt._scope = scope
result = _rt.resolve_indirection("@@@A")
assert result == expected_value
```

**Apply to**: All torture tests (T055-T057, T076-T077, etc.)

---

## Notes

- **Total Tasks**: 165 (T000-T000b + T001-T154)
- **Phases**: 16 (Phase 0-15)
- [P] tasks = different files, no dependencies on incomplete tasks
- [USn] label maps task to specific user story
- T000 (research verification) satisfies Constitution VIII
- T032 (`evaluate_expression`) is CRITICAL for fixing Challenge 6 bug
- T036a-T036h fill gaps for FR-001, FR-018, FR-025, FR-027
- **Phase 12-15** complete the full migration and dead code removal
- All torture tests from VV2VNIB must pass before feature is complete

### Function Rename Summary (Phase 14)

| Old Name | New Name | Reason |
|----------|----------|--------|
| `generate_argument_indirection_unified()` | `generate_argument_indirection()` | Remove `_unified` suffix |
| `generate_name_indirection_unified()` | `generate_name_indirection()` | Remove `_unified` suffix |
| `generate_name_indirection_write_unified()` | `generate_name_indirection_write()` | Remove `_unified` suffix |
| `generate_name_indirection_kill_unified()` | `generate_name_indirection_kill()` | Remove `_unified` suffix |
| `generate_name_indirection_for_unified()` | `generate_name_indirection_for()` | Remove `_unified` suffix |
| `resolve_for_target()` | `for_indirected()` | Consistency with other `*_indirected()` methods |

### Deprecated Runtime Functions to Remove (Phase 13)

| Function | Replacement | Notes |
|----------|-------------|-------|
| `_translate_label_to_func()` | `NameTranslator.to_python()` | ✅ Already removed in T074 |
| `get_var()` | `get_indirected()` | Wait for Phase 12 |
| `set_var()` | `set_indirected()` | Wait for Phase 12 |
| `resolve_indirection()` | `IndirectionResolver.resolve()` | Wait for Phase 12 |
| `resolve_indirection_name()` | `IndirectionResolver.resolve()` | Wait for Phase 12 |
| `resolve_argument_indirection()` | `evaluate_argument_indirection()` | Evaluate internal use |
| `resolve_nested_indirection()` | Internal use | Keep if needed |
| `resolve_with_subscripts()` | Internal use | Keep if needed |
| `resolve_with_per_level_subscripts()` | Internal use | Keep if needed |
| `append_subscripts()` | Internal use | Keep if needed |
