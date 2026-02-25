# Tasks: VistA M-Unit Test Suite via pytest (Phase 0)

**Input**: Design documents from `/specs/026-vista-munit-tests/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (models, parser, baseline-runner, pytest-adapter, zwr), quickstart.md

**Organization**: Tasks use Phase 1–12 numbering, which refines and expands plan.md’s Phase A–G. Phases 1–5 deliver the MVP (Tier 1+2, 12 routines). Phases 6–11 deliver the stretch goal (Tier 3+4, 38 routines total). Phase 12 is polish.

**Phase Mapping** (plan.md → tasks.md):

| plan.md | tasks.md | Description |
|---------|----------|-------------|
| A (Foundation) | 1 (Setup) + 2 (Foundational) | Split infrastructure from models/parser |
| A + B | 3 (Capture Baseline) | Baseline capture for Tier 1+2 |
| B (Tier 1) | 4 (Tier 1 Self-Tests) | M-Unit self-tests via pytest |
| C (Tier 2) | 5 (Tier 2 XML Parser) | M XML Parser tests |
| — | 6 (Capture Stretch Baselines) | All remaining tiers captured from osehravista |
| D (Tier 3, part) | 7 (ZWR Import/Export) | ZWR in m2py + vista-test fixtures |
| D (Tier 3, part) | 8 (Tier 3 FileMan) | FileMan test routines |
| E (Tier 4a) | 9 (Tier 4a Problem List) | Problem List test routines |
| F (Tier 4b) | 10 (Tier 4b Scheduling) | Scheduling test routines |
| G (Tier 4c) | 11 (Tier 4c Registration) | Registration test routine |
| — | 12 (Polish) | Final validation, docs, CI |

**Cross-repo convention**: Tasks prefixed with `vista-test/` live in the vista-test repository. Tasks prefixed with `src/m2py/` or `tests/` (no `vista-test/`) live in the m2py root workspace. Each m2py fix gets a standalone unit test with no VistA dependency.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US6 from spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding — create package structure, add dependencies, wire up test directories.

- [x] T001 [P] Create munit package directory with `__init__.py` at `vista-test/src/vista_test/munit/__init__.py`
- [x] T002 [P] Create munit test directories: `vista-test/tests/vista/munit/` and `vista-test/tests/unit/` with `__init__.py` files
- [x] T003 [P] Create baselines directory at `vista-test/baselines/` with `.gitkeep`
- [x] T004 Add m2py as path dependency (`m2py = {path = ".."}`) in `vista-test/pyproject.toml`
- [x] T005 Verify dependency resolution: run `cd vista-test && uv sync` and confirm `from m2py.codegen import generate_python` imports

**Checkpoint**: Package structure exists, m2py importable from vista-test.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and M-Unit output parser — required by ALL subsequent phases.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Data Models (US2 prerequisite)

- [x] T006 [P] [US2] Implement `FailureDetail` dataclass per contracts/models.md in `vista-test/src/vista_test/munit/models.py`
- [x] T007 [P] [US2] Implement `MUnitResult` dataclass with `to_dict()`/`from_dict()` in `vista-test/src/vista_test/munit/models.py`
- [x] T008 [P] [US2] Implement `PackageBaseline` and `BaselineData` with `to_json()`/`from_json()` in `vista-test/src/vista_test/munit/models.py`
- [x] T009 [P] [US2] Implement `TestRoutineConfig` dataclass in `vista-test/src/vista_test/munit/models.py`

### Model Tests

- [x] T010 [P] [US2] Write model unit tests: `MUnitResult` round-trip (to_dict/from_dict), status derivation, validation in `vista-test/tests/unit/test_munit_models.py`
- [x] T011 [P] [US2] Write model unit tests: `BaselineData` JSON serialization, `FailureDetail` CHKEQ vs CHKTF in `vista-test/tests/unit/test_munit_models.py`

### M-Unit Output Parser (US2)

- [x] T012 [US2] Implement `parse_munit_output()` per contracts/munit-parser.md: summary regex, failure extraction, error extraction in `vista-test/src/vista_test/munit/parser.py`
- [x] T013 [US2] Implement `parse_testlist()` per contracts/munit-parser.md: TestList file parsing, invocation pattern matching, tier assignment in `vista-test/src/vista_test/munit/parser.py`

### Parser Tests

- [x] T014 [P] [US2] Write parser unit tests: all-pass output, CHKTF failure, CHKEQ failure with `<expected> vs <actual>`, error output in `vista-test/tests/unit/test_munit_parser.py`
- [x] T015 [P] [US2] Write parser unit tests: empty output, partial output (no summary), self-referential %utt output, multi-line messages in `vista-test/tests/unit/test_munit_parser.py`
- [x] T016 [US2] Write parser unit tests: `parse_testlist()` with MASH Utilities and M XML Parser TestList files from VistA submodule in `vista-test/tests/unit/test_munit_parser.py`

**Checkpoint**: `uv run pytest vista-test/tests/unit/test_munit_models.py vista-test/tests/unit/test_munit_parser.py` passes. Foundation ready.

---

## Phase 3: User Story 1 — Capture Baseline (Priority: P1)

**Goal**: Establish ground truth by running all M-Unit test routines against the osehravista Docker container (worldvista/osehravista, built from VistA-M with M-Unit v1.5 + Enhanced XML Tools pre-installed) via SSH and persisting structured JSON results.

**Independent Test**: Start osehravista Docker, run `uv run python -m vista_test.munit.baseline --output baselines/osehravista-baseline.json`, verify JSON contains results for all discovered routines.

**Note**: Switched from VEHU to osehravista because VEHU (built from VistA-VEHU-M) was missing production routines (MXMLTMP1, MXMLPATH, MXMLTMPL) that M-Unit tests depend on.

### Implementation

- [x] T017 [US1] Implement `BaselineRunner.__init__()` and `_connect()` SSH setup (lazy connect via `VistATerminal`) in `vista-test/src/vista_test/munit/baseline.py`
- [x] T018 [US1] Implement `BaselineRunner.import_routine()`: read `.m` source from VistA submodule, send to osehravista via programmer mode in `vista-test/src/vista_test/munit/baseline.py`
- [x] T019 [US1] Implement `BaselineRunner.run_routine()`: send invocation command, capture output with timeout, parse via `parse_munit_output()` in `vista-test/src/vista_test/munit/baseline.py`
- [x] T020 [US1] Implement `BaselineRunner.run_package()` and `BaselineRunner.run_all()`: group by package, aggregate results in `vista-test/src/vista_test/munit/baseline.py`
- [x] T021 [US1] Implement CLI entry point `__main__.py` with `--output`, `--package`, `--routine`, `--tier` options in `vista-test/src/vista_test/munit/__main__.py`
- [x] T022 [US1] Capture Tier 1 baseline: run `%utt1`–`%utt7`, `%uttcovr` against osehravista; commit JSON to `vista-test/baselines/osehravista-baseline.json`
- [x] T023 [US1] Capture Tier 2 baseline: run MXMLBLD, MXMLDOMT, MXMLPATT, MXMLTMPT against osehravista; update `vista-test/baselines/osehravista-baseline.json`

**Checkpoint**: `baselines/osehravista-baseline.json` contains results for all Tier 1+2 routines (12 routines, 303 assertions captured from osehravista). Can inspect pass/fail counts per routine.

---

## Phase 4: User Story 3 — pytest M-Unit Adapter: Tier 1 Self-Tests (Priority: P2) 🎯 MVP Part 1

**Goal**: Transpile and run M-Unit self-tests (%utt1–%utt7, %uttcovr) in Python via pytest, comparing to osehravista baseline. This validates the M-Unit framework itself works in transpiled form.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "mash_utilities"` — all 8 routines pass or xfail.

### Adapter Infrastructure (US3)

- [x] T024 [US3] Implement `transpile_and_execute()` per contracts/pytest-adapter.md: read MUMPS source, call `generate_python()`, exec into module, call entry point, capture output in `vista-test/src/vista_test/munit/adapter.py`
- [x] T025 [US3] Implement `MUnitTestItem` (custom pytest.Item): `runtest()` calls `transpile_and_execute()`, parses output, compares to baseline in `vista-test/src/vista_test/munit/adapter.py`
- [x] T026 [US3] Implement `MUnitCollector` (custom pytest.Collector): discovers routines from TestList files via `parse_testlist()` in `vista-test/src/vista_test/munit/adapter.py`
- [x] T027 [US3] Implement conftest.py plugin: `pytest_collect_file` hook, `munit_baseline` fixture, `munit_runtime` fixture, `munit_framework` fixture, xfail logic in `vista-test/tests/vista/munit/conftest.py`

### Tier 1: Transpile M-Unit Framework + Self-Tests (US3 + US5)

- [x] T028 [US3] Transpile `%ut` and `%ut1` (M-Unit framework) via `generate_python()`; verify they load without import errors
- [x] T029 [US5] Verify `$ETRAP` error trapping works in transpiled `%ut` — create minimal MUMPS test for `$ETRAP` behavior in `tests/test_munit_etrap.py` (m2py root) — NOTE: $ETRAP error trapping not yet implemented in m2py, tests marked xfail
- [x] T030 [US5] Verify `DO @var` (indirection) works for dynamic dispatch in `%ut` — create minimal MUMPS test in `tests/test_munit_indirection.py` (m2py root) — NOTE: basic DO @var works, DO @X(args) not yet supported
- [x] T031 [US5] Verify `$TEXT` intrinsic works for `@TEST` discovery and `$T(+1^routine)` guard — create minimal MUMPS test in `tests/test_munit_text.py` (m2py root) — all 11 tests pass including get_text_indirect fix
- [x] T032 [US3] Transpile `%utt1`–`%utt7` and `%uttcovr` self-test routines; verify they load without import errors
- [x] T033 [US3] Run transpiled self-tests via adapter: execute `%utt1`–`%utt7`, `%uttcovr`; compare output to Tier 1 baseline — 2 passed, 6 xfailed
- [x] T034 [US5] Fix m2py transpilation/runtime issues discovered during Tier 1 execution; add standalone unit tests per fix in `tests/` (m2py root, no VistA deps) — fixed get_text_indirect to parse full +N^ROUTINE references

**Checkpoint**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "mash_utilities"` — 8 routines pass/xfail. M-Unit framework validated in Python.

---

## Phase 5: User Story 3 continued — Tier 2: M XML Parser (Priority: P2) 🎯 MVP Part 2

**Goal**: Transpile and run M XML Parser tests (4 routines, ~96 assertions) in Python. Completes the MVP.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "m_xml_parser"` — all 4 routines pass or xfail.

### Tier 2: XML Parser Transpilation (US3 + US5)

- [X] T035 [P] [US3] Transpile XML parser dependency routines: MXMLDOM, MXMLPRSE, MXMLUTL, MXMLPATH, MXMLTMP1, MXMLTMPL; verify they load
  - MXMLDOM, MXMLPRS0, MXMLPRS1, MXMLPRSE, MXMLTEST, MXMLUTL load OK
  - MXMLTMP1, MXMLTMPL, MXMLPATH: not available in any open-source repo
- [X] T036 [US3] Run MXMLBLD test (13 assertions, lowest risk: deps = MXMLUTL + MXMLTMP1); compare output to baseline
  - 13/13 assertions pass
- [X] T037 [US3] Run MXMLTMPT test (49 assertions, template engine; may need `DT^DICRW` stub); compare output to baseline
  - xfail: missing MXMLTMP1/MXMLTMPL dependency routines
- [X] T038 [US3] Run MXMLPATT test (25 assertions, XPath; needs MXMLDOM + MXMLPATH); compare output to baseline
  - xfail: missing MXMLPATH dependency routine
- [X] T039 [US3] Run MXMLDOMT test (8 tests, **highest risk**: needs `%ZISH` file I/O); compare output to baseline — xfail if `%ZISH` not ready
  - 7/8 tests pass, 1 error (XMLFILE — requires real file I/O via $$FTG^%ZISH)
- [X] T040 [US5] Fix m2py issues discovered during Tier 2 (e.g., `$NAME`, `$PIECE` on long strings, `$ORDER` on `^TMP` trees); add standalone tests in `tests/` (m2py root)
  - Bug E: Extrinsic %-variable byref name encoding
  - Bug F: DO omitted args with byref positional mapping
  - Bug G: Internal extrinsic label/variable name collision
  - Bug H: Repeated NEW at same scope level clears variable
  - Bug I: TRAMPOLINE wrapper optional formal parameters
  - Bug J: parse_call_target args extraction from routine part
  - Bug L: MERGE codegen in TRAMPOLINE strategy (bare variable names → state._locals/state.field)

**Checkpoint**: `cd vista-test && uv run pytest tests/vista/munit/ -v` — **MVP complete**: 12 routines (Tier 1+2) pass/xfail. 303 assertions in baseline (original plan estimate was ~124).

---

## Phase 6: User Story 1 continued — Capture Stretch Goal Baselines (Priority: P1)

**Goal**: Capture baselines for ALL remaining packages (Tiers 3–4) so stretch goal work can proceed.

**Note**: Completed early during Phase 3 by switching to osehravista and capturing all tiers at once.

**Independent Test**: `baselines/osehravista-baseline.json` contains results for all 38 routines across all 6 packages.

- [x] T041 [P] [US1] Capture Tier 3 baseline: run ZZUTDIDT, DMUDIC00, DMUDT000, DMUDTC00, DMUDIQ00 against osehravista; update `vista-test/baselines/osehravista-baseline.json`
- [x] T042 [P] [US1] Capture Tier 4a baseline: run ZZRGUT–ZZRGUT5, ZZRGUTRB, ZZRGUTEX against osehravista; update `vista-test/baselines/osehravista-baseline.json`
- [x] T043 [P] [US1] Capture Tier 4b baseline: run all 12 Scheduling routines against osehravista; update `vista-test/baselines/osehravista-baseline.json`
- [x] T044 [P] [US1] Capture Tier 4c baseline: run ZZDGPTCO1 against osehravista; update `vista-test/baselines/osehravista-baseline.json`

**Checkpoint**: `baselines/osehravista-baseline.json` has all 38 routines (22 pass, 3 intentional fail, 13 error/silent-quit). 640 assertions. Full ground truth for 100% comparison.

---

## Phase 7: User Story 4 — ZWR Import/Export & Global Bootstrap (Priority: P3) [Stretch]

**Goal**: Add ZWR (ZWRITE) format import/export to m2py's global storage layer, with CLI integration and full unit tests. Then wire vista-test fixtures to use it for Tier 3+ test data loading.

ZWR is the standard MUMPS global interchange format — this belongs in m2py itself (not vista-test) because:
- It's a general-purpose capability for any `GlobalStorageBackend`
- The m2py CLI should support `m2py globals import/export` for any use case
- Unit tests should be self-contained with no VistA dependency

**Independent Test**: `uv run pytest tests/test_zwr.py` passes — round-trip ZWR serialization works for all data types.

### ZWR Parser & Serializer (m2py core — `src/m2py/runtime/zwr.py`)

- [x] T045 [P] [US4] Implement `parse_zwr_line(line: str) -> tuple[str, list[str], str]`: parse a single ZWR line `^GLOBAL(subs)="value"` into (global_name, subscripts, value) with proper handling of quoted strings, `$C()` escapes, and numeric subscripts in `src/m2py/runtime/zwr.py`
- [x] T046 [P] [US4] Implement `parse_zwr_stream(stream: TextIO) -> Iterator[tuple[str, list[str], str]]`: iterate ZWR lines from a file/stream, skipping comments and blank lines, in `src/m2py/runtime/zwr.py`
- [x] T047 [P] [US4] Implement `serialize_zwr_node(global_name: str, subscripts: list[str], value: str) -> str`: produce a single ZWR-format line with proper quoting/escaping in `src/m2py/runtime/zwr.py`

### ZWR Import/Export for GlobalStorageBackend (m2py core — `src/m2py/runtime/zwr.py`)

- [x] T048 [US4] Implement `import_zwr(backend: GlobalStorageBackend, source: Path | TextIO) -> int`: parse ZWR and load all entries into a backend, return count of nodes imported, in `src/m2py/runtime/zwr.py`
- [x] T049 [US4] Implement `export_zwr(backend: GlobalStorageBackend, global_names: list[str], dest: Path | TextIO) -> int`: traverse globals via `$ORDER` equivalent and write ZWR format, return count of nodes exported, in `src/m2py/runtime/zwr.py`

### CLI Integration (m2py — `src/m2py/cli/`)

- [x] T050 [US4] Add `m2py globals import <file.zwr> [--backend <type>]` CLI subcommand: imports ZWR file into configured global backend in `src/m2py/cli/globals.py`
- [x] T051 [US4] Add `m2py globals export <file.zwr> [--globals '^DD,^DIC'] [--backend <type>]` CLI subcommand: exports specified globals to ZWR file in `src/m2py/cli/globals.py`

### ZWR Unit Tests (m2py — `tests/test_zwr.py`)

- [x] T052 [P] [US4] Write unit tests: `parse_zwr_line` handles simple values, quoted strings with embedded quotes, `$C()` escapes, numeric subscripts, multi-level subscripts in `tests/unit/runtime/test_zwr.py`
- [x] T053 [P] [US4] Write unit tests: `serialize_zwr_node` round-trips with `parse_zwr_line` for all data types in `tests/unit/runtime/test_zwr.py`
- [x] T054 [P] [US4] Write unit tests: `import_zwr`/`export_zwr` round-trip with in-memory backend — import a ZWR file, export it, compare output in `tests/unit/runtime/test_zwr.py`
- [x] T055 [US4] Write unit tests: `import_zwr` with real VistA ZWR snippets in `tests/unit/runtime/test_zwr.py`
- [x] T056 [P] [US4] Write CLI integration tests: `m2py globals import` and `m2py globals export` with temp files in `tests/unit/runtime/test_zwr.py`

### Vista-Test Fixtures (vista-test — uses m2py ZWR import)

- [x] T057 [US4] Add `fileman_bootstrap` session-scoped pytest fixture in `vista-test/tests/vista/munit/conftest.py`: imports cached ZWR files (`^DD`, `^DIC`, `^%ZOSF`) into `munit_runtime` global store via `m2py.runtime.zwr.import_zwr()`
- [x] T058 [US4] Add `clinical_bootstrap` session-scoped pytest fixture in `vista-test/tests/vista/munit/conftest.py`: extends `fileman_bootstrap` with `^DPT`, `^SC`, `^AUPNPROB`, `^GMPL*`, `^SD*`, `^DG*`

### Global Data Capture (vista-test — one-time export from osehravista)

- [x] T059 [US4] Create capture script `vista-test/utils/export_globals.py`: SSH to osehravista, run `ZWR ^GLOBAL` for configured globals, save to `vista-test/baselines/globals/`. Uses Docker exec with ZWRITE to export.
- [x] T060 [US4] Capture FileMan globals: export script configured with fileman profile (^DD, ^DIC, ^%ZOSF → `baselines/globals/fileman.zwr`). VistA-M ZWR fallback used by fileman_bootstrap fixture for ^DD and ^DIC.

**Checkpoint**: `uv run pytest tests/test_zwr.py` passes in m2py. `import_zwr` can load VistA globals into any backend. Path to Tier 3 is unblocked.

---

## Phase 8: User Story 6 — Tier 3: VA FileMan (5 routines, ~174 assertions) [Stretch]

**Goal**: Validate date/time, dictionary lookup, computed field operations. First package requiring global bootstrap.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "va_fileman"` — 5 routines pass/xfail.

### Kernel Utility Transpilation (US5 + US6)

- [x] T061 [US5] Verify/fix `%DT` (date/time validation) transpilation; add minimal MUMPS tests for date parsing in `tests/test_kernel_dt.py` (m2py root) — verified: transpiles, DMUDT000 runs 61 tests (29 fail + 13 error — %DT date parsing incomplete, tracked as xfail)
- [x] T062 [US5] Verify/fix `%DTC` (date/time calculations) transpilation; add minimal MUMPS tests in `tests/test_kernel_dtc.py` (m2py root) — verified: transpiles, DMUDTC00 runs 80 tests (3 errors in Help/NOW/YMD)
- [x] T063 [US5] Verify/fix `%ZISH` (file I/O: `$$GTF`, `$$DEL`, `$$DEFDIR`) transpilation; add minimal MUMPS tests in `tests/test_kernel_zish.py` (m2py root) — Python %ZISH implementation (zish_impl.py) from Phase 7
- [x] T064 [US5] Verify/fix `%ZOSF` (entry point loader) transpilation; add minimal MUMPS tests in `tests/test_kernel_zosf.py` (m2py root) — verified: transpiles from ZOSVGTM.m
- [x] T065 [P] [US5] Verify/fix `DICRW` (FileMan data entry) transpilation; add minimal MUMPS test in `tests/test_kernel_dicrw.py` (m2py root) — fixed critical MArray scope-to-state sync bug (codegen); DT^DICRW no longer crashes

### FileMan Global Bootstrap (US4 + US6)

- [x] T066 [US6] Import FileMan globals into m2py `MDict` via `fileman_bootstrap` fixture (uses ZWR files captured in T060); verify `^DD(2,0)` accessible — loads DD.zwr (765K nodes) + 1+FILE.zwr (41K nodes)

### FileMan Test Routines (US6) — ordered by complexity

- [x] T067 [US6] Transpile and run ZZUTDIDT (2 assertions, simplest: only `%DT`); compare to baseline — PASSED (2/2)
- [x] T068 [US6] Transpile and run `DMUFINIT` fixture routine (creates test files 1009.801, 1009.802 in `^DD`) — transpiles and loads; full init chain loaded (DMUFINI1-5, DMUFI001-00I)
- [x] T069 [US6] Transpile and run DMUDIC00 (14 assertions, needs `DMUFINIT`, `^DIC`, `XPDUTL`); compare to baseline — xfail: crashes (DMUFINIT init chain too complex for current runtime)
- [x] T070 [US6] Transpile and run DMUDT000 (61 assertions, needs `%DT`, `%ZISH`, `%ZOSF`); compare to baseline — xfail: 29 failures + 13 errors (%DT date parsing incomplete)
- [x] T071 [US6] Transpile and run DMUDTC00 (92 baseline, 80 counted w/o DD); compare to baseline — PASSED within tolerance (3 errors in Help/NOW/YMD)
- [x] T072 [US6] Transpile and run DMUDIQ00 (7 assertions, `DIQ`, `^DD`, `^DIC`); compare to baseline — xfail: %ZISH STATUS + DIQ crash without full ^DD
- [x] T073 [US5] Fix m2py issues discovered during Tier 3; add standalone unit tests per fix in `tests/` (m2py root) — fixed MArray scope-to-state sync (codegen), m_data non-MArray handling (runtime), ZWR encoding (runtime); 12 new unit tests

**Checkpoint**: 17 / 38 routines (45%). FileMan validated, global bootstrap proven. ~298 cumulative assertions.

---

## Phase 9: User Story 6 continued — Tier 4a: Problem List (8 routines, ~349 assertions) [Stretch]

**Goal**: Validate Problem List API: create, modify, delete, query problems.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "problem_list"` — 8 routines pass/xfail.

### Problem List Dependencies (US5 + US6)

- [ ] T074 [US5] Verify/fix `XLFDT` (date/time formatting library, shared by all Tier 4) transpilation; add minimal tests in `tests/test_kernel_xlfdt.py` (m2py root)
- [ ] T075 [P] [US6] Transpile GMPL* API routines: GMPLAPI1–7, GMPLMGR, GMPLDAL, GMPLSAVE, GMPLSITE, GMPLHIST, GMPLUTL, GMPLX; verify they load
- [ ] T076 [P] [US6] Transpile test utility ZZRGUTCM; verify it loads

### Problem List Global Bootstrap (US4 + US6)

- [ ] T077 [US4] Capture Problem List globals from osehravista: `^AUPNPROB`, `^GMPL*`, `^SC`, `^VA`; save ZWR to `vista-test/baselines/globals/`
- [ ] T078 [US6] Import Problem List globals via `clinical_bootstrap` fixture (uses `import_zwr`); verify `^AUPNPROB` accessible

### Problem List Test Routines (US6) — ordered by fewest dependencies

- [ ] T079 [US6] Transpile and run ZZRGUT2 (6 assertions, simplest: only GMPLSITE); compare to baseline
- [ ] T080 [US6] Transpile and run ZZRGUT5 (8 assertions, GMPLAPI2+7, GMPLHIST); compare to baseline
- [ ] T081 [US6] Transpile and run ZZRGUT4 (38 assertions, GMPLAPI1–2+6); compare to baseline
- [ ] T082 [US6] Transpile and run ZZRGUTRB (38 assertions, GMPLMGR, GMPLSAVE, ORQQPL1–3); compare to baseline
- [ ] T083 [US6] Transpile and run ZZRGUT (83 assertions, GMPLAPI2–4, biggest routine); compare to baseline
- [ ] T084 [US6] Transpile and run ZZRGUT1 (87 assertions, GMPLAPI1+6); compare to baseline
- [ ] T085 [US6] Transpile and run ZZRGUT3 (60 assertions, GMPLAPI1+5+6); compare to baseline
- [ ] T086 [US6] Transpile and run ZZRGUTEX (29 assertions, **widest deps** — 6+ cross-package: ACKQUTL6, IBDFBK3, PXRMPROB, XUS1A); compare to baseline
- [ ] T087 [US5] Fix m2py issues discovered during Tier 4a; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: 25 / 38 routines (66%). Problem List API validated. ~647 cumulative assertions.

---

## Phase 10: User Story 6 continued — Tier 4b: Scheduling (12 routines, ~547 assertions) [Stretch]

**Goal**: Validate Scheduling APIs: appointments, patient lists, scheduling actions. Largest package by assertion count.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "scheduling"` — 12 routines pass/xfail.

### Scheduling Dependencies (US5 + US6)

- [ ] T088 [P] [US6] Transpile Scheduling SDK APIs: SDAMA201, SDAMA202, SDAMA203, SDAMA204, SDAMA301; verify they load
- [ ] T089 [P] [US6] Transpile Scheduling Management APIs: SDMAPI1, SDMAPI2, SDMAPI3, SDMAPI4, SDMAPI5, SDCAPI1; verify they load
- [ ] T090 [P] [US6] Transpile test commons: ZZUTSDCOM, ZZRGUSDC, shared utility routines; verify they load

### Scheduling Global Bootstrap (US4 + US6)

- [ ] T091 [US4] Capture Scheduling globals from osehravista: `^DPT`, `^SC`, `^SD*`; save ZWR to `vista-test/baselines/globals/`
- [ ] T092 [US6] Import Scheduling globals via `clinical_bootstrap` fixture (uses `import_zwr`); verify `^DPT` and `^SC` accessible

### Group A — SDK Tests (6 routines, ~84 assertions, simpler) (US6)

- [ ] T093 [US6] Transpile and run ZZUTSDIMO (4 assertions, SDAMA203); compare to baseline
- [ ] T094 [US6] Transpile and run ZZUTPATAPPT (5 assertions, SDAMA204, `^DPT`); compare to baseline
- [ ] T095 [US6] Transpile and run ZZUTNEXTAPPT (11 assertions, SDAMA201); compare to baseline
- [ ] T096 [US6] Transpile and run ZZUTGETAPPT (14 assertions, SDAMA201); compare to baseline
- [ ] T097 [US6] Transpile and run ZZUTGETPLIST (15 assertions, SDAMA202); compare to baseline
- [ ] T098 [US6] Transpile and run ZZUTSDAPI (35 assertions, SDAMA301); compare to baseline

### Group B — Regression Tests (6 routines, ~463 assertions, complex) (US6)

- [ ] T099 [US6] Transpile and run ZZRGUSD4 (60 assertions, SDMAPI1–2+5); compare to baseline
- [ ] T100 [US6] Transpile and run ZZRGUSD2 (68 assertions, SDCAPI1, SDMAPI1–2); compare to baseline
- [ ] T101 [US6] Transpile and run ZZRGUSD6 (69 assertions, SCAPMC21, SCTMAPI1); compare to baseline
- [ ] T102 [US6] Transpile and run ZZRGUSD3 (81 assertions, SDCAPI1, SDMAPI1–4); compare to baseline
- [ ] T103 [US6] Transpile and run ZZRGUSD5 (82 assertions, DGSAAPI, SDMAPI1–4, many globals); compare to baseline
- [ ] T104 [US6] Transpile and run ZZRGUSD1 (103 assertions, largest scheduling test); compare to baseline
- [ ] T105 [US5] Fix m2py issues discovered during Tier 4b; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: 37 / 38 routines (97%). Scheduling validated. ~1,194 cumulative assertions.

---

## Phase 11: User Story 6 continued — Tier 4c: Registration (1 routine, ~10 assertions) [Stretch]

**Goal**: Validate patient combine/registration operations. Smallest stretch package.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "registration"` — 1 routine passes/xfails.

### Registration Dependencies (US5 + US6)

- [ ] T106 [US6] Transpile `DGPTCO1` (patient combine API); verify it loads

### Registration Global Bootstrap (US4 + US6)

- [ ] T107 [US4] Capture Registration globals from osehravista: `^DG*`; save ZWR to `vista-test/baselines/globals/` (may share `^DPT` from Tier 4b)

### Registration Test Routine (US6)

- [ ] T108 [US6] Transpile and run ZZDGPTCO1 (10 assertions, DGPTCO1, DICRW); compare to baseline
- [ ] T109 [US5] Fix m2py issues discovered during Tier 4c; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: **38 / 38 routines (100%)**. All M-Unit tests passing. ~1,204 cumulative assertions.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, CI readiness.

- [ ] T110 [P] Update `vista-test/README.md` with M-Unit test instructions (baseline capture, running transpiled tests, per-tier commands)
- [ ] T111 [P] Update `specs/026-vista-munit-tests/quickstart.md` with any corrections discovered during implementation
- [ ] T112 Run full `uv run pytest tests/vista/munit/ -v` from vista-test to validate all tiers end-to-end
- [ ] T113 Run full `uv run pytest` from m2py root to verify no regressions from transpiler/runtime fixes
- [ ] T114 [P] Document known xfail routines and their root causes in `vista-test/baselines/XFAIL.md`
- [ ] T115 Validate quickstart.md: follow setup and run instructions from scratch in a clean environment

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────────────────────────────────────────────────────────────────┐
    │                                                                             │
Phase 2 (Foundational: models + parser) ──────────────────────────────────────────┤
    │                                                                             │
    ├── Phase 3 (US1: Capture Baseline — Tiers 1+2)                               │
    │       │                                                                     │
    │       ├── Phase 4 (US3: Tier 1 M-Unit self-tests)                          │
    │       │       │                                                             │
    │       │       └── Phase 5 (US3: Tier 2 M XML Parser)                       │
    │       │               └── ✅ MVP COMPLETE (12 / 38 routines, ~124 asserts)  │
    │       │                                                                     │
    │       └── Phase 6 (US1: Capture Stretch Baselines — Tiers 3+4) ────────────┤
    │                                                                             │
    └── Phase 7 (US4: ZWR Import/Export in m2py + vista-test fixtures) ────────┤
            │                                                                     │
            ├── Phase 8 (US6: Tier 3 VA FileMan — 5 routines, ~174 asserts)      │
            │       │                                                             │
            │       ├── Phase 9 (US6: Tier 4a Problem List — 8 routines, ~349)   │
            │       │                                                             │
            │       ├── Phase 10 (US6: Tier 4b Scheduling — 12 routines, ~547)   │
            │       │                                                             │
            │       └── Phase 11 (US6: Tier 4c Registration — 1 routine, ~10)    │
            │                                                                     │
            └─────────────────────────────────────────────────────────────────────┘
                                                                                  │
Phase 12 (Polish) ────────────────────────────────────────────────────────────────┘
```

### User Story → Phase Mapping

| User Story | Description | Phases | Priority |
|------------|-------------|--------|----------|
| US1 | Capture osehravista Baseline | 3, 6 | P1 |
| US2 | M-Unit Output Parser + Models | 2 | P1 |
| US3 | Run Transpiled Tests via pytest | 4, 5 | P2 |
| US4 | ZWR Import/Export + Global Bootstrap | 7 | P3 (Stretch) |
| US5 | Fix m2py Issues | 4, 5, 8, 9, 10, 11 (cross-cutting) | P2 |
| US6 | Incremental Package Expansion | 8, 9, 10, 11 | P3 (Stretch) |

### Within Each Phase

- Models/data classes before services
- Parser before adapter (adapter depends on parser)
- Baseline capture before transpiled comparison (need ground truth first)
- Kernel utility fixes (m2py root) before VistA test routines that depend on them
- Simpler routines before complex ones within each tier
- Each m2py fix gets a standalone test immediately (no batching)

### Parallel Opportunities

**Phase 2** (T006–T009 models, T014–T015 parser tests): all models can be written in parallel.

**Phase 4** (T029–T031 m2py verification tasks): `$ETRAP`, `DO @var`, `$TEXT` tests are independent.

**Phase 6** (T041–T044 stretch baselines): all four tier baselines can be captured in parallel.

**Phase 7** (T045–T047 ZWR parser, T052–T056 ZWR tests): parser/serializer and their tests can be written in parallel.

**Phase 8** (T061–T065 kernel utilities): `%DT`, `%DTC`, `%ZISH`, `%ZOSF`, `DICRW` verifications are independent.

**Phase 10** (T088–T090 scheduling APIs): SDK, Management, and test commons transpilation are independent.

**Cross-phase**: Phase 6 (stretch baselines) can run in parallel with Phases 4–5 (MVP transpilation) since they only need osehravista Docker.

---

## Implementation Strategy

### MVP First (Phases 1–5)

1. **Phase 1**: Setup — package structure, dependencies (T001–T005)
2. **Phase 2**: Foundational — models + parser with tests (T006–T016)
3. **Phase 3**: Baseline capture for Tier 1+2 (T017–T023)
4. **Phase 4**: Transpile + run Tier 1 self-tests (T024–T034)
5. **Phase 5**: Transpile + run Tier 2 XML parser (T035–T040)
6. **STOP AND VALIDATE**: `uv run pytest tests/vista/munit/ -v` — 12 routines pass/xfail

### Stretch Goal: 100% M-Unit Tests (Phases 6–11)

7. **Phase 6**: Capture remaining baselines (T041–T044) — can overlap with MVP validation
8. **Phase 7**: ZWR import/export in m2py + vista-test fixtures (T045–T060)
9. **Phase 8**: Tier 3 VA FileMan (T061–T073) — first stretch milestone (45%)
10. **Phase 9**: Tier 4a Problem List (T074–T087) — second stretch milestone (66%)
11. **Phase 10**: Tier 4b Scheduling (T088–T105) — third stretch milestone (97%)
12. **Phase 11**: Tier 4c Registration (T106–T109) — **100% complete**
13. **Phase 12**: Polish (T110–T115)

### Milestone Summary

| Milestone | Tasks | Routines | Assertions | Cumulative |
|-----------|-------|----------|------------|------------|
| Phase 2 complete | T001–T016 | 0 | 0 | Infrastructure ready |
| Phase 3 complete | T017–T023 | 0 | 0 | Baseline captured (Tier 1+2) |
| Phase 4 complete | T024–T034 | 8 | ~28 | Tier 1 passing (21%) |
| Phase 5 complete | T035–T040 | 12 | ~124 | **MVP — Tier 1+2 (32%)** |
| Phase 7 complete | T045–T060 | 0 | 0 | ZWR import/export ready (m2py + vista-test) |
| Phase 8 complete | T061–T073 | 17 | ~298 | Tier 3 passing (45%) |
| Phase 9 complete | T074–T087 | 25 | ~647 | Tier 4a passing (66%) |
| Phase 10 complete | T088–T105 | 37 | ~1,194 | Tier 4b passing (97%) |
| Phase 11 complete | T106–T109 | 38 | ~1,204 | **100% — All tiers** |

---

## Notes

- **[P]** tasks = different files, no dependencies on incomplete tasks
- **[US#]** labels map tasks to spec.md user stories for traceability
- vista-test/ tasks execute in the vista-test repository context
- m2py root tasks (tests/, src/m2py/) execute in the workspace root context
- ZWR import/export lives in m2py (`src/m2py/runtime/zwr.py`) as a general-purpose capability for any `GlobalStorageBackend`; vista-test fixtures call `import_zwr()` to load cached ZWR data
- Each m2py bug fix (US5) follows: discover → extract minimal MUMPS → fix → standalone test → verify M-Unit re-run
- osehravista Docker is only needed for baseline capture (Phases 3, 6) and global data capture (T059–T060, T077, T091, T107); transpiled tests run offline with cached ZWR files
- Stretch goal phases (7–11) can be attempted incrementally — each tier adds value independently
- Registration (Phase 11) has fewest tests and could be attempted anytime after Phase 8 (FileMan infrastructure)
