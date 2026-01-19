# Research Notes: Test Suite Consolidation & VistA Compatibility

**Spec**: 013-test-consolidation  
**Phase**: 0 - Research  
**Date**: 2026-01-17

## Research Tasks

### 1. Existing Infrastructure Review

#### 1.1 Test Fixture Architecture

**Finding**: The `execute_mumps` fixture is the standard pattern for runtime testing.

**Location**: [tests/unit/codegen/conftest.py](../../tests/unit/codegen/conftest.py)

**Usage Pattern**:
```python
def test_feature(execute_mumps):
    result = execute_mumps("TEST\n S X=1\n W X\n Q")
    assert result == "1"
```

**Decision**: All CONVERT stubs will use this pattern.  
**Rationale**: Consistent with existing spec-aligned tests, validates actual runtime behavior.  
**Alternatives Considered**: `generate_python` fixture (rejected - only checks code structure, not semantics).

#### 1.2 Database Abstraction Layer

**Finding**: GlobalStorageBackend protocol exists in [src/m2py/runtime/globals.py](../../src/m2py/runtime/globals.py)

**Current State**:
- `InMemoryGlobalStorage` - fully implemented for testing
- `YottaDBBackend` - stub, raises ImportError
- `IRISBackend` - stub, raises ImportError

**Protocol Methods Available**:
- `get`, `set`, `kill`, `kill_all`, `data` - core operations ✅
- `order`, `query`, `incr` - $ORDER/$QUERY/$INCREMENT ✅
- `kill_node` - ZKILL support ✅
- Naked indicator tracking ✅

**Missing from Protocol (needed for this spec)**:
- LOCK operations (`lock_incr`, `lock_decr`)
- Transaction operations (`tp`, `commit`, `rollback`, `tlevel`)
- SSVN queries (`^$GLOBAL`, `^$JOB`, `^$LOCK`, `^$ROUTINE`)

**Decision**: Extend `GlobalStorageBackend` protocol with lock/transaction/SSVN methods.  
**Rationale**: Constitution III requires database operations go through abstraction layer.  
**Alternatives Considered**: Separate protocol for locks (rejected - MUMPS treats globals and locks as related).

### 2. ASG Structure Review

#### 2.1 Statement ASG Nodes

**Finding**: All statement types have ASG definitions in [src/m2py/asg/statements.py](../../src/m2py/asg/statements.py)

| Statement | ASG Class | Status |
|-----------|-----------|--------|
| LOCK | `MLockStatement` | ✅ Defined (line 570) |
| VIEW | `MViewStatement` | ✅ Defined (line 585) |
| BREAK | `MBreakStatement` | ✅ Defined (line 541) |
| JOB | `MJobStatement` + `MJobTarget` | ✅ Defined (lines 690, 706) |
| OPEN/CLOSE/USE | `MOpenStatement`, `MCloseStatement`, `MUseStatement` | ✅ Defined |
| Transaction | `MTStartStatement`, `MTCommitStatement`, `MTRollbackStatement` | ⚠️ Need to verify |
| NEW (exclusive) | `MNewStatement` | ⚠️ Need exclusive syntax support |

#### 2.2 Expression ASG Nodes

**Finding**: Most expression types exist in [src/m2py/asg/expressions.py](../../src/m2py/asg/expressions.py)

| Function | Status | Notes |
|----------|--------|-------|
| $ASCII | Need to verify | Should be intrinsic function |
| $CHAR | Need to verify | Should be intrinsic function |
| $TEXT | Need to verify | Requires line mapping (Spec 007) |
| $JUSTIFY | Need to verify | Right-justify formatting |
| $TRANSLATE | Need to verify | Character translation |
| $REVERSE | Need to verify | String reversal |
| $FNUMBER | Need to verify | Numeric formatting |
| $NEXT | Need to verify | Deprecated subscript navigation |
| Math functions | Need to verify | $EXP, $LOG, $SQRT, trig |

### 3. Gaps Audit Summary

**Source**: [specs/gaps-stubs.md](../gaps-stubs.md)

| Category | DELETE | CONVERT | KEEP (implement) |
|----------|--------|---------|------------------|
| §7.2 Operators | 4 | 2 | 1 (exponentiation) |
| §8.2.18 SET | 9 | 1 | 6 (computed offsets - done in Spec 007) |
| §8.2.9 IF | 0 | TBD | TBD |
| Fall-through | 0 | 0 | 5+ |
| Z-commands | 8 | 0 | 7 (with VistA usage) |
| Math functions | 0 | 0 | 6 |
| Library functions | 0 | 0 | 68 (zero VistA usage - OUT OF SCOPE) |

**Total Estimated**:
- DELETE: ~44 stubs
- CONVERT: ~39 stubs  
- IMPLEMENT: ~200 features

### 4. Implementation Strategy Research

#### 4.1 Fall-Through Semantics

**MUMPS Behavior**: When a label body does not end with QUIT/GOTO/HALT, execution continues to the next label.

```mumps
TEST
 W "A"
FOR
 W "B"
END
 W "C"
 Q
```

Calling `D TEST` outputs "ABC".

**Decision**: Generate explicit fall-through calls at end of non-exiting labels.
```python
def TEST(_rt, _scope=None, **_kwargs):
    _rt.write("A")
    return FOR(_rt, _scope)  # Explicit fall-through

def FOR(_rt, _scope=None, **_kwargs):
    _rt.write("B")
    return END(_rt, _scope)  # Explicit fall-through
```

**Rationale**: Constitution I (semantic correctness) requires matching MUMPS behavior exactly.  
**Alternatives Considered**: 
- Linear execution model (rejected - breaks label-as-function paradigm)
- TRAMPOLINE for all labels (rejected - overkill, only GOTO needs trampoline)

#### 4.2 Database Backend Integration

**YottaDB Python API** (from yottadb package):

```python
import yottadb
# Transactions
yottadb.tp(callback, *args)  # Execute callback in transaction
# Locks
yottadb.lock_incr(name, subscripts, timeout)
yottadb.lock_decr(name, subscripts)
# Atomic increment
yottadb.incr(name, subscripts, amount)
```

**IRIS Python API** (from intersystems-iris package):

```python
import iris
irispy = iris.IRIS(connection)
# Transactions (via %Global)
irispy.tStart()
irispy.tCommit()
irispy.tRollback()
# Locks
irispy.lock(name, subscripts, timeout)
irispy.unlock(name, subscripts)
# TLevel
irispy.getTLevel()
```

**Decision**: Extend protocol with:
- `lock(name, subscripts, timeout, lock_type)` → bool
- `unlock(name, subscripts)`
- `transaction_start()`
- `transaction_commit()`
- `transaction_rollback()`
- `get_tlevel()` → int

**Rationale**: Both backends have native support; Memory backend can simulate for tests.

#### 4.3 $TEXT Implementation

**Requirement**: `$TEXT(LABEL)` returns first line of label, `$TEXT(LABEL+n)` returns nth line.

**Dependency**: Spec 007 line mapping infrastructure (`_source_lines`, `_label_lines`).

**Implementation Approach**:
```python
def _text(label, offset=0):
    line_num = _label_lines.get(label, -1)
    if line_num < 0:
        return ""
    target = line_num + offset
    if 0 <= target < len(_source_lines):
        return _source_lines[target]
    return ""
```

**Decision**: Use existing `_source_lines` and `_label_lines` from Spec 007.  
**Rationale**: Infrastructure already exists, just needs intrinsic function wrapper.

#### 4.4 Z-Commands with VistA Usage

| Z-Command | VistA Files | Implementation Approach |
|-----------|-------------|------------------------|
| ZWRITE | 54 | Format variable/global display |
| ZLINK | 20 | Dynamic routine loading (subprocess?) |
| ZSHOW | 9 | System information display |
| ZKILL | 5 | `kill_node()` in backend (already in protocol) |
| ZGOTO | 2 | Stack unwinding (complex - needs research) |
| ZHALT | 1 | `sys.exit()` with status code |
| $ZERROR | 121 | Error string special variable |

**Decision**: Implement all 7 Z-commands fully (no stubs).  
**Rationale**: Constitution I requires semantic correctness for all VistA-utilized features.

### 5. Research Conclusions

#### Unknowns Resolved

| Unknown | Resolution |
|---------|------------|
| Database abstraction for LOCK | Extend GlobalStorageBackend protocol |
| Database abstraction for transactions | Extend GlobalStorageBackend protocol |
| $TEXT dependency | Use Spec 007 infrastructure |
| Fall-through approach | Generate explicit calls to next label |
| Z-command implementation depth | Full implementation for all 7 with VistA usage |

#### Risks Identified

1. **ZGOTO complexity**: Stack unwinding may require TRAMPOLINE-like infrastructure
2. **IRIS API compatibility**: Need to verify IRIS transaction/lock semantics match YDB
3. **JOB command**: Subprocess spawning needs database connection sharing

#### Next Steps (Phase 1)

1. Design database abstraction protocol extensions (data-model.md)
2. Define contracts for new intrinsic functions (contracts/)
3. Create implementation quickstart guide (quickstart.md)
