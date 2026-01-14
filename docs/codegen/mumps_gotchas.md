# MUMPS Gotchas for Python Code Generation

This document captures MUMPS semantics and edge cases that affect Python code generation. These were discovered during MUGJ validation testing.

## IF Command with Comma Conditions

MUMPS IF supports comma-separated conditions where comma acts as logical AND:

```mumps
IF X=1,Y=2 S Z=1    ; Execute SET only if both X=1 AND Y=2
```

**Key points:**
- Comma is NOT an expression operator - it separates conditions at command level
- All conditions are evaluated in order (short-circuit on first false)
- Each condition evaluation updates `$TEST`

**ASG Representation:**
- `MIfStatement.conditions` contains a list of expressions
- Single condition also populates `MIfStatement.condition` for backward compatibility

**Python Translation:**
```python
# Conceptual Python equivalent

if x == 1 and y == 2:
    z = 1
```

**Reference:** MUMPS spec 8.1.35: "IF with n arguments is equivalent in execution to n IFs, each with one argument."

---

## $TEST Special Variable

The special variable `$TEST` (`$T`) holds the result of the last IF evaluation:

```mumps
I X=1 S Y=1     ; $TEST = 1 (true) or 0 (false)
E S Y=2         ; ELSE uses $TEST from previous IF
I  S Y=3        ; Argumentless IF also uses current $TEST
```

**Key points:**
- Every IF condition updates `$TEST`
- ELSE executes when `$TEST` is false
- Argumentless IF (`I ` with no condition) tests current `$TEST` value
- Must be tracked across statements for correct ELSE behavior

**Python Translation** uses a module-level `_test` variable:
```python
from m2py.codegen.helpers import m_truth

_test = False  # Module-level $TEST tracking

def EXAMPLE():
    global _test
    _test = m_truth(X == 1)
    if _test:
        Y = 1
    if not _test:  # ELSE
        Y = 2
    if _test:  # Argumentless IF
        Y = 3
```

Each generated function declares `global _test` to share state across labels.

---

## Label Naming Rules

MUMPS allows label names that would be invalid identifiers in Python. The `NameTranslator` class in `src/m2py/codegen/names.py` handles these translations:

| Pattern | Example | Python Equivalent |
|---------|---------|-------------------|
| `%` prefix | `%ROUTINE`, `%0` | `_pct_ROUTINE`, `_pct_0` |
| Pure numeric | `0`, `01`, `012` | `_n_0`, `_n_01`, `_n_012` |
| Reserved words | `if`, `for`, `class` | `_m_if`, `_m_for`, `_m_class` |

**Key points:**
- **Case-preserving**: `FOO`, `foo`, and `Foo` remain distinct
- **Reversible**: `NameTranslator.reverse()` recovers original MUMPS name
- Leading zeros are significant: `01` ≠ `1` (both get `_n_` prefix but preserve value)
- Labels starting with `%` are common for utility routines
- Reserved word labels are parsed as labels (not commands) at line start

**Usage:**
```python
from m2py.codegen.names import NameTranslator

nt = NameTranslator()
nt.translate("%START")  # "_pct_START"
nt.translate("01")      # "_n_01"
nt.translate("if")      # "_m_if"
nt.reverse("_pct_FOO")  # "%FOO"
```

**Source:** MUGJ V1DO1.m, V1LL1.m, V1LL2.m tests

---

## Labelless First Lines

MUMPS files can have code before the first label (preamble):

```mumps
	S VCOMP="LABEL LESS"    ; No label - starts with whitespace
V1LL1	;Comment line
```

**ASG Representation:**
- Synthetic label with empty name `""` created as first label
- Contains statements from labelless lines
- `MRoutine.labels[0].name == ""` indicates preamble

**Python Translation:**
- Execute preamble code before any labeled entry point
- Or include as initialization in main module

---

## Parse-Time vs Runtime Validation

Some MUMPS constructs cannot be validated at parse time:

| Construct | Example | Validation Time |
|-----------|---------|-----------------|
| Label references | `D MYLABEL` | Parse (if internal) |
| Routine references | `D ^ROUTINE` | Runtime only |
| Pattern match validity | `X?2.1N` | Runtime (invalid repcount) |
| `$RANDOM` argument | `$R(N)` | Runtime (N may be ≤0) |
| `$SELECT` all-false | `$S(0:"x")` | Runtime error |
| Label+offset bounds | `G LBL+999` | Runtime (offset too large) |
| Indirection targets | `D @X` | Runtime |

**ASG flags:**
- `MCall.is_resolved`: False for unresolvable targets
- `MCall.call_type`: `ROUTINE_CALL`, `INDIRECT_CALL` for runtime targets
- `MXecuteStatement.requires_runtime_eval`: True for dynamic code

---

## KILL Command Semantics

MUMPS has three KILL forms with distinct semantics:

```mumps
K                 ; Kill All - delete all local variables
K X,Y,Z           ; Selective Kill - delete specific variables
K (X,Y,Z)         ; Exclusive Kill - delete ALL EXCEPT listed
K (X,Y),(X,Z)     ; Multiple exclusive - keeps intersection only
K (X,Y),Z         ; Mixed - exclusive kill, then also kill Z
```

**ASG Representation:**
- `MKillStatement.is_kill_all`: True for argumentless KILL
- `MKillStatement.targets`: List of variables for selective
- `MKillStatement.exclusive`: True for exclusive kill
- `MKillStatement.except_list`: Variables to preserve
- `MKillStatement.except_groups`: For multiple exclusive groups

**Detection:**
```python
# Conceptual Python equivalent

if len(kill_stmt.targets) == 0 and not kill_stmt.exclusive:
    # Kill All
elif kill_stmt.exclusive:
    # Exclusive Kill - preserve except_list
else:
    # Selective Kill - delete targets
```

---

## QUIT Command Ambiguity

QUIT with value vs QUIT then next command:

```mumps
Q X      ; QUIT with return value X
Q  S Y=1 ; QUIT (no value) then SET Y=1
```

**Key point:** Double space after QUIT signals argumentless QUIT followed by another command. Grammar uses negative lookahead to avoid consuming command keywords as return values.

---

## XECUTE Command Semantics

XECUTE executes a string as MUMPS code at runtime:

```mumps
X "S X=1"              ; Simple literal
X A                    ; Execute contents of A
X "D LABEL1,LABEL2"    ; Multiple commands
X A,B,C                ; Execute multiple strings
X "G DONE"             ; Control flow affects caller
```

**Key semantic points:**
1. **Runtime evaluation required** - Cannot be statically translated
2. **Variable persistence** - Changes to variables persist after XECUTE completes
3. **Self-modification** - XECUTE can KILL or modify its own source variable
4. **Control flow** - GOTO in XECUTE affects the calling context
5. **Nested XECUTE** - Can nest 2-3+ levels with escaped quotes

**ASG Representation:**
- `MXecuteStatement.arguments`: List of string expressions
- `MXecuteStatement.requires_runtime_eval`: Always True
- `MXecuteStatement.is_constant`: True if all arguments are string literals
- `MXecuteStatement.constant_values`: Extracted literal values when constant

**Python Translation Strategy:**
- Constant XECUTE with simple statements may be inlined
- Dynamic XECUTE requires runtime interpreter (e.g., `exec()` on generated Python)

---

## FOR Loop Edge Cases

### Open-Ended FOR (No End Value)

```mumps
F I=1:1 Q:I>10 W I    ; Loop until QUIT
```

Requires `while True:` with break:
```python
# Conceptual Python equivalent

i = 1
while True:
    if i > 10:
        break
    print(i)
    i += 1
```

### Step = 0 (Infinite Loop)

```mumps
F I=1:0:10 Q:DONE    ; Step 0 = infinite loop
```

### Subscripted Loop Variable

```mumps
F A(1,2)=1:1:3 S X=A(1,2)
```

Loop variable can be subscripted - requires dict-style assignment.

### Complex Parameter Expressions

```mumps
F %I=31,%Y#4=0+28,31,30,...
```

The `%Y#4=0+28` is an expression tree: `((%Y # 4) = 0) + 28`. Evaluates to 28 (non-leap) or 29 (leap year).

---

## Indirection Patterns

### Simple Indirection

```mumps
S @A=1    ; SET the variable whose name is in A
W @A      ; WRITE the value of variable named by A
```

### Name Indirection with Subscripts

```mumps
S @A@(1,2)=3   ; A contains "ARRAY", sets ARRAY(1,2)=3
```

The `@A@(subs)` pattern applies subscripts to the resolved name.

### Multi-Level Indirection

```mumps
D @@A     ; Double indirection - evaluate A, then evaluate that result
D @@@A    ; Triple indirection
```

**ASG Representation:**
- `MCall.indirection_levels`: Count of @ signs
- `MIndirection.nested`: For recursive indirection structure

---

## Format Controls in WRITE

WRITE statements can include format controls:

| Control | Meaning | ASG Type |
|---------|---------|----------|
| `!` | Newline | `MFormatControl(NEWLINE)` |
| `#` | Form feed | `MFormatControl(FORMFEED)` |
| `?n` | Tab to column n | `MFormatControl(TAB, expr=n)` |
| `*n` | Output char(n) | `MFormatControl(CHARCODE, expr=n)` |

**Postconditioned format controls:**
```mumps
W:$Y>55 #    ; Form feed only if $Y > 55
```

---

## Naked Global References

Naked globals use the last referenced global's context:

```mumps
S ^A(1,2)=1    ; Sets context: ^A with (1)
S ^(3)=2       ; Actually ^A(1,3)
S ^(4,5)=3     ; Actually ^A(1,4,5)
```

**Key points:**
- Context = global name + all subscripts except the last
- `^(subs)` replaces the last subscript with new ones
- Must track "naked indicator" at runtime

**ASG Representation:**
- `MNakedGlobal.subscripts`: The new subscripts to apply

**Runtime Requirement:** Code generation must track the "naked indicator" (last global name and subscripts) at runtime. The `MNakedGlobal` type itself signals this requirement.

---

## $SELECT Function Syntax

$SELECT uses special `condition:value` pair syntax (not standard function arguments):

```mumps
S X=$S(A=1:"ONE",A=2:"TWO",1:"OTHER")  ; Select based on conditions
```

**Key points:**
- Colon (`:`) separates condition from value (NOT an operator)
- Conditions evaluated left-to-right, first true wins
- Convention: Use `1:"default"` as last pair for default value
- If no condition is true, **runtime error** occurs

**ASG Representation:**
- `SelectFunction.arguments`: List of `(condition, value)` tuples
- Each pair is a `SelectArg` with `condition` and `value` expressions

**Python Translation:**
```python
# Conceptual Python equivalent

x = "ONE" if a == 1 else ("TWO" if a == 2 else "OTHER")
```

---

## Left-Hand $PIECE Assignment

$PIECE can appear on the left side of SET to replace substrings:

```mumps
S $P(X,"^",2)="NEW"    ; Replace second ^-piece of X
S $E(X,1,3)="ABC"      ; Replace first 3 characters
```

**Key points:**
- Modifies the variable in-place
- Creates the variable if it doesn't exist
- Pads with delimiter if piece index is beyond current length

**ASG Representation:**
- `MSetStatement.target`: Contains `IntrinsicFunction` (not just variable)
- `MAssignment.target.name`: `$PIECE` or `$EXTRACT`

**Python Translation:**
```python
# Conceptual Python equivalent

# $P(X,"^",2)="NEW" 
pieces = x.split("^")
pieces[1] = "NEW"  # 0-indexed
x = "^".join(pieces)
```

---

## Multi-Assignment SET Expansion

SET can assign to multiple targets simultaneously:

```mumps
S (A,B,C)=0        ; Set A, B, and C to 0
S A=1,B=2,C=3      ; Comma-separated individual assignments
```

**Key points:**
- `(A,B,C)=value` is syntactic sugar for assigning same value to multiple targets
- Expanded in ASG to separate `MAssignment` objects
- Different from comma-separated with different values

**ASG Representation:**
- Single `MSetStatement` with multiple `MAssignment` children
- Each assignment has its own target but shared value expression

---

## Special Variable Abbreviations

Special variables can be abbreviated to first letters:

| Full Name | Abbreviations | Meaning |
|-----------|---------------|---------|
| `$HOROLOG` | `$H` | Date/time value |
| `$JOB` | `$J` | Process ID |
| `$TEST` | `$T` | IF result flag |
| `$STORAGE` | `$S` | Available storage |
| `$IO` | `$I` | Current device |

**Known limitation:** Mixed-case special variables (`$Test`, `$TEst`) may fail to parse. Use fully uppercase or fully lowercase.

---

## Command Postconditions

Commands can have postconditions that control execution:

```mumps
S:X>0 Y=1        ; SET only if X>0
D:FLAG ROUTINE   ; DO only if FLAG is true
Q:A=""           ; QUIT only if A is empty
W:$Y>55 #        ; Form feed only if $Y>55
```

**Argument-level postconditions:**

```mumps
D LABEL1:X,LABEL2:Y   ; Call LABEL1 if X, LABEL2 if Y
S A=1:X,B=2:Y         ; Set A if X, B if Y
```

**ASG Representation:**
- `MStatement.postcondition`: Command-level condition
- `MDoArgument.postcondition`: Per-argument condition

---

## Known Parser Limitations

Some MUMPS constructs are not fully supported:

| Construct | Status | Notes |
|-----------|--------|-------|
| Indirect pattern match (`?@`) | ❌ Not parsed | `X?@PATTERN` fails |
| Mixed-case special vars | ❌ Not parsed | `$Test`, `$TEst` fail |
| Lowercase special vars | ⚠️ Misclassified | Parsed as functions |

**Workarounds:**
- Use uppercase special variables (`$TEST`, `$HOROLOG`)
- Avoid indirect pattern match (use direct patterns)

---

## File Encoding

MUMPS source files may use different character encodings:

```python
# Conceptual Python equivalent

# Parser tries UTF-8 first, falls back to Latin-1
with open(filepath, 'r', encoding='utf-8') as f:
    source = f.read()
# Fallback for VistA files with special characters
with open(filepath, 'r', encoding='latin-1') as f:
    source = f.read()
```

**Key points:**
- VistA-M codebase contains Latin-1 encoded files (°, ö, §, ÷)
- Parser automatically falls back to Latin-1 if UTF-8 fails
- 7 of 33,951 VistA files require Latin-1 fallback

---

## Caché-Specific Functions

Some MUMPS implementations (InterSystems Caché) add extended functions:

| Function | Description | Standard Equivalent |
|----------|-------------|---------------------|
| `$LI` | List item | `$LIST` abbreviation |
| `$LISTGET` | Get list element | Standard |
| `$INCREMENT` | Atomic increment | Standard |
| `$NAMESPACE` | Current namespace | Implementation-specific |
| `$EREF` | Extended reference | Implementation-specific |

**ASG Representation:**
- All parse as `MIntrinsicFunction` nodes
- Function name preserved for code generation
- No special handling required at parse time

---

## External Routine Calls

Calls to other routines cannot be resolved at parse time:

```mumps
D ^LIBRARY         ; External routine call
D UTIL^LIBRARY     ; Label in external routine
D @A^@B            ; Doubly indirect
```

**ASG Representation:**
- `MCall.routine`: Routine name (without ^)
- `MCall.is_resolved`: False (cannot validate externally)
- `MCall.call_type`: `ROUTINE_CALL`

### External DO (Spec 008 Phases 3-4)

External DO calls transfer control to another routine and return:

```mumps
D ^ext2              ; Call entry label of ext2 routine
D HELPER^ext2        ; Call HELPER label in ext2
D LABEL+5^ext2       ; Call 5th line after LABEL
D +10^ext2           ; Call 10th line of ext2 (line dispatch)
```

**Code Generation Pattern:**
```python
# D ^ext2
import ext2
ext2.ext2(_rt, _scope)

# D HELPER^ext2
import ext2
ext2.HELPER(_rt, _scope)

# D LABEL+5^ext2 (with offset validation)
import ext2
if "LABEL" in ext2._label_lines:
    target_line = ext2._label_lines["LABEL"] + 5
    ext2._dispatch_line(target_line, _rt, _scope)

# D +10^ext2 (direct line dispatch)
import ext2
ext2._dispatch_line(10, _rt, _scope)
```

**Key Implementation Details:**
- Import statement generated for each external routine reference
- `_rt` (runtime) and `_scope` (variable dictionary) passed to all calls
- Label+offset patterns validated at runtime
- Line dispatch uses `_dispatch_line()` function in target module

### External GOTO (Spec 008 Phase 6)

External GOTO transfers control permanently without return:

```mumps
G ^dispatcher        ; Transfer to entry label
G ERROR^handler      ; Transfer to ERROR label
G +10^handler        ; Transfer to line 10
```

**Code Generation Pattern:**
```python
# G ^dispatcher
import dispatcher
from m2py.runtime import GotoExternal
raise GotoExternal(dispatcher.dispatcher, _rt, _scope)

# G ERROR^handler
import handler
from m2py.runtime import GotoExternal
raise GotoExternal(handler.ERROR, _rt, _scope)

# G +10^handler (line dispatch)
import handler
from m2py.runtime import GotoExternal
raise GotoExternal(handler._dispatch_line, _rt, _scope, 10)
```

**Key Implementation Details:**
- Raises `GotoExternal` exception caught by runtime
- Target function/line passed to exception handler
- No return to caller - control fully transferred
- Runtime unwinds stack and executes target

### External Extrinsic Functions (Spec 008 Phase 7)

External extrinsic functions call functions in other routines and return values:

```mumps
S X=$$ADD^MATH(3,5)      ; Call ADD function in MATH routine
S Y=$$MAX^UTIL(A,B,C)    ; Call MAX with multiple args
```

**Code Generation Pattern:**
```python
# Generated code for: S X=$$ADD^MATH(3,5)
import MATH
X = _call_extrinsic(MATH.ADD, 3, 5, _scope=_scope)
```

**Key Implementation Details:**
- Import statement generated inline for external routine
- `_call_extrinsic` helper saves/restores `$TEST` around call
- `_scope` parameter passed for cross-routine variable visibility
- Return value from external function becomes expression value

### Cross-Routine Variable Visibility (Spec 008 Phase 5)

Variables are visible across routine calls via `_scope` parameter:

```mumps
; In main routine
MAIN S X=42
 D SHOW^helper
 Q

; In helper routine
HELPER W X,!
 Q
```

**Code Generation Pattern:**
```python
# main.py
def MAIN(_rt, _scope):
    _scope["X"] = 42
    import helper
    helper.SHOW(_rt, _scope)

# helper.py
def SHOW(_rt, _scope):
    _rt.write(str(_scope.get("X", "")))
```

**Key Implementation Details:**
- All routines receive `_scope` dictionary parameter
- Variables stored in `_scope` instead of local scope
- `_scope` shared across all external calls
- NEW command creates temporary scope overlay (Spec 005)

---

## READ Command Variants

```mumps
R X           ; Read into X
R X:10        ; With 10 second timeout
R *X          ; Single character (ASCII code)
R X#5         ; Fixed length (max 5 chars)
R X#5:10      ; Fixed length with timeout
R !,"Prompt:",X  ; Prompts and format controls
```

**ASG Representation:**
- `MReadTarget.variable`: Target variable
- `MReadTarget.timeout`: Timeout expression
- `MReadTarget.fixed_length`: Max length expression
- `MReadTarget.is_char_read`: True for `*X` pattern

---

## $TEXT Function

Returns source code lines for the current routine (Spec 008 Phase 8):

```mumps
S X=$T(+0)          ; Routine name
S X=$T(+1)          ; First line of current routine
S X=$T(+2)          ; Second line
S X=$T(LABEL)       ; Label line
S X=$T(LABEL+N)     ; N lines after label
S X=$T(-1)          ; Negative offset (returns empty string)
S X=$T(+99)         ; Past end (returns empty string)
```

**Code Generation Strategy:**
- Embed source lines in generated code as `_source_lines` list
- Use `_rt.get_text(offset=N)` for $T(+N), $T(-N)
- Use `_rt.get_text(label="LABEL", offset=N)` for $T(LABEL+N)
- $T(+0) returns routine name
- Out-of-range and negative offsets return empty string
- Only current routine supported in this phase (no ^ROUTINE)

---

## Pattern Match Operator

MUMPS uses `?` for pattern matching against pattern codes:

```mumps
I X?1N.N S Y=1      ; True if X is 1+ digits
I X'?1A.A S Y=2     ; True if X is NOT 1+ letters
```

**Pattern Codes:**

| Code | Meaning | Python Equivalent |
|------|---------|-------------------|
| `N` | Numeric (0-9) | `[0-9]` |
| `A` | Alphabetic (A-Za-z) | `[A-Za-z]` |
| `L` | Lowercase (a-z) | `[a-z]` |
| `U` | Uppercase (A-Z) | `[A-Z]` |
| `P` | Punctuation | `[!-/:-@[-\`{-~]` |
| `C` | Control (ASCII 0-31, 127) | `[\x00-\x1f\x7f]` |
| `E` | Everything (any char) | `.` |

**Multipliers:**

| Pattern | Meaning |
|---------|---------|
| `1N` | Exactly 1 digit |
| `3A` | Exactly 3 letters |
| `.N` | Zero or more digits |
| `1.N` | One or more digits |
| `2.5A` | 2 to 5 letters |

**ASG Representation:**
- `MPatternMatch.subject`: Expression being tested
- `MPatternMatch.pattern`: Raw pattern string (e.g., `"1N.A"`)
- `MPatternMatch.operator`: Either `"?"` or `"'?"` for negated match
- `MPatternMatch.compiled_regex`: Pre-built Python regex string
- `MPatternMatch.pattern_indirect`: For indirect patterns (`?@VAR`)

**Indirect Pattern Match:** Supported via `pattern_indirect` field - pattern in variable evaluated at runtime.

---

## Numeric Literal Formats

MUMPS allows various numeric literal formats:

```mumps
S X=5           ; Integer
S X=5.5         ; Decimal
S X=.5          ; Leading decimal (no integer part)
S X=5E3         ; Scientific notation (5000)
S X=.5E-2       ; Leading decimal with exponent (0.005)
S X=00123       ; Leading zeros preserved
```

**Key points:**
- Leading decimal (`.5`) is valid - parsed as `0.5`
- Leading zeros are significant for string comparisons
- Scientific notation uses `E` or `e` with optional sign
- Trailing zeros after decimal are preserved

**Numeric String Coercion:**
MUMPS extracts leading numeric portion from strings:
```mumps
S X=+"123ABC"   ; X = 123
S X=+"ABC123"   ; X = 0 (no leading digits)
S X=+"-5.5E2X"  ; X = -550
```

---

## Chained Unary Operators

MUMPS allows multiple unary operators in sequence:

```mumps
S X=--Y         ; Double negation
S X=''Y         ; Double NOT
S X=+-Y         ; Plus then minus
S X=-'Y         ; Negation of NOT
```

**Current Limitation:** The parser supports chained unary operators, but deeply nested chains (9+ levels) may require special handling.

**ASG Representation:**
- Nested `MUnaryOp` nodes
- Each operator wraps the next level
- Innermost contains the primary expression

---

## Operator Precedence

MUMPS evaluates strictly left-to-right with no precedence:

```mumps
S X=2+3*4    ; = (2+3)*4 = 20 (NOT 2+(3*4)=14)
```

**Python Translation:**
- Cannot directly translate - need explicit parentheses
- Or restructure with intermediate variables

---

## See Also

- [runtime_requirements.md](runtime_requirements.md) - Runtime support requirements
- [for_loops.md](for_loops.md) - FOR loop translation strategies
- [goto_handling.md](goto_handling.md) - GOTO handling patterns
- [../asg/statements.md](../asg/statements.md) - Statement ASG reference
