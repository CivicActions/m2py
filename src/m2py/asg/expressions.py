"""ASG Expression elements.

Defines all expression types for the MUMPS ASG:
- MExpr: Base expression class
- MLiteral: Literal values (string, integer, decimal)
- MVariable: Local variable references
- MGlobal: Global variable references (^NAME)
- MNakedGlobal: Naked global references (^(subscripts))
- MBinaryOp: Binary operations
- MUnaryOp: Unary operations
- MIntrinsicFunction: Built-in functions ($LENGTH, etc.)
- MExtrinsicFunction: User-defined functions ($$FUNC^ROUTINE)
- MPatternMatch: Pattern matching (X?pattern)
- MIndirection: Indirect references (@variable)
- MSpecialVariable: Special variables ($TEST, $HOROLOG, etc.)
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional

from m2py.asg.elements import ASGElement
from m2py.asg.enums import LiteralType, FormatControlType

if TYPE_CHECKING:
    from m2py.asg.elements import MCall


@dataclass
class MExpr(ASGElement):
    """Base class for all expressions.
    
    Expressions are the fundamental building blocks that produce values
    in MUMPS. They can be literals, variable references, operations,
    function calls, or special forms like pattern matching.
    """
    
    # Type annotation (may be computed during analysis)
    result_type: Optional[str] = None  # "string", "number", "unknown"


# =============================================================================
# Literals
# =============================================================================

@dataclass
class MLiteral(MExpr):
    """Literal value expression.
    
    Represents a constant value in the source code:
    - String literals: "hello"
    - Integer literals: 42
    - Decimal literals: 3.14
    """
    
    value: Any = None
    literal_type: LiteralType = LiteralType.STRING
    raw_value: Optional[str] = None  # Original text representation


# =============================================================================
# Variable References
# =============================================================================

@dataclass
class MVariable(MExpr):
    """Local variable reference.
    
    Represents a reference to a local variable, optionally with subscripts
    for array access: X, NAME, DATA(1,2,3)
    """
    
    name: str = ""
    subscripts: List["MExpr"] = field(default_factory=list)


@dataclass
class MGlobal(MExpr):
    """Global variable reference.
    
    Represents a reference to a global (persistent) variable:
    ^GLOBAL, ^DATA(1,2,3)
    """
    
    name: str = ""
    subscripts: List["MExpr"] = field(default_factory=list)


@dataclass
class MNakedGlobal(MExpr):
    """Naked global reference.
    
    Represents a reference using the naked indicator ^(subscripts),
    which uses the last global context. This is a MUMPS optimization
    that requires runtime tracking.
    """
    
    subscripts: List["MExpr"] = field(default_factory=list)
    requires_runtime_tracking: bool = True


# =============================================================================
# Operations
# =============================================================================

@dataclass
class MBinaryOp(MExpr):
    """Binary operation expression.
    
    Represents operations with two operands:
    - Arithmetic: +, -, *, /, \\ (integer divide), # (modulo), ** (power)
    - Comparison: =, <, >, ], ]] (sorts after), [ (contains)
    - Logical: &, !
    - String: _ (concatenation)
    - Pattern: ? (pattern match)
    """
    
    operator: str = ""
    left: Optional["MExpr"] = None
    right: Optional["MExpr"] = None


@dataclass
class MUnaryOp(MExpr):
    """Unary operation expression.
    
    Represents operations with a single operand:
    - Numeric: + (positive), - (negative)
    - Logical: ' (NOT)
    """
    
    operator: str = ""
    operand: Optional["MExpr"] = None


# =============================================================================
# Functions
# =============================================================================

@dataclass
class MIntrinsicFunction(MExpr):
    """Intrinsic (built-in) function call.
    
    Represents calls to MUMPS built-in functions:
    $LENGTH(str), $PIECE(str,delim,pos), $ORDER(arr), etc.
    """
    
    name: str = ""  # Function name without $
    arguments: List["MExpr"] = field(default_factory=list)


@dataclass
class MExtrinsicFunction(MExpr):
    """Extrinsic (user-defined) function call.
    
    Represents calls to user-defined functions:
    $$FUNC, $$FUNC^ROUTINE, $$FUNC(args)
    """
    
    target: Optional["MCall"] = None
    arguments: List["MExpr"] = field(default_factory=list)


# =============================================================================
# Special Expressions
# =============================================================================

@dataclass
class MPatternMatch(MExpr):
    """Pattern match expression.
    
    Represents pattern matching using the ? operator:
    X?1A.N, X?@pattern (indirect pattern)
    """
    
    subject: Optional["MExpr"] = None
    pattern: str = ""  # Raw pattern string for direct patterns
    pattern_indirect: Optional["MExpr"] = None  # For indirect patterns ?@X


@dataclass
class MIndirection(MExpr):
    """Indirection expression.
    
    Represents indirect references using @:
    - Name indirection: @X (where X contains a variable name)
    - Subscript indirection: Y(@X) (X provides subscript)
    - Argument indirection: DO @X (X contains label/routine)
    """
    
    expression: Optional["MExpr"] = None
    indirection_type: str = ""  # "name", "subscript", "argument"
    
    # Analysis flags
    can_resolve_statically: bool = False
    resolved_value: Optional[str] = None


@dataclass
class MFormatControl(MExpr):
    """Format control expression for WRITE/READ commands.
    
    Represents I/O format controls:
    - ! (newline) - Output line feed
    - # (formfeed) - Output form feed/page break  
    - ?n (tab) - Tab to column n
    - *n (charcode) - Output character with ASCII code n
    
    For tab (?n) and charcode (*n), the expression field contains
    the column number or character code respectively.
    """
    
    control_type: "FormatControlType" = None  # Type of format control
    expression: Optional["MExpr"] = None  # Column/charcode expr for ?n/*n


@dataclass
class MSpecialVariable(MExpr):
    """Special variable reference.
    
    Represents intrinsic special variables (ISVs):
    $TEST, $HOROLOG, $IO, $JOB, $PIECE, etc.
    """
    
    name: str = ""  # Variable name without $
