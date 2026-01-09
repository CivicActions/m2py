# Research: Minimal Control Flow Foundation

**Feature**: Spec 004 - Codegen Foundation  
**Date**: 2026-01-08  
**Status**: Complete

## Overview

This document captures research decisions for Spec 004. Since this spec uses well-understood technologies (Python code generation, MUMPS semantics) with existing infrastructure (textX parser, ASG), research focused on confirming design patterns and validating edge cases.

## Technical Decisions

### 1. Numeric Coercion Algorithm

**Decision**: Implement `m_num()` using regex-based prefix extraction

**Rationale**: 
- ANSI MUMPS 7.1.4.5 specifies left-to-right scanning for numeric prefix
- Python's `float()` and `int()` can't handle strings like `"3A"` (raises ValueError)
- Regex approach: `^([+-]?(?:\d+\.?\d*|\.\d+))` captures valid numeric prefix

**Alternatives Considered**:
- Character-by-character scanning: More verbose, no performance benefit
- Exception handling with `float()`: Doesn't extract prefix, just fails

**Reference**: YDB outputs verified:
- `"3A"+0` → `3`
- `"A3"+0` → `0`
- `"  42"+0` → `42`
- `""+0` → `0`

### 2. Name Translation Strategy

**Decision**: Use prefix-based escaping with case preservation

**Rationale**:
- MUMPS names are case-sensitive (`FOO` ≠ `foo`)
- Python reserves ~35 keywords that MUMPS allows as identifiers
- Prefix strategy ensures injectivity (no collisions)

**Translation Rules**:
| MUMPS Pattern | Python Pattern | Example |
|---------------|----------------|---------|
| `%name` | `_pct_name` | `%UTIL` → `_pct_UTIL` |
| Numeric label | `_n_digits` | `01` → `_n_01` |
| Python keyword | `_m_name` | `for` → `_m_for` |
| Regular name | unchanged | `FOO` → `FOO` |

**Alternatives Considered**:
- Suffix escaping (`FOO_m`): Collides with legitimate MUMPS names ending in `_m`
- Hash-based: Not reversible, harder to debug

### 3. Code Generation Architecture

**Decision**: Visitor pattern over ASG with string accumulation

**Rationale**:
- ASG classes are already dataclasses with typed fields
- Visitor pattern is natural for tree traversal
- String accumulation (not template engine) keeps dependencies minimal

**Structure**:
```
generate_python(source: str) -> str
  └── parse + analyze → MRoutine (ASG)
       └── RoutineGenerator.visit(routine) → Python source
            ├── visit_label(label) → function definition
            ├── visit_statement(stmt) → statement code
            └── visit_expression(expr) → expression code
```

**Alternatives Considered**:
- Jinja2 templates: Overkill for initial scope, adds dependency
- AST building + unparse: More complex, same result

### 4. Runtime Design

**Decision**: Minimal `MUMPSRuntime` class with output buffer and variable storage

**Rationale**:
- Spec 004 needs only: variable get/set, output capture, and implicit coercion
- $TEST tracking deferred to Spec 005
- Keep runtime simple; expand as specs require

**Interface**:
```python
class MUMPSRuntime:
    def get(self, name: str) -> str           # Returns "" for undefined
    def set(self, name: str, value: str)      # Stores value
    def write(self, value: str)               # Appends to output
    def execute(code: str) -> ExecutionResult # Runs generated Python
```

### 5. FOR Loop Translation

**Decision**: Generate Python `while` loops for all FOR variants (consistency)

**Rationale**:
- MUMPS FOR has unusual semantics (loop variable persists after loop)
- Python `for` doesn't naturally support increment expressions
- `while` with explicit counter management matches M semantics

**Patterns**:
| MUMPS | Python Pattern |
|-------|----------------|
| `F I=1:1:3` | `I = 1; while I <= 3: ...; I += 1` |
| `F I=1:1` | `I = 1; while True: ...; I += 1` |
| `F I="A","B"` | `for I in ["A", "B"]: ...` (exception: value list) |
| `F ` | `while True: ...` |

### 6. GOTO Translation (Simple Case)

**Decision**: Forward GOTO as function call with early return

**Rationale**:
- Spec 004 only covers label GOTO (no offsets, no cross-label complexity)
- Forward jump = call target label + return
- Backward jump = not in Spec 004 scope

**Pattern**:
```mumps
 G DONE
 ; skipped code
DONE W "X" Q
```
→
```python
DONE()  # Call target
return  # Early exit
# ... skipped code not generated in simple case
```

**Note**: Spec 006 will handle complex GOTO patterns (cross-label, backward jumps).

## Edge Cases Validated

All edge cases from spec.md were validated against YDB:

| Edge Case | YDB Validation | Notes |
|-----------|----------------|-------|
| Undefined variable | Returns `""` | Runtime handles implicitly |
| Negative increment | `F I=3:-1:1` → `321` | Decrement works correctly |
| Left-to-right eval | `2+3*4` → `20` | No operator precedence |
| Empty string compare | `""<1` → `1` | Coerces to 0 |
| QUIT postcondition | `Q:I>3` exits loop | Needed for open-ended FOR |

## Dependencies

No external dependencies beyond existing project requirements:
- textX (already in pyproject.toml)
- pytest (already in pyproject.toml)

## Open Questions

None - all clarifications resolved during spec phase.
