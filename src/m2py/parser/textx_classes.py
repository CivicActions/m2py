"""Custom classes for textX direct instantiation.

This module provides custom classes that textX can instantiate directly during parsing,
avoiding the need for post-parse conversion. These classes are wrappers that match
grammar rule names and accept textX constructor parameters, then create ASG nodes.

Key insight: textX custom classes must:
1. Have the same name as the grammar rule
2. Accept `parent` as the first parameter
3. Accept all attributes defined in the grammar rule

Each class inherits from an ASG class and overrides ``__init__`` to adapt
to textX's calling convention.
"""

from typing import List, Optional, Type

from m2py.asg.expressions import (
    MExpr,
    MLiteral,
    MVariable,
    MGlobal,
    MNakedGlobal,
    MIntrinsicFunction,
    MExtrinsicFunction,
    MExternalFunction,
    MSpecialVariable,
    MStructuredSystemVariable,
    MIndirection,
    MSelectArg,
    MDeviceControl,
)
from m2py.asg.statements import (
    MZWriteSubscriptAll,
    MZWriteSubscriptRange,
)
from m2py.asg.enums import LiteralType


# =============================================================================
# Helper Functions
# =============================================================================


def _unwrap_expr(expr):
    """Unwrap textX expression structure to get to the underlying ASG node.

    The textX grammar creates wrapper objects:
    - Expr: Contains left=UnaryExpr tail+=BinaryOpTail (where BinaryOpTail has op and right)
    - UnaryExpr: Contains operators + operand

    For simple expressions, we return the operand directly (our custom ASG class).
    For expressions with operators (binary ops, pattern match), the textX structure
    is preserved here because the semantic analyzer's _analyze_Expr() will process
    the tail elements to build proper ASG nodes (MBinaryOp, MPatternMatch, etc.).
    """
    if expr is None:
        return None

    # If it's already one of our ASG classes, return it
    if isinstance(expr, MExpr):
        return expr

    # Expr with left attribute (grammar: left=UnaryExpr (tail+=ExprTail)*)
    if hasattr(expr, "left"):
        # If no binary ops/pattern matches (tail is empty), just unwrap the left
        has_tail = hasattr(expr, "tail") and expr.tail
        if not has_tail:
            return _unwrap_expr(expr.left)
        # Complex expression with binary ops or pattern match - handled by semantic analyzer
        return expr

    # UnaryExpr without operator -> unwrap to operand
    # Check for 'operators' list (not 'operator') based on actual grammar
    if hasattr(expr, "operand"):
        operators = getattr(expr, "operators", None)
        operator = getattr(expr, "operator", None)
        has_operator = (operators and len(operators) > 0) or (operator is not None)
        if not has_operator:
            return _unwrap_expr(expr.operand)
        # Has operator(s) -> keep it (unary operation)
        return expr

    return expr


def _unwrap_subscripts(subscripts):
    """Extract and unwrap subscript expressions.

    Subscripts is a Subscripts object with args list of Expr objects.
    Returns list of unwrapped expressions.
    """
    if subscripts is None:
        return []

    if not hasattr(subscripts, "args"):
        return []

    return [_unwrap_expr(arg) for arg in subscripts.args]


def _get_function_arg_list(args):
    """Extract FunctionArg objects from the first+rest grammar structure.

    The grammar uses first+rest to allow empty leading arguments: (,arg2) -> [None, arg2]
    """
    if args is None:
        return []

    # Extract from first + rest structure
    if hasattr(args, "first"):
        result = []
        # Add first arg (may be None for empty leading position)
        if args.first is not None:
            result.append(args.first)
        elif hasattr(args, "rest") and args.rest:
            # Empty first position before comma - add placeholder
            result.append(None)
        # Add rest args
        if hasattr(args, "rest") and args.rest:
            for rest_item in args.rest:
                if hasattr(rest_item, "arg") and rest_item.arg is not None:
                    result.append(rest_item.arg)
                else:
                    result.append(None)  # Empty position
        return result

    return []


def _unwrap_function_args(args):
    """Extract and unwrap function argument expressions.

    FunctionArgs contains FunctionArg objects with either:
    - byref: ByRefArg (for .VAR or .@VAR by-reference syntax) - extract the variable or indirection
    - expr: Expr (for by-value expressions) - unwrap the expression

    For intrinsic functions, we just extract the expressions.
    The semantic analyzer handles MActualParameter creation for DO/extrinsic calls.
    """
    if args is None:
        return []

    arg_list = _get_function_arg_list(args)
    if not arg_list:
        return []

    result = []
    for arg in arg_list:
        if arg is None:
            # Omitted argument - append None
            result.append(None)
        # Check for by-reference argument: .VAR or .@VAR
        elif hasattr(arg, "byref") and arg.byref:
            # Extract the LocalVariable or Indirection from the ByRefArg
            byref = arg.byref
            if hasattr(byref, "indirect") and byref.indirect:
                result.append(byref.indirect)
            elif hasattr(byref, "var") and byref.var:
                result.append(byref.var)
            else:
                result.append(None)
        # Check for by-value argument: expression
        elif hasattr(arg, "expr") and arg.expr:
            result.append(_unwrap_expr(arg.expr))
        else:
            # Omitted argument - append None
            result.append(None)

    return result


def _unwrap_function_args_with_passing_mode(args):
    """Extract function arguments preserving by-reference passing mode.

    Used for extrinsic functions where by-reference semantics are meaningful.
    Creates MActualParameter objects with proper PassingMode.

    FunctionArgs contains FunctionArg objects with either:
    - byref: ByRefArg (for .VAR or .@VAR by-reference syntax)
    - expr: Expr (for by-value expressions)
    - neither: omitted parameter
    """
    from m2py.asg.enums import PassingMode
    from m2py.asg.expressions import MActualParameter

    if args is None:
        return []

    arg_list = _get_function_arg_list(args)
    if not arg_list:
        return []

    result = []
    for arg in arg_list:
        if arg is None:
            # Omitted argument
            result.append(
                MActualParameter(
                    passing_mode=PassingMode.OMITTED,
                    expression=None,
                    variable_name=None,
                )
            )
        # Check for by-reference argument: .VAR or .@VAR
        elif hasattr(arg, "byref") and arg.byref:
            byref = arg.byref
            # Check for indirection: .@VAR
            if hasattr(byref, "indirect") and byref.indirect:
                result.append(
                    MActualParameter(
                        passing_mode=PassingMode.BY_REFERENCE,
                        expression=byref.indirect,  # The Indirection
                        variable_name=None,  # Name determined at runtime
                    )
                )
            # Regular variable: .VAR
            elif hasattr(byref, "var") and byref.var:
                var = byref.var
                result.append(
                    MActualParameter(
                        passing_mode=PassingMode.BY_REFERENCE,
                        expression=var,  # The LocalVariable
                        variable_name=var.name,
                    )
                )
        # Check for by-value argument: expression
        elif hasattr(arg, "expr") and arg.expr:
            result.append(
                MActualParameter(
                    passing_mode=PassingMode.BY_VALUE,
                    expression=_unwrap_expr(arg.expr),
                    variable_name=None,
                )
            )
        else:
            # Omitted argument
            result.append(
                MActualParameter(
                    passing_mode=PassingMode.OMITTED,
                    expression=None,
                    variable_name=None,
                )
            )

    return result


# =============================================================================
# Expression Custom Classes
# =============================================================================


class NumericLiteral(MLiteral):
    """textX custom class for NumericLiteral grammar rule.

    Grammar: NumericLiteral: value=NUMBER;

    For numbers with exponent notation, we store both the parsed value
    and the original string representation to preserve precision for
    large numbers that exceed float64 precision.
    """

    def __init__(self, parent=None, value: str = ""):
        # Don't call super().__init__() with arguments - dataclass fields are set directly
        # textX will set parent automatically via the _tx_* attributes

        # Parse the numeric value
        if "." in value or "E" in value.upper():
            # Store as float for numeric operations, but flag that we have
            # an exact decimal representation for string operations
            parsed_value = float(value)
            lit_type = LiteralType.DECIMAL
            # Store exact string representation for precise formatting
            # This is used by m_str() to avoid float precision loss
            original_string = value
        else:
            parsed_value = int(value)
            lit_type = LiteralType.INTEGER
            original_string = None

        # Set dataclass fields directly
        object.__setattr__(self, "value", parsed_value)
        object.__setattr__(self, "literal_type", lit_type)
        # Store original string for precise formatting
        object.__setattr__(self, "_original_string", original_string)


class StringLiteral(MLiteral):
    """textX custom class for StringLiteral grammar rule.

    Grammar: StringLiteral: value=STRING_VALUE;
    """

    def __init__(self, parent=None, value: str = ""):
        # Remove surrounding quotes (grammar always provides them)
        parsed_value = value[1:-1]
        # Handle escaped quotes ("" -> ")
        parsed_value = parsed_value.replace('""', '"')

        object.__setattr__(self, "value", parsed_value)
        object.__setattr__(self, "literal_type", LiteralType.STRING)


class LocalVariable(MVariable):
    """textX custom class for LocalVariable grammar rule.

    Grammar: LocalVariable: name=VARNAME subscripts=Subscripts?;
    """

    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))


class GlobalVariable(MGlobal):
    """textX custom class for GlobalVariable grammar rule.

    Grammar: GlobalVariable: '^' name=VARNAME subscripts=Subscripts?;
    """

    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))


class ExtendedGlobalPipe(MGlobal):
    """textX custom class for ExtendedGlobalPipe grammar rule.

    Grammar: ExtendedGlobalPipe: '^|' environment=StringLiteral '|' name=VARNAME subscripts=Subscripts?;

    Represents pipe-delimited extended global reference: ^|"env"|globalname
    """

    def __init__(self, parent=None, name: str = "", subscripts=None, environment=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))
        object.__setattr__(self, "environment", environment)


class ExtendedGlobalBracket(MGlobal):
    """textX custom class for ExtendedGlobalBracket grammar rule.

    Grammar: ExtendedGlobalBracket: '^[' environment=StringLiteral ']' name=VARNAME subscripts=Subscripts?;

    Represents bracket-delimited extended global reference: ^["gld"]globalname
    """

    def __init__(self, parent=None, name: str = "", subscripts=None, environment=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))
        object.__setattr__(self, "environment", environment)


class NakedGlobal(MNakedGlobal):
    """textX custom class for NakedGlobal grammar rule.

    Grammar: NakedGlobal: '^' subscripts=Subscripts;
    """

    def __init__(self, parent=None, subscripts=None):
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))


# =============================================================================
# ZWRITE-specific Variable Classes with Pattern Subscripts
# =============================================================================


def _unwrap_zwrite_subscripts(subscripts):
    """Extract and unwrap ZWRITE subscript expressions, including ranges.

    ZWrite subscripts can include:
    - Regular expressions (expr=...)
    - Wildcard (*) via all='*'
    - Ranges (start:end) via start=... and end=... (either may be None)

    Grammar: ZWriteSubscript: all='*' | (start=Expr? ':' end=Expr?) | expr=Expr
    """
    if subscripts is None:
        return []

    if not hasattr(subscripts, "args"):
        return []

    result = []
    for arg in subscripts.args:
        # ZWRITE subscript wildcards and ranges - YDB extension edge case
        # Check for wildcard (all='*')
        if hasattr(arg, "all") and arg.all:
            result.append(MZWriteSubscriptAll())
        # Check for range (has start or end, or just ':' which gives both as None)
        # We detect range by checking if it's not an expr and not all
        elif hasattr(arg, "start") or hasattr(arg, "end"):
            # This could be a range even if start and end are both None (just ':')
            # We need to check if this is a range by looking for the ':' marker
            # In textX, after matching (start=Expr? ':' end=Expr?), we'll have
            # start and end attributes (possibly None)
            start_val = getattr(arg, "start", None)
            end_val = getattr(arg, "end", None)
            expr_val = getattr(arg, "expr", None)

            # If there's an expr, it's a plain expression, not a range
            if expr_val is not None:
                result.append(_unwrap_expr(expr_val))
            else:
                # It's a range (could be :, a:, :b, or a:b)
                range_sub = MZWriteSubscriptRange()
                if start_val is not None:
                    object.__setattr__(range_sub, "start", _unwrap_expr(start_val))
                if end_val is not None:
                    object.__setattr__(range_sub, "end", _unwrap_expr(end_val))
                result.append(range_sub)
        # Regular expression via expr attribute
        elif hasattr(arg, "expr") and arg.expr is not None:
            result.append(_unwrap_expr(arg.expr))

    return result


class ZWriteGlobalPattern:
    """textX custom class for ZWriteGlobalPattern grammar rule.

    Grammar: ZWriteGlobalPattern: '^' '?' name_pattern=PatternSpec subscripts=ZWriteSubscripts?;

    Global pattern match for ZWRITE - matches all globals whose names
    match the pattern. E.g., ^?.E matches all single-character global names.
    """

    def __init__(self, parent=None, name_pattern=None, subscripts=None):
        object.__setattr__(self, "name_pattern", name_pattern)
        object.__setattr__(self, "subscripts", _unwrap_zwrite_subscripts(subscripts))


class ZWriteGlobal(MGlobal):
    """textX custom class for ZWriteGlobal grammar rule.

    Grammar: ZWriteGlobal: '^' name=VARNAME subscripts=ZWriteSubscripts?;

    Global variable with ZWRITE pattern subscripts (ranges, wildcards).
    """

    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_zwrite_subscripts(subscripts))


class ZWriteNakedGlobal(MNakedGlobal):
    """textX custom class for ZWriteNakedGlobal grammar rule.

    Grammar: ZWriteNakedGlobal: '^' subscripts=ZWriteSubscripts;

    Naked global with ZWRITE pattern subscripts.
    """

    def __init__(self, parent=None, subscripts=None):
        object.__setattr__(self, "subscripts", _unwrap_zwrite_subscripts(subscripts))


class ZWriteLocal(MVariable):
    """textX custom class for ZWriteLocal grammar rule.

    Grammar: ZWriteLocal: name=VARNAME subscripts=ZWriteSubscripts?;

    Local variable with ZWRITE pattern subscripts.
    """

    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_zwrite_subscripts(subscripts))


class SpecialVariable(MSpecialVariable):
    """textX custom class for SpecialVariable grammar rule.

    Grammar: SpecialVariable: '$' name=SVARNAME;
    """

    def __init__(self, parent=None, name: str = ""):
        object.__setattr__(self, "name", name)


class AnySpecialVariable(MSpecialVariable):
    """textX custom class for AnySpecialVariable grammar rule.

    Grammar: AnySpecialVariable: '$' name=/[A-Za-z][A-Za-z0-9]*/;

    This is a catch-all for implementation-specific ISVs (e.g., $ZYERR, $ZINT)
    that may use non-standard abbreviations not covered by the strict SVARNAME list.
    """

    def __init__(self, parent=None, name: str = ""):
        object.__setattr__(self, "name", name)


class DeviceControl(MDeviceControl):
    """textX custom class for DeviceControl grammar rule.

    Grammar: DeviceControl: '/' keyword=DEVICECTRLKEYWORD ('(' params+=Expr[','] ')')?;

    Represents GT.M/YDB device control mnemonics like /EOF, /WAIT, /LISTEN, etc.
    """

    def __init__(self, parent=None, keyword: str = "", params=None):
        object.__setattr__(self, "keyword", keyword)
        object.__setattr__(self, "params", params if params else [])


class StructuredSystemVariable(MStructuredSystemVariable):
    """textX custom class for StructuredSystemVariable grammar rule.

    Grammar: StructuredSystemVariable: '^$' name=SSVNAME subscripts=Subscripts?;

    Represents Structured System Variables (SSVNs) per MUMPS 1995 spec 7.1.4.12:
    ^$CHARACTER, ^$DEVICE, ^$EVENT, ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE, ^$SYSTEM
    """

    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))


class IntrinsicFunction(MIntrinsicFunction):
    """textX custom class for IntrinsicFunction grammar rule.

    Grammar: IntrinsicFunction: '$' name=FUNCNAME args=FunctionArgs;
    This rule matches intrinsic function calls with parenthesized arguments
    (e.g., $P(X,"^",1)). Argumentless function references are matched by
    IntrinsicFunctionNoArgs instead.
    """

    def __init__(self, parent=None, name: str = "", args=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "arguments", _unwrap_function_args(args))


class IntrinsicFunctionNoArgs(MIntrinsicFunction):
    """textX custom class for IntrinsicFunctionNoArgs grammar rule.

    Grammar: IntrinsicFunctionNoArgs: '$' name=FUNCNAME;
    This rule matches intrinsic functions without arguments (e.g., $H, $J)
    and implementation-specific variables like $ZVersion. Maps to
    MIntrinsicFunction with an empty arguments list.
    """

    def __init__(self, parent=None, name: str = ""):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "arguments", [])


class SelectFunction(MIntrinsicFunction):
    """textX custom class for SelectFunction grammar rule.

    Grammar: SelectFunction: '$' name=SELECTNAME args=SelectFunctionArgs;

    $SELECT uses special syntax with condition:value pairs.
    We map this to MIntrinsicFunction with proper MSelectArg ASG nodes
    containing the unwrapped condition and value expressions.

    Name is preserved as-is (not uppercased); code generators normalize
    function names as needed.
    """

    def __init__(self, parent=None, name: str = "", args=None):
        object.__setattr__(self, "name", name)  # Preserve as-is for consistency
        # args is a SelectFunctionArgs with args=[SelectArg, ...]
        # Each SelectArg has .condition and .value attributes (raw textX objects)
        # Convert to proper MSelectArg ASG nodes with unwrapped expressions
        arguments = []
        if args is None or args.args is None:
            object.__setattr__(self, "select_args", arguments)
            return
        for select_arg in args.args:
            # Create MSelectArg with properly unwrapped expressions
            m_select_arg = MSelectArg()
            m_select_arg.condition = _unwrap_expr(select_arg.condition)
            m_select_arg.value = _unwrap_expr(select_arg.value)
            arguments.append(m_select_arg)
        object.__setattr__(self, "arguments", arguments)


class TextFunction(MIntrinsicFunction):
    """textX custom class for TextFunction grammar rule.

    Grammar: TextFunction: '$' name=TEXTNAME '(' arg=TextFunctionArg ')';

    $TEXT uses special line-reference syntax. The argument contains:
    - labelIndirect: Indirection for label part (e.g., @X in $T(@X+1))
    - label: Label name
    - offset: Optional offset expression (via OffsetExpr)
    - routineIndirect: Indirection for routine name
    - routine: Literal routine name

    We map this to MIntrinsicFunction. The arguments list is empty (line refs
    are not normal expressions). The line_ref dict captures parsed components.
    """

    def __init__(self, parent=None, name: str = "", arg=None):
        object.__setattr__(self, "name", name)  # Preserve as-is

        # Build a dict capturing the line reference structure
        # Values are unwrapped ASG nodes where applicable
        line_ref = {}
        if arg:
            # Check for label indirection (e.g., $T(@X) or $T(@X+1))
            if hasattr(arg, "labelIndirect") and arg.labelIndirect:
                line_ref["label_indirect"] = _unwrap_expr(arg.labelIndirect)
            elif hasattr(arg, "label") and arg.label:
                line_ref["label"] = arg.label  # Plain string
            # Offset is always captured regardless of whether label is static or indirect
            if hasattr(arg, "offset") and arg.offset:
                line_ref["offset"] = _unwrap_expr(arg.offset)
            # Capture offset sign (+ or -) for proper offset handling
            # offsetSign is set when + or - precedes the offset expression
            if hasattr(arg, "offsetSign") and arg.offsetSign:
                line_ref["offset_sign"] = arg.offsetSign
            if hasattr(arg, "routineIndirect") and arg.routineIndirect:
                line_ref["routine_indirect"] = _unwrap_expr(arg.routineIndirect)
            if hasattr(arg, "routine") and arg.routine:
                line_ref["routine"] = arg.routine  # Plain string

        # Don't put dict in arguments - that causes analyzer issues
        # The line_ref is stored separately
        object.__setattr__(self, "arguments", [])
        object.__setattr__(self, "line_ref", line_ref)


class ExtrinsicFunction(MExtrinsicFunction):
    """textX custom class for ExtrinsicFunction grammar rule.

    Grammar: ExtrinsicFunction: '$$' label=TEXTLABELNAME? ('^' (routineIndirect=Indirection | routine=VARNAME))? args=FunctionArgs?;

    Extrinsic functions support full parameter passing semantics including
    by-reference (.VAR syntax), so we preserve MActualParameter info.
    Routine part can be indirect: $$func^@(routineExpr)
    """

    def __init__(
        self,
        parent=None,
        label: str = "",
        routine: Optional[str] = None,
        routineIndirect=None,
        args=None,
    ):
        from m2py.asg.elements import MCall

        # Create an MCall target
        call = MCall()
        call.name = label if label else ""
        call.routine = routine

        # Handle routine indirection: $$func^@(expr)
        if routineIndirect is not None:
            call.routine_indirection = routineIndirect
            call.routine_is_indirect = True

        object.__setattr__(self, "target", call)
        # Use the helper that preserves by-ref passing mode
        object.__setattr__(
            self, "arguments", _unwrap_function_args_with_passing_mode(args)
        )


class ExternalFunction(MExternalFunction):
    """textX custom class for ExternalFunction grammar rule.

    Grammar: ExternalFunction: '$&' package=VARNAME? ('.' name=VARNAME | name=VARNAME) args=FunctionArgs?;

    External functions call C/system functions linked into the MUMPS runtime.
    They support full parameter passing semantics including by-reference.
    """

    def __init__(
        self, parent=None, package: Optional[str] = None, name: str = "", args=None
    ):
        object.__setattr__(self, "package", package)
        object.__setattr__(self, "name", name)
        # Use the helper that preserves by-ref passing mode
        object.__setattr__(
            self, "arguments", _unwrap_function_args_with_passing_mode(args)
        )


class Indirection(MIndirection):
    """textX custom class for Indirection grammar rule.

    Grammar: Indirection: '@' expr=PrimaryExpr subscripts=Subscripts? name_subscripts+=NameIndirectionSubscripts*;

    Supports:
    - @X - simple indirection
    - @X(1,2) - indirection with direct subscripts
    - @X@(1,2) - name indirection: evaluate X, use as variable name, append subscripts
    - @X@(1)@(2) - chained name indirection subscripts
    """

    def __init__(self, parent=None, expr=None, subscripts=None, name_subscripts=None):
        object.__setattr__(self, "expression", _unwrap_expr(expr))
        # Handle direct subscripts for @X(1,2) form
        if subscripts is not None:
            object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))
        else:
            object.__setattr__(self, "subscripts", None)
        # Handle name indirection subscripts for @X@(1,2) form
        if name_subscripts:
            # Each name_subscripts item has a 'subscripts' attribute
            name_ind_subs = []
            for ns in name_subscripts:
                if hasattr(ns, "subscripts") and ns.subscripts:
                    name_ind_subs.append(_unwrap_subscripts(ns.subscripts))
            object.__setattr__(
                self,
                "name_indirection_subscripts",
                name_ind_subs if name_ind_subs else None,
            )
        else:
            object.__setattr__(self, "name_indirection_subscripts", None)


# =============================================================================
# Unknown Command Handler
# =============================================================================


class UnknownCommand:
    """Catch-all for unrecognized commands.

    This class is instantiated by textX when a word in command position
    doesn't match any known command. It immediately raises an error
    with a clear message about the unrecognized command.

    This ensures unknown commands fail fast during parsing rather than
    propagating through to the ASG or code generation phases.
    """

    def __init__(self, parent=None, word: str = "", rest: str = "", **kwargs):
        """Raise MUMPSUnknownCommandError for the unrecognized command.

        Args:
            parent: Parent node (from textX)
            word: The unrecognized command word
            rest: Rest of the line after the command word
            **kwargs: Additional textX attributes (e.g., _tx_position)
        """
        from m2py.parser.exceptions import MUMPSUnknownCommandError

        raise MUMPSUnknownCommandError(
            command=word,
            line=None,  # Position info not easily available from textX offset
            column=None,
        )


class FunctionArgs:
    """Custom class for FunctionArgs grammar rule.

    Wraps the first+rest grammar pattern and exposes a flat .args property
    for convenient access. The first+rest structure supports empty leading
    arguments like (,arg2).
    """

    def __init__(self, parent=None, first=None, rest=None, **kwargs):
        self._first = first
        self._rest = rest if rest else []
        self.parent = parent

    @property
    def first(self):
        return self._first

    @property
    def rest(self):
        return self._rest

    @property
    def args(self):
        """Backward-compatible args list.

        Converts first+rest representation to a flat list of FunctionArg objects.
        Empty positions (None) are preserved for omitted arguments.
        """
        result = []
        # Add first arg
        if self._first is not None:
            result.append(self._first)
        elif self._rest:
            # Empty first position with subsequent args - add placeholder
            result.append(None)
        # Add rest args
        for rest_item in self._rest:
            if hasattr(rest_item, "arg"):
                result.append(rest_item.arg)
        return result


# =============================================================================
# Class Registry
# =============================================================================

# Classes from expressions.tx grammar
EXPRESSION_CLASSES = [
    NumericLiteral,
    StringLiteral,
    LocalVariable,
    GlobalVariable,
    ExtendedGlobalPipe,
    ExtendedGlobalBracket,
    NakedGlobal,
    SpecialVariable,
    StructuredSystemVariable,
    TextFunction,
    SelectFunction,
    IntrinsicFunction,
    IntrinsicFunctionNoArgs,
    ExtrinsicFunction,
    ExternalFunction,
    Indirection,
    FunctionArgs,
]

# Classes from commands.tx grammar (expressions used within command context)
COMMAND_EXPRESSION_CLASSES = [
    AnySpecialVariable,  # Catch-all for $Zxxx ISVs
    DeviceControl,  # Device control mnemonics like /EOF, /WAIT
    ZWriteGlobalPattern,  # ZWRITE global name pattern match (^?.E)
    ZWriteGlobal,  # ZWRITE global with pattern subscripts
    ZWriteNakedGlobal,  # ZWRITE naked global with pattern subscripts
    ZWriteLocal,  # ZWRITE local variable with pattern subscripts
]

# Command classes that need special handling
COMMAND_CLASSES = [
    UnknownCommand,
]


def get_expression_classes() -> List[Type]:
    """Get list of custom expression classes for textX registration.

    Only includes classes from expressions.tx grammar.
    """
    return EXPRESSION_CLASSES.copy()


def get_all_classes() -> List[Type]:
    """Get all custom classes (expressions + commands) for textX registration.

    This includes expression classes, command expression classes, and command classes.
    Use this when loading the full command grammar.
    """
    return EXPRESSION_CLASSES + COMMAND_EXPRESSION_CLASSES + COMMAND_CLASSES
