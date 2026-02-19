# Implementation Plan: VistA M-Unit Test Suite via pytest (Phase 0)

**Branch**: `026-vista-munit-tests` | **Date**: 2025-07-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/026-vista-munit-tests/spec.md`

## Summary

Build a pytest-integrated M-Unit test pipeline that: (1) captures VEHU Docker baseline results for 38 M-Unit test routines (~1,204 assertions) across 5 VistA packages via SSH, (2) parses M-Unit framework output into structured data, and (3) transpiles+executes the same tests in Python via m2py, comparing results to baseline. Minimum viable scope: Tier 1 (M-Unit self-tests, 8 routines) and Tier 2 (M XML Parser, 4 routines). Stretch goal: 100% of M-Unit tests passing across all 5 packages — VA FileMan (Tier 3), Problem List, Scheduling, and Registration (Tier 4). Tests that fail on VEHU are `xfail` in pytest. m2py transpilation/runtime bugs discovered during this work are fixed in the m2py root with standalone unit tests.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: m2py (transpiler/runtime), paramiko (SSH), pytest, textX  
**Storage**: JSON files (baseline data), m2py global store (MDict) for transpiled globals  
**Testing**: pytest with M-Unit output parsing; m2py standalone unit tests for transpiler fixes  
**Target Platform**: Linux (dev container)  
**Project Type**: Dual-repo (m2py root + vista-test subdirectory)  
**Performance Goals**: Each routine transpile+execute < 30s; full suite < 15 minutes  
**Constraints**: VEHU Docker must be running for baseline capture only; transpiled tests run offline  
**Scale/Scope**: 12 routines (MVP), 38 routines (full), ~1,204 assertions across 5 VistA packages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ PASS | Core goal: transpiled tests must match VEHU behavior exactly |
| II. YDB as Reference | ✅ PASS | VEHU (which runs on Cache) is baseline; m2py returns 47 for GETSYS so GT.M paths taken — acceptable since we compare output not implementation |
| III. Strict Layer Separation | ✅ PASS | No codegen changes — only runtime fixes and test infrastructure |
| IV. Explicit Over Implicit | ✅ PASS | All M-Unit behavior made explicit through structured parser |
| V. Foundational Correctness | ✅ PASS | Tests validate existing foundational infrastructure |
| VI. Cross-Cutting Semantics | ✅ PASS | M-Unit exercises $ETRAP, indirection, $TEXT — validates cross-cutting features |
| VII. Minimize Runtime Surface | ✅ PASS | No new runtime abstractions; uses existing MUMPSRuntime |
| VIII. Research Before Implementation | ✅ PASS | Research phase completed — see research.md |

No constitution violations. All work is test infrastructure + bug fixes in existing layers.

## Project Structure

### Documentation (this feature)

```text
specs/026-vista-munit-tests/
├── plan.md              # This file
├── research.md          # Phase 0 output — M-Unit internals, dependencies, API patterns
├── data-model.md        # Phase 1 output — MUnitResult, BaselineData, etc.
├── quickstart.md        # Phase 1 output — setup and run instructions
├── contracts/           # Phase 1 output — module interface specifications
│   ├── models.md        # Data classes contract
│   ├── munit-parser.md  # Parser contract
│   ├── baseline-runner.md  # VEHU baseline runner contract
│   └── pytest-adapter.md   # pytest M-Unit adapter contract
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (cross-repository)

```text
# vista-test/ (separate repository, VistA functional tests)
vista-test/
├── src/vista_test/
│   └── munit/                  # NEW: M-Unit support package
│       ├── __init__.py
│       ├── models.py           # Data classes (MUnitResult, BaselineData, etc.)
│       ├── parser.py           # M-Unit output parser
│       ├── baseline.py         # VEHU baseline runner (SSH + M-Unit execution)
│       └── adapter.py          # Transpile + execute + compare logic
├── tests/
│   ├── unit/
│   │   ├── test_munit_parser.py    # NEW: Parser unit tests
│   │   └── test_munit_models.py    # NEW: Model serialization tests
│   └── vista/
│       └── munit/                  # NEW: M-Unit pytest plugin + tests
│           └── conftest.py         # pytest discovery, fixtures, xfail logic
├── baselines/                      # NEW: Committed VEHU baseline JSON
│   └── vehu-baseline.json
├── VistA/                          # Submodule (read-only)
│   └── Packages/*/Testing/MUnit/   # TestList files + .m test sources
└── pyproject.toml                  # Add m2py path dependency

# m2py root (transpiler + runtime — fixes only)
src/m2py/
├── codegen/                        # Transpilation fixes (if needed)
└── runtime/                        # Runtime fixes (if needed)
tests/
├── functional/                     # Existing functional tests
└── <new-test-files>.py             # NEW: Standalone unit tests for each m2py fix
```

**Structure Decision**: Dual-repo layout. vista-test owns all VistA test infrastructure (parser, baseline, adapter, baselines). m2py root owns transpiler/runtime code. Each m2py bug fix gets a standalone test in `tests/` with no VistA dependency. vista-test imports m2py as a path-based dev dependency (`m2py = {path = ".."}`).

## Complexity Tracking

No constitution violations — this section is not applicable.

## Implementation Phases

### Phase A — Foundation (MVP Infrastructure)

Build the core infrastructure shared by all tiers: data models, parser, baseline runner, pytest adapter.

| Step | File(s) | Description | Depends On |
|------|---------|-------------|------------|
| A1 | `vista-test/src/vista_test/munit/models.py` | Data classes: `MUnitResult`, `FailureDetail`, `BaselineData`, `PackageBaseline`, `TestRoutineConfig` | — |
| A2 | `vista-test/src/vista_test/munit/parser.py` | M-Unit output parser: summary, failure, error extraction | A1 |
| A3 | `vista-test/tests/unit/test_munit_parser.py` | Parser unit tests: pass, fail (CHKTF+CHKEQ), error, empty, partial | A2 |
| A4 | `vista-test/tests/unit/test_munit_models.py` | Model serialization round-trip tests (to_dict/from_dict/JSON) | A1 |
| A5 | `vista-test/src/vista_test/munit/baseline.py` | Baseline runner: SSH to VEHU, import routines, execute, parse, serialize | A1, A2 |
| A6 | `vista-test/pyproject.toml` | Add m2py path dependency (`m2py = {path = ".."}`) | — |
| A7 | `vista-test/src/vista_test/munit/adapter.py` | Transpile+execute engine: `transpile_and_execute()`, `MUnitTestItem`, `MUnitCollector` | A1, A2, A6 |
| A8 | `vista-test/tests/vista/munit/conftest.py` | pytest plugin: TestList discovery, baseline loading, xfail logic, session fixtures | A5, A7 |

### Phase B — Tier 1: M-Unit Self-Tests (8 routines, ~28 assertions)

Validate the M-Unit framework itself transpiles and runs correctly.

| Step | Description | Depends On |
|------|-------------|------------|
| B1 | Capture VEHU baseline for `%utt1`–`%utt7`, `%uttcovr` | A5 |
| B2 | Transpile `%ut` + `%ut1` (M-Unit framework) — fix m2py issues as encountered | A6 |
| B3 | Transpile `%utt1`–`%utt7`, `%uttcovr` — fix m2py issues as encountered | B2 |
| B4 | Run transpiled self-tests, compare to baseline, iterate on m2py fixes | B1, B3 |
| B5 | Add standalone m2py unit tests for each transpilation/runtime fix (no VistA deps) | B4 |
| B6 | Commit baseline JSON to `vista-test/baselines/vehu-baseline.json` | B1 |

**Key risks**: `$ETRAP` (error trapping), `DO @var` (indirection), `$TEXT` (source introspection) must work. These are foundational M-Unit mechanisms.

### Phase C — Tier 2: M XML Parser (4 routines, ~96 assertions)

Validate XML parse/build/template/XPath functionality.

| Step | Description | Depends On |
|------|-------------|------------|
| C1 | Capture VEHU baseline for MXMLBLD, MXMLDOMT, MXMLPATT, MXMLTMPT | A5 |
| C2 | Transpile XML parser routines: MXMLDOM, MXMLPRSE, MXMLUTL, MXMLPATH, MXMLTMP1, MXMLTMPL, MXMLBLD | A6 |
| C3 | Start with MXMLBLD (lowest risk: 13 assertions, deps = MXMLUTL + MXMLTMP1) | C2 |
| C4 | MXMLTMPT (49 assertions, template engine; needs `DT^DICRW` — may need stub) | C2 |
| C5 | MXMLPATT (25 assertions, XPath; needs MXMLDOM + MXMLPATH) | C2 |
| C6 | MXMLDOMT (9 assertions, **highest risk**: needs `%ZISH` file I/O) | C2 |
| C7 | Fix m2py issues encountered; add standalone unit tests per fix | C3–C6 |
| C8 | Update baseline JSON with Tier 2 results | C1 |

**Key risks**: `%ZISH` (file I/O) for MXMLDOMT, `DT^DICRW` (FileMan date entry) for MXMLTMPT. May need runtime stubs or deferred xfail for these two routines initially.

### Phase D — Tier 3: VA FileMan (5 routines, ~174 assertions) [Stretch]

Validate date/time, dictionary lookup, computed field operations.

| Step | Description | Depends On |
|------|-------------|------------|
| D1 | Build global bootstrap tool: `GlobalBootstrap` class for VEHU export | A5 |
| D2 | Export FileMan globals from VEHU: `^DD`, `^DIC`, `^%ZOSF` | D1 |
| D3 | Import globals into m2py `MDict` store; pytest fixture for FileMan bootstrap | D2 |
| D4 | Transpile Kernel utilities: `%DT`, `%DTC`, `%ZISH`, `%ZOSF`, `DICRW` | A6 |
| D5 | Start with ZZUTDIDT (simplest: 3 assertions, only needs `%DT`) | D3, D4 |
| D6 | Transpile+run `DMUFINIT` fixture (creates test files 1009.801, 1009.802) | D3, D4 |
| D7 | DMUDIC00 (14 assertions, needs `DMUFINIT`, `^DIC`, `XPDUTL`) | D6 |
| D8 | DMUDT000 (58 assertions, needs `%DT`, `%ZISH`, `%ZOSF`) | D4 |
| D9 | DMUDTC00 (92 assertions, date/time calculations, `%ZISH`) | D4 |
| D10 | DMUDIQ00 (7 assertions, `DIQ`, `^DD`, `^DIC`) | D3, D4 |
| D11 | Capture VEHU baseline for all 5 FileMan routines; update baseline JSON | A5 |
| D12 | Fix m2py issues; add standalone unit tests per fix | D5–D10 |

**Prerequisites**: Global bootstrap infrastructure (~50-100 MB for `^DD`). `%ZISH` transpilation (file system operations). `%ZOSF` transpilation (MUMPS entry point loader).

**Suggested order**: ZZUTDIDT → DMUFINIT+DMUDIC00 → DMUDT000 → DMUDTC00 → DMUDIQ00 (increasing complexity).

### Phase E — Tier 4a: Problem List (8 routines, ~349 assertions) [Stretch]

Validate Problem List API: create, modify, delete, query problems.

| Step | Description | Depends On |
|------|-------------|------------|
| E1 | Export Problem List globals: `^AUPNPROB`, `^GMPL*`, `^SC`, `^VA` | D1 |
| E2 | Transpile GMPL* API routines (~10): GMPLAPI1–7, GMPLMGR, GMPLDAL, GMPLSAVE, GMPLSITE, GMPLHIST, GMPLUTL, GMPLX | A6 |
| E3 | Transpile test utility: ZZRGUTCM | A6 |
| E4 | Transpile XLFDT (date/time formatting library — shared by all Tier 4) | A6 |
| E5 | Start with ZZRGUT2 (simplest: 6 assertions, only GMPLSITE) | E1, E2 |
| E6 | ZZRGUT5 (8 assertions, GMPLAPI2+7, GMPLHIST) | E1, E2 |
| E7 | ZZRGUT4 (38 assertions, GMPLAPI1–2+6) | E1, E2 |
| E8 | ZZRGUTRB (38 assertions, GMPLMGR, GMPLSAVE, ORQQPL1–3) | E1, E2 |
| E9 | ZZRGUT (83 assertions, GMPLAPI2–4, biggest routine) | E1, E2 |
| E10 | ZZRGUT1 (87 assertions, GMPLAPI1+6) | E1, E2 |
| E11 | ZZRGUT3 (60 assertions, GMPLAPI1+5+6) | E1, E2 |
| E12 | ZZRGUTEX (29 assertions, **widest deps** — 6+ cross-package references) | E1, E2, D4 |
| E13 | Capture VEHU baseline for all 8 Problem List routines | A5 |
| E14 | Fix m2py issues; add standalone unit tests per fix | E5–E12 |

**Prerequisites**: All Tier 3 prerequisites plus Problem List API routines and clinical globals. `ZZRGUTEX` has the broadest dependency surface in the entire test suite.

**Suggested order**: ZZRGUT2 → ZZRGUT5 → ZZRGUT4 → ZZRGUTRB → ZZRGUT → ZZRGUT1 → ZZRGUT3 → ZZRGUTEX (fewest to most dependencies).

### Phase F — Tier 4b: Scheduling (12 routines, ~547 assertions) [Stretch]

Validate Scheduling APIs: appointments, patient lists, scheduling actions.

| Step | Description | Depends On |
|------|-------------|------------|
| F1 | Export Scheduling globals: `^DPT`, `^SC`, `^SD*` | D1 |
| F2 | Transpile Scheduling SDK APIs: SDAMA201–204, SDAMA301 | A6 |
| F3 | Transpile Scheduling Management APIs: SDMAPI1–5, SDCAPI1 | A6 |
| F4 | Transpile test commons: ZZUTSDCOM, ZZRGUSDC, ZZRGUSD5 (shared utility) | A6 |
| F5 | **Group A — SDK tests** (simpler, 6 routines, ~84 assertions): | |
| F5a | ZZUTSDIMO (4 assertions, SDAMA203) | F1, F2, F4 |
| F5b | ZZUTPATAPPT (5 assertions, SDAMA204, `^DPT`) | F1, F2, F4 |
| F5c | ZZUTNEXTAPPT (11 assertions, SDAMA201) | F1, F2, F4 |
| F5d | ZZUTGETAPPT (14 assertions, SDAMA201) | F1, F2, F4 |
| F5e | ZZUTGETPLIST (15 assertions, SDAMA202) | F1, F2, F4 |
| F5f | ZZUTSDAPI (35 assertions, SDAMA301) | F1, F2, F4 |
| F6 | **Group B — Regression tests** (complex, 6 routines, ~463 assertions): | |
| F6a | ZZRGUSD4 (60 assertions, SDMAPI1–2+5) | F1, F3, F4 |
| F6b | ZZRGUSD2 (68 assertions, SDCAPI1, SDMAPI1–2) | F1, F3, F4 |
| F6c | ZZRGUSD6 (69 assertions, SCAPMC21, SCTMAPI1) | F1, F3, F4 |
| F6d | ZZRGUSD3 (81 assertions, SDCAPI1, SDMAPI1–4) | F1, F3, F4 |
| F6e | ZZRGUSD5 (82 assertions, DGSAAPI, SDMAPI1–4, many globals) | F1, F3, F4 |
| F6f | ZZRGUSD1 (103 assertions, largest scheduling test) | F1, F3, F4 |
| F7 | Capture VEHU baseline for all 12 Scheduling routines | A5 |
| F8 | Fix m2py issues; add standalone unit tests per fix | F5–F6 |

**Prerequisites**: Patient and clinic data bootstrap. Scheduling API routines (~10). Test commons transpilation.

**Suggested order**: SDK tests first (fewer deps, validate API layer), then regression tests (ascending assertion count).

### Phase G — Tier 4c: Registration (1 routine, ~10 assertions) [Stretch]

Validate patient combine/registration operations.

| Step | Description | Depends On |
|------|-------------|------------|
| G1 | Export Registration globals: `^DG*` | D1 |
| G2 | Transpile `DGPTCO1` (patient combine API) | A6 |
| G3 | ZZDGPTCO1 (10 assertions, DGPTCO1, DICRW) | G1, G2, D4 |
| G4 | Capture VEHU baseline | A5 |
| G5 | Fix m2py issues; add standalone unit tests per fix | G3 |

**Prerequisites**: Patient data in `^DPT`, FileMan (`DICRW`), `^DG*` globals. Can share bootstrap with Tier 4b since both need `^DPT`.

**Note**: Registration has the fewest tests (1 routine, 10 assertions) and could be attempted anytime after FileMan infrastructure (Phase D) is working.

## Phase Dependencies (DAG)

```
Phase A (Foundation) ──────────────────────────────────────────────────┐
    │                                                                  │
    ├── Phase B (Tier 1: M-Unit self-tests)                           │
    │       └── Phase C (Tier 2: M XML Parser)                        │
    │               └── MVP COMPLETE                                   │
    │                                                                  │
    └── Phase D (Tier 3: VA FileMan) ── requires global bootstrap ────┤
            │                                                          │
            ├── Phase E (Tier 4a: Problem List) ── clinical data ─────┤
            │                                                          │
            ├── Phase F (Tier 4b: Scheduling) ── patient/clinic data ──┤
            │                                                          │
            └── Phase G (Tier 4c: Registration) ── patient data ───────┘
                                                                       │
                                                              100% COMPLETE
```

## Milestone Summary

| Milestone | Routines | Assertions | Cumulative | Key Deliverable |
|-----------|----------|------------|------------|-----------------|
| Phase A complete | 0 | 0 | Infrastructure | Parser, baseline runner, pytest adapter |
| Phase B complete | 8 | ~28 | 8 / 38 (21%) | M-Unit framework validated in Python |
| Phase C complete | 12 | ~124 | 12 / 38 (32%) | **MVP — Tier 1+2 passing** |
| Phase D complete | 17 | ~298 | 17 / 38 (45%) | FileMan validated, global bootstrap working |
| Phase E complete | 25 | ~647 | 25 / 38 (66%) | Problem List API validated |
| Phase F complete | 37 | ~1,194 | 37 / 38 (97%) | Scheduling validated |
| Phase G complete | 38 | ~1,204 | 38 / 38 (100%) | **All M-Unit tests passing** |

## Stretch Goal: m2py Issues Tracking

As each tier is attempted, m2py transpilation/runtime bugs will surface. Each bug follows this workflow:

1. **Discover** — transpiled test fails with Python error (not assertion failure)
2. **Extract** — create minimal MUMPS snippet reproducing the issue
3. **Fix** — fix in `src/m2py/` (codegen, analysis, or runtime)
4. **Test** — add standalone unit test in `tests/` (no VistA dependency)
5. **Verify** — re-run the M-Unit test that surfaced the bug

**Expected bug categories by tier**:

| Tier | Likely Issues |
|------|--------------|
| 1 (Self-tests) | `$ETRAP`, `DO @var` (indirection), `$TEXT`, `SETIO`/`RESETIO` I/O switching |
| 2 (XML Parser) | `$NAME`, `$PIECE` on long strings, `$ORDER` on `^TMP` trees, `%ZISH` file I/O |
| 3 (FileMan) | `%DT` date validation, `%DTC` date math, `^DD` traversal, `%ZOSF` entry loading |
| 4 (Clinical) | Complex indirection, `XLFDT` formatting, `$ORDER`/`$QUERY` on large trees, by-reference passing across packages |
