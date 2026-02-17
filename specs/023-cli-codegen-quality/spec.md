# Feature Specification: CLI & Codegen Quality

**Feature Branch**: `023-cli-codegen-quality`  
**Created**: 2026-02-14  
**Status**: Draft  
**Input**: User description: "Add a CLI allowing a user to transpile a target file or directory (including nested directories) of MUMPS files into a working Python codebase. Add type hints to generated code with pyright validation. Add ruff lint checking and auto-formatting for generated code. Analyze code coverage and fill gaps. Deduplicate tests with substantial coverage overlap."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Transpile a Single MUMPS File (Priority: P1)

A developer has a single MUMPS routine file (e.g., `MYROUTINE.m`) and wants to convert it into a working Python module. They run a command pointing at the file and receive a Python file on disk that can be imported and executed with the m2py runtime.

**Why this priority**: This is the foundational use case — without single-file transpilation via a command-line interface, no other workflow is possible. It unlocks the core value of m2py for end users.

**Independent Test**: Can be fully tested by providing a known MUMPS file, running the CLI command, and verifying the output Python file exists, is syntactically valid, and produces correct output when executed.

**Acceptance Scenarios**:

1. **Given** a valid MUMPS file `HELLO.m`, **When** the user runs the transpile command targeting that file, **Then** a Python file is written to the output location containing valid, executable Python code.
2. **Given** a valid MUMPS file, **When** the user runs the transpile command with no explicit output path, **Then** the output file is written alongside the input file with the same base name and a `.py` extension.
3. **Given** a valid MUMPS file, **When** the user runs the transpile command with `--output /some/dir`, **Then** the output file is written to `/some/dir/` preserving any relative directory structure from the input path.
4. **Given** a MUMPS file that cannot be parsed, **When** the user runs the transpile command, **Then** the tool reports a clear error message identifying the file and the nature of the parsing failure, and exits with a non-zero status code.
5. **Given** a MUMPS file that parses but uses unsupported language features, **When** the user runs the transpile command, **Then** the tool reports a clear warning or error identifying what is unsupported, and either skips that file or exits with a non-zero status code.

---

### User Story 2 - Transpile a Directory of MUMPS Files (Priority: P1)

A developer has a directory tree containing many MUMPS routine files (possibly nested in subdirectories) and wants to transpile all of them into a corresponding Python package structure in a single operation.

**Why this priority**: Real-world MUMPS codebases consist of many routines. Batch transpilation is essential for practical adoption and is tightly coupled with single-file transpilation.

**Independent Test**: Can be tested by providing a directory with multiple `.m` files in nested subdirectories, running the command, and verifying all expected Python files are generated in the correct output structure.

**Acceptance Scenarios**:

1. **Given** a directory containing multiple `.m` files, **When** the user runs the transpile command targeting that directory, **Then** each MUMPS file is transpiled and a corresponding Python file is produced in the output directory.
2. **Given** a directory with nested subdirectories containing `.m` files, **When** the user runs the transpile command, **Then** the nested structure is preserved in the output (mirroring the input directory layout).
3. **Given** a mixed directory containing both `.m` files and non-MUMPS files, **When** the user runs the transpile command, **Then** only `.m` files are processed; other files are ignored.
4. **Given** a directory where some files transpile successfully and others fail, **When** the user runs the transpile command, **Then** the tool processes all files, reports errors for failures, and still writes output for successful files. A summary of successes and failures is displayed at the end.

---

### User Story 3 - Generated Code Passes Type Checking (Priority: P2)

A developer transpiles a MUMPS file and wants confidence that the generated Python code has proper type annotations where feasible and passes static type checking without errors. An expression-level type inference pass classifies the result type of MUMPS expressions, enabling the codegen to emit type hints on function signatures and simple variable assignments.

**Why this priority**: Type-annotated generated code increases developer trust and IDE support. The expression-level type inference also lays the foundation for future MUMPS-aware type analysis and codegen optimizations (e.g., skipping unnecessary type coercions).

**Independent Test**: Can be tested by transpiling a representative set of MUMPS files and running pyright in `basic` mode on the output, expecting zero errors.

**Acceptance Scenarios**:

1. **Given** a transpiled Python file produced by the CLI, **When** pyright analyzes the file in `basic` mode, **Then** no type errors are reported.
2. **Given** the transpiled output, **When** a developer opens it in an IDE with type checking enabled, **Then** type hints appear on function signatures, enabling autocomplete and type-based navigation.
3. **Given** a MUMPS routine with string operations (`$PIECE`, `$EXTRACT`), arithmetic, and intrinsic functions, **When** transpiled, **Then** the ASG has expression-level result types populated, and the generated code uses appropriate type annotations where the type is statically known.

---

### User Story 4 - Generated Code Passes Linting (Priority: P2)

A developer transpiles a MUMPS file and wants the output to conform to standard Python style and linting rules, so it integrates cleanly into modern Python toolchains.

**Why this priority**: Lint-clean generated code eliminates friction for developers integrating transpiled code into existing Python projects with CI/CD pipelines that enforce linting.

**Independent Test**: Can be tested by transpiling a representative set of MUMPS files and running a linter on the output, expecting zero lint errors.

**Acceptance Scenarios**:

1. **Given** a transpiled Python file, **When** a linter analyzes the file, **Then** no lint errors or warnings are reported.
2. **Given** a set of transpiled Python files, **When** the linter runs across all files, **Then** all files pass without requiring manual fixups.

---

### User Story 5 - Generated Code is Auto-Formatted (Priority: P3)

A developer transpiles MUMPS files to disk and wants the output to be consistently formatted using standard Python formatting conventions, without needing to run a formatter manually afterward.

**Why this priority**: Consistent formatting is a polish feature that improves readability and diff quality. It depends on the CLI (P1) being in place and is lower priority than correctness (type checking, linting).

**Independent Test**: Can be tested by transpiling files, then running a formatter in check mode — the output should already be formatted (i.e., no changes needed).

**Acceptance Scenarios**:

1. **Given** a transpiled Python file written to disk by the CLI, **When** a formatter runs in check mode, **Then** no formatting changes are needed.
2. **Given** that the transpiler is used in a CI/CD pipeline, **When** the output is committed to version control, **Then** the formatting is deterministic and consistent across runs.

---

### User Story 6 - Comprehensive Test Coverage (Priority: P3)

A project maintainer wants to ensure that the m2py codebase has thorough test coverage, with gaps identified and filled, so that regressions are caught early.

**Why this priority**: Coverage improvements strengthen the project's reliability but do not directly add new user-facing functionality. They support long-term maintainability.

**Independent Test**: Can be tested by running the test suite with coverage reporting and verifying that coverage meets or exceeds the target threshold for each module.

**Acceptance Scenarios**:

1. **Given** the current test suite, **When** coverage is measured and gaps analyzed, **Then** all meaningful gaps (untested code paths representing real behavioral risk) are identified and prioritized for testing.
2. **Given** identified meaningful coverage gaps, **When** new tests are written for those gaps, **Then** the gap is closed without introducing redundant or overlapping tests. Coverage work stops when remaining uncovered paths are pedantic or low-value.
3. **Given** the new tests, **When** the full test suite runs, **Then** all existing tests continue to pass (no regressions).

---

### User Story 7 - Deduplicated Test Suite (Priority: P3)

A project maintainer wants to identify and remove tests that substantially duplicate coverage of the same code paths, reducing test suite run time and maintenance burden without decreasing overall coverage.

**Why this priority**: Test deduplication is a maintenance optimization. It only makes sense after coverage gaps are filled (Story 6), ensuring that removals don't create new gaps.

**Independent Test**: Can be tested by comparing coverage reports before and after deduplication — coverage must not decrease, and test suite run time should decrease or remain stable.

**Acceptance Scenarios**:

1. **Given** pairs or groups of tests that exercise the same code paths, **When** redundant tests are removed, **Then** overall code coverage does not decrease.
2. **Given** the deduplicated test suite, **When** the full suite runs, **Then** all remaining tests pass and total execution time is reduced or unchanged.
3. **Given** the deduplication process, **When** tests are removed, **Then** each removal is justified by demonstrating the coverage overlap (e.g., by showing that another test covers the same lines/branches).

---

### Edge Cases

- What happens when the input path does not exist or is inaccessible? The CLI must report a clear "file/directory not found" error and exit with a non-zero status code.
- What happens when the output directory is not writable? The CLI must report a permissions error and exit with a non-zero status code.
- What happens when a MUMPS file has no labels (empty routine)? The transpiler should produce a valid (possibly empty or minimal) Python module without crashing.
- What happens when a MUMPS filename conflicts with a Python reserved word or built-in module name? The output filename must be adjusted or the user warned.
- What happens when the same input file is transpiled twice to the same output location? The output should be overwritten (idempotent behavior).
- How does the CLI handle very large directories (thousands of files)? It should process files without excessive memory usage and provide progress feedback.
- What happens when the generated code contains constructs that are correct but trigger linter false-positives (e.g., dynamically generated variable names from indirection)? These should be handled by targeted lint suppression in the generated code, not by turning off lint rules globally.

## Requirements *(mandatory)*

### Functional Requirements

#### CLI

- **FR-001**: The system MUST provide a command-line interface that accepts a file path to a single MUMPS `.m` file and produces a transpiled Python `.py` file.
- **FR-002**: The system MUST provide a command-line interface that accepts a directory path and recursively transpiles all `.m` files found within it, including nested subdirectories.
- **FR-003**: The CLI MUST write `.py` files alongside the corresponding `.m` input files by default (same directory, same base name, `.py` extension). The CLI MUST also accept an optional `--output` / `-o` flag specifying a dedicated output directory, in which case the input directory structure is mirrored within it.
- **FR-004**: The CLI MUST report clear, actionable error messages for parse failures, unsupported features, file-not-found, and permission errors.
- **FR-005**: The CLI MUST exit with status code 0 on full success and a non-zero status code when any file fails to transpile.
- **FR-006**: The CLI MUST provide a summary at the end of batch transpilation showing the count of files processed successfully and the count of files that failed.
- **FR-007**: The CLI MUST be installable as a named command (`m2py`) via the project's package entry points, runnable as `m2py <path>` (no subcommand).
- **FR-008**: The CLI MUST support a `--verbose` or `-v` flag that provides detailed progress output during transpilation (files being processed, timing, etc.).
- **FR-008a**: The CLI MUST support a `--no-format` flag that disables ruff lint-fix and formatting on generated output. Ruff processing MUST be enabled by default.

#### Code Quality — Type Hints

- **FR-009**: Generated Python code MUST include type hints on generated function signatures (parameters and return types) where the type is statically known.
- **FR-010**: Generated Python code MUST pass pyright type checking in `basic` mode with zero errors.
- **FR-010a**: An expression-level type inference pass MUST be added to the ASG (adding a `result_type` field to `MExpr`) that classifies expression results using an `ExprResultType` enum with values: `STRING` (str), `NUMERIC` (int | Decimal), `BOOLEAN_INT` (0 or 1), `NUMERIC_STRING` (formatted number as str, e.g. $JUSTIFY), and `UNKNOWN` (cannot determine statically). See data-model.md for the authoritative type mapping table. This provides the foundation for emitting type hints and for future MUMPS-aware type analysis.
- **FR-011**: The test suite MUST include automated tests that run pyright in `basic` mode on representative transpiled output and assert zero errors.
- **FR-012**: Any codegen issues discovered through type checking MUST be fixed in the codegen layer (not suppressed via type-ignore comments, unless a specific construct genuinely requires dynamic typing).

#### Code Quality — Linting

- **FR-013**: Generated Python code MUST pass linting using ruff's default rule set (`E` + `F` — pycodestyle errors and pyflakes) with zero errors or warnings. Additional rule categories may be enabled in future iterations.
- **FR-014**: The test suite MUST include automated tests that run a linter on representative transpiled output and assert zero lint issues.
- **FR-015**: Any codegen issues discovered through linting MUST be fixed in the codegen layer. Where a lint rule conflicts with a necessary codegen pattern (e.g., dynamically generated names), a targeted inline suppression comment MUST be emitted in the generated code.

#### Code Quality — Formatting

- **FR-016**: Python files written to disk by the CLI MUST be auto-formatted before being saved by default, so that the output is deterministically formatted. This MUST be skippable via `--no-format`.
- **FR-017**: Formatting MUST only apply to files written to disk by the CLI. Code generated for in-memory execution (unit tests, runtime `XECUTE`) MUST NOT be formatted.
- **FR-018**: The test suite MUST include automated tests that verify transpiled output is already formatted (formatter check mode returns no changes).

#### Test Coverage

- **FR-019**: Code coverage analysis MUST be performed across the entire codebase. Meaningful gaps (untested code paths that represent real behavioral risk) MUST have new tests added. Coverage work MUST stop when remaining uncovered paths are pedantic or low-value (e.g., defensive error branches requiring exotic system states, trivially unreachable code).
- **FR-020**: New tests MUST be added to existing spec-aligned test files where appropriate, rather than creating new test files unnecessarily.
- **FR-021**: No coverage exclusion markers (e.g., `# pragma: no cover`) MUST be added to the source code to artificially inflate coverage numbers.

#### Test Deduplication

- **FR-022**: Tests with substantial duplication of coverage (exercising the same code paths) MUST be identified through coverage analysis.
- **FR-023**: Redundant tests MUST be removed only when another test demonstrably covers the same lines and branches.
- **FR-024**: Overall code coverage MUST NOT decrease as a result of test deduplication.

### Key Entities

- **MUMPS Routine File**: A `.m` source file containing one or more labeled entry points and MUMPS commands. The input unit for transpilation.
- **Transpiled Python Module**: A `.py` file generated from a single MUMPS routine. Contains function definitions corresponding to MUMPS labels, with type hints and proper formatting.
- **Output Directory**: The target directory structure where transpiled Python modules are written. Mirrors the input directory layout.
- **Transpilation Report**: A summary produced by the CLI after batch processing, listing successes, failures, and any warnings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can transpile a single MUMPS file to a Python file via the CLI in under 5 seconds for typical routine sizes (≤500 lines). This is a soft guideline, not a gated metric.
- **SC-002**: A user can transpile a directory of 100+ MUMPS files in a single CLI invocation, with all successful outputs written to disk.
- **SC-003**: 100% of transpiled Python files pass pyright in `basic` mode with zero errors.
- **SC-003a**: Expression-level type inference covers ≥80% of expressions with concrete types (STRING, NUMERIC, BOOLEAN_INT, NUMERIC_STRING), with UNKNOWN used only for genuinely dynamic constructs (variables, indirection, XECUTE, extrinsic function returns). This is advisory — no automated gate enforces this threshold.
- **SC-004**: 100% of transpiled Python files pass linting with zero errors (excluding targeted inline suppressions for genuinely dynamic constructs).
- **SC-005**: 100% of transpiled Python files written to disk are already auto-formatted (formatter check mode reports no changes).
- **SC-006**: All meaningful coverage gaps (untested code paths representing real behavioral risk) are addressed. Remaining uncovered code is limited to low-value paths (defensive error handling, exotic system states) where further tests would be pedantic. No coverage exclusion markers are added.
- **SC-007**: Test suite execution time does not increase by more than 10% after coverage gap-filling, and decreases or remains stable after deduplication.
- **SC-008**: The CLI provides clear, actionable error messages for all failure modes (parse errors, unsupported features, file system errors), enabling users to resolve issues without consulting documentation.

## Clarifications

### Session 2026-02-14

- Q: What is the default output path when no `--output` flag is provided? → A: Default writes `.py` alongside `.m` inputs; `--output`/`-o` flag redirects to a dedicated directory mirroring input structure.
- Q: Which ruff rule set should generated code pass? → A: Ruff defaults (`E` + `F` — pycodestyle errors and pyflakes). Expandable later.
- Q: Should coverage targets be overall aggregate, per-module, or numeric? → A: No hard numeric target. Focus on identifying and fixing all meaningful gaps until further tests become pedantic and low-value.
- Q: What pyright strictness level for generated code? → A: `basic` mode (already passes with zero changes). Add expression-level type inference to the ASG as a foundation for type hints and future MUMPS-aware type tracking. Variable-level type tracking deferred to future work as a custom system external to pyright.

## Assumptions

- The existing `generate_python()` function in the codegen module is the correct entry point for transpilation and does not need to be replaced, only wrapped by the CLI.
- MUMPS files use the `.m` file extension. Other extensions are not transpiled unless explicitly specified.
- The type checker used for generated code validation is pyright in `basic` mode. This catches real errors (wrong imports, undefined names, bad calls) without fighting MUMPS's inherently dynamic type system.
- Expression-level type inference on the ASG is the foundation for future MUMPS-aware type analysis. Full variable-level type tracking (across assignments, branches, and control flow) is explicitly out of scope for this feature but enabled by the expression-level foundation. Any future type tracking system would be custom and MUMPS-domain-specific, not built on pyright's type system.
- The linter and formatter used are ruff, which is a standard Python tool. If not already a dependency, it will be added.
- Auto-formatting only applies to files persisted to disk via the CLI. Code generated in-memory for test execution or runtime `XECUTE` is not formatted, as formatting would add unnecessary overhead and the code is never read by humans.
- Coverage targets are qualitative rather than numeric. The goal is to close all meaningful gaps (code paths that represent real behavioral risk), stopping when remaining uncovered paths are pedantic or low-value. Coverage numbers are tracked for progress visibility but are not a pass/fail gate.
- Test deduplication is performed conservatively — only tests with clearly redundant coverage are removed, with coverage measurements taken before and after to confirm no decrease.
