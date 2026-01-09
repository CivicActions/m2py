<!--
  SYNC IMPACT REPORT
  ==================
  Version Change: 1.0.0 → 1.1.0
  
  Modified Principles:
  - III. Multi-Phase Architecture → III. Strict Layer Separation (expanded with codegen boundary rules)
  - V. Incremental Validation → V. Foundational Correctness (reframed for "complexity first" approach)
  
  Added Sections:
  - II. YDB as Reference Implementation (new principle, formerly implicit in Test-Driven)
  - VI. Cross-Cutting Semantics (new principle for M value model, $TEST, etc.)
  
  Removed Sections: None
  
  Templates Status:
  - plan-template.md: ✅ Compatible (Constitution Check section exists)
  - spec-template.md: ✅ Compatible (requirements align with principles)
  - tasks-template.md: ✅ Compatible (phase structure supports foundational-first)
  - checklist-template.md: ✅ Compatible (generic structure)
  
  Follow-up TODOs: None
  
  Rationale: Entering code generation phase requires explicit principles for:
  (1) layer boundaries that prevent codegen from doing parsing/analysis work,
  (2) YDB validation as the authoritative reference,
  (3) foundational M semantics that must be correct from earliest spec.
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

### II. YDB as Reference Implementation

YottaDB (YDB) is the authoritative reference for validating MUMPS behavior. When the
ANSI specification is ambiguous or implementation-defined, YDB behavior is correct.

- Generated Python MUST match YDB output for equivalent MUMPS input
- Test expected outputs SHOULD be generated from YDB execution
- Edge cases MUST be validated against YDB before assuming correctness
- Use `docker run --rm -v "$(pwd):/workspace" ydb <file.m>` for validation

### III. Strict Layer Separation

The transpiler uses distinct phases: parsing, semantic analysis, and code generation.
Each phase has clear responsibilities and boundaries.

- **Parsing**: Produces CST from MUMPS source using textX grammar
- **Semantic Analysis**: Transforms CST → ASG, resolves all references, classifies control flow
- **Code Generation**: Translates complete, resolved ASG to Python—nothing else

**Critical boundary**: If code generation discovers missing ASG nodes, unresolved
references, or analysis gaps, fix them in parser or analysis—NEVER build parse-like
or generic analysis code into codegen. Codegen receives a complete ASG and emits Python.

### IV. Explicit Over Implicit

MUMPS has many implicit behaviors that differ from Python. These MUST be made explicit
in generated code through helper functions and runtime support.

- Undefined variables return empty string (not exception)
- All values are strings; numeric operations require explicit coercion via `m_num()`
- Truth evaluation uses numeric interpretation via `m_truth()`
- Left-to-right evaluation with no operator precedence
- Comparisons use M semantics via `m_compare()`

### V. Foundational Correctness

Solve hard structural problems early while the codebase is small. Foundational semantics
must be correct from the earliest spec to avoid painful refactors later.

- Tackle cross-label GOTO, variable scoping, and control flow restructuring before simpler features
- Each spec builds on validated foundational infrastructure
- Complexity is front-loaded; later specs benefit from solid foundations
- Validate each foundational piece before building upon it

**Contrast with "incremental"**: We still validate incrementally, but the *order* prioritizes
hard problems over easy ones. Simple constructs are added after structural patterns are proven.

### VI. Cross-Cutting Semantics

Certain M semantics affect nearly all generated code and must be correct from the start.
These are "day one" requirements, not incremental additions.

- **Value Model**: Numeric coercion rules (ANSI 7.1.4.5), truth evaluation (ANSI 1.2.4)
- **$TEST Variable**: Postconditions do NOT update $TEST; $TEST stacking for argumentless DO
- **Array Model**: Sparse trees where nodes can have both value AND children
- **Variable Scoping**: Default visibility to callees, NEW creates local scope, by-reference aliasing

These semantics MUST be implemented in shared helpers/runtime, not duplicated per-command.

## Technical Constraints

- **Python Version**: 3.10+
- **Parser**: textX for grammar definition
- **Testing**: pytest with YDB validation
- **Package Management**: uv exclusively (never bare python, pip, or pytest)

## Governance

This constitution supersedes all other practices for M2PY development.

- All changes MUST verify compliance with these principles
- Layer boundary violations MUST be fixed in the correct layer, not worked around
- Amendments require documentation of rationale and impact assessment
- Version follows semantic versioning: MAJOR (breaking principle changes), MINOR (additions), PATCH (clarifications)

**Version**: 1.1.0 | **Ratified**: 2025-12-19 | **Last Amended**: 2026-01-08
