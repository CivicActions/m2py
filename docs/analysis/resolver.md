# Reference Resolution

The resolver links `MCall` references to their target `MLabel` objects and builds back-references.

**Source**: [`src/m2py/analysis/resolver.py`](../../src/m2py/analysis/resolver.py)

## Overview

Reference resolution:

1. Builds a label lookup table for the routine
2. Scans all statements for `MCall` objects (in GOTO, DO)
3. Resolves each `MCall.target` to its `MLabel`
4. Populates back-references (`MLabel.callers`, `MLabel.goto_sources`)

## Usage

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")
parser.resolve_references(routine)

# Now MCall.target is populated
for label in routine.labels:
    for stmt in label.body.walk_statements():
        if isinstance(stmt, MDoStatement):
            for call in stmt.targets:
                if call.is_resolved:
                    print(f"DO {call.name} -> {call.target.name}")
```

## What Gets Populated

### On MCall

| Field | Value |
|-------|-------|
| `target` | The resolved `MLabel`, or `None` |
| `is_resolved` | `True` if successfully resolved |
| `call_type` | Classification (see below) |

### On MLabel

| Field | Value |
|-------|-------|
| `callers` | List of `MCall` from DO statements |
| `goto_sources` | List of `MCall` from GOTO statements |

## Call Type Classification

During resolution, each `MCall` is classified:

| CallType | Condition | Example |
|----------|-----------|---------|
| `LABEL_CALL` | Local label, no offset | `D LABEL` |
| `OFFSET_CALL` | Local label with offset | `D LABEL+2` |
| `ROUTINE_CALL` | External routine | `D LABEL^ROUTINE` |
| `INDIRECT_CALL` | Indirection present | `D @CMD` |
| `UNRESOLVED` | Label not found | Unknown label |

## Resolution Rules

### Local Calls

```mumps
D MYLABEL    ; Resolved to MYLABEL in same routine
G LOOP       ; Resolved to LOOP in same routine
```

- Looked up in label map
- `is_resolved = True` if found
- Back-reference added to target label

### External Calls

```mumps
D UTIL^LIBRARY    ; External - not resolved
G END^CLEANUP     ; External - not resolved
```

- `call_type = ROUTINE_CALL`
- `is_resolved = False`
- Not added to back-references (target not loaded)

### Indirect Calls

```mumps
D @CMD           ; Indirect - cannot resolve
D @LABEL^@ROUT   ; Both parts indirect
```

- `call_type = INDIRECT_CALL`
- `is_resolved = False`

## Helper Functions

### get_unresolved_calls

Get all calls that could not be resolved:

```python
from m2py.analysis.resolver import get_unresolved_calls

unresolved = get_unresolved_calls(routine)
for call in unresolved:
    print(f"Unresolved: {call.name} (type={call.call_type})")
```

### get_external_calls

Get all calls to external routines:

```python
from m2py.analysis.resolver import get_external_calls

external = get_external_calls(routine)
for call in external:
    print(f"External: {call.name}^{call.routine}")
```

## Back-Reference Usage

Back-references enable analysis of callers:

```python
# Find all callers of a label
for label in routine.labels:
    if label.callers:
        print(f"{label.name} is called by:")
        for caller in label.callers:
            # Find the statement containing this call
            print(f"  - DO from somewhere")
    
    if label.goto_sources:
        print(f"{label.name} is jumped to by {len(label.goto_sources)} GOTOs")
```

## Code Generation Implications

| CallType | Code Generation Strategy |
|----------|-------------------------|
| `LABEL_CALL` | Direct function call |
| `OFFSET_CALL` | May need $TEXT source lookup |
| `ROUTINE_CALL` | Import from other module |
| `INDIRECT_CALL` | Runtime dispatch |
| `UNRESOLVED` | Error or runtime lookup |

## Example

```mumps
TEST   D INIT
       G:DONE END
       D PROCESS^UTIL
       Q
INIT   S X=1
       Q
END    W "Done",!
       Q
```

After resolution:

```
MCall(name="INIT") -> MLabel(name="INIT")
  call_type=LABEL_CALL, is_resolved=True
  
MCall(name="END") -> MLabel(name="END")
  call_type=LABEL_CALL, is_resolved=True
  
MCall(name="PROCESS", routine="UTIL") -> None
  call_type=ROUTINE_CALL, is_resolved=False
```

Back-references:
```
MLabel(name="INIT").callers = [MCall from DO INIT]
MLabel(name="END").goto_sources = [MCall from G:DONE END]
```
