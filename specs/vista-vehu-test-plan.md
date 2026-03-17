# VistA-VEHU Runtime Validation Test Plan

## Executive Summary

**Transpilation is complete.** With 99.99% of VistA-VEHU-M routines transpiling successfully, the goal now shifts to **proving correct transpilation** through progressive runtime testing. This document defines a phased strategy for validating transpiled Python code against the original MUMPS behavior, starting with foundational library functions and building toward full CPRS workflow coverage.

The validation approach compares outputs from:
1. **YottaDB** — Running original MUMPS code
2. **m2py** — Running transpiled Python code

Each layer of VistA is tested and validated before moving to dependent layers, ensuring that any discrepancies are caught and fixed at their source.

**VistA-VEHU-M scope**: 175 packages, ~4,485 registered RPCs, thousands of roll-and-scroll menu options.

**m2py transpilation status** (measured 2026-02-18):

| Metric | Value |
|--------|-------|
| **Total routines** | 39,304 |
| **Transpile OK** | 39,299 (99.99%) |
| **Failures** | 5 (4 MWAPI + 1 malformed) |

**Per-package status** (key packages — all at 100%):

| Package | Routines | Transpile OK | Rate | Notes |
|---------|----------|-------------|------|-------|
| RPC Broker (XWB) | 40 | 40 | 100% | Ready for runtime testing |
| Foundations (XOBU) | 8 | 8 | 100% | Ready |
| List Manager (VALM) | 48 | 48 | 100% | Ready |
| Problem List (GMPL) | 94 | 94 | 100% | Ready |
| Kernel Library (XLF) | 33 | 33 | 100% | Ready |
| Health Summary (GMTS) | 294 | 294 | 100% | Ready |
| Virtual Patient Record (VPR) | 104 | 104 | 100% | Ready |
| Consult Request Tracking (GMRC) | 225 | 225 | 100% | Ready |

**Remaining failures** (5 routines):
- **ZISG, ZISG1, ZISG2, ZISG3** — MWAPI routines using `^$EVENT`, `^$WINDOW` SSVNs (LIM-003, X11.6 standard)
- **ZZBACSUA** — Malformed MUMPS syntax in source file

---

## Architecture: VistA Package Dependency Layers

VistA has a well-defined layered architecture. Lower layers are required by upper layers:

```
Layer 5: Clinical Applications
         ┌──────────────────────────────────────────────────────┐
         │ Problem List (GMPL)  │ TIU (Text Integration)       │
         │ Consults (GMRC)      │ Health Summary (GMTS)        │
         │ Vitals (GMR)         │ Clinical Reminders (PXRM)    │
         │ CPRS/OERR (OR*)      │ VPR (Virtual Patient Record) │
         └──────────────────────────────────────────────────────┘

Layer 4: Clinical Infrastructure
         ┌──────────────────────────────────────────────────────┐
         │ Registration (DG)    │ Scheduling (SD)               │
         │ Patient File (DPT)   │ PCE (AUPN/PX)                │
         │ Pharmacy (PS)        │ Lab (LR)                      │
         │ Radiology (RA)       │ Lexicon (LEX)                 │
         └──────────────────────────────────────────────────────┘

Layer 3: Integration Services
         ┌──────────────────────────────────────────────────────┐
         │ RPC Broker (XWB)     │ VistALink (XOBV)             │
         │ List Manager (VALM)  │ HL7 (HLCS/HL)                │
         │ MailMan (XM)         │ KIDS/PatchMgmt (XPD)         │
         └──────────────────────────────────────────────────────┘

Layer 2: VA FileMan (DI/DD/DIC/DIE/DIR)
         ┌──────────────────────────────────────────────────────┐
         │ Data Dictionary (DD) │ Input/Edit (DIE)              │
         │ Lookup (DIC)         │ Print (DIP)                   │
         │ Read (DIR)           │ Sort (DIS)                    │
         │ Data Extract (DIQ)   │ Computed Fields (DIEQ)        │
         └──────────────────────────────────────────────────────┘

Layer 1: Kernel (XU*)
         ┌──────────────────────────────────────────────────────┐
         │ Library Fns (XLF*)   │ Device Mgmt (ZIS*)           │
         │ Security (XUS*)      │ Menu System (XQ*)            │
         │ TaskMan (ZTM*)       │ Alerts (XQA*)                │
         │ Parameter (XPar)     │ Toolkit (XT*)                │
         └──────────────────────────────────────────────────────┘

Layer 0: M Language Runtime
         ┌──────────────────────────────────────────────────────┐
         │ m2py runtime: MArray, MUMPSRuntime, globals, I/O    │
         └──────────────────────────────────────────────────────┘
```

---

## Testing Strategies

Three complementary testing strategies validate transpiled code at different levels of integration:

### Strategy 1: Direct Function Call Testing

**Purpose**: Validate pure computation functions with no I/O or global state dependencies.

**Approach**: Transpile both the function under test AND the test harness call, then compare outputs.

```
┌─────────────────────────────────────────────────────────────────┐
│ Test Harness (MUMPS)           │  Test Harness (Python)        │
│ ────────────────────           │  ────────────────────         │
│ TEST                           │  (transpiled from MUMPS)      │
│  W $$UP^XLFSTR("hello"),!      │  → executes transpiled code   │
│  W $$CRC32^XLFCRC("data"),!    │  → captures stdout            │
│  Q                             │                               │
└─────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
    YottaDB Output                     Python Output
    "HELLO\n3785022994\n"              "HELLO\n3785022994\n"
         │                                    │
         └────────────► COMPARE ◄─────────────┘
                          ✓ MATCH
```

**Implementation**:
1. Create a MUMPS test harness routine with function calls and WRITE statements
2. Run harness through YottaDB via `utils/run_mumps_ydb.py` → capture stdout
3. Transpile the harness + all dependencies via m2py
4. Execute transpiled Python → capture stdout
5. Assert outputs match exactly (or with normalized whitespace)

**Best for**: XLF library functions, pure computation routines, extrinsic functions (`$$TAG^ROUTINE`)

**Example test fixture**:
```python
def test_xlfstr_up():
    harness = '''TEST
 W $$UP^XLFSTR("hello world"),!
 Q'''
    ydb_output = run_ydb(harness, dependencies=["XLFSTR"])
    py_output = transpile_and_run(harness, dependencies=["XLFSTR"])
    assert ydb_output == py_output
```

---

### Strategy 2: RPC Testing (via vista-test library)

**Purpose**: Validate RPC entry points that return structured data to GUI clients.

**Approach**: Use the `vista-test` RPC broker client to call RPCs against both YottaDB VistA and transpiled m2py server, comparing responses.

```
┌─────────────────────────────────────────────────────────────────┐
│  vista-test VistABroker                                         │
│  ──────────────────────                                         │
│  broker.call("XWB EGCHO STRING", [param])                       │
│                                                                 │
│         ┌──────────────────┐    ┌──────────────────┐           │
│         │  YottaDB VistA   │    │  m2py Server     │           │
│         │  (TCP port 9430) │    │  (TCP port 9431) │           │
│         └──────────────────┘    └──────────────────┘           │
│                │                         │                      │
│                ▼                         ▼                      │
│          RPC Response              RPC Response                 │
│                │                         │                      │
│                └──────► COMPARE ◄────────┘                     │
│                           ✓ MATCH                              │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation** (using vista-test library):
```python
from vista_test.rpc import VistABroker

def test_rpc_echo_string():
    # Call against YottaDB VistA
    with VistABroker("localhost", 9430) as ydb_broker:
        ydb_broker.authenticate(access="PRO1234", verify="PRO1234!!")
        ydb_broker.create_context("XWB RPC CONTEXT")
        ydb_result = ydb_broker.call("XWB EGCHO STRING", ["hello"])
    
    # Call against m2py server
    with VistABroker("localhost", 9431) as m2py_broker:
        m2py_broker.authenticate(access="PRO1234", verify="PRO1234!!")
        m2py_broker.create_context("XWB RPC CONTEXT")
        m2py_result = m2py_broker.call("XWB EGCHO STRING", ["hello"])
    
    assert ydb_result == m2py_result
```

**Best for**: All registered RPCs (4,485 in VistA-VEHU), CPRS workflows, any TAG^ROUTINE entry point

**Prerequisites**: 
- m2py RPC Broker server implementation (responds to RPC protocol)
- Pre-populated global state (user records, RPC definitions, etc.)

---

### Strategy 3: Terminal Roll-and-Scroll Testing (via vista-test library)

**Purpose**: Validate interactive menu-driven interfaces that use terminal I/O.

**Approach**: Use the `vista-test` terminal client to drive menu interactions against both systems, comparing screen outputs and navigation behavior.

```
┌─────────────────────────────────────────────────────────────────┐
│  vista-test VistATerminal                                       │
│  ────────────────────────                                       │
│  terminal.send("LM")           # Select List Manager            │
│  terminal.expect("Select:")    # Wait for prompt                │
│  output = terminal.screen      # Capture screen state           │
│                                                                 │
│         ┌──────────────────┐    ┌──────────────────┐           │
│         │  YottaDB VistA   │    │  m2py Terminal   │           │
│         │  (SSH/telnet)    │    │  (SSH/telnet)    │           │
│         └──────────────────┘    └──────────────────┘           │
│                │                         │                      │
│                ▼                         ▼                      │
│          Screen Output            Screen Output                 │
│          Menu State               Menu State                    │
│                │                         │                      │
│                └──────► COMPARE ◄────────┘                     │
│                      ✓ MATCH (normalized)                      │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation** (using vista-test library):
```python
from vista_test.terminal import VistATerminal

def test_list_manager_navigation():
    # Drive YottaDB VistA terminal
    with VistATerminal("ydb-host", user="vehu", password="vehu") as ydb_term:
        ydb_term.login(access="PRO1234", verify="PRO1234!!")
        ydb_term.send("LM")
        ydb_term.expect("ListMan")
        ydb_output = ydb_term.screen
    
    # Drive m2py terminal
    with VistATerminal("m2py-host", user="vehu", password="vehu") as m2py_term:
        m2py_term.login(access="PRO1234", verify="PRO1234!!")
        m2py_term.send("LM")
        m2py_term.expect("ListMan")
        m2py_output = m2py_term.screen
    
    assert normalize_screen(ydb_output) == normalize_screen(m2py_output)
```

**Best for**: FileMan (DI*), List Manager (VALM*), Menu System (XQ*), any roll-and-scroll interface

**Prerequisites**:
- m2py terminal server implementation (responds to SSH/telnet with $PRINCIPAL I/O)
- VT100 output normalization for comparison

---

### Strategy Selection by VistA Layer

| Layer | Primary Strategy | Secondary Strategy |
|-------|------------------|-------------------|
| Layer 0 (m2py runtime) | Unit tests (existing pytest suite) | — |
| Layer 1 (Kernel XLF*) | **Direct function call** | — |
| Layer 2 (FileMan) | Direct function call | **Terminal** |
| Layer 3 (Integration - XWB*) | **RPC** | Direct function call |
| Layer 4 (Clinical Infra) | RPC | Terminal |
| Layer 5 (Clinical Apps) | **RPC** | Terminal |

---

### Runtime Prerequisites by Strategy

Each testing strategy requires different levels of m2py runtime support. Strategy 1 works today; Strategies 2 and 3 require new infrastructure built in dedicated phases before they can be used.

#### Strategy 1: Direct Function Call — Ready Now

**No additional m2py infrastructure required.** The transpiled code runs as Python, writing to `$PRINCIPAL` (captured via `PrincipalDevice._output`). All required runtime features are already implemented: `PrincipalDevice`, `$X`/`$Y` tracking, `READ` variants, `WRITE` format controls, file I/O, globals (`MDict`/SQLite), `LOCK`, `$TEST`, indirection.

#### Strategy 2: RPC Server — Built in Phase 2

The RPC interface does **not** fall out of transpilation. The VistA RPC Broker (XWBTCPL) uses GT.M-specific TCP server primitives (`ZLISTEN`, `W /LISTEN`, `W /WAIT`, multi-socket devices) that m2py's `TCPDevice` doesn't support. Instead of implementing the full GT.M socket device model, **Phase 2 builds a Python-native RPC server** that speaks the RPC Broker protocol and dispatches into transpiled RPC handler routines. See Phase 2 for the full gap analysis and build plan.

#### Strategy 3: Terminal Server — Built in Phase 5

The terminal interface also does **not** fall out of transpilation. VistA's roll-and-scroll depends on terminal capability variables, device configuration globals, and Kernel I/O utilities that go beyond what transpiled code alone provides. **Phase 5 builds a Python-native terminal server** wrapping a PTY, with IO variable bootstrap and terminal capability setup. See Phase 5 for the full gap analysis and build plan.

#### Summary: Transpiled vs. Purpose-Built

| Component | Transpiled? | Purpose-built? |
|-----------|-------------|----------------|
| RPC business logic (XWBZ1, XUSRB, GMPL*, TIU*) | ✅ Yes | — |
| RPC protocol server (TCP listen, accept, dispatch) | ❌ No | Phase 2 |
| NULL device for RPC isolation | ❌ No | Phase 2 |
| Terminal UI logic (XQ*, VALM*, ^DIR, ^DIC) | ✅ Yes | — |
| Terminal connection management | ❌ No | Phase 5 |
| Terminal capability setup (IO vars, escape seqs) | ❌ No | Phase 5 |
| Global data (`^XWB(8994)`, `^%ZIS`, `^DIC(19)`, etc.) | ❌ No | Phase 2 (RPC globals), Phase 5 (terminal globals) |
| Direct function calls (XLF*, utility functions) | ✅ Yes | — |

The pattern is consistent: **business logic transpiles and works, but server infrastructure must be purpose-built in Python**. This is actually a strength — the Python-native servers are simpler, more testable, and avoid the GT.M-specific socket model entirely, while the transpiled code provides the actual VistA functionality.

---

## Phase 0: OSEHRA M-Unit Test Suite via pytest

**Goal**: Leverage the existing OSEHRA M-Unit test suite (58 test routines, 1,186 assertions) as the foundational validation layer. First establish a baseline by running the tests against the VEHU Docker container, then run the same tests — transpiled to Python — against the transpiled VistA-VEHU codebase.

**Why this approach**: Rather than writing new test harnesses for individual functions, we reuse the comprehensive test suite that VistA's own CI system relies on:
- **Pre-existing coverage** — Tests already exist for VA FileMan (date/time, DIC, DT, DIQ), Problem List, Scheduling, Registration, and M XML Parser
- **Proven correctness** — These tests are maintained by the OSEHRA community and run against production VistA instances
- **Baseline comparison** — Running on VEHU Docker first reveals which tests pass/fail in MUMPS, so we only expect matching behavior from the transpiled Python
- **Transpilable test framework** — The `%ut` (M-Unit) framework is itself pure MUMPS and transpiles via m2py, so both test infrastructure and test routines run natively in Python
- **Broad dependency coverage** — These tests exercise FileMan, Kernel Library, Problem List API, Scheduling API, and XML parsing — spanning Layers 0-4 of the VistA architecture

### M-Unit Framework Overview

The **M-Unit** testing framework (`%ut` / `%ut1`, from the MASH Utilities package) is VistA's built-in unit testing system. It provides:

| M-Unit API | pytest Equivalent | Description |
|------------|-------------------|-------------|
| `CHKEQ^%ut(expected,actual,msg)` | `assert actual == expected` | Assert equality |
| `CHKTF^%ut(value,msg)` | `assert value` | Assert truthy |
| `FAIL^%ut(msg)` | `pytest.fail(msg)` | Explicit failure |
| `SUCCEED^%ut` | (implicit pass) | Force success |
| `STARTUP` tag | `setup_module()` | Runs once before all tests in routine |
| `SHUTDOWN` tag | `teardown_module()` | Runs once after all tests in routine |
| `SETUP` tag | `setup_function()` | Runs before each test |
| `TEARDOWN` tag | `teardown_function()` | Runs after each test |

**Test discovery** uses two mechanisms:
1. **`@TEST` annotation** — Tags like `T1 ; @TEST - Make sure Start-up runs` are discovered by scanning routine source
2. **`XTENT` offset list** — Tag `XTENT` contains a list of entry points to run (older convention)

**Output format**: Each assertion prints `.` on success. Failures print `ENTRY - NAME - message`. Summary: `"Ran N Routines, M Entry Tags\nChecked X tests, with Y failures and encountered Z errors."`

### Target: 5 packages, 58 test routines, 1,186 assertions

| Package | Test Routines | Assertions | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **VA FileMan** | 30 (DMUDT000, DMUDIC00, DMUDTC00, DMUDIQ00, ZZUTDIDT, DMUFI*, DMUFINI*) | ~175 | `^DIC`, `^DT`, `^DIQ`, `^DIE`, `^DD` | Date/time, lookup, sort, computed fields. DMUFI* routines create test fixtures (files 1009.801, 1009.802) |
| **Problem List** | 9 (ZZRGUT, ZZRGUT1-5, ZZRGUTRB, ZZRGUTEX, ZZRGUTCM) | ~232 | `GMPLAPI*`, `AUPNPROB`, `XLFDT`, `XLFSTR` | Full CRUD via Problem List API: add, edit, delete, verify, replace |
| **Scheduling** | 12 (ZZRGUSD1-6, ZZUTGETAPPT, ZZUTNEXTAPPT, ZZUTSDAPI, ZZUTSDIMO, ZZUTGETPLIST, ZZUTPATAPPT) | ~463 | `SD*`, `^SC`, `^DPT`, `XLFDT` | Appointment management, scheduling API |
| **Registration** | 1 (ZZDGPTCO1) | ~10 | `DG*`, `^DPT` | Patient record validation |
| **M XML Parser** | 4 (MXMLDOMT, MXMLBLD, MXMLPATT, MXMLTMPT) | ~97 | `MXML*`, `%ZISH` | DOM parsing, XML builder, pattern matching |
| **M-Unit self-tests** | 7 (utt1-7, uttcovr) | ~50+ | `%ut`, `%ut1` | Framework's own regression tests |

**Important**: These test routines live in `VistA/Packages/*/Testing/MUnit/` (the OSEHRA testing repo), **not** in VistA-VEHU-M. They must be imported into the environment before running — exactly as the OSEHRA ctest infrastructure does via `UnitTest.cmake.in`.

### Phase 0a: Establish VEHU Docker Baseline

**Purpose**: Run all M-Unit tests against the live VEHU Docker container to establish which tests pass in the original MUMPS environment. Any failures here set our **expected failure baseline** — we don't need the transpiled Python to do better than the original.

**Approach**:
1. Start the WorldVistA VEHU Docker container (`worldvista/vehu`)
2. Import M-Unit test routines from `VistA/Packages/*/Testing/MUnit/*.m` into the VEHU instance using `vehuprog` programmer mode
3. Execute test routines via `D ^ZZRGUT`, `D EN^%ut("DMUDT000")`, etc. and capture output
4. Parse M-Unit output to extract per-test pass/fail results
5. Store baseline results as JSON fixtures for comparison

**Implementation** — `utils/run_munit_vehu.py`:
```python
"""Run M-Unit tests against VEHU Docker container via SSH programmer mode.

Usage:
    uv run python utils/run_munit_vehu.py                     # Run all
    uv run python utils/run_munit_vehu.py --package "VA FileMan"  # One package
    uv run python utils/run_munit_vehu.py --routine DMUDT000  # One routine
    uv run python utils/run_munit_vehu.py --save-baseline     # Save results as JSON
"""
```

The script will:
1. Connect to VEHU via SSH (`vehuprog` / `prog`) to get MUMPS direct mode
2. Import test routine `.m` files using `%RI` (routine import) or ZWR load
3. Execute each TestList command (e.g., `D ^ZZRGUT`, `D EN^%ut("DMUDT000")`)
4. Parse output for pass/fail counts and individual failure messages
5. Output structured results as JSON

**Baseline output format** — `tests/vista/baselines/vehu_munit_baseline.json`:
```json
{
  "timestamp": "2026-02-19T...",
  "vehu_image": "worldvista/vehu:latest",
  "packages": {
    "VA FileMan": {
      "routines": {
        "DMUDT000": {"tests": 58, "failures": 0, "errors": 0, "status": "pass"},
        "DMUDIC00": {"tests": 16, "failures": 0, "errors": 0, "status": "pass"},
        "DMUDTC00": {"tests": 92, "failures": 2, "errors": 0, "status": "fail",
          "failures_detail": [
            {"entry": "%DTFUT^DMUDT000", "message": "Future Date Test Full Failed."}
          ]
        }
      }
    }
  },
  "summary": {"total_tests": 1186, "total_pass": 1180, "total_fail": 6, "total_error": 0}
}
```

### Phase 0b: M-Unit pytest Adapter for Transpiled Code

**Purpose**: Build a pytest adapter that transpiles M-Unit test routines and their dependencies, then runs them as native Python tests — comparing results against the VEHU baseline.

**Architecture**:

```
┌─────────────────────────────────────────────────────────────────┐
│  M-Unit Test Discovery (pytest)                                 │
│  ──────────────────────────────                                 │
│  1. Scan VistA/Packages/*/Testing/MUnit/TestList files          │
│  2. For each TestList entry (e.g., "D ^ZZRGUT"):               │
│     a. Transpile routine + all dependencies via m2py            │
│     b. Discover @TEST tags and XTENT entries in source          │
│     c. Generate pytest test items for each test entry point     │
│  3. Run transpiled tests with m2py runtime                      │
│                                                                 │
│  MUMPS:  D CHKEQ^%ut(expected,actual,msg)                       │
│  Python: %ut.CHKEQ(expected, actual, msg)  # transpiled         │
│          → internally increments counters / records failures    │
│                                                                 │
│  After each routine completes, check %ut failure/error counts   │
│  against the VEHU baseline to determine pass/fail               │
└─────────────────────────────────────────────────────────────────┘
```

**Two complementary test execution strategies**:

#### Strategy A: Transpile and Run M-Unit Natively (Primary)

The M-Unit framework (`%ut`, `%ut1`) transpiles to Python alongside the test routines. The transpiled tests call transpiled `CHKEQ`, `CHKTF`, etc. — using the same assertion logic as the original MUMPS. m2py runs the transpiled routine and captures the M-Unit summary output.

```python
# tests/vista/test_munit.py — pytest adapter

import pytest
from m2py import transpile_routine, execute_transpiled
from tests.vista.baselines import load_baseline

MUNIT_PACKAGES = [
    ("VA FileMan", ["ZZUTDIDT", "DMUDIC00", "DMUDT000", "DMUDTC00", "DMUDIQ00"]),
    ("Problem List", ["ZZRGUT", "ZZRGUT1", "ZZRGUT2", "ZZRGUT3", "ZZRGUT4", "ZZRGUT5", "ZZRGUTRB", "ZZRGUTEX"]),
    ("Scheduling", ["ZZRGUSD1", "ZZRGUSD2", "ZZRGUSD3", "ZZRGUSD4", "ZZRGUSD5", "ZZRGUSD6",
                     "ZZUTGETAPPT", "ZZUTNEXTAPPT", "ZZUTSDAPI", "ZZUTSDIMO", "ZZUTGETPLIST", "ZZUTPATAPPT"]),
    ("Registration", ["ZZDGPTCO1"]),
    ("M XML Parser", ["MXMLDOMT", "MXMLBLD", "MXMLPATT", "MXMLTMPT"]),
]

baseline = load_baseline("tests/vista/baselines/vehu_munit_baseline.json")

@pytest.mark.parametrize("package,routine", [
    (pkg, rtn) for pkg, rtns in MUNIT_PACKAGES for rtn in rtns
])
def test_munit_routine(package, routine, vista_runtime):
    """Run a transpiled M-Unit test routine and compare against VEHU baseline."""
    # Skip if test fails on VEHU too (expected failure)
    vehu_result = baseline.get(package, routine)
    if vehu_result and vehu_result["status"] == "fail":
        pytest.xfail(f"Also fails on VEHU: {vehu_result['failures_detail']}")

    # Transpile and execute the test routine
    result = vista_runtime.run_munit(routine)

    # Compare results
    assert result.errors == 0, f"Errors in {routine}: {result.error_messages}"
    assert result.failures == 0, f"Failures in {routine}: {result.failure_messages}"
```

#### Strategy B: Parse @TEST Tags into Individual pytest Items (Advanced)

For finer-grained reporting, parse M-Unit test routines at the source level to discover individual `@TEST`-tagged entry points, then run each as a separate pytest test item:

```python
# tests/vista/conftest.py — pytest plugin for M-Unit collection

def pytest_collect_file(parent, file_path):
    """Collect .m files as M-Unit test modules."""
    if file_path.suffix == ".m" and file_path.parent.name == "MUnit":
        return MUnitFile.from_parent(parent, path=file_path)

class MUnitFile(pytest.File):
    def collect(self):
        """Parse @TEST tags from the MUMPS source."""
        source = self.path.read_text()
        for tag, name in parse_test_tags(source):
            yield MUnitItem.from_parent(self, name=f"{tag} - {name}", tag=tag)

class MUnitItem(pytest.Item):
    def __init__(self, *, tag, **kwargs):
        super().__init__(**kwargs)
        self.tag = tag

    def runtest(self):
        """Transpile and call a single M-Unit test entry point."""
        routine = self.path.stem
        result = self.config.vista_runtime.run_munit_tag(routine, self.tag)
        if result.failures > 0:
            raise MUnitFailure(result.failure_messages)

    def repr_failure(self, excinfo):
        return f"M-Unit assertion failed: {excinfo.value}"
```

This would produce pytest output like:
```
tests/vista/munit/VA FileMan/DMUDT000.m::DTFUT - %DT Future Assumed Flag PASSED
tests/vista/munit/VA FileMan/DMUDT000.m::DTPAST - %DT="P" - Past assumed flag PASSED
tests/vista/munit/VA FileMan/DMUDT000.m::DTI - Internationl Dates PASSED
tests/vista/munit/VA FileMan/DMUDIC00.m::FINDC - FIND^DIC with computed fields PASSED
```

### Infrastructure Requirements

| Component | Description | Status |
|-----------|-------------|--------|
| **M-Unit framework transpilation** | Transpile `%ut`, `%ut1` to Python | ✅ %ut routines are in VistA-VEHU-M and transpile at 100% |
| **Test routine transpilation** | Transpile 58 test routines from VistA repo | ⬜ Need to verify (all VistA-VEHU-M routines transpile at 99.99%) |
| **Dependency resolution** | Transpile all dependencies (FileMan, Problem List API, etc.) | ✅ All packages transpile at 100% |
| **Global state bootstrap** | Load FileMan data dictionaries (`^DD`), test files, patient data | ⬜ Required for FileMan/Problem List/Scheduling tests |
| **VEHU Docker baseline runner** | `utils/run_munit_vehu.py` + SSH-based test execution | ⬜ To build |
| **pytest M-Unit adapter** | `tests/vista/test_munit.py` or conftest plugin | ⬜ To build |
| **M-Unit output parser** | Parse summary lines and failure details from M-Unit output | ⬜ To build |

### Global State Requirements

Unlike the original Phase 0 (XLF pure functions), M-Unit tests require pre-populated global state:

| Test Package | Required Globals | Source |
|-------------|-----------------|--------|
| VA FileMan | `^DD` (data dictionary), test files 1009.801/1009.802 (created by `DMUFINIT`) | Bootstrap from VEHU + test STARTUP routines |
| Problem List | `^AUPNPROB`, `^DPT` (patient), `^VA(200,...)` (user), clinic data | Bootstrap from VEHU |
| Scheduling | `^SC` (clinic), `^DPT` (patient), appointment data | Bootstrap from VEHU |
| Registration | `^DPT` (patient demographics) | Bootstrap from VEHU |
| M XML Parser | `^TMP($J)` for temporary XML storage | Created dynamically in tests |

**Bootstrap approach**: Export globals from the VEHU Docker container using `%GO` (global output) in ZWR format, then import into the m2py global store. This gives the transpiled tests the same data environment as the VEHU baseline.

### Validation Gate

Phase 0 is complete when:
- **0a**: VEHU Docker baseline captured — all 58 test routines run, results stored as JSON
- **0b**: pytest adapter operational — `uv run pytest tests/vista/test_munit.py` discovers and runs transpiled M-Unit tests
- **0b**: All tests that **pass on VEHU** also **pass in transpiled Python** (failures on VEHU are expected failures in Python via `pytest.xfail`)
- The M-Unit framework itself (`%utt1`-`%utt7`) passes its own self-test suite when transpiled

### Implementation Order

1. **Build VEHU baseline runner** (`utils/run_munit_vehu.py`)
   - SSH into VEHU programmer mode
   - Import test routines from `VistA/Packages/*/Testing/MUnit/*.m`
   - Execute TestList commands, parse output
   - Save baseline JSON

2. **Build global state bootstrap** (`utils/bootstrap_globals.py`)
   - Export required globals from VEHU via `%GO`
   - Import into m2py's SQLite global store
   - Verify `^DD`, `^DPT`, `^VA(200)` are accessible

3. **Build pytest M-Unit adapter** (`tests/vista/test_munit.py` + `tests/vista/conftest.py`)
   - Transpile M-Unit framework + test routines
   - Execute tests in m2py runtime
   - Compare against baseline

4. **Start with M-Unit self-tests** (`%utt1`-`%utt7`)
   - Simplest tests — verify the framework itself works when transpiled
   - No external data dependencies beyond `^TMP`

5. **Expand to M XML Parser** (4 routines, minimal data dependencies)
   - Tests create their own data via `^TMP($J)`

6. **Expand to VA FileMan** (30 routines, requires `^DD` bootstrap)
   - `DMUFINIT` creates test files — must transpile correctly

7. **Expand to Problem List + Scheduling + Registration** (22 routines, requires full patient/clinic data)

---

## Phase 1: RPC Example Routines (XWBZ1, XWBEXMPL)

**Goal**: Validate RPC-style entry points that return structured data, proving the RPC test harness works.

**Why this phase**: These routines are:
- **Zero external dependencies** — XWBZ1 has none; XWBEXMPL has one optional (FILE^DID)
- **Designed for testing** — Created as RPC Broker example/demo routines
- **Representative** — Cover common RPC patterns: single value, array, global array returns
- **Foundation for RPC strategy** — Once validated, the same approach works for all 4,485 RPCs

### Target: XWBZ1 + XWBEXMPL — 12 registered RPCs

| RPC Name | TAG^ROUTINE | Return Type | Complexity |
|----------|-------------|-------------|------------|
| XWB EGCHO STRING | ECHO1^XWBZ1 | Single value | Trivial: echo input |
| XWB EGCHO LIST | LIST^XWBZ1 | Array | Simple: generate 28-item list |
| XWB EGCHO BIG LIST | BIG^XWBZ1 | Global array | Moderate: 32K via ^TMP |
| XWB EGCHO SORT LIST | SRT^XWBZ1 | Array | Moderate: sort with direction |
| XWB EGCHO MEMO | MEMO^XWBZ1 | Global array | Moderate: accept/return text |
| XWB EXAMPLE ECHO STRING | ECHOSTR^XWBEXMPL | Single value | Trivial: echo |
| XWB EXAMPLE GET LIST | GETLIST^XWBEXMPL | Global array | Moderate: lines/KB |
| XWB EXAMPLE SORT NUMBERS | SORTNUM^XWBEXMPL | Array | Moderate: sort HI/LO |
| XWB EXAMPLE GLOBAL SORT | GSORT^XWBEXMPL | Global array | Moderate: indirection |
| XWB EXAMPLE BIG TEXT | BIGTXT^XWBEXMPL | Single value | Simple: count chars/lines |

**Testing Strategy**: Can use either Strategy 1 (Direct) or Strategy 2 (RPC)

**Test Approach (Direct — initial)**:
1. Create MUMPS harness that calls RPC entry points directly with mock RESULT array
2. Compare YDB vs m2py output for each entry point
3. Validates: basic SET, QUIT w/value, FOR loops, $ORDER, $NAME, global refs, indirection (@)

**Test Approach (RPC — once broker is available)**:
1. Use vista-test `VistABroker` to call each RPC against YottaDB VistA
2. Call same RPC against m2py RPC server
3. Compare structured responses

**Roll-and-Scroll**: None — these are RPC-only routines.

---

## Phase 2: Build RPC Server Infrastructure

**Goal**: Build the Python-native infrastructure required for Strategy 2 (RPC testing). This is a **build phase**, not a validation phase — it produces the tools that subsequent phases depend on.

**Why this is a prerequisite**: The VistA RPC Broker server (XWBTCPL) uses GT.M-specific TCP server primitives that cannot be replicated via transpilation alone. Rather than implementing the full GT.M socket device model, we build a Python-native RPC server that speaks the same protocol.

### What the original RPC Broker does (XWBTCPL → XWBTCPC → XWBBRK)

1. Opens a server socket with `OPEN dev:(ZLISTEN=port:TCP)::"SOCKET"`
2. Listens with `W /LISTEN(backlog)`
3. Accepts connections with `W /WAIT(timeout)`, reading `$KEY` for `"CONNECT|handle|ip"`
4. Forks a child process via `JOB EN^XWBTCPC(args)` for each connection
5. Child dispatches RPCs by looking up `^XWB(8994,"B",rpcname)` and executing `D @(TAG_"^"_ROUTINE)`
6. RPC code runs with `$IO` set to a NULL device (suppressing stray output)

### m2py runtime gap analysis

| Requirement | Status | Gap |
|-------------|--------|-----|
| TCP client (`OPEN "host:port":(CONNECT)`) | ✅ Supported | — |
| TCP server (`ZLISTEN`, `/LISTEN`, `/WAIT`) | ❌ Missing | No server-mode socket device |
| Multi-socket device (`SOCKET=handle` on USE/CLOSE) | ❌ Missing | TCPDevice wraps single socket |
| `$KEY` for connection events | ❌ Missing | Only set on READ termination |
| JOB (fork child process) | ✅ Supported | `subprocess.Popen` via `job_runner.py` |
| LOCK +/- (semaphore) | ✅ Supported | SQLiteGlobalStorage cross-process locks |
| NULL device (suppress output) | ❌ Missing | No `/dev/null` device type |
| `^%ZOSF` / `^%ZIS` globals | ❌ Not loaded | Must be populated from VistA instance |
| Indirection (`D @computed_ref`) | ✅ Supported | `IndirectionResolver` |
| `$ZINTERRUPT` | ⚠️ Partial | ISV stored but no signal handler |

### Build deliverables

```
┌─────────────────────────────────────────────────────────┐
│  Python-native RPC Server (new m2py component)          │
│  ─────────────────────────────────────────────          │
│  • TCP listener (Python asyncio or threading)           │
│  • RPC protocol parser ({XWB} framing)                  │
│  • Lookup ^XWB(8994,"B",name) → tag^routine             │
│  • Call into transpiled routine code                    │
│  • Return formatted RPC response                        │
│                                                         │
│  Transpiled VistA code handles the business logic:      │
│  • ECHO1^XWBZ1, VALIDAV^XUSRB, etc.                   │
│  • Reads/writes globals (^VA, ^TMP, ^XWB, etc.)         │
│  • Uses m2py runtime for everything except TCP serving  │
└─────────────────────────────────────────────────────────┘
```

1. **Global bootstrap utility** — Import globals from a YDB VistA instance into m2py's global store:
   - `^XWB(8994,...)` — RPC registry (names, tags, routines, return types)
   - `^VA(200,...)` — User records (for authentication in Phase 4)
   - `^%ZOSF(...)` — OS function mappings
   - `^DIC(19,...)` — Option definitions (for RPC context checking)
2. **NULL device** — `NullDevice(MUMPSDevice)` that discards all writes (trivial — RPCs execute with `$IO` pointing here to suppress stray output)
3. **RPC protocol server** — Python TCP server that:
   - Accepts `{XWB}` framed connections
   - Parses RPC name and parameters from the protocol message
   - Looks up tag^routine in `^XWB(8994,"B",name)`
   - Executes the transpiled routine via `D @(TAG_"^"_ROUTINE)` (indirection)
   - Returns RPC response over TCP
4. **RPC catalog** — Parse `^XWB(8994)` to generate a complete RPC→tag^routine mapping for test generation

### Validation gate

Phase 2 is complete when:
- vista-test `VistABroker` can connect to the m2py RPC server
- `XWB EGCHO STRING` RPC returns identical results from YDB and m2py
- All 12 Phase 1 example RPCs pass via the RPC server (Strategy 2 re-test)

---

## Phase 3: RPC Broker Validation (XWB*)

**Goal**: Validate the RPC Broker server-side dispatch mechanism using the RPC server built in Phase 2. This is the gateway for all GUI client communication.

**Prerequisite**: Phase 2 (RPC server infrastructure) must be complete.

### Target: 40 routines — all transpile (100%)

| Component | Key Routines | Purpose |
|-----------|-------------|---------|
| RPC Dispatch | XWBRPC, XWBBRK, XWBBRK2 | Parse request, lookup RPC, execute |
| TCP/IP Listener | XWBTCP, XWBTCPC, XWBTCPL, XWBTCPM* | Connection handling |
| Security | XWBSEC | Context option checking |
| Library | XWBLIB | GET VARIABLE VALUE, IS RPC AVAILABLE |
| Examples | XWBZ1, XWBEXMPL, XWBFM | Demo/test RPCs |
| M2M (Server-to-Server) | XWBM2M*, XWBRPC | Machine-to-machine broker |

**Key RPCs** (called during every CPRS session):
- `XWB CREATE CONTEXT` → CRCONTXT^XWBSEC — Context/option access check
- `XWB GET VARIABLE VALUE` → VARVAL^XWBLIB — Read server-side variable
- `XWB IM HERE` → IMHERE^XWBLIB — Keep-alive
- `XWB IS RPC AVAILABLE` → CKRPC^XWBLIB — Check RPC access
- `XWB ARE RPCS AVAILABLE` → CKRPCS^XWBLIB — Bulk check

**Testing Strategy**: RPC (Strategy 2) + Direct (Strategy 1)

**Test Approach**:
1. Use vista-test `VistABroker` to call each XWB RPC against YottaDB VistA
2. Call same RPC against m2py RPC server
3. Compare structured responses
4. XWBFM provides FileMan integration that can also be tested via terminal (Strategy 3)

---

## Phase 4: Kernel Sign-On / Authentication (XUS*)

**Goal**: Validate the authentication flow. This is exercised at the start of every CPRS session.

**Prerequisite**: Phase 2 (RPC server, global bootstrap for `^VA(200)`) must be complete.

### Target: ~83 XUS* routines

| Component | Key Routines | RPCs |
|-----------|-------------|------|
| Sign-On | XUSRB, XUSRB1, XUSRB2, XUSRB4 | XUS SIGNON SETUP, XUS AV CODE, XUS GET USER INFO |
| Verify Code | XUS, XUS1, XUS1A, XUS1B, XUS2, XUS3 | XUS CVC |
| Division | XUSRB2 | XUS DIVISION GET/SET |
| SSO/STS | XUSBSE1, XUESSO3, XUESSO4 | XUS BSE TOKEN, XUS ESSO VALIDATE |
| Keys | XUSRB | XUS KEY CHECK, XUS ALLKEYS |
| Intro | XUSRB | XUS INTRO MSG |

**Key RPCs** (CPRS sign-on sequence):
1. `XUS SIGNON SETUP` → SETUP^XUSRB — Initialize session
2. `XUS AV CODE` → VALIDAV^XUSRB — Validate access/verify codes
3. `XUS GET USER INFO` → USERINFO^XUSRB2 — Return user meta (DUZ, name, division)
4. `XUS DIVISION GET` → DIVGET^XUSRB2 — Get user divisions
5. `XUS DIVISION SET` → DIVSET^XUSRB2 — Set active division
6. `XUS INTRO MSG` → INTRO^XUSRB — Return intro text
7. `XUS KEY CHECK` → OWNSKEY^XUSRB — Check security key
8. `XWB CREATE CONTEXT` → CRCONTXT^XWBSEC — Verify app context

**Dependencies**: FileMan (^VA(200) user file), ^DIC, ^XUSEC security globals.

**Testing Strategy**: RPC (Strategy 2)

**Test Approach**:
1. Pre-populate ^VA(200) with test user records in both YDB and m2py global store
2. Use vista-test `VistABroker` to execute sign-on sequence against both systems:
   - SETUP → AV CODE → GET USER INFO → DIVISION GET/SET
3. Compare all RPC responses between YDB and m2py

**Roll-and-Scroll**: Terminal sign-on uses XUS routines reading from $PRINCIPAL — can be tested with Strategy 3 once terminal server exists (Phase 5).

---

## Phase 5: Build Terminal Server Infrastructure

**Goal**: Build the Python-native infrastructure required for Strategy 3 (terminal testing). Like Phase 2, this is a **build phase** that produces tools for subsequent phases.

**Why this is a prerequisite**: VistA's roll-and-scroll interface depends on terminal capability variables, device configuration globals, and Kernel I/O utilities that go beyond what transpiled code alone provides. FileMan (Phase 6), List Manager (Phase 7), and clinical applications (Phases 8-9) all need this infrastructure.

### What a VistA terminal session requires

1. A terminal connection (`$PRINCIPAL` bound to a PTY or socket)
2. Kernel device setup (`D ^%ZIS`) populating IO variables: `IOM` (width), `IOSL` (page length), `IOF` (form feed), `IOXY` (cursor positioning code), `IOST` (terminal type)
3. Terminal escape sequences loaded from `^%ZIS(2,...)`: `IORVON`, `IOINHI`, `IOUON`, `IOELEOL`, `IOSTBM`, etc. (~20+ variables)
4. Menu system globals: `^DIC(19,...)` (options), `^ORD(101,...)` (protocols), `^XUTL("XQ",$J,...)` (session state)
5. USE device parameters: `NOCENABLE`, `NOESCAPE`, `WIDTH=n`, `NOWRAP`

### m2py runtime gap analysis

| Requirement | Status | Gap |
|-------------|--------|-----|
| `PrincipalDevice` (stdin/stdout) | ✅ Supported | — |
| `$X`/`$Y` tracking | ✅ Supported | — |
| `SET $X=n` | ✅ Supported | — |
| `SET $Y=n` | ❌ Missing | No `set_y()` method |
| `READ *X` (single char) | ✅ Supported | — |
| `READ *X:timeout` (single char + timeout) | ⚠️ Partial | `read_char()` has no timeout param |
| `W !`, `W #`, `W ?n`, `W $C(n)` | ✅ Supported | — |
| `USE $P:(NOCENABLE:NOESCAPE)` | ❌ Missing | USE params ignored |
| IOM/IOSL/IOF/IOBS/IOXY variables | ❌ Not populated | Set by `D ^%ZIS` from globals |
| Terminal escape sequence vars | ❌ Not populated | Loaded from `^%ZIS(2,...)` |
| `^%ZOSF("XY")` cursor positioning | ❌ Not loaded | XECUTEd for cursor movement |
| `^%ZIS(1/2,...)` device/terminal globals | ❌ Not loaded | Must be populated |
| `^DIC(19,...)` menu options | ❌ Not loaded | Must be populated |
| `^ORD(101,...)` protocols | ❌ Not loaded | Must be populated |

### Build deliverables

```
┌─────────────────────────────────────────────────────────┐
│  Python-native Terminal Server (new m2py component)     │
│  ──────────────────────────────────────────────         │
│  • PTY or socket-based terminal (Python pty module)     │
│  • PrincipalDevice bound to terminal I/O                │
│  • Bootstrap IO variables (IOM=80, IOSL=24, IOXY=...)   │
│  • Populate ^%ZIS(2,...) with VT100 escape sequences    │
│                                                         │
│  Transpiled VistA code handles the UI logic:            │
│  • XQ* menu system, VALM* List Manager                  │
│  • ^DIR prompting, ^DIC lookup, ^DIE editing           │
│  • Reads/writes via $PRINCIPAL (PrincipalDevice)        │
│  • Cursor positioning via X IOXY (transpiled XECUTE)    │
└─────────────────────────────────────────────────────────┘
```

1. **Runtime extensions**:
   - `set_y()` on `PrincipalDevice` — complement to existing `set_x()` (trivial)
   - `read_char(timeout=)` — extend single-char read with timeout parameter
   - USE parameter handling — parse NOCENABLE, NOESCAPE, WIDTH, NOWRAP
2. **Terminal global bootstrap** — Extend the Phase 2 global bootstrap to also import:
   - `^%ZIS(1,...)` — Device definitions
   - `^%ZIS(2,...)` — Terminal type capabilities (escape sequences)
   - `^ORD(101,...)` — Protocol file (List Manager action protocols)
3. **Terminal server harness** — Binds `PrincipalDevice` to a PTY/socket instead of bare stdin/stdout
4. **IO variable bootstrap** — Set `IOM=80`, `IOSL=24`, `IOF="#"`, `IOST="C-VT100"`, and load terminal escape sequences (`IORVON`, `IOINHI`, etc.) from `^%ZIS(2,...)`

### Validation gate

Phase 5 is complete when:
- vista-test `VistATerminal` can connect to the m2py terminal server
- A simple `D ^DIR` prompt reads input and validates it correctly
- Screen output from a basic menu invocation matches between YDB and m2py (normalized)

---

## Phase 6: VA FileMan Core (DI/DD/DIC/DIR)

**Goal**: Validate the foundational data access layer. Nearly every VistA package depends on FileMan.

**Prerequisites**: Phase 2 (global bootstrap), Phase 5 (terminal server for interactive FileMan).

### Target: ~861 routines (large scope — subdivide)

**Suggested sub-phases**:

| Sub-Phase | Component | Key Routines | Purpose |
|-----------|-----------|-------------|---------|
| 6a | DIR (Read) | DIR, DIR0, DIR1, DIR2 | User input with validation |
| 6b | DIC (Lookup) | DIC, DIC0, DIC1, DIC11, DICN | File/record lookup |
| 6c | DIQ (Data Extract) | DIQ, DIQ1, GET1^DIQ | Read field values |
| 6d | DIE (Edit) | DIE, DIE0, DIE1 | Create/edit records |
| 6e | DDIOL (Output) | DDIOL | Standard output utility |
| 6f | DILFD (Field Defs) | DILFD | Data dictionary access |
| 6g | DIP (Print) | DIP, DIP0 | Report printing |

**RPC Interface**: FileMan is primarily roll-and-scroll, but many RPCs call FileMan internally:
- `GET1^DIQ(file,ien,field)` — Single field read (used everywhere)
- `$$FIND1^DIC(file,...)` — Single record lookup
- `D ^DIC` — Interactive lookup
- `D ^DIE` — Interactive edit
- `D ^DIR` — Interactive read/prompt

**Testing Strategy**: Direct (Strategy 1) + Terminal (Strategy 3)

**Test Approach**:
1. **Direct (DIQ/DIC utilities)**: Create harness calling `$$GET1^DIQ(file,ien,field)`, compare YDB vs m2py
2. **Terminal (interactive)**: Use vista-test `VistATerminal` to drive ^DIC, ^DIE, ^DIR prompts
3. Build a test FileMan database with known file structures
4. This is a major milestone — once FileMan works, most package tests become feasible

---

## Phase 7: List Manager (VALM*)

**Goal**: Validate the scrolling list interface framework. Many clinical screens use List Manager.

**Prerequisites**: Phase 5 (terminal server), Phase 6 (FileMan — protocols in file 101).

### Target: 48 routines — all transpile (100%)

**Key Routines**: VALM, VALM1, VALM10, VALM2, VALMEVNT

**Testing Strategy**: Terminal (Strategy 3)

**Test Approach**:
1. Use vista-test `VistATerminal` to drive list interactions
2. Build/display test lists, compare screen output
3. Navigation commands (+, -, page up/down)
4. Item selection and action protocol execution
5. Compare normalized screen output between YDB and m2py

**Dependencies**: Kernel menu system (XQ*), FileMan (protocols in file 101).

---

## Phase 8: Clinical Applications Tier 1

**Prerequisites**: Phase 2 (RPC server), Phase 5 (terminal server), Phase 6 (FileMan), Phase 7 (List Manager).

### 8a: Problem List (GMPL) — 94 routines, all transpile (100%)

**Namespace**: GMPL*

**External Dependencies**: XLFSTR, XLFDT (Kernel Library — Phase 0), ICDEX/ICDXCODE (ICD coding), VALM (List Manager — Phase 7), DIE/DIC/DICN (FileMan — Phase 6), Lexicon (LEX).

**Testing Strategy**: RPC (Strategy 2) + Terminal (Strategy 3)

**Test Approach**:
1. **RPC**: Use vista-test `VistABroker` to call ORWPL/ORQQPL RPCs, compare responses
2. **Terminal**: Use vista-test `VistATerminal` to drive roll-and-scroll problem list screens
3. Pre-populate ^AUPNPROB (problem file) with test records
4. GMPLUTL* provides utility functions testable via Strategy 1 (Direct)

**RPC Interface**: Problem List RPCs are registered under CPRS in the `OR CPRS GUI CHART` context. Key RPCs live in ORWPL/ORQQPL routines (Order Entry package), which call back into GMPL routines:
- Problem list display → GMPLDISP, GMPLDIS1
- Problem add/edit → GMPLINTR, GMPLEDIT, GMPLEDT*
- Problem save → GMPLSAVE
- Problem utilities → GMPLUTL*

**Roll-and-Scroll Interface**: Full roll-and-scroll problem list management via List Manager:
- GMPLMENU — Problem selection sub-list
- GMPLMGR* — Problem list manager screens
- GMPLDISP — Display formatting

### 8b: Text Integration Utilities / TIU — 548 routines

**Namespace**: TIU*

**RPC Interface**: 97 registered TIU RPCs. Key ones:
- `TIU CREATE RECORD` → MAKE^TIUSRVP
- `TIU UPDATE RECORD` → UPDATE^TIUSRVP
- `TIU GET RECORD TEXT` → TGET^TIUSRVR1
- `TIU DOCUMENTS BY CONTEXT` → CONTEXT^TIUSRVLO
- `TIU SIGN RECORD` → SIGN^TIUSRVP
- `TIU AUTHORIZATION` → CANDO^TIUSRVA

**Roll-and-Scroll**: Document entry/editing via List Manager screens.

**Testing Strategy**: RPC (Strategy 2) + Terminal (Strategy 3)

**Test Approach**:
1. **RPC**: Use vista-test `VistABroker` for document CRUD operations
2. **Terminal**: Use vista-test `VistATerminal` for document entry screens
3. TIU configuration heavily uses FileMan — Phase 6 prerequisite

### 8c: Health Summary (GMTS) — 294 routines, all transpile (100%)

**Namespace**: GMTS*

**All clinical packages now at 100% transpilation.** Good candidate for parallel development.

**RPC Interface**: Via ORWRP* routines in Order Entry. Health summaries generate formatted text reports.

**Roll-and-Scroll**: Health summary type management and display.

**Testing Strategy**: RPC (Strategy 2) + Terminal (Strategy 3)

**Test Approach**:
1. **RPC**: Use vista-test `VistABroker` to request health summaries
2. **Terminal**: Use vista-test `VistATerminal` to navigate summary screens
3. Compare formatted report output between YDB and m2py
4. Health summary generation depends on GMTS utility functions (testable via Strategy 1)

---

## Phase 9: Clinical Applications Tier 2

- Consult Request Tracking (GMRC*, 225 routines, 100%)
- Virtual Patient Record (VPR*, 104 routines, 100%)
- Clinical Reminders (PXRM*, 519 routines, 100%)
- Scheduling (SD*, 1797 routines, 100%)
- Registration (DG*, 2179 routines, 100%)

All packages now transpile at 100%. These depend on all lower layers and have complex FileMan data models — runtime testing is the focus.

---

## Test Organization Strategy

### Directory Structure

Tests are organized by VistA package namespace, matching the long-term vision from the start. Cross-package integration tests live in `by_workflow/`. Phase ordering (see above) guides *which* packages to test first, not how to organize the files.

```
tests/
├── functional/           # Existing m2py functional tests
├── vista/                # VistA-VEHU validation tests
│   ├── conftest.py       # Shared fixtures: transpile helper, YDB runner, etc.
│   ├── baselines/        # VEHU Docker baseline results (Phase 0a)
│   │   └── vehu_munit_baseline.json  # M-Unit test results from VEHU
│   ├── munit/            # OSEHRA M-Unit tests via pytest (Phase 0b)
│   │   ├── conftest.py       # M-Unit pytest adapter (discovery + execution)
│   │   ├── test_munit.py     # Parametrized test runner for all M-Unit routines
│   │   └── test_munit_self.py # M-Unit framework self-tests (%utt1-%utt7)
│   ├── by_package/       # One directory per VistA namespace prefix
│   │   ├── xlf/                  # Kernel Library Functions
│   │   │   ├── test_xlfstr.py        # UP, LOW, STRIP, REPLACE, etc.
│   │   │   ├── test_xlfdt.py         # NOW, FMTE, HTFM, DT, etc.
│   │   │   ├── test_xlfcrc.py        # CRC32, CRC16
│   │   │   ├── test_xlfmth.py        # ABS, SQRT, PWR, etc.
│   │   │   ├── test_xlfjson.py       # ENCODE, DECODE
│   │   │   └── test_xlfname.py       # Name formatting
│   │   ├── xwb/                  # RPC Broker (Phases 1, 3)
│   │   │   ├── test_xwbz1.py         # ECHO1, LIST, BIG, SRT, MEMO
│   │   │   ├── test_xwbexmpl.py      # ECHOSTR, GETLIST, SORTNUM, etc.
│   │   │   ├── test_xwblib.py        # GET VARIABLE VALUE, etc.
│   │   │   ├── test_xwbsec.py        # CREATE CONTEXT
│   │   │   └── test_xwb_dispatch.py  # RPC lookup and execution
│   │   ├── xu/                   # Kernel / Authentication (Phase 4)
│   │   │   ├── test_xus_validate.py     # AV CODE validation
│   │   │   └── test_xus_userinfo.py     # GET USER INFO
│   │   ├── di/                   # VA FileMan (Phase 6)
│   │   │   ├── test_dir.py           # DIR reader
│   │   │   ├── test_dic.py           # DIC lookup
│   │   │   ├── test_diq.py           # DIQ extract
│   │   │   ├── test_die.py           # DIE edit
│   │   │   └── test_ddiol.py         # DDIOL output
│   │   ├── valm/                 # List Manager (Phase 7)
│   │   │   └── test_valm.py          # List Manager framework
│   │   ├── gmpl/                 # Problem List (Phase 8)
│   │   │   ├── test_gmpl_display.py
│   │   │   ├── test_gmpl_add.py
│   │   │   └── test_gmpl_utils.py
│   │   ├── tiu/                  # Text Integration (Phase 8)
│   │   │   ├── test_tiu_create.py
│   │   │   └── test_tiu_display.py
│   │   ├── gmts/                 # Health Summary (Phase 8)
│   │   │   └── test_gmts.py
│   │   ├── gmrc/                 # Consults (Phase 9)
│   │   ├── vpr/                  # Virtual Patient Record (Phase 9)
│   │   ├── sd/                   # Scheduling (Phase 9)
│   │   ├── dg/                   # Registration (Phase 9)
│   │   └── ...                   # ~175 total namespaces
│   ├── by_workflow/          # Cross-package integration tests
│   │   ├── test_cprs_signon.py       # Full CPRS sign-on sequence
│   │   ├── test_patient_lookup.py    # Patient search/selection
│   │   ├── test_note_creation.py     # Create/sign TIU note
│   │   ├── test_problem_management.py # Add/edit/close problems
│   │   ├── test_order_entry.py       # Place lab/rad/med orders
│   │   └── test_consult_request.py   # Create/complete consult
│   ├── rpc_catalog/          # Auto-generated RPC test stubs
│   │   └── test_all_rpcs.py  # Parametrized test for all 4,485 RPCs
│   └── transpilation/        # Transpilation success tracking
│       └── test_transpile_all.py  # Ensure all routines transpile
```

### Test Fixture Pattern

Each test module follows this pattern:

```python
"""Tests for XWBZ1 - RPC Broker Example Routines."""
import pytest
from tests.vista.conftest import transpile_routine, run_rpc_ydb, run_rpc_python

pytestmark = [pytest.mark.xwb, pytest.mark.rpc]

class TestXWBZ1Echo:
    """XWB ECHO STRING - echo a string value."""
    
    def test_echo_simple(self, xwbz1_module):
        """ECHO1^XWBZ1 returns input unchanged."""
        result_ydb = run_rpc_ydb("ECHO1", "XWBZ1", params=["Hello World"])
        result_py = run_rpc_python(xwbz1_module, "ECHO1", params=["Hello World"])
        assert result_py == result_ydb
    
    def test_echo_empty(self, xwbz1_module):
        """ECHO1^XWBZ1 handles empty string."""
        result_ydb = run_rpc_ydb("ECHO1", "XWBZ1", params=[""])
        result_py = run_rpc_python(xwbz1_module, "ECHO1", params=[""])
        assert result_py == result_ydb

class TestXWBZ1List:
    """XWB ECHO LIST - return a fixed list."""
    
    def test_list_returns_28_items(self, xwbz1_module):
        """LIST^XWBZ1 creates Y(1..28) array."""
        result_ydb = run_rpc_ydb("LIST", "XWBZ1")
        result_py = run_rpc_python(xwbz1_module, "LIST")
        assert result_py == result_ydb
        assert len(result_py) == 28
```

### Conftest Shared Fixtures

```python
"""Shared fixtures for VistA-VEHU transpilation tests."""
import pytest
from m2py.codegen import generate_python

VISTA_ROUTINES_BASE = "VistA-VEHU-M/Packages"

@pytest.fixture(scope="session")
def transpile_routine():
    """Returns a function that transpiles a VistA routine to Python."""
    def _transpile(package: str, routine: str) -> str:
        path = f"{VISTA_ROUTINES_BASE}/{package}/Routines/{routine}.m"
        with open(path) as f:
            source = f.read()
        return generate_python(source, routine_name=routine)
    return _transpile

def run_rpc_ydb(tag: str, routine: str, params=None) -> dict:
    """Run an RPC entry point via YottaDB and capture RESULT."""
    # Uses utils/run_mumps_ydb.py to execute TAG^ROUTINE with params
    ...

def run_rpc_python(module, tag: str, params=None) -> dict:
    """Run an RPC entry point in transpiled Python and capture RESULT."""
    ...
```

### Marking & Filtering

Marks are semantic — by package namespace and interface type, not by phase number. Phase ordering is a *scheduling* concern (what to work on next), not a test identity.

```python
# By VistA package namespace
@pytest.mark.xlf             # Kernel Library Functions
@pytest.mark.xwb             # RPC Broker
@pytest.mark.xu              # Kernel / Authentication
@pytest.mark.di              # VA FileMan
@pytest.mark.valm            # List Manager
@pytest.mark.gmpl            # Problem List
@pytest.mark.tiu             # Text Integration
@pytest.mark.gmts            # Health Summary
@pytest.mark.gmrc            # Consults
@pytest.mark.vpr             # Virtual Patient Record
@pytest.mark.sd              # Scheduling
@pytest.mark.dg              # Registration

# By interface / testing strategy
@pytest.mark.direct          # Strategy 1: Direct function call testing
@pytest.mark.rpc             # Strategy 2: RPC testing via vista-test
@pytest.mark.terminal        # Strategy 3: Terminal roll-and-scroll testing

# By dependency tier (for CI gating)
@pytest.mark.tier0           # No VistA dependencies (XLF — pure computation)
@pytest.mark.tier1           # Kernel infrastructure (XWB, XU)
@pytest.mark.tier2           # Data layer (FileMan, List Manager)
@pytest.mark.tier3           # Clinical applications (GMPL, TIU, GMTS, etc.)
```

```bash
# Make sure you are in the vista-test directory
cd vista-test

# Run all Kernel Library tests
uv run pytest tests/vista/ -m xlf

# Run all RPC interface tests across packages
uv run pytest tests/vista/ -m rpc

# Run a specific package
uv run pytest tests/vista/ -m gmpl

# Run all tests with no VistA dependencies (fast CI gate)
uv run pytest tests/vista/ -m tier0

# Run everything up through data layer
uv run pytest tests/vista/ -m "tier0 or tier1 or tier2"

# Run by directory (equivalent to package mark)
uv run pytest tests/vista/by_package/xlf/
```

---

## Scaling: Full VistA Coverage

The directory structure above already follows the long-term layout. As new packages are validated, add a directory under `by_package/` matching the VistA namespace prefix. The full target includes ~175 namespaces — some notable ones not yet listed:

```
tests/vista/by_package/
├── or/               # Order Entry / CPRS
├── ps/               # Pharmacy
├── lr/               # Lab
├── ra/               # Radiology
├── pxrm/             # Clinical Reminders
└── ...               # ~175 total namespaces
```

### RPC Catalog Coverage Tracking

The 4,485 registered RPCs can be auto-cataloged from the `^XWB(8994)` global:

```
Format: RPC_NAME^TAG^ROUTINE^RETURN_TYPE^AVAILABILITY
Return types: 1=Single, 2=Array, 3=Word Processing, 4=Global Array
```

A parametrized test can attempt transpilation + basic RPC invocation for each:

```python
@pytest.mark.parametrize("rpc_name,tag,routine", ALL_RPCS)
def test_rpc_transpiles(rpc_name, tag, routine):
    """Each RPC's implementing routine must transpile."""
    code = generate_python(load_routine(routine), routine_name=routine)
    assert code is not None
```

### Success Metrics

| Milestone | Phase | Criteria | Status |
|-----------|-------|----------|--------|
| M-1 | — | All VistA-VEHU-M routines transpile (>99%) | ✅ **COMPLETE** (99.99%) |
| M0a | 0a | VEHU Docker M-Unit baseline captured (58 routines, 1,186 assertions) | ⬜ Pending |
| M0b | 0b | Transpiled M-Unit tests pass in Python (matching VEHU baseline) | ⬜ Pending |
| M1 | 1 | RPC example routines produce identical output via direct calls | ⬜ Pending |
| M2 | 2 | Python-native RPC server accepts connections, dispatches RPCs | ⬜ Pending |
| M3 | 3 | RPC Broker dispatch produces identical responses (XWB RPCs) | ⬜ Pending |
| M4 | 4 | CPRS sign-on sequence completes in Python | ⬜ Pending |
| M5 | 5 | Python-native terminal server drives ^DIR prompt correctly | ⬜ Pending |
| M6 | 6 | FileMan DIQ/DIC/DIR produce correct results | ⬜ Pending |
| M7 | 7 | List Manager displays and navigates correctly | ⬜ Pending |
| M8 | 8 | Clinical apps (Problem List, TIU, Health Summary) work | ⬜ Pending |
| M9 | 9 | Full CPRS chart review session works end-to-end | ⬜ Pending |
| M10 | — | All 4,485 RPCs transpile; core workflows pass | 🔄 Transpilation complete, runtime pending |

---

## Immediate Next Steps

With **99.99% transpilation complete**, work proceeds phase by phase. Each phase must pass its validation gate before the next begins.

**Phase 0a — VEHU Docker M-Unit baseline (no transpilation needed):**
1. Build `utils/run_munit_vehu.py` — SSH into VEHU, import test routines, execute, parse output
2. Run all 58 M-Unit test routines from `VistA/Packages/*/Testing/MUnit/` against VEHU Docker
3. Save baseline results as `tests/vista/baselines/vehu_munit_baseline.json`

**Phase 0b — Transpiled M-Unit via pytest:**
4. Build global state bootstrap — export globals from VEHU, import into m2py SQLite store
5. Build pytest M-Unit adapter (`tests/vista/test_munit.py`) — transpile + execute test routines
6. Start with M-Unit self-tests (`%utt1`-`%utt7`), then M XML Parser, then FileMan, then Problem List/Scheduling

**Phase 1 — RPC example validation (Strategy 1):**
4. Write XWBZ1/XWBEXMPL tests using direct function calls
5. Validate all 12 RPC entry points produce identical output

**Phase 2 — Build RPC server infrastructure:**
6. Global bootstrap utility — import `^XWB(8994)`, `^%ZOSF`, `^VA(200)` from YDB
7. `NullDevice(MUMPSDevice)` — discards all writes (trivial)
8. Python-native RPC server — TCP server speaking RPC Broker protocol
9. Re-test Phase 1 RPCs via Strategy 2 (vista-test `VistABroker`)

**Phase 3-4 — RPC Broker + Authentication validation:**
10. Validate XWB infrastructure RPCs via the RPC server
11. Validate CPRS sign-on sequence end-to-end

**Phase 5 — Build terminal server infrastructure:**
12. Runtime extensions: `set_y()`, `read_char(timeout=)`, USE parameters
13. Terminal global bootstrap — `^%ZIS(1/2)`, `^ORD(101)`, IO variables
14. Python-native terminal server — PTY/socket binding
