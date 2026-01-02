# Feature Specification: MUMPS Spec-Aligned Unit Test Organization

**Feature Branch**: `002-spec-unit-test-organization` (tracking branch for PR; changes apply in-place to `tests/` directory)  
**Created**: 2026-01-01  
**Status**: Draft  
**Input**: User description: "Reorganize unit tests to systematically map to MUMPS spec sections, enabling verifiable coverage of parser and ASG output against the 1995 ANSI M standard"

---

## Executive Summary

This specification defines a systematic reorganization of M2PY's unit tests to directly map to sections of the ANSI M X11.1-1995 standard. The goal is to establish **verifiable, gap-free coverage** of the MUMPS language specification, ensuring both the textX parser and the Abstract Semantic Graph (ASG) correctly handle every language feature.

### Key Outcomes

1. **Spec-Aligned Test Structure**: Tests organized by MUMPS spec section (§5-§9), enabling direct traceability
2. **Three-Level Testing**: Separate verification of parser output (raw extraction), final ASG (analysis-complete), and Python codegen/execution
3. **Stub-First Coverage**: Every spec section has test stubs from day one, using `xfail` markers for pending implementation
4. **Coverage Matrix**: Explicit tracking of what's tested, what's pending, and what's intentionally out-of-scope
5. **Backward Compatibility Analysis**: Identification of any pre-1995 syntax that differs and needs support
6. **Extension Support**: Structure accommodating YottaDB/GT.M Z-commands and vendor extensions

### Not In Scope

- Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER, ASSIGN) per `docs/limitations.md`
- THEN command (zero real-world usage identified)
- Actual MUMPS runtime execution (codegen tests verify generated Python behavior against YDBTest expected outputs and MUMPS spec, not live MUMPS interpreter comparison)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verify Parser Extracts All Language Features Correctly (Priority: P1)

As a developer working on M2PY, I want unit tests that verify the textX parser correctly extracts all syntactic elements from MUMPS source code, so that I can confidently know the parser captures everything needed before semantic analysis.

**Why this priority**: The parser is the foundation—if it doesn't extract information correctly, no downstream analysis can succeed. This catches bugs at the earliest stage.

**Independent Test**: Parse MUMPS code for each spec section and verify the raw textX model contains the expected structure (correct classes instantiated, all attributes populated, proper nesting).

**Acceptance Scenarios**:

1. **Given** a MUMPS command with all its syntactic variations (per §8.2.x), **When** parsed, **Then** the textX model contains the command class with all arguments, postconditions, and options correctly captured
2. **Given** an expression with operators (per §7.2), **When** parsed, **Then** the textX model contains operator nodes in left-to-right order with correct operands
3. **Given** a routine with labels and formal parameters (per §6.1-6.2), **When** parsed, **Then** the textX model contains label nodes with name and parameter list correctly captured
4. **Given** intrinsic function calls (per §7.1.5), **When** parsed, **Then** the textX model contains function call nodes with function name and all arguments

---

### User Story 2 - Verify ASG Contains All Features Needed for Python Codegen (Priority: P1)

As a developer building the Python code generator, I want unit tests that verify the final ASG (after all analysis passes) contains complete, accurate semantic information for every language construct, so that code generation can be a straightforward traversal.

**Why this priority**: The ASG is the contract between parsing and codegen. If it's incomplete or incorrect, code generation will produce wrong Python code.

**Independent Test**: Parse MUMPS code, run all analysis passes, and verify the ASG contains correct types, resolved references, classified constructs, and annotated variables.

**Acceptance Scenarios**:

1. **Given** a FOR loop construct, **When** fully analyzed, **Then** the ASG node has `loop_type` classified (BOUNDED/OPEN_ENDED/STRING_LIST/etc), `is_infinite` flag set, and body scope correctly nested
2. **Given** a GOTO statement, **When** fully analyzed, **Then** the ASG node has `goto_type` classified, `target` resolved to MLabel (or marked EXTERNAL/INDIRECT), and `exits_loops` populated if applicable
3. **Given** a routine with subroutine calls, **When** fully analyzed, **Then** each MLabel has `input_variables`, `output_variables`, and `variables_newed` correctly computed
4. **Given** variables with various scopes, **When** fully analyzed, **Then** variable nodes are correctly distinguished as local/global/SSV and scope boundaries are marked

---

### User Story 3 - Identify and Document Coverage Gaps (Priority: P1)

As a project maintainer, I want a clear coverage matrix that shows exactly which MUMPS spec sections have tests, which are pending implementation, and which are intentionally excluded, so that I can track progress and prioritize work.

**Why this priority**: Without explicit gap tracking, it's impossible to know when we've achieved complete coverage or what work remains.

**Independent Test**: Run `uv run python utils/audit_tests.py` and verify all §5-§9 sections are accounted for.

**Acceptance Scenarios**:

1. **Given** the complete MUMPS 1995 spec table of contents, **When** the audit script runs, **Then** every section is accounted for in at least one test category (parser, asg, or codegen) as either: tested (pass), stub-marked (xfail), skip-marked, or flagged as missing
2. **Given** a test file with `@pytest.mark.skip(reason="...")`, **When** the audit script runs, **Then** it appears in the "skipped" category with the reason
3. **Given** a test with `@pytest.mark.xfail(reason="...")`, **When** the audit script runs, **Then** it appears in the "stub" category
4. **Given** a missing spec section, **When** the audit script runs, **Then** it is flagged and the script exits with non-zero status

---

### User Story 4 - Ensure Backward Compatibility with Pre-1995 Syntax (Priority: P2)

As a developer parsing legacy MUMPS code, I want the parser to handle any syntax variations from earlier standards (1977, 1984, 1990) that might appear in real codebases, so that the parser works with all production MUMPS code.

**Why this priority**: Real codebases like VistA contain code written over decades. If pre-1995 syntax differs, we must support it.

**Independent Test**: Identify syntax differences between standards and verify the parser handles both old and new forms.

**Acceptance Scenarios**:

1. **Given** a syntax element that changed between standards, **When** both old and new forms are parsed, **Then** both produce valid ASG nodes
2. **Given** a deprecated construct from an earlier standard, **When** parsed, **Then** it either parses correctly or produces a clear deprecation warning
3. **Given** code from VistA (written against various spec versions), **When** parsed, **Then** no syntax errors occur due to standard version differences

---

### User Story 5 - Support YottaDB/GT.M Z-Commands (Priority: P2)

As a developer parsing YottaDB-specific MUMPS code, I want the parser to correctly handle Z-commands (ZBREAK, ZWRITE, ZGOTO, etc.) that are implemented, so that real YottaDB codebases parse successfully.

**Why this priority**: The primary target runtime is YottaDB, and Z-commands appear frequently in YDB test suites and production code.

**Independent Test**: Parse Z-commands that M2PY implements and verify correct ASG representation.

**Acceptance Scenarios**:

1. **Given** an implemented Z-command (e.g., ZWRITE, ZBREAK), **When** parsed, **Then** the ASG contains the correct command node with all arguments
2. **Given** an unimplemented Z-command, **When** parsed, **Then** a clear error indicates it's an unrecognized vendor extension
3. **Given** the YDBTest suite Z-command usage, **When** parsed, **Then** all commonly-used Z-commands are handled

---

### User Story 6 - Restructure Existing Tests Without Losing Information (Priority: P2)

As a developer refactoring the test suite, I want to migrate existing unit tests into the new spec-aligned structure while preserving all test coverage and maintaining the ability to identify gaps.

**Why this priority**: We have significant existing test investment that must not be lost during reorganization.

**Independent Test**: After migration, run both old and new test suites and verify identical coverage.

**Acceptance Scenarios**:

1. **Given** an existing test file (e.g., `test_command_grammar.py`), **When** migrated to spec-aligned structure, **Then** all original test cases exist in the new location
2. **Given** the pre-migration test count, **When** migration completes, **Then** the post-migration test count is equal or greater
3. **Given** a test that covers multiple spec sections, **When** migrated, **Then** it's placed in the primary section with cross-references noted

---

### User Story 7 - Verify Python Codegen Produces Correct Behavior (Priority: P2)

As a developer building the Python code generator, I want stub tests for every language feature that will verify the generated Python code executes correctly and produces the same results as MUMPS semantics.

**Why this priority**: Codegen is the ultimate goal of the transpiler. Having stubs in place from the start ensures we know exactly what needs to be implemented and can track progress toward complete coverage.

**Independent Test**: For each spec section, generate Python from MUMPS, execute it, and verify output matches expected MUMPS behavior.

**Source of Truth for Expected Behavior**: Codegen tests MUST validate against one of these authoritative sources:
- **YDBTest functional suites**: `tests/functional/` contains YottaDB validation suites (MUGJ, MVTS, basic_inref, merge_inref, indirection_inref, m_commands_inref, io_inref, tp_inref, triggers_inref, longname_inref, unicode_inref) with known expected outputs
- **MUMPS Spec Citations**: For behaviors not covered by test suites, cite the specific MUMPS 1995 spec section (e.g., "per §7.2.5, pattern match returns 1 or 0")
- **Reference Implementation**: When ambiguous, YottaDB/GT.M runtime behavior is authoritative

**Acceptance Scenarios**:

1. **Given** a MUMPS routine with SET and WRITE commands, **When** transpiled and executed, **Then** the Python output matches expected YDBTest output or MUMPS spec behavior
2. **Given** a MUMPS FOR loop, **When** transpiled and executed, **Then** the Python loop iterates correctly with proper variable scoping per YDBTest validation
3. **Given** a MUMPS intrinsic function call, **When** transpiled and executed, **Then** the Python function produces identical results to YDBTest expected outputs
4. **Given** a codegen stub test (marked xfail), **When** implementation is completed, **Then** the test transitions from xfail to passing
5. **Given** a codegen test without YDBTest coverage, **When** implemented, **Then** the test MUST cite the MUMPS spec section defining the expected behavior

---

### User Story 8 - Manage Test Stubs with xfail for 100% Suite Pass Rate (Priority: P1)

As a developer, I want all unimplemented tests to use `pytest.xfail` markers so that the test suite always shows 100% passing while clearly indicating what's pending implementation.

**Why this priority**: A green CI pipeline is essential for developer confidence. Using xfail allows us to have complete coverage stubs while maintaining a passing suite.

**Independent Test**: Run `pytest` and verify all tests pass (implemented tests pass, stubs show as xfail).

**Acceptance Scenarios**:

1. **Given** a stub test marked with `@pytest.mark.xfail(reason="stub: needs implementation")`, **When** pytest runs, **Then** it shows as "xfail" (expected failure) and the suite passes
2. **Given** a stub test that gets implemented, **When** the implementation is complete, **Then** removing the xfail marker causes the test to pass normally
3. **Given** the full test suite with stubs, **When** `pytest` runs with default options, **Then** exit code is 0 (success)
4. **Given** compound markers (`@pytest.mark.stub`, `@pytest.mark.parser`/`@pytest.mark.asg`/`@pytest.mark.codegen`, and `@pytest.mark.xfail(reason="...")` together), **When** running `pytest -m "not stub"`, **Then** only implemented tests run

---

### Edge Cases

- **Syntax ambiguity**: MUMPS allows abbreviated commands—how do we test that `S` parses identically to `SET`?
- **Indirection everywhere**: Many constructs support `@` indirection—how do we avoid duplicating indirection tests across every command?
- **Argumentless commands**: Commands like argumentless DO, FOR, and NEW have special semantics—ensure they're tested distinctly from argument forms
- **Multi-argument commands**: Commands accepting multiple arguments (SET, WRITE, KILL) need tests for both single and multiple argument forms (minimum: 1, 2, and 3+ arguments)
- **Postcondition scope**: Command postconditions (`SET:Cond X=1`) gate the entire command; argument postconditions (`DO Label:C1,Label2:C2`) are independent per argument per §8.1.4
- **Pattern match complexity**: Pattern syntax (§7.2.5) is complex enough to warrant exhaustive separate testing—including pattern codes (A=alpha, C=control, E=any, L=lowercase, N=numeric, P=punctuation, U=uppercase), alternation `?(3N,2A)`, indefinite quantifiers `.E`, and pattern indirection `?@P`
- **Naked global references**: The "naked indicator" (`^(subscript)`) relies on runtime state from the last global reference—tests must verify sequence-dependent behavior
- **$TEST side effects**: `$TEST` is set by argumentless IF, and by OPEN/READ/JOB/LOCK commands with timeouts—tests must verify all contributing commands and ELSE behavior
- **Exclusive NEW**: `NEW (X,Y)` stacks *all locals except* X and Y (inverse of normal NEW)—requires distinct variable scope tests
- **Left-to-right evaluation**: MUMPS has no operator precedence; all binary operators evaluate strictly left-to-right—tests must verify `2+3*4` equals `20`, not `14`
- **Transaction nesting**: `TSTART` can nest; `$TLEVEL` tracks depth; `TROLLBACK` can roll back one level or all—tests must cover nested transaction parsing
- **Device parameter syntax**: OPEN/USE accept complex, colon-delimited parameter lists inside parentheses—parser must handle nested structures generically

---

## Requirements *(mandatory)*

### Functional Requirements

#### Test Structure Requirements

- **FR-001**: Test directory structure MUST mirror MUMPS 1995 spec organization with directories for each major section (§5 Metalanguage, §6 Routine, §7 Expression, §8 Commands, §9 Charset)
- **FR-002**: Each test file MUST be named to indicate its corresponding spec section (e.g., `test_s7_1_2_local_variables.py` for §7.1.2)
- **FR-003**: Tests MUST be organized into these categories:
  - `parser/` - textX output verification
  - `asg/` - final ASG after analysis
  - `codegen/` - Python generation and execution
  - `analysis/` - internal algorithm unit tests (FOR classifier, GOTO classifier, resolver)
  - `meta/` - tooling and infrastructure tests (textX integration, parser API)
  - `cross_cutting/` - features spanning multiple commands (indirection, postconditions, timeouts)
- **FR-004**: Test files MUST include docstrings referencing the specific MUMPS spec section(s) they cover. Example format: `"""Tests for SET command parsing (§8.2.18)."""`. This applies to both stub creation and migration.
- **FR-005**: Cross-cutting features (indirection, postconditions, timeouts) MUST have dedicated test files rather than being duplicated across command tests

#### Parser Test Requirements

- **FR-006**: Parser tests MUST verify textX model structure without running semantic analysis
- **FR-007**: Parser tests MUST verify all syntactic elements are captured (command keywords, arguments, operators, literals, variables)
- **FR-008**: Parser tests MUST verify correct textX class instantiation for each grammar rule
- **FR-009**: Parser tests MUST verify proper handling of both abbreviated and full command keywords

#### ASG Test Requirements

- **FR-010**: ASG tests MUST verify final ASG state after all analysis passes (semantic analysis, reference resolution, GOTO classification, FOR analysis, variable analysis)
- **FR-011**: ASG tests MUST verify that all fields required for Python codegen are populated
- **FR-012**: ASG tests MUST verify correct type classifications (ForLoopType, GotoType, etc.)
- **FR-013**: ASG tests MUST verify reference resolution (MCall.target linked to MLabel, etc.)
- **FR-014**: ASG tests MUST verify variable scope analysis (input_variables, output_variables, variables_newed)

#### Codegen Test Requirements

- **FR-030**: Codegen tests MUST verify that generated Python code executes without errors
- **FR-031**: Codegen tests MUST verify that generated Python produces output matching expected MUMPS behavior
- **FR-032**: Codegen tests MUST cover all language features that have ASG support
- **FR-033**: Codegen tests MUST use MUMPS examples from one of these authoritative sources: `mumps-reference/`, `tests/functional/*_inref/` (YDBTest), `tests/functional/mugj/`, or `VistA-M/`
- **FR-034**: Codegen tests for unimplemented features MUST exist as stubs marked with `@pytest.mark.xfail`
- **FR-056**: Codegen test stubs MUST include comments citing the YDBTest functional suite file or MUMPS spec section that defines expected behavior

#### Stub Management Requirements

- **FR-035**: Stub tests MUST use `@pytest.mark.xfail(reason="stub: <description>")` to indicate pending implementation
- **FR-036**: Stub tests MUST use compound markers: `@pytest.mark.stub` combined with `@pytest.mark.parser`, `@pytest.mark.asg`, or `@pytest.mark.codegen`
- **FR-037**: Running `pytest` with default options MUST produce exit code 0 (all tests pass, stubs show as xfail)
- **FR-038**: Running `pytest -m "not stub"` MUST execute only implemented tests
- **FR-039**: Out-of-scope features (per limitations.md) MUST use `@pytest.mark.skip(reason="out-of-scope: <reason>")` instead of xfail
- **FR-040**: When a stub is implemented, the `@pytest.mark.stub` and `@pytest.mark.xfail` markers MUST be removed
- **FR-057**: Migration tasks MUST verify that implemented tests have had stub/xfail markers removed per FR-040

#### Coverage Tracking Requirements

- **FR-015**: Unimplemented spec sections MUST have stub test files per FR-035 marker requirements
- **FR-016**: Out-of-scope sections (per limitations.md) MUST have stub test files with `@pytest.mark.skip(reason="out-of-scope: <reason>")`
- **FR-017**: Implementation-defined features (VIEW, Z-commands) MUST have stub test files with `@pytest.mark.skip(reason="implementation-defined: <note>")` for unimplemented variants
- **FR-018**: A coverage matrix document MUST exist mapping every §1995 section to its test status
- **FR-019**: pytest collection MUST show xfail/skip reasons when running with `-v` flag

#### Backward Compatibility Requirements

- **FR-020**: System MUST parse syntax that is valid in 1977/1984/1990 standards even if superseded in 1995
- **FR-021**: Analysis phase MUST document any identified syntax differences between standard versions
- **FR-022**: Test suite MUST include specific tests for any identified backward-compatibility syntax

#### Extension Requirements

- **FR-023**: Test structure MUST accommodate YottaDB/GT.M Z-commands in a dedicated extension section
- **FR-024**: Z-commands that are implemented MUST have corresponding tests
- **FR-025**: Z-commands that are not implemented MUST be documented in the coverage matrix
- **FR-061**: Test structure MUST accommodate YottaDB/GT.M Z-functions ($Z... intrinsic functions) in the dedicated extension section
- **FR-062**: Z-functions that are implemented or referenced in the codebase MUST have corresponding tests (at minimum: $ZSTATUS, $ZLEVEL, $ZTRAP, $ZDATE, $ZSEARCH, $ZVERSION)
- **FR-063**: Z-functions that are not implemented MUST be documented in the coverage matrix with skip markers

#### Library Function Requirements (ANSI M Annex I)

- **FR-058**: Test structure MUST include stub files for ANSI M Annex I normative library functions:
  - **MATH library** (57 functions per §7.1.6.5): %ABS, %ARCCOS, %ARCCOSH, %ARCCOT, %ARCCOTH, %ARCCSC, %ARCSEC, %ARCSIN, %ARCSINH, %ARCTAN, %ARCTANH, %CABS, %CADD, %CCOS, %CDIV, %CEXP, %CLOG, %CMUL, %COMPLEX, %CONJUG, %COS, %COSH, %COT, %COTH, %CPOWER, %CSC, %CSCH, %CSIN, %CSUB, %DECDMS, %DEGRAD, %DMSDEC, %E, %EXP, %LOG, %LOG10, %MTXADD, %MTXCOF, %MTXCOPY, %MTXDET, %MTXEQU, %MTXINV, %MTXMUL, %MTXSCA, %MTXSUB, %MTXTRP, %MTXUNIT, %PI, %RADDEG, %SEC, %SECH, %SIGN, %SIN, %SINH, %SQRT, %TAN, %TANH
  - **STRING library** (6 functions per §7.1.6.6): %CRC16, %CRC32, %CRCCCITT, %FORMAT, %PRODUCE, %REPLACE
  - **CHARACTER library** (5 functions per §7.1.6.4): %COLLATE, %COMPARE, %LOWER, %PATCODE, %UPPER
- **FR-059**: Library function stubs MUST be organized under `test_s7_1_6_5_library_functions_*.py` files within parser/asg/codegen directories
- **FR-060**: Library function stubs MUST use `@pytest.mark.xfail` since these are normative but rarely implemented in real codebases

#### Out-of-Scope Features (per limitations.md)

- **FR-055**: The following MUMPS 1995 spec sections are explicitly out-of-scope and MUST have skip-marked test files (not xfail stubs):
  - §5 Metalanguage (informative, no executable semantics)
  - §6.3.4 Event Processing (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
  - §6.4 Embedded Programs
  - THEN command (zero real-world usage)
  - ASSIGN command (event processing)
  - RLOAD/RSAVE commands (routine library management)
  - ^$LIBRARY, ^$EVENT SSVNs (related to out-of-scope features)

#### Language Semantic Requirements

- **FR-046**: Tests for naked global references (`^(sub)`) MUST verify sequence-dependent state transitions based on prior global references
- **FR-047**: Tests for `$TEST` MUST cover all commands that modify it: argumentless IF, and OPEN/READ/JOB/LOCK with timeouts
- **FR-048**: Tests for NEW command MUST include Exclusive NEW form `NEW (X,Y)` with inverse scoping verification
- **FR-049**: Tests for postconditions MUST distinguish command-level (`SET:C X=1,Y=2` gates both) from argument-level (`DO L1:C1,L2:C2` independent)
- **FR-050**: Tests for binary operators MUST verify strict left-to-right evaluation without precedence (e.g., `2+3*4=20`)
- **FR-051**: Tests for transaction commands MUST cover nested TSTART with `$TLEVEL` tracking
- **FR-052**: Tests for Structured System Variables (SSVNs per §7.1.3) MUST cover parsing and ASG representation for: `^$JOB`, `^$ROUTINE`, `^$GLOBAL`, `^$LOCK`, `^$DEVICE`, `^$CHARACTER`, `^$SYSTEM`, `^$Z` (§7.1.3.8 implementation-defined), and `^$Y` (§7.1.3.10 implementation-defined). Note: `^$LIBRARY` and `^$EVENT` are out-of-scope per limitations.md but MUST have skip-marked test files. (Special variables like `$DEVICE`, `$IOREFERENCE`, `$PIOREFERENCE` are covered under FR-028/§7.1.4.10, not here.)
- **FR-053**: Analysis function unit tests (FOR classifier, GOTO classifier, resolver) MUST be organized in a dedicated `analysis/` directory since they test internal algorithms, not spec compliance
- **FR-054**: Non-spec-aligned tooling tests (textX integration, parse result tracking) MUST be organized in a dedicated `meta/` directory
- **FR-029**: Codegen test fixtures MUST provide a helper function `compare_output_to_functional_suite(routine_name: str, actual_output: str, suite: str = "mugj") -> ComparisonResult` where `ComparisonResult` has `passed: bool`, `expected: str`, `diff: str | None`. Comparison rules: (a) trailing whitespace is ignored, (b) floating-point numbers match if within 1e-9 relative tolerance OR 1e-12 absolute tolerance for values < 1e-6, (c) line order matters. Supported suites: `tests/functional/*_inref/`, `tests/functional/mugj/`

#### Migration Requirements

- **FR-026**: All existing tests in `tests/unit/` MUST be migrated to the new structure or explicitly marked as superseded
- **FR-027**: Migration MUST preserve all test assertions and coverage. Validation: post-migration test count MUST equal or exceed pre-migration count, AND a diff of test function names MUST show no unaccounted removals
- **FR-028**: Migration MUST not break CI/CD pipelines during transition

#### Documentation Requirements

- **FR-041**: `docs/testing.md` MUST be updated to describe the new spec-aligned test structure
- **FR-042**: `docs/testing.md` MUST document the three-level testing approach (parser, asg, codegen)
- **FR-043**: `docs/testing.md` MUST document the stub/xfail workflow for pending tests
- **FR-044**: `docs/testing.md` MUST include the marker usage table and common pytest commands
- **FR-045**: A coverage audit script MUST be created as `utils/audit_tests.py` that dynamically scans test files and generates coverage reports. The script MUST:
  - Accept optional `--section` argument to filter by spec section (e.g., `--section s7` or `--section s8_commands`)
  - Output summary counts per spec section: total tests, passed, xfail stubs, skipped
  - Show status for each test category (parser, asg, codegen)
  - Generate markdown table output suitable for docs/coverage-matrix.md
  - Exit with non-zero status if any expected sections are missing test files

### Key Entities

- **Spec Section**: A numbered section from ANSI M X11.1-1995 (e.g., §7.1.2 Local variable name)
- **Test Category**: One of: "parser" (textX output), "asg" (final ASG after analysis), "codegen" (Python generation/execution), "analysis" (internal algorithm tests—no marker required), "meta" (tooling/infrastructure tests—no marker required), "cross_cutting" (features spanning multiple commands—uses appropriate parser/asg/codegen marker)
- **Test Status**: One of: implemented (passes), stub (xfail), out-of-scope (skip), implementation-defined (skip)
- **Test Source**: Origin of test code: original, mumps-reference example, YDBTest, VistA
- **Pytest Markers**: `@pytest.mark.stub`, `@pytest.mark.parser`, `@pytest.mark.asg`, `@pytest.mark.codegen`, `@pytest.mark.xfail`, `@pytest.mark.skip`

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of MUMPS 1995 spec sections (§5-§9) are accounted for in the test structure (tested, xfail stub, or skip-marked per FR-055)
- **SC-002**: All existing unit tests are migrated without loss of coverage (test count ≥ current count)
- **SC-003**: Running `pytest --collect-only tests/unit/` shows clear categorization of all tests by spec section
- **SC-004**: Running `uv run python utils/audit_tests.py` exits with status 0 and shows all sections covered
- **SC-005**: All implemented commands have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-006**: All implemented intrinsic functions have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-007**: All implemented operators have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-008**: All implemented special variables have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-009**: Cross-cutting features (indirection, postconditions, timeouts) have exhaustive dedicated tests
- **SC-010**: YottaDB Z-commands that are implemented have corresponding tests
- **SC-011**: Backward compatibility analysis is documented with specific syntax differences identified (P2—may be deferred)
- **SC-012**: VistA codebase parses without syntax errors due to standard version differences (P2—may be deferred)
- **SC-013**: Running `pytest` with default options produces exit code 0 (green CI)
- **SC-014**: Running `pytest -m "not stub"` executes only implemented tests
- **SC-015**: Every spec section has stubs at all three levels (parser, asg, codegen) from initial structure creation
- **SC-016**: `docs/testing.md` accurately describes the new test organization and workflows
- **SC-017**: `utils/audit_tests.py` exists and can generate `docs/coverage-matrix.md` dynamically
- **SC-018**: Language semantic edge cases (naked refs, $TEST, Exclusive NEW, postcondition scope, L-to-R eval, transaction nesting) have dedicated tests
- **SC-019**: Non-spec-aligned tests (analysis functions, tooling/meta) are organized separately from spec-aligned tests

---

## Assumptions

- The MUMPS 1995 ANSI standard is the authoritative reference, with earlier standards consulted for backward compatibility only
- Test code examples can be adapted from `mumps-reference/examples__*.md`, YDBTest functional suites (`tests/functional/*_inref/`), MUGJ suite (`tests/functional/mugj/`), and VistA codebase under appropriate licensing
- The existing analysis passes (semantic analyzer, resolver, goto_analysis, for_analysis, variables) represent the complete set needed for Python codegen
- Z-command support follows YottaDB/GT.M semantics where applicable
- The spec section numbering in `mumps-reference/` files accurately reflects the 1995 standard structure

---

## MUMPS 1995 Spec Section Reference

The test structure will map to these major sections:

### §5 Metalanguage (Informative)
- §5.1 BNF notation and operators (out-of-scope per FR-055: informative, no executable semantics)

### §6 Routine Structure
- §6.1 Routine head (routinehead)
- §6.2 Routine body (routinebody)
  - §6.2.1 Level line
  - §6.2.2 Formal line
  - §6.2.3 Label
  - §6.2.4 Label separator
  - §6.2.5 Line body
- §6.3 Routine execution
  - §6.3.1 Generic indirection / Transaction processing (note: 1995 spec has duplicate §6.3.1 numbering)
  - §6.3.2 Error processing
  - §6.3.4 Event processing (out-of-scope per FR-055: ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
- §6.4 Embedded programs (out-of-scope per FR-055)

### §7 Expressions
- §7.1 Expression atom (expratom)
  - §7.1.1 Values and Variables
  - §7.1.2 Variable names (glvn, lvn, gvn)
  - §7.1.3 Structured system variables (ssvn): ^$CHARACTER (§7.1.3.1), ^$DEVICE (§7.1.3.2), ^$EVENT/^$GLOBAL (§7.1.3.3—duplicate numbering), ^$JOB (§7.1.3.4), ^$LOCK (§7.1.3.5), ^$LIBRARY/^$ROUTINE (§7.1.3.6—duplicate numbering), ^$SYSTEM (§7.1.3.7), ^$Z (§7.1.3.8), ^$Y (§7.1.3.10). Note: ^$LIBRARY/^$EVENT out-of-scope per FR-055.
  - §7.1.4 Expression items (literals, extrinsic functions, special variables)
    - §7.1.4.8 Extrinsic functions ($$label)
    - §7.1.4.10 Special variables ($DEVICE, $ECODE, $EREF, $ESTACK, $ETRAP, $HOROLOG, $IO, $IOREFERENCE, $JOB, $KEY, $PDISPLAY, $PIOREFERENCE, $PRINCIPAL, $QUIT, $REFERENCE, $STACK, $STORAGE, $SYSTEM, $TEST, $TLEVEL, $TRESTART, $X, $Y, $Z)
  - §7.1.5 Intrinsic functions ($ASCII, $CHAR, $DATA, $DEXTRACT [deprecated—§7.1.5.4], $DPIECE [deprecated—§7.1.5.5], $EXTRACT, $FIND, $FNUMBER, $GET, $HOROLOG [function form—§7.1.5.10], $JUSTIFY, $LENGTH, $MUMPS [§7.1.5.13], $NAME, $NEXT [deprecated—§7.1.5.14, use $ORDER], $ORDER, $PIECE, $QLENGTH, $QSUBSCRIPT, $QUERY, $RANDOM, $REVERSE, $SELECT, $STACK, $TEXT, $TRANSLATE, $TYPE [§7.1.5.25], $VIEW, $Z [implementation-defined—§7.1.5.23])
  - §7.1.6 M[UMPS] Standard Library (CHARACTER, MATH, STRING libraries per Annex I)
- §7.2 Operators
  - §7.2.1 Unary operators
  - §7.2.1 Binary operators (concatenation, arithmetic)
  - §7.2.2 Truth operators (relational, logical)
    - §7.2.2.1 Relational operators (=, <, >, [, ], ]])
    - §7.2.2.2 Numeric relations
    - §7.2.2.3 String relations (contains, follows, sorts-after)
    - §7.2.2.4 Logical operators (&, !, ')
  - §7.2.3 Pattern match operator (?)
- §7.3 Indirection (canonical location: §7.1.4.12 namevalue in 1995 spec; §7.3 is a logical grouping for test organization)
  - Name indirection (@)
  - Argument indirection
  - Pattern indirection

### §8 Commands
- §8.1 General command rules
  - §8.1.1 Spaces in commands
  - §8.1.2 Comments
  - §8.1.3 Command argument indirection
  - §8.1.4 Postconditions
  - §8.1.5 Timeouts
  - §8.1.6 Line references
  - §8.1.7 Parameter passing
  - §8.1.8 Object usage (limited scope)
- §8.2 Command definitions
  - §8.2.1 BREAK
  - §8.2.2 CLOSE
  - §8.2.3 DO
  - §8.2.4 ELSE
  - §8.2.5 FOR
  - §8.2.6 GOTO
  - §8.2.7 HALT
  - §8.2.8 HANG
  - §8.2.9 IF
  - §8.2.10 JOB
  - §8.2.11 KILL
  - §8.2.12 LOCK
  - §8.2.13 MERGE
  - §8.2.14 NEW
  - §8.2.15 OPEN
  - §8.2.16 QUIT
  - §8.2.17 READ
  - §8.2.18 SET
  - §8.2.19 TCOMMIT
  - §8.2.20 TRESTART
  - §8.2.21 TROLLBACK
  - §8.2.22 TSTART
  - §8.2.23 USE
  - §8.2.24 VIEW
  - §8.2.25 WRITE
  - §8.2.26 XECUTE
  - §8.2.27 Z-commands (implementation-defined)
  - §8.2.28 RLOAD (out-of-scope)
  - §8.2.29 RSAVE (out-of-scope)
  - §8.2.32 THEN (out-of-scope)
  - Extended KILL commands (numbered in parallel to transaction commands):
    - KSUBSCRIPTS (shares §8.2.20 numbering with TRESTART)
    - KVALUE (shares §8.2.21 numbering with TROLLBACK)
  - Event processing commands (out-of-scope): ABLOCK, ASSIGN, ASTART, ASTOP, AUNBLOCK, ESTART, ESTOP, ETRIGGER
- §8.3 Device parameters

### §9 Character Set Profile (Informative)
- §9.1 Character set definitions

### Extensions (Non-Standard)
- YottaDB Z-commands: ZBREAK, ZCOMPILE, ZCONTINUE, ZEDIT, ZGOTO, ZHELP, ZLINK, ZMESSAGE, ZPRINT, ZSHOW, ZSTEP, ZSYSTEM, ZWRITE, ZKILL, ZWITHDRAW, ZHALT, ZALLOCATE, ZDEALLOCATE, ZTRIGGER
- YottaDB Z-functions: Implementation-defined `$Z...` functions tested in extensions section. Key functions include: $ZASCII, $ZCHAR, $ZCOLLATE, $ZCONVERT, $ZDATA, $ZDATE, $ZEXTRACT, $ZFIND, $ZINCR, $ZIO, $ZJOB, $ZLENGTH, $ZLEVEL, $ZMESSAGE, $ZMODE, $ZNAME, $ZNEXT, $ZORDER, $ZPARSE, $ZPIECE, $ZPOSITION, $ZPREVIOUS, $ZSEARCH, $ZSOCKET, $ZSTATUS, $ZTRANSLATE, $ZTRAP, $ZTRIGGER, $ZVERSION, $ZWIDTH, $ZWRITE

---

## Dependencies

- **Spec 001** (textX Semantic Graph): The ASG structure and analysis passes defined there are the basis for ASG-level testing
- **docs/limitations.md**: Defines which commands are out-of-scope (referenced by FR-016, FR-039)
- **docs/testing.md**: Current testing documentation (to be updated)
- **mumps-reference/**: Contains spec text and examples for test creation
- **tests/functional/**: YDBTest validation suites (MUGJ, MVTS, basic_inref, merge_inref, etc.) providing expected behavior baselines
- **YDBTest/**: Source YottaDB test files
- **VistA-M/**: Contains production MUMPS code for compatibility validation

---

## Appendix A: Stub Test Pattern Examples

### Implemented Test (No Markers)

```python
"""Tests for SET command - §8.2.18"""

class TestSetCommandParser:
    """Parser-level tests for SET command."""
    
    @pytest.mark.parser
    def test_simple_set(self, command_metamodel):
        """SET X=1 - basic assignment."""
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        assert model is not None
        assert len(model.assignments) == 1
```

### Stub Test (Pending Implementation)

```python
"""Tests for MERGE command codegen - §8.2.13"""

class TestMergeCommandCodegen:
    """Codegen tests for MERGE command."""
    
    @pytest.mark.stub
    @pytest.mark.codegen
    @pytest.mark.xfail(reason="stub: MERGE codegen not yet implemented")
    def test_merge_local_to_local(self):
        """MERGE A=B - merge local array to another local."""
        mumps_code = "TEST S B(1)=1,B(2)=2 M A=B"
        # When implemented:
        # result = transpile_and_execute(mumps_code)
        # assert result.locals["A"] == {"1": "1", "2": "2"}
        pytest.fail("MERGE codegen not implemented")
```

### Out-of-Scope Test (Skip)

```python
"""Tests for ABLOCK command - §8.2.x (Event Processing)"""

@pytest.mark.skip(reason="out-of-scope: Event processing commands not implemented per limitations.md")
class TestABlockCommand:
    """ABLOCK command is not implemented."""
    
    def test_ablock_basic(self):
        pass
```

### Marker Usage Summary

| Marker | When to Use |
|--------|-------------|
| `@pytest.mark.parser` | Tests verifying textX parser output |
| `@pytest.mark.asg` | Tests verifying analyzed ASG structure |
| `@pytest.mark.codegen` | Tests verifying Python generation/execution |
| `@pytest.mark.stub` | Test is a placeholder awaiting implementation |
| `@pytest.mark.xfail(reason="stub: ...")` | Combined with `stub` for pending tests |
| `@pytest.mark.skip(reason="out-of-scope: ...")` | Feature will never be implemented |

### Running Tests

```bash
# Run all tests (stubs show as xfail, suite passes)
uv run pytest

# Run only implemented tests
uv run pytest -m "not stub"

# Run only parser tests
uv run pytest -m parser

# Run only codegen stubs to see what's pending
uv run pytest -m "stub and codegen" --collect-only

# Run implemented codegen tests only
uv run pytest -m "codegen and not stub"
```
