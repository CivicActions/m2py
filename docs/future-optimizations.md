# Future Optimizations

This document tracks potential optimizations that were considered but deferred in favor of simpler, correct implementations. These can be revisited once the core transpiler is stable and performance profiling identifies actual bottlenecks.

## Cross-Routine Variable Passing (Static Analysis)

**Current approach** (Spec 008): Pass a `_scope` dictionary to all external calls. All non-NEWed variables are stored in this shared dictionary.

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

**Current approach** (Spec 014 T068-T070): Each external extrinsic call (`$$LABEL^ROUTINE`) emits its own `import` statement inline:

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

**Current approach** (Spec 008): Every generated `.py` file includes `_source_lines = [...]` with the original MUMPS source.

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

**Current approach** (Spec 010): `$PIECE` and `$EXTRACT` generate calls to runtime helper functions (`m_piece()`, `m_extract()`) that handle all edge cases including out-of-range indices, invalid positions, and range extraction.

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

## Contributing

When adding optimizations to this document, include:
1. Current approach and its rationale
2. Proposed optimization with concrete benefits
3. Why it was deferred (complexity, correctness risk, etc.)
4. Prerequisites or triggers for revisiting
5. Related code locations
