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

// Formal parameter list: (param1, param2, ...)
FormalList:
    '(' params+=PARAM_NAME[/,/] ')'
;

// Continuation line: starts with whitespace or dot
ContLine:
    /[\t ]/ rest=/[^\r\n]*/ NL
;
```

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
| `]]` | Sorts after | |
| `&` | AND | Logical |
| `!` | OR | Logical |
| `'&` `'!` | NAND, NOR | |
| `_` | Concatenate | String |
| `?` | Pattern match | See below |
| `'?` | Not pattern match | |

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

// Naked global: ^(subscripts) - uses last referenced global name
NakedGlobal:
    '^' '(' subscripts+=Expr[','] ')'
;

// Subscripts: (expr, expr, ...)
Subscripts:
    '(' subscripts+=Expr[','] ')'
;
```

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
    name=LABEL_NAME ('+' offset=Expr)? ('^' routine=ROUTINE_NAME)?
;
```

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
