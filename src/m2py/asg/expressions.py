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
from m2py.asg.enums import LiteralType, FormatControlType, IndirectionType, PassingMode

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
    that requires runtime tracking of the "naked indicator" (the last
    referenced global name and subscripts).

    Code generation must track the naked indicator at runtime since
    the global name comes from the previous global reference.
    """

    subscripts: List["MExpr"] = field(default_factory=list)


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

    Per MUMPS spec 8.1.7, extrinsic function arguments support both
    by-value and by-reference passing modes (same as DO command):
    $$CALC(.X,Y) - X is by-reference, Y is by-value
    """

    target: Optional["MCall"] = None
    arguments: List["MActualParameter"] = field(default_factory=list)


# =============================================================================
# Special Expressions
# =============================================================================


@dataclass
class MPatternMatch(MExpr):
    """Pattern match expression.

    Represents pattern matching using the ? operator:
    X?1A.N, X?@pattern (indirect pattern)
    Also supports negated pattern match: X'?1A.N

    The pattern field stores a flattened string representation (e.g., "1A.N")
    rather than the structured PatternSpec from the grammar. The compiled_regex
    field contains the equivalent Python regex for code generation. This design
    keeps the ASG simple since downstream code only needs the regex, not the
    individual pattern atoms. See pattern_compiler.py for the string-to-regex
    conversion.
    """

    subject: Optional["MExpr"] = None
    # Raw pattern string - intentionally flattened from structured PatternSpec
    # See docstring above for design rationale
    pattern: str = ""
    pattern_indirect: Optional["MExpr"] = None  # For indirect patterns ?@X
    operator: str = "?"  # Either "?" or "'?" for negated match

    # Pre-built regex pattern string for code generation (not a compiled re.Pattern)
    # None if indirect pattern (must be compiled at runtime)
    compiled_regex: Optional[str] = None


@dataclass
class MIndirection(MExpr):
    """Indirection expression.

    Represents indirect references using @:
    - Name indirection: @X (where X contains a variable name)
    - Subscript indirection: Y(@X) (X provides subscript)
    - Argument indirection: DO @X (X contains label/routine)
    - Pattern indirection: Y?@X (X contains pattern)
    - Variable name indirection: @X@(1,2) (X evaluates to variable name, append subscripts)
    """

    expression: Optional["MExpr"] = None
    indirection_type: IndirectionType = IndirectionType.UNKNOWN

    # Direct subscripts for @X(1,2) form
    subscripts: Optional[List["MExpr"]] = None

    # Name indirection subscripts for @X@(1,2) form
    # Each entry is a list of subscript expressions for one @(...) group
    name_indirection_subscripts: Optional[List[List["MExpr"]]] = None

    # Analysis flags for static resolution
    can_resolve_statically: bool = False
    resolved_value: Optional[str] = None

    # Runtime evaluation flags (set by textX custom class)
    requires_runtime_eval: bool = True  # Indirection always requires runtime
    result_type: Optional[str] = None  # Type is unknown until runtime


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

    control_type: Optional["FormatControlType"] = None  # Type of format control
    expression: Optional["MExpr"] = None  # Column/charcode expr for ?n/*n


@dataclass
class MSpecialVariable(MExpr):
    """Special variable reference.

    Represents intrinsic special variables (ISVs):
    $TEST, $HOROLOG, $IO, $JOB, $PIECE, etc.
    """

    name: str = ""  # Variable name without $


# =============================================================================
# Parameter Passing Support
# =============================================================================


@dataclass
class MActualParameter(ASGElement):
    """Represents an actual parameter in a call (DO, extrinsic function).

    Tracks the passing mode per MUMPS spec (MDC 8.1.7):
    - BY_VALUE: Expression evaluated and passed (D SUB(X+1))
    - BY_REFERENCE: Variable reference with . prefix (D SUB(.X))
    - OMITTED: Empty parameter position (D SUB(,Y))

    For BY_REFERENCE, the variable_name field contains the actual variable
    name that will be aliased to the formal parameter.

    Example:
        D CALC(A+1, .X, , Y)
        -> [BY_VALUE(A+1), BY_REFERENCE(X), OMITTED, BY_VALUE(Y)]
    """

    passing_mode: PassingMode = PassingMode.BY_VALUE
    expression: Optional[MExpr] = (
        None  # The expression (for BY_VALUE) or variable (for BY_REFERENCE)
    )
    variable_name: Optional[str] = None  # For BY_REFERENCE: the actual variable name

    @property
    def is_byref(self) -> bool:
        """Check if this parameter is passed by reference."""
        return self.passing_mode == PassingMode.BY_REFERENCE

    @property
    def is_omitted(self) -> bool:
        """Check if this parameter position is omitted."""
        return self.passing_mode == PassingMode.OMITTED
