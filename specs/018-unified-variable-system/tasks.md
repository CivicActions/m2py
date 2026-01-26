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

**Checkpoint**: IF argument indirection works correctly. The critical bug (`I @A` where `A="1=0"`) is fixed.

---

## Phase 5: User Story 3 - Multi-Level Indirection Resolution (Priority: P1)

**Goal**: Multi-level indirection (`@@VAR`, `@@@VAR`) resolves correctly with per-level subscripts

**Independent Test**: `S A="B",B="C",C=99 W @@A` outputs `99`

### Tests for User Story 3

- [ ] T054 [P] [US3] Create `tests/unit/core/test_name_indirection_multilevel.py` with VV2VNIA patterns
- [ ] T055 [P] [US3] Create torture test II-127: `@@X@(1,2)@(5,6)` with per-level subscripts
- [ ] T056 [P] [US3] Create torture test II-131: `@B@(@B@(@B@(9)),@B,I)` deep nesting
- [ ] T057 [P] [US3] Create torture test II-132.3: `@@@@A` four-level chain with recursive @-expressions
- [ ] T057a [P] [US3] Create end-to-end validation tests in `TestWriteIndirectionEndToEnd` class (per Learnings §1)

### Implementation for User Story 3 - WRITE Command Migration

- [ ] T058 [US3] Update WRITE command codegen to use `IndirectionResolver` for @VAR output
- [ ] T059 [US3] Ensure multi-level indirection resolves through all levels correctly
- [ ] T060 [US3] Ensure per-level subscripts are applied at correct resolution points
- [ ] T061 [US3] Run VV2VNIA, VV2VNIB tests and fix any regressions
- [ ] T062 [US3] Remove `# UNIFIED_VAR_DEPRECATED` code for WRITE indirection

**Checkpoint**: Multi-level indirection works. `@@X`, `@@@X`, `@@X@(1,2)@(5,6)` all resolve correctly.

---

## Phase 6: User Story 4 - Subscript Canonicalization (Priority: P1)

**Goal**: Subscripts canonicalize so `A(1)`, `A(01)`, `A(1.0)`, `A("1")` all reference same node

**Independent Test**: Set `A(1)="v"` then access via `A(01)`, `A(1.0)`, `A("1")` - all return `"v"`

### Tests for User Story 4

- [ ] T063 [P] [US4] Create `tests/unit/core/test_subscript_canonicalization.py`
- [ ] T064 [P] [US4] Create test: `A(1)` vs `A(01)` vs `A(1.0)` vs `A("1")` - all same node
- [ ] T065 [P] [US4] Create test: `A("01")` is DISTINCT from `A(1)` (non-canonical string preserved)
- [ ] T065a [P] [US4] Create end-to-end validation tests in `TestSubscriptCanonicalizationEndToEnd` class (per Learnings §1)

### Implementation for User Story 4

- [ ] T066 [US4] Update codegen subscript generation to use `SubscriptCanonicalizer.canonicalize()`
- [ ] T067 [US4] Update runtime MArray access to canonicalize subscripts before storage key creation
- [ ] T068 [US4] Update `CurrentScope.get_subscripted()` to canonicalize subscripts
- [ ] T069 [US4] Verify all YDB canonicalization edge cases pass

**Checkpoint**: Subscript canonicalization matches YDB exactly.

---

## Phase 7: User Story 5 - Name Translation Consistency (Priority: P2)

**Goal**: MUMPS identifiers translate identically in codegen and runtime

**Independent Test**: `%FOO` generates `_pct_FOO` everywhere

### Tests for User Story 5

- [ ] T070 [P] [US5] Create integration test: `@"%ABC"` resolves correctly at runtime
- [ ] T071 [P] [US5] Create test: codegen and runtime produce same translation for all edge cases

### Implementation for User Story 5

- [ ] T072 [US5] Verify `codegen/names.py` now uses `core.names.NameTranslator`
- [ ] T073 [US5] Verify `runtime/__init__.py` uses same `NameTranslator` (no duplicate logic)
- [ ] T074 [US5] Remove the now-dead `_translate_label_to_func()` from runtime (was `# UNIFIED_VAR_DEPRECATED`)
- [ ] T074a [US5] Update `runtime/__init__.py` to use `core.names.NameTranslator` (moved from Phase 2 T012)
- [ ] T075 [US5] Run cross-component name translation tests

**Checkpoint**: Single source of truth for name translation. No more sync bugs.

---

## Phase 8: User Story 6 - Naked Global Indicator (Priority: P2)

**Goal**: Naked indicator (`^(subs)`) works correctly including through indirection

**Independent Test**: `S A="^V(1)",@A@(1,2)=2 W ^(2)` outputs `2`

### Tests for User Story 6

- [ ] T076 [P] [US6] Create torture test II-129: naked indicator after `@A@(subs)` indirection
- [ ] T077 [P] [US6] Create test: global access via indirection updates naked indicator

### Implementation for User Story 6

- [ ] T078 [US6] Ensure `IndirectionResolver` updates naked indicator when resolving global references
- [ ] T079 [US6] Verify `^(subs)` resolves correctly after indirected global access
- [ ] T080 [US6] Run relevant MUGJ global indirection tests

**Checkpoint**: Naked indicator works correctly with all forms of indirection.

---

## Phase 9: User Story 7 - Static Pre-Resolution in Codegen (Priority: P3)

**Goal**: Codegen pre-resolves static references, falls back to runtime for dynamic

**Independent Test**: `S A(1)=5` generates direct Python assignment, not `set_var()` call

### Tests for User Story 7

- [ ] T081 [P] [US7] Create codegen test: static `S X=1` generates direct assignment
- [ ] T082 [P] [US7] Create codegen test: dynamic `S @Y=1` generates runtime call

### Implementation for User Story 7

- [ ] T083 [US7] Implement static resolution detection in codegen for variable references
- [ ] T084 [US7] Generate direct Python code for statically-resolvable cases
- [ ] T085 [US7] Ensure performance does not regress vs current implementation

**Checkpoint**: Optimal codegen for static cases while correctly handling dynamic cases.

---

## Phase 10: Additional Command Migration

**Purpose**: Migrate remaining commands to use unified components

### KILL/READ Migration

- [ ] T086 [P] Migrate KILL command to use `IndirectionResolver` for @VAR targets
- [ ] T087 [P] Migrate READ command to use `IndirectionResolver` for @VAR targets
- [ ] T088 Run V1IDNM1, V1IDNM3 tests for KILL/READ

### FOR Migration

- [ ] T089 Migrate FOR command argument indirection to use `IndirectionResolver`
- [ ] T090 Verify FOR with @-expressions in loop bounds works correctly

### DO/GOTO Migration

- [ ] T091 Migrate DO command label indirection to use `IndirectionResolver`
- [ ] T092 Migrate GOTO command to use `IndirectionResolver`
- [ ] T093 Run V1IDDO, V1IDGO tests

**Checkpoint**: All commands migrated to unified components.

---

## Phase 11: Polish & Final Validation

**Purpose**: Clean up, validate, and complete the migration

### Dead Code Removal

- [ ] T094 Run `grep -r UNIFIED_VAR_DEPRECATED src/` - list must be empty
- [ ] T095 [P] Remove any remaining deprecated code identified
- [ ] T096 [P] Remove backward-compatibility shims in `codegen/names.py` (if no longer needed)

### Full Test Suite Validation

- [ ] T097 Run complete MUGJ V1ID* test suite (V1IDNM1-3, V1IDARG1, V1IDDO1, V1IDGO1, V1XECA1)
- [ ] T098 Run complete VV2VNI* test suite (VV2VNIA, VV2VNIB, VV2VNIC)
- [ ] T099 Fix any remaining test failures

### Documentation & Cleanup

- [ ] T100 [P] Update `docs/` with unified variable system documentation
- [ ] T101 [P] Run quickstart.md validation scenarios
- [ ] T102 Code review: verify no f-string interpolation for subscript expressions (FR-035)
- [ ] T103 Performance benchmark: verify no regression vs current implementation

**Checkpoint**: Migration complete. All tests pass. No deprecated code remains.

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
Phase 11 (Polish & Validation)
```

### Critical Path

1. **T000-T000b**: Research Verification (Constitution VIII gate)
2. **T001-T005**: Setup (blocks everything)
3. **T006-T036h**: Foundational components (blocks all user stories)
4. **T049-T053**: US2 IF migration (fixes Challenge 6 critical bug)
5. **T094-T099**: Final validation

### Parallel Opportunities

**Within Phase 2 (Foundational)**:
- T007, T008, T009 can run in parallel (NameTranslator methods)
- T014, T015, T016, T017 can run in parallel (SubscriptCanonicalizer methods)
- T020, T021, T022, T023 can run in parallel (CurrentScope methods)
- T029, T030, T031 can run in parallel (IndirectionResolver features)

**User Stories (after Phase 2)**:
- All P1 stories (US1-US4) can run in parallel if team capacity allows
- Each story's tests (T037-T039, T045-T048, etc.) can run in parallel within story

---

## Implementation Strategy

### MVP First (Challenge 6 Bug Fix)

1. Complete Phase 0 (Research Verification) **← Constitution VIII**
2. Complete Phase 1 + Phase 2 (Foundational)
3. Complete Phase 4 (US2 - IF argument indirection) **← Fixes critical bug**
4. Verify `I @A` where `A="1=0"` now correctly returns FALSE
5. Deploy/demo bug fix

### Full Migration

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

## Notes

- **Total Tasks**: 114 (T000-T000b + T001-T103 + T036a-T036h)
- **Phases**: 12 (Phase 0-11)
- [P] tasks = different files, no dependencies on incomplete tasks
- [USn] label maps task to specific user story
- T000 (research verification) satisfies Constitution VIII
- T032 (`evaluate_expression`) is CRITICAL for fixing Challenge 6 bug
- T036a-T036h fill gaps for FR-001, FR-018, FR-025, FR-027
- T094 (dead code scan) ensures migration is complete
- All torture tests from VV2VNIB must pass before feature is complete
