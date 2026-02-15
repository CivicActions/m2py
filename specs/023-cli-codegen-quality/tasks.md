# Tasks: CLI & Codegen Quality

**Input**: Design documents from `/specs/023-cli-codegen-quality/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Tests**: Included where specified in spec (FR-011, FR-014, FR-018 require automated tests).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project configuration — entry point, dependencies, ruff config

- [ ] T001 Add `[project.scripts]` entry point and ruff dependency to `pyproject.toml`
- [ ] T002 Add `[tool.ruff]` and `[tool.ruff.lint]` config (select E+F, ignore E501+E741) to `pyproject.toml`
- [ ] T003 [P] Add `ExprResultType` enum (STRING, NUMERIC, BOOLEAN_INT, NUMERIC_STRING, UNKNOWN) to `src/m2py/asg/enums.py`
- [ ] T004 [P] Add `result_type: Optional[ExprResultType] = None` field to `MExpr` in `src/m2py/asg/expressions.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core modules that ALL user stories depend on — type inference pass and ruff pipeline helpers

**⚠️ CRITICAL**: CLI (Phase 3) and code quality stories (Phases 4-6) depend on this phase

- [ ] T005 Implement `infer_expression_types(routine)` in `src/m2py/analysis/type_inference.py` per type mapping table in data-model.md
- [ ] T006 Integrate `infer_expression_types` as step 7 (after `compute_signatures`) in `src/m2py/codegen/__init__.py` `generate_python()` pipeline
- [ ] T007 [P] Implement `lint_fix(source, filename) -> str` helper in `src/m2py/cli/transpile.py` — subprocess `ruff check --fix --fix-only` via stdin pipe
- [ ] T008 [P] Implement `format_code(source, filename) -> str` helper in `src/m2py/cli/transpile.py` — subprocess `ruff format` via stdin pipe
- [ ] T009 Implement `TranspileResult` and `TranspileSummary` dataclasses in `src/m2py/cli/transpile.py` per data-model.md
- [ ] T010 Implement `transpile_file(input_path, output_path, no_format) -> TranspileResult` in `src/m2py/cli/transpile.py` — generate → lint-fix → format → write pipeline
- [ ] T011 Run existing test suite (`uv run pytest`) and verify no regressions from T003-T006 changes

**Checkpoint**: Foundation ready — type inference populates ASG, ruff helpers available, transpile pipeline works for a single file

---

## Phase 3: User Story 1 — Transpile a Single MUMPS File (Priority: P1) 🎯 MVP

**Goal**: A developer can run `m2py HELLO.m` and get a working `HELLO.py` on disk

**Independent Test**: Provide a known `.m` file, run `uv run m2py HELLO.m`, verify `.py` output exists, is valid Python, and produces correct output when executed

### Implementation

- [ ] T012 [US1] Implement argparse CLI with positional `paths`, `--output`/`-o`, `--verbose`/`-v`, `--no-format` in `src/m2py/cli/__init__.py` per contracts/cli.md
- [ ] T013 [US1] Implement `main(argv=None) -> int` entry point in `src/m2py/cli/__init__.py` — parse args, call `transpile_file()`, print summary to stderr, return exit code
- [ ] T014 [US1] Handle single-file path resolution: validate `.m` extension, compute output path (alongside input or under `--output` dir), create output directories
- [ ] T015 [US1] Handle error cases: file not found, permission denied, parse failure, unsupported features — report to stderr, return `TranspileResult(success=False)`
- [ ] T015a [US1] Handle edge case: MUMPS filename conflicts with Python reserved words or built-in module names (e.g., `IF.m`, `FOR.m`) — detect and warn or adjust output filename
- [ ] T016 [US1] Verify CLI end-to-end: create test `.m` file in `tmp/`, run `uv run m2py tmp/TEST.m`, verify `.py` output is valid and executable. Include an empty routine (no labels) to verify it produces valid minimal Python output.

**Checkpoint**: `uv run m2py FILE.m` works for single files with proper error handling

---

## Phase 4: User Story 2 — Transpile a Directory of MUMPS Files (Priority: P1)

**Goal**: A developer can run `m2py routines/` and transpile all `.m` files recursively with a success/failure summary

**Independent Test**: Create a directory with nested `.m` files, run `uv run m2py dir/`, verify all `.py` outputs exist with correct structure

### Implementation

- [ ] T017 [US2] Implement `transpile_paths(paths, output_dir, no_format) -> TranspileSummary` in `src/m2py/cli/transpile.py` — resolve files/dirs, glob `**/*.m`, call `transpile_file()` for each
- [ ] T018 [US2] Implement directory structure mirroring: when `--output` is specified, compute relative paths and mirror input layout in output dir
- [ ] T019 [US2] Implement batch summary output to stderr: `"Transpiled 47/50 files (3 failed)"`, list errors per failed file
- [ ] T020 [US2] Wire `transpile_paths()` into `main()` in `src/m2py/cli/__init__.py` — replace single-file logic with unified path handling
- [ ] T021 [US2] Handle edge cases: empty directories, non-`.m` files ignored, mixed success/failure continues processing all files
- [ ] T022 [US2] Verify batch end-to-end: create directory tree with `.m` files in `tmp/`, run `uv run m2py tmp/batch/`, verify all outputs and summary

**Checkpoint**: `uv run m2py DIR/` works for directories. US1 single-file still works (regression check).

---

## Phase 5: User Story 3 — Generated Code Passes Type Checking (Priority: P2)

**Goal**: All transpiled Python passes pyright `basic` with zero errors. Expression-level type inference populates ~85-90% of expressions with concrete types.

**Independent Test**: Transpile representative MUMPS files, run `uv run pyright --pythonversion 3.10` on output, assert exit code 0

### Implementation

- [ ] T023 [US3] Emit type hints on generated function return types in `src/m2py/codegen/routine.py` where all QUIT expressions share a `result_type`
- [ ] T024 [P] [US3] Emit type hints on simple SET assignments in `src/m2py/codegen/statements.py` where RHS `result_type` is known (not UNKNOWN)
- [ ] T025 [US3] Fix any pyright `basic` errors discovered in generated code — fix in codegen layer, not via `# type: ignore`
- [ ] T026 [US3] Add automated pyright validation test in `tests/unit/codegen/test_code_quality.py` — transpile ≥3 representative MUMPS files, run pyright basic, assert zero errors

**Checkpoint**: All transpiled output passes `pyright --pythonversion 3.10 -p <config>` in basic mode

---

## Phase 6: User Story 4 — Generated Code Passes Linting (Priority: P2)

**Goal**: All transpiled Python passes `ruff check` (E+F rules, ignoring E501/E741) with zero errors after post-gen lint-fix

**Independent Test**: Transpile representative MUMPS files via CLI, run `ruff check` on output, assert zero issues

### Implementation

- [ ] T027 [US4] Fix any remaining ruff E/F lint issues in codegen that `ruff check --fix` cannot auto-fix — adjust emitters in `src/m2py/codegen/`
- [ ] T028 [US4] Add targeted `# noqa` comments in codegen emitters for genuinely dynamic constructs (indirection, XECUTE-generated names) in `src/m2py/codegen/statements.py` and `src/m2py/codegen/expressions.py`
- [ ] T029 [US4] Add automated ruff lint validation test in `tests/unit/codegen/test_code_quality.py` — transpile ≥3 representative MUMPS files, run `ruff check`, assert zero issues

**Checkpoint**: All transpiled output passes `ruff check` with select E+F, ignore E501+E741

---

## Phase 7: User Story 5 — Generated Code is Auto-Formatted (Priority: P3)

**Goal**: Transpiled Python written to disk is already ruff-formatted; `ruff format --check` reports no changes

**Independent Test**: Transpile files via CLI, run `ruff format --check` on output directory, assert exit code 0

### Implementation

- [ ] T030 [US5] Verify `format_code()` pipeline integration end-to-end — transpile files via CLI, run `ruff format --check` on outputs, assert no changes
- [ ] T030a [US5] Verify FR-017 negative: calling `generate_python()` directly (without CLI) does NOT produce ruff-formatted output, confirming formatting is CLI-only
- [ ] T031 [US5] Verify `--no-format` flag skips formatting — transpile with `--no-format`, run `ruff format --check`, expect changes needed
- [ ] T032 [US5] Add automated format validation test in `tests/unit/codegen/test_code_quality.py` — transpile representative files, assert output is pre-formatted

**Checkpoint**: All CLI disk output is deterministically formatted. `--no-format` bypasses it.

---

## Phase 8: User Story 6 — Comprehensive Test Coverage (Priority: P3)

**Goal**: Identify and fill meaningful coverage gaps across the codebase; stop when remaining gaps are pedantic

**Independent Test**: Run `uv run pytest --cov=m2py --cov-report=term-missing`, verify all new tests pass and coverage improves without regressions

### Implementation

- [ ] T033 [US6] Run coverage analysis: `uv run pytest --cov=m2py --cov-report=term-missing` and identify uncovered lines per module
- [ ] T034 [US6] Add tests for meaningful gaps in `src/m2py/runtime/__init__.py` (78% → higher) — add to existing spec-aligned test files where appropriate
- [ ] T035 [US6] Add tests for meaningful gaps in `src/m2py/codegen/statements.py` (81% → higher) — add to existing spec-aligned test files
- [ ] T036 [P] [US6] Add tests for meaningful gaps in `src/m2py/codegen/expressions.py` (84% → higher) — add to existing spec-aligned test files
- [ ] T037 [P] [US6] Add tests for meaningful gaps in `src/m2py/analysis/semantic_analyzer.py` (85% → higher) — add to existing spec-aligned test files
- [ ] T038 [US6] Add tests for new code: `src/m2py/analysis/type_inference.py` in `tests/unit/analysis/test_type_inference.py`
- [ ] T039 [US6] Add tests for new code: `src/m2py/cli/` in `tests/integration/test_cli.py`
- [ ] T040 [US6] Re-run coverage and confirm no `# pragma: no cover` markers were added; remaining uncovered paths are documented as low-value

**Checkpoint**: Coverage improved for all targeted modules. All existing tests still pass.

---

## Phase 9: User Story 7 — Deduplicated Test Suite (Priority: P3)

**Goal**: Remove tests with substantial coverage overlap, reducing maintenance and runtime without decreasing coverage

**Independent Test**: Compare coverage before/after deduplication — coverage must not decrease, runtime should decrease or stay stable

### Implementation

- [ ] T041 [US7] Baseline: record current coverage numbers, test count, and execution time (`time uv run pytest --cov=m2py --cov-report=term-missing | tail -30`)
- [ ] T042 [US7] Analyze test overlap: identify test groups exercising the same code paths (use `--cov-report=json` and compare per-test coverage)
- [ ] T043 [US7] Remove redundant tests conservatively — for each removal, verify coverage does not decrease by re-running coverage
- [ ] T044 [US7] Final validation: compare coverage and test count against baseline from T041, confirm coverage ≥ baseline and test runtime ≤ baseline + 10%

**Checkpoint**: Test suite is leaner. Coverage unchanged or improved. Runtime stable or improved.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final integration verification and documentation

- [ ] T045 [P] Run full test suite with coverage: `uv run pytest --cov=m2py` — verify all tests pass, no regressions
- [ ] T046 [P] Run quickstart.md validation: execute all quickstart commands against `tmp/` test files
- [ ] T047 Update `main.py` to import and call `m2py.cli:main` instead of printing stub message
- [ ] T048 Verify `uv sync && uv run m2py --help` works from a clean environment
- [ ] T049 Run `uv run pytest` one final time to confirm green across all tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 - Single File)**: Depends on Phase 2
- **Phase 4 (US2 - Directory)**: Depends on Phase 3 (builds on single-file CLI)
- **Phase 5 (US3 - Type Checking)**: Depends on Phase 2 (type inference must be integrated)
- **Phase 6 (US4 - Linting)**: Depends on Phase 2 (ruff helpers must exist)
- **Phase 7 (US5 - Formatting)**: Depends on Phase 3 (needs CLI to write files)
- **Phase 8 (US6 - Coverage)**: Depends on all prior phases (tests new code from all stories)
- **Phase 9 (US7 - Dedup)**: Depends on Phase 8 (must fill gaps before removing tests)
- **Phase 10 (Polish)**: Depends on all prior phases

### User Story Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational) → ┬── Phase 3 (US1) → Phase 4 (US2) → Phase 7 (US5)
                                            ├── Phase 5 (US3)
                                            └── Phase 6 (US4)
                                            All above → Phase 8 (US6) → Phase 9 (US7) → Phase 10
```

### Parallel Opportunities

After Phase 2 completes:
- **Phases 3, 5, 6** can proceed in parallel (different files, independent concerns)
- Phase 4 must follow Phase 3 (extends single-file CLI to directories)
- Phase 7 must follow Phase 3 (needs CLI to write files to test formatting)

Within phases:
- T003 + T004 (enum + field) in parallel
- T007 + T008 (lint_fix + format_code helpers) in parallel
- T023 + T024 (return type hints + SET hints) in parallel
- T036 + T037 (expression + analyzer coverage) in parallel
- T045 + T046 (test suite + quickstart validation) in parallel

---

## Implementation Strategy

### MVP First (User Stories 1-2 Only)

1. Complete Phase 1: Setup (~4 tasks)
2. Complete Phase 2: Foundational (~7 tasks)
3. Complete Phase 3: US1 Single File (~5 tasks)
4. Complete Phase 4: US2 Directory (~6 tasks)
5. **STOP and VALIDATE**: `uv run m2py` works for files and directories
6. This delivers the core CLI value with working transpilation

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. US1 → Single file transpilation works (MVP!)
3. US2 → Batch/directory transpilation works
4. US3 + US4 → Generated code quality (type hints, lint-clean) — can be parallel
5. US5 → Auto-formatted output polish
6. US6 → Coverage gaps filled
7. US7 → Test suite optimized
8. Polish → Final validation

---

## Notes

- All file paths are relative to repository root (`/workspaces/m2py/`)
- Use `uv run` for all Python/pytest commands per constitution
- Use workspace `tmp/` for temporary test files, not `/tmp`
- Test `.m` files for CLI validation should be committed to `tmp/` or created inline in tests via `tmp_path` fixture
- `ruff` is available at `/usr/local/py-utils/bin/ruff` and will also be added as a project dependency
- Commit after each completed task or logical group
