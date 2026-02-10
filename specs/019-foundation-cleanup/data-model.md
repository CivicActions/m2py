# Data Model: Phase 1 — Foundation & Cleanup

**Branch**: `019-foundation-cleanup` | **Date**: 2026-02-09 | **Status**: ✅ Complete

## New Modules

### `core/values.py` — MUMPS Value Semantics

The canonical source for MUMPS value-model functions.

**Entities**:

| Function | Signature | Responsibility |
|----------|-----------|----------------|
| `mumps_canonical_str` | `(value: int \| float \| Decimal) -> str` | Canonical number → string formatting with exponent guard |
| `m_str` | `(value: Any) -> str` | MUMPS string coercion (delegates to `mumps_canonical_str` for numerics) |
| `m_num` | `(value: Any) -> int \| float \| Decimal` | MUMPS numeric coercion |
| `m_truth` | `(value: Any) -> bool` | MUMPS truth evaluation |
| `m_compare` | `(left: Any, op: str, right: Any) -> int` | MUMPS comparison semantics |
| `_decimal_binop` | `(left: Any, right: Any, op: Callable) -> int \| Decimal` | Shared Decimal arithmetic helper |
| `m_add` | `(left: Any, right: Any) -> int \| Decimal` | MUMPS addition (thin wrapper) |
| `m_sub` | `(left: Any, right: Any) -> int \| Decimal` | MUMPS subtraction (thin wrapper) |
| `m_mul` | `(left: Any, right: Any) -> int \| Decimal` | MUMPS multiplication (thin wrapper) |

**Relationships**:
- `codegen/helpers.py` re-exports all public functions for backward compatibility
- `runtime/helpers.py` imports `mumps_canonical_str` for `m_format_output`
- `core/subscripts.py` imports `mumps_canonical_str` for `canonicalize_numeric`
- `runtime/__init__.py`, `runtime/helpers.py`, `runtime/globals.py`, `core/indirection.py` import value-model functions directly

**Validation**: `mumps_canonical_str` MUST apply the exponent guard (exponent < -43 → `"0"`) consistently.

---

### `core/parsing.py` — String-Level Parsing Utilities

**Entities**:

| Function | Signature | Responsibility |
|----------|-----------|----------------|
| `parse_subscripted_name` | `(name: str) -> tuple[str, list[str]]` | Parse `'ARR(1,2)'` → `('ARR', ['1', '2'])` |
| `canonicalize_subscript` | `(sub: str) -> int \| float \| str` | Convert numeric subscript strings to appropriate Python types |

**Relationships**:
- Replaces 3 independent `_parse_subscripted_name` implementations
- `runtime/__init__.py` calls `parse_subscripted_name` then `canonicalize_subscript`
- `core/scope.py` and `core/indirection.py` call `parse_subscripted_name` only

**Validation**: Returns empty list (not `None`) for unsubscripted names.

---

### `core/tokenizer.py` — Delimiter-Aware String Splitting

**Entities**:

| Function | Signature | Responsibility |
|----------|-----------|----------------|
| `split_at_toplevel` | `(s: str, delimiter: str = ",", respect_quotes: bool = True) -> list[str]` | Split string respecting parenthesis nesting and quote state |

**Relationships**:
- Replaces 13+ hand-rolled parenthesis-depth state machines
- Used by `core/parsing.py` internally
- Used by `runtime/__init__.py`, `core/scope.py`, `core/indirection.py`

**Validation**: Empty string → `['']`. Respects nested parentheses and double-quoted strings.

---

### `asg/elements.py` — Extended MRoutine Flags

**New fields on `MRoutine`**:

| Field | Type | Default | Set By |
|-------|------|---------|--------|
| `has_exclusive_kill` | `bool` | `False` | `analysis/variables.py` |
| `has_exclusive_new` | `bool` | `False` | `analysis/variables.py` |

**Relationships**:
- Read by `codegen/shared_state.py:routine_uses_dynamic_locals()` to force dynamic locals
- Prevents `NotImplementedError` for exclusive KILL/NEW under TRAMPOLINE strategy

---

## Modified Modules

### `codegen/helpers.py` — Independent Implementations

Retains its own implementations of:
- `m_str`, `m_num`, `m_truth`, `m_compare`, `m_add`, `m_sub`, `m_mul`
- `m_div`, `m_mod`, `m_range` (codegen-only, not in `core/values.py`)

`core/values.py` is the canonical source used by `runtime/` and `core/`.
`codegen/helpers.py` retains independent copies used by generated Python code.
Backward compatibility is maintained — generated code continues to import from `codegen.helpers`.

### `runtime/helpers.py` — Simplified

- `m_format_output`: Delegates numeric formatting to `mumps_canonical_str` from `core/values.py`
- `_is_canonical_numeric`: Retained (used internally by comparison logic)
- Docstring corrected (S-17)

### `analysis/variables.py` — Extended Detection

New detection functions:
- `_routine_has_exclusive_kill(routine) -> bool`
- `_routine_has_exclusive_new(routine) -> bool`

Set new flags at lines 188–193 alongside existing flag-setting code.

### `codegen/shared_state.py` — Extended Predicate

`routine_uses_dynamic_locals()` adds:
```
or routine.has_exclusive_kill
or routine.has_exclusive_new
```

### `analysis/semantic_analyzer.py` — Deduplicated Helpers

New/refactored internal methods:
- `_analyze_kill_like_args(cmd, stmt)` — shared argument parsing for KILL-family commands (K, KS, KV, ZK, ZW)
- `_analyze_call_target(target, parent, *, has_args)` — shared target analysis for DO/GOTO/JOB
- `unwrap_expression()` — assertion added for non-empty operator tails

### `codegen/expressions.py` — contains_naked_global Delegated

`contains_naked_global()` canonical implementation moved to `analysis/variables.py`.
`codegen/expressions.py` retains a thin delegating wrapper that imports from
`analysis.variables` to maintain call-site compatibility.

### `analysis/for_analysis.py` — Simplified

- `_check_var_modified_in_scope`: Uses `scope.walk_statements()` for recursive
  traversal and its own `statement_modifies_variable()` for per-statement
  write detection (SET, READ, KILL including kill-all and exclusive kill).
- `_check_var_passed_byref_in_scope`: Uses `scope.walk_statements()` instead
  of manual recursive scope traversal.

## State Transitions

No state machines introduced. All changes are structural (module organization)
and detection logic (flag computation).

## Dependency Graph (Post-Refactoring)

```
core/values.py          (no m2py imports)
core/names.py           (no m2py imports)
core/tokenizer.py       (no m2py imports)
core/parsing.py         ← core/tokenizer.py
core/subscripts.py      ← core/values.py
core/scope.py           ← core/parsing.py, core/values.py
core/indirection.py     ← core/parsing.py, core/tokenizer.py, core/values.py
asg/elements.py         (no m2py imports)
asg/statements.py       (no m2py imports)
analysis/variables.py   ← asg/*, core/*
analysis/for_analysis.py ← analysis/variables.py
codegen/helpers.py      ← core/values.py (re-exports)
codegen/names.py        ← core/names.py (re-exports)
codegen/expressions.py  (reads ASG annotations, no analysis import)
runtime/__init__.py     ← core/values.py, core/names.py, core/parsing.py
runtime/helpers.py      ← core/values.py
runtime/globals.py      ← core/values.py
```

No backward imports from runtime/core → codegen (except `generate_python` injected via callback).
