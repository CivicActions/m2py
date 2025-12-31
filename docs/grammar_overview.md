# textX Grammar Overview

This document describes how M2PY uses textX grammars to parse MUMPS source code.

## Grammar File Organization

The grammar is split across four files for maintainability:

| File | Purpose | Size |
|------|---------|------|
| `mumps.tx` | Routine structure (labels, lines) | ~60 lines |
| `line.tx` | Line content parsing | ~40 lines |
| `commands.tx` | Individual command syntax | ~400 lines |
| `expressions.tx` | Expression parsing | ~350 lines |

All grammar files are located in: [`src/m2py/grammar/`](../src/m2py/grammar/)

## Grammar Overview

### Routine Structure (mumps.tx)

The top-level grammar defines MUMPS routine structure:

```textx
// Root element - a complete MUMPS routine
Routine:
    lines*=Line
;

// A line can be a label line, continuation, comment, or empty
Line:
    LabelLine | ContLine | CommentLine | EmptyLine
;

// Label line: label at column 1, optional formal params, then rest
LabelLine:
    label=LABEL_NAME formal_list=FormalList? rest=/[^\r\n]*/ NL
;

// Formal parameter list: (param1, param2, ...) or empty ()
FormalList:
    '(' params*=PARAM_NAME[/,/] ')'
;

// Continuation line: starts with tab or single space, then rest
// Note: Dot level indicators appear in 'rest', not as linestart character
ContLine:
    /[\t ]/ rest=/[^\r\n]*/ NL
;
```

### Line Level (Dot Blocks)

MUMPS uses dot prefixes to indicate block nesting level (per MUMPS 1995 spec §6.2):

```mumps
TEST
 D           ; Argumentless DO starts a block
 . S X=1     ; Level 1: space + dot + space + command
 . D         ; Nested argumentless DO  
 . . S Y=2   ; Level 2: space + two dots + space + command
 . W X       ; Back to level 1
 Q           ; Level 0: block ended
```

The linestart character (tab or space) is matched by the grammar's `ContLine` rule. 
The dot(s) and subsequent content are captured in the `rest` attribute, then parsed 
separately by the line content parser. The parser tracks `_dot_level` internally to 
structure DO blocks correctly.

### Label Names

MUMPS labels can be:
- **Alphabetic**: Start with letter or `%`, followed by alphanumerics
- **Numeric**: Purely numeric (e.g., `123`)

```textx
LABEL_NAME:
    /[A-Za-z%][A-Za-z0-9]*|[0-9]+/
;
```

### Expression Grammar (expressions.tx)

MUMPS uses **strict left-to-right evaluation** with no operator precedence. The expression grammar reflects this:

```textx
// Left-to-right: left operand, then zero or more (op, right) tails
Expr:
    left=UnaryExpr (tail+=ExprTail)*
;

// Each tail is either a binary operation or pattern match
ExprTail:
    PatternMatchTail | BinaryOpTail
;

// Pattern match has special syntax
PatternMatchTail:
    op=PatternMatchOp ('@' indirect_expr=UnaryExpr | pattern=PatternSpec)
;

// Regular binary operation
BinaryOpTail:
    op=BinaryOp right=UnaryExpr
;

// Unary operators can be chained: --X, ''X, +-X
UnaryExpr:
    operators*=UnaryOp operand=PrimaryExpr
;
```

### Binary Operators

MUMPS has many operators, some multi-character:

```textx
BinaryOp:
    // Multi-character operators first (order matters in PEG)
    op=/\*\*|>=|<=|'>|'<|'=|'\[|'\]|'&|'!|]]|\[|\]/
    | op=/[+\-*\/#\\=<>&!_\]]/ 
;
```

| Operator | Meaning | Notes |
|----------|---------|-------|
| `+` `-` `*` `/` | Arithmetic | Standard |
| `\` | Integer division | Different from `/` |
| `#` | Modulo | |
| `**` | Exponentiation | |
| `=` | Equals | Compare, not assign |
| `<` `>` | Less/greater than | |
| `'=` `'<` `'>` | Negated comparisons | NOT equals, etc. |
| `[` | Contains | String contains |
| `]` | Follows | String collation |
| `]]` | Sorts after | MUMPS 1995 ANSI standard¹ |
| `&` | AND | Logical |
| `!` | OR | Logical |
| `'&` `'!` | NAND, NOR | |
| `_` | Concatenate | String |
| `?` | Pattern match | See below |
| `'?` | Not pattern match | |

> ¹ The `]]` "sorts after" operator was added in the MUMPS 1995 ANSI standard.
> It is distinct from `]` (follows) and returns true if the left operand sorts
> after the right operand in subscript collation order. See
> [mumps-reference/1995__a902027.md](../mumps-reference/1995__a902027.md) for the specification.

### Pattern Match Syntax

Pattern matching uses a special syntax:

```textx
PatternSpec:
    atoms+=PatternAtom
;

PatternAtom:
    count=PatternCount? (
        codes=PatternCodes | 
        literal=StringLiteral |
        '(' alternates+=PatternSpec[','] ')'
    )
;

PatternCount:
    /\d+\.?\d*|\.+\d*/
;

PatternCodes:
    /[ACELNPU]+/
;
```

**Pattern codes**:
- `A` - Alphabetic
- `C` - Control characters
- `E` - Any character (Everything)
- `L` - Lowercase
- `N` - Numeric
- `P` - Punctuation
- `U` - Uppercase

**Examples**:
- `X?1N.A` - Starts with one digit, followed by zero or more letters
- `X?.N` - Zero or more digits
- `X?1"Mr. ".E` - Starts with "Mr. ", followed by anything

### Variables and Globals

```textx
// Local variable: name with optional subscripts
LocalVariable:
    name=VARNAME subscripts=Subscripts?
;

// Global variable: ^name with optional subscripts
GlobalVariable:
    '^' name=VARNAME subscripts=Subscripts?
;

// Extended global references (environment/namespace specification)
// ^|"env"|name - pipe-delimited environment
ExtendedGlobalPipe:
    '^|' environment=StringLiteral '|' name=VARNAME subscripts=Subscripts?
;

// ^["gld"]name - bracket-delimited global directory
ExtendedGlobalBracket:
    '^[' environment=StringLiteral ']' name=VARNAME subscripts=Subscripts?
;

// Naked global: ^(subscripts) - uses last referenced global name
NakedGlobal:
    '^' '(' subscripts+=Expr[','] ')'
;

// Subscripts: (expr, expr, ...)
Subscripts:
    '(' subscripts+=Expr[','] ')'
;
```

### Intrinsic Special Variables (ISVs)

MUMPS provides built-in special variables accessed with `$NAME` syntax:

```textx
SpecialVariable:
    '$' name=SVARNAME
;

// ISV names ordered for longest-match-first (critical for PEG parsing)
SVARNAME:
    /[Pp][Ii][Oo][Rr][Ee][Ff][Ee][Rr][Ee][Nn][Cc][Ee]|...|[Xx]|[Yy]/
;
```

**Longest-Match-First Rule**: The `SVARNAME` regex lists patterns from longest to shortest:
- `PIOREFERENCE` before `IO` (prevents partial match)
- `IOREFERENCE` before `IO`
- `PRINCIPAL` before `P`

**Common ISVs**:
| ISV | Description | Assignable |
|-----|-------------|------------|
| `$HOROLOG` | Current date/time | No |
| `$IO` | Current I/O device | No |
| `$JOB` | Process ID | No |
| `$PRINCIPAL` | Principal I/O device | No |
| `$TEST` | IF condition result | No |
| `$X` | Cursor column position | Yes |
| `$Y` | Cursor row position | Yes |

**Assignable ISVs**: Some ISVs like `$X` and `$Y` can appear on the left side of SET:
```mumps
S $X=0,$Y=0  ; Reset cursor position
```

### Z-ISVs (YottaDB/GT.M Extensions)

YottaDB and GT.M implementations provide additional intrinsic special variables with `$Z` prefix. These are called Z-ISVs and many of them are settable (can appear on the left side of SET and in NEW statements).

**Settable Z-ISVs** (parsed as `SpecialVariable`):
| Z-ISV | Description | Use in SET/NEW |
|-------|-------------|----------------|
| `$ZTRAP` | Error trap handler | `S $ZTRAP="ERRSUB"` |
| `$ZSTATUS` | Error status/message | `S $ZSTATUS=""` |
| `$ZGBLDIR` | Global directory path | `S $ZGBLDIR="db.gld"` |
| `$ZINTERRUPT` | Interrupt handler | `S $ZINTERRUPT="INTSUB"` |
| `$ZYERROR` | Extended error info | `S $ZYERROR="ERRSUB^ROU"` |
| `$ZSTEP` | Step action handler | `S $ZSTEP="N"` |
| `$ZLEVEL` | Stack level | Read mostly |
| `$ZPOSITION` | Current position | Read mostly |
| `$ZEOF` | End of file flag | Device-dependent |
| `$ZJOB` | Job information | Read mostly |
| `$ZCMDLINE` | Command line args | Read mostly |
| `$ZKEY` | Key value | Device-dependent |

**Trigger Z-ISVs** (for trigger context):
| Z-ISV | Description |
|-------|-------------|
| `$ZTWORMHOLE` | Data passed through transaction |
| `$ZTRIGGEROP` | Trigger operation type (SET/KILL/etc.) |
| `$ZTOLDVALUE` | Value before trigger |
| `$ZTVALUE` | Current/new value |
| `$ZTUPDATE` | Piece numbers updated |
| `$ZTSLATE` | Transaction slate data |
| `$ZTDELIM` | Trigger delimiter |
| `$ZTLEVEL` | Transaction level |
| `$ZTNAME` | Trigger name |
| `$ZTCODE` | Trigger code |
| `$ZTDATA` | Trigger data info |

**Read-only Z-ISVs** (parsed as `IntrinsicFunctionNoArgs`):
| Z-ISV | Description |
|-------|-------------|
| `$ZCHSET` | Character set (M or UTF-8) |
| `$ZSYSTEM` | Last OS command return code |
| `$ZVERSION` | YDB/GT.M version |

**Example usage**:
```mumps
; Error trapping
S $ZTRAP="ERRHND"  
; ... code that might fail ...
Q
ERRHND
W "Error: ",$ZSTATUS,!
S $ZTRAP=""
Q

; Transaction wormhole (triggers)
S $ZTWORMHOLE="audit-user-123"
TSTART
S ^DATA("key")="value"
TCOMMIT
```

**Grammar Note**: Settable Z-ISVs are included in the `SVARNAME` pattern, ensuring they parse as `SpecialVariable` and can be used with SET and NEW commands. The pattern uses longest-match-first ordering (e.g., `ZTWORMHOLE` before `ZT`) to prevent partial matching.

### Structured System Variables (SSVs)

SSVs provide subscripted access to system information via `^$NAME` syntax:

```textx
StructuredSystemVariable:
    '^$' name=SSVNAME subscripts=Subscripts?
;

// SSV names
SSVNAME:
    /[Jj][Oo][Bb]|[Ll][Oo][Cc][Kk]|[Rr][Oo][Uu][Tt][Ii][Nn][Ee]|.../
;
```

**Common SSVs**:
| SSV | Description | Example |
|-----|-------------|---------|
| `^$JOB` | Process information | `^$JOB($JOB,"NAME")` |
| `^$LOCK` | Lock table | `^$LOCK(name)` |
| `^$ROUTINE` | Routine information | `^$ROUTINE("TEST")` |
| `^$GLOBAL` | Global directory | `^$GLOBAL("^DATA")` |
| `^$DEVICE` | Device information | `^$DEVICE(device)` |
| `^$SYSTEM` | System information | `^$SYSTEM("VERSION")` |

### Intrinsic Functions

```textx
IntrinsicFunction:
    '$' name=FUNC_NAME args=FunctionArgs?
;

FunctionArgs:
    '(' args+=FunctionArg[','] ')'
;

// Function argument: by-reference, by-value, or omitted
FunctionArg:
    byref=ByRefArg | expr=Expr?
;

// By-reference: .VAR syntax
ByRefArg:
    '.' var=LocalVariable
;
```

**Common functions**: `$EXTRACT`, `$PIECE`, `$LENGTH`, `$ORDER`, `$DATA`, `$GET`, etc.

**By-Reference**: The `.VAR` syntax indicates call-by-reference (per MUMPS spec 8.1.7):
- `D SUB(A,B)` → both by-value
- `D SUB(.A,B)` → A by-reference, B by-value  
- `$$CALC(.X,.Y)` → both by-reference (extrinsic functions support this too)

### Extrinsic Functions

User-defined functions are called with `$$`:

```textx
ExtrinsicFunction:
    '$$' target=CallTarget args=ActualList?
;

CallTarget:
    name=LABEL_NAME ('+' offset=OffsetExpr)? ('^' routine=ROUTINE_NAME)?
;
```

### Computed Entry Points in DO/GOTO

MUMPS allows computed offsets in DO and GOTO targets. The offset expression can include
global variable values, intrinsic functions, and arithmetic operations:

```mumps
; Simple computed offset
D 1+^COUNT^ROUTINE    ; Label 1, offset = value of ^COUNT, routine = ROUTINE

; Complex offset expression with globals
D LABEL+^V1A(2)-^(3)/10    ; Offset = ^V1A(2) - ^(3) / 10

; Multiple bare globals in offset
D Z+-20+^VAR1+^VAR2^ROUTINE
```

The grammar uses `OffsetExpr` instead of `Expr` to properly distinguish offset expressions
from routine references. `OffsetExpr` supports:
- Bare globals (`^NAME`) - parsed as global values, not routine refs
- Subscripted globals (`^NAME(subscripts)`)
- Naked globals (`^(subscripts)`)
- Local variables, intrinsic functions, and literals

The key insight is that after the offset expression is parsed, any subsequent `^NAME`
is interpreted as the routine reference.

### Argument Postconditions (DO, GOTO, XECUTE)

Per MUMPS spec 8.1.4, three commands support argument-level postconditions:
DO, GOTO, and XECUTE. This allows conditional execution of individual arguments.

```mumps
; DO with argument postconditions
D INIT,PROC:DEBUG,CLEANUP    ; PROC runs only if DEBUG is true

; GOTO with argument postconditions  
G DONE:X>100,RETRY:ERR,LOOP  ; First matching condition wins

; XECUTE with argument postconditions
X "S X=1":A>0,"S Y=1":B>0    ; Each arg can have its own condition
X:ENABLE "CODE1":COND1,"CODE2":COND2  ; Command AND arg postconditions
```

The grammar structure for XECUTE arguments:
```textx
XecuteCommand:
    /([Xx][Ee][Cc][Uu][Tt][Ee]|[Xx])(?![A-Za-z])/ postcond=Postcondition? WS args+=XecuteArg[/,/]
;

XecuteArg:
    expr=Expr postcond=Postcondition?
;
```

Note: Only DO, GOTO, and XECUTE support argument postconditions. Other commands
like SET, WRITE, and READ do NOT have this capability per the MUMPS specification.

### Indirection

The `@` operator provides dynamic name resolution:

```textx
Indirection:
    '@'+ expr=PrimaryExpr subscripts=Subscripts?
;
```

Types of indirection:
- **Name indirection**: `@X` where X contains a variable name
- **Subscript indirection**: `Y(@X)` where X provides subscripts
- **Argument indirection**: `D @CMD` where CMD contains a call target

## Whitespace Handling

MUMPS is whitespace-sensitive. The grammar uses `skipws=False`:

```python
# In parser.py
metamodel = metamodel_from_file(
    grammar_path,
    skipws=False,  # Don't skip whitespace
    classes=custom_classes,
)
```

This means:
- Whitespace must be explicitly matched in grammar rules
- Line structure (tabs, dots) is preserved
- Command arguments are space-separated

## Custom Classes

textX custom classes map grammar rules to ASG types:

```python
# In textx_classes.py
class NumericLiteral(MLiteral):
    def __init__(self, parent, value):
        v = value
        if "." in value:
            lit_type = LiteralType.DECIMAL
        else:
            lit_type = LiteralType.INTEGER
        super().__init__(value=v, literal_type=lit_type)

class LocalVariable(MVariable):
    def __init__(self, parent, name, subscripts=None):
        super().__init__(name=name, subscripts=subscripts or [])
```

This allows the parser to directly construct ASG nodes during parsing.

## Command Abbreviations

MUMPS commands can be abbreviated (per MUMPS spec). Most commands have a single minimum abbreviation, but **HALT and HANG share the `H` abbreviation**:

| Full | Minimum | Example |
|------|---------|---------|
| SET | S | `S X=1` |
| WRITE | W | `W "hello"` |
| QUIT | Q | `Q` |
| GOTO | G | `G LABEL` |
| DO | D | `D SUB` |
| IF | I | `I X>0` |
| FOR | F | `F I=1:1:10` |
| **HALT** | **H** | `H` (no argument) |
| **HANG** | **H** | `H 5` (with argument) |
| TSTART | TS | `TS ():serial` (begin transaction) |
| TCOMMIT | TC | `TC` (commit transaction) |
| TRESTART | TRE | `TRE` (restart transaction) |
| TROLLBACK | TRO | `TRO` (rollback transaction) |

### Transaction Commands (TSTART)

The TSTART command begins a transaction with optional restart variables and parameters:

```textx
TStartCommand:
    /([Tt][Ss][Tt][Aa][Rr][Tt]|[Tt][Ss])(?![A-Za-z])/ postcond=Postcondition? 
    (WS restart_arg=TStartRestartArg? (':' params+=TStartParam[':'])?)?
;

TStartRestartArg:
    all='*' | '(' vars*=VARNAME[','] ')'
;

TStartParam:
    name=/[Ss][Ee][Rr][Ii][Aa][Ll]|[Ss]|[Tt][Rr][Aa][Nn][Ss][Aa][Cc][Tt][Ii][Oo][Nn][Ii][Dd]|[Tt]|[Zz][A-Za-z0-9]*/ 
    ('=' value=Expr)?
;
```

**Examples**:
| Syntax | Description |
|--------|-------------|
| `TS` | Non-restartable transaction |
| `TS ()` | Restartable transaction (empty restart list) |
| `TS *` | Restartable, restore all local variables on restart |
| `TS (A,B)` | Restartable, restore A and B on restart |
| `TS ():serial` | Restartable serial transaction |
| `TS ():S` | Restartable serial (abbreviated) |
| `TS ():T="BA"` | Transaction with ID "BA" |
| `TS ():serial:T="X"` | Serial transaction with ID "X" |

**Parameters**:
- `SERIAL` (S): Transaction is serializable
- `TRANSACTIONID` (T): Named transaction identifier (value required)
- Z-prefixed: Implementation-specific parameters

### VIEW Command

The VIEW command provides implementation-specific system control:

```textx
ViewCommand:
    /([Vv][Ii][Ee][Ww]|[Vv])(?![A-Za-z])/ postcond=Postcondition? WS? args+=ViewArg[/,/]?
;

ViewArg:
    expr=Expr values+=ViewColonValue*
;

ViewColonValue:
    ':' value=Expr
;
```

**GT.M/YottaDB Syntax**: Each VIEW argument supports colon-separated values:

| Example | Description |
|---------|-------------|
| `VIEW "trace":1:"^trace"` | Enable tracing with global storage |
| `VIEW "GVDUPSETNOOP":0` | Set duplicate SET behavior |
| `VIEW "JOBPID":1` | Enable job PID tracking |
| `V 0` | Simple VIEW with expression |

The `ViewArg` rule captures the main expression and any colon-separated values that follow.

### Z-Commands (YottaDB/GT.M Extensions)

M2PY supports vendor-specific Z-commands commonly used in YottaDB and GT.M implementations:

| Full | Minimum | Purpose | Example |
|------|---------|---------|---------|
| ZALLOCATE | ZA | Incremental lock (always +) | `ZALLOCATE ^gbl:60` |
| ZBREAK | ZB | Set/remove breakpoints | `ZBREAK label^routine:"action"` |
| ZCOMPILE | ZC | Compile routine | `ZCOMPILE "routine.m"` |
| ZCONTINUE | (none) | Continue from breakpoint | `ZCONTINUE` |
| ZDEALLOCATE | ZD | Decremental unlock (always -) | `ZDEALLOCATE ^gbl` |
| ZGOTO | ZGO | Extended GOTO with stack unwinding | `ZGOTO 0:label` |
| ZHALT | ZH | Halt with exit code | `ZHALT 1` |
| ZKILL | ZKI | Kill variable, keep descendants | `ZKILL X(1)` |
| ZLINK | ZLI | Compile and link routine | `ZLINK "routine"` |
| ZMESSAGE | ZM | Generate MUMPS error | `ZMESSAGE 150372994` |
| ZPRINT | ZP | Print source code | `ZPRINT label^routine` |
| ZSHOW | ZSH | Display process info | `ZSHOW "BS":^RESULT` (to global) |
| ZSYSTEM | ZSY | Execute shell command | `ZSYSTEM "ls -la"` |
| ZTRIGGER | (none) | Trigger update notification | `ZTRIGGER ^global` |
| ZWITHDRAW | ZWI | Kill variable, keep descendants | `ZWITHDRAW X(1)` (alias for ZKILL) |
| ZWRITE | ZWR | Write variables with names | `ZWR X` |

**Note**: ZCONTINUE requires full spelling to avoid conflict with ZC (ZCOMPILE abbreviation).

### ZSHOW Output Destinations

ZSHOW supports optional output destinations to capture information into variables:

```mumps
ZSHOW "*"             ; Display all info to terminal
ZSHOW "V":^RESULT     ; Output variables to ^RESULT global
ZSHOW "L":@gvar       ; Output locks via indirection
ZSHOW "*":^XUTL("SYS",$J)  ; Output to subscripted global
```

The grammar rule is:
```textx
ZShowArg:
    codes=Expr (':' destination=VarRef)?
;
```

**ZSHOW codes** (string argument):
- `"*"` - All information
- `"B"` - Breakpoints
- `"D"` - Devices
- `"G"` - Globals
- `"I"` - Intrinsic special variables
- `"L"` - Locks
- `"S"` - Stack
- `"V"` - Variables

### HALT vs HANG Disambiguation

The grammar uses **ordered alternatives** and **negative lookahead** to distinguish:

```textx
// In Command alternatives, HaltCommand comes BEFORE HangCommand
Command:
    ... |
    HaltCommand |    // Try this first
    HangCommand |    // Only if HaltCommand doesn't match
    ...
;

// HaltCommand: matches H|HALT without following whitespace (before AND after postcondition)
HaltCommand:
    /[Hh][Aa][Ll][Tt]|[Hh]/ !WS postcond=Postcondition? !WS
;

// HangCommand: requires H|HANG followed by whitespace and expression(s)
// Supports multiple comma-separated durations: H 0,1,2,3
HangCommand:
    /[Hh][Aa][Nn][Gg]|[Hh]/ postcond=Postcondition? SingleSpace args+=Expr[/,/]
;
```

The double `!WS` negative lookahead ensures:
- `H` alone → HALT (no whitespace follows)
- `H:X` → HALT with postcondition (no whitespace after postcond)
- `H 5` → HANG (`!WS` fails because space follows, so HaltCommand doesn't match)
- `H:X>0 5` → HANG with postcondition (`!WS` after postcond fails due to space)
- `H 0,1,2,3` → HANG with multiple durations

## Grammar Testing

Test grammar rules with:

```bash
# Parse a file and inspect the result
uv run python utils/validate_asg.py tests/functional/mugj/inref/V1FORA.m

# Test expression parsing
uv run python -c "
from m2py import MUMPSParser
parser = MUMPSParser()
routine = parser.parse('TEST  S X=1+2*3,!\\n Q\\n')
print(routine.labels[0].body.statements)
"
```

## References

- **textX Grammar Syntax**: [https://textx.github.io/textX/grammar/](https://textx.github.io/textX/grammar/)
- **textX Custom Classes**: [https://textx.github.io/textX/metamodel/](https://textx.github.io/textX/metamodel/)
- **Grammar Files**: [`src/m2py/grammar/`](../src/m2py/grammar/)
- **Custom Classes**: [`src/m2py/parser/textx_classes.py`](../src/m2py/parser/textx_classes.py)
