# Research: YDB Test Suite Failure Resolution

**Spec**: [spec.md](spec.md) | **Date**: 2026-01-22

## R1: TRAMPOLINE Implementation Architecture

### Decision
TRAMPOLINE strategy already generates RoutineState dataclass with fields for cross-label variables. Enhancement required: add local variable dictionary for argumentless KILL/NEW.

### Findings

**Current Implementation** (`src/m2py/codegen/shared_state.py`):
- `generate_routine_state_class(routine)` creates RoutineState dataclass
- Fields: simple variables (Any = None), array variables (MArray = field(default_factory=MArray))
- Variables sourced from `routine.routine_state_vars` and `routine.array_vars`

**TRAMPOLINE Flow** (`src/m2py/codegen/routine.py`):
1. Strategy selected when `routine.needs_trampoline` is True
2. `generate_routine_state_class()` generates dataclass definition
3. `state = RoutineState()` created at routine entry
4. Labels receive `state` parameter and read/write fields

**Gap for Argumentless KILL/NEW**:
- Current RoutineState only has statically-known fields
- Argumentless `KILL` needs to clear ALL local variables, including dynamic ones
- Argumentless `NEW` needs to save/restore entire variable namespace

### Rationale
RoutineState needs a `_locals: dict[str, Any]` field to track dynamic variables. KILL would clear this dict; NEW would push/pop it via stack pattern.

### Alternatives Considered
1. **Convert all variables to dict-based**: Rejected - loses type safety for known variables
2. **Separate locals dict outside RoutineState**: Rejected - breaks state passing contract
3. **Hybrid approach (chosen)**: Add `_locals` dict field to RoutineState, use for dynamic access

---

## R2: Variable Analysis for NEW/KILL

### Decision
Variable analysis pass in `src/m2py/analysis/variables.py` already tracks NEW/KILL scopes. Enhancement required: track dynamic variable patterns.

### Findings

**Current Implementation** (`src/m2py/analysis/variables.py`):
- `ScopeVariables` dataclass tracks: reads, writes, newed, formal_params
- Handles selective NEW (`NEW X,Y`) and exclusive NEW (`NEW (X,Y)`)
- `MNewStatement.exclusive` flag indicates argumentless NEW

**Key Classes**:
```python
@dataclass
class ScopeVariables:
    reads: Set[str]
    writes: Set[str]
    newed: Set[str]
    formal_params: Set[str]
    input_variables: Set[str]
    output_variables: Set[str]
```

**Gap**:
- Analysis identifies NEW/KILL targets but codegen doesn't handle argumentless variants
- Need to propagate "has_argumentless_kill" and "has_argumentless_new" flags to codegen

### Rationale
Add flags to `MRoutine` ASG node indicating presence of argumentless KILL/NEW. Codegen checks these to include `_locals` dict in RoutineState.

---

## R3: Sorts-After Operator

### Decision
`m_sorts_after()` helper already implemented in `src/m2py/runtime/helpers.py`. Codegen in `src/m2py/codegen/expressions.py` uses it.

### Findings

**Implementation** (`src/m2py/runtime/helpers.py:1204`):
```python
def m_sorts_after(left: Any, right: Any) -> int:
    """Check if left strictly sorts after right (MUMPS ]] operator)."""
```

**Usage** (`src/m2py/codegen/expressions.py:563`):
```python
# Sorts after: A]]B returns 1 if A strictly sorts after B
return f"m_sorts_after({left}, {right})"
```

**If failures exist**: May be bug in collation logic, not missing implementation.

### Rationale
No new implementation needed. Debug existing helper against MUMPS spec.

---

## R4: LHS $PIECE Current Scope

### Decision
LHS $PIECE implemented for local variables and globals. Gap: indirection (`S $P(@X,"^",1)=Y`) not supported.

### Findings

**Current Implementation** (`src/m2py/codegen/statements.py:916`):
- `_generate_lhs_piece()` handles:
  - Local variables: `MVariable` → getter/setter lambdas
  - Global variables: `GlobalVariable` → `_rt.globals.get/set`
- Generates `m_set_piece(getter, setter, delimiter, from, to, value)`

**Gap Identified**:
```python
elif isinstance(first_arg, MVariable):
    # ... handled
elif isinstance(first_arg, GlobalVariable):
    # ... handled
else:
    raise NotImplementedError(
        f"LHS $PIECE first argument must be a variable, got {type(first_arg).__name__}"
    )
```

**Missing case**: `MIndirection` as first argument

### Rationale
Need to add indirection support by evaluating the indirected expression at runtime to determine target.

---

## R5: LIM-015 Z-Extensions

### Decision
Z-commands/Z-functions intentionally unsupported (YDB-specific). Configure xfail for affected tests.

### Findings

**Current Configuration** (`src/m2py/limitations.py:326`):
```python
"LIM-015": Limitation(
    id="LIM-015",
    title="Z-Commands/Z-Functions Not Supported",
    ...
)
```

**Commands raising LIM-015** (`src/m2py/codegen/statements.py:728-752`):
- ZALLOCATE, ZDEALLOCATE, ZBREAK, ZCOMPILE, ZCONTINUE
- ZEDIT, ZHELP, ZMESSAGE, ZPRINT, ZSTEP, ZSYSTEM, ZTRIGGER

**Affected tests** (per failure-analysis.md):
- V1SVH (uses $ZHOROLOG)
- V2ZTRG (uses ZTRIGGER)
- V2ZB (uses ZBREAK)
- etc. (12 total)

### Rationale
Tests should be marked xfail with reason "LIM-015: Z-extension". No code changes needed.

---

## R6: Merge Suite Infrastructure

### Decision
Merge tests use different infrastructure than mugj/basic (separate drivers, outrefs). Need investigation of test harness.

### Findings

**Structure** (`tests/functional/test_merge.py`):
- Uses `MERGE_SUBTESTS` from `suite_definitions.py`
- Each subtest has its own outref file
- Outref contains YDB infrastructure output (database setup, replication)

**Key difference from mugj/basic**:
- mugj/basic: Single outref file per suite
- merge: Multiple outrefs, one per subtest (`outref/gbl2gbl.txt`, etc.)
- Outref filtering may not be stripping infrastructure output correctly

**Potential issues**:
1. Outref mismatch due to YDB infrastructure output
2. Missing outref files for some subtests
3. Test harness not loading correct outref

### Rationale
Debug test harness to ensure correct outref loaded and filtered. May need enhanced outref normalization.

---

## Summary of Required Changes

| Area | Change | Files |
|------|--------|-------|
| TRAMPOLINE | Add `_locals` dict to RoutineState | `shared_state.py`, `routine.py` |
| Variable Analysis | Track argumentless KILL/NEW presence | `variables.py`, `elements.py` |
| Codegen | Handle argumentless KILL/NEW | `statements.py` |
| LHS $PIECE | Add indirection support | `statements.py` |
| Tests | Configure LIM-015 xfails | `suite_definitions.py` or test files |
| merge suite | Debug infrastructure/outref | `test_merge.py`, `conftest.py` |

---

## NEEDS CLARIFICATION: NONE

All technical unknowns resolved through codebase research.
