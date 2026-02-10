# Research: Phase 1 — Foundation & Cleanup

**Branch**: `019-foundation-cleanup` | **Date**: 2026-02-09

## R-01: C-04 Exception Hierarchy — Already Resolved

**Question**: Are `CodegenError` and `UnsupportedFeatureError` still duplicated between `codegen/__init__.py` and `codegen/statements.py`?

**Decision**: C-04 is already implemented. Skip this item.

**Rationale**: `codegen/exceptions.py` already exists (20 lines) with `CodegenError`
and `UnsupportedFeatureError(CodegenError)` properly defined. Both `codegen/__init__.py`
(line 14) and `codegen/statements.py` (line 105) import from `codegen/exceptions.py`.
There is no duplicate class definition.

**Alternatives considered**: None — the work is already done.

---

## R-02: C-02 NameTranslator — Already Moved

**Question**: Do `translate_name` and `NameTranslator` need to be moved to `core/names.py`?

**Decision**: FR-017 is already implemented. Skip this item.

**Rationale**: `core/names.py` (241 lines) is the canonical definition with
`NameTranslator` at line 20. `codegen/names.py` is a re-export shim
(`from m2py.core.names import NameTranslator, translate_name`). All 24+ usages
in codegen go through the shim.

**Alternatives considered**: None — already in the target state.

---

## R-03: Backward Import Count — 18, Not 15

**Question**: How many deferred imports from `m2py.codegen` exist in runtime/ and core/?

**Decision**: The spec's count of "15" should be "18" (or "17 + 1 generate_python").

**Rationale**: Full scan found:
- `runtime/__init__.py`: 12 deferred imports (4× `translate_name`, 3× `NameTranslator`, 2× `m_num`, 1× `m_compare,m_num,m_truth`, 1× `m_str,m_compare,m_num,m_truth`, 1× `m_truth`)
- `runtime/helpers.py`: 3 deferred imports (1× `m_num,m_str`, 1× `m_str`, 1× `m_str`)
- `runtime/globals.py`: 1 deferred import (1× `m_num,m_str`)
- `core/indirection.py`: 1 deferred import (1× `m_truth`)
- `runtime/__init__.py`: 1 deferred import of `generate_python` (XECUTE callback)

**Breakdown by symbol**:
| Symbol | Count | Source |
|--------|-------|--------|
| `translate_name` | 4 | `codegen/names.py` → already in `core/names.py` |
| `NameTranslator` | 3 | `codegen/names.py` → already in `core/names.py` |
| `m_num` | 5 (unique import sites) | `codegen/helpers.py` → move to `core/values.py` |
| `m_str` | 4 | `codegen/helpers.py` → move to `core/values.py` |
| `m_truth` | 3 | `codegen/helpers.py` → move to `core/values.py` |
| `m_compare` | 2 | `codegen/helpers.py` → move to `core/values.py` |
| `generate_python` | 1 | `codegen/__init__.py` → callback injection |

**Impact**: For `translate_name`/`NameTranslator` (7 sites), the fix is to change the
import path from `m2py.codegen.names` to `m2py.core.names` — no function movement needed
since FR-017 is already done. For value-model functions (10 sites), the import path
changes from `m2py.codegen.helpers` to `m2py.core.values`.

---

## R-04: C-06 Exclusive KILL/NEW — Root Cause Analysis

**Question**: Why do exclusive KILL (`K (X)`) and exclusive NEW (`N (X)`) raise
`NotImplementedError` under TRAMPOLINE without dynamic locals?

**Decision**: Add `has_exclusive_kill` and `has_exclusive_new` flags to `MRoutine`
and include them in `routine_uses_dynamic_locals()`.

**Rationale**: The data flow is:
1. `analysis/variables.py` (lines 188–189) sets `routine.has_argumentless_kill` and
   `routine.has_argumentless_new` by walking ASG statements.
2. `codegen/shared_state.py` (line 50–53) computes `routine_uses_dynamic_locals()` as
   `has_argumentless_kill OR has_argumentless_new OR has_name_indirection_on_locals OR has_external_gotos`.
3. `codegen/statements.py` branches on `ctx.uses_dynamic_locals`:
   - Exclusive KILL at line 4635: `NotImplementedError` when TRAMPOLINE without dynamic locals
   - Argumentless KILL at line 4654: same pattern
   - Exclusive NEW at line 4848: same pattern
   - Argumentless NEW at line 4875: same pattern

The bug: `_routine_has_argumentless_kill` only checks `stmt.is_kill_all` (which is
`not stmt.targets and not stmt.exclusive`). It does NOT detect exclusive KILL
(`stmt.exclusive == True`). Since exclusive KILL also requires iterating all variables
at runtime, it needs `dynamic_locals = True`.

**Fix**: Add two detection functions in `analysis/variables.py`:
```python
def _routine_has_exclusive_kill(routine) -> bool:
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MKillStatement) and stmt.exclusive:
                return True
    return False

def _routine_has_exclusive_new(routine) -> bool:
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MNewStatement) and stmt.exclusive:
                return True
    return False
```

Add `has_exclusive_kill: bool = False` and `has_exclusive_new: bool = False` to
`MRoutine` in `asg/elements.py`. Update `routine_uses_dynamic_locals()` in
`codegen/shared_state.py` to include these flags.

**Alternatives considered**: (a) Force `dynamic_locals = True` for any routine with KILL
or NEW statements — rejected as too aggressive, penalizing normal targeted KILL/NEW.

---

## R-05: walk_statements() — Already Exists on MScope

**Question**: Does `walk_statements()` already exist? What does the spec's S-10 actually need?

**Decision**: S-10's goal is partially achieved. `MScope.walk_statements()` exists at
`asg/elements.py` line 74 and is used at 14 call sites. However, 8 call sites
still use direct `scope.statements` iteration. The plan should focus on migrating
those 8 sites and potentially adding missing nested-scope handling (e.g., `else` bodies).

**Rationale**: The existing `walk_statements()` only recurses into `get_body_scope`
and `get_then_scope`. It does NOT check `get_else_scope`. This means FOR-ELSE
or IF-ELSE nested statements may be missed. Some of the 8 direct-iteration sites
may be intentionally non-recursive (e.g., only wanting top-level statements in
a single scope). Creating a separate `asg/traversal.py` module may be unnecessary
—extending `MScope.walk_statements()` to also handle else-scopes and parameterizing
recursion depth may suffice.

**Action**: Audit all 8 direct-iteration sites. For each, determine if it should be
recursive. If yes, switch to `walk_statements()`. If it needs special behavior
(e.g., tracking depth), consider adding parameters to the existing method rather
than creating a new module.

---

## R-06: m_format_output Docstring — Confirmed Wrong

**Question**: Is the `m_format_output` docstring actually inaccurate?

**Decision**: The docstring is misleading but the specific claim in S-17 is slightly
different from what was reported.

**Rationale**: The docstring at `runtime/helpers.py` line 124 says:
```
m_format_output("0.5") → ".5"  # Numeric strings also formatted
```
But the code returns strings AS-IS — `"0.5"` would return `"0.5"`, not `".5"`.
The "Examples" section's last line is wrong. The docstring's description text is
mostly accurate ("canonical number formatting") but the example implies string-to-string
canonicalization that doesn't happen. Fix: remove the incorrect example and clarify
that string values pass through unchanged.

---

## R-07: Functional Test xfails — Not True Test Failures

**Question**: Does the "zero xfails" requirement in FR-025 conflict with existing
functional test infrastructure?

**Decision**: Runtime `pytest.xfail()` calls in functional tests are acceptable — they
guard against infrastructure issues (transpile failure, missing modules), not assertion
failures. FR-025's "zero xfails" should mean zero `@pytest.mark.xfail` markers and
zero unexpected failures. The runtime `pytest.xfail()` pattern is a dynamic discovery
mechanism, not a known-failure marker.

**Rationale**: `test_mugj.py` and `test_mvts.py` call `pytest.xfail()` at runtime when:
- A routine fails to transpile (line 312, 290 respectively)
- A routine module is not available (line 316, 295)
- No entry point exists (line 333, 311)

These are not "known failures" — they're dynamic guards for routines that may not
be implemented yet. The test framework counts them separately from marker-based xfails.

---

## R-08: Parenthesis-Depth State Machine Count — 13+ Confirmed

**Question**: How many state machines exist and where?

**Decision**: 13+ independent state machines across `runtime/__init__.py` (7),
`core/scope.py` (1), `core/indirection.py` (5).

**Rationale**: Each implements the same fundamental algorithm: walk characters,
track `paren_depth`/`depth` and `in_quotes`/`in_string`, split on delimiter at
depth 0. Variations:
- Delimiter: comma (most), space (some)
- Quote handling: some track `in_string` (double quotes), some ignore
- Return type: `list[str]` vs `tuple`
- Edge cases: some handle escaped quotes, some don't

The `split_at_toplevel()` utility needs parameters:
- `delimiter: str = ","` — what to split on
- `respect_quotes: bool = True` — whether to track quote state
- Possibly `strip_whitespace: bool = False` — some callers strip, some don't

---

## R-09: unwrap_expression — Semantic Difference

**Question**: Do the two `unwrap_expression` implementations actually diverge?

**Decision**: They have different attribute checks but both appear to work correctly
in their respective contexts. The semantic analyzer's version handles parse-time
attributes differently.

**Rationale**:
- `_unwrap_expr` (textx_classes.py:45): checks `operators` (plural, list attribute)
- `unwrap_expression` (semantic_analyzer.py:2818): checks `operator` (singular) and `ops`

This is because textX class attributes differ from ASG node attributes. Neither drops
tails in practice because operator tails mean the expression IS a binary operation
and should not be unwrapped. The "silently drops tails" concern from the refactoring
plan may be overstated — but adding an assertion for safety is still worth doing.
