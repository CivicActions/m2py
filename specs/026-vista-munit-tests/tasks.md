# Tasks: VistA M-Unit Test Suite via pytest (Phase 0)

**Input**: Design documents from `/specs/026-vista-munit-tests/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (models, parser, baseline-runner, pytest-adapter, zwr), quickstart.md

**Organization**: Tasks use Phase 1–13 numbering, which refines and expands plan.md’s Phase A–G. Phases 1–5 deliver the MVP (Tier 1+2, 12 routines). Phases 6–12 deliver the stretch goal (Tier 3+4, 38 routines total). Phase 8 adds backend compatibility for YottaDB and IRIS. Phase 13 is polish.

**Phase Mapping** (plan.md → tasks.md):

| plan.md | tasks.md | Description |
|---------|----------|-------------|
| A (Foundation) | 1 (Setup) + 2 (Foundational) | Split infrastructure from models/parser |
| A + B | 3 (Capture Baseline) | Baseline capture for Tier 1+2 |
| B (Tier 1) | 4 (Tier 1 Self-Tests) | M-Unit self-tests via pytest |
| C (Tier 2) | 5 (Tier 2 XML Parser) | M XML Parser tests |
| — | 6 (Capture Stretch Baselines) | All remaining tiers captured from osehravista |
| D (Tier 3, part) | 7 (ZWR Import/Export) | ZWR in m2py + munit fixtures |
| — | 8 (Backend Compatibility) | YottaDB/IRIS testing infrastructure + regression fixes |
| D (Tier 3, part) | 9 (Tier 3 FileMan) | FileMan test routines |
| E (Tier 4a) | 10 (Tier 4a Problem List) | Problem List test routines |
| F (Tier 4b) | 11 (Tier 4b Scheduling) | Scheduling test routines |
| G (Tier 4c) | 12 (Tier 4c Registration) | Registration test routine |
| — | 13 (Polish) | Final validation, docs, CI |

**Cross-repo convention**: _Originally, tasks prefixed with `vista-test/` lived in a separate vista-test repository. These have been consolidated into m2py itself._ Tasks referencing `tests/functional/munit/` or `tests/unit/` live in the m2py workspace. M-Unit library code is in `tests/functional/munit/lib/`. Each m2py fix gets a standalone unit test with no VistA dependency.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US6 from spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding — create package structure, add dependencies, wire up test directories.

_Originally in a separate vista-test repo; consolidated into m2py `tests/functional/munit/` with library code in `tests/functional/munit/lib/`._

- [x] T001 [P] Create munit package directory with `__init__.py` at `vista-test/src/vista_test/munit/__init__.py`
- [x] T002 [P] Create munit test directories: `vista-test/tests/vista/munit/` and `vista-test/tests/unit/` with `__init__.py` files
- [x] T003 [P] Create baselines directory at `vista-test/baselines/` with `.gitkeep`
- [x] T004 Add m2py as path dependency (`m2py = {path = ".."}`) in `vista-test/pyproject.toml`
- [x] T005 Verify dependency resolution: run `cd vista-test && uv sync` and confirm `from m2py.codegen import generate_python` imports

**Checkpoint**: Package structure exists, m2py importable from vista-test.

_After consolidation: `tests/functional/munit/` structure exists within m2py._

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and M-Unit output parser — required by ALL subsequent phases.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

_Originally in vista-test; models and parser now live in `tests/functional/munit/lib/`._

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

_After consolidation: `uv run pytest tests/unit/munit/` or test via functional munit tests._

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

_Note: After consolidation, the equivalent command is `uv run pytest tests/functional/munit/ -v -k "mash_utilities"`._

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

_After consolidation: `uv run pytest tests/functional/munit/ -v -k "mash_utilities"`._

---

## Phase 5: User Story 3 continued — Tier 2: M XML Parser (Priority: P2) 🎯 MVP Part 2

**Goal**: Transpile and run M XML Parser tests (4 routines, ~96 assertions) in Python. Completes the MVP.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "m_xml_parser"` — all 4 routines pass or xfail.

_Note: After consolidation, the equivalent command is `uv run pytest tests/functional/munit/ -v -k "m_xml_parser"`._

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

_After consolidation: `uv run pytest tests/functional/munit/ -v` — MVP complete._

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

**Goal**: Add ZWR (ZWRITE) format import/export to m2py's global storage layer, with CLI integration and full unit tests. Then wire M-Unit fixtures to use it for Tier 3+ test data loading.

ZWR is the standard MUMPS global interchange format — this belongs in m2py itself because:
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

### M-Unit Test Fixtures (uses m2py ZWR import)

- [x] T057 [US4] Add `fileman_bootstrap` session-scoped pytest fixture in `tests/functional/munit/conftest.py`: imports cached ZWR files (`^DD`, `^DIC`, `^%ZOSF`) into `munit_runtime` global store via `m2py.runtime.zwr.import_zwr()`
- [x] T058 [US4] Add `clinical_bootstrap` session-scoped pytest fixture in `tests/functional/munit/conftest.py`: extends `fileman_bootstrap` with `^DPT`, `^SC`, `^AUPNPROB`, `^GMPL*`, `^SD*`, `^DG*`

### Global Data Capture (one-time export from osehravista)

- [x] T059 [US4] Create capture script `utils/export_globals.py`: SSH to osehravista, run `ZWR ^GLOBAL` for configured globals, save to `tests/functional/munit/baselines/globals/`. Uses Docker exec with ZWRITE to export.
- [x] T060 [US4] Capture FileMan globals: export script configured with fileman profile (^DD, ^DIC, ^%ZOSF → `baselines/globals/fileman.zwr`). VistA-M ZWR fallback used by fileman_bootstrap fixture for ^DD and ^DIC.

**Checkpoint**: `uv run pytest tests/test_zwr.py` passes in m2py. `import_zwr` can load VistA globals into any backend. Path to Tier 3 is unblocked.

### DIKC Compiled Cross-Reference Engine (m2py fixes — resolves DMUFINIT tolerated extras)

**Goal**: Fix the DIKC compiled cross-reference chain so that DMUFINIT produces exact-match output with no tolerated extras or known mismatches. All 4 tolerated entries share a common root cause in INDEX^DIKC → LOADALL^DIKC1 → FIREALL → FIRE → SETXARR → XECUTE.

- [ ] T116 [US6] Debug DIKC LOADALL^DIKC1 @DIKTMP compilation: verify `"SS"` (subscript-used) flags are set correctly for subscript-type cross-reference fields, so SETXARR's `DINULL` null-subscript guard works. Root cause of D-xref empty-date extras (`^DMU(1009.801,"D","",9)`, `^DMU(1009.801,"D","",13)`).
- [ ] T117 [US6] Fix DIKC FIRE/SETXARR null-subscript detection: ensure `I $G(X(DIKO))="",$G(@DIKTMP@(DIFILE,DIXR,DIKO,"SS")) S DINULL=1` correctly prevents xref entries with empty subscript values. Add m2py unit tests for SETXARR with null vs non-null subscript fields in `tests/` (m2py root).
- [ ] T118 [US6] Fix DIKC FIREALL/FIRESUB sub-file recursion: investigate why `^DD(1009.802,0,0)` header node is written — FIRESUB should not recurse into DD metadata (field 0). Likely DIMF or `$D(@DISBROOT)` check misbehaving. Add m2py unit test for FIRESUB recursion boundary.
- [ ] T119 [US6] Fix DIKC FIRE DIKON branch + DIKK2 UNIQUE key validation: in the `DIKON'=""` branch, `$$UNIQUE^DIKK2` should detect duplicate ZIP CODE key and kill entry 7 (`^DMU(1009.802,36,1,1,1,7,0)=12208`). Determine whether DIKON is incorrectly empty (wrong branch) or DIKK2 uniqueness check fails. Add m2py unit test.
- [ ] T120 [US6] Remove `_KNOWN_TOLERATED_EXTRAS` and `_KNOWN_MISMATCHES` from `tests/functional/munit/test_dmufinit.py`: once T116–T119 are fixed, delete toleration sets, remove associated filtering logic, and update comments. DMUFINIT test should pass with zero extras, zero mismatches, zero missing.
- [ ] T121 [US6] Add m2py unit tests for DIKC chain edge cases: compiled xref with mixed subscript/non-subscript fields, FIREALL header-node counting across sub-files, UNIQUE key constraint enforcement. Tests in `tests/` (m2py root), no VistA dependency.

**Checkpoint**: DMUFINIT test passes with exact match — `_KNOWN_TOLERATED_EXTRAS` and `_KNOWN_MISMATCHES` removed. DIKC compiled cross-reference engine handles null subscripts, sub-file recursion, and key uniqueness correctly.

---

## Phase 8: Backend Compatibility — YottaDB & IRIS Testing Infrastructure + Regression Fixes

**Goal**: Make M-Unit functional tests runnable against YottaDB and IRIS backends (using m2py's Docker infrastructure), fix m2py regressions found with external backends, and fix all M-Unit test failures when running against these backends.

**Context**: m2py supports pluggable backends via `M2PY_GLOBAL_BACKEND` env var (inmemory, sqlite, yottadb, iris). The m2py test suite uses `--backend` CLI option (propagated to env var). The YottaDB backend runs inside Docker (`utils/ydb.sh` / `Dockerfile.yottadb`); the IRIS backend uses a Docker container for the server but runs Python locally (`utils/iris.sh`). M-Unit tests were consolidated from the separate vista-test repo into `tests/functional/munit/` within m2py.

**Known issues from initial backend testing**:
- m2py + YottaDB: 55 failures (lock indirection, residual global state between tests, V4SYSTEM/V4PRIN/V4JOB system-specific, per02276, MERGE tests)
- m2py + IRIS: 207 failures (above + empty string subscripts unsupported, IRIS-specific API differences)
- M-Unit + YottaDB: ZWR bootstrap too slow — 843K `set()` calls over C binding takes 18+ minutes
- M-Unit + IRIS: DMUFINIT crashes with `<SUBSCRIPT>` error on `$ORDER(^UTILITY("%RCR","","1","0"))` — IRIS doesn't support empty string subscripts

**Independent Test**: `bash utils/ydb.sh uv run pytest tests/functional/munit/ --backend yottadb -n0` and `bash utils/iris.sh uv run pytest tests/functional/munit/ --backend iris -n0` both pass/xfail with no unexpected failures.

### M-Unit Backend Infrastructure (US3 + US5)

_Originally planned for a separate vista-test repo; consolidated into m2py `tests/functional/munit/` during migration._

- [x] T122 [US3] Add `--backend` CLI option to `tests/functional/munit/conftest.py`: register `pytest_addoption` with choices inmemory/yottadb/iris, propagate to `M2PY_GLOBAL_BACKEND` env var (mirrors m2py’s pattern in `tests/conftest.py`)
- [x] T123 [US3] Add backend-specific pytest markers: register `backend_yottadb`, `backend_iris`, `backend_inmemory` markers in `pyproject.toml` and implement `pytest_collection_modifyitems` skip logic in `tests/functional/munit/conftest.py`
- [x] T124 [P] [US3] Add `yottadb` and `iris` optional dependency groups to `pyproject.toml`: `yottadb = ["yottadb>=2.0.0"]` and `backend = ["intersystems-irispython>=5.3.1"]`
- [x] T125 [P] [US3] Create `Dockerfile.yottadb` for running tests inside YottaDB Docker: installs m2py + deps, sets `M2PY_GLOBAL_BACKEND=yottadb`
- [x] T126 [P] [US3] Create `utils/ydb.sh` wrapper: auto-builds Docker image, mounts workspace, runs commands inside container with YDB env configured
- [x] T127 [P] [US3] Create `utils/iris.sh` wrapper: auto-starts IRIS container, exports connection env vars, runs commands locally with `M2PY_GLOBAL_BACKEND=iris`

### ZWR Bulk Import Optimization (US4 + US5)

- [x] T128 [US4] Implement `import_zwr_ydb_native(path: Path) -> int` in `src/m2py/runtime/zwr.py`: use YottaDB's `MUPIP LOAD` for bulk ZWR import when running inside a YDB environment (subprocess call to `mupip load`), falling back to line-by-line `set()` when MUPIP unavailable. Target: 843K nodes in <30s vs 18+ minutes
- [x] T129 [US4] Add `import_zwr_bulk()` dispatch function in `src/m2py/runtime/zwr.py`: auto-detect backend type and use native bulk import when available (MUPIP LOAD for YDB), fall back to standard line-by-line import. Update `import_zwr()` to call this dispatcher
- [x] T130 [P] [US4] Write unit tests for `import_zwr_ydb_native()`: verify MUPIP LOAD subprocess invocation, fallback behavior when MUPIP unavailable, node count reporting in `tests/unit/runtime/test_zwr.py`
- [x] T131 [US4] Implement IRIS bulk import via `iris.cls` routine: write a helper that sends ZWR file contents through IRIS `%SYS.GlobalQuery` or uses `$SYSTEM.OBJ.Load()` for batch global import, avoiding per-node TCP round-trips. Add to `src/m2py/runtime/zwr.py`

### Fix m2py YottaDB Backend Regressions (US5)

- [x] T132 [US5] Fix lock indirection tests failing with YottaDB backend: investigate whether lock state leaks between tests or if the YDB lock API behaves differently from inmemory; add test isolation (unlock-all in teardown) in `tests/conftest.py` or fix lock cleanup in `src/m2py/runtime/yottadb_backend.py` — **Fixed**: yield-based cleanup fixture calls `kill_all()` + `releaseAllLocks()` per test; YDB `close()` releases locks; unit tests pass. **Residual**: V3LOCK MVTS has 15 cross-process lock FAILs on YDB in CI (passes on inmemory/SQLite) — JOB'd child processes in Docker don't share YDB lock space correctly. Tracked separately.
- [x] T133 [US5] Fix residual global state failures in YottaDB: tests that pass with inmemory but fail with YDB due to leftover globals from previous tests. Add per-test global cleanup fixture or use YDB transaction rollback in `tests/conftest.py` — **Fixed**: `cleanup_globals` yield fixture in conftest.py calls `kill_all()` before each test; YDB `kill_all()` enumerates via `yottadb.subscript_next()` instead of tracking names; system globals protected. 24 standalone tests in test_backend_fixes.py.
- [x] T134 [US5] Fix V4SYSTEM, V4PRIN, V4JOB MVTS test failures with YottaDB: these test system-specific intrinsic variables (`$SYSTEM`, `$PRINCIPAL`, `$JOB`). Investigate whether YDB returns different values and update test expectations or skip with `backend_yottadb` marker in test files under `tests/functional/` — **Fixed**: root causes were codegen bugs (not backend-specific): missing `$PRINCIPAL` intrinsic, `$JOB` returning wrong PID, `$SYSTEM` format. All three routines pass on all backends now (verified in CI).
- [x] T135 [US5] Fix per02276 MVTS test failure with YottaDB: investigate root cause (likely MERGE or $ORDER edge case with real YDB storage) and fix in `src/m2py/runtime/` or mark as backend-specific xfail with standalone m2py unit test — **Fixed**: root cause was `merge_tree` passing int/float MArray values to `set()` without stringification, crashing `.encode()` on YDB/IRIS. Fixed with defensive `str()` conversion. per02276 passes on all backends.
- [x] T136 [US5] Fix MERGE test failures with YottaDB backend: investigate whether MERGE codegen produces invalid YDB API calls or if subscript ordering differs; fix in `src/m2py/runtime/yottadb_backend.py` or `src/m2py/codegen/statements.py` — **Fixed**: same root cause as T135 (value stringification in merge_tree). YDB `_merge_tree_recursive` also had a latent key-iteration bug fixed. All MERGE tests pass on all backends.

### Fix m2py IRIS Backend Regressions (US5)

- [x] T137 [US5] Handle IRIS empty string subscript limitation: add guard in `src/m2py/runtime/iris_backend.py` `set()`/`get()`/`order()` methods to detect empty-string subscripts and either raise a clear error or remap to a sentinel value, with comprehensive unit tests in `tests/runtime/backend/` — **Fixed**: IRIS backend raises clear `<SUBSCRIPT>` error on empty subscripts; empty-string subscript tests skip on IRIS with documented reason; canonical string coercion applied to all backends uniformly. Documented in runtime.md and limitations.md.
- [x] T138 [US5] Fix IRIS-specific test failures beyond empty subscripts: categorize the ~150 additional IRIS failures (vs YDB's 55), determine which are IRIS API limitations vs m2py bugs, mark genuine IRIS limitations with `backend_iris` skip markers, fix m2py bugs with standalone tests — **Fixed**: commit 5269f632 reduced 255 IRIS failures to 0. Root causes: missing `_naked_indicator` property, missing `_lock_table` shim, `JOB` not passing `--backend` to children, `kill_all()` not enumerating via SQL, locks not released on `close()`. Two genuine IRIS limitations skipped with inline reasons: `$INCREMENT` non-transactional, lock counting semantics.
- [x] T139 [P] [US5] Add backend compatibility test matrix documentation in `docs/runtime.md`: document known backend differences (empty subscripts, lock semantics, system variables), supported operations per backend, and test skip reasons — **Done**: runtime.md has full 4-backend comparison matrix (10+ dimensions); limitations.md has YDB-specific and IRIS-specific limitation sections with test skip reasons; SSVN backend comparison table included.

### Fix M-Unit YottaDB Failures (US6)

- [x] T140 [US6] Wire `fileman_bootstrap` to use bulk ZWR import: update `tests/functional/munit/conftest.py` to call `import_zwr_bulk()` (from T129) instead of `import_zwr()` for the 843K-node DD/DIC/INDEX load, making YDB bootstrap complete in <60s — **Done differently**: T129 implemented bulk import via backend polymorphism instead of a separate `import_zwr_bulk()`. `conftest.py` calls `import_zwr(backend, path)` → `backend.import_zwr(source)` → YDB's `import_zwr()` dispatches to MUPIP LOAD natively when available (line 1080 of yottadb_backend.py). No code change needed.
- [x] T141 [US6] Run all M-Unit tests with YottaDB backend end-to-end: `bash utils/ydb.sh uv run pytest tests/functional/munit/ --backend yottadb -n0 -v`. Fix or xfail any failures discovered — **Done**: CI matrix (`ci.yml`) runs munit split on YDB backend; all 18 tests pass (7 passed, 11 xfailed). ubicloud-standard-2 runner allocated for YDB munit.
- [x] T142 [US5] Fix m2py issues discovered during M-Unit YottaDB testing: each bug gets a standalone unit test in `tests/` (m2py root, no VistA dependency), then re-verify M-Unit tests pass — **Done**: No m2py bugs discovered during YDB M-Unit testing; all issues were resolved in prior phases (T132-T136).

### Fix M-Unit IRIS Failures (US6)

- [x] T143 [US6] Fix DMUFINIT `<SUBSCRIPT>` error with IRIS backend: the empty string subscript in `$ORDER(^UTILITY("%RCR","","1","0"))` crashes IRIS. Either (a) fix the transpiled code to avoid empty-string subscripts when on IRIS, (b) add an IRIS-specific codepath in the runtime (M2PY.Helper GOrder already handles this), or (c) xfail DMUFINIT on IRIS with a clear skip reason in `tests/functional/munit/test_dmufinit.py` — **Done via (b)**: M2PY.Helper ObjectScript class on the IRIS server handles `GOrder` with null subscripts, avoiding the `<SUBSCRIPT>` error. All 18 munit tests pass on IRIS (7 passed, 11 xfailed).
- [x] T144 [US6] Run all M-Unit tests with IRIS backend end-to-end: `bash utils/iris.sh uv run pytest tests/functional/munit/ --backend iris -n0 -v`. Fix or xfail any failures discovered — **Done**: CI matrix (`ci.yml`) runs munit split on IRIS backend with custom `m2py-iris-img` (built from Dockerfile.iris); all 18 tests pass (7 passed, 11 xfailed).
- [x] T145 [US5] Fix m2py issues discovered during M-Unit IRIS testing: each bug gets a standalone unit test in `tests/` (m2py root, no VistA dependency), then re-verify M-Unit tests pass — **Done**: No m2py bugs discovered during IRIS M-Unit testing; IRIS null-subscript issue resolved in T143 via M2PY.Helper GOrder.

### CI Integration (US3)

- [x] T146 [P] [US3] Add backend test invocation examples to `docs/testing.md`: document how to run M-Unit tests with each backend, Docker prerequisites, and expected behavior differences - keep this concise.

**Checkpoint**: M-Unit functional tests pass with all three backends (inmemory, YottaDB, IRIS). m2py test suite has zero unexpected regressions with YDB and IRIS. Backend-specific limitations are documented and xfailed with clear reasons. ZWR bootstrap completes in <60s on YDB.

---

## Phase 9: User Story 6 — Tier 3: VA FileMan (5 routines, ~174 assertions) [Stretch]

**Goal**: Validate date/time, dictionary lookup, computed field operations. First package requiring global bootstrap.

**Independent Test**: `uv run pytest tests/functional/munit/ -v -k "va_fileman"` — 5 routines pass/xfail.

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

## Phase 10: User Story 6 continued — Tier 4a: Problem List (8 routines, ~349 assertions) [Stretch]

**Goal**: Validate Problem List API: create, modify, delete, query problems.

**Independent Test**: `uv run pytest tests/functional/munit/ -v -k "problem_list"` — 8 routines pass/xfail.

### Problem List Dependencies (US5 + US6)

- [ ] T074 [US5] Verify/fix `XLFDT` (date/time formatting library, shared by all Tier 4) transpilation; add minimal tests in `tests/test_kernel_xlfdt.py` (m2py root)
- [ ] T075 [P] [US6] Transpile GMPL* API routines: GMPLAPI1–7, GMPLMGR, GMPLDAL, GMPLSAVE, GMPLSITE, GMPLHIST, GMPLUTL, GMPLX; verify they load
- [ ] T076 [P] [US6] Transpile test utility ZZRGUTCM; verify it loads

### Problem List Global Bootstrap (US4 + US6)

- [ ] T077 [US4] Capture Problem List globals from osehravista: `^AUPNPROB`, `^GMPL*`, `^SC`, `^VA`; save ZWR to `tests/functional/munit/baselines/globals/`
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

## Phase 11: User Story 6 continued — Tier 4b: Scheduling (12 routines, ~547 assertions) [Stretch]

**Goal**: Validate Scheduling APIs: appointments, patient lists, scheduling actions. Largest package by assertion count.

**Independent Test**: `uv run pytest tests/functional/munit/ -v -k "scheduling"` — 6 routines pass (Group B excluded: fail in baseline).

### Scheduling Dependencies (US5 + US6)

- [X] T088 [P] [US6] Transpile Scheduling SDK APIs: SDAMA201, SDAMA202, SDAMA203, SDAMA204, SDAMA301; verify they load
- [X] T089 [P] [US6] Transpile Scheduling Management APIs: SDMAPI1, SDMAPI2, SDMAPI3, SDMAPI4, SDMAPI5, SDCAPI1; verify they load
- [X] T090 [P] [US6] Transpile test commons: ZZUTSDCOM, ZZRGUSDC, shared utility routines; verify they load

### Scheduling Global Bootstrap (US4 + US6)

- [X] T091 [US4] Scheduling globals not needed — Group A SDK tests pass without clinical globals
- [X] T092 [US6] Scheduling library fixture created with auto-importer add_dirs() for VistA-M + VistA-VEHU-M

### Group A — SDK Tests (6 routines, ~84 assertions, simpler) (US6)

- [X] T093 [US6] ZZUTSDIMO: 4 tests, 0 failures, 0 errors — PASS
- [X] T094 [US6] ZZUTPATAPPT: 6 tests, 0 failures, 0 errors — PASS
- [X] T095 [US6] ZZUTNEXTAPPT: 32 tests, 0 failures, 0 errors — PASS
- [X] T096 [US6] ZZUTGETAPPT: 37 tests, 0 failures, 0 errors — PASS
- [X] T097 [US6] ZZUTGETPLIST: 37 tests, 0 failures, 0 errors — PASS
- [X] T098 [US6] ZZUTSDAPI: 6 tests, 0 failures, 0 errors — PASS

### Group B — Regression Tests (6 routines, ~463 assertions, complex) (US6)

- [X] T099–T104: ZZRGUSD1–6 excluded — all ERROR on osehravista baseline (require fakedoc1 test user)
- [X] T105 [US5] No m2py issues discovered during Tier 4b

**Checkpoint**: 31 / 32 routines passing (Group A only). ~122 Scheduling assertions validated. Group B excluded (baseline failures).

---

## Phase 12: User Story 6 continued — Tier 4c: Registration (1 routine, ~10 assertions) [Stretch]

**Goal**: Validate patient combine/registration operations. Smallest stretch package.

**Independent Test**: `uv run pytest tests/functional/munit/ -v -k "registration"` — 1 routine passes/xfails.

### Registration Dependencies (US5 + US6)

- [ ] T106 [US6] Transpile `DGPTCO1` (patient combine API); verify it loads

### Registration Global Bootstrap (US4 + US6)

- [ ] T107 [US4] Capture Registration globals from osehravista: `^DG*`; save ZWR to `tests/functional/munit/baselines/globals/` (may share `^DPT` from Tier 4b)

### Registration Test Routine (US6)

- [ ] T108 [US6] Transpile and run ZZDGPTCO1 (10 assertions, DGPTCO1, DICRW); compare to baseline
- [ ] T109 [US5] Fix m2py issues discovered during Tier 4c; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: **38 / 38 routines (100%)**. All M-Unit tests passing. ~1,204 cumulative assertions.

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, CI readiness.

- [ ] T110 [P] Update `README.md` with M-Unit test instructions (baseline capture, running transpiled tests, per-tier commands)
- [ ] T111 [P] Update `specs/026-vista-munit-tests/quickstart.md` with any corrections discovered during implementation
- [ ] T112 Run full `uv run pytest tests/functional/munit/ -v` to validate all tiers end-to-end
- [ ] T113 Run full `uv run pytest` from m2py root to verify no regressions from transpiler/runtime fixes
- [ ] T114 [P] Document known xfail routines and their root causes in `tests/functional/munit/baselines/XFAIL.md`
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
    └── Phase 7 (US4: ZWR Import/Export in m2py + munit fixtures) ────────┤
            │                                                                     │
            ├── Phase 8 (Backend: YottaDB/IRIS infra + regression fixes) ─────┤
            │                                                                     │
            ├── Phase 9 (US6: Tier 3 VA FileMan — 5 routines, ~174 asserts)      │
            │       │                                                             │
            │       ├── Phase 10 (US6: Tier 4a Problem List — 8 routines, ~349)  │
            │       │                                                             │
            │       ├── Phase 11 (US6: Tier 4b Scheduling — 12 routines, ~547)  │
            │       │                                                             │
            │       └── Phase 12 (US6: Tier 4c Registration — 1 routine, ~10)   │
            │                                                                     │
            └─────────────────────────────────────────────────────────────────────┘
                                                                                  │
Phase 13 (Polish) ────────────────────────────────────────────────────────────────┘
```

### User Story → Phase Mapping

| User Story | Description | Phases | Priority |
|------------|-------------|--------|----------|
| US1 | Capture osehravista Baseline | 3, 6 | P1 |
| US2 | M-Unit Output Parser + Models | 2 | P1 |
| US3 | Run Transpiled Tests via pytest | 4, 5, 8 | P2 |
| US4 | ZWR Import/Export + Global Bootstrap | 7, 8 | P3 (Stretch) |
| US5 | Fix m2py Issues | 4, 5, 8, 9, 10, 11, 12 (cross-cutting) | P2 |
| US6 | Incremental Package Expansion | 8, 9, 10, 11, 12 | P3 (Stretch) |

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

**Phase 8** (T124–T127 backend infrastructure): Dockerfile, ydb.sh, iris.sh, and dependency groups are independent. T132–T136 (YDB fixes) and T137–T138 (IRIS fixes) can run in parallel.

**Phase 9** (T061–T065 kernel utilities): `%DT`, `%DTC`, `%ZISH`, `%ZOSF`, `DICRW` verifications are independent.

**Phase 11** (T088–T090 scheduling APIs): SDK, Management, and test commons transpilation are independent.

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

### Stretch Goal: 100% M-Unit Tests (Phases 6–12)

7. **Phase 6**: Capture remaining baselines (T041–T044) — can overlap with MVP validation
8. **Phase 7**: ZWR import/export in m2py + munit fixtures (T045–T060)
9. **Phase 8**: Backend compatibility — YottaDB/IRIS infra + regression fixes (T122–T147)
10. **Phase 9**: Tier 3 VA FileMan (T061–T073) — first stretch milestone (45%)
11. **Phase 10**: Tier 4a Problem List (T074–T087) — second stretch milestone (66%)
12. **Phase 11**: Tier 4b Scheduling (T088–T105) — third stretch milestone (97%)
13. **Phase 12**: Tier 4c Registration (T106–T109) — **100% complete**
14. **Phase 13**: Polish (T110–T115)

### Milestone Summary

| Milestone | Tasks | Routines | Assertions | Cumulative |
|-----------|-------|----------|------------|------------|
| Phase 2 complete | T001–T016 | 0 | 0 | Infrastructure ready |
| Phase 3 complete | T017–T023 | 0 | 0 | Baseline captured (Tier 1+2) |
| Phase 4 complete | T024–T034 | 8 | ~28 | Tier 1 passing (21%) |
| Phase 5 complete | T035–T040 | 12 | ~124 | **MVP — Tier 1+2 (32%)** |
| Phase 7 complete | T045–T060 | 0 | 0 | ZWR import/export ready (m2py + munit fixtures) |
| Phase 8 complete | T122–T147 | 0 | 0 | All backends passing — YDB/IRIS infra + fixes |
| Phase 9 complete | T061–T073 | 17 | ~298 | Tier 3 passing (45%) |
| Phase 10 complete | T074–T087 | 25 | ~647 | Tier 4a passing (66%) |
| Phase 11 complete | T088–T105 | 37 | ~1,194 | Tier 4b passing (97%) |
| Phase 12 complete | T106–T109 | 38 | ~1,204 | **100% — All tiers** |

---

## Notes

- **[P]** tasks = different files, no dependencies on incomplete tasks
- **[US#]** labels map tasks to spec.md user stories for traceability
- _Originally, vista-test/ tasks lived in a separate repository; these have been consolidated into `tests/functional/munit/` and `tests/functional/munit/lib/` within m2py_
- m2py root tasks (tests/, src/m2py/) execute in the workspace root context
- ZWR import/export lives in m2py (`src/m2py/runtime/zwr.py`) as a general-purpose capability for any `GlobalStorageBackend`; munit fixtures call `import_zwr()` to load cached ZWR data
- Each m2py bug fix (US5) follows: discover → extract minimal MUMPS → fix → standalone test → verify M-Unit re-run
- osehravista Docker is only needed for baseline capture (Phases 3, 6) and global data capture (T059–T060, T077, T091, T107); transpiled tests run offline with cached ZWR files
- Stretch goal phases (7–12) can be attempted incrementally — each tier adds value independently
- Registration (Phase 12) has fewest tests and could be attempted anytime after Phase 9 (FileMan infrastructure)
