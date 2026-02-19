# Tasks: VistA M-Unit Test Suite via pytest (Phase 0)

**Input**: Design documents from `/specs/026-vista-munit-tests/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (models, parser, baseline-runner, pytest-adapter, global-bootstrap), quickstart.md

**Organization**: Tasks are organized by implementation phase (A–G from plan.md), which map to user stories from spec.md. Phases A–C deliver the MVP (Tier 1+2, 12 routines, ~124 assertions). Phases D–G deliver the stretch goal (Tier 3+4, 38 routines total, ~1,204 assertions).

**Cross-repo convention**: Tasks prefixed with `vista-test/` live in the vista-test repository. Tasks prefixed with `src/m2py/` or `tests/` (no `vista-test/`) live in the m2py root workspace. Each m2py fix gets a standalone unit test with no VistA dependency.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US6 from spec.md)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding — create package structure, add dependencies, wire up test directories.

- [ ] T001 [P] Create munit package directory with `__init__.py` at `vista-test/src/vista_test/munit/__init__.py`
- [ ] T002 [P] Create munit test directories: `vista-test/tests/vista/munit/` and `vista-test/tests/unit/` with `__init__.py` files
- [ ] T003 [P] Create baselines directory at `vista-test/baselines/` with `.gitkeep`
- [ ] T004 Add m2py as path dependency (`m2py = {path = ".."}`) in `vista-test/pyproject.toml`
- [ ] T005 Verify dependency resolution: run `cd vista-test && uv sync` and confirm `from m2py.codegen import generate_python` imports

**Checkpoint**: Package structure exists, m2py importable from vista-test.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and M-Unit output parser — required by ALL subsequent phases.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Data Models (US2 prerequisite)

- [ ] T006 [P] [US2] Implement `FailureDetail` dataclass per contracts/models.md in `vista-test/src/vista_test/munit/models.py`
- [ ] T007 [P] [US2] Implement `MUnitResult` dataclass with `to_dict()`/`from_dict()` in `vista-test/src/vista_test/munit/models.py`
- [ ] T008 [P] [US2] Implement `PackageBaseline` and `BaselineData` with `to_json()`/`from_json()` in `vista-test/src/vista_test/munit/models.py`
- [ ] T009 [P] [US2] Implement `TestRoutineConfig` dataclass in `vista-test/src/vista_test/munit/models.py`

### Model Tests

- [ ] T010 [P] [US2] Write model unit tests: `MUnitResult` round-trip (to_dict/from_dict), status derivation, validation in `vista-test/tests/unit/test_munit_models.py`
- [ ] T011 [P] [US2] Write model unit tests: `BaselineData` JSON serialization, `FailureDetail` CHKEQ vs CHKTF in `vista-test/tests/unit/test_munit_models.py`

### M-Unit Output Parser (US2)

- [ ] T012 [US2] Implement `parse_munit_output()` per contracts/munit-parser.md: summary regex, failure extraction, error extraction in `vista-test/src/vista_test/munit/parser.py`
- [ ] T013 [US2] Implement `parse_testlist()` per contracts/munit-parser.md: TestList file parsing, invocation pattern matching, tier assignment in `vista-test/src/vista_test/munit/parser.py`

### Parser Tests

- [ ] T014 [P] [US2] Write parser unit tests: all-pass output, CHKTF failure, CHKEQ failure with `<expected> vs <actual>`, error output in `vista-test/tests/unit/test_munit_parser.py`
- [ ] T015 [P] [US2] Write parser unit tests: empty output, partial output (no summary), self-referential %utt output, multi-line messages in `vista-test/tests/unit/test_munit_parser.py`
- [ ] T016 [US2] Write parser unit tests: `parse_testlist()` with MASH Utilities and M XML Parser TestList files from VistA submodule in `vista-test/tests/unit/test_munit_parser.py`

**Checkpoint**: `uv run pytest vista-test/tests/unit/test_munit_models.py vista-test/tests/unit/test_munit_parser.py` passes. Foundation ready.

---

## Phase 3: User Story 1 — Capture VEHU Baseline (Priority: P1)

**Goal**: Establish ground truth by running all M-Unit test routines against the VEHU Docker container via SSH and persisting structured JSON results.

**Independent Test**: Start VEHU Docker, run `uv run python -m vista_test.munit.baseline --output baselines/vehu-baseline.json`, verify JSON contains results for all discovered routines.

### Implementation

- [ ] T017 [US1] Implement `BaselineRunner.__init__()` and `_connect()` SSH setup (lazy connect via `VistATerminal`) in `vista-test/src/vista_test/munit/baseline.py`
- [ ] T018 [US1] Implement `BaselineRunner.import_routine()`: read `.m` source from VistA submodule, send to VEHU via programmer mode in `vista-test/src/vista_test/munit/baseline.py`
- [ ] T019 [US1] Implement `BaselineRunner.run_routine()`: send invocation command, capture output with timeout, parse via `parse_munit_output()` in `vista-test/src/vista_test/munit/baseline.py`
- [ ] T020 [US1] Implement `BaselineRunner.run_package()` and `BaselineRunner.run_all()`: group by package, aggregate results in `vista-test/src/vista_test/munit/baseline.py`
- [ ] T021 [US1] Implement CLI entry point `__main__.py` with `--output`, `--package`, `--routine`, `--tier` options in `vista-test/src/vista_test/munit/__main__.py`
- [ ] T022 [US1] Capture Tier 1 baseline: run `%utt1`–`%utt7`, `%uttcovr` against VEHU; commit JSON to `vista-test/baselines/vehu-baseline.json`
- [ ] T023 [US1] Capture Tier 2 baseline: run MXMLBLD, MXMLDOMT, MXMLPATT, MXMLTMPT against VEHU; update `vista-test/baselines/vehu-baseline.json`

**Checkpoint**: `baselines/vehu-baseline.json` contains results for all Tier 1+2 routines (12 routines). Can inspect pass/fail counts per routine.

---

## Phase 4: User Story 3 — pytest M-Unit Adapter: Tier 1 Self-Tests (Priority: P2) 🎯 MVP Part 1

**Goal**: Transpile and run M-Unit self-tests (%utt1–%utt7, %uttcovr) in Python via pytest, comparing to VEHU baseline. This validates the M-Unit framework itself works in transpiled form.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "mash_utilities"` — all 8 routines pass or xfail.

### Adapter Infrastructure (US3)

- [ ] T024 [US3] Implement `transpile_and_execute()` per contracts/pytest-adapter.md: read MUMPS source, call `generate_python()`, exec into module, call entry point, capture output in `vista-test/src/vista_test/munit/adapter.py`
- [ ] T025 [US3] Implement `MUnitTestItem` (custom pytest.Item): `runtest()` calls `transpile_and_execute()`, parses output, compares to baseline in `vista-test/src/vista_test/munit/adapter.py`
- [ ] T026 [US3] Implement `MUnitCollector` (custom pytest.Collector): discovers routines from TestList files via `parse_testlist()` in `vista-test/src/vista_test/munit/adapter.py`
- [ ] T027 [US3] Implement conftest.py plugin: `pytest_collect_file` hook, `munit_baseline` fixture, `munit_runtime` fixture, `munit_framework` fixture, xfail logic in `vista-test/tests/vista/munit/conftest.py`

### Tier 1: Transpile M-Unit Framework + Self-Tests (US3 + US5)

- [ ] T028 [US3] Transpile `%ut` and `%ut1` (M-Unit framework) via `generate_python()`; verify they load without import errors
- [ ] T029 [US5] Verify `$ETRAP` error trapping works in transpiled `%ut` — create minimal MUMPS test for `$ETRAP` behavior in `tests/test_munit_etrap.py` (m2py root)
- [ ] T030 [US5] Verify `DO @var` (indirection) works for dynamic dispatch in `%ut` — create minimal MUMPS test in `tests/test_munit_indirection.py` (m2py root)
- [ ] T031 [US5] Verify `$TEXT` intrinsic works for `@TEST` discovery and `$T(+1^routine)` guard — create minimal MUMPS test in `tests/test_munit_text.py` (m2py root)
- [ ] T032 [US3] Transpile `%utt1`–`%utt7` and `%uttcovr` self-test routines; verify they load without import errors
- [ ] T033 [US3] Run transpiled self-tests via adapter: execute `%utt1`–`%utt7`, `%uttcovr`; compare output to Tier 1 baseline
- [ ] T034 [US5] Fix m2py transpilation/runtime issues discovered during Tier 1 execution; add standalone unit tests per fix in `tests/` (m2py root, no VistA deps)

**Checkpoint**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "mash_utilities"` — 8 routines pass/xfail. M-Unit framework validated in Python.

---

## Phase 5: User Story 3 continued — Tier 2: M XML Parser (Priority: P2) 🎯 MVP Part 2

**Goal**: Transpile and run M XML Parser tests (4 routines, ~96 assertions) in Python. Completes the MVP.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "m_xml_parser"` — all 4 routines pass or xfail.

### Tier 2: XML Parser Transpilation (US3 + US5)

- [ ] T035 [P] [US3] Transpile XML parser dependency routines: MXMLDOM, MXMLPRSE, MXMLUTL, MXMLPATH, MXMLTMP1, MXMLTMPL; verify they load
- [ ] T036 [US3] Run MXMLBLD test (13 assertions, lowest risk: deps = MXMLUTL + MXMLTMP1); compare output to baseline
- [ ] T037 [US3] Run MXMLTMPT test (49 assertions, template engine; may need `DT^DICRW` stub); compare output to baseline
- [ ] T038 [US3] Run MXMLPATT test (25 assertions, XPath; needs MXMLDOM + MXMLPATH); compare output to baseline
- [ ] T039 [US3] Run MXMLDOMT test (9 assertions, **highest risk**: needs `%ZISH` file I/O); compare output to baseline — xfail if `%ZISH` not ready
- [ ] T040 [US5] Fix m2py issues discovered during Tier 2 (e.g., `$NAME`, `$PIECE` on long strings, `$ORDER` on `^TMP` trees); add standalone tests in `tests/` (m2py root)

**Checkpoint**: `cd vista-test && uv run pytest tests/vista/munit/ -v` — **MVP complete**: 12 routines (Tier 1+2) pass/xfail. ~124 assertions validated.

---

## Phase 6: User Story 1 continued — Capture Stretch Goal Baselines (Priority: P1)

**Goal**: Capture VEHU baselines for ALL remaining packages (Tiers 3–4) so stretch goal work can proceed.

**Independent Test**: `baselines/vehu-baseline.json` contains results for all 38 routines across all 5 packages.

- [ ] T041 [P] [US1] Capture Tier 3 baseline: run ZZUTDIDT, DMUDIC00, DMUDT000, DMUDTC00, DMUDIQ00 against VEHU; update `vista-test/baselines/vehu-baseline.json`
- [ ] T042 [P] [US1] Capture Tier 4a baseline: run ZZRGUT–ZZRGUT5, ZZRGUTRB, ZZRGUTEX against VEHU; update `vista-test/baselines/vehu-baseline.json`
- [ ] T043 [P] [US1] Capture Tier 4b baseline: run all 12 Scheduling routines against VEHU; update `vista-test/baselines/vehu-baseline.json`
- [ ] T044 [P] [US1] Capture Tier 4c baseline: run ZZDGPTCO1 against VEHU; update `vista-test/baselines/vehu-baseline.json`

**Checkpoint**: `baselines/vehu-baseline.json` has all 38 routines. Full ground truth for 100% comparison.

---

## Phase 7: User Story 4 — Global Bootstrap Infrastructure (Priority: P3) [Stretch]

**Goal**: Build the global export/import tool so Tier 3+ tests have the data they need. This is the critical enabler for all stretch goals.

**Independent Test**: Export `^DD(2,0)` from VEHU, import into m2py `MDict`, query it back — values match.

### Global Bootstrap Tool (US4)

- [ ] T045 [US4] Implement `GlobalBootstrap.__init__()` and `export_globals()`: SSH to VEHU, traverse globals via `$ORDER`, write ZWR format in `vista-test/src/vista_test/munit/bootstrap.py`
- [ ] T046 [US4] Implement `GlobalBootstrap.import_globals()`: parse ZWR format, load entries into m2py `MDict` global store in `vista-test/src/vista_test/munit/bootstrap.py`
- [ ] T047 [US4] Implement `GlobalBootstrap.bootstrap_tier()`: Tier 3 exports `^DD`, `^DIC`, `^%ZOSF`; Tier 4 adds `^DPT`, `^SC`, `^AUPNPROB`, `^GMPL*`, `^SD*`, `^DG*` in `vista-test/src/vista_test/munit/bootstrap.py`
- [ ] T048 [US4] Implement caching: skip re-export if ZWR files already exist on disk in `vista-test/src/vista_test/munit/bootstrap.py`
- [ ] T049 [US4] Add pytest fixtures: `fileman_bootstrap` (session-scoped, Tier 3) and `clinical_bootstrap` (session-scoped, Tier 4) in `vista-test/tests/vista/munit/conftest.py`

### Global Bootstrap Tests

- [ ] T050 [P] [US4] Write unit test: ZWR parsing round-trip (export → import → query) for simple globals in `vista-test/tests/unit/test_munit_bootstrap.py`
- [ ] T051 [US4] Integration test: export `^DD(2,0)` from VEHU, import into `MDict`, verify value matches VEHU in `vista-test/tests/unit/test_munit_bootstrap.py`

**Checkpoint**: Global bootstrap works for FileMan globals. Path to Tier 3 is unblocked.

---

## Phase 8: User Story 6 — Tier 3: VA FileMan (5 routines, ~174 assertions) [Stretch]

**Goal**: Validate date/time, dictionary lookup, computed field operations. First package requiring global bootstrap.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "va_fileman"` — 5 routines pass/xfail.

### Kernel Utility Transpilation (US5 + US6)

- [ ] T052 [US5] Verify/fix `%DT` (date/time validation) transpilation; add minimal MUMPS tests for date parsing in `tests/test_kernel_dt.py` (m2py root)
- [ ] T053 [US5] Verify/fix `%DTC` (date/time calculations) transpilation; add minimal MUMPS tests in `tests/test_kernel_dtc.py` (m2py root)
- [ ] T054 [US5] Verify/fix `%ZISH` (file I/O: `$$GTF`, `$$DEL`, `$$DEFDIR`) transpilation; add minimal MUMPS tests in `tests/test_kernel_zish.py` (m2py root)
- [ ] T055 [US5] Verify/fix `%ZOSF` (entry point loader) transpilation; add minimal MUMPS tests in `tests/test_kernel_zosf.py` (m2py root)
- [ ] T056 [P] [US5] Verify/fix `DICRW` (FileMan data entry) transpilation; add minimal MUMPS test in `tests/test_kernel_dicrw.py` (m2py root)

### FileMan Global Bootstrap (US4 + US6)

- [ ] T057 [US4] Export FileMan globals from VEHU: `^DD`, `^DIC`, `^%ZOSF`; cache ZWR files in `vista-test/baselines/globals/`
- [ ] T058 [US6] Import FileMan globals into m2py `MDict` via `fileman_bootstrap` fixture; verify `^DD(2,0)` accessible

### FileMan Test Routines (US6) — ordered by complexity

- [ ] T059 [US6] Transpile and run ZZUTDIDT (3 assertions, simplest: only `%DT`); compare to baseline
- [ ] T060 [US6] Transpile and run `DMUFINIT` fixture routine (creates test files 1009.801, 1009.802 in `^DD`)
- [ ] T061 [US6] Transpile and run DMUDIC00 (14 assertions, needs `DMUFINIT`, `^DIC`, `XPDUTL`); compare to baseline
- [ ] T062 [US6] Transpile and run DMUDT000 (58 assertions, needs `%DT`, `%ZISH`, `%ZOSF`); compare to baseline
- [ ] T063 [US6] Transpile and run DMUDTC00 (92 assertions, date/time calculations, `%ZISH`); compare to baseline
- [ ] T064 [US6] Transpile and run DMUDIQ00 (7 assertions, `DIQ`, `^DD`, `^DIC`); compare to baseline
- [ ] T065 [US5] Fix m2py issues discovered during Tier 3; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: 17 / 38 routines (45%). FileMan validated, global bootstrap proven. ~298 cumulative assertions.

---

## Phase 9: User Story 6 continued — Tier 4a: Problem List (8 routines, ~349 assertions) [Stretch]

**Goal**: Validate Problem List API: create, modify, delete, query problems.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "problem_list"` — 8 routines pass/xfail.

### Problem List Dependencies (US5 + US6)

- [ ] T066 [US5] Verify/fix `XLFDT` (date/time formatting library, shared by all Tier 4) transpilation; add minimal tests in `tests/test_kernel_xlfdt.py` (m2py root)
- [ ] T067 [P] [US6] Transpile GMPL* API routines: GMPLAPI1–7, GMPLMGR, GMPLDAL, GMPLSAVE, GMPLSITE, GMPLHIST, GMPLUTL, GMPLX; verify they load
- [ ] T068 [P] [US6] Transpile test utility ZZRGUTCM; verify it loads

### Problem List Global Bootstrap (US4 + US6)

- [ ] T069 [US4] Export Problem List globals from VEHU: `^AUPNPROB`, `^GMPL*`, `^SC`, `^VA`; cache ZWR files in `vista-test/baselines/globals/`
- [ ] T070 [US6] Import Problem List globals via `clinical_bootstrap` fixture; verify `^AUPNPROB` accessible

### Problem List Test Routines (US6) — ordered by fewest dependencies

- [ ] T071 [US6] Transpile and run ZZRGUT2 (6 assertions, simplest: only GMPLSITE); compare to baseline
- [ ] T072 [US6] Transpile and run ZZRGUT5 (8 assertions, GMPLAPI2+7, GMPLHIST); compare to baseline
- [ ] T073 [US6] Transpile and run ZZRGUT4 (38 assertions, GMPLAPI1–2+6); compare to baseline
- [ ] T074 [US6] Transpile and run ZZRGUTRB (38 assertions, GMPLMGR, GMPLSAVE, ORQQPL1–3); compare to baseline
- [ ] T075 [US6] Transpile and run ZZRGUT (83 assertions, GMPLAPI2–4, biggest routine); compare to baseline
- [ ] T076 [US6] Transpile and run ZZRGUT1 (87 assertions, GMPLAPI1+6); compare to baseline
- [ ] T077 [US6] Transpile and run ZZRGUT3 (60 assertions, GMPLAPI1+5+6); compare to baseline
- [ ] T078 [US6] Transpile and run ZZRGUTEX (29 assertions, **widest deps** — 6+ cross-package: ACKQUTL6, IBDFBK3, PXRMPROB, XUS1A); compare to baseline
- [ ] T079 [US5] Fix m2py issues discovered during Tier 4a; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: 25 / 38 routines (66%). Problem List API validated. ~647 cumulative assertions.

---

## Phase 10: User Story 6 continued — Tier 4b: Scheduling (12 routines, ~547 assertions) [Stretch]

**Goal**: Validate Scheduling APIs: appointments, patient lists, scheduling actions. Largest package by assertion count.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "scheduling"` — 12 routines pass/xfail.

### Scheduling Dependencies (US5 + US6)

- [ ] T080 [P] [US6] Transpile Scheduling SDK APIs: SDAMA201, SDAMA202, SDAMA203, SDAMA204, SDAMA301; verify they load
- [ ] T081 [P] [US6] Transpile Scheduling Management APIs: SDMAPI1, SDMAPI2, SDMAPI3, SDMAPI4, SDMAPI5, SDCAPI1; verify they load
- [ ] T082 [P] [US6] Transpile test commons: ZZUTSDCOM, ZZRGUSDC, shared utility routines; verify they load

### Scheduling Global Bootstrap (US4 + US6)

- [ ] T083 [US4] Export Scheduling globals from VEHU: `^DPT`, `^SC`, `^SD*`; cache ZWR files in `vista-test/baselines/globals/`
- [ ] T084 [US6] Import Scheduling globals via `clinical_bootstrap` fixture; verify `^DPT` and `^SC` accessible

### Group A — SDK Tests (6 routines, ~84 assertions, simpler) (US6)

- [ ] T085 [US6] Transpile and run ZZUTSDIMO (4 assertions, SDAMA203); compare to baseline
- [ ] T086 [US6] Transpile and run ZZUTPATAPPT (5 assertions, SDAMA204, `^DPT`); compare to baseline
- [ ] T087 [US6] Transpile and run ZZUTNEXTAPPT (11 assertions, SDAMA201); compare to baseline
- [ ] T088 [US6] Transpile and run ZZUTGETAPPT (14 assertions, SDAMA201); compare to baseline
- [ ] T089 [US6] Transpile and run ZZUTGETPLIST (15 assertions, SDAMA202); compare to baseline
- [ ] T090 [US6] Transpile and run ZZUTSDAPI (35 assertions, SDAMA301); compare to baseline

### Group B — Regression Tests (6 routines, ~463 assertions, complex) (US6)

- [ ] T091 [US6] Transpile and run ZZRGUSD4 (60 assertions, SDMAPI1–2+5); compare to baseline
- [ ] T092 [US6] Transpile and run ZZRGUSD2 (68 assertions, SDCAPI1, SDMAPI1–2); compare to baseline
- [ ] T093 [US6] Transpile and run ZZRGUSD6 (69 assertions, SCAPMC21, SCTMAPI1); compare to baseline
- [ ] T094 [US6] Transpile and run ZZRGUSD3 (81 assertions, SDCAPI1, SDMAPI1–4); compare to baseline
- [ ] T095 [US6] Transpile and run ZZRGUSD5 (82 assertions, DGSAAPI, SDMAPI1–4, many globals); compare to baseline
- [ ] T096 [US6] Transpile and run ZZRGUSD1 (103 assertions, largest scheduling test); compare to baseline
- [ ] T097 [US5] Fix m2py issues discovered during Tier 4b; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: 37 / 38 routines (97%). Scheduling validated. ~1,194 cumulative assertions.

---

## Phase 11: User Story 6 continued — Tier 4c: Registration (1 routine, ~10 assertions) [Stretch]

**Goal**: Validate patient combine/registration operations. Smallest stretch package.

**Independent Test**: `cd vista-test && uv run pytest tests/vista/munit/ -v -k "registration"` — 1 routine passes/xfails.

### Registration Dependencies (US5 + US6)

- [ ] T098 [US6] Transpile `DGPTCO1` (patient combine API); verify it loads

### Registration Global Bootstrap (US4 + US6)

- [ ] T099 [US4] Export Registration globals from VEHU: `^DG*`; cache ZWR files in `vista-test/baselines/globals/` (may share `^DPT` from Tier 4b)

### Registration Test Routine (US6)

- [ ] T100 [US6] Transpile and run ZZDGPTCO1 (10 assertions, DGPTCO1, DICRW); compare to baseline
- [ ] T101 [US5] Fix m2py issues discovered during Tier 4c; add standalone unit tests per fix in `tests/` (m2py root)

**Checkpoint**: **38 / 38 routines (100%)**. All M-Unit tests passing. ~1,204 cumulative assertions.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, CI readiness.

- [ ] T102 [P] Update `vista-test/README.md` with M-Unit test instructions (baseline capture, running transpiled tests, per-tier commands)
- [ ] T103 [P] Update `specs/026-vista-munit-tests/quickstart.md` with any corrections discovered during implementation
- [ ] T104 Run full `uv run pytest tests/vista/munit/ -v` from vista-test to validate all tiers end-to-end
- [ ] T105 Run full `uv run pytest` from m2py root to verify no regressions from transpiler/runtime fixes
- [ ] T106 [P] Document known xfail routines and their root causes in `vista-test/baselines/XFAIL.md`
- [ ] T107 Validate quickstart.md: follow setup and run instructions from scratch in a clean environment

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ─────────────────────────────────────────────────────────────────┐
    │                                                                             │
Phase 2 (Foundational: models + parser) ──────────────────────────────────────────┤
    │                                                                             │
    ├── Phase 3 (US1: Capture VEHU Baseline — Tiers 1+2)                         │
    │       │                                                                     │
    │       ├── Phase 4 (US3: Tier 1 M-Unit self-tests)                          │
    │       │       │                                                             │
    │       │       └── Phase 5 (US3: Tier 2 M XML Parser)                       │
    │       │               └── ✅ MVP COMPLETE (12 / 38 routines, ~124 asserts)  │
    │       │                                                                     │
    │       └── Phase 6 (US1: Capture Stretch Baselines — Tiers 3+4) ────────────┤
    │                                                                             │
    └── Phase 7 (US4: Global Bootstrap Infrastructure) ──────────────────────────┤
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
| US1 | Capture VEHU Baseline | 3, 6 | P1 |
| US2 | M-Unit Output Parser + Models | 2 | P1 |
| US3 | Run Transpiled Tests via pytest | 4, 5 | P2 |
| US4 | Global Bootstrap | 7 | P3 (Stretch) |
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

**Phase 8** (T052–T056 kernel utilities): `%DT`, `%DTC`, `%ZISH`, `%ZOSF`, `DICRW` verifications are independent.

**Phase 10** (T080–T082 scheduling APIs): SDK, Management, and test commons transpilation are independent.

**Cross-phase**: Phase 6 (stretch baselines) can run in parallel with Phases 4–5 (MVP transpilation) since they only need VEHU Docker.

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
8. **Phase 7**: Build global bootstrap tool (T045–T051)
9. **Phase 8**: Tier 3 VA FileMan (T052–T065) — first stretch milestone (45%)
10. **Phase 9**: Tier 4a Problem List (T066–T079) — second stretch milestone (66%)
11. **Phase 10**: Tier 4b Scheduling (T080–T097) — third stretch milestone (97%)
12. **Phase 11**: Tier 4c Registration (T098–T101) — **100% complete**
13. **Phase 12**: Polish (T102–T107)

### Milestone Summary

| Milestone | Tasks | Routines | Assertions | Cumulative |
|-----------|-------|----------|------------|------------|
| Phase 2 complete | T001–T016 | 0 | 0 | Infrastructure ready |
| Phase 3 complete | T017–T023 | 0 | 0 | Baseline captured (Tier 1+2) |
| Phase 4 complete | T024–T034 | 8 | ~28 | Tier 1 passing (21%) |
| Phase 5 complete | T035–T040 | 12 | ~124 | **MVP — Tier 1+2 (32%)** |
| Phase 8 complete | T052–T065 | 17 | ~298 | Tier 3 passing (45%) |
| Phase 9 complete | T066–T079 | 25 | ~647 | Tier 4a passing (66%) |
| Phase 10 complete | T080–T097 | 37 | ~1,194 | Tier 4b passing (97%) |
| Phase 11 complete | T098–T101 | 38 | ~1,204 | **100% — All tiers** |

---

## Notes

- **[P]** tasks = different files, no dependencies on incomplete tasks
- **[US#]** labels map tasks to spec.md user stories for traceability
- vista-test/ tasks execute in the vista-test repository context
- m2py root tasks (tests/, src/m2py/) execute in the workspace root context
- Each m2py bug fix (US5) follows: discover → extract minimal MUMPS → fix → standalone test → verify M-Unit re-run
- VEHU Docker is only needed for baseline capture (Phases 3, 6) and global export (Phases 7, 8, 9, 10, 11); transpiled tests run offline
- Stretch goal phases (7–11) can be attempted incrementally — each tier adds value independently
- Registration (Phase 11) has fewest tests and could be attempted anytime after Phase 8 (FileMan infrastructure)
