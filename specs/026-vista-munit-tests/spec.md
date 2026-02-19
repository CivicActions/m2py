# Feature Specification: VistA M-Unit Test Suite via pytest (Phase 0)

**Feature Branch**: `026-vista-munit-tests`  
**Created**: 2025-07-22  
**Status**: Draft  
**Input**: User description: "Implement Phase 0 of VistA-VEHU test plan: run OSEHRA M-Unit test suite against VEHU Docker baseline and transpiled Python via pytest"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Capture VEHU Docker M-Unit Baseline (Priority: P1)

A developer wants to establish the ground truth for VistA's existing M-Unit test suite by running all 58 test routines (1,186 assertions) against the live VEHU Docker container. This captures which tests pass and which fail in the original MUMPS environment, so the transpiled Python is only expected to match — not exceed — the original behavior.

**Why this priority**: Without a baseline, there is no reference to compare transpiled results against. Every subsequent story depends on this data.

**Independent Test**: Can be fully tested by starting the VEHU Docker container, running the baseline tool, and verifying the output JSON contains results for all 58 test routines across 5 packages.

**Acceptance Scenarios**:

1. **Given** the VEHU Docker container is running and accessible via SSH, **When** the baseline runner executes all M-Unit test routines, **Then** structured JSON results are produced containing per-routine pass/fail counts for all 58 routines across 5 packages (VA FileMan, Problem List, Scheduling, Registration, M XML Parser).
2. **Given** a test routine must be imported before execution, **When** the baseline runner encounters a routine not already loaded in VEHU, **Then** it imports the routine from the VistA submodule (`vista-test/VistA/Packages/*/Testing/MUnit/*.m`) before running it.
3. **Given** some M-Unit tests may fail even on the original VEHU, **When** a test routine produces failures or errors, **Then** the baseline records failure counts and individual failure messages (entry tag, test name, assertion message) so they can inform expected-failure annotations later.
4. **Given** the baseline has been captured, **When** it is saved to the designated location and committed, **Then** it can be loaded by the pytest adapter in Story 3 to drive `xfail` annotations without requiring a running VEHU Docker container.

---

### User Story 2 — M-Unit Output Parser (Priority: P1)

A developer needs a reliable parser for M-Unit framework output so that both the baseline runner (Story 1) and the pytest adapter (Story 3) can extract structured test results from raw M-Unit text output.

**Why this priority**: Both Story 1 and Story 3 depend on parsing M-Unit output. Extracting per-test pass/fail from raw text is non-trivial and must handle edge cases (multi-line messages, error output mixed with results).

**Independent Test**: Can be fully tested with captured sample M-Unit output strings — no Docker or transpilation needed. Unit tests verify correct parsing of passes, failures, errors, and summary lines.

**Acceptance Scenarios**:

1. **Given** raw M-Unit output from a passing test routine (e.g., `".........\nRan 1 Routine, 5 Entry Tags\nChecked 9 tests, with 0 failures and encountered 0 errors."`), **When** the parser processes it, **Then** it returns a structured result with total tests, zero failures, zero errors, and status "pass".
2. **Given** raw M-Unit output containing failures (e.g., `"DTFUT - Future Date Test - Future Date Test Full Failed."`), **When** the parser processes it, **Then** it extracts each failure's entry tag, test name, and assertion message into a structured list.
3. **Given** raw M-Unit output with errors (e.g., routines that crash or produce `<UNDEFINED>` errors), **When** the parser processes it, **Then** it records the error count and any error messages without losing other test results.
4. **Given** output from the M-Unit self-test routines (`%utt1`–`%utt7`), **When** the parser processes it, **Then** it correctly handles the self-referential output format where the framework tests itself.

---

### User Story 3 — Run Transpiled M-Unit Tests via pytest (Priority: P2)

A developer wants to run the same M-Unit test routines — transpiled to Python — against the transpiled VistA codebase and compare results to the VEHU baseline. Tests that pass on VEHU must also pass in Python; tests that fail on VEHU are marked as expected failures.

**Why this priority**: This is the core validation goal of Phase 0, but depends on Stories 1 and 2. It's the primary deliverable that proves m2py produces semantically correct Python.

**Independent Test**: Can be tested by running `uv run pytest tests/vista/munit/` from the vista-test directory against the transpiled code with a pre-generated baseline JSON.

**Acceptance Scenarios**:

1. **Given** the M-Unit framework (`%ut`, `%ut1`) has been transpiled to Python, **When** a transpiled test routine calls `CHKEQ^%ut(expected, actual, msg)`, **Then** the transpiled assertion logic correctly compares values and records pass/fail using the same semantics as the original MUMPS.
2. **Given** a test routine passes on VEHU, **When** the same routine is transpiled and run in Python, **Then** it also passes (same number of checks, zero failures, zero errors).
3. **Given** a test routine fails on VEHU (recorded in the baseline), **When** that routine is run in Python, **Then** it is marked as `xfail` (expected failure) rather than a test failure.
4. **Given** the full set of 58 test routines, **When** `uv run pytest tests/vista/munit/` is run, **Then** each routine appears as a separate test item with clear pass/xfail/fail reporting.
5. **Given** a transpiled test routine produces a Python error (e.g., missing runtime feature, transpilation bug), **When** the pytest adapter catches the error, **Then** it reports the error with enough context (routine name, entry tag, Python traceback) to identify the root cause for an m2py fix.

---

### User Story 4 — Bootstrap Global State for Test Dependencies (Priority: P3 — Stretch Goal)

A developer needs to populate the m2py global store with data from VEHU so that transpiled test routines can access the globals they depend on (data dictionaries, patient records, etc.).

**Why this priority**: Most M-Unit tests beyond M XML Parser require pre-populated global state. Without bootstrap, transpiled tests will fail with missing data, not transpilation bugs.

**Independent Test**: Can be tested by exporting globals from VEHU, importing into the m2py global store, and querying specific expected globals (e.g., `^DD(2,0)` exists, `^DPT("B",...)` has entries).

**Acceptance Scenarios**:

1. **Given** the VEHU Docker container is running, **When** the bootstrap tool exports globals required by M-Unit test packages, **Then** the exported data covers at minimum: `^DD` (data dictionary), `^DIC` (file attributes), and any package-specific globals identified in the test plan.
2. **Given** exported global data in a portable format, **When** the bootstrap tool imports it into the m2py global store, **Then** transpiled code accessing those globals via `MDict` retrieves the same values as the original MUMPS code on VEHU.
3. **Given** the M XML Parser tests (4 routines) use only `^TMP($J)` which is created dynamically, **When** those tests run without any bootstrap, **Then** they should pass after transpilation (making them the ideal first target).
4. **Given** the M-Unit self-tests (`%utt1`–`%utt7`) use only the framework's own globals, **When** those tests run with minimal bootstrap, **Then** they validate the M-Unit framework transpilation works correctly.

---

### User Story 5 — Fix m2py Transpilation and Runtime Issues (Priority: P2)

As M-Unit tests are transpiled and run, the developer discovers transpilation or runtime bugs in m2py. Each bug must be fixed in the m2py codebase (root workspace) with standalone unit tests that have no VistA dependency.

**Why this priority**: Fixing m2py issues is essential for Story 3 to succeed, but each fix is an independent unit of work tracked in the m2py repo, not in vista-test.

**Independent Test**: Each m2py fix is accompanied by a minimal MUMPS-to-Python test case in the m2py test suite that demonstrates the bug and verifies the fix, with no reference to VistA code.

**Acceptance Scenarios**:

1. **Given** a transpiled M-Unit test encounters a Python error traceable to a transpilation bug, **When** the developer extracts a minimal MUMPS snippet reproducing the issue, **Then** a new test is added to `tests/` in the m2py repo that fails before the fix and passes after.
2. **Given** a transpiled M-Unit test encounters a runtime error (e.g., missing intrinsic function, incorrect `$ORDER` behavior), **When** the developer identifies the runtime gap, **Then** the fix is made in `src/m2py/` with a corresponding unit test that validates correct behavior using only m2py constructs.
3. **Given** multiple M-Unit tests fail due to the same root cause, **When** the m2py fix is applied, **Then** all dependent M-Unit tests pass without individual workarounds.

---

### User Story 6 — Incremental Test Expansion by Package (Priority: P3)

A developer wants to expand M-Unit test coverage incrementally, starting with the simplest packages (no data dependencies) and progressing to packages requiring fuller global state.

**Why this priority**: Incremental expansion de-risks the effort by validating simpler scenarios first and building confidence before tackling data-heavy packages.

**Independent Test**: Each package tier can be run independently via pytest marks or directory targeting, and each tier's pass rate is tracked separately.

**Acceptance Scenarios**:

1. **Given** the M-Unit self-tests (`%utt1`–`%utt7`) have no external data dependencies, **When** they are the first tests transpiled and run, **Then** they validate that the M-Unit framework itself works correctly in Python.
2. **Given** the M XML Parser tests (4 routines) create their own temporary data, **When** they are run after M-Unit self-tests pass, **Then** they validate XML parsing with minimal bootstrap requirements.
3. **Given** VA FileMan tests (30 routines) require `^DD` and test fixture files, **When** they are run after global bootstrap is complete, **Then** they validate date/time, lookup, sort, and computed field operations.
4. **Given** Problem List (9 routines), Scheduling (12 routines), and Registration (1 routine) tests require patient and clinic data, **When** they are run with full global bootstrap, **Then** they validate clinical infrastructure APIs.

---

### Edge Cases

- What happens when the VEHU Docker container is not running or SSH is unreachable? The baseline runner must report a clear error and not produce partial results.
- How does the system handle M-Unit test routines that hang or produce no output within a timeout? Each routine execution must have a configurable timeout with clear timeout error reporting.
- What happens when a test routine imports successfully but its dependencies are missing from VEHU? The baseline must record this as an error, not silently skip the routine.
- How does the parser handle malformed M-Unit output (e.g., a routine that crashes mid-test producing partial output)? The parser must extract whatever results are available and record the unparsed remainder as an error.
- What happens when a transpiled routine produces different output formatting (e.g., extra whitespace, different line endings) than the MUMPS original? The parser must normalize output before comparison where appropriate.
- How does the system handle the large VA FileMan fixture initialization (DMUFINIT creates test files 1009.801, 1009.802)? The fixture creation routines themselves must be transpiled and run as part of STARTUP, or their effects must be pre-loaded via global bootstrap.

## Requirements *(mandatory)*

### Functional Requirements

#### Baseline Runner (Phase 0a — lives in vista-test)

- **FR-001**: The baseline runner MUST connect to the VEHU Docker container via SSH programmer mode (`vehuprog`/`prog`) and enter MUMPS direct mode.
- **FR-002**: The baseline runner MUST import M-Unit test routines from the VistA submodule (`vista-test/VistA/Packages/*/Testing/MUnit/*.m`) into the VEHU instance before executing them.
- **FR-003**: The baseline runner MUST execute each test routine using the command specified in the corresponding TestList file (e.g., `D ^ZZRGUT`, `D EN^%ut("DMUDT000")`, `D TEST^MXMLBLD`).
- **FR-004**: The baseline runner MUST capture raw M-Unit output from each test routine execution, including all assertion dots, failure messages, and summary lines.
- **FR-005**: The baseline runner MUST produce a structured JSON file containing per-routine results (test count, failure count, error count, individual failure details) grouped by package. This file is committed into the vista-test repository and regenerated manually when VEHU or test routines change.
- **FR-006**: The baseline runner MUST support running all packages, a single package, or a single routine via command-line options.
- **FR-007**: The baseline runner MUST enforce a configurable per-routine execution timeout (default: 120 seconds) and record timeout as an error.

#### M-Unit Output Parser (shared between Phase 0a and 0b)

- **FR-008**: The parser MUST extract the total test count, failure count, and error count from the M-Unit summary line (`"Checked X tests, with Y failures and encountered Z errors."`).
- **FR-009**: The parser MUST extract individual failure details including the entry tag name, test description, and assertion message from failure output lines.
- **FR-010**: The parser MUST handle both `@TEST` annotated tests and `XTENT`-style entry point lists.
- **FR-011**: The parser MUST handle partial output (routine crashed mid-test) by extracting available results and flagging the remainder as an error.

#### pytest M-Unit Adapter (Phase 0b — lives in vista-test, imports from m2py)

- **FR-012**: The pytest adapter MUST discover M-Unit test routines from the VistA submodule TestList files and present each routine as a separate pytest test item (one item per routine, not per `@TEST` tag).
- **FR-013**: The pytest adapter MUST transpile each test routine and its dependencies using m2py before execution.
- **FR-014**: The pytest adapter MUST execute transpiled test routines using the m2py runtime and capture M-Unit output.
- **FR-015**: The pytest adapter MUST compare transpiled test results against the VEHU baseline: routines that pass on VEHU must pass in Python; routines that fail on VEHU are marked `xfail`.
- **FR-016**: The pytest adapter MUST report individual test routine results with clear identification (package name, routine name, pass/xfail/fail status). Granularity is one result per routine.
- **FR-017**: The pytest adapter MUST capture and report Python errors (tracebacks) from transpiled code to assist debugging m2py issues.

#### Global State Bootstrap (Phase 0b — stretch goal, tool lives in vista-test)

- **FR-018**: *(Stretch goal)* The bootstrap tool MUST export required globals from the VEHU Docker container in a portable format (ZWR or equivalent).
- **FR-019**: *(Stretch goal)* The bootstrap tool MUST import exported globals into the m2py global store so transpiled code can access them.
- **FR-020**: *(Stretch goal)* The bootstrap MUST support incremental loading — only globals needed for the current test tier need to be loaded.
- **FR-020a**: For Tier 1+2 targets (M-Unit self-tests, M XML Parser), any minimal global state needed MUST be handled inline in pytest fixtures rather than requiring the bootstrap tool.

#### m2py Fixes (lives in m2py root workspace)

- **FR-021**: Each m2py transpilation or runtime bug discovered during M-Unit testing MUST be fixed in the m2py codebase (`src/m2py/`).
- **FR-022**: Each m2py fix MUST include standalone unit tests in the m2py test suite (`tests/`) that reproduce the bug with minimal MUMPS code and verify the fix — with no dependency on VistA routines.
- **FR-023**: m2py fixes MUST NOT introduce regressions in existing m2py tests.

#### Cross-Repository Structure

- **FR-024**: All VistA-VEHU functional test code (baseline runner, pytest adapter, global bootstrap) MUST reside in the `vista-test` repository.
- **FR-025**: The VistA submodule (`vista-test/VistA/`) provides read-only access to M-Unit test routines and TestList files. No modifications to submodule content.
- **FR-026**: The `VistA-VEHU-M/` directory is read-only reference material for the transpiled VistA routine sources.
- **FR-027**: m2py transpilation and runtime fixes go in the root workspace (`/workspaces/m2py/src/m2py/`) with standalone tests in `/workspaces/m2py/tests/`.

### Key Entities

- **M-Unit Test Routine**: A MUMPS routine containing test entry points tagged with `@TEST` annotations or listed in `XTENT`. Located in `VistA/Packages/<package>/Testing/MUnit/<routine>.m`. Contains assertions (`CHKEQ`, `CHKTF`, `FAIL`, `SUCCEED`) and lifecycle hooks (`STARTUP`, `SHUTDOWN`, `SETUP`, `TEARDOWN`).
- **M-Unit Framework**: The `%ut` and `%ut1` routines from the MASH Utilities package that implement the assertion API, test discovery, execution lifecycle, and result reporting. Pre-installed in VistA-VEHU-M. Must also transpile correctly to serve as the Python-side test runner.
- **TestList File**: A text file in each package's MUnit directory listing the commands to invoke test routines (e.g., `D ^ZZRGUT`, `D EN^%ut("DMUDT000")`). Used by the OSEHRA ctest infrastructure and adapted here for pytest discovery.
- **VEHU Baseline**: A JSON file containing per-routine test results from running M-Unit tests against the VEHU Docker container. Serves as the ground truth for comparing transpiled Python behavior.
- **Global State Snapshot**: An export of MUMPS globals from VEHU (in ZWR or similar format) required by test routines. Loaded into the m2py global store before running transpiled tests.

## Clarifications

### Session 2026-02-19

- Q: Does "Phase 0 complete" mean all 58 routines pass, or a subset? → A: Minimum viable = Tier 1+2 (11 routines: %utt1-7 + 4 XML Parser). Tiers 3-4 (FileMan, Problem List, Scheduling, Registration) are stretch goals within the same spec.
- Q: Should pytest report one item per routine or one per @TEST tag? → A: One pytest item per routine. Simpler; matches M-Unit summary output directly.
- Q: Should the global bootstrap tool be built for minimum viable scope or deferred? → A: Defer bootstrap tool to stretch goals. Handle any minimal Tier 1+2 globals inline in test fixtures.
- Q: Should the VEHU baseline JSON be committed or generated on-the-fly? → A: Commit baseline JSON into vista-test repo. Transpiled tests run offline against the committed fixture. Regenerate manually when needed.

## Assumptions

- The WorldVistA VEHU Docker image (`worldvista/vehu`) is available and can be pulled/started via Docker.
- SSH access to the VEHU container works on port 2222 with credentials `vehuprog`/`prog` for programmer mode.
- The `%ut` / `%ut1` M-Unit framework is already installed in the VEHU instance (confirmed: it's in VistA-VEHU-M MASH Utilities).
- Test routines from the VistA submodule are compatible with the VEHU instance (same VistA version/patch level).
- The m2py transpiler successfully transpiles the M-Unit framework routines (`%ut`, `%ut1`) and all 58 test routines (99.99% transpile rate applies).
- Global export from VEHU via `%GO` or equivalent is feasible for the required data sets.
- M-Unit output format is consistent across all test routines and follows the documented format from the `%ut` framework.
- M XML Parser tests and M-Unit self-tests have no external global data dependencies and are suitable as first targets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: VEHU baseline captured for all 58 M-Unit test routines, with per-routine results stored in a structured format that the pytest adapter can load.
- **SC-002**: The M-Unit output parser correctly extracts results from 100% of M-Unit output variants encountered in the 58 test routines, validated by unit tests against captured sample output.
- **SC-003**: The M-Unit self-tests (`%utt1`–`%utt7`, 7 routines) pass when transpiled and run in Python, validating framework correctness.
- **SC-004**: The M XML Parser tests (4 routines, ~97 assertions) pass when transpiled and run in Python, as the first package with no external global dependencies.
- **SC-005**: Every Tier 1+2 M-Unit test routine (11 routines: `%utt1`–`%utt7` + 4 M XML Parser) that passes on VEHU also passes when transpiled and run in Python — zero regressions compared to the baseline. Tiers 3-4 (FileMan, Problem List, Scheduling, Registration) are stretch goals tracked in the same spec.
- **SC-006**: Every m2py bug discovered during M-Unit testing has a corresponding standalone unit test in the m2py repo that does not depend on VistA.
- **SC-007**: Running `uv run pytest tests/vista/munit/` from the vista-test directory discovers and executes all 58 transpiled test routines with clear per-routine pass/xfail/fail reporting.
