# Special Variables API Contract

**Spec 011**: Extended Operators, Commands & Completion

## Special Variable List

| MUMPS | Abbreviation | Description | Implementation |
|-------|--------------|-------------|----------------|
| `$TEST` | `$T` | IF condition result | Already in Spec 005 |
| `$HOROLOG` | `$H` | Days,seconds timestamp | Runtime method |
| `$JOB` | `$J` | Process ID | `os.getpid()` |
| `$IO` | - | Current I/O device | Runtime field |
| `$X` | - | Column position | Runtime tracking |
| `$Y` | - | Line position | Runtime tracking |
| `$STORAGE` | `$S` | Available memory | Large constant |
| `$STACK` | `$ST` | Call stack level | Runtime counter |
| `$QUIT` | `$Q` | 1 if in extrinsic | Context flag |

## Codegen Patterns

```python
def _generate_special_variable(var: MSpecialVariable, ctx) -> str:
    name = var.name.upper()
    
    match name:
        case "TEST" | "T":
            return "int(_test)"
        case "HOROLOG" | "H":
            return "_rt.horolog()"
        case "JOB" | "J":
            return "os.getpid()"
        case "IO":
            return "_rt.io()"
        case "X":
            return "_rt.x()"
        case "Y":
            return "_rt.y()"
        case "STORAGE" | "S":
            return "2147483647"
        case "STACK" | "ST":
            return "_rt.stack_level()"
        case "QUIT" | "Q":
            return "_rt.quit_flag()"
        case _:
            raise NotImplementedError(f"${var.name}")
```

## Runtime Implementation

### $HOROLOG

```python
import datetime

def horolog(self) -> str:
    """Return MUMPS $HOROLOG format: days,seconds.
    
    Days since December 31, 1840 (MUMPS epoch).
    Seconds since midnight.
    """
    now = datetime.datetime.now()
    epoch = datetime.date(1840, 12, 31)
    days = (now.date() - epoch).days
    seconds = now.hour * 3600 + now.minute * 60 + now.second
    return f"{days},{seconds}"
```

### $X / $Y Column and Line Tracking

```python
class MUMPSRuntime:
    def __init__(self):
        self._x = 0  # Column position (0-based internally)
        self._y = 0  # Line position
    
    def x(self) -> int:
        return self._x
    
    def y(self) -> int:
        return self._y
    
    def write(self, value):
        s = str(value)
        for char in s:
            if char == '\n':
                self._x = 0
                self._y += 1
            elif char == '\f':
                self._x = 0
                self._y = 0
            else:
                self._x += 1
        print(s, end='')
```

### $STACK

```python
class MUMPSRuntime:
    def __init__(self):
        self._stack_depth = 0
    
    def stack_level(self) -> int:
        return self._stack_depth
    
    def push_frame(self):
        self._stack_depth += 1
    
    def pop_frame(self):
        self._stack_depth -= 1
```

### $QUIT

The `$QUIT` value depends on invocation context:
- `0` at main level or in DO-called subroutine
- `1` inside extrinsic function (`$$label`)

```python
# Option 1: Runtime flag
class MUMPSRuntime:
    def __init__(self):
        self._in_extrinsic = False
    
    def quit_flag(self) -> int:
        return 1 if self._in_extrinsic else 0

# Option 2: Function parameter
def LABEL(_rt, _scope=None, _is_extrinsic=False):
    # $QUIT returns _is_extrinsic
    pass
```

## Validation Scenarios

| MUMPS | Expected Output Format |
|-------|----------------------|
| `W $H` | `NNNNN,NNNNN` (e.g., `67585,77643`) |
| `W $J` | Positive integer (process ID) |
| `W $IO` | Device name (e.g., `"0"` or `/dev/tty`) |
| `W "ABC" W $X` | `ABC3` |
| `W $STACK` | `0` at main level |
| `W $STORAGE` | Large positive integer |
| `W $Q` | `0` at main, `1` in extrinsic |
