# Research: LHS Functions & Global Variables (Spec 009)

**Date**: 2025-01-20  
**Status**: Complete

## Executive Summary

This research resolved all technical unknowns for implementing LHS functions ($PIECE, $EXTRACT), subscripted local variables, global variables, naked references, $DATA, and KILL commands. The parser already correctly captures all required constructs - only codegen and runtime changes are needed.

---

## R1: Parser/CST Node Mapping

### Decision
Use existing textX CST nodes - no parser changes required.

### Findings

Parser output validated for each construct:

| MUMPS Construct | CST Node Type | Key Attributes |
|-----------------|---------------|----------------|
| `$P(X,"^",2)` (LHS) | `IntrinsicFunction` | `name='P'`, `arguments=[LocalVariable, StringLiteral, NumericLiteral]` |
| `$E(X,2,3)` (LHS) | `IntrinsicFunction` | `name='E'`, `arguments=[LocalVariable, NumericLiteral, ...]` |
| `^G("a")` | `GlobalVariable` | `name='G'`, `subscripts=[StringLiteral]` |
| `^(2)` (naked) | `NakedGlobal` | `subscripts=[NumericLiteral]` |
| `X(1,2)` | `LocalVariable` | `name='X'`, `subscripts=[NumericLiteral, ...]` |

### Rationale
textX parser already distinguishes LHS $PIECE/EXTRACT from RHS - they both appear as `IntrinsicFunction`, but in SET assignments the target field contains them. Codegen must detect `IntrinsicFunction` in target position.

---

## R2: LHS $PIECE Semantics

### Decision
Create `m_set_piece(var_name, delim, piece_num, value, scope)` runtime helper.

### YDB Reference Output
```
MUMPS: S X="A^B^C" S $P(X,"^",2)="NEW" W X,!
YDB:   A^NEW^C
```

### Semantics
- `$P(var,delim,n)=value` replaces the nth piece (1-indexed)
- If n > current piece count, pads with empty pieces
- First argument is the target variable (may be subscripted)
- Standard: 1977__a107074.md (SET with function arguments)

---

## R3: LHS $EXTRACT Semantics

### Decision
Create `m_set_extract(var_name, start, end, value, scope)` runtime helper.

### YDB Reference Output
```
MUMPS: S X="HELLO" S $E(X,2,3)="XX" W X,!
YDB:   HXXLO
```

### Semantics
- `$E(var,from,to)=value` replaces characters from `from` to `to` (1-indexed, inclusive)
- If value shorter than range, string shrinks
- If value longer than range, string expands
- First argument is the target variable

---

## R4: Subscripted Local Variables

### Decision
Use MArray for subscripted locals via `_scope` dictionary.

### Current State
Codegen generates: `_scope['X'][1] = 1`
But `_scope['X']` doesn't exist when first accessed.

### Required Change
Codegen must auto-vivify with MArray:
```python
if 'X' not in _scope:
    _scope['X'] = MArray()
_scope['X'][1] = 1
```

Or use dict.setdefault pattern in generated code.

### YDB Reference
```
MUMPS: S X(1)=1 W X(1),!
YDB:   1
```

---

## R5: Global Variable Storage

### Decision
Use `GlobalStorageBackend` protocol with `InMemoryGlobalStorage` as default.

### Design
```python
class GlobalStorageBackend(Protocol):
    def get(self, name: str, subscripts: tuple) -> str | None: ...
    def set(self, name: str, subscripts: tuple, value: str) -> None: ...
    def kill(self, name: str, subscripts: tuple) -> None: ...
    def data(self, name: str, subscripts: tuple) -> int: ...
    def get_naked_indicator(self) -> tuple[str, tuple] | None: ...
```

### YDB Reference
```
MUMPS: S ^G("a")=1 W ^G("a"),!
YDB:   1
```

### Rationale
- Protocol allows swapping backends (InMemory, YottaDB, IRIS)
- `InMemoryGlobalStorage` uses nested dict/MArray structure
- Global storage separate from local `_scope` dict

---

## R6: Naked Reference Tracking

### Decision
Track last global reference in `GlobalStorageBackend.get_naked_indicator()`.

### YDB Reference
```
MUMPS: S ^G(1)=1,^(2)=2 W ^(2),!
YDB:   2
```

### Semantics
- After any global access `^NAME(s1,s2)`, naked indicator becomes `(^NAME, (s1,))`
- `^(x)` expands to `^NAME(s1,x)` using stored indicator
- Error if no prior global reference in execution

---

## R7: $DATA Function

### Decision
Implement as `m_data(variable, scope)` runtime helper.

### YDB Reference
```
MUMPS: S X(1)=1,X(1,2)=3 W $D(X),"-",$D(X(1)),"-",$D(X(1,2)),!
YDB:   10-11-1
```

### Return Values
| Code | Meaning |
|------|---------|
| 0 | Not defined |
| 1 | Defined, no descendants |
| 10 | Not defined at this level, has descendants |
| 11 | Defined AND has descendants |

### MArray Integration
MArray already tracks both `.value` and `._children` - $DATA maps directly:
- `0`: no value, no children
- `1`: has value, no children  
- `10`: no value, has children
- `11`: has value, has children

---

## R8: KILL Command

### Decision
Add `MKillStatement` codegen handler calling `MArray.kill()` or `_globals.kill()`.

### YDB Reference
```
MUMPS: S X=1,X(1)=2 K X(1) W $D(X),"-",$D(X(1)),!
YDB:   1-0
```

### Semantics
- `K X` kills X and all descendants
- `K X(1)` kills only that node and its descendants
- Parent value preserved (X still has value 1 after K X(1))

---

## Alternatives Considered

### Alt 1: Use Python dicts directly instead of MArray
**Rejected**: Cannot model "has value AND has children" semantics needed for $DATA 11.

### Alt 2: Separate nakedness tracking from storage backend  
**Rejected**: Naked indicator is tightly coupled to global access patterns.

### Alt 3: Parse-time LHS function detection
**Rejected**: Parser already captures correctly as IntrinsicFunction - semantic distinction is target vs expression position, handled in codegen.

---

## Dependencies

| Dependency | Purpose | Status |
|------------|---------|--------|
| MArray class | Sparse array with value+children | ✅ Exists in runtime |
| `_scope` dict | Local variable storage | ✅ Exists from spec 008 |
| IntrinsicFunction parsing | LHS function capture | ✅ Parser works |
| GlobalVariable parsing | Global reference capture | ✅ Parser works |
| NakedGlobal parsing | Naked reference capture | ✅ Parser works |

---

## Implementation Implications

1. **No parser changes** - All constructs already parse correctly
2. **Runtime additions**: 
   - `m_set_piece()` helper
   - `m_set_extract()` helper  
   - `m_data()` helper
   - `GlobalStorageBackend` protocol
   - `InMemoryGlobalStorage` class
3. **Codegen changes**:
   - Extend `_generate_set()` for GlobalVariable, NakedGlobal, IntrinsicFunction targets
   - Add `_generate_kill()` handler
   - Auto-vivify MArray for subscripted locals
   - Generate $DATA calls as `m_data()` invocations
