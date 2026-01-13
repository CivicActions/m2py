# Quickstart: External Calls & Cross-Routine Infrastructure

**Spec**: 008-external-calls

## Overview

This spec enables MUMPS programs to call external routines (`D ^ROUTINE`, `$$FUNC^ROUTINE`) and access source code lines (`$TEXT`). After implementation, multi-routine MUMPS programs can be transpiled and executed.

## Prerequisites

- Spec 007 complete (line dispatch, source_lines)
- Python 3.10+
- `uv` for package management

## Quick Test

After implementation, verify external calls work:

```bash
# Create test routines directory
mkdir -p /tmp/test_ext

cat > /tmp/test_ext/main.m << 'EOF'
MAIN W "Starting",!
 D ^helper
 W "Done",!
 Q
EOF

cat > /tmp/test_ext/helper.m << 'EOF'
HELPER W "In helper",!
 Q
EOF

# Transpile both routines
uv run python -m m2py /tmp/test_ext/main.m -o /tmp/test_ext/main.py
uv run python -m m2py /tmp/test_ext/helper.m -o /tmp/test_ext/helper.py

# Run with search path (standard Python)
PYTHONPATH=/tmp/test_ext uv run python /tmp/test_ext/main.py
```

Expected output: `Starting\nIn helper\nDone\n`

## API Usage

### Configure Search Paths

Use standard Python mechanisms - no special runtime configuration needed:

```python
# Option 1: Modify sys.path at entry point
import sys
sys.path.insert(0, "/path/to/routines")
sys.path.insert(0, "/path/to/more/routines")

# Option 2: Use PYTHONPATH environment variable
# PYTHONPATH=/path/to/routines:/path/to/more python main.py
```

### Generated Code Pattern

When transpiling `D ^ext2`, the generated Python becomes:

```python
import ext2
ext2.ext2(_rt, _scope)  # Entry label matches routine name (VistA convention)
```

For `$$FUNC^ext2(X,Y)` (with $TEST isolation):

```python
import ext2
_saved_test = _rt._test
try:
    result = ext2.FUNC(_rt, _scope, X, Y)
finally:
    _rt._test = _saved_test
```

## Common Patterns

### External DO

```mumps
; Call entry label of routine
MAIN D ^utility Q

; Call specific label
MAIN D HELPER^utility Q

; Call with arguments
MAIN D ADD^math(1,2) Q
```

### External GOTO

```mumps
; Transfer control permanently (no return)
MAIN G ^dispatcher

; Transfer to specific label
MAIN G ERROR^handler
```

### Extrinsic Functions

```mumps
; Call function and use return value
MAIN S X=$$CALC^math(10,20)
 W X,!
 Q
```

### $TEXT Function

```mumps
; Get first line of current routine
MAIN W $T(+1),!
 Q

; Get line from external routine  
MAIN W $T(+1^utility),!
 Q

; Get label line from external routine
MAIN W $T(HELPER^utility),!
 Q
```

## Troubleshooting

### "Routine 'X' not found"

Check that:
1. File `X.m` exists in one of the search paths
2. Search paths are correctly configured
3. Filename matches routine name exactly

### "Label 'Y' not found in routine 'X'"

Check that:
1. The label exists in the routine file
2. Label name matches exactly (case-sensitive in Python)

### Variables not visible across routines

Ensure:
1. `_scope` dictionary is passed to all calls
2. Variable wasn't NEWed in the callee

## File Structure

```
specs/008-external-calls/
├── spec.md          # Full specification
├── plan.md          # Implementation plan
├── research.md      # Technical decisions
├── data-model.md    # Data structures
├── quickstart.md    # This file
└── tasks.md         # Implementation tasks (after /speckit.tasks)
```
