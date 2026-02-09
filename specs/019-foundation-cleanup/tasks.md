# Tasks: Foundation & Cleanup

## Phase 1: Setup
- [x] T001 Create feature directory structure in /specs/019-foundation-cleanup
- [ ] T002 [P] Create new core module files: src/m2py/core/values.py, src/m2py/core/parsing.py, src/m2py/core/tokenizer.py (values.py done; parsing.py, tokenizer.py are US3)
- [ ] T003 [P] Create new test files: tests/unit/core/test_values.py, tests/unit/core/test_parsing.py, tests/unit/core/test_tokenizer.py (test_values.py done; test_parsing.py, test_tokenizer.py are US3)

## Phase 2: Foundational
- [x] T004 Update pyproject.toml and uv dependencies if needed for Decimal, textX (no changes needed — Decimal is stdlib, textX already a dep)
- [x] T005 [P] Add initial contracts to contracts/module-contracts.md for new modules
- [x] T006 [P] Add initial data model to data-model.md for new entities

## Phase 3: User Story 1 — Transpiler Produces Identical Output After Refactoring (P1)
- [x] T007 [US1] Move mumps_canonical_str, m_num, m_str, m_truth, m_compare, m_add, m_sub, m_mul to src/m2py/core/values.py
- [x] T008 [P] [US1] Update codegen/helpers.py to re-export from core/values.py
- [x] T009 [US1] Update runtime/helpers.py to delegate m_format_output to core/values.py
- [x] T010 [US1] Update SubscriptCanonicalizer in core/subscripts.py to delegate to core/values.py
- [x] T011 [US1] Update all deferred imports in runtime/__init__.py, runtime/helpers.py, runtime/globals.py, core/indirection.py to use core/values.py (17 value-model imports done; 1 generate_python remains — that's US2/T016)
- [x] T012 [US1] Remove duplicate _is_canonical_numeric from runtime/helpers.py
- [x] T013 [US1] Add/Update tests for value-model functions in tests/unit/core/test_values.py
- [x] T014 [US1] Run uv run pytest and verify zero failures, xfails, skips (5776 passed, 0 failed)

## Phase 4: User Story 2 — Runtime Can Be Used Without Codegen Layer (P2)
- [ ] T015 [US2] Move NameTranslator and translate_name to core/names.py (skip if already done)
- [ ] T016 [US2] Update runtime to inject generate_python as callback, not import from codegen
- [ ] T017 [US2] Add integration test: import runtime and core/values without codegen
- [ ] T018 [US2] Run uv run pytest and verify runtime-only tests pass

## Phase 5: User Story 3 — Contributor Can Modify Subscript Parsing in One Place (P2)
- [ ] T019 [US3] Move parse_subscripted_name and canonicalize_subscript to core/parsing.py
- [ ] T020 [US3] Move split_at_toplevel to core/tokenizer.py
- [ ] T021 [US3] Update runtime/__init__.py, core/scope.py, core/indirection.py to delegate to core/parsing.py and core/tokenizer.py
- [ ] T022 [US3] Add/Update tests for parsing/tokenizer in tests/unit/core/test_parsing.py and test_tokenizer.py

## Phase 6: User Story 4 — Contributor Can Add a New Kill-Like Command Without Duplication (P3)
- [ ] T023 [US4] Deduplicate kill analyzers in analysis/semantic_analyzer.py using _analyze_kill_like
- [ ] T024 [US4] Deduplicate DO/GOTO/JOB argument processing using _analyze_call_arguments
- [ ] T025 [US4] Add assertion to unwrap_expression for operator tails
- [ ] T026 [US4] Add/Update tests for kill/analyzer helpers

## Phase 7: User Story 5 — Contributor Can Walk ASG Statements with a Single Utility (P3)
- [ ] T027 [US5] Audit/extend MScope.walk_statements in asg/elements.py to handle else-scopes
- [ ] T028 [US5] Migrate direct-iteration sites to walk_statements where appropriate
- [ ] T029 [US5] Add/Update tests for ASG walker utility

## Phase 8: Polish & Cross-Cutting
- [ ] T030 [P] Update documentation in quickstart.md, research.md, data-model.md, contracts/module-contracts.md to reflect final module structure
- [ ] T031 [P] Final constitution check: verify all 8 principles in plan.md
- [ ] T032 [P] Run uv run pytest and verify all tests pass, zero failures/xfails/skips

## Dependencies
- User Story 1 (US1) must be completed before US2, US3, US4, US5
- US2, US3, US4, US5 can be executed in parallel after US1
- Foundational and setup phases are prerequisites for all user stories

## Parallel Execution Examples
- T002, T003 can be done in parallel
- T005, T006 can be done in parallel
- T008, T013 can be done in parallel
- T017, T022, T026, T029 can be done in parallel
- T030, T031, T032 can be done in parallel

## Implementation Strategy
- MVP: Complete User Story 1 (T007–T014)
- Incremental delivery: Each user story is independently testable
- All tasks follow strict checklist format (checkbox, ID, [P] if parallel, [USx] if user story, file path)

---

**Total tasks**: 32
**Tasks per user story**:
- US1: 8
- US2: 4
- US3: 4
- US4: 4
- US5: 3
- Setup/Foundational/Polish: 9

**Parallel opportunities**: 10
**Independent test criteria**: Each user story has explicit test tasks
**MVP scope**: User Story 1 (T007–T014)
**Format validation**: All tasks follow strict checklist format
