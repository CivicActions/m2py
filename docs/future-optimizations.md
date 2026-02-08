# Future Optimizations

This document tracks potential optimizations that were considered but deferred in favor of simpler, correct implementations. These can be revisited once the core transpiler is stable.

## Cross-Routine Variable Passing (Static Analysis)

**Current approach**: Pass a `_scope` dictionary to all external calls. All non-NEWed variables are stored in this shared dictionary.

**Potential optimization**: Use the existing variable analysis infrastructure (`MLabel.input_variables`, `output_variables`, `compute_transitive_inputs()`) to:

1. Recursively analyze external routines at transpile-time
2. Determine exactly which variables each external call reads and writes
3. Generate explicit Python function parameters and return values instead of `_scope` dict

**Benefits**:
- Cleaner generated Python: `result = ext2(X, Y)` instead of `ext2(_scope)`
- Better IDE support (type hints, autocomplete)
- Potential performance improvement (dict lookups vs direct variables)

**Why deferred**:
- MUMPS semantics allow any variable to be read/written anywhere
- Indirection (`@VAR`) and XECUTE defeat static analysis
- Callers can pass variables not explicitly declared
- Correctness is more important than aesthetics initially

**Prerequisites to implement**:
- Stable cross-routine calling infrastructure
- Whole-program analysis capability (multi-file transpilation)
- Clear strategy for handling analysis-defeating patterns (fallback to `_scope`)

**Related code**:
- `src/m2py/analysis/variables.py` - existing variable analysis
- `MLabel.input_variables`, `output_variables` - per-label analysis results
- `compute_transitive_inputs()` - call-chain propagation

---

## Deduplicate External Routine Imports

**Current approach**: Each external extrinsic call (`$$LABEL^ROUTINE`) emits its own `import` statement inline:

```python
def TEST(_rt, _scope=None, **_kwargs):
    import math
    _scope['A'] = _call_extrinsic(_rt, math.ADD, 1, 2, _scope=_scope)
    import math  # Duplicate!
    _scope['B'] = _call_extrinsic(_rt, math.MULT, 3, 4, _scope=_scope)
```

**Potential optimization**: Track imported modules during code generation and emit each import only once, ideally at the top of the function:

```python
def TEST(_rt, _scope=None, **_kwargs):
    import math  # Single import
    _scope['A'] = _call_extrinsic(_rt, math.ADD, 1, 2, _scope=_scope)
    _scope['B'] = _call_extrinsic(_rt, math.MULT, 3, 4, _scope=_scope)
```

Or even at module level for routines that always call a given external:

```python
import math  # Module-level import

def TEST(_rt, _scope=None, **_kwargs):
    _scope['A'] = _call_extrinsic(_rt, math.ADD, 1, 2, _scope=_scope)
    _scope['B'] = _call_extrinsic(_rt, math.MULT, 3, 4, _scope=_scope)
```

**Benefits**:
- Cleaner generated code (no duplicate imports)
- Slightly faster execution (Python checks sys.modules on each import)
- More idiomatic Python style
- Easier to read and understand generated code

**Why deferred**:
- Python's import statement is idempotent - duplicate imports are semantically correct
- Python caches modules in `sys.modules`, so overhead is minimal (~100ns per redundant import)
- Current inline approach handles conditional imports correctly (import only when path is taken)
- Module-level imports would require multi-pass analysis to determine which routines are always called

**Prerequisites to implement**:
- Add `ctx.imported_modules: set[str]` to track already-emitted imports
- Check before emitting: `if module not in ctx.imported_modules`
- Consider: function-scoped dedup vs module-level hoisting (different trade-offs)
- Handle conditional branches: imports in IF blocks should stay conditional

**Implementation sketch**:
```python
# In expressions.py, _generate_extrinsic():
python_module_name = translate_name(routine_name)
if python_module_name not in ctx.imported_modules:
    ctx.emitter.line(f"import {python_module_name}")
    ctx.imported_modules.add(python_module_name)
```

**Related code**:
- `src/m2py/codegen/expressions.py` - `_generate_extrinsic()` emits imports
- `src/m2py/codegen/routine.py` - `GeneratorContext` could track imported modules

---

## Conditional $TEXT Source Embedding

**Current approach**: Every generated `.py` file includes `_source_lines = [...]` with the original MUMPS source.

**Potential optimization**: Whole-program analysis to determine which routines are referenced by `$TEXT(^routine)` calls, and only embed source in those routines.

**Benefits**:
- Reduced generated file sizes (typically 1-5KB per routine saved)
- Faster module loading for routines that don't need $TEXT

**Why deferred**:
- VistA routines are typically small, overhead is negligible
- Whole-program analysis requires multi-pass transpilation
- External $TEXT queries (routine A reading B's source) are unpredictable
- "Always correct" beats "optimized but potentially broken"

**Prerequisites to implement**:
- Multi-file transpilation with dependency tracking
- $TEXT reference extraction during parsing
- CLI option to opt-in to optimization (with clear documentation of limitations)

---

## Inline String Operations for $PIECE and $EXTRACT

**Current approach**: `$PIECE` and `$EXTRACT` generate calls to runtime helper functions (`m_piece()`, `m_extract()`) that handle all edge cases including out-of-range indices, invalid positions, and range extraction.

**Potential optimization**: When function arguments are **literal constants**, generate inline Python string operations:

```python
# Current: $E("HELLO",2,4) generates:
m_extract("HELLO", 2, 4)

# Optimized: could generate:
"HELLO"[1:4]  # Direct Python slice (1-indexed to 0-indexed conversion)

# Current: $P("A^B^C","^",2) generates:
m_piece("A^B^C", "^", 2)

# Optimized: could generate:
"A^B^C".split("^")[1]  # Direct Python split/index
```

For dynamic arguments, a lambda expression could avoid function call overhead:
```python
# $E(X,N,M) could generate:
(lambda s,f,t: s[max(0,f-1):t] if f>0 and t>=f else "")(str(X), int(N), int(M))
```

**Benefits**:
- Faster execution (no function call overhead)
- More idiomatic Python output
- Better for debugging/reading generated code in simple cases

**Why deferred**:
- Helper functions are clearer and easier to maintain
- Edge case handling (out-of-range, negative indices) is complex inline
- Lambda expressions for dynamic cases are verbose and hard to read
- Function call overhead is negligible for typical MUMPS workloads
- "Correct and readable" beats "micro-optimized" initially

**Prerequisites to implement**:
- Literal detection in ASG (identify constant vs dynamic arguments)
- Comprehensive edge-case testing for inline expressions
- Performance profiling showing helper calls as actual bottleneck
- Consider a `--optimize` flag to opt-in

**Related code**:
- `src/m2py/codegen/expressions.py` - `_gen_piece()`, `_gen_extract()`, `_gen_length()`
- `src/m2py/runtime/helpers.py` - `m_piece()`, `m_extract()`

---

## Plain Python Variables for Local-Only Scalars

**Current approach**: All variables use `_scope` dictionary with MArray wrappers:

```python
# MUMPS: S X=1 W X
_scope.setdefault('X', MArray()).value = 1
_rt.write(_scope.get('X', MArray()).value)
```

**Potential optimization**: When a variable is:
1. Only used within a single label (doesn't cross call boundaries)
2. Never accessed with subscripts (scalar-only usage)
3. Not passed by reference to other routines
4. Not subject to indirection or XECUTE

Generate plain Python variables:

```python
# Optimized:
X = 1
_rt.write(X)
```

**Benefits**:
- Generated code looks like normal Python
- Easy for developers to refactor and maintain
- No runtime overhead from dictionary lookups and MArray allocation
- IDE autocomplete and type inference work naturally

**Why deferred**:
- Requires multi-pass analysis to prove variable doesn't escape
- Must handle edge cases: NEW, KILL, by-reference parameters
- Conservative approach (always use _scope) is always correct
- Indirection (`@VAR`) defeats static analysis for affected variables

**Analysis required**:
- Add `MLabel.local_only_vars: set[str]` - variables that don't escape label scope
- Add `MLabel.scalar_vars: set[str]` - variables never accessed with subscripts
- Track variables read/written by called routines transitively
- Identify variables subject to indirection (fallback to _scope)

**Related code**:
- `src/m2py/analysis/variables.py` - existing variable analysis
- `src/m2py/codegen/expressions.py` - `_generate_variable()`
- `src/m2py/codegen/statements.py` - `_generate_set()`

---

## Eliminate Redundant m_num() Calls

**Current approach**: All arithmetic operands are wrapped in `m_num()` for MUMPS numeric coercion:

```python
# MUMPS: S X=3+5
_scope.setdefault('X', MArray()).value = (m_num(3) + m_num(5))

# MUMPS: S Y=A+B+C
... = (m_num(m_num(_scope.get('A',...).value) + m_num(_scope.get('B',...).value)) + m_num(_scope.get('C',...).value))
```

**Potential optimization**: Skip `m_num()` when operand type is already known to be numeric:

```python
# Literal integers are already numeric:
X = 3 + 5  # No m_num needed

# Result of arithmetic is already numeric:
Y = m_num(A) + m_num(B) + m_num(C)  # No nested m_num on intermediate results
```

**Benefits**:
- Cleaner generated code, especially for arithmetic-heavy routines
- Obvious that `3 + 5` equals `8` - no helper obscuring intent
- Easier to refactor: developer can see the math directly

**Why deferred**:
- Requires type tracking through expressions
- Current approach is always correct (m_num on numeric is identity)
- Overhead is negligible for typical MUMPS workloads

**Analysis required**:
- Add `MExpr.known_type: Optional[str]` - "numeric", "string", "boolean", None
- Propagate types: `MLiteral(INTEGER)` → numeric, `MBinaryOp(+)` result → numeric
- Codegen checks `known_type` before emitting `m_num()`

**Related code**:
- `src/m2py/asg/expressions.py` - add `known_type` field
- `src/m2py/codegen/expressions.py` - `_generate_binary_op()`
- `src/m2py/codegen/helpers.py` - `m_num()`

---

## Simplify m_compare() to Python Operators

**Current approach**: All comparisons use `m_compare()` helper:

```python
# MUMPS: I X=Y
_test = m_truth(m_compare(_scope.get('X',...).value, "=", _scope.get('Y',...).value))

# MUMPS: I N>10
_test = m_truth(m_compare(_scope.get('N',...).value, ">", 10))
```

**Potential optimization**: When operand types are known, use Python operators directly:

```python
# String equality (both operands are string literals):
_test = X == Y  # m_compare with "=" is string equality

# Numeric comparison (both operands are known numeric):
_test = N > 10  # Direct Python comparison

# Mixed/unknown: keep m_compare for safety
_test = m_compare(A, ">", B)
```

Additionally, `m_truth()` after `m_compare()` is always redundant since `m_compare()` already returns `bool`:

```python
# Current (redundant):
_test = m_truth(m_compare(X, "=", Y))

# Simplified:
_test = m_compare(X, "=", Y)  # Already returns bool
```

**Benefits**:
- `X == Y` is immediately understandable vs `m_compare(X, "=", Y)`
- Standard Python comparison operators work with IDE tooling
- Easier to refactor into idiomatic Python

**Why deferred**:
- MUMPS comparison semantics differ from Python:
  - `=` is string equality (compares string representations)
  - `<` and `>` are numeric (coerce both operands)
- Type tracking required to prove when Python operators are equivalent
- `m_compare()` is always correct; simplification risks subtle bugs

**Analysis required**:
- Type propagation to identify numeric vs string contexts
- Track `m_compare()` return type as boolean for `m_truth()` elimination
- Conservative: only simplify when both operand types are proven

**Related code**:
- `src/m2py/codegen/expressions.py` - `_generate_binary_op()`
- `src/m2py/codegen/helpers.py` - `m_compare()`, `m_truth()`

---

## Reduce m_truth() Usage

**Current approach**: Every IF condition is wrapped in `m_truth()`:

```python
# MUMPS: I X
_test = m_truth(_scope.get('X',...).value)
if _test:

# MUMPS: I X>10
_test = m_truth(m_compare(...))  # Redundant - m_compare returns bool
```

**Potential optimization**: Skip `m_truth()` when expression type is already boolean:

```python
# After m_compare (already bool):
_test = m_compare(X, ">", 10)  # No m_truth wrapper

# After boolean operators (', AND, OR in MUMPS):
_test = not m_truth(X)  # Outer m_truth is Python bool, no wrapping needed

# Python bool literals:
_test = True  # No m_truth(True) needed
```

**Benefits**:
- `if X > 10:` reads better than `if m_truth(m_compare(X, ">", 10)):`
- Reduces nesting depth in generated code
- Boolean results are obviously boolean

**Why deferred**:
- Requires type tracking to prove expression is boolean
- Current approach handles all MUMPS truth semantics correctly
- Edge cases: MUMPS treats "0" as false, "" as false, "00" as false

**Analysis required**:
- Track `MExpr.known_type == "boolean"` for comparison results
- Track return types of boolean-producing operations
- Only eliminate `m_truth()` when type is proven boolean

**Related code**:
- `src/m2py/codegen/statements.py` - `_generate_if()`
- `src/m2py/codegen/helpers.py` - `m_truth()`

---

## Unified Type Analysis Pass

The optimizations above (m_num elimination, m_compare simplification, m_truth reduction) share a common prerequisite: **expression type tracking**. A unified analysis pass could:

1. **Propagate known types through expressions**:
   - `MLiteral(INTEGER/DECIMAL)` → numeric
   - `MLiteral(STRING)` → string
   - `MBinaryOp(+,-,*,/,\,#)` → numeric (result of arithmetic)
   - `MBinaryOp(=,<,>)` via `m_compare` → boolean
   - `MUnaryOp(')` → boolean (logical NOT)
   - `MVariable` → unknown (unless tracked)

2. **Track variable types within label scope**:
   - If `S X=1` and X is never assigned string → X is numeric
   - If X is only used in arithmetic → treat as numeric context

3. **Provide hints to codegen**:
   - `MExpr.known_type: Optional[Literal["numeric", "string", "boolean"]]`
   - `MExpr.needs_coercion: bool` - False if type matches context

**Benefits**:
- Single analysis pass enables multiple codegen simplifications
- Foundation for more advanced optimizations (constant folding, etc.)
- Generated code progressively approaches idiomatic Python

**Why deferred**:
- Significant analysis infrastructure investment
- MUMPS dynamic typing makes type inference inherently limited
- Current "always wrap" approach is correct and maintainable

**Related code**:
- `src/m2py/analysis/` - new `type_analysis.py`
- `src/m2py/asg/expressions.py` - add type fields
- All codegen expression/statement generators

---

## Extract State-to-Scope Sync Helper

**Current approach**: The logic for syncing `RoutineState` variables back to `_scope` is duplicated ~14 times across three files:

```python
# Pattern repeated in multiple locations:
if uses_dynamic:
    _scope.update({k: v for k, v in state._locals.items()})
else:
    for field in state.__dataclass_fields__:
        val = getattr(state, field)
        if val is not None:
            _scope[field] = val
```

**Locations**:
- `src/m2py/runtime/__init__.py` - 6 occurrences (in `resolve_goto_target`, `call_external_with_offset`, `run_with_goto_support`)
- `src/m2py/codegen/routine.py` - 4 occurrences (GotoExternal handlers in trampoline)
- `src/m2py/codegen/statements.py` - 4 occurrences (external DO calls)

**Proposed refactoring**: Create a runtime helper function:

```python
# In src/m2py/runtime/__init__.py
def sync_state_to_scope(state, scope: Dict[str, Any], uses_dynamic_locals: bool) -> None:
    """Sync RoutineState variables back to scope dict.
    
    MUMPS has a single symbol table - variables set in a called routine
    must be visible to the caller. This function ensures state changes
    propagate back to the shared scope dictionary.
    
    Args:
        state: RoutineState dataclass instance
        scope: Shared scope dictionary (_scope)
        uses_dynamic_locals: True if state has _locals dict, False for static fields
    """
    if uses_dynamic_locals:
        scope.update({k: v for k, v in state._locals.items()})
    else:
        for field in state.__dataclass_fields__:
            val = getattr(state, field)
            if val is not None:
                scope[field] = val
```

Then codegen emits:
```python
ctx.emitter.line("sync_state_to_scope(state, _scope, uses_dynamic)")
```

**Benefits**:
- Single source of truth for sync logic
- Easier to fix bugs (one place to change)
- Cleaner generated code
- Testable in isolation

**Why deferred**:
- Current duplication works correctly
- Refactoring touches critical control flow paths
- Risk of subtle scope visibility bugs during transition

**Related code**:
- `src/m2py/runtime/__init__.py` - `resolve_goto_target()`, `run_with_goto_support()`
- `src/m2py/codegen/routine.py` - `_generate_trampoline_code()`
- `src/m2py/codegen/statements.py` - `_generate_single_target_do()`

---

## Extract Postcondition Evaluation to Runtime

**Current approach**: Postcondition evaluation via `execute_mumps` is duplicated in codegen:

```python
# In src/m2py/codegen/indirection.py (generate_indirect_do):
ctx.emitter.line("_pc_temp_var = 'ZPOSTCOND'")
ctx.emitter.line(f"_pc_scope = dict({scope_ref})")
ctx.emitter.line("_rt.execute_mumps(f'S {_pc_temp_var}={_call_target.postcondition}', _pc_scope)")
ctx.emitter.line("_pc_result = _pc_scope.get(_pc_temp_var)")
ctx.emitter.line("if isinstance(_pc_result, MArray):")
# ... 8 more lines of boilerplate

# Same pattern in src/m2py/codegen/statements.py (_generate_multi_target_indirect_goto)
```

**Proposed refactoring Option A**: Extract to codegen helper:

```python
# In src/m2py/codegen/helpers.py or indirection.py
def emit_postcondition_check(ctx: "GeneratorContext", scope_ref: str) -> None:
    """Emit code to evaluate _call_target.postcondition and skip if false."""
    ctx.emitter.line("if _call_target.postcondition:")
    with ctx.emitter.indented():
        # ... all the evaluation logic
```

**Proposed refactoring Option B**: Move evaluation into runtime:

```python
# In src/m2py/runtime/__init__.py
def evaluate_postcondition(self, postcondition: str, scope: Dict[str, Any]) -> bool:
    """Evaluate a MUMPS postcondition expression.
    
    Args:
        postcondition: MUMPS expression string (e.g., "X>0", "A=B")
        scope: Current scope dictionary
        
    Returns:
        True if postcondition is truthy, False otherwise
    """
    temp_var = "ZPOSTCOND"
    temp_scope = dict(scope)
    self.execute_mumps(f"S {temp_var}={postcondition}", temp_scope)
    result = temp_scope.get(temp_var)
    if isinstance(result, MArray):
        result = result.value
    return result not in (0, "", "0", None)
```

Then codegen emits simply:
```python
ctx.emitter.line("if _call_target.postcondition and not _rt.evaluate_postcondition(_call_target.postcondition, _scope):")
ctx.emitter.line("    continue")
```

**Benefits**:
- Option A: Reduces codegen duplication while keeping evaluation inline
- Option B: Simpler generated code, testable runtime method, single responsibility
- Both: Easier to modify postcondition semantics in one place

**Why deferred**:
- Current duplication is only 2 places
- Option B adds function call overhead per postcondition check
- Both options require coordinated changes across files

**Related code**:
- `src/m2py/codegen/indirection.py` - `generate_indirect_do()`
- `src/m2py/codegen/statements.py` - `_generate_multi_target_indirect_goto()`
- `src/m2py/runtime/__init__.py` - `MUMPSRuntime`

---

## Factor Out Nested handle_goto_external Helper

**Current approach**: In `resolve_goto_target()`, a nested helper function `handle_goto_external()` is defined inside a closure (`offset_wrapper`):

```python
def resolve_goto_target(goto: GotoExternal) -> Callable[..., Any]:
    # ... 50 lines of setup ...
    def offset_wrapper(_rt, _scope=None, ...):
        # ... 20 lines of state setup ...
        def handle_goto_external(_goto, state, uses_dynamic):
            # Sync state back to scope BEFORE transferring control
            if uses_dynamic:
                _scope.update({k: v for k, v in state._locals.items()})
            else:
                for field in state.__dataclass_fields__:
                    # ...
            run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
        # ... uses handle_goto_external in multiple try/except blocks ...
```

**Problems**:
- Nested function is hard to test in isolation
- Logic duplicates what `run_with_goto_support()` does at a higher level
- Closure captures make reasoning about scope difficult
- Similar patterns exist in `run_with_goto_support()` and `call_external_with_offset()`

**Proposed refactoring**: Factor to module-level function with explicit parameters:

```python
def _handle_nested_goto_external(
    goto: GotoExternal,
    state: Any,
    scope: Dict[str, Any],
    uses_dynamic_locals: bool,
    runtime: "MUMPSRuntime",
) -> None:
    """Handle GotoExternal exception by syncing state and transferring control.
    
    Called when a routine raises GotoExternal to transfer to another routine.
    Syncs current state to scope before control transfer to maintain MUMPS
    symbol table semantics.
    """
    sync_state_to_scope(state, scope, uses_dynamic_locals)
    run_with_goto_support(resolve_goto_target(goto), runtime, scope)
```

**Benefits**:
- Testable in isolation
- Clear parameter contract (no closure captures)
- Single implementation for all GotoExternal handling
- Easier to reason about control flow

**Why deferred**:
- Requires careful analysis of closure variable usage
- `offset_wrapper` has complex state management that may need restructuring
- Current nested approach works correctly

**Related code**:
- `src/m2py/runtime/__init__.py` - `resolve_goto_target()`, `run_with_goto_support()`, `call_external_with_offset()`

---

## Unify resolve_do_targets API for Postcondition Handling

**Current approach**: `resolve_do_targets()` returns `List[CallTarget]` with postcondition strings attached. Codegen then emits code to evaluate postconditions:

```python
# Runtime returns targets with unevaluated postconditions:
CallTarget(label="LABEL", routine=None, offset=None, postcondition="X>0")

# Codegen emits evaluation logic:
for _call_target in _call_targets:
    if _call_target.postcondition:
        # ... 10 lines of execute_mumps evaluation ...
        if not truthy:
            continue
    # execute target
```

**Problem**: Two different callers (DO and GOTO codegen) both implement postcondition evaluation, leading to duplication.

**Proposed refactoring**: Add optional evaluation to the runtime:

```python
# Option A: Eager evaluation (filter in resolve_do_targets)
def resolve_do_targets(
    self, 
    target_str: str, 
    scope: Dict[str, Any],
    evaluate_postconditions: bool = False,  # New parameter
) -> List[CallTarget]:
    """...
    If evaluate_postconditions=True, only returns targets whose postconditions
    evaluate to true. Postcondition field will be None in returned targets.
    """

# Option B: Separate filter method
def filter_by_postcondition(
    self,
    targets: List[CallTarget],
    scope: Dict[str, Any],
) -> List[CallTarget]:
    """Return only targets whose postconditions evaluate to true."""
```

**Benefits**:
- Codegen becomes simpler: `_call_targets = _rt.resolve_do_targets(..., evaluate_postconditions=True)`
- Postcondition evaluation logic in one place
- Easier to test postcondition edge cases

**Why deferred**:
- DO and GOTO have different postcondition semantics:
  - DO: Execute all targets whose postconditions pass
  - GOTO: Execute first target whose postcondition passes
- Lazy vs eager evaluation affects state (postcondition may depend on prior target's effects)
- Current explicit approach makes semantics clear in generated code

**Related code**:
- `src/m2py/runtime/__init__.py` - `resolve_do_targets()`, `parse_call_target()`
- `src/m2py/codegen/indirection.py` - `generate_indirect_do()`
- `src/m2py/codegen/statements.py` - `_generate_multi_target_indirect_goto()`

---

## Consider ScopeManager Abstraction

**Current approach**: The `_scope` dictionary flows through multiple layers with manual sync operations:

1. **Caller** creates/passes `_scope` dict
2. **Generated code** creates `RoutineState` dataclass, copies from `_scope`
3. **Trampoline** passes both `state` and `_scope` to label functions
4. **Runtime** (`resolve_do_targets`, `execute_mumps`) reads/writes `_scope`
5. **Generated code** syncs `RoutineState` back to `_scope` at various points

**Problems**:
- Easy to forget sync in new code paths
- State/scope duality creates confusion
- Changes to sync logic require updates in multiple places

**Proposed abstraction**:

```python
class ScopeManager:
    """Manages MUMPS symbol table with automatic state synchronization.
    
    Provides a unified interface for variable access that handles
    the RoutineState ↔ _scope synchronization automatically.
    """
    def __init__(self, scope: Dict[str, Any], state: Optional[Any] = None):
        self._scope = scope
        self._state = state
        self._uses_dynamic = hasattr(state, '_locals') if state else False
    
    def get(self, name: str) -> Any:
        """Get variable value (checks state first, then scope)."""
        
    def set(self, name: str, value: Any) -> None:
        """Set variable value (updates both state and scope)."""
    
    def sync_to_scope(self) -> None:
        """Ensure all state changes are reflected in scope."""
    
    def as_dict(self) -> Dict[str, Any]:
        """Return scope dict for passing to runtime methods."""
```

**Benefits**:
- Single abstraction for all variable access
- Automatic sync eliminates manual sync calls
- Testable in isolation
- Foundation for future optimizations (lazy sync, change tracking)

**Why deferred**:
- Significant refactoring across codegen and runtime
- Current approach, while verbose, is explicit about when syncs occur
- Performance implications of abstraction layer unknown
- Risk of subtle bugs during transition

**Related code**:
- All files that use `_scope` dict
- `src/m2py/codegen/routine.py` - RoutineState generation
- `src/m2py/runtime/__init__.py` - runtime methods using scope

---

## Contributing

When adding optimizations to this document, include:
1. Current approach and its rationale
2. Proposed optimization with concrete benefits
3. Why it was deferred (complexity, correctness risk, etc.)
4. Prerequisites or triggers for revisiting
5. Related code locations
