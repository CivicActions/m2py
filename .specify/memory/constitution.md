<!--
  SYNC IMPACT REPORT
  ==================
  Version Change: N/A → 1.0.0 (initial ratification)
  
  Modified Principles: N/A (initial version)
  
  Added Sections:
  - Core Principles (5 principles)
  - Technical Constraints
  - Governance
  
  Removed Sections: N/A
  
  Templates Status:
  - plan-template.md: ✅ Compatible (Constitution Check section exists)
  - spec-template.md: ✅ Compatible (requirements align with principles)
  - tasks-template.md: ✅ Compatible (phase structure supports incremental validation)
  - checklist-template.md: ✅ Compatible (generic structure)
  
  Follow-up TODOs: None
-->

# M2PY Constitution

## Purpose

This constitution defines the guiding principles for developing M2PY, a MUMPS-to-Python
transpiler. These principles inform architectural decisions, resolve ambiguity, and
establish shared expectations.

## Core Principles

### I. Semantic Correctness First

The primary goal is 100% correct translation of MUMPS logic to Python. Idiomatic or
"pretty" Python is a secondary concern that can be addressed through post-transpilation refactoring.

- Generated code MUST produce identical output to original MUMPS execution
- MUMPS edge cases MUST be handled according to ANSI MUMPS standards
- When uncertain, consult the MUMPS specification at https://71.174.62.16/Demo/AnnoStd
- Mark uncertain translations explicitly for later review

### II. Test-Driven Validation

Testing is the source of truth for correctness. External test suites (e.g., `tests/functional/`)
provide authoritative validation.

- Tests MUST pass before adding new complexity
- New features MUST have corresponding tests
- Integration tests compare transpiled output against MUMPS reference output

### III. Multi-Phase Architecture

The transpiler MUST separate parsing, semantic analysis, and code generation into
distinct phases. Complete semantic understanding MUST be achieved before generating
target code.

- All references (labels, variables, jump targets) MUST be resolved before code generation
- Scopes and control structures MUST be explicitly modeled
- Each phase MUST be independently testable

### IV. Explicit Over Implicit

MUMPS has many implicit behaviors that differ from Python. These MUST be made explicit
in generated code.

- Undefined variables return empty string (not exception)
- All values are strings; numeric operations require explicit coercion
- Left-to-right evaluation with no operator precedence

### V. Incremental Validation

Build complexity incrementally, validating at each step. Never skip ahead to advanced
features before foundational patterns are solid.

- Start with the simplest constructs and prove them correct
- Add complexity only after simpler features pass tests
- Each increment depends on validated previous work

## Technical Constraints

- **Python Version**: 3.10+
- **Parser**: TextX for grammar definition
- **Testing**: pytest

## Governance

This constitution supersedes all other practices for M2PY development.

- All changes MUST verify compliance with these principles
- Complexity MUST be justified against the incremental validation principle
- Amendments require documentation of rationale and impact assessment
- Version follows semantic versioning: MAJOR (breaking principle changes), MINOR (additions), PATCH (clarifications)

**Version**: 1.0.0 | **Ratified**: 2025-12-19 | **Last Amended**: 2025-12-19
