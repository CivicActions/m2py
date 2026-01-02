# Feature Specification: MUMPS Spec-Aligned Unit Test Organization

**Feature Branch**: `002-spec-unit-test-organization`  
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
- Actual MUMPS runtime execution (codegen tests verify generated Python behavior, not MUMPS interpreter behavior)

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

**Independent Test**: Generate a coverage report from test markers and compare against the full spec section list.

**Acceptance Scenarios**:

1. **Given** the complete MUMPS 1995 spec table of contents, **When** compared to test files, **Then** every section is accounted for (tested, skip-marked, or documented as out-of-scope)
2. **Given** a test file with `@pytest.mark.skip(reason="not-implemented")`, **When** the coverage report runs, **Then** it appears in the "pending" category with the reason
3. **Given** the limitations.md exclusions, **When** the coverage report runs, **Then** those sections appear as "out-of-scope" not "missing"

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

**Acceptance Scenarios**:

1. **Given** a MUMPS routine with SET and WRITE commands, **When** transpiled and executed, **Then** the Python output matches expected MUMPS output
2. **Given** a MUMPS FOR loop, **When** transpiled and executed, **Then** the Python loop iterates correctly with proper variable scoping
3. **Given** a MUMPS intrinsic function call, **When** transpiled and executed, **Then** the Python function produces identical results
4. **Given** a codegen stub test (marked xfail), **When** implementation is completed, **Then** the test transitions from xfail to passing

---

### User Story 8 - Manage Test Stubs with xfail for 100% Suite Pass Rate (Priority: P1)

As a developer, I want all unimplemented tests to use `pytest.xfail` markers so that the test suite always shows 100% passing while clearly indicating what's pending implementation.

**Why this priority**: A green CI pipeline is essential for developer confidence. Using xfail allows us to have complete coverage stubs while maintaining a passing suite.

**Independent Test**: Run `pytest` and verify all tests pass (implemented tests pass, stubs show as xfail).

**Acceptance Scenarios**:

1. **Given** a stub test marked with `@pytest.mark.xfail(reason="stub: needs implementation")`, **When** pytest runs, **Then** it shows as "xfail" (expected failure) and the suite passes
2. **Given** a stub test that gets implemented, **When** the implementation is complete, **Then** removing the xfail marker causes the test to pass normally
3. **Given** the full test suite with stubs, **When** `pytest` runs with default options, **Then** exit code is 0 (success)
4. **Given** compound markers `@pytest.mark.stub` and `@pytest.mark.codegen`, **When** running `pytest -m "not stub"`, **Then** only implemented tests run

---

### Edge Cases

- **Syntax ambiguity**: MUMPS allows abbreviated commands—how do we test that `S` parses identically to `SET`?
- **Indirection everywhere**: Many constructs support `@` indirection—how do we avoid duplicating indirection tests across every command?
- **Argumentless commands**: Commands like argumentless DO, FOR, and NEW have special semantics—ensure they're tested distinctly from argument forms
- **Multi-argument commands**: Commands accepting multiple arguments (SET, WRITE, KILL) need tests for both single and multiple argument forms
- **Postcondition variations**: Command postconditions vs argument postconditions have different rules per §8.1.4
- **Pattern match complexity**: Pattern syntax (§7.2.5) is complex enough to warrant exhaustive separate testing

---

## Key Language Nuances *(guidance for test authors)*

The following MUMPS language features have subtle semantics that require dedicated test coverage beyond simple parsing verification:

### Naked Global References (`^(subscripts)`)
**Spec Reference**: §7.1.2.1 (gvn), multiple command sections  
**Challenge**: The "naked indicator" is runtime state updated by *any* global reference. `^(subscript)` relies on the *last* global reference context.  
**Test Strategy**: Sequence-dependent tests (e.g., `SET ^A(1)=1 SET ^(2)=2` must verify naked indicator tracks correctly). Codegen tests must verify Python runtime maintains naked indicator state.  
**Status**: Parser/ASG support implemented (`MNakedGlobal`), codegen requires runtime tracking.

### `$TEST` Special Variable Side Effects
**Spec Reference**: §7.1.7, §8.2.9 (IF), §8.2.12 (LOCK), §8.2.15 (OPEN), §8.2.17 (READ)  
**Challenge**: `$TEST` is set by argumentless IF, and by OPEN/READ/JOB/LOCK commands *with timeouts*. It drives ELSE behavior.  
**Test Strategy**: Tests for each command that sets `$TEST` must verify the side effect. ELSE tests must verify dependency on `$TEST` from multiple sources.  
**Status**: Parser support exists; codegen must track `$TEST` runtime state.

### Exclusive NEW (`NEW (X,Y)`)
**Spec Reference**: §8.2.14  
**Challenge**: Exclusive NEW stacks *all variables except* the named ones—inverse of normal scoping. Static analysis cannot fully determine affected variables.  
**Test Strategy**: Parser tests for syntax; ASG tests verify `MNewStatement.exclusive=True` and `except_list` populated; codegen tests verify runtime scope behavior.  
**Status**: Fully implemented and tested (see `test_classifier.py`).

### Command vs. Argument Postconditions
**Spec Reference**: §8.1.4  
**Challenge**: `SET:Cond X=1,Y=2` (command postcondition) gates both assignments. `DO L1:C1,L2:C2` (argument postconditions) are independent per argument.  
**Test Strategy**: Dedicated tests for postcondition scope boundaries at both levels for commands that support both forms.  
**Status**: Parser distinguishes them; ASG/codegen tests needed.

### Transaction Processing Nesting
**Spec Reference**: §8.2.19-22, §6.3.2  
**Challenge**: `TSTART` can be nested. `$TLEVEL` tracks depth. `TROLLBACK` can roll back one level or all.  
**Test Strategy**: Parser tests for nested TSTART/TCOMMIT; ASG tests for `$TLEVEL` tracking; codegen tests for rollback behavior at different nesting levels.  
**Status**: Parser support exists; codegen scope limited.

### Device Parameter Syntax
**Spec Reference**: §8.3, §8.2.15 (OPEN), §8.2.23 (USE)  
**Challenge**: Device parameters use complex, implementation-defined syntax with nested colons and parentheses (e.g., `OPEN "DEV":(param1:param2:param3)`).  
**Test Strategy**: Parser tests must handle parameter strings generically without choking on internal delimiters.  
**Status**: Basic support exists; exhaustive device parameter testing deferred.

### Structured System Variables (SSVNs)
**Spec Reference**: §7.1.3  
**Challenge**: `^$JOB`, `^$DEVICE`, `^$ROUTINE` look like globals but have fixed schema-defined subscripts.  
**Test Strategy**: Parser must distinguish SSVNs from standard globals; ASG must use correct node type.  
**Status**: Parser support exists (`MSSVN` class).

### Strict Left-to-Right Operator Evaluation
**Spec Reference**: §7.2  
**Challenge**: MUMPS has NO operator precedence—all operators evaluate strictly left-to-right. `2+3*4` equals `20`, not `14`.  
**Test Strategy**: Expression tests must verify left-to-right evaluation without implicit precedence.  
**Status**: Parser captures correctly; codegen must generate Python with explicit parentheses.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Test Structure Requirements

- **FR-001**: Test directory structure MUST mirror MUMPS 1995 spec organization with directories for each major section (§5 Metalanguage, §6 Routine, §7 Expression, §8 Commands, §9 Charset)
- **FR-002**: Each test file MUST be named to indicate its corresponding spec section (e.g., `test_s7_1_2_local_variables.py` for §7.1.2)
- **FR-003**: Tests MUST be organized into three categories: `parser/` (textX output), `asg/` (final ASG after analysis), and `codegen/` (Python generation and execution)
- **FR-004**: Test files MUST include docstrings referencing the specific MUMPS spec section(s) they cover
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
- **FR-033**: Codegen tests MUST use realistic MUMPS examples (from mumps-reference, YDBTest, or VistA where appropriate)
- **FR-034**: Codegen tests for unimplemented features MUST exist as stubs marked with `@pytest.mark.xfail`

#### Stub Management Requirements

- **FR-035**: Stub tests MUST use `@pytest.mark.xfail(reason="stub: <description>")` to indicate pending implementation
- **FR-036**: Stub tests MUST use compound markers: `@pytest.mark.stub` combined with `@pytest.mark.parser`, `@pytest.mark.asg`, or `@pytest.mark.codegen`
- **FR-037**: Running `pytest` with default options MUST produce exit code 0 (all tests pass, stubs show as xfail)
- **FR-038**: Running `pytest -m "not stub"` MUST execute only implemented tests
- **FR-039**: Out-of-scope features (per limitations.md) MUST use `@pytest.mark.skip(reason="out-of-scope: <reason>")` instead of xfail
- **FR-040**: When a stub is implemented, the `@pytest.mark.stub` and `@pytest.mark.xfail` markers MUST be removed

#### Coverage Tracking Requirements

- **FR-015**: Unimplemented spec sections MUST have stub test files with `@pytest.mark.xfail` and `@pytest.mark.stub` markers
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

#### Migration Requirements

- **FR-026**: All existing tests in `tests/unit/` MUST be migrated to the new structure or explicitly marked as superseded
- **FR-027**: Migration MUST preserve all test assertions and coverage
- **FR-028**: Migration MUST not break CI/CD pipelines during transition

#### Documentation Requirements

- **FR-041**: `docs/testing.md` MUST be updated to describe the new spec-aligned test structure
- **FR-042**: `docs/testing.md` MUST document the three-level testing approach (parser, asg, codegen)
- **FR-043**: `docs/testing.md` MUST document the stub/xfail workflow for pending tests
- **FR-044**: `docs/testing.md` MUST include the marker usage table and common pytest commands
- **FR-045**: Coverage matrix document MUST be created in `docs/` (e.g., `docs/coverage-matrix.md`)

#### Language Nuance Requirements

- **FR-046**: Naked global references MUST have dedicated tests verifying runtime context tracking across sequences of global operations
- **FR-047**: `$TEST` side effects MUST be tested for each command that modifies it (argumentless IF, OPEN/READ/JOB/LOCK with timeouts)
- **FR-048**: Exclusive NEW syntax (`NEW (X,Y)`) MUST have tests at all three levels verifying inverse scoping behavior
- **FR-049**: Command vs. argument postcondition scope differences MUST have dedicated comparative tests
- **FR-050**: Left-to-right operator evaluation (no precedence) MUST have tests verifying expressions like `2+3*4` produce MUMPS-correct results
- **FR-051**: Transaction nesting (TSTART within TSTART) MUST have parser and ASG tests for nested structures

### Key Entities

- **Spec Section**: A numbered section from ANSI M X11.1-1995 (e.g., §7.1.2 Local variable name)
- **Test Category**: One of: "parser" (textX output), "asg" (final ASG after analysis), or "codegen" (Python generation/execution)
- **Test Status**: One of: implemented (passes), stub (xfail), out-of-scope (skip), implementation-defined (skip)
- **Test Source**: Origin of test code: original, mumps-reference example, YDBTest, VistA
- **Pytest Markers**: `@pytest.mark.stub`, `@pytest.mark.parser`, `@pytest.mark.asg`, `@pytest.mark.codegen`, `@pytest.mark.xfail`, `@pytest.mark.skip`

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of MUMPS 1995 spec sections (§5-§9) are accounted for in the test structure (tested, xfail stub, or skip-marked)
- **SC-002**: All existing unit tests are migrated without loss of coverage (test count ≥ current count)
- **SC-003**: Running `pytest --collect-only tests/unit/` shows clear categorization of all tests by spec section
- **SC-004**: Coverage matrix document accurately reflects test status for every spec section
- **SC-005**: All implemented commands have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-006**: All implemented intrinsic functions have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-007**: All implemented operators have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-008**: All implemented special variables have parser-level, ASG-level, and codegen-level tests (or stubs)
- **SC-009**: Cross-cutting features (indirection, postconditions, timeouts) have exhaustive dedicated tests
- **SC-010**: YottaDB Z-commands that are implemented have corresponding tests
- **SC-011**: Backward compatibility analysis is documented with specific syntax differences identified
- **SC-012**: VistA codebase parses without syntax errors due to standard version differences
- **SC-013**: Running `pytest` with default options produces exit code 0 (green CI)
- **SC-014**: Running `pytest -m "not stub"` executes only implemented tests
- **SC-015**: Every spec section has stubs at all three levels (parser, asg, codegen) from initial structure creation
- **SC-016**: `docs/testing.md` accurately describes the new test organization and workflows
- **SC-017**: `docs/coverage-matrix.md` exists and matches actual test coverage status
- **SC-018**: Language nuance tests exist for: naked globals, `$TEST` side effects, exclusive NEW, postcondition scope, left-to-right evaluation, transaction nesting

---

## Assumptions

- The MUMPS 1995 ANSI standard is the authoritative reference, with earlier standards consulted for backward compatibility only
- Test code examples can be adapted from `mumps-reference/examples__*.md`, YDBTest suite, and VistA codebase under appropriate licensing
- The existing analysis passes (semantic analyzer, resolver, goto_analysis, for_analysis, variables) represent the complete set needed for Python codegen
- Z-command support follows YottaDB/GT.M semantics where applicable
- The spec section numbering in `mumps-reference/` files accurately reflects the 1995 standard structure

---

## MUMPS 1995 Spec Section Reference

The test structure will map to these major sections:

### §5 Metalanguage (Informative)
- §5.1 BNF notation and operators

### §6 Routine Structure
- §6.1 Routine head (routinehead)
- §6.2 Routine body (routinebody)
  - §6.2.1 Level line
  - §6.2.2 Formal line
  - §6.2.3 Label
  - §6.2.4 Label separator
  - §6.2.5 Line body
- §6.3 Routine execution
  - §6.3.1 Generic indirection
  - §6.3.2 Transaction processing (limited scope)
  - §6.3.3 Error processing
  - §6.3.4 Event processing (out-of-scope)
- §6.4 Embedded programs (out-of-scope)

### §7 Expressions
- §7.1 Expression atom (expratom)
  - §7.1.1 Values and Variables
  - §7.1.2 Variable names (glvn, lvn, gvn)
  - §7.1.3 Structured system variables (ssvn)
  - §7.1.4 Expression items (literals)
  - §7.1.5 Intrinsic functions ($ASCII through $VIEW)
  - §7.1.6 Extrinsic functions ($$label)
  - §7.1.7 Special variables ($DEVICE through $Y)
- §7.2 Operators
  - §7.2.1 Unary operators
  - §7.2.2 Binary operators (arithmetic, string, relational, logical)
  - §7.2.3 String operators (_, [, ], ]])
  - §7.2.4 Relational operators
  - §7.2.5 Pattern match operator (?)
- §7.3 Indirection
  - §7.3.1 Name indirection
  - §7.3.2 Argument indirection
  - §7.3.3 Pattern indirection

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
  - §8.2.19-22 Transaction commands (TCOMMIT, TRESTART, TROLLBACK, TSTART)
  - §8.2.23 USE
  - §8.2.24 VIEW
  - §8.2.25 WRITE
  - §8.2.26 XECUTE
  - §8.2.27 Z-commands (implementation-defined)
- §8.3 Device parameters

### §9 Character Set Profile (Informative)
- §9.1 Character set definitions

### Extensions (Non-Standard)
- YottaDB Z-commands (ZBREAK, ZCOMPILE, ZCONTINUE, ZEDIT, ZGOTO, ZHELP, ZLINK, ZMESSAGE, ZPRINT, ZSHOW, ZSTEP, ZSYSTEM, ZWRITE, etc.)

---

## Dependencies

- **Spec 001** (textX Semantic Graph): The ASG structure and analysis passes defined there are the basis for ASG-level testing
- **docs/limitations.md**: Defines which commands are out-of-scope
- **docs/testing.md**: Current testing documentation (to be updated)
- **mumps-reference/**: Contains spec text and examples for test creation
- **YDBTest/**: Contains real-world MUMPS code for test examples
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
- **VistA-M/**: Contains production MUMPS code for compatibility validation
