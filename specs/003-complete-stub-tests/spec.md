# Feature Specification: Complete Stub Tests

**Feature Branch**: `003-complete-stub-tests`  
**Created**: January 4, 2026  
**Status**: Draft  
**Input**: User description: "Complete all remaining stub unit tests and implement any parsing or ASG analysis gaps discovered. Analyze stubs, prioritize by code coverage, group into batches, and systematically implement tests following a validation process."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Parser Stub Tests (Priority: P1)

As a developer validating the MUMPS parser, I want all parser stub tests to be implemented so that I can verify the parser correctly handles every MUMPS language construct defined in the 1995 ANSI spec.

**Why this priority**: Parser tests form the foundation - ASG and codegen tests depend on correct parsing. There are ~1,620 stub tests remaining. Parser stubs should be completed first as they provide the base validation layer.

**Independent Test**: Can be tested by running `uv run pytest tests/unit/parser/ -v` and verifying all tests pass (no xfail markers remaining).

**Acceptance Scenarios**:

1. **Given** a parser stub test for a MUMPS construct, **When** the test is implemented with proper assertions, **Then** the test validates the parser output matches the expected AST structure
2. **Given** an existing parser implementation, **When** stubs are converted to real tests, **Then** any parser bugs discovered are fixed and documented
3. **Given** a MUMPS language feature from the spec, **When** test examples are sourced from MUGJ/YDB/VistA, **Then** the tests use realistic MUMPS code

---

### User Story 2 - Complete ASG Stub Tests (Priority: P2)

As a developer building the semantic analysis layer, I want all ASG stub tests implemented so that I can verify the Abstract Semantic Graph correctly captures all semantic information needed for Python code generation.

**Why this priority**: ASG tests validate the semantic analysis phase. Many ASG tests already pass (~1,562 implemented), but stubs remain for complex features like indirection, transaction processing, and error handling.

**Independent Test**: Can be tested by running `uv run pytest tests/unit/asg/ -v` and verifying all tests pass.

**Acceptance Scenarios**:

1. **Given** an ASG stub test, **When** the test is implemented, **Then** it validates the ASG structure captures all semantic information from the parsed MUMPS
2. **Given** a MUMPS construct with complex semantics (indirection, transactions), **When** the ASG test is implemented, **Then** the ASG contains sufficient information for code generation
3. **Given** the validate_asg.py utility, **When** checking ASG quality for test inputs, **Then** the ASG meets quality requirements for Python generation

---

### User Story 3 - Codegen Tests (OUT OF SCOPE)

Codegen stub tests are **explicitly out of scope** for spec 003. These will be addressed in a future specification after parser and ASG validation is complete.

**Rationale**: Codegen tests depend on correct parsing and ASG generation. Completing parser and ASG tests first establishes a solid foundation and maximizes regression protection before tackling code generation

---

### User Story 4 - Track Progress via Coverage Matrix (Priority: P1)

As a project maintainer, I want the coverage matrix to accurately reflect test completion status so that I can track progress and identify gaps.

**Why this priority**: The coverage matrix is essential for planning and tracking. It should be updated as tests are completed.

**Independent Test**: Can be tested by running `uv run python utils/audit_tests.py --output docs/coverage-matrix.md` and verifying the matrix reflects current state.

**Acceptance Scenarios**:

1. **Given** a completed stub test, **When** the coverage matrix is regenerated, **Then** the test shows as ✅ instead of 🚧
2. **Given** the coverage matrix, **When** viewing the summary, **Then** implemented test count increases and stub count decreases
3. **Given** daily progress, **When** the matrix is updated, **Then** clear progress toward 100% coverage is visible

---

### Edge Cases

- What happens when a stub test reveals a parser bug? Document and fix the bug, then complete the test.
- What happens when MUMPS spec is ambiguous? Use MUGJ/YDB behavior as authoritative reference.
- What happens when a test requires unimplemented ASG analysis? Implement the analysis, then complete the test.
- How do we handle out-of-scope features (event processing, embedded programs)? Mark as skipped with documentation.
- What happens when existing tests have incorrect assertions? Refine tests based on spec validation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All parser stub tests MUST be converted to implemented tests with proper assertions
- **FR-002**: All ASG stub tests MUST be converted to implemented tests validating semantic graph structure
- **FR-003**: Codegen stub tests are OUT OF SCOPE for this spec (deferred to later work)
- **FR-004**: Tests MUST use example MUMPS code from authoritative sources (MUGJ, YDB, VistA)
- **FR-005**: Parser bugs discovered MUST be fixed before marking tests as complete
- **FR-006**: ASG analysis gaps discovered MUST be implemented before marking tests as complete
- **FR-007**: Coverage matrix MUST be regenerated per-batch (after each batch completion, aligns with FR-010 step 8)
- **FR-008**: Tests MUST be prioritized by code coverage impact (coverage-first strategy) - prioritize stubs testing currently-untested code paths to maximize regression protection before making implementation changes
- **FR-009**: Tests MUST be grouped into logical batches with the following constraints:
  - Batch sizes: minimum 3, maximum 15 stubs per batch
  - Related tests grouped together to enable learning transfer between tests
  - Simpler/routine tests (likely already implemented) → larger batches (10-15)
  - Complex/abstract features (e.g., indirection, transactions) → smaller focused batches (3-5)
  - Detailed batch sizing determined during planning research phase
- **FR-010**: Each test implementation MUST follow the MUMPS-spec-driven validation process:
  1. **Research**: Read MUMPS reference (`mumps-reference/`) carefully to understand the spec semantics
  2. **Find Examples**: Search for example content in order: MUGJ (`YDBTest/mugj/`) → YDB test suite → VistA codebase. Use examples to validate spec understanding.
  3. **Evaluate ASG Quality**: Test current parsing/ASG with `validate_asg.py` to assess if ASG meets quality requirements for Python code generation. Use this to understand what the ASG SHOULD contain (which may differ from current output if inadequate).
  4. **Check Existing Tests**: Search for existing test content that may already cover this functionality. Consolidate into spec-aligned test functions rather than duplicating.
  5. **Implement Tests**: Build out parser, ASG, and other unit tests as needed. Tests should specify the CORRECT ASG structure (per step 3 analysis), not just the current behavior.
  6. **Fix Implementation Gaps**: Iterate on fixing code gaps in `src/m2py/` until tests pass. Commit implementation fixes before test changes.
  7. **Verify Complete**: Run related tests until passing, then run full suite (`uv run pytest`) at batch completion.
  8. **Mark Complete**: Update task tracking before moving to next item.
- **FR-011**: Implementation changes MUST be committed separately from test changes, with related fixes batched together using descriptive commit messages
- **FR-012**: validate_asg.py SHOULD be enhanced early in implementation to accept M code from stdin or command-line argument (currently file-only), plus any other improvements needed for efficient test development workflow
- **FR-013**: Parser test assertions MUST validate textX model object structure (node types, attribute values, child node relationships)
- **FR-014**: Tests MUST be isolated (no shared mutable state) and deterministic (same input produces same result)
- **FR-015**: Tests MUST support parallel execution via pytest-xdist (already configured in project)

### Key Entities

- **Stub Test**: A test function marked with `@pytest.mark.xfail` or containing placeholder assertions
- **Implemented Test**: A test function with complete assertions that passes without xfail markers
- **Coverage Matrix**: The docs/coverage-matrix.md file tracking test coverage by spec section
- **ASG Quality**: Developer-evaluated assessment that the semantic graph contains sufficient information for Python code generation. Evaluated by: (1) running validate_asg.py, (2) reading ASG output, (3) judging if codegen has what it needs. Gaps become test assertions.
- **Spec Section**: A MUMPS 1995 ANSI standard section (§5-§9) with defined language features

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All parser and ASG stub tests converted to implemented tests (687 xfail stubs → 0 xfails; codegen deferred)
- **SC-002**: **Concrete success command**: `uv run pytest tests/unit/parser/ tests/unit/asg/ tests/unit/analysis/ tests/unit/meta/ tests/unit/cross_cutting/ -v` passes with 0 failures and 0 xfail markers (currently: 1,189 passed, 93 skipped, 687 xfailed)
- **SC-003**: Coverage matrix shows ✅ for all in-scope spec sections in Parser and ASG columns
- **SC-004**: Parser code coverage reaches 95%+ (measured by pytest-cov)
- **SC-005**: ASG analysis code coverage reaches 95%+ (measured by pytest-cov)
- **SC-006**: All MUGJ functional tests can be parsed and generate valid ASG (no parsing errors)
- **SC-007**: Each test batch completion is documented in task tracking
- **SC-008**: No duplicate test implementations - existing tests are refactored into spec-aligned structure

## Clarifications

### Session 2026-01-04

- Q: What prioritization strategy for stubs - coverage-first, section-by-section, layer-by-layer, or hybrid? → A: Coverage-first (Option A) - prioritize stubs that test currently-untested code paths to maximize regression protection before making implementation changes
- Q: Are codegen tests in scope? → A: No - codegen tests are OUT OF SCOPE for spec 003 and will be addressed in later work
- Q: Batch grouping strategy - file-based, spec-section, or size-based? → A: Hybrid size-based with related grouping. Batch sizes 3-15 stubs, grouped by related tests for learning transfer. Simpler/routine tests use larger batches; complex/abstract features (e.g., indirection) use smaller focused batches. Detailed batch sizing determined during planning research.
- Q: How to verify implementation fixes don't break other tests? → A: Hybrid regression testing - run related test files during batch development for fast iteration; run full test suite (`uv run pytest` unfiltered, including integration/functional) at batch completion; optionally run full suite mid-batch for high-risk changes affecting shared code paths
- Q: Commit discipline for implementation changes? → A: Commit implementation fix before test(s), batch related fixes together with descriptive messages (e.g., "Fix expression handling for FOR parameter tests"). Avoids excessive commit history while maintaining bisect-ability for debugging.
- Q: What if an implementation fix causes a previously-passing test to fail? → A: If new behavior is correct per MUMPS spec, update the regressing test to expect the improved behavior. HOWEVER: Before modifying any existing test, apply the highest verification standards - check MUMPS reference, examples, and/or YDB tests very carefully to be 100% confident the change is correct AND that it improves (not reduces) Python code generation ease/quality.
- Q: How should ASG quality be evaluated beyond validate_asg.py pass/fail? → A: validate_asg.py output is the quality definition, but requires developer judgment. Developer must READ the ASG output and evaluate if it provides sufficient information for Python code generation. Gaps identified should be encoded as assertions in ASG unit tests, then implementation adjusted to address them. Note: validate_asg.py may need enhancement early in this work to accept M code from stdin/argument (currently file-only).
- Q: What should parser test assertions validate? → A: Assert on textX model object structure - node types, attribute values, and child node relationships. This validates the actual parser output that feeds into semantic analysis.
- Q: What test quality requirements should apply (isolation, determinism)? → A: Tests MUST be isolated and deterministic. However, this is largely automatic given the project's unidirectional data flow architecture (parse → analyze → generate) with no shared mutable state or persistent storage.
- Q: Should tests be designed to run in parallel with pytest-xdist? → A: Tests MUST support parallel execution; pytest-xdist is already implemented and automatically applied. This is enabled by the isolation/determinism properties above.
- Q: When should the coverage matrix be regenerated? → A: Per-batch - regenerate after completing each batch (aligns with FR-010 step 8). Balances progress visibility with avoiding excessive overhead.

## Assumptions

- The existing parser implementation is substantially complete for the 1995 MUMPS spec
- The existing ASG structure can represent all necessary semantic information
- MUGJ tests in `tests/functional/mugj/` are the authoritative validation source
- Out-of-scope features (event processing, embedded programs) remain skipped
- The validate_asg.py utility accurately assesses ASG quality for Python generation
- Test batches can be completed incrementally without breaking existing functionality
