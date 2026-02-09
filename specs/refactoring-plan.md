# M2PY Consolidated Refactoring Analysis

Synthesized from three independent analyses (Opus, Codex, Gemini). Every
factual claim has been validated against the current codebase. Items are grouped
by theme and ordered within each priority tier by impact.

**Priority 1 — Correctness**: Items that could cause generated Python to
diverge from MUMPS specification behavior.

**Priority 2 — Simplicity / Organization**: Items that reduce maintenance
burden, eliminate duplication, or fix architectural layering.

---

## Table of Contents

1. [Priority 1: Correctness Improvements](#priority-1-correctness-improvements)
2. [Priority 2: Simplicity & Organization](#priority-2-simplicity--organization)
3. [Priority 3: Functionality Gaps (VistA-Used)](#priority-3-functionality-gaps-vista-used)
4. [Deferred: Feature-Completeness Gaps](#deferred-feature-completeness-gaps)
5. [Rejected / Already Resolved Claims](#rejected--already-resolved-claims)

---

## Priority 1: Correctness Improvements

### C-01: Dual Canonical Number Formatters Diverge on Edge Cases

**Sources:** Opus ND-001, Gemini 1.2 (related)
**Validated:** ✅ Confirmed

**Facts:**
- `m_str()` in [codegen/helpers.py](src/m2py/codegen/helpers.py#L20) and
  `m_format_output()` in [runtime/helpers.py](src/m2py/runtime/helpers.py#L124)
  both implement MUMPS canonical number formatting.
- `m_format_output` has an exponent guard capping `exponent < -43` → `"0"`
  that `m_str` lacks. Very small Decimals could therefore produce different
  results at compile-time vs runtime.
- `SubscriptCanonicalizer.canonicalize_numeric()` in [core/subscripts.py](src/m2py/core/subscripts.py#L22) is a **third** implementation of the
  same Decimal-digit-decomposition logic.
- Any bugfix to canonical formatting must currently be applied in 3 places.

**Candidate Design:**
Create a single `mumps_canonical_str(value) -> str` in a new `core/values.py`.
Both `m_str` and `m_format_output` delegate to it. `m_format_output` adds its
string-passthrough and MArray-unwrap responsibilities on top.
`SubscriptCanonicalizer` also delegates to it for numeric canonicalization.

**Effort:** Medium (2–3 days). Extracting the function is straightforward;
the work is in ensuring every call site passes through correctly, updating
tests, and verifying that the exponent-guard behavior is applied consistently.

---

### C-02: Architecture Violation — Runtime/Core Imports from Codegen

**Sources:** Opus ND-012, Codex Runtime section
**Validated:** ✅ 15 backward imports confirmed

**Facts:**
- 14 imports from `m2py.codegen` in `runtime/` and 1 in `core/`. All are
  deferred (inside function bodies) to avoid circular imports.
- Functions imported: `m_num`, `m_str`, `m_truth`, `m_compare`,
  `translate_name`, `NameTranslator`, `generate_python`.
- The MUMPS value model functions (`m_num`, `m_str`, `m_truth`, `m_compare`)
  are actually foundational semantics that belong below codegen.

**Why this is a correctness concern:** The backward imports force deferred
(in-function) imports. If a call is made before codegen is loaded (e.g., during
testing or runtime-only use), it crashes. It also makes it impossible to use
the runtime without the full codegen layer.

**Candidate Design:**
1. Create `core/values.py` with `m_num`, `m_str`, `m_truth`, `m_compare`.
2. Both codegen-generated code and runtime import from `core/values`.
3. Keep re-exports in `codegen/helpers.py` for backwards compatibility.
4. Move `translate_name` / `NameTranslator` to `core/names.py`.
5. For `generate_python` — this is only used by runtime XECUTE exec. Either
   pass it as a callback at `MUMPSRuntime` construction or accept a thin
   runtime→codegen dependency for this one case.

**Effort:** Medium (2–3 days). Moving functions is mechanical. The risk is in
updating all 15 import sites and generated-code templates that `from m2py.codegen.helpers import ...`.

---

### C-03: Three Independent `_parse_subscripted_name` Implementations

**Sources:** Opus ND-002, Opus ND-003
**Validated:** ✅ 3 implementations confirmed with different return types

**Facts:**
| Location | Return no-subs | Type | Error handling |
|---|---|---|---|
| [runtime/__init__.py L106](src/m2py/runtime/__init__.py#L106) | `None` | `Tuple[str, Optional[Tuple]]` | Raises `IndirectionError` |
| [core/scope.py L429](src/m2py/core/scope.py#L429) | `[]` | `Tuple[str, List[str]]` | Silent fallback `(name, [])` |
| [core/indirection.py L1352](src/m2py/core/indirection.py#L1352) | `[]` | `tuple[str, List[str]]` | No validation |

- The runtime version converts numeric subscripts to int/float; the
  core versions return raw strings. This can cause lookup mismatches when
  a subscript parsed as `"1"` in one path doesn't match `1` in another.
- Similarly, `_parse_subscript_list` (3 implementations) and
  `_split_argument_list` (3 implementations, 2 distinct algorithms) diverge.

**Why correctness:** A subscript lookup using `"1"` vs `1` can fail to find
data, causing silent data loss or incorrect `$DATA`/`$ORDER` results.

**Candidate Design:**
Create `core/parsing.py` with:
```python
def parse_subscripted_name(name: str) -> tuple[str, list[str]]:
    """Parse 'ARR(1,2)' → ('ARR', ['1', '2']). Returns [] for no subs."""

def split_argument_list(s: str) -> list[str]:
    """Split comma-separated args respecting parens and quotes."""
```
All three call sites delegate to these. Numeric subscript conversion moves
to a separate `canonicalize_subscript()` step applied where needed (runtime
storage operations).

**Effort:** Small–Medium (1–2 days). The functions are self-contained. The
main work is identifying all callers and adjusting their expectations.

---

### C-04: `UnsupportedFeatureError` — Two Classes with Different Bases

**Sources:** Opus DC-002
**Validated:** ✅ Confirmed

**Facts:**
- [codegen/__init__.py L25](src/m2py/codegen/__init__.py#L25): `class UnsupportedFeatureError(CodegenError)`
- [codegen/statements.py L105](src/m2py/codegen/statements.py#L105): `class UnsupportedFeatureError(Exception)`
- Code catching `CodegenError` will **not** catch errors from `statements.py`.
- The `statements.py` copy exists to "avoid circular import."

**Candidate Design:**
Create `codegen/exceptions.py` containing `CodegenError` and
`UnsupportedFeatureError(CodegenError)`. Both `__init__.py` and `statements.py`
import from there. No circular dependency since exceptions have no dependencies.

**Effort:** Trivial (< 1 hour). Move classes, update imports.

---

### C-05: LOCK Indirection Silently Skipped

**Sources:** Opus SI-001, Codex Codegen section
**Validated:** ✅ Confirmed at [statements.py L5571](src/m2py/codegen/statements.py#L5571)

**Facts:**
- `L @X` silently emits `# LOCK indirection not yet supported` and continues.
- No error at compile time or runtime. The lock is simply not acquired.
- MUMPS allows indirect lock names and VistA uses them for dynamic lock
  management (**222 VistA files** use LOCK with indirection).

**Candidate Design:**
Short term: change the comment to `raise NotImplementedError("LOCK indirection
not yet supported")` so that programs depending on it fail loudly.
Long term: implement `_rt.lock_indirected()` following the same pattern as
`_rt.set_indirected()` and other indirection entry points.

**Effort:** Trivial for `NotImplementedError` (< 1 hour). Medium for full
implementation (1–2 days) following existing indirection patterns.

---

### C-06: KILL/NEW Exclusive + Argumentless Not Supported for TRAMPOLINE Without Dynamic Locals

**Sources:** Codex Codegen section
**Validated:** ✅ 4 `NotImplementedError` blocks confirmed

**Facts:**
- [Exclusive KILL L4664](src/m2py/codegen/statements.py#L4664),
  [Argumentless KILL L4683](src/m2py/codegen/statements.py#L4683),
  [Exclusive NEW L4878](src/m2py/codegen/statements.py#L4878),
  [Argumentless NEW L4904](src/m2py/codegen/statements.py#L4904) —
  all raise `NotImplementedError` when strategy is TRAMPOLINE but
  `uses_dynamic_locals` is false.
- These code paths are reachable for routines using GOTO-based control flow
  without any dynamic variable creation.

**Candidate Design:**
Either:
(a) Force `uses_dynamic_locals = True` whenever exclusive KILL/NEW or
argumentless forms appear — the semantic analyzer can detect these during
analysis and set the flag.
(b) Emit code that operates on the known set of `state_vars` for
exclusive forms — iterate all dataclass fields except the exclusion set.

Option (a) is simpler and correct. If a routine uses `N (X)`, it needs
dynamic local access. The analyzer should infer this.

**Effort:** Small (half a day). The fix is in the semantic analyzer's
`uses_dynamic_locals` detection logic.

---

### C-07: By-Reference Call Handling Diverges Between Strategies

**Sources:** Codex Codegen section, Gemini 2.1
**Validated:** ✅ Confirmed different approaches

**Facts:**
- **SIMPLE_FUNCTIONS** ([L4493](src/m2py/codegen/statements.py#L4493)): True MArray aliasing — passes `_scope.setdefault(var, MArray())` directly.
- **TRAMPOLINE** ([L4518](src/m2py/codegen/statements.py#L4518)): Value-result approach — destructures return tuple based on callee signatures.
- The TRAMPOLINE approach can lose mutations if the callee modifies the
  by-ref variable and then errors before returning.

**Candidate Design:**
Unify on MArray aliasing for both strategies. TRAMPOLINE already has `state._locals`
dict access when `uses_dynamic_locals` is true, which can hold MArray references.
For static state fields, wrap byref parameters in MArray objects and unwrap
on return. This is closer to MUMPS semantics (true pass-by-reference).

**Effort:** Large (3–5 days). Requires changes to both call-site generation
and callee function signatures, plus comprehensive testing.

---

### C-08: `contains_naked_global` — Analysis in Codegen Layer

**Sources:** Gemini 1.3, validated against analysis/ directory
**Validated:** ✅ Defined at [expressions.py L195](src/m2py/codegen/expressions.py#L195), no equivalent in analysis/

**Facts:**
- Performs ~80-line recursive ASG traversal in codegen to check for naked
  global references.
- Used at [statements.py L1124](src/m2py/codegen/statements.py#L1124) to decide evaluation order.
- The analysis phase has structurally identical traversal patterns (e.g.,
  `walk_expressions`, `_collect_globals_from_node`).

**Why correctness:** If this check has a bug or misses a node type, it
silently affects evaluation order — a subtle correctness issue. Running it
once during analysis and caching the result as an ASG annotation would be
more reliable and auditable.

**Candidate Design:**
Move to `analysis/variables.py` as `has_naked_global(expr) -> bool`. Call
during semantic analysis, store result as `expr._has_naked_global`. Codegen
reads the pre-computed annotation.

**Effort:** Small (half a day). The function is self-contained. Moving it
and adding annotation storage is mechanical.

---

### C-09: ZWRITE Subscript Ranges Treated as Wildcard

**Sources:** Opus SI-002
**Validated:** ✅ Confirmed at [statements.py L6580](src/m2py/codegen/statements.py#L6580)

**Facts:**
- `ZW ^A(1:3)` should display nodes with first subscript between 1 and 3.
- Currently `break`s out of subscript processing, treating the range as `*`.
- Code is duplicated identically for both globals and locals paths
  ([L6580](src/m2py/codegen/statements.py#L6580) and [L6600](src/m2py/codegen/statements.py#L6600)).

**Candidate Design:**
Add range filtering after the subscript prefix match. When encountering
`MZWriteSubscriptRange`, record the range bounds and add a runtime filter: 
`if start <= m_num(subscript) <= end: include`. Requires runtime collation
comparison for non-numeric ranges.

**Effort:** Medium (1–2 days). Codegen changes are small; the runtime
filtering logic requires care around MUMPS collation.

---

## Priority 2: Simplicity & Organization

### S-01: Strategy-Dispatch Pattern — 69 Occurrences

**Sources:** Opus ND-005
**Validated:** ✅ 69 occurrences across expressions.py (20), statements.py (42), indirection.py (7)

**Facts:**
The 3-way dispatch for variable access is copy-pasted ~69 times:
```python
if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
    base = f"state._locals.get({name!r}, MArray())"
elif ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
    base = f"state.{python_name}"
else:
    base = f"_scope.get({name!r}, MArray())"
```

**Candidate Design:**
Extract three helpers in a new `codegen/var_access.py`:
```python
def var_read_expr(var_name: str, ctx) -> str
def var_write_stmt(var_name: str, value_expr: str, ctx) -> str
def var_base_expr(var_name: str, ctx) -> str
```
Each call site reduces to `base = var_base_expr(var_name, ctx)`.

**Effort:** Large (3–5 days). 69 call sites to update, each with slight
variations that must be preserved. Best done with careful search-and-replace
and comprehensive test coverage.

---

### S-02: Subscript Tuple Generation — ~99 Occurrences

**Sources:** Opus ND-009
**Validated:** ✅ 99 occurrences across expressions.py (57), statements.py (36), indirection.py (6)

**Facts:**
Same 4-line pattern repeated 99 times:
```python
sub_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]
if len(sub_exprs) == 1:
    subscripts_tuple = f"({sub_exprs[0]},)"
else:
    subscripts_tuple = f"({', '.join(sub_exprs)},)"
```

**Candidate Design:**
```python
def gen_subscripts_tuple(subscripts, ctx) -> str:
    exprs = [generate_expr(sub, ctx) for sub in subscripts]
    return f"({', '.join(exprs)},)" if exprs else "()"
```
Each call site becomes `subs = gen_subscripts_tuple(var.subscripts, ctx)`.

**Effort:** Medium (1–2 days). Mechanical extraction with no behavioral risk.

---

### S-03: Indirection Functions — 11 Near-Identical (~800 Lines)

**Sources:** Opus ND-006
**Validated:** ✅ 11 functions in [codegen/indirection.py](src/m2py/codegen/indirection.py)

**Facts:**
All 11 follow the same template:
1. Count indirection levels
2. Build scope expression
3. Type-switch on inner expression
4. Build `per_level_subscripts`
5. Format final `_rt.xxx_indirected(...)` call

Only the runtime method name and return-value handling differ.

**Candidate Design:**
```python
def _build_indirection_call(ind, ctx, runtime_method: str, **kwargs) -> str:
    """Shared template for all indirection code generation."""
    # ... ~70 lines of shared logic ...
    return f"_rt.{runtime_method}({args})"
```
Each function becomes 3–5 lines.

**Effort:** Large (2–3 days). The variations between functions are subtle and
must be carefully parameterized.

---

### S-04: Scope ↔ State Sync Blocks — 22 Copies

**Sources:** Opus ND-014, Codex Codegen section
**Validated:** ✅ 16 in statements.py (9 state→scope, 7 scope→state) + 6 in routine.py

**Facts:**
Two patterns repeated 22 times total:
- **State→scope:** `_scope.update({k: v for k, v in state._locals.items()})`
- **Scope→state:** `for _k, _v in _scope.items(): ...` with MArray wrapping

**Candidate Design:**
```python
def emit_state_to_scope_sync(ctx):
    ctx.emitter.line("_scope.update({k: v for k, v in state._locals.items()})")

def emit_scope_to_state_sync(ctx, state_var="state"):
    ctx.emitter.line(f"for _k, _v in _scope.items():")
    ctx.emitter.indent()
    # ... MArray wrapping ...
    ctx.emitter.dedent()
```

**Effort:** Medium (1–2 days). The variations between sync blocks must be
audited to confirm they are truly identical before factoring.

---

### S-05: LHS `$PIECE` / `$EXTRACT` — Near-Identical Functions

**Sources:** Opus ND-007
**Validated:** ✅ ~300 lines of duplication at [statements.py](src/m2py/codegen/statements.py#L1279) and [L1430](src/m2py/codegen/statements.py#L1430)

**Facts:**
Both `_generate_lhs_piece` and `_generate_lhs_extract` follow the exact same
4-step structure. The MIndirection handling block (~50 lines) is identical.

**Candidate Design:**
Extract `_build_lhs_getter_setter(first_arg, ctx) -> tuple[str, str]` that
returns `(getter_expr, setter_expr)` for any variable type (global, naked,
indirection, local). Both functions become short wrappers adding position
args and calling `m_set_piece` or `m_set_extract`.

**Effort:** Medium (1 day). Clean extraction with clear boundaries.

---

### S-06: `m_add`/`m_sub`/`m_mul` — Three Identical Arithmetic Helpers

**Sources:** Opus ND-010
**Validated:** ✅ ~40 lines each at [helpers.py L297, L336, L375](src/m2py/codegen/helpers.py#L297)

**Facts:**
Only the operator differs (`+`, `-`, `*`). The Decimal coercion, type
checking, and edge-case handling are identical.

**Candidate Design:**
```python
def _decimal_binop(left, right, op):
    """Shared implementation for MUMPS arithmetic."""
    # ... 40 lines of shared logic ...

def m_add(l, r): return _decimal_binop(l, r, operator.add)
def m_sub(l, r): return _decimal_binop(l, r, operator.sub)
def m_mul(l, r): return _decimal_binop(l, r, operator.mul)
```

**Effort:** Small (half a day). Straightforward extraction.

---

### S-07: Parenthesis-Depth + Quote-Tracking State Machine — 15+ Copies

**Sources:** Opus DC-001
**Validated:** ✅ At least 15 implementations across runtime/, core/

**Facts:**
The same character-walking state machine (tracking paren depth, quote state,
splitting on commas at depth 0) is reimplemented in every function that
parses subscripts, argument lists, or expressions from strings.

**Candidate Design:**
Create `core/tokenizer.py` with:
```python
def split_at_toplevel(s: str, delimiter: str = ",",
                      respect_quotes: bool = True) -> list[str]:
    """Split string respecting parentheses nesting and quotes."""
```
This replaces the hand-rolled state machines throughout.

**Effort:** Medium (1–2 days). After creating the utility, each call site
needs testing to confirm identical behavior.

---

### S-08: Kill-Like Analyzers — 5 Near-Identical Methods

**Sources:** Opus ND-016
**Validated:** ✅ In [analysis/semantic_analyzer.py](src/m2py/analysis/semantic_analyzer.py)

**Facts:**
`_analyze_KillCommand`, `_analyze_KSubscriptsCommand`,
`_analyze_KValueCommand`, `_analyze_ZKillCommand`, `_analyze_ZWithdrawCommand`
all iterate targets, analyze expressions, and return ASG nodes differing only
in class type. ZKill and ZWithdraw are literally identical (ZWithdraw is a
MUMPS alias for ZKill).

**Candidate Design:**
```python
def _analyze_kill_like(self, cmd, target_class):
    targets = [self._analyze_expression(t) for t in cmd.targets]
    return target_class(targets=targets, ...)

def _analyze_ZWithdrawCommand(self, cmd):
    return self._analyze_ZKillCommand(cmd)  # alias
```

**Effort:** Small (half a day). Clean pattern.

---

### S-09: DO/GOTO/JOB Argument Processing — Near-Identical Loops

**Sources:** Opus ND-017
**Validated:** ✅ In analysis/semantic_analyzer.py

**Facts:**
All three iterate `cmd.args`, check for indirection, build `MCall` with
`routine`/`label`/`offset` using ~30-line blocks that vary only in
post-processing.

**Candidate Design:**
Extract `_analyze_call_arguments(self, cmd) -> list[MCall]` shared helper.

**Effort:** Small (half a day).

---

### S-10: Scope-Walking Pattern — 4+ Reimplementations

**Sources:** Opus ND-015
**Validated:** ✅ Confirmed across for_analysis.py, goto_analysis.py, variables.py, parser.py

**Facts:**
Each reimplements "walk all statements recursively, visiting into IF/FOR/DO
bodies." If a new scope-bearing ASG node is added, all must be updated.

**Candidate Design:**
Create `asg/traversal.py`:
```python
def walk_statements(scope, visitor_fn, *, recurse_into_bodies=True):
    """Walk all statements in scope, calling visitor_fn(stmt) for each."""
    for stmt in scope.statements:
        visitor_fn(stmt)
        if recurse_into_bodies:
            for body in _get_bodies(stmt):
                walk_statements(body, visitor_fn)
```

**Effort:** Medium (1–2 days). Must accommodate the slightly different
traversal needs of each call site (some skip FOR bodies, some track depth).

---

### S-11: `_is_canonical_numeric` — Two Implementations

**Sources:** Opus ND-011
**Validated:** ✅ [runtime/helpers.py L989](src/m2py/runtime/helpers.py#L989) imports `m_str` from codegen

**Facts:**
The runtime version imports `m_str` from codegen (architecture violation).
The core version uses `SubscriptCanonicalizer.is_canonical_numeric_string()`.

**Candidate Design:**
Delete the runtime copy. Use `SubscriptCanonicalizer` as the single source of
truth, or after C-01, use `mumps_canonical_str` from `core/values.py`.

**Effort:** Small (half a day). Part of C-01 / C-02 refactoring.

---

### S-12: offset_wrapper — Two Duplicated Closures

**Sources:** Opus ND-013
**Validated:** ✅ [runtime/__init__.py L1113–1224](src/m2py/runtime/__init__.py#L1113) and [L1470–1556](src/m2py/runtime/__init__.py#L1470)

**Facts:**
Two ~100-line closures sharing ~80% identical logic (scope init, state
creation, trampoline loop, state sync). They differ in error handling
approach and state sync mechanism (`__dataclass_fields__` vs `dir(state)`).

**Candidate Design:**
Extract `_create_offset_entry_wrapper(base_fn, offset, strategy, ...)` factory
that parameterizes the differences.

**Effort:** Medium (1 day).

---

### S-13: Inline XECUTE Re-uses Parser But Creates Coupling

**Sources:** Codex Codegen section
**Validated:** ✅ [statements.py L5843](src/m2py/codegen/statements.py#L5843) imports and calls parser functions

**Facts:**
The XECUTE handler imports `parse_commands_from_line` and
`_structure_commands_with_bodies` from the parser. This is **not**
reimplementation — it correctly reuses existing functions. However, it
creates a codegen→parser backward dependency and duplicates the
analysis pipeline inline (calling `analyze_command()`,
`analyze_quit_context_for_statements()`, etc.).

**Candidate Design:**
Extract a `compile_mumps_line(code_str) -> list[MStatement]` top-level
function (in parser or a new `core/compile.py`) that runs the full
parse→analyze→structure pipeline. Both regular parsing and XECUTE call
this single function.

**Effort:** Medium (1–2 days). Mainly reorganizing existing code.

---

### S-14: GotoExternal Handler Blocks — 4–6 Copies

**Sources:** Opus DC-003, validated count
**Validated:** ✅ 4 in statements.py + 2 in routine.py = 6 total

**Facts:**
Each `except GotoExternal` block includes identical scope→state sync logic.

**Candidate Design:**
Extract `_emit_goto_external_handler(ctx)` that emits the standard catch block.

**Effort:** Small (half a day).

---

### S-15: Expression Unwrapping — Two Paths

**Sources:** Opus DC-006
**Validated:** ✅

**Facts:**
- [parser/textx_classes.py L52](src/m2py/parser/textx_classes.py#L52): `_unwrap_expr()` — complete, handles tails
- [analysis/semantic_analyzer.py L2932](src/m2py/analysis/semantic_analyzer.py#L2932): `unwrap_expression()` — shallow, drops tails

`unwrap_expression()` silently drops operator tails — a potential
correctness issue if any caller passes an `Expr` with a tail.

**Candidate Design:**
Add an assertion in `unwrap_expression()` that tails are empty, or remove it
and use `_unwrap_expr` exclusively.

**Effort:** Small (half a day). Check all callers first.

---

### S-16: ASG Cleanup — Deprecated Fields and Missing Types

**Sources:** Opus DC-008, DC-009, DC-010, DC-011, DC-012
**Validated:** ✅

**Facts:**
- `MIfStatement` has both `condition` and `conditions` (redundant)
- `MHangStatement` has both `duration` (deprecated) and `durations`
- `MLockStatement.targets` is `List[Any]` with dicts (untyped)
- `MXecuteStatement` has both `arguments` and `code_expressions` (legacy)
- `_analyze_ZWithdrawCommand` is identical to `_analyze_ZKillCommand`

**Candidate Design:**
- Remove `condition` from `MIfStatement`, use only `conditions: list`
- Remove `duration` from `MHangStatement`
- Create `MLockTarget` dataclass, replace `List[Any]`
- Remove `code_expressions` from `MXecuteStatement`
- Have `_analyze_ZWithdrawCommand` delegate to `_analyze_ZKillCommand`
- Update all consumers

**Effort:** Medium (1–2 days total for all). Each individual change is small
but touching ASG definitions requires updating all consumers.

---

### S-17: `m_format_output` Misleading Docstring

**Sources:** Opus SI-014
**Validated:** ✅ Confirmed via YDB

**Facts:**
Docstring claims `m_format_output("0.5") → ".5"` but the code returns
strings as-is. The behavior is correct; only the docstring is wrong.

**Candidate Design:**
Fix the docstring to state: "String values are returned unchanged.
Only numeric types undergo canonical formatting."

**Effort:** Trivial (minutes).

---

### S-18: Dead XECUTE Stubs in Indirection Module

**Sources:** Opus SI-012
**Validated:** ✅ At [indirection.py L1433](src/m2py/codegen/indirection.py#L1433)

**Facts:**
`generate_xecute_constant()` and `generate_xecute_dynamic()` both raise
`NotImplementedError`. XECUTE is fully implemented in `statements.py`.
These are dead code.

**Candidate Design:**
Delete both functions.

**Effort:** Trivial (minutes). Verify no callers first.

---

### S-19: Comment Extraction Reparses Source Lines

**Sources:** Gemini 1.1
**Validated:** ✅ Partially — it's a lightweight character scan, not a full reparse

**Facts:**
[statements.py L146](src/m2py/codegen/statements.py#L146): `_emit_source_comment` looks up the original MUMPS source
line from `ctx.routine.source_lines` and scans for unquoted semicolons.
This works but bypasses the parser's existing comment knowledge.

**Candidate Design:**
Add `comment: Optional[str]` to `MStatement` in the ASG, populated during
parsing. Codegen reads `stmt.comment` instead of re-scanning source.

**Effort:** Small–Medium (1 day). Requires parser modification to capture
inline comments.

---

### S-20: Variable Modification Detection — Duplicated

**Sources:** Opus DC-007
**Validated:** ✅ Both in analysis/

**Facts:**
- `for_analysis.py` reimplements write detection in `_check_var_modified_in_scope`
- `variables.py` has comprehensive `_extract_statement_variables` that already
  identifies writes

**Candidate Design:**
Have `_check_var_modified_in_scope` call into `variables.py`'s existing
infrastructure instead of reimplementing write detection.

**Effort:** Small (half a day).

---

## Priority 3: Functionality Gaps (VistA-Used)

These are simplified or incomplete implementations of features that have
significant usage in the VA VistA codebase (33,951 .m files analyzed).
Ordered by VistA file count.

### F-01: LOCK Command — No Inter-Process Locking

**VistA usage:** 2,977 files (8.8%)
**Limitation:** None documented

**Facts:**
- LOCK uses Python `threading.Lock` for in-process synchronization only.
- MUMPS locks are designed for inter-process coordination.
- Missing: inter-process lock management, lock timeout with `$TEST` update,
  lock escalation/de-escalation, `^$LOCK` SSVN (1 VistA file).
- LOCK indirection (`L @X`) is silently skipped (see C-05, 222 VistA files).
- In-process locking works correctly for single-process use.

**Candidate Design:**
For multi-process scenarios, implement a lock manager using either:
(a) A shared SQLite database or file-based advisory locks.
(b) A lightweight lock server process (similar to YDB's approach).
For single-process m2py, current implementation is functional. Inter-process
locking only matters once JOB (F-02) creates real processes.

**Effort:** Large (5+ days). Requires IPC infrastructure. Tightly coupled to
JOB implementation.

---

### F-02: I/O Device Management — Only `$PRINCIPAL`

**VistA usage:** 1,062 files use OPEN (3.1%)
**Limitation:** None documented

**Facts:**
- The I/O subsystem handles only `$PRINCIPAL` (stdin/stdout).
- File I/O (`OPEN "file.txt":("RW")`), TCP sockets, and device parameter
  processing are minimally stubbed.
- Missing: device parameter parsing, `$KEY` for READ termination, full `$X`/`$Y`
  position tracking, device-specific WRITE rules.
- VistA uses OPEN/USE/CLOSE extensively for file operations, HL7 TCP
  communication, and print device management.

**Candidate Design:**
Implement a device abstraction layer in runtime:
```python
class MUMPSDevice(ABC):
    def read(self, maxlen=None, timeout=None) -> str
    def write(self, data: str)
    def open(self, params: dict)
    def close(self)
```
Subclasses: `PrincipalDevice`, `FileDevice`, `TCPDevice`. The runtime
`USE` command switches the active device. Start with `FileDevice` (covers
most VistA usage).

**Effort:** Very Large (10+ days). Requires design for device parameter
parsing, device table management, and per-device READ/WRITE semantics.

---

### F-03: Error Trapping — Partial `$ETRAP`/`$ECODE`

**VistA usage:** 435 files use `$ETRAP`, 384 files use `$ECODE` (combined ~500 unique files, 1.5%)
**Limitation:** None documented

**Facts:**
- `$ETRAP` is settable and `$ECODE` is partially maintained.
- Missing: proper stack unwinding during error trap execution, `$ECODE` format
  with surrounding commas (`,Merr,`), nested error traps (error during error
  handling), error trap context (`$STACK(-1)`).
- `$ZTRAP` (YDB-specific, 45 VistA files) is not implemented — see F-09.
  `$ZSTATUS` (42 files) and `$ZPOSITION` (17 files) are also used in
  VistA error handling — see F-09.
- VistA's Kernel error handling (`^%ZTER`) depends heavily on `$ETRAP`/`$ECODE`.

**Candidate Design:**
The error trap mechanism needs:
1. Proper `$ECODE` accumulation with `,Merr,` format.
2. QUIT from error trap unwinds to the stack level where `$ETRAP` was set.
3. `NEW $ETRAP` / `NEW $ESTACK` support for nested error handling.
4. `$STACK(-1)` returning the error context.
Implement as a try/except wrapper emitted around each subroutine entry point
that catches exceptions and dispatches to `$ETRAP` code.

**Effort:** Medium–Large (3–5 days). The stack unwinding semantics are
the hardest part.

---

### F-04: JOB Command — Thread-Based, Not Process-Based

**VistA usage:** 343 files (1.0%)
**Limitation:** None documented

**Facts:**
- MUMPS JOB creates a separate process with its own symbol table.
- Current implementation uses Python threads, sharing memory.
- JOB'd routines share global state with the parent (incorrect).
- `$JOB` returns thread ID, not process ID.
- No MUMPS-level inter-process signaling.
- VistA's TaskMan (`^%ZTMS`) is built on JOB and is critical infrastructure.

**Candidate Design:**
Use `subprocess` or `multiprocessing` to create real processes.
The JOB'd routine would need its own Python process with:
- Independent local variable space.
- Shared global storage (via the global storage backend).
- Shared LOCK table (see F-01).
Pass initial parameters via globals or a temporary file.

**Effort:** Large (5–8 days). Architectural change affecting runtime
initialization, global storage sharing, and lock coordination.

---

### F-05: TSTART Restart Variables

**VistA usage:** 193 files use `TS (vars)`; 28 files use `TS *` (0.6%)
**Limitation:** LIM-016 (TROLLBACK:n and $TRESTART documented; restart vars gap not explicitly listed)

**Facts:**
- `TS (X,Y)` and `TS *` should save/restore specified variables on
  transaction restart. Only bare `TS` works.
- LIM-016 documents TROLLBACK:n (0 VistA files) and $TRESTART (0 VistA files)
  but does not mention TSTART restart variable lists.
- TRESTART mechanism is also unimplemented.
- VistA uses `TS (vars)` in database update routines for rollback safety.

**Candidate Design:**
At TSTART, snapshot the specified variables (deep copy their MArray trees).
On TROLLBACK, restore from snapshot. For `TS *`, snapshot all current locals.
The existing `copy.deepcopy()` transaction mechanism can be extended to include
local variable snapshots alongside global snapshots.

**Effort:** Medium (2–3 days). The infrastructure for global snapshots already
exists; extending it to locals is incremental.

---

### F-06: READ with `#maxlen`

**VistA usage:** 88 files (0.3%)
**Limitation:** None documented

**Facts:**
- `READ X#5` (read up to 5 characters) has limited support.
- Combining `#maxlen` with `:timeout` is incomplete.
- Terminal raw mode for character-at-a-time input is not fully implemented.
- `$KEY` reflecting the termination character is missing.
- VistA uses `READ X#n` for menu prompts and fixed-length field input.

**Candidate Design:**
For non-interactive (piped) input, implement as `input()[:maxlen]`.
For interactive input, use Python's `termios`/`tty` modules to read
character-by-character until maxlen is reached or a terminator is entered.
Set `$KEY` to the terminating character.

**Effort:** Medium (2–3 days). Terminal raw mode handling requires
platform-specific code.

---

### F-07: SSVNs — Mostly Stubbed

**VistA usage:** 81 files total — `^$JOB` (13), `^$ROUTINE` (12),
`^$SYSTEM` (5), `^$CHARACTER` (4), `^$GLOBAL` (1), `^$LOCK` (1)
**Limitation:** LIM-003 (MWAPI SSVNs only: `^$EVENT`, `^$WINDOW`, `^$DISPLAY`),
LIM-011 (`^$LIBRARY`)

**Facts:**
- `^$JOB(pid)` — returns `"1"` for current process only. VistA uses it
  to check if a JOB'd process is alive.
- `^$ROUTINE(name)` — minimal implementation. VistA uses it to check
  routine existence.
- `^$SYSTEM` — hard-coded values.
- `^$LOCK` — not implemented (1 VistA file).
- `^$CHARACTER` — not implemented (4 VistA files).
- Most SSVNs that return multiple subscripted values are not implemented.

**Candidate Design:**
Extend `InMemoryGlobalStorage` SSVN handling:
- `^$JOB(pid)`: query process table or threading module.
- `^$ROUTINE(name)`: check if routine exists in loaded modules.
- `^$SYSTEM("VOL")`: return configured volume.
- `^$LOCK`: expose current lock table.

**Effort:** Medium (2–3 days). Each SSVN is small but they require
knowledge of what VistA actually queries.

---

### F-08: `$STACK` Per-Level Introspection

**VistA usage:** 21 files use `$STACK(` (0.06%)
**Limitation:** None documented

**Facts:**
- `$STACK` returns current call depth (works).
- `$STACK(n)` and `$STACK(n,"PLACE")`, `$STACK(n,"MCODE")`,
  `$STACK(n,"ECODE")` are not implemented.
- Used in VistA error handling routines to build stack traces.

**Candidate Design:**
Maintain a call stack list in `MUMPSRuntime` that records
`(routine, label, line)` at each DO/XECUTE entry. `$STACK(n,"PLACE")`
returns the recorded location. `$STACK(n,"MCODE")` returns the source line.

**Effort:** Medium (1–2 days). Requires updating DO/XECUTE call sites
to push/pop stack frames.

---

### F-09: YDB Error Handling — `$ZTRAP`, `$ZSTATUS`, `$ZPOSITION`

**VistA usage:** `$ZTRAP` (45 files), `$ZSTATUS` (42 files), `$ZPOSITION` (17 files)
**Limitation:** LIM-015

**Facts:**
- `$ZTRAP` is YDB's legacy error trapping mechanism (predates ANSI `$ETRAP`).
  VistA Kernel routines (`ZOSFGTM`, etc.) use `$ZTRAP` as the primary error
  handler when running on GT.M/YDB.
- `$ZSTATUS` contains the full error message from the last error (42 files).
  Used alongside `$ECODE` in error handlers.
- `$ZPOSITION` identifies the routine+offset of the last error (17 files).
  Used in error logging.
- These three features form a cohesive YDB error handling subsystem.
- Related to F-03 (`$ETRAP`/`$ECODE`) — implementing both gives full
  VistA error handling coverage.

**Candidate Design:**
Extend the runtime error infrastructure:
- `$ZTRAP`: Store as an ISV. On error, if `$ZTRAP` is set and `$ETRAP` is not,
  XECUTE the `$ZTRAP` code in the error context.
- `$ZSTATUS`: Populate from Python exception message on every trapped error.
- `$ZPOSITION`: Record `routine+offset` in the exception handler.

**Effort:** Medium (2–3 days). Builds on the same infrastructure as F-03.
Implementing F-03 and F-09 together would be most efficient.

---

### F-10: `$ZDATE` — Date Formatting

**VistA usage:** 26 files (0.08%)
**Limitation:** LIM-015

**Facts:**
- `$ZDATE(horolog, format, months, days)` formats `$HOROLOG` values
  into human-readable date strings.
- Used in VistA System Monitor (KMPVCBG), Kernel routines (ZOSFGTM,
  ZOSFONT, ZOSFIS2, ZOSFDTM), FileMan (DINZONT), and ZSY.
- Format codes include `DD`, `MON`, `YY`, `YYYY`, `24:60:SS`, etc.
- VistA also has its own date formatting (`$$HTE^XLFDT`) but some
  routines use `$ZDATE` directly for platform-specific code paths.

**Candidate Design:**
Implement as a Python function mapping `$HOROLOG` to formatted strings:
```python
def m_zdate(horolog: str, fmt: str = "MM/DD/YY", ...) -> str:
    # Parse $H into date components
    # Apply format string substitutions
```
Most VistA usage involves simple format strings.

**Effort:** Small–Medium (1–2 days). Well-defined semantics, standard
date arithmetic.

---

### F-11: ZLINK / ZSYSTEM — Runtime Environment Commands

**VistA usage:** ZLINK (16 files), ZSYSTEM (6 files)
**Limitation:** LIM-015

**Facts:**
- `ZLINK routine` compiles and links a routine at runtime. Used in
  Kernel (ZOSV2GTM, ZTMGRSET, ZTMOVE), FileMan (DIFROM6, DINIT21),
  Toolkit (XTRGRPE, XTVCHG), VPE (XVSE), and others.
- `ZSYSTEM command` executes an OS shell command. Used in Kernel
  (ZISHGTM, ZOSFGTM, ZOSFGUX) for file operations (`rm`, `mv`, `DEL`).
- Both are YDB-specific but have non-trivial VistA usage in system
  administration and routine management code.

**Candidate Design:**
- ZLINK: In m2py context, this could trigger re-importing a Python
  module. `importlib.reload()` provides the mechanism.
- ZSYSTEM: Map to `subprocess.run()` with the command string.
  Security considerations apply.

**Effort:** Small–Medium (1–2 days). ZSYSTEM is straightforward;
  ZLINK requires design decisions about runtime module reloading.

---

### F-12: YDB I/O & Environment SVNs — `$ZEOF`, `$ZSEARCH`, `$ZRO`, `$ZJOB`

**VistA usage:** `$ZEOF` (13 files), `$ZJOB` (12 files), `$ZSEARCH` (11 files),
`$ZRO` (10 files), `$ZMESSAGE` fn (7 files), `^%G` (6 files)
**Limitation:** LIM-015

**Facts:**
- `$ZEOF`: End-of-file flag for sequential file I/O. Blocked on F-02
  (I/O device management).
- `$ZJOB`: Extended job information (bitmask of process attributes).
  Different from ANSI `$JOB` (process ID).
- `$ZSEARCH(pattern)`: File system search using wildcards. Used in
  Kernel (ZISHGTM) and Toolkit (XTEDTVXD) for file operations.
- `$ZRO` / `$ZROUTINES`: Routine search path. Used in Kernel to
  locate routine source files.
- `$ZMESSAGE(code)`: Returns error message text for a given error code.
- `^%G`: YDB global display utility. Referenced from 6 VistA files
  but requires interactive terminal infrastructure.

**Candidate Design:**
- `$ZSEARCH`: Map to Python `glob.glob()` or `pathlib.Path.glob()`.
- `$ZRO`: Return a configurable routine search path string.
- `$ZJOB`: Return a bitmask based on process state.
- `$ZEOF`: Part of F-02 device management.
- `$ZMESSAGE`: Lookup table of YDB error codes → messages.
- `^%G`: Low priority — interactive utility.

**Effort:** Medium (2–3 days total for the group). `$ZEOF` is blocked
on F-02. `$ZSEARCH` and `$ZRO` are independent and straightforward.

---

### F-13: Extended Global References — `^|"env"|NAME`, `^[UCI,VOL]NAME`

**VistA usage:** 9–21 files (3 pipe-form `^|"env"|NAME`, 6+ bracket-form
`^[UCI,VOL]NAME`; heavy use in Kernel TaskMan: ZTM2.m, ZTM5.m, XPDCOMF.m)
**Limitation:** Not tracked (gap found during dead-code analysis cross-reference)

**Facts:**
- The parser already has textX classes `ExtendedGlobalPipe` and
  `ExtendedGlobalBracket` (both listed as dead code with coverage gaps).
- Codegen raises `NotImplementedError` for extended globals (1 line in
  `codegen/expressions.py`).
- VistA's Kernel TaskMan (ZTM2.m) uses `^[ZTM,ZTN]%ZTSK(...)` extensively
  for cross-namespace global access.
- Pipe form `^|"%SYS"|SYS` appears in Kernel routines (KMPSGE.m, NVSSTM.m).

**Candidate Design:**
- Wire existing parser classes through semantic analysis.
- Add ASG representation for namespace-qualified global references.
- Codegen emits `_rt.get_global_ns(env, name, subscripts)` or similar.
- Runtime stores namespace as a prefix on the global name (e.g.,
  `env:NAME` key in the global dict), or accepts a namespace parameter.

**Effort:** Medium (2–3 days). Parser classes exist; work is in analysis
wiring, ASG representation, codegen, and runtime namespace support.

---

### F-14: strict_mode LVUNDEF Activation

**VistA usage:** N/A (runtime configuration feature)
**Limitation:** Not tracked

**Facts:**
- FR-025 spec compliance: MUMPS should raise an error when reading an
  undefined local variable (LVUNDEF). By default, m2py returns empty
  string (matching common MUMPS implementations).
- Implementation already exists in `core/scope.py` (~5 lines) with
  `LVUNDEFError` exception class.
- However, there is **no activation mechanism** — no CLI flag, no config
  option, no runtime toggle to enable strict mode.
- The implementation is dead code with no way to turn it on.

**Candidate Design:**
- Add `--strict-lvundef` CLI flag to `main.py`.
- Pass flag through to `MUMPSRuntime` constructor.
- Runtime sets `self._strict_lvundef = True` and scope reads it.

**Effort:** Trivial (< 1 hour). The core logic exists; just needs a
CLI flag and plumbing.

---

## Deferred: Feature-Completeness Gaps

These items have **zero or negligible VistA usage** and are deferred
indefinitely unless a specific routine requires them.

| ID | Gap | LIM | VistA Files | Notes | Effort |
|---|---|---|---:|---|---|
| SI-004 | Transaction `TROLLBACK:n` | LIM-016 | 0 | Rollback to specific level | Large |
| SI-004 | `$TRESTART` | LIM-016 | 0 | Transaction restart count | Small |
| SI-011 | VIEW behavioral keywords | LIM-005 | 2 | Only `VIEW "TRACE"` in test utils | Small–Medium |
| SI-013 | User-defined pattern tables | LIM-006 | 3 | `PATCODE "YZ"` | Small |
| SI-016 | Exclusive NEW runtime limits | — | — | Addressed in C-06 | — |
| Gemini 2.2 | ANSI library functions | LIM-014 | 0 | ^STRING, ^CHARACTER, extended ^MATH | Very Large |
| — | Zero-usage Z-commands | LIM-015 | 0 | ZALLOCATE, ZDEALLOCATE, ZCOMPILE, ZCONTINUE, ZEDIT, ZHELP, ZTRIGGER | — |

---

## Rejected / Already Resolved Claims

| Claim | Source | Status | Reason |
|---|---|---|---|
| Dead `SemanticScope`/`ScopeVariableInfo` scaffolding | Codex | **Already removed** | Not found in current source. Only appears in old spec documents. |
| `parse_line_content` vs `parse_commands_from_line` duplicate error-wrapping | Codex | **Incorrect** | `parse_commands_from_line` is a thin wrapper that passes through `MParseError` from `parse_line_content`. No duplicate error handling. |
| `Scope.set_subscripted` has unreachable `ValueError` | Codex | **Incorrect** | No `ValueError` exists anywhere in `core/scope.py`. |
| Loop variable analysis mixed into emitter | Gemini 2.3 | **Incorrect** | Loop analysis is cleanly separated in `analysis/for_analysis.py`. `ForGenContext` reads pre-computed annotations; it does not perform analysis. |
| Integer division / exponentiation inline → correctness bug | Gemini 1.2 | **Mostly incorrect** | `int(m_num(a) / m_num(b))` matches MUMPS truncation-toward-zero. `m_num(0)` returns Python `int(0)`, so `0**0 = 1` is correct. `Decimal(-2)**Decimal(0.5)` raises `InvalidOperation`, matching MUMPS's `NEGFRACPWR` error. The inline operators are correct for all reachable cases. |
| `dead_code_analysis.py` generates unreachable statements | Opus (htmlcov ref) | **File doesn't exist** | Only present in old code coverage reports. `_get_reachable_labels` in codegen/__init__.py is unrelated (GOTO validation). |

---

## Recommended Implementation Order

The plan is structured into phases with explicit parallel tracks (A, B, C…).
Items in the same track are sequential; items across tracks can be worked on
simultaneously with minimal merge-conflict risk because they touch different
areas of the codebase.

**Bottleneck:** `codegen/statements.py` is touched by 14 items. All
statements.py work is serialized into a single track per phase to avoid
conflicts.

**Estimated total:** ~45–55 days of work across all items (less with
parallelism).

---

### Phase 1: Zero-Risk Quick Wins (0.5–1 day)

All independent, touching different files. Do them all in parallel.

| Track | Items | Files Touched | Time |
|-------|-------|--------------|------|
| A | **C-04** (codegen/exceptions.py), **C-05** (LOCK → NotImplementedError) | `codegen/__init__.py`, `codegen/statements.py`, `codegen/exceptions.py` (new) | < 1 hr |
| B | **S-17** (docstring fix), **S-18** (delete dead stubs) | `runtime/helpers.py`, `codegen/indirection.py` | minutes |

---

### Phase 2: Analysis & Parser Layer (1.5–2 days)

Clean up the analysis tier before touching codegen. None of these conflict
with Phase 3's core-layer work, so Phase 2 and 3 can overlap if two people
are available.

| Track | Items | Files Touched | Time |
|-------|-------|--------------|------|
| A | **S-08** (kill-like analyzers) → **S-09** (DO/GOTO/JOB args) → **S-15** (unwrap_expression) | `analysis/semantic_analyzer.py`, `parser/textx_classes.py` | 1.5 days |
| B | **S-20** (reuse variable write detection) → **C-08** (move contains_naked_global) | `analysis/for_analysis.py`, `analysis/variables.py`, `codegen/expressions.py` | 1 day |

**Why this order:** S-08 and S-09 both consolidate methods in `semantic_analyzer.py`;
doing them together avoids editing the same file twice. S-15 also touches that
file but is small. Track B touches completely separate analysis files.

---

### Phase 3: Core Architecture (3–5 days)

Creates the foundational abstractions that later phases depend on. Two
parallel tracks creating new files in `core/`.

| Track | Items | Files Touched | Time |
|-------|-------|--------------|------|
| A | **C-01** + **C-02** + **S-11** (core/values.py — unify formatters, resolve backward imports) | `core/values.py` (new), `codegen/helpers.py`, `runtime/helpers.py`, `core/subscripts.py`, 15 import sites | 3 days |
| B | **C-03** + **S-07** (core/parsing.py + core/tokenizer.py) | `core/parsing.py` (new), `core/tokenizer.py` (new), `runtime/__init__.py` (parse fns), `core/scope.py`, `core/indirection.py` | 2–3 days |
| C | **S-06** (_decimal_binop extraction) | `codegen/helpers.py` | 0.5 day |

**Conflicts:** Track A and C both touch `codegen/helpers.py` — do S-06 either
before or after C-01, or fold it into Track A since it's small. Track B is
fully independent.

**Gate:** Phase 4+ should not start until Track A completes, as it establishes
`core/values.py` which affects codegen import paths.

---

### Phase 4: Codegen Deduplication (6–9 days)

The largest phase — heavy refactoring of `codegen/statements.py`,
`codegen/expressions.py`, and `codegen/indirection.py`. The statements.py
items must be carefully sequenced.

| Track | Items | Files Touched | Time |
|-------|-------|--------------|------|
| A (statements.py — sequential) | **S-02** (subscript tuple, 99 sites) → **S-05** (LHS piece/extract) → **S-04** (scope↔state sync) → **S-14** (GotoExternal handler) → **C-09** (ZWRITE range) | `codegen/statements.py`, `codegen/expressions.py` | 5–7 days |
| B | **S-03** (indirection template extraction, 11 fns) | `codegen/indirection.py` | 2–3 days |
| C | **S-12** (offset_wrapper consolidation) | `runtime/__init__.py` | 1 day |
| D | **S-10** (generic statement walker) → **S-16** (ASG field cleanup) | `asg/traversal.py` (new), `asg/statements.py`, analysis consumers | 2–3 days |

**Why S-02 first in Track A:** It's the most mechanical (99 identical extractions),
low risk, and reduces code volume in statements.py before the harder S-05/S-04
work. S-01 (var_base_expr, 69 sites) is deliberately deferred — it's the
single largest item and benefits from S-02+S-04 being done first so there's
less noise in the file.

**Why S-16 after S-10:** The statement walker (S-10) creates `asg/traversal.py`
infrastructure that S-16's consumer updates may want to use.

Track B (indirection.py) and Track C (runtime/__init__.py) are completely
independent of Track A.

---

### Phase 5: Remaining Structural Work (5–8 days)

With the major deduplication done, tackle the remaining items including the
largest single refactor (S-01).

| Track | Items | Files Touched | Time |
|-------|-------|--------------|------|
| A | **S-01** (var_base_expr, 69 sites — largest single item) | `codegen/statements.py`, `codegen/expressions.py`, `codegen/indirection.py`, `codegen/var_access.py` (new) | 3–5 days |
| B | **S-13** (extract compile_mumps_line for XECUTE) → **S-19** (comment extraction via ASG) | `codegen/statements.py` (XECUTE handler), `parser/line_parser.py`, `asg/statements.py` | 2–3 days |

**Conflict note:** Track A and B both touch `codegen/statements.py` but in
very different sections (A: variable access patterns throughout; B: XECUTE
handler at L5843 and comment extraction at L146). If this is a concern,
serialize them — do S-01 first since it's the largest change.

---

### Phase 6: Correctness Fixes (3–6 days)

Items that change behavior rather than just structure. These should be done
after the structural refactoring to avoid re-doing work.

| Track | Items | Files Touched | Time |
|-------|-------|--------------|------|
| A | **C-06** (force dynamic_locals for exclusive KILL/NEW) | `analysis/semantic_analyzer.py` | 0.5 day |
| B | **C-07** (unify by-ref call handling — high risk) | `codegen/statements.py` (call handling sections) | 3–5 days |

**Why C-07 is last in the structural phases:** It's the highest-risk change,
modifying how function call arguments are generated for both strategies. All
other statements.py refactoring should be complete first so the code is
cleaner and the change is easier to reason about. C-06 is independent
(analysis layer).

---

### Phase 7: Functionality — Independent Features (8–12 days)

These add new capabilities. Most touch `runtime/` (adding new functions) plus
`codegen/statements.py` (generating calls to them). However, the runtime
additions are in distinct subsystems and can be parallelized.

| Track | Items | Files Touched | Time |
|-------|-------|--------------|------|
| A (error handling) | **F-03** + **F-09** (ETRAP/ECODE + ZTRAP/ZSTATUS/ZPOSITION) → **F-08** ($STACK introspection) | `runtime/__init__.py` (error handling), `codegen/statements.py` (SET $ETRAP etc.) | 5–7 days |
| B (transactions) | **F-05** (TSTART restart variables) | `runtime/__init__.py` (transaction mgr), `codegen/statements.py` (TSTART handler) | 2–3 days |
| C (standalone fns) | **F-10** ($ZDATE) → **F-11** (ZLINK/ZSYSTEM) | `runtime/helpers.py` or new `runtime/zfunctions.py`, `codegen/statements.py` (Z-cmd handlers) | 2–3 days |
| D (SVNs & SSVNs) | **F-07** (^$JOB, ^$ROUTINE etc.) → **F-12** ($ZSEARCH, $ZRO, $ZJOB, $ZMESSAGE — excluding $ZEOF) | `runtime/globals.py` (SSVNs), new `runtime/zfunctions.py` | 3–4 days |
| E (READ) | **F-06** (READ #maxlen + $KEY) | `runtime/__init__.py` (read handler), `codegen/statements.py` (READ codegen) | 2–3 days |
| F (globals) | **F-13** (extended global refs) | `parser/textx_classes.py`, `analysis/semantic_analyzer.py`, `codegen/expressions.py`, `runtime/__init__.py` | 2–3 days |
| G (config) | **F-14** (strict_mode LVUNDEF) | `main.py`, `runtime/__init__.py`, `core/scope.py` | < 1 hr |

**Conflict mitigation:** Tracks B, C, and E all touch `codegen/statements.py`
but in different command handlers (TSTART ~L5413, Z-commands ~L6400+, READ ~L5100).
If only one person is working, prioritize Track A first (highest VistA impact),
then C and D (small, independent), then B and E.

---

### Phase 8: Functionality — Large Architecture (15–20 days, sequential)

These are the three largest items with deep architectural dependencies.
They should be done in this order.

| Order | Item | Files Touched | Time |
|-------|------|--------------|------|
| 1 | **F-02** (I/O device management) | `runtime/__init__.py` (new device layer), `codegen/statements.py` (OPEN/USE/CLOSE/READ/WRITE), new `runtime/devices.py` | 10+ days |
| 2 | **F-04** (JOB as real processes) | `runtime/__init__.py` (JOB handler), global storage sharing | 5–8 days |
| 3 | **F-01** (LOCK inter-process) + **F-12** ($ZEOF — blocked on F-02) | `runtime/__init__.py` (lock manager), `runtime/devices.py` ($ZEOF) | 5+ days |

**Why this order:** F-02 (I/O) unblocks F-12's $ZEOF and improves F-06.
F-04 (JOB) must precede F-01 (inter-process LOCK only matters with
separate processes). F-01 is last because in-process locking already works.

---

### Summary: Critical Path

The longest dependency chain determines minimum calendar time:

```
Phase 1 (0.5d) → Phase 3A (3d) → Phase 4A (5-7d) → Phase 5A (3-5d) → Phase 6B (3-5d)
→ Phase 7A (5-7d) → Phase 8 (20+d)
= ~40-48 days minimum on the critical path
```

With two parallel workers, Phases 2–5 can overlap significantly, reducing
the wall-clock time for the structural work from ~18 days to ~12 days.
Phase 7 features are highly parallelizable (4-5 independent tracks).

### Quick Reference: Item → Phase Mapping

| Item | Phase | Track | Effort |
|------|-------|-------|--------|
| C-01+C-02+S-11 | 3 | A | 3 days |
| C-03 | 3 | B | 1–2 days |
| C-04 | 1 | A | < 1 hr |
| C-05 | 1 | A | < 1 hr |
| C-06 | 6 | A | 0.5 day |
| C-07 | 6 | B | 3–5 days |
| C-08 | 2 | B | 0.5 day |
| C-09 | 4 | A | 1–2 days |
| S-01 | 5 | A | 3–5 days |
| S-02 | 4 | A | 1–2 days |
| S-03 | 4 | B | 2–3 days |
| S-04 | 4 | A | 1–2 days |
| S-05 | 4 | A | 1 day |
| S-06 | 3 | C | 0.5 day |
| S-07 | 3 | B | 1–2 days |
| S-08 | 2 | A | 0.5 day |
| S-09 | 2 | A | 0.5 day |
| S-10 | 4 | D | 1–2 days |
| S-12 | 4 | C | 1 day |
| S-13 | 5 | B | 1–2 days |
| S-14 | 4 | A | 0.5 day |
| S-15 | 2 | A | 0.5 day |
| S-16 | 4 | D | 1–2 days |
| S-17 | 1 | B | minutes |
| S-18 | 1 | B | minutes |
| S-19 | 5 | B | 1 day |
| S-20 | 2 | B | 0.5 day |
| F-01 | 8 | — | 5+ days |
| F-02 | 8 | — | 10+ days |
| F-03+F-09 | 7 | A | 4–6 days |
| F-04 | 8 | — | 5–8 days |
| F-05 | 7 | B | 2–3 days |
| F-06 | 7 | E | 2–3 days |
| F-07 | 7 | D | 2–3 days |
| F-08 | 7 | A | 1–2 days |
| F-10 | 7 | C | 1–2 days |
| F-11 | 7 | C | 1–2 days |
| F-12 | 7+8 | D | 2–3 days |
| F-13 | 7 | F | 2–3 days |
| F-14 | 7 | G | < 1 hr |
