# Research: Unified Variable/Expression/Indirection/Subscript System

**Feature Branch**: `018-unified-variable-system`  
**Research Date**: 2025-01-25  
**Sources**: MUGJ test suite, YDB docker verification, codebase analysis, MUMPS specification

---

## Executive Summary

This research documents the comprehensive investigation of MUMPS variable semantics, indirection behavior, and the existing m2py infrastructure. The findings inform the design of a unified variable system that correctly handles all variable access patterns while maintaining the Constitution's requirement for layer separation and minimized runtime surface.

**Key Findings**:
1. **Name vs Argument Indirection** is the critical distinction - fundamentally different evaluation semantics
2. **Multi-level indirection** with per-level subscripts is well-defined but complex
3. **Existing infrastructure** is substantial and largely correct - unification, not replacement, is needed
4. **Subscript canonicalization** applies only to numeric literals, not string values
5. **Recursive @-expressions** require runtime parsing (value contains @ → re-evaluate)

---

## 1. Indirection Semantics Deep Dive

### 1.1 Name Indirection vs Argument Indirection

**Critical Discovery**: These are fundamentally different operations that happen to share the same `@` syntax.

#### Name Indirection (SET, WRITE, KILL, etc.)

The resolved value is used **as a variable identifier** to look up or set a value.

```mumps
; Example: S A="B",B=5  W @A  → outputs "5"
; Resolution: @A → read A → "B" → look up B → 5
```

**YDB Verification**:
```
$ echo 'TEST S A="B",B=5 W @A Q' | docker run --rm -i ydb
5
```

**Error Behavior**: If the resolved value is not a valid variable name, error `VAREXPECTED`:
```
$ echo 'TEST S A="1+1" S @A=5 Q' | docker run --rm -i ydb
%YDB-E-VAREXPECTED, Variable expected in this context
```

#### Argument Indirection (IF, FOR conditions, XECUTE, etc.)

The resolved value is **evaluated as a MUMPS expression** - the result is the expression's value, not a variable lookup.

```mumps
; Example: S A="1=0" I @A  → condition is FALSE
; Resolution: @A → read A → "1=0" → evaluate as expression → 0 (false)
```

**YDB Verification**:
```
$ echo 'TEST S A="1=0" I @A W "TRUE" E  W "FALSE" Q' | docker run --rm -i ydb
FALSE

$ echo 'TEST S A="X>5",X=10 I @A W "TRUE" E  W "FALSE" Q' | docker run --rm -i ydb
TRUE
```

**Empty String Behavior** ⚠️ **YDB-Specific Edge Case**:

| Test | Command | Result |
|------|---------|--------|
| Non-indirection | `I ""` | FALSE (empty→0→false) |
| Indirected via variable | `S A="" I @A` | **TRUE** (unexpected!) |
| Direct literal indirection | `I @""` | **TRUE** (unexpected!) |

```bash
# Verified 2025-01-25:
printf 'TEST\n I "" W "TRUE"\n E  W "FALSE"\n Q\n' | docker run --rm -i ydb
# Output: FALSE

printf 'TEST\n S A="" I @A W "TRUE"\n E  W "FALSE"\n Q\n' | docker run --rm -i ydb
# Output: TRUE (!)
```

This appears to be YDB-specific behavior where the indirection operation itself succeeds (returns empty),
and the empty result in IF context is treated differently than a literal empty string.
**Needs further investigation** against MUMPS specification.

In name context, empty string is error:
```
$ echo 'TEST S @""=5 Q' | docker run --rm -i ydb
%YDB-E-VAREXPECTED
```

### 1.2 Multi-Level Indirection

Multi-level indirection (`@@VAR`, `@@@VAR`) resolves each `@` level sequentially from outside-in.

```mumps
; S A="B",B="C",C=99 W @@A  → outputs "99"
; Resolution: @@A → @(value of A) → @"B" → value of B → "C" → value of C → 99
```

**YDB Verification**:
```
$ echo 'TEST S A="B",B="C",C=99 W @@A Q' | docker run --rm -i ydb
99
```

### 1.3 Per-Level Subscripts (@X@(subs) syntax)

The `@X@(subs)` syntax applies subscripts **after** name resolution, before value lookup:

```mumps
; S X="A",A(1,2)="hello" W @X@(1,2)  → outputs "hello"
; Resolution: @X → "A", then @"A"@(1,2) → A(1,2) → "hello"
```

**Multi-level with subscripts** (MUGJ VV2VNIA II-127):
```mumps
; S X="A",A(1,2)="B(3,4)" S @@X@(1,2)@(5,6)=1
; Resolution:
;   @X → "A"
;   @"A"@(1,2) → A(1,2) → "B(3,4)"  
;   @"B(3,4)"@(5,6) → B(3,4,5,6) = 1
```

**YDB Verification**:
```
$ echo 'TEST S X="A",A(1,2)="B(3,4)" S @@X@(1,2)@(5,6)=1 W B(3,4,5,6) Q' | docker run --rm -i ydb
1
```

### 1.4 Recursive @-Expressions (Value Contains @)

When the resolved value itself starts with `@`, it triggers recursive evaluation:

```mumps
; S A="@B",B="C",C=99 W @@A
; Resolution:
;   @A → "@B" (contains @!)
;   @"@B" → recursively evaluate @B → "C" → variable C → 99
```

**YDB Verification**:
```
$ echo 'TEST S A="@B",B="C",C=99 W @@A Q' | docker run --rm -i ydb
99
```

MUGJ V1IDNM2 I-503 tests this with intrinsic functions:
```mumps
S A="@$E(""ABCDEF"",3)",B="@$E(""ABCDEF"",4)",D=40
S @A=@B  ; @A evaluates $E→"C"→@C; @B evaluates $E→"D"→@D→40
W C      ; outputs 40
```

### 1.5 Subscript Indirection

Indirection can appear **within subscripts**:
```mumps
S B="C",C=3 W A(1,@B,5)  ; equivalent to W A(1,3,5)
```

These are evaluated during subscript construction, left-to-right.

---

## 2. Subscript Canonicalization

### 2.1 Numeric Canonicalization Rules

**MUMPS Rule**: Numeric values have a single canonical form. The canonical form has:
- No leading zeros (except for pure "0")
- No trailing zeros after decimal
- No decimal point for integers

| Input | Canonical Form |
|-------|----------------|
| `1` | `1` |
| `01` | `1` |
| `1.0` | `1` |
| `1.50` | `1.5` |
| `0.5` | `.5` |
| `.50` | `.5` |

### 2.2 String vs Numeric Subscripts

**Critical Finding**: String subscripts are NOT automatically canonicalized.

```mumps
S A(1)="one"
S A("01")="zero-one"  ; These are DISTINCT nodes!
W A(01)    ; → "one" (numeric 01 → 1)
W A("01")  ; → "zero-one" (string "01" preserved)
```

**YDB Verification**:
```
$ echo 'TEST S A(1)="one" S A("01")="zero-one" W A(01),!,A("01") Q' | docker run --rm -i ydb
one
zero-one

$ echo 'TEST S A("01")="NOPE" W $D(A(1)),!,$D(A("01")) Q' | docker run --rm -i ydb
0
1
```

**Implication**: Canonicalization happens at parse time for numeric literals, but string values preserve their exact form. The string `"1"` is treated as numeric because it's purely numeric, but `"01"` is preserved.

Actually, let me verify:
```
$ echo 'TEST S A(1)="x" W A("1") Q' | docker run --rm -i ydb
x
```

So `A("1")` DOES access the same node as `A(1)`. The canonicalization applies when the string is purely numeric. The string "01" has leading zero so it's NOT purely numeric in the canonical sense.

---

## 3. Existing Infrastructure Analysis

### 3.1 ASG Layer (`src/m2py/asg/`)

#### MIndirection Class (expressions.py)
```python
@dataclass
class MIndirection(MExpr):
    expression: MExpr = None           # The @-expression source
    indirection_type: IndirectionType = IndirectionType.UNKNOWN
    subscripts: List[MExpr] = None     # For @X(1,2) form
    name_indirection_subscripts: List[List[MExpr]] = None  # For @X@(1,2)@(3,4)
    can_resolve_statically: bool = False
    resolved_value: str = None
    requires_runtime_eval: bool = True
```

#### IndirectionType Enum (enums.py)
```python
class IndirectionType(Enum):
    NAME = "name"           # Variable name lookup
    SUBSCRIPT = "subscript" # Within subscript expression  
    ARGUMENT = "argument"   # Full expression evaluation
    PATTERN = "pattern"     # Pattern match context
    UNKNOWN = "unknown"     # Not yet classified
```

**Assessment**: ASG structure is correct. The distinction between `subscripts` (for `@X(1,2)`) and `name_indirection_subscripts` (for `@X@(1,2)`) properly captures the MUGJ test patterns.

### 3.2 Parser Layer (`src/m2py/parser/`)

#### textx_classes.py - Indirection
```python
class Indirection(MIndirection):
    """
    Grammar: Indirection: '@' expr=PrimaryExpr subscripts=Subscripts? 
                         name_subscripts+=NameIndirectionSubscripts*;
    """
    def __init__(self, parent=None, expr=None, subscripts=None, name_subscripts=None):
        # Properly captures @X, @X(1,2), @X@(1,2), @X@(1)@(2)
```

**Assessment**: Parser correctly builds MIndirection nodes with proper subscript separation.

### 3.3 Analysis Layer (`src/m2py/analysis/`)

#### semantic_analyzer.py
- `_classify_indirection()`: Classifies type, attempts static resolution
- Sets `IndirectionType.ARGUMENT` for IF conditions
- Sets `IndirectionType.NAME` as default

**Key Code Path** (IF command analysis):
```python
def _analyze_IfCommand(self, cmd, parent):
    # ...
    if isinstance(analyzed, MIndirection):
        analyzed.indirection_type = IndirectionType.ARGUMENT
```

**Assessment**: Analysis correctly identifies argument indirection contexts. However, indirection classification is scattered across command-specific analyzers.

### 3.4 Codegen Layer (`src/m2py/codegen/`)

#### indirection.py (1252 lines!)

Key functions:
- `_count_indirection_levels()`: Count `@@...` depth
- `_count_indirection_levels_with_subscripts()`: Collect all subscripts per level
- `generate_name_indirection()`: Generate read via @VAR
- `generate_name_indirection_write()`: Generate write via @VAR=
- `generate_argument_indirection()`: For IF @A, DO @X
- `generate_multi_level_indirection()`: For @@VAR, @@@VAR

**Key Pattern - Multi-level Resolution**:
```python
def _count_indirection_levels_with_subscripts(indirection):
    """Returns (count, [subscripts_per_level])"""
    # Handles @X, @@X, @@@X, @X@(1)@(2), @@X@(1)@(2,3)
```

**Assessment**: Codegen is comprehensive but complex. The 1252 lines suggest incremental accumulation. Key issue: scope management fragmentation between `_scope` and Python locals.

### 3.5 Runtime Layer (`src/m2py/runtime/`)

#### Key Functions (__init__.py)
- `resolve_indirection(name, levels, _scope)`: Resolves N levels of indirection
- `get_var(name, _scope)`: Get variable by name string  
- `set_var(name, value, _scope)`: Set variable by name string
- `append_subscripts(name, subscripts)`: Build subscripted name string
- `execute_mumps(code, _scope)`: Parse and execute MUMPS string (for XECUTE)

**resolve_indirection Implementation** (lines 2890-3100):
```python
def resolve_indirection(self, name, levels, _scope):
    """Resolve N levels of name indirection."""
    current = name
    for _ in range(levels):
        current = self.get_var(current, _scope)
        if not self._is_valid_var_name(current):
            raise ...  # VAREXPECTED
    return self.get_var(current, _scope)
```

**Assessment**: Runtime has the core functionality but:
1. No argument indirection support (expression evaluation)
2. No recursive @-expression handling
3. Name translation may not be consistent with codegen

---

## 4. MUGJ Test Pattern Catalog

### 4.1 V1IDNM Series (Name Indirection)

| Test | Pattern | Key Behavior |
|------|---------|--------------|
| I-491 | `@A` basic | Simple one-level name resolution |
| I-492 | `@@A` | Two-level resolution |
| I-493 | `@@@A` | Three-level resolution |
| I-494 | `@A(1)` | Indirection with subscripts |
| I-495 | `@(A_B)` | Dynamic expression as indirection source |
| I-496 | `@$E(...)` | Intrinsic function result as variable name |
| I-497 | `@A=value` | SET target is indirection |
| I-503 | `@"@$E(...)"` | Recursive @-expression in value |
| I-507 | `@@A*2` | Multi-level in expression |
| I-508 | `@@@B(1)` | Three levels with subscripts |

### 4.2 VV2VNI Series (Variable Name Indirection)

| Test | Pattern | Key Behavior |
|------|---------|--------------|
| II-120 | `@X@(subs)` | Name indirection subscripts (local) |
| II-121 | `@"lit"@(subs)` | Literal string with name indirection subs |
| II-122 | `@(expr)@(subs)` | Complex expression + name indirection |
| II-123 | `@^GVN@(subs)` | Global variable name indirection |
| II-124 | `@@^GVN@(subs)` | Two-level global indirection |
| II-125 | `@@@^GVN@(subs)` | Three-level global indirection |
| II-126 | `@^V(3)@(@^V(2)@(4))` | Subscript contains indirection |
| II-127 | `@@X@(1,2)@(5,6)` | Multi-level with per-level subscripts |
| II-129 | Naked after `@A@(subs)` | Naked indicator updated by indirection |
| II-130 | `@B@("A")` in postcondition | Indirection in postcondition |
| II-132.3 | `@@@@A` where values contain `@` | Recursive @-expression evaluation |
| II-135 | XECUTE with `@B@(subs)` | Name indirection inside XECUTE |

### 4.3 V1IDARG Series (Argument Indirection)

| Test | Pattern | Key Behavior |
|------|---------|--------------|
| I-417 | `I @A` where A="1" | Evaluates "1" as expression → true |
| I-417 | `I @A` where A="1=0" | Evaluates "1=0" → false (NOT "1=0"→true!) |
| I-420 | `I @@^V(100)` | Two-level argument indirection |
| I-421 | `I @@@^V(2)` | Three-level argument indirection |
| I-422 | `I @^V(101)` where value has operator | Value contains expression with operator |

### 4.4 V1IDDO/V1IDGO Series (DO/GOTO Indirection)

| Test | Pattern | Key Behavior |
|------|---------|--------------|
| I-461 | `D @A` | Simple label indirection |
| I-462 | `D @L` where L="@L(1)" | Recursive label indirection |
| I-463 | `D @A+offset` | Label indirection with offset |
| I-466 | `D ^@A` | Routine name indirection |
| I-467 | `D @A^@C` | Both label and routine indirection |

---

## 5. Decision Points and Design Implications

### 5.1 Decision: Unified Resolution Pipeline

**Rationale**: Both name and argument indirection share the first N-1 resolution steps. Only the final step differs (variable lookup vs expression evaluation).

**Design**:
```
resolve_indirection(source, levels, context) →
  1. For each level 1..N-1: resolve as name indirection
  2. Final step:
     - NAME context: return variable value
     - ARGUMENT context: evaluate as expression
```

### 5.2 Decision: Recursive @-Expression Handling

**Rationale**: MUGJ tests (II-132.3, I-503) require that if a resolved value starts with `@`, it triggers recursive evaluation.

**Design**: After resolution, check if result starts with `@`. If so, recursively resolve:
```python
def resolve_value(value, context, _scope):
    if value.startswith("@"):
        return resolve_indirection(value, 1, context, _scope)
    return value  # or lookup if NAME context
```

### 5.3 Decision: Subscript Handling Strategy

**Rationale**: Per-level subscripts (`@X@(1)@(2)`) are applied BETWEEN resolution levels.

**Design**:
```
resolve_with_subscripts(expr, subscripts_per_level, context) →
  current = resolve(expr)
  for subs in subscripts_per_level:
    current = append_subscripts(current, subs)
    current = resolve(current)  # Resolve the subscripted reference
  final_step(current, context)
```

### 5.4 Decision: Name Translation Consolidation

**Rationale**: Constitution VII requires shared implementation. Current split between codegen and runtime.

**Design**: Create `src/m2py/core/names.py`:
```python
def translate_mumps_to_python(name: str) -> str:
    """Single source of truth for MUMPS→Python name translation."""
    if name.startswith("%"):
        return "_pct_" + name[1:]
    if name[0].isdigit():
        return "_n_" + name
    if name in PYTHON_KEYWORDS:
        return "_m_" + name
    return name
```

### 5.5 Decision: Scope Unification

**Rationale**: Variable access currently splits between Python locals and `_scope` dict depending on scope strategy. This causes "variable not found" bugs.

**Design**: Create `CurrentScope` abstraction:
```python
class CurrentScope:
    """Unified variable access regardless of storage mechanism."""
    def get(self, name: str, default="") -> Any
    def set(self, name: str, value: Any) -> None
    def exists(self, name: str) -> bool
```

Implementation adapts to actual storage (locals, _scope, state._locals).

### 5.6 Decision: Expression Evaluation for Argument Indirection

**Rationale**: Argument indirection requires parsing and evaluating MUMPS expressions at runtime. Current `execute_mumps()` executes commands, not expressions.

**Design**: Add `evaluate_expression(expr_str, _scope)`:
```python
def evaluate_expression(self, expr_str: str, _scope: Dict) -> Any:
    """Evaluate MUMPS expression string, return value."""
    # Wrap in SET to temp var: "S _TEMP=<expr>"
    # Execute and retrieve _TEMP
    # Or: Parse expression directly if simpler
```

---

## 6. Integration Points

### 6.1 Parser Integration

**No changes needed**. Parser correctly builds MIndirection with:
- `expression`: The @-expression source
- `subscripts`: For `@X(subs)` form
- `name_indirection_subscripts`: For `@X@(subs)` form

### 6.2 Analysis Integration

**Enhancement needed**: Consolidate indirection classification into single pass.

Currently scattered:
- `_classify_indirection()` for general classification
- `_analyze_IfCommand()` sets ARGUMENT type
- `_analyze_SetCommand()` checks for argument indirection in SET @A

**Consolidation**:
- Move to `_classify_indirection()` 
- Pass context from parent command analysis
- Use visitor pattern or context stack

### 6.3 Codegen Integration

**Strategy**: Per-command migration (Constitution compliance).

Phase 1: Migrate SET command
- Replace current SET indirection with unified resolver calls
- Remove dead code after migration
- Validate with MUGJ V1IDNM2 tests

Phase 2: Migrate WRITE, KILL
- Same pattern
- Dead code cleanup

Phase 3: Migrate IF, FOR (argument indirection)
- Use expression evaluation path
- Validate with V1IDARG tests

Phase 4: Migrate DO, GOTO
- Label/routine indirection
- Validate with V1IDDO tests

### 6.4 Runtime Integration

**New functions needed**:
- `evaluate_expression(expr_str, _scope)`: For argument indirection
- `resolve_name_indirection(name, levels, subscripts_per_level, _scope)`: Enhanced multi-level

**Existing functions to enhance**:
- `get_var()`: Use unified name translation
- `set_var()`: Use unified name translation
- `resolve_indirection()`: Support recursive @-expressions

---

## 7. Risk Analysis

### 7.1 High Risk: Argument Indirection Expression Evaluation

**Risk**: Parsing MUMPS expressions at runtime is complex. The `execute_mumps()` approach using full transpilation is heavy.

**Mitigation**: 
1. First validate with MUGJ tests using current infrastructure
2. Consider lightweight expression parser for simple cases
3. Fall back to full transpile for complex expressions

### 7.2 Medium Risk: Scope Unification Breaking Existing Tests

**Risk**: Changing variable access patterns may break working code.

**Mitigation**:
1. Build CurrentScope as adapter over existing storage
2. Migrate one command at a time
3. Run full test suite after each migration

### 7.3 Low Risk: Name Translation Inconsistencies

**Risk**: Shared name translation may expose latent bugs.

**Mitigation**:
1. Build comprehensive unit tests from MUGJ patterns
2. Test both directions (MUMPS→Python, Python→MUMPS for runtime parsing)

---

## 8. Test Strategy

### 8.1 Unit Tests from MUGJ

Extract each MUGJ test pattern into standalone unit tests:

```python
# From V1IDNM2 I-503
def test_name_indirection_with_recursive_at():
    """Value of indirection contains @-expression with function."""
    # S A="@$E(""ABCDEF"",3)",B="@$E(""ABCDEF"",4)",D=40
    # S @A=@B  ; Sets C=40
    assert C == 40
```

### 8.2 YDB Validation Tests

For each extracted test, validate against YDB:
```bash
uv run python utils/validate.py --code 'TEST S A="@$E(""ABCDEF"",3)" ...'
```

### 8.3 Regression Testing

After each migration phase:
1. Run existing test suite
2. Run new MUGJ-extracted tests
3. Run YDB validation on key patterns

---

## 9. Unresolved Questions → RESOLVED

All clarification questions have been resolved through YDB verification and MUGJ test analysis:

| Question | Resolution |
|----------|------------|
| Name vs Argument indirection distinction? | Resolved - FR-010/011/012 in spec |
| Multi-level subscript application order? | Resolved - Applied between levels |
| Recursive @-expression handling? | Resolved - If value starts with @, re-evaluate |
| Subscript canonicalization for strings? | Resolved - Numeric strings canonicalize, non-numeric preserve |
| Empty string in argument context? | Resolved - Succeeds, evaluates to false |
| Error on invalid name in name context? | Resolved - VAREXPECTED error |

---

## 10. Appendix: YDB Verification Commands

```bash
# Name indirection basic
echo 'TEST S A="B",B=5 W @A Q' | docker run --rm -i ydb

# Argument indirection - expression evaluation
echo 'TEST S A="1=0" I @A W "TRUE" E  W "FALSE" Q' | docker run --rm -i ydb

# Multi-level with subscripts
echo 'TEST S X="A",A(1,2)="B(3,4)" S @@X@(1,2)@(5,6)=1 W B(3,4,5,6) Q' | docker run --rm -i ydb

# Recursive @-expression
echo 'TEST S A="@B",B="C",C=99 W @@A Q' | docker run --rm -i ydb

# Subscript canonicalization
echo 'TEST S A(1)="one" S A("01")="zero-one" W A(01),!,A("01") Q' | docker run --rm -i ydb

# Error case - invalid name
echo 'TEST S A="1+1" S @A=5 Q' | docker run --rm -i ydb 2>&1

# Empty string in contexts
echo 'TEST S @""=5 Q' | docker run --rm -i ydb 2>&1  # Error
echo 'TEST I @"" W "HI" Q' | docker run --rm -i ydb   # No error, false
```

---

## 11. Architectural Challenges Analysis

**Deep codebase analysis performed** to identify challenges that could affect migration. These findings inform Phase 0 planning.

### 11.1 Three Scope Storage Mechanisms

**Problem**: Variables are stored inconsistently across three mechanisms:

| Mechanism | Location | Usage |
|-----------|----------|-------|
| `_scope` dict | Passed as parameter | Most generated code |
| `state.VAR` fields | State object attributes | Legacy TRAMPOLINE patterns |
| `state._locals` dict | State object internal | Some DO calls |

**Files Affected**:
- `codegen/statements.py` - Uses all three patterns
- `codegen/indirection.py` - `_get_scope_expr()` (L38-44) attempts unification
- `runtime/__init__.py` - Only knows about `_scope` dict

**Implication**: `CurrentScope` must adapt to all three; `_get_scope_expr()` is a starting point but not used consistently.

### 11.2 Duplicate Name Translation

**Problem**: MUMPS→Python name translation exists in two places:

1. **codegen/names.py** - `NameTranslator` class with `translate()`/`reverse()` methods
2. **runtime/__init__.py** (L113-148) - `_translate_label_to_func()` function

The runtime version is documented as: *"mirrors the logic in m2py.codegen.names.translate_name but is provided here for runtime use to avoid circular imports"*

**Resolution**: Move to `src/m2py/core/names.py`, import from both codegen and runtime to eliminate duplication and ensure consistency.

### 11.3 Two Runtime Resolution Functions

**Problem**: Runtime has two indirection resolution functions:

| Function | Returns | Used For |
|----------|---------|----------|
| `resolve_indirection()` | VALUE | SET @A=5, WRITE @A |
| `resolve_indirection_name()` | NAME | SET @A=5 (left-hand side) |

**Assessment**: This distinction is correct but maps to our `IndirectionContext.VALUE` vs `IndirectionContext.TARGET` in contracts. The `IndirectionResolver` interface unifies these.

### 11.4 MArray .value Extraction Inconsistency

**Problem**: MArray values are extracted inconsistently:

**In codegen** (indirection.py L445):
```python
if isinstance(val, MArray):
    val = val.value
```

**In runtime** (various locations):
```python
value = var.value if hasattr(var, 'value') else var
```

**Implication**: FR-038 requires ALWAYS extracting `.value` from MArray. `CurrentScope.get()` must enforce this consistently.

### 11.5 Strategy Conditionals Scattered

**Problem**: 50+ conditionals like `ctx.strategy == GotoStrategy.TRAMPOLINE` scattered through codegen files:
- `codegen/statements.py` - ~25 occurrences
- `codegen/routine.py` - ~15 occurrences
- `codegen/indirection.py` - ~10 occurrences

**Implication**: Strategy-specific scope handling must be abstracted into `CurrentScope` to reduce these conditionals.

### 11.6 Code Expected to be Deprecated

Based on analysis, the following code areas will be replaced by unified components:

| File | Lines (approx) | Replacement |
|------|----------------|-------------|
| `codegen/indirection.py` L150-400 | ~250 | IndirectionResolver |
| `codegen/names.py` | ~80 | core/names.py NameTranslator |
| `runtime/__init__.py` L113-148 | ~35 | Import from core/names.py |
| `codegen/indirection.py` `_get_scope_expr()` | ~6 | CurrentScope.scope_expr() |
| Scattered `.value` extraction | ~20 sites | CurrentScope.get() |

**Total**: ~400 lines expected to be replaced/consolidated

### 11.7 MUGJ Torture Test Patterns

From VV2VNIB, the most complex patterns that integration tests must verify:

| ID | Pattern | Complexity |
|----|---------|------------|
| II-131 | `@B@(@B@(@B@(9)),@B,I)` | Deep nesting + mixed subscript indirection |
| II-132.1 | Value contains `@B@(1)` | Recursive @-expression in value |
| II-132.3 | `@@@@A` where each level contains @-expressions | 4-level chain with recursive resolution |
| I-417 (V1IDARG) | `I @A S B=1` where `A=""` | Empty string in argument context |
| I-420 | `I @A` where `A="1=0"` | Expression evaluation in IF |
| I-421 | `DO @A` where `A="ROUTINE^ENTRY"` | Label indirection in DO |

These patterns must pass before migration is considered complete.

---

## 12. Plan Validation Findings (2025-01-25)

Cross-validation of plan against learnings.md and actual codebase implementation.

### 12.1 Critical Bug Confirmed: Argument Indirection Expression Evaluation

**Status**: ❌ SEMANTIC CORRECTNESS BUG

The learnings document (Section 10) explicitly warned about this:
> *"For `I @A` where `A="1=0"`: **Wrong**: `m_truth("1=0")` → `m_num("1=0")` → `1` → true"*

The current codebase has this exact bug in `generate_argument_indirection()` ([codegen/indirection.py#L416](src/m2py/codegen/indirection.py#L416)):

```python
# Returns string value to m_truth(), does NOT evaluate as expression
return value_expr  # BUG: "1=0" string → m_truth("1=0") → 1 → TRUE
```

**Verified via YDB**:
```bash
# Expected: FALSE (evaluates 1=0 as expression)
printf 'TEST\n S A="1=0" I @A W "TRUE"\n E  W "FALSE"\n Q\n' | docker run --rm -i ydb
# Output: FALSE

# Current m2py: TRUE (WRONG - treats "1=0" as string)
uv run python utils/validate.py --code 'TEST S A="1=0" I @A W "TRUE" E  W "FALSE" Q'
# m2py: 'TRUE' ← BUG
```

### 12.2 Addressed Learnings (Verified in Codebase)

| Learning | Status | Evidence |
|----------|--------|----------|
| MArray .value extraction | ✅ Addressed | `m_str`, `m_num`, `m_truth` all have T075h handlers |
| F-string trap | ✅ Addressed | Codebase uses string concatenation patterns |
| Recursive @-expression | ✅ Addressed | `resolve_nested_indirection()` handles `@` prefixes |

### 12.3 Documentation Fix Required

**learnings.md Section 11** states:
> *"Empty string: `S A="" I @A` → Succeeds (evaluates to truthy - YDB-specific behavior)"*

**research.md previously stated** (now corrected):
> *"`I @""` → false"*

**Actual YDB behavior** (verified 2025-01-25):
- `I ""` → FALSE (empty string converts to 0)
- `S A="" I @A` → **TRUE** (indirection of empty succeeds as truthy)

This YDB-specific edge case needs test coverage and may require spec clarification.

### 12.4 Validation Summary

| Concern | Plan Coverage | Action |
|---------|--------------|--------|
| Name vs Argument indirection | ✅ Comprehensive | IndirectionContext enum |
| Expression evaluation bug | ⚠️ Identified, needs fix | Challenge 6 added, evaluate_expression() required |
| Three scope mechanisms | ✅ Addressed | CurrentScope unification |
| Name translation duplication | ✅ Addressed | Move to core/names.py |
| Empty string edge case | ⚠️ Documented | Add torture test |
| Naked indicator with indirection | ✅ FR-028 | Add II-129 to torture tests |
| Evaluation order | ✅ FR-019 | Left-to-right guaranteed |
