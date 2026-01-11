"""ASG Enumerations for type classification.

Defines enums used to classify ASG elements:
- ForLoopType: Classification of FOR loop control flow
- ForParamType: Type of individual FOR parameter
- GotoType: Classification of GOTO target and behavior
- CallType: Type of subroutine call
- LiteralType: Type of literal value
"""

from enum import Enum, auto


class ForLoopType(Enum):
    """Classification of FOR loop control flow patterns.

    Used to determine how a FOR loop can be transpiled to Python:
    - BOUNDED: Standard for loop with known bounds (F I=1:1:10)
    - OPEN_ENDED: Potentially infinite loop (F I=1:1)
    - STRING_LIST: Iteration over explicit values (F I="A","B","C")
    - MIXED: Combination of patterns (F I="A",1:1:3)
    - ARGUMENTLESS: Infinite loop until QUIT (F)
    """

    BOUNDED = auto()
    OPEN_ENDED = auto()
    STRING_LIST = auto()
    MIXED = auto()
    ARGUMENTLESS = auto()


class ForParamType(Enum):
    """Type of individual FOR parameter within a FOR command.

    A FOR command can have multiple parameters, each of which can be:
    - VALUE: Single expression (F I=7)
    - RANGE: Bounded range with start:step:end (F I=1:1:10)
    - OPEN_RANGE: Unbounded range with start:step (F I=1:1)
    """

    VALUE = auto()
    RANGE = auto()
    OPEN_RANGE = auto()


class GotoType(Enum):
    """Classification of GOTO statement behavior.

    Used to determine the control flow impact of a GOTO:
    - FORWARD_JUMP: Jump ahead (same or different label, check is_cross_label)
    - BACKWARD_JUMP: Jump back (same or different label, check is_cross_label)
    - LOOP_EXIT: Exits a single FOR loop
    - MULTI_LOOP_EXIT: Exits multiple nested FOR loops
    - EXTERNAL: Jumps to external routine (^routine)
    - UNRESOLVED: Target cannot be statically determined

    Note: The is_cross_label field on MGotoStatement indicates whether the
    jump crosses label boundaries. This is orthogonal to direction.
    """

    FORWARD_JUMP = auto()
    BACKWARD_JUMP = auto()
    LOOP_EXIT = auto()
    MULTI_LOOP_EXIT = auto()
    EXTERNAL = auto()
    UNRESOLVED = auto()


class GotoCodegenPattern(Enum):
    """Pre-computed code generation pattern for GOTO statements.

    Determined during classify_gotos() analysis, used by codegen to select
    the Python pattern to generate:
    - BREAK: Single loop exit - generates 'break'
    - MULTI_BREAK: Multi-loop exit - generates 'raise _LoopExit()'
    - FORWARD: Intra-label forward jump - restructure to if/else
    - FUNCTION_CALL: Cross-label jump - generates 'label(); return'
    - UNSUPPORTED: Cannot be transpiled statically
    """

    BREAK = auto()
    MULTI_BREAK = auto()
    FORWARD = auto()
    FUNCTION_CALL = auto()
    UNSUPPORTED = auto()


class CallType(Enum):
    """Type of subroutine call or reference.

    Classifies how a DO, GOTO, or extrinsic call is structured:
    - LABEL_CALL: Simple label reference (DO label)
    - OFFSET_CALL: Label with offset (DO label+offset)
    - ROUTINE_CALL: External routine reference (DO label^routine)
    - INDIRECT_CALL: Indirected call (DO @expr)
    - UNRESOLVED: Cannot determine statically
    """

    LABEL_CALL = auto()
    OFFSET_CALL = auto()
    ROUTINE_CALL = auto()
    INDIRECT_CALL = auto()
    UNRESOLVED = auto()


class LiteralType(Enum):
    """Type of literal value.

    Classifies the syntactic form of a literal:
    - STRING: Quoted string literal ("hello")
    - INTEGER: Integer numeric literal (42)
    - DECIMAL: Decimal numeric literal (3.14)
    """

    STRING = auto()
    INTEGER = auto()
    DECIMAL = auto()


class FormatControlType(Enum):
    """Type of I/O format control in WRITE/READ commands.

    Format controls modify device output:
    - NEWLINE: ! - Output newline (line feed)
    - FORMFEED: # - Output form feed (page break)
    - TAB: ?n - Tab to column n
    - CHARCODE: *n - Output character with ASCII code n
    """

    NEWLINE = auto()
    FORMFEED = auto()
    TAB = auto()
    CHARCODE = auto()


class IndirectionType(Enum):
    """Classification of indirection (@) usage patterns.

    Used to determine code generation strategy for indirect references:
    - NAME: Name indirection - @X where X contains a variable name
    - SUBSCRIPT: Subscript indirection - Y(@X) where X provides subscripts
    - ARGUMENT: Argument indirection - DO @X, GOTO @X where X contains label/routine
    - PATTERN: Pattern indirection - Y?@X where X contains pattern to match
    - UNKNOWN: Cannot determine type statically
    """

    NAME = auto()
    SUBSCRIPT = auto()
    ARGUMENT = auto()
    PATTERN = auto()
    UNKNOWN = auto()


class PassingMode(Enum):
    """Classification of parameter passing mode for function arguments.

    Used for variable analysis to track how arguments are passed:
    - BY_VALUE: Expression is evaluated and passed (D SUB(X+1) or D SUB(X))
    - BY_REFERENCE: Variable reference passed with . prefix (D SUB(.X))
      Creates aliasing - modifications to formal param affect caller's actual
    - OMITTED: Parameter position is empty (D SUB(,Y) - first arg omitted)

    Per MUMPS spec MDC 8.1.7:
    - Call-by-reference format: .actualname
    - Call-by-value format: expr
    - Omitted-parameter format: empty position in actuallist
    """

    BY_VALUE = auto()
    BY_REFERENCE = auto()
    OMITTED = auto()


class ScopeStrategy(Enum):
    """Classification of label for code generation strategy.

    Determines how a label should be transpiled to Python based on
    variable analysis and return value analysis:
    - PURE_FUNCTION: No side effects, can be clean Python function
      with args from formal_list and return from QUIT value
    - FUNCTION_WITH_OUTPUTS: Has return value AND modifies by-ref params
      Returns tuple of (return_value, modified_refs)
    - SUBROUTINE: No return value, may have side effects
      Python function returning None
    - REQUIRES_RUNTIME: Static analysis insufficient (indirection, XECUTE)
      Must use runtime.get_local()/set_local() pattern
    """

    PURE_FUNCTION = auto()
    FUNCTION_WITH_OUTPUTS = auto()
    SUBROUTINE = auto()
    REQUIRES_RUNTIME = auto()
