# Research: VistA M-Unit Test Suite via pytest

**Spec**: 026-vista-munit-tests | **Date**: 2025-07-22

## R1: M-Unit Framework Output Format

**Question**: What is the exact output format of `%ut` / `%ut1` so we can build a reliable parser?

**Decision**: Parse output using regex against these documented patterns from `ut.m`.

**Findings** (from `VistA-VEHU-M/Packages/MASH Utilities/Routines/ut.m` lines 60–250):

| Signal | Pattern | Source |
|--------|---------|--------|
| Assertion pass | Single `.` character (no newline) | `ut.m:184` `W "."` |
| Summary line 1 | `Ran N Routine(s), M Entry Tag(s)` | `ut.m:166` |
| Summary line 2 | `Checked X test(s), with Y failure(s) and encountered Z error(s).` | `ut.m:167–168` |
| CHKTF failure | `{entry}^{routine} - {name} - {message}\n` | `ut.m:213–214` |
| CHKEQ failure | `{entry}^{routine} - {name} - <{expected}> vs <{actual}> - {message}\n` | `ut.m:231–234` |
| Error | `{entry}^{routine} - {name} - Error: {$ZS or $ZE}\n` | `ut.m:260–262` |
| Verbose OK | `[OK]` after test name | `ut.m:156` |
| Verbose FAIL | `[FAIL]` after test name | `ut.m:160` |
| Verbose timing | `{N}ms` after OK/FAIL | `ut.m:138–147` |

**Key observations**:
- Non-verbose mode (default): output is dots + summary + failure lines only
- Verbose mode adds `[OK]`/`[FAIL]` per test and timing info
- The framework uses `$PRINCIPAL` for output via `SETIO^%ut1` / `RESETIO^%ut1` — these switch `$IO` temporarily
- Dots are written without newlines: `W "."` — parser must handle inline dots before the summary

**Alternatives considered**: None — the format is fixed by the M-Unit framework source.

---

## R2: M-Unit Test Discovery Mechanism

**Question**: How does M-Unit discover tests in a routine?

**Decision**: Two discovery modes — both supported in the framework's `CHEKTEST^%ut1`:

1. **NEWSTYLE (`@TEST` annotations)**: `%ut1` scans routine source for lines containing `;@TEST` comment annotation. Each annotated label becomes a test entry point.
2. **XTENT offset list**: Routine has a label `XTENT` with a list of `;;entrypoint^description` entries. Framework reads these sequentially.

**Findings** (from `ut1.m` lines 1–100):
- `CHEKTEST^%ut1` first checks for `XTENT` label in the routine
- If not found, falls back to `NEWSTYLE` scanning
- Self-tests (utt1–7) use `@TEST` annotations
- Some older VistA routines use `XTENT` style
- Discovery is at routine load time before any tests execute

**Alternatives considered**: Manual test lists — rejected because the framework handles discovery.

---

## R3: M-Unit Test Lifecycle

**Question**: What is the execution lifecycle of tests within a routine?

**Decision**: Document the lifecycle to ensure the transpiled framework preserves execution order.

**Findings** (from `ut.m` lines 60–170, `EN1` entry point):

```
STARTUP (once per routine, if label exists)
  For each test entry:
    SETUP (if label exists)
    test entry point execution
    TEARDOWN (if label exists)
SHUTDOWN (once per routine, if label exists)
```

- `$ETRAP` set to `D ERROR^%ut` — all errors are caught and recorded
- Error in a test does NOT stop the routine — execution continues to next test
- `%ut("CURR")` tracks current routine index
- `%ut("ECNT")` tracks entry count within current routine
- `%ut("CHK")` tracks total assertion count
- `%ut("FAIL")` tracks total failure count
- `%ut("ERESSION")` tracks error count

---

## R4: Self-Test Dependencies (Tier 1: utt1–utt7 + uttcovr)

**Question**: What external dependencies do the M-Unit self-tests have?

**Decision**: Self-tests are nearly self-contained. Only conditional dependency is `^DIC` (safely guarded).

**Findings**:

| File | Globals Used | External Routines | Notes |
|------|-------------|-------------------|-------|
| utt1.m | `^TMP($J)` | `%ut` only | STARTUP sets ^TMP, SETUP increments KBANCOUNT, 7 test tags (T1–T7) |
| utt2.m | `^TMP($J)` | `%ut`, `%utt2` (self-ref) | Tests CACHECOV; replaced `^%ZOSF("LOAD")` with inline code |
| utt3.m | `^TMP($J)` | `%ut` | Basic assertion tests |
| utt4.m | none | none | `$$NOW` copied from XLFDT — no external dependency |
| utt5.m | `^TMP($J)` | `%ut`, `%utt4` | Variable leak tests; replaced `$$NOW^XLFDT` with `$$NOW^%utt4` |
| utt6.m | `^TMP($J)` | `%ut`, `%uttcovr` | Guarded `I $T(+1^DIC)'="" D CMNDLINE` — skips if DIC absent |
| utt7.m | `^TMP($J)` | `%ut` | Additional tests |
| uttcovr.m | `^TMP($J)` | `%ut` | Coverage tests called from utt6 |

**Key finding**: The self-tests deliberately removed VA Kernel dependencies (commit history shows `XLFDT` replaced with local copy, `%ZOSF("LOAD")` replaced with inline code). They are designed to run standalone.

**Routines required for transpilation**: `%ut`, `%ut1`, `%utt1`–`%utt7`, `%uttcovr` (10 total).

---

## R5: XML Parser Test Dependencies (Tier 2: MXMLDOMT, MXMLBLD, MXMLPATT, MXMLTMPT)

**Question**: What external dependencies do the M XML Parser tests have?

**Decision**: Moderate dependency set — requires the XML parser codebase (~8 routines) plus FileMan for MXMLTMPT.

**Findings**:

| File | Globals | External Routines | Risk |
|------|---------|-------------------|------|
| MXMLBLD.m | `^TMP("MXMLBLD",$J)` | `%ut`, `MXMLUTL`, `MXMLTMP1` | Low — XML builder logic |
| MXMLDOMT.m | `^TMP($J)` | `%ut`, `MXMLDOM`, `%ZISH` | **High** — file I/O via `%ZISH` |
| MXMLPATT.m | `^TMP($J)` | `%ut`, `MXMLDOM`, `MXMLPATH` | Medium — DOM + XPath |
| MXMLTMPT.m | local only | `%ut`, `MXMLTMP1`, `MXMLTMPL`, `DT^DICRW` | Medium — template + FileMan |

**Full XML dependency tree** (routines to transpile):
- `MXMLDOM` — DOM parser (core)
- `MXMLPRSE` — SAX-style parser (used by MXMLDOM)
- `MXMLUTL` — XML utility functions (encoding)
- `MXMLPATH` — XPath implementation
- `MXMLTMP1` — Template engine (push/apply)
- `MXMLTMPL` — Template application
- `MXMLBLD` — XML builder (also a test file)
- `%ZISH` — Kernel file I/O (used only by MXMLDOMT)
- `DICRW` — FileMan (used only by MXMLTMPT `DT^DICRW`)

**Risk**: `%ZISH` performs actual file system operations (`$$GTF^%ZISH` = global-to-file, `$$DEL^%ZISH` = delete). The transpiled version needs to handle these, or MXMLDOMT may need to be deferred.

**Alternative**: Start with MXMLBLD.m and MXMLTMPT.m which have fewer dependencies, defer MXMLDOMT.m and MXMLPATT.m.

---

## R6: Transpilation API and Execution Pattern

**Question**: How should transpiled M-Unit tests be loaded and executed?

**Decision**: Follow the existing functional test pattern from `tests/functional/conftest.py`.

**Findings** (from `src/m2py/codegen/__init__.py:151` and `tests/functional/conftest.py:330–410`):

```python
# 1. Transpile MUMPS → Python
from m2py.codegen import generate_python
python_code = generate_python(mumps_source, routine_name="utt1")

# 2. Create module and inject
import types, sys
mod = types.ModuleType("utt1")
exec(python_code, mod.__dict__)
sys.modules["utt1"] = mod

# 3. Execute with runtime
from m2py.runtime import MUMPSRuntime
runtime = MUMPSRuntime()
runtime._capture_output = True  # Capture WRITE output

# 4. Call the entry point
mod.EN(runtime)  # or whatever the entry label is

# 5. Get output
output = runtime.get_output()
```

**Key detail**: `generate_python()` returns a Python string. The caller must `exec()` it into a module namespace. The runtime is shared across all modules in a test session (important for globals like `^TMP`).

**For M-Unit**: The test runner would:
1. Transpile `%ut`, `%ut1`, and all test routines
2. Load all into a shared module namespace
3. Call `EN^%ut(routine_name, verbose)` on the transpiled `%ut`
4. Capture output and parse it

---

## R7: m2py Runtime Compatibility with M-Unit

**Question**: What m2py runtime features does M-Unit depend on, and which are potentially missing?

**Decision**: Document known gaps for the implementation plan to address.

**Findings**:

| Feature | Used By | m2py Status | Notes |
|---------|---------|-------------|-------|
| `$SYSTEM` ($SY) | `GETSYS^%ut` | ✅ Supported | Returns `"47,m2py"` → GETSYS()=47 (GT.M path) |
| `$ZSTATUS` ($ZS) | `ERROR^%ut` | ✅ Supported | Lines 3075–3095 of runtime/__init__.py |
| `$ETRAP` | `EN1^%ut` | ⚠️ Needs verification | Error trap mechanism — critical for test lifecycle |
| `$ZGETJPI` | Verbose timing | ❌ Not implemented | Only used when `%utVERB=2` — skip verbose mode |
| `$TEXT` ($T) | Discovery, guards | ⚠️ Needs verification | Used for `$T(+1^DIC)` guard and `NEWSTYLE` scanning |
| `DO @var` | Indirection | ⚠️ Needs verification | Used for `D @%ut("ENT")` — calling test entry points |
| `$NAME` ($NA) | `utt1` | ⚠️ Needs verification | Used for global reference construction |
| `^TMP($J)` globals | Most tests | ✅ Expected | Runtime global store should handle this |
| `SETIO/RESETIO` | I/O switching | ⚠️ Needs design | May need runtime support for `$IO`/`$PRINCIPAL` |

**Critical for success**: `$ETRAP`, `DO @var` (indirection), and `$TEXT` are essential for the framework. These must be verified/fixed early.

**Non-critical**: `$ZGETJPI` only affects verbose timing display. Running in non-verbose mode avoids this entirely.

---

## R8: Cross-Repository Architecture

**Question**: How should vista-test depend on m2py for transpilation?

**Decision**: vista-test adds m2py as a path-based dev dependency (both repos are co-located in the workspace).

**Findings**:
- `vista-test/pyproject.toml` currently has `paramiko>=3.0` as only dependency
- m2py is at `/workspaces/m2py/` (workspace root)
- vista-test is at `/workspaces/m2py/vista-test/` (subdirectory)
- The dependency can be added as: `m2py = {path = ".."}` in vista-test's pyproject.toml
- Alternative: `uv add --dev --path ..` from vista-test directory

**Architecture**:
```
/workspaces/m2py/                  # m2py root (transpiler + runtime)
├── src/m2py/                      # transpiler source
├── tests/                         # m2py unit tests (standalone)
└── vista-test/                    # vista-test repo (separate git)
    ├── src/vista_test/            # VistA test framework
    │   └── munit/                 # NEW: M-Unit support module
    │       ├── parser.py          # M-Unit output parser
    │       ├── baseline.py        # Baseline runner (SSH to VEHU)
    │       └── adapter.py         # pytest adapter (transpile + run)
    ├── tests/vista/munit/         # NEW: M-Unit pytest tests
    │   └── conftest.py            # pytest plugin (discovery, xfail)
    ├── baselines/                  # NEW: Committed baseline JSON
    └── VistA/                     # Submodule (read-only)
```

---

## R9: VEHU Docker Baseline Capture Approach

**Question**: How to execute M-Unit tests via SSH to capture baseline output?

**Decision**: Use `VistATerminal` from vista-test for SSH connection, send MUMPS commands, capture output.

**Findings** (from `vista-test/src/vista_test/terminal/session.py:233`):
- `VistATerminal` has `connect()`, `send()`, `send_and_wait()`, `expect()` methods
- SSH transport to VEHU: port 2222, user `vehuprog`, password `prog`
- For programmer mode direct access: send MUMPS commands directly
- Each test routine execution: `D EN^%ut("routinename")`
- Capture output between command and next prompt

**Alternative**: Use `utils/run_mumps_ydb.py` pattern — but that's for YDB not VEHU. The SSH approach via `VistATerminal` is correct for VEHU.

**TestList invocation formats** (from actual TestList files):
- M-Unit self-tests: `D EN^%ut("%utt1",1)` (verbose), or `D ^%utt1` (non-verbose entry point)
- XML Parser: `D TEST^MXMLBLD`, `D ^MXMLDOMT`, `D TEST^MXMLPATT`, `D TEST^MXMLTMPT`
- Problem List: `D ^ZZRGUT`, `D ^ZZRGUT1`, `D ^ZZRGUT2`, etc.
- VA FileMan: `D ^ZZUTDIDT`, `D ^DMUDIC00`, `D ^DMUDT000`, `D ^DMUDTC00`, `D ^DMUDIQ00`
- Scheduling: `D ^ZZUTGETAPPT`, `D ^ZZRGUSD1`, ..., `D ^ZZRGUSD6`
- Registration: `D ^ZZDGPTCO1`

---

## R10: Parser Design for Robustness

**Question**: How to handle edge cases in M-Unit output parsing?

**Decision**: Two-pass parser — first extract summary, then extract failures/errors.

**Approach**:
1. **Summary regex**: `r"Checked\s+(\d+)\s+tests?,\s+with\s+(\d+)\s+failures?\s+and\s+encountered\s+(\d+)\s+errors?\."`
2. **Failure regex**: `r"^(\S+)\^(\S+)\s+-\s+(.+?)\s+-\s+(.+)$"` for CHKTF; with `<expected> vs <actual>` variant for CHKEQ
3. **Error regex**: `r"^(\S+)\^(\S+)\s+-\s+(.+?)\s+-\s+Error:\s+(.+)$"`
4. **Dots**: Count `.` characters before summary line for assertion tracking
5. **Partial output**: If no summary line found, mark as error and extract whatever failures/errors are present

**Edge cases**:
- Multi-routine runs: M-Unit outputs one summary per routine when called with `EN^%ut`
- Self-referential output from `%utt` (framework testing itself produces nested dots)
- VEHU prompt text mixed in with output (SSH capture includes prompt strings)
- `W !` produces newlines — output may have blank lines between elements

---

## R11: VA FileMan Test Dependencies (Tier 3)

**Question**: What is required to run the 5 VA FileMan test routines?

**Decision**: FileMan tests require substantial infrastructure — `^DD` (data dictionary), `^DIC` globals, `%ZISH` file I/O, and the `DMUFINIT` fixture routine.

**Findings**:

| Routine | Assertions | Key Dependencies |
|---------|-----------|-----------------|
| ZZUTDIDT | 3 | `%DT` (date/time) — simplest FileMan test |
| DMUDIC00 | 14 | `^DIC`, `^DIBT`, `DMUFINIT` (fixtures), `XPDUTL` |
| DMUDT000 | 58 | `%DT`, `%ZISH`, `%ZOSF` |
| DMUDTC00 | 92 | `%DTC` (date/time calc), `%ZISH` |
| DMUDIQ00 | 7 | `^DD`, `^DIC`, `DIQ`, `DIQ1`, `DILFD`, `%ZISH` |

**Prerequisites for Tier 3**:
1. **Global bootstrap**: Must export `^DD`, `^DIC`, and related globals from VEHU (~large dataset)
2. **DMUFINIT fixture**: Creates test files 1009.801, 1009.802 in `^DD` — must run as STARTUP
3. **%ZISH transpilation**: File I/O operations (`$$GTF`, `$$DEL`, `$$DEFDIR`) must work in Python
4. **%ZOSF transpilation**: MUMPS entry point loader — DMUDT000 depends on it
5. **ZZUTDIDT** is the lowest-risk entry point (only needs `%DT` date validation)

**Estimated effort**: Medium-High. Global export alone could be significant. `%ZISH` and `%ZOSF` are complex Kernel utilities with platform-specific behavior.

---

## R12: Problem List Test Dependencies (Tier 4a)

**Question**: What is required to run the 8 Problem List test routines?

**Decision**: Problem List tests have deep clinical data dependencies and call many GMPL* (Problem List API) routines.

**Findings**:

| Routine | Assertions | Key Dependencies |
|---------|-----------|-----------------|
| ZZRGUT | 83 | `GMPLAPI2–4`, `GMPLMGR`, `GMPLDAL`, `^AUPNPROB`, `XLFDT` |
| ZZRGUT1 | 87 | `GMPLAPI1`, `GMPLAPI6`, `^SC`, `^VA`, `XLFDT` |
| ZZRGUT2 | 6 | `GMPLSITE`, `XLFDT` |
| ZZRGUT3 | 60 | `GMPLAPI1`, `GMPLAPI5–6`, `^SC`, `^VA`, `XLFDT` |
| ZZRGUT4 | 38 | `GMPLAPI1–2`, `GMPLAPI6`, `^SC`, `^VA`, `XLFDT` |
| ZZRGUT5 | 8 | `GMPLAPI2`, `GMPLAPI7`, `GMPLHIST`, `GMPLX`, `XLFDT` |
| ZZRGUTRB | 38 | `GMPLMGR`, `GMPLSAVE`, `GMPLX`, `ORQQPL1–3`, `^AUPNPROB`, `XLFDT` |
| ZZRGUTEX | 29 | `ACKQUTL6`, `IBDFBK3`, `PXRMPROB`, `GMPLMGR`, `GMPLUTL`, `XUS1A` — **many cross-package deps** |

**Total assertions**: ~349 across 8 routines.

**Prerequisites for Tier 4a**:
1. **GMPL* API routines**: Full Problem List API (~10 routines: GMPLAPI1–7, GMPLMGR, GMPLDAL, GMPLSAVE, GMPLSITE, GMPLHIST, GMPLUTL, GMPLX)
2. **Global state**: `^AUPNPROB` (ICD/problem dictionary), `^GMPL` (problem list data), `^SC` (clinic data), `^VA` (VA-specific data)
3. **ORQQPL1–3**: CPRS Problem List RPC handlers (ZZRGUTRB uses these)
4. **ZZRGUTCM**: Shared test utility routine (referenced by ZZRGUT, ZZRGUT5, ZZRGUTRB)
5. **XLFDT**: Date/time formatting library (used by all routines)
6. **ZZRGUTEX** has the broadest dependency surface — references routines across 6+ VistA packages

**Estimated effort**: Very High. Requires transpiling 20+ API routines and loading substantial clinical global data.

---

## R13: Scheduling Test Dependencies (Tier 4b)

**Question**: What is required to run the 12 Scheduling test routines?

**Decision**: Scheduling tests split into two groups: SDK-style API tests (ZZUT*) and regression tests (ZZRGUSD*).

**Findings**:

**Group A — Scheduling SDK API tests (6 routines, ~84 assertions)**:
| Routine | Assertions | Key Dependencies |
|---------|-----------|-----------------|
| ZZUTGETAPPT | 14 | `SDAMA201` (Get Appointments API) |
| ZZUTNEXTAPPT | 11 | `SDAMA201` |
| ZZUTSDAPI | 35 | `SDAMA301` (Scheduling actions API) |
| ZZUTSDIMO | 4 | `SDAMA203` (IMO API) |
| ZZUTGETPLIST | 15 | `SDAMA202` (Patient List API) |
| ZZUTPATAPPT | 5 | `SDAMA204` (Patient Appointments API), `^DPT` |

All share `ZZUTSDCOM` (common setup/teardown utility).

**Group B — Scheduling regression tests (6 routines, ~463 assertions)**:
| Routine | Assertions | Key Dependencies |
|---------|-----------|-----------------|
| ZZRGUSD1 | 103 | `SDMAPI1–2`, `^DIC`, `^SC`, `^DPT` |
| ZZRGUSD2 | 68 | `SDCAPI1`, `SDMAPI1–2`, `^DPT` |
| ZZRGUSD3 | 81 | `SDCAPI1`, `SDMAPI1–4`, `^DPT`, `^SC` |
| ZZRGUSD4 | 60 | `SDMAPI1–2`, `SDMAPI5`, `^DPT`, `^SC` |
| ZZRGUSD5 | 82 | `DGSAAPI`, `SDMAPI1–4`, `^DPT`, many globals |
| ZZRGUSD6 | 69 | `SCAPMC21`, `SCTMAPI1`, `SDMAPI1–2`, `^DIC` |

All share `ZZRGUSD5` (common utility) and `ZZRGUSDC` (shared setup).

**Total assertions**: ~547 across 12 routines.

**Prerequisites for Tier 4b**:
1. **SDAMA* API routines**: Scheduling Data Management APIs (201–204, 301)
2. **SDMAPI* routines**: Scheduling Management APIs (1–5)
3. **SDCAPI1**: Scheduling Cancel API
4. **Global state**: `^DPT` (patient data), `^SC` (clinic/hospital locations), `^SD` (scheduling data)
5. **ZZUTSDCOM / ZZRGUSDC**: Test common setup routines (create test patients/clinics)

**Estimated effort**: Very High. Largest test package by assertion count. Requires patient, clinic, and appointment data.

---

## R14: Registration Test Dependencies (Tier 4c)

**Question**: What is required to run the 1 Registration test routine?

**Decision**: Registration is the smallest stretch package and could be a good intermediate target.

**Findings**:
| Routine | Assertions | Key Dependencies |
|---------|-----------|-----------------|
| ZZDGPTCO1 | 10 | `DGPTCO1`, `^DG`, `DICRW` |

**Prerequisites**: `DGPTCO1` (patient combine API), `^DG*` globals, patient data in `^DPT`, FileMan available (`DICRW`).

**Estimated effort**: Medium. Small routine but still requires patient data bootstrap. Could potentially be attempted alongside Tier 3 once FileMan infrastructure is working.

---

## R15: Global Bootstrap Strategy for Stretch Goals

**Question**: How to bootstrap the global state needed by Tier 3+4 routines?

**Decision**: Two-phase bootstrap approach — FileMan first, then clinical data.

**Phase 1 — FileMan Bootstrap (enables Tier 3)**:
- Export `^DD` (data dictionary definitions — core of FileMan)
- Export `^DIC` (file name/attributes)
- Export `^%ZOSF` (entry points)
- Run `DMUFINIT` to create test fixture files
- Estimated size: ~50-100 MB in ZWR format for full `^DD`

**Phase 2 — Clinical Data Bootstrap (enables Tier 4)**:
- Export `^DPT` (patient records — at least the test patients)
- Export `^SC` (hospital location / clinics)
- Export `^AUPNPROB` (ICD problem dictionary)
- Export `^GMPL*` (Problem List data)
- Export `^SD*` (Scheduling data)
- Export `^DG*` (Registration data)
- Plus any cross-reference indices these globals depend on

**Implementation approach**:
1. Build a `GlobalBootstrap` class that connects to VEHU via SSH
2. Uses `%GO` (Global Output) or direct `$O` traversal to export globals in ZWR format
3. Imports into m2py `MDict` global store
4. Cached on disk after first export (avoid re-exporting each run)
5. Pytest fixtures manage bootstrap lifecycle per tier

**Alternative**: Export only the specific global subtrees referenced by test assertions (surgical precision but fragile). Rejected because missing subscript paths would produce confusing failures.
