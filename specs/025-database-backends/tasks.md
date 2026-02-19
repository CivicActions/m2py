# Tasks: Database Storage Backends for YottaDB and IRIS

**Input**: Design documents from `/workspaces/m2py/specs/025-database-backends/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Branch**: `025-database-backends`

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Docker environment setup

- [x] T001 [P] Create Docker configuration for YottaDB (`Dockerfile.yottadb` + `utils/ydb.sh`)
- [x] T002 [P] Create Docker container helper for IRIS (`utils/iris.sh`)
- [ ] T003 [P] Create tests/runtime/backend/ directory structure
- [ ] T004 [P] Add yottadb and intersystems-irispython to pyproject.toml as optional backend dependencies

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 [P] Create backend exception hierarchy in src/m2py/runtime/backend_exceptions.py
- [ ] T006 [P] Create test fixtures for backend parameterization in tests/runtime/backend/conftest.py
- [ ] T007 Update get_global_storage() factory in src/m2py/runtime/__init__.py to support backend selection via M2PY_GLOBAL_BACKEND
- [ ] T008 [P] Create environment configuration helper functions for reading backend parameters
- [ ] T009 [P] Add pytest markers for backend testing (backend_inmemory, backend_yottadb, backend_iris)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Store and Retrieve MUMPS Globals in YottaDB (Priority: P1) 🎯 MVP

**Goal**: Enable persistent global storage in YottaDB with full MUMPS semantics

**Independent Test**: Set M2PY_GLOBAL_BACKEND=yottadb, run transpiled code that sets `^TEST(1)="value"`, restart process, verify value persists

### Implementation for User Story 1

- [ ] T010 [US1] Create YottaDBGlobalStorage class stub in src/m2py/runtime/yottadb_backend.py
- [ ] T011 [US1] Implement lazy connection initialization (_ensure_initialized) with YottaDB SDK import
- [ ] T012 [US1] Implement get() method with subscript canonicalization and YDB exception translation
- [ ] T013 [US1] Implement set() method with subscript canonicalization
- [ ] T014 [US1] Implement kill() and kill_all() methods
- [ ] T015 [US1] Implement data() method returning correct $DATA codes (0/1/10/11)
- [ ] T016 [US1] Implement order() method with MUMPS collation order
- [ ] T017 [US1] Implement query() method using recursive order() traversal
- [ ] T018 [US1] Implement get_tree() and merge_tree() bulk operations
- [ ] T019 [US1] Implement incr() atomic increment operation
- [ ] T020 [US1] Add thread safety locks around all YDB API calls
- [ ] T021 [US1] Update factory to instantiate YottaDBGlobalStorage when backend=yottadb

### Tests for User Story 1

- [ ] T022 [P] [US1] Create test_basic_operations.py with tests for get/set/kill/data operations
- [ ] T023 [P] [US1] Create test_order_query.py with YottaDB-specific traversal tests
- [ ] T024 [P] [US1] Create test_subscript_canonicalization.py with numeric/string collation tests including explicit validation of numeric vs string canonicalization (e.g., subscript '1' equivalent to 1)
- [ ] T025 [P] [US1] Create test_connection_lifecycle.py with lazy init and error handling tests
- [ ] T026 [P] [US1] Create test_exception_translation.py validating YDB exception mapping

**Checkpoint**: YottaDB backend fully functional - can persist globals across process restarts

---

## Phase 4: User Story 2 - Store and Retrieve MUMPS Globals in IRIS (Priority: P1)

**Goal**: Enable persistent global storage in IRIS with namespace support

**Independent Test**: Set M2PY_GLOBAL_BACKEND=iris, run transpiled code, verify persistence and cross-validation with IRIS native MUMPS

### Implementation for User Story 2

- [ ] T027 [US2] Create IRISGlobalStorage class stub in src/m2py/runtime/iris_backend.py
- [ ] T028 [US2] Implement lazy connection initialization (_ensure_connected) reading IRIS connection parameters
- [ ] T029 [US2] Implement get() method with extended reference parsing (^|"NAMESPACE"|Global)
- [ ] T030 [US2] Implement set() method with namespace switching
- [ ] T031 [US2] Implement kill() and kill_all() methods
- [ ] T032 [US2] Implement data() method returning correct $DATA codes
- [ ] T033 [US2] Implement order() method
- [ ] T034 [US2] Implement query() method using IRIS native query API
- [ ] T035 [US2] Implement get_tree() and merge_tree() bulk operations
- [ ] T036 [US2] Implement incr() atomic increment operation
- [ ] T037 [US2] Add thread safety locks around IRIS connection operations
- [ ] T038 [US2] Implement _parse_extended_ref() helper for namespace parsing
- [ ] T039 [US2] Update factory to instantiate IRISGlobalStorage when backend=iris

### Tests for User Story 2

- [ ] T040 [P] [US2] Add IRIS-specific tests to test_basic_operations.py
- [ ] T041 [P] [US2] Add IRIS namespace tests to test_extended_globals.py
- [ ] T042 [P] [US2] Create test_cross_validation.py validating m2py writes are readable by IRIS native MUMPS and YottaDB native MUMPS
- [ ] T043 [P] [US2] Add IRIS connection parameter tests to test_connection_lifecycle.py
- [ ] T044 [P] [US2] Add IRIS exception translation tests to test_exception_translation.py

**Checkpoint**: IRIS backend fully functional - can persist globals with namespace support

---

## Phase 5: User Story 3 - Unified Test Suite Validates All Backends (Priority: P1)

**Goal**: Reorganize existing tests into unified backend test suite, ensure all backends pass identical tests

**Independent Test**: Run `uv run pytest tests/runtime/backend/` with each backend, verify all pass

### Implementation for User Story 3

- [ ] T045 [US3] Audit existing tests in tests/unit/runtime/, tests/integration/ for backend operations
- [ ] T046 [US3] Move (not copy) existing test_global_storage.py backend selection tests to tests/runtime/backend/, removing from original location tests/unit/runtime/
- [ ] T047 [P] [US3] Reorganize global operations tests into test_basic_operations.py
- [ ] T048 [P] [US3] Reorganize order/query tests into test_order_query.py
- [ ] T049 [P] [US3] Reorganize subscript collation tests into test_subscript_canonicalization.py
- [ ] T050 [P] [US3] Reorganize naked reference tests into test_naked_references.py
- [ ] T051 [P] [US3] Reorganize MERGE tests into test_merge_operations.py
- [ ] T052 [P] [US3] Reorganize $INCREMENT tests into test_increment.py
- [ ] T053 [US3] Update all reorganized tests to use backend fixture from conftest.py
- [ ] T054 [US3] Add @pytest.mark.backend_* decorators to all tests
- [ ] T055 [US3] Run full test suite against inmemory backend to validate no regressions
- [ ] T056 [US3] Run full test suite against yottadb backend in Docker
- [ ] T057 [US3] Run full test suite against iris backend in Docker

**Checkpoint**: All backends pass identical unified test suite - semantic equivalence proven

---

## Phase 6: User Story 4 - Lock Operations Across Backends (Priority: P2)

**Goal**: Implement MUMPS LOCK semantics using native database lock mechanisms

**Independent Test**: Spawn two processes with same backend, both attempt lock on same global, verify only one succeeds

### Implementation for User Story 4

- [ ] T058 [US4] Implement lock() method in YottaDBGlobalStorage using yottadb.lock()
- [ ] T059 [US4] Implement unlock() method in YottaDBGlobalStorage with lock state tracking
- [ ] T060 [US4] Implement unlock_all() method in YottaDBGlobalStorage
- [ ] T061 [US4] Implement lock() method in IRISGlobalStorage using IRIS native locks
- [ ] T062 [US4] Implement unlock() method in IRISGlobalStorage
- [ ] T063 [US4] Implement unlock_all() method in IRISGlobalStorage
- [ ] T064 [US4] Add lock state tracking to YottaDB backend (workaround for YDB lock-all semantics)
- [ ] T065 [US4] Handle lock timeout parameter (None = wait indefinitely)

### Tests for User Story 4

- [ ] T066 [P] [US4] Create test_locks.py with lock acquisition tests for all backends
- [ ] T067 [P] [US4] Add lock timeout tests (success within timeout, failure on timeout)
- [ ] T068 [P] [US4] Add multi-process lock coordination tests
- [ ] T069 [P] [US4] Add selective unlock tests (unlock specific node, not all)
- [ ] T070 [P] [US4] Add nested lock tests
- [ ] T070a [P] [US4] Create multi-threaded test validating backend thread safety with concurrent get/set operations from multiple threads

**Checkpoint**: Lock operations work correctly across all backends with proper inter-process coordination

---

## Phase 7: User Story 5 - Transaction Support Across Backends (Priority: P2)

**Goal**: Implement MUMPS transaction semantics (TSTART/TCOMMIT/TROLLBACK) using native database transactions

**Independent Test**: Start transaction, modify globals, rollback, verify globals restored to pre-transaction state

### Implementation for User Story 5

- [ ] T071 [US5] Implement transaction_start() in YottaDBGlobalStorage with transaction depth tracking
- [ ] T072 [US5] Implement transaction_commit() in YottaDBGlobalStorage using yottadb.tp() callback model
- [ ] T073 [US5] Implement transaction_rollback() in YottaDBGlobalStorage
- [ ] T074 [US5] Create transaction context manager for YDB callback adapter
- [ ] T075 [US5] Implement transaction_start() in IRISGlobalStorage using IRIS.begin()
- [ ] T076 [US5] Implement transaction_commit() in IRISGlobalStorage using IRIS.commit()
- [ ] T077 [US5] Implement transaction_rollback() in IRISGlobalStorage using IRIS.rollback()
- [ ] T078 [US5] Handle nested transaction levels correctly (increment/decrement depth)

### Tests for User Story 5

- [ ] T079 [P] [US5] Create test_transactions.py with basic transaction commit tests
- [ ] T080 [P] [US5] Add transaction rollback tests validating state restoration
- [ ] T081 [P] [US5] Add nested transaction tests ($TLEVEL tracking)
- [ ] T082 [P] [US5] Add transaction atomicity tests (all-or-nothing)
- [ ] T083 [P] [US5] Add transaction isolation tests (read committed minimum)

**Checkpoint**: Transaction operations provide ACID guarantees across all backends

---

## Phase 8: User Story 6 - Connection Configuration via Environment (Priority: P2)

**Goal**: Validate connection configuration via environment variables with clear error messages

**Independent Test**: Set different environment variables, verify runtime connects to correct backend without code changes

### Implementation for User Story 6

- [ ] T084 [US6] Add environment variable validation in YottaDBGlobalStorage initialization
- [ ] T085 [US6] Add environment variable validation in IRISGlobalStorage initialization
- [ ] T086 [US6] Implement clear error messages for missing YottaDB environment (not running inside container)
- [ ] T087 [US6] Implement clear error messages for missing M2PY_IRIS_PASSWORD (IRIS)
- [ ] T088 [US6] Add default value handling for optional parameters (M2PY_IRIS_HOST=localhost, etc.)
- [ ] T089 [US6] Document all environment variables in backend exception messages

### Tests for User Story 6

- [ ] T090 [P] [US6] Add configuration validation tests to test_connection_lifecycle.py
- [ ] T091 [P] [US6] Test missing required environment variables raise BackendConfigurationError
- [ ] T092 [P] [US6] Test default values are applied when optional env vars not set
- [ ] T093 [P] [US6] Test backend switching via M2PY_GLOBAL_BACKEND environment variable
- [ ] T094 [P] [US6] Test error messages include actionable guidance

**Checkpoint**: Configuration validation provides clear error messages and sensible defaults

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, CI/CD, performance validation, security hardening

- [ ] T095 [P] Update docs/architecture.md with backend architecture diagram
- [ ] T096 [P] Update docs/runtime.md with backend usage examples
- [ ] T097 [P] Update README.md with backend installation instructions
- [ ] T098 [P] Create Docker Compose configuration for multi-backend testing with services: yottadb (future port 1972), iris (ports 1972, 52773), shared network, named volumes (yottadb-data, iris-data) for data persistence
- [ ] T099 [P] Update CI/CD workflows to run tests against all three backends
- [ ] T100 [P] Add backend performance benchmarks to tests/runtime/backend/ measuring get/set/order latency with acceptance criteria: 95th percentile <10ms for typical operations (≤3 subscript levels, ≤1KB values)
- [ ] T101 [P] Validate quickstart.md examples work end-to-end with default Docker connection parameters matching yottadb/yottadb:latest and intersystems/iris-community:latest images
- [ ] T102 [P] Document IRIS namespace isolation semantics in quickstart.md (how USER namespace is default, how extended references work, cross-namespace limitations)
- [ ] T103 [P] Update docs/limitations.md with backend-specific limitations including database-specific limits (max key length, value size, subscript depth) for YottaDB and IRIS
- [ ] T104 Code review and refactoring for consistency across backends (consistent error messages, method signatures, variable naming, exception handling patterns)
- [ ] T105 Security review of connection parameter handling (especially M2PY_IRIS_PASSWORD in environment)
- [ ] T106 [P] Validate InMemoryGlobalStorage implements all protocol methods correctly after protocol updates (including any new SSVN methods)
- [ ] T107 [P] Implement SSVN operations (ssvn_get, ssvn_set, ssvn_data, ssvn_order, ssvn_query) in YottaDBGlobalStorage for system-wide state (^$JOB, ^$LOCK)
- [ ] T108 [P] Implement SSVN operations in IRISGlobalStorage for system-wide state
- [ ] T109 [P] Create tests for SSVN operations in test_ssvn_operations.py validating system variable access across backends

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - US1, US2 can proceed in parallel (different files)
  - US3 depends on US1, US2 having basic implementations
  - US4, US5, US6 can start after US1, US2 but may need updates to both backend files
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Setup (Phase 1) 
    ↓
Foundational (Phase 2) [BLOCKS EVERYTHING]
    ↓
    ├─→ US1: YottaDB Backend (Phase 3) ──┐
    │                                     ↓
    ├─→ US2: IRIS Backend (Phase 4) ─────→ US3: Unified Tests (Phase 5)
    │                                     ↓
    └─→ US6: Env Config (Phase 8) [Can run anytime after Foundational, independent of US3/US4/US5]
                                          ↓
                                     ├─→ US4: Locks (Phase 6)
                                     │
                                     └─→ US5: Transactions (Phase 7)
                                          ↓
                                     Polish (Phase 9)
```

**Critical Path**:
1. Setup → Foundational (must complete first)
2. Foundational → US1 & US2 in parallel (different backend files)
3. US1 & US2 → US3 (needs backends to test against)
4. US3 → US4 & US5 in parallel (can add to existing backends)
5. US6 can run in parallel with US4/US5 (validation tests)
6. All → Polish

### Within Each User Story

- **US1 (YottaDB)**: Implementation before tests (tests need backend to exist)
- **US2 (IRIS)**: Implementation before tests
- **US3 (Unified Tests)**: Reorganization tasks can be parallelized (different test files)
- **US4 (Locks)**: YottaDB and IRIS lock implementations can be parallel
- **US5 (Transactions)**: YottaDB and IRIS transaction implementations can be parallel
- **US6 (Environment)**: Validation can be added to both backends in parallel

### Parallel Opportunities

**Phase 1 (Setup)**: All 4 tasks can run in parallel (different files/directories)

**Phase 2 (Foundational)**: Tasks T005, T006, T008, T009 can run in parallel (different files)

**Phase 3 (US1)**: 
- Tests T022-T026 can all run in parallel (different test files)
- Implementation tasks are sequential (same class)

**Phase 4 (US2)**:
- Tests T040-T044 can run in parallel (different test files)
- Implementation tasks are sequential (same class)

**Phase 5 (US3)**: Tests T047-T052 can run in parallel (different test files being reorganized)

**Phase 6 (US4)**: 
- YottaDB lock implementation (T058-T060) independent from IRIS (T061-T063)
- Tests T066-T070 can run in parallel (different aspects)

**Phase 7 (US5)**:
- YottaDB transaction implementation (T071-T074) independent from IRIS (T075-T077)
- Tests T079-T083 can run in parallel

**Phase 8 (US6)**:
- YottaDB validation (T084, T086) independent from IRIS (T085, T087)
- Tests T090-T094 can run in parallel

**Phase 9 (Polish)**: All documentation tasks (T095-T103) can run in parallel

---

## Parallel Example: User Story 1 (YottaDB Backend)

```bash
# After Foundational phase completes, these can run in parallel:

# Developer A: Backend implementation
git checkout -b us1-yottadb-implementation
# Work on T010-T021 (sequential within backend class)

# Developer B: Test suite
git checkout -b us1-yottadb-tests
# Work on T022-T026 in parallel:
# - T022: test_basic_operations.py
# - T023: test_order_query.py  
# - T024: test_subscript_canonicalization.py
# - T025: test_connection_lifecycle.py
# - T026: test_exception_translation.py

# Once backend implementation (T010-T021) completes:
# - Merge backend implementation
# - Run test suite T022-T026
# - Checkpoint: YottaDB backend fully functional
```

---

## Parallel Example: Multiple User Stories

```bash
# After Foundational phase completes:

# Team 1: YottaDB backend (Phase 3)
git checkout -b us1-yottadb
# Implement T010-T021, test T022-T026

# Team 2: IRIS backend (Phase 4) - CAN RUN IN PARALLEL
git checkout -b us2-iris  
# Implement T027-T039, test T040-T044

# Both teams work independently (different files)
# No merge conflicts, no blocking

# Once BOTH complete:
# Team 3: Unified test suite reorganization (Phase 5)
git checkout -b us3-unified-tests
# Reorganize T045-T057
```

---

## Implementation Strategy

### MVP (Minimum Viable Product)

**Scope**: Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (US1 - YottaDB) = **26 tasks**

**Delivers**: 
- YottaDB backend with persistent global storage
- Basic test suite validating YottaDB functionality
- Foundation for adding more backends

**Validation**: 
```bash
# Run transpiled code inside YDB container
bash utils/ydb.sh uv run python -c "from m2py.runtime import get_global_storage; \
    import os; os.environ['M2PY_GLOBAL_BACKEND'] = 'yottadb'; \
    backend = get_global_storage(); \
    backend.set('^TEST', '1', value='persistent'); \
    print(backend.get('^TEST', '1'))"
```

### Incremental Delivery

1. **Release 1 (MVP)**: Phases 1-3 (YottaDB backend only) - 26 tasks
2. **Release 2**: Add Phase 4 (IRIS backend) - +18 tasks = 44 total
3. **Release 3**: Add Phase 5 (Unified test suite) - +13 tasks = 57 total  
4. **Release 4**: Add Phases 6-8 (Locks, Transactions, Config) - +31 tasks = 88 total
5. **Release 5 (Complete)**: Add Phase 9 (Polish) - +11 tasks = **99 total tasks**

### Quality Gates

**After each phase**:
- All tests for that phase pass
- Code review completed
- Documentation updated
- No breaking changes to existing functionality

**Before merging to main**:
- All 109 tasks complete
- Full test suite passes for all three backends (inmemory, yottadb, iris)
- Performance benchmarks meet 95th percentile <10ms goal
- Security review complete
- quickstart.md validated end-to-end

---

## Task Summary

**Total Tasks**: 109 (T001-T109)

**Tasks per User Story**:
- Setup: 4 tasks (T001-T004)
- Foundational: 5 tasks (T005-T009)
- US1 (YottaDB Backend - P1): 17 tasks (T010-T026)
- US2 (IRIS Backend - P1): 18 tasks (T027-T044)
- US3 (Unified Test Suite - P1): 13 tasks (T045-T057)
- US4 (Lock Operations - P2): 14 tasks (T058-T070a, including thread safety)
- US5 (Transaction Support - P2): 13 tasks (T071-T083)
- US6 (Environment Config - P2): 11 tasks (T084-T094)
- Polish: 14 tasks (T095-T109, including SSVN, InMemory validation, enhanced docs)

**Parallel Opportunities**: 
- Setup: 4 parallel tasks
- Foundational: 4 parallel tasks
- US1: 5 parallel test tasks
- US2: 5 parallel test tasks  
- US3: 6 parallel reorganization tasks
- US4: 6 parallel test tasks (+ 2 parallel implementation streams)
- US5: 5 parallel test tasks (+ 2 parallel implementation streams)
- US6: 5 parallel test tasks (+ 2 parallel implementation streams, can run anytime after Foundational)
- Polish: 13 parallel documentation/validation tasks

**Independent Test Criteria**:
- ✅ US1: YottaDB persists globals across process restarts
- ✅ US2: IRIS persists globals and supports namespaces
- ✅ US3: All backends pass identical test suite
- ✅ US4: Multi-process lock coordination works
- ✅ US5: Transaction rollback restores state
- ✅ US6: Backend selection via environment works

**Suggested MVP Scope**: Phases 1-3 (Setup + Foundational + US1 YottaDB) = 26 tasks

**Format Validation**: ✅ All tasks follow checklist format (checkbox, ID, labels, file paths)
