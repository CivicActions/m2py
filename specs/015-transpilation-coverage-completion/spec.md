# Feature Specification: Transpilation Coverage Completion

**Feature Branch**: `015-transpilation-coverage-completion`  
**Created**: 2026-01-20  
**Status**: Draft  
**Input**: User description: "Get transpilation readiness metric to 100% by analyzing parser/asg/analysis coverage gaps when running codegen tests. Categorize each gap as: A) missing codegen for supported features, B) codegen improvements using parser/asg/analysis better, or C) dead code to remove from parser/asg/analysis."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Complete Transpilation Pipeline (Priority: P1)

As a developer transpiling MUMPS code to Python, I want all parser/asg/analysis code that exists to be exercised by the codegen layer, so that I have confidence the transpilation pipeline is complete and working end-to-end.

**Why this priority**: This is the core objective - ensuring the transpilation pipeline exercises all parsing and analysis infrastructure. Currently at 78.6% (70% raw coverage), leaving significant parser/asg/analysis code unused by codegen.

**Independent Test**: Can be verified by running `uv run python utils/coverage_check.py transpile` and observing the progress metric reaches 100% (or documents explicit exclusions).

**Acceptance Scenarios**:

1. **Given** codegen tests run against parser/asg/analysis code, **When** coverage is measured, **Then** transpilation progress metric reaches 100%
2. **Given** any gap in parser/asg/analysis coverage, **When** reviewed by a developer, **Then** each gap is categorized and addressed per the A/B/C resolution strategy

---

### User Story 2 - Remove Dead Analysis Code (Priority: P2)

As a maintainer of the m2py codebase, I want unused parser/asg/analysis code to be removed, so that the codebase is lean and all existing code serves a clear purpose.

**Why this priority**: Dead code adds maintenance burden, confuses contributors, and artificially inflates coverage metrics. Removing it improves code quality.

**Independent Test**: Can be verified by confirming no parser/asg/analysis code exists that is never executed by any test (unit or integration) and serves no documented future purpose.

**Acceptance Scenarios**:

1. **Given** analysis code that codegen doesn't use AND cannot reasonably use, **When** dead code audit is performed, **Then** the code is removed
2. **Given** removed code, **When** the full test suite runs, **Then** all tests still pass

---

### User Story 3 - Improve Codegen Using Analysis Features (Priority: P3)

As a developer working on code generation, I want the codegen layer to leverage all valuable parser/asg/analysis features, so that generated Python code is more efficient and correct.

**Why this priority**: Some analysis features (like for loop classification, variable analysis) may provide optimizations or correctness improvements that codegen isn't currently using.

**Independent Test**: Can be verified by identifying specific analysis features that improve codegen output and implementing their use.

**Acceptance Scenarios**:

1. **Given** an analysis feature that can improve codegen, **When** codegen is updated to use it, **Then** the analysis code becomes covered AND generated Python improves
2. **Given** codegen improvements, **When** the transpilation runs, **Then** output is functionally equivalent but potentially more optimized

---

### Edge Cases

- What happens when analysis code is used by integration tests but not unit codegen tests? (Should count as valid usage, but the transpilation metric specifically measures codegen tests)
- How should utility/helper functions be handled if they're only partially covered? (Partial coverage may be acceptable for defensive code paths)
- What about error handling paths that only trigger on malformed input? (May keep for robustness, document as intentionally untested by codegen)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST categorize each uncovered parser/asg/analysis code region into one of three categories:
  - **Category A**: Parser/asg/analysis code for MUMPS features missing codegen implementation
  - **Category B**: Parser/asg/analysis code that could improve existing codegen if utilized
  - **Category C**: Dead code that should be removed (no valid codegen use case)

- **FR-002**: System MUST implement codegen for all Category A gaps where the MUMPS feature is valid for transpilation

- **FR-003**: System MUST update codegen to use Category B analysis features where they improve output quality or correctness

- **FR-004**: System MUST remove Category C dead code from parser/asg/analysis layers

- **FR-005**: System MUST maintain existing overall test coverage ≥85% after all changes

- **FR-006**: System MUST document any exceptions to 100% transpilation coverage with clear justification (e.g., error handling paths, defensive code)

### Key Entities

- **Coverage Gap**: A region of parser/asg/analysis code not executed by codegen tests
  - Attributes: module, lines, category (A/B/C), resolution, justification
  
- **Resolution Action**: The action taken to address a coverage gap
  - Types: implement_codegen, improve_codegen, remove_code, document_exception

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Transpilation readiness metric reaches 100% (from current 78.6%)
- **SC-002**: All coverage gaps have documented categorization and resolution via A/B/C strategy
- **SC-003**: No parser/asg/analysis code exists without clear purpose (codegen use, error handling, or documented future use)
- **SC-004**: Full test suite passes with no regressions
- **SC-005**: Overall test coverage remains ≥85%

Note: The 100% target maps to 85% raw coverage, which matches what parser/asg/analysis unit tests achieve. This threshold already excludes ~15% of code (imports, infrastructure) from the metric.

## Coverage Gap Analysis

Based on the current coverage report (70% raw, 78.6% normalized), the following modules have significant uncovered regions:

### Parser Layer (~30% uncovered)

| File | Coverage | Key Uncovered Areas |
|------|----------|---------------------|
| parser.py | 70% | Lines 569-609 (classify_for_patterns methods), 848-905 (FOR pattern extraction) |
| textx_classes.py | 65% | Lines 399-441, 521-522, 711-717, 742-746 (various textX class methods) |
| line_parser.py | 39% | Lines 168-182, 197-202, 216-250 (line parsing utilities) |
| exceptions.py | 14% | Lines 32-55, 85-90 (error formatting methods) |

### ASG Layer (~20% uncovered)

| File | Coverage | Key Uncovered Areas |
|------|----------|---------------------|
| elements.py | 56% | Lines 84-117, 123-150, 332-335 (to_dict serialization, iteration helpers) |
| type_helpers.py | 70% | Lines 10-11, 44, 58, 107-109 (type checking utilities) |
| expressions.py | 96% | Lines 25, 385, 390 (minor gaps) |
| statements.py | 98% | Lines 22-23, 406, 432 (minor gaps) |

### Analysis Layer (~30% uncovered)

| File | Coverage | Key Uncovered Areas |
|------|----------|---------------------|
| semantic_analyzer.py | 67% | Many regions (see full report) - largest file with most gaps |
| variables.py | 70% | Lines 197-322 (VariableAnalysisCache class), 1355-1471 (advanced variable analysis) |
| for_analysis.py | 61% | Lines 259-271, 303-324, 370-371 (FOR loop analysis helpers) |
| goto_analysis.py | 81% | Lines 235-240, 451-457 (goto classification edge cases) |
| pattern_compiler.py | 70% | Lines 70-82, 165-167, 311-312, 358-366 (pattern compilation paths) |
| resolver.py | 68% | Lines 176-189, 201-214 (reference resolution paths) |

### Preliminary Gap Categories

Based on initial analysis, likely categorizations:

**Category A (Missing Codegen)**:
- FOR pattern classification utilities in parser (used for analysis but codegen may not leverage)
- Some semantic_analyzer paths for specific statement types

**Category B (Codegen Improvements)**:
- VariableAnalysisCache - could enable incremental codegen
- Advanced FOR loop analysis - could optimize loop generation

**Category C (Dead Code Candidates)**:
- to_dict serialization methods - useful for debugging but not codegen
- Some line_parser utilities if superseded by textX grammar
- Error formatting methods rarely exercised

## Assumptions

- The 85% target for raw coverage (100% normalized) is achievable with the A/B/C strategy
- The 85% threshold was chosen because parser/asg/analysis unit tests achieve ~85% coverage, indicating this captures all meaningful code
- The ~15% baseline represents imports, infrastructure, and defensive code already excluded from the metric
- For infrastructure/utility code (debugging helpers, error formatting) not tied to MUMPS features: keep if it has identifiable intrinsic value, remove if it doesn't - when unsure, stop and ask
- The transpilation metric specifically targets codegen tests because they represent the full transpilation pipeline usage

## Clarifications

### Session 2026-01-20

- Q: How should non-feature infrastructure code (debugging, error formatting, caching) be handled? → A: Keep if it has identifiable intrinsic value (debugging, edge case handling), remove if not. When unsure, stop and ask.
- Q: What is the target for the transpilation metric? → A: 100% (not 95%). The metric already normalizes 85% raw coverage to 100%, and 85% is what parser/asg/analysis unit tests achieve, so codegen should match that.