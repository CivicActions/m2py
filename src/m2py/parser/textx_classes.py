"""Custom classes for textX direct instantiation.

This module provides custom classes that textX can instantiate directly during parsing,
avoiding the need for post-parse conversion. These classes are wrappers that match
grammar rule names and accept textX constructor parameters, then create ASG nodes.

Key insight: textX custom classes must:
1. Have the same name as the grammar rule
2. Accept `parent` as the first parameter
3. Accept all attributes defined in the grammar rule

We use a class factory approach to create wrappers that inherit from ASG classes
but adapt to textX's calling convention.
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
    MSpecialVariable,
    MIndirection,
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
    is preserved here because SemanticAnalyzer._analyze_Expr() will process the
    tail elements to build proper ASG nodes (MBinaryOp, MPatternMatch, etc.).
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


def _unwrap_function_args(args):
    """Extract and unwrap function argument expressions.

    FunctionArgs contains FunctionArg objects with either:
    - byref: ByRefArg (for .VAR by-reference syntax) - extract the variable
    - expr: Expr (for by-value expressions) - unwrap the expression

    For intrinsic functions, we just extract the expressions.
    The semantic analyzer handles MActualParameter creation for DO/extrinsic calls.
    """
    if args is None:
        return []

    if not hasattr(args, "args"):
        return []

    result = []
    for arg in args.args:
        # Check for by-reference argument: .VAR
        if hasattr(arg, "byref") and arg.byref:
            # Extract the LocalVariable from the ByRefArg
            result.append(arg.byref.var)
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
    - byref: ByRefArg (for .VAR by-reference syntax)
    - expr: Expr (for by-value expressions)
    - neither: omitted parameter
    """
    from m2py.asg.enums import PassingMode
    from m2py.asg.expressions import MActualParameter

    if args is None:
        return []

    if not hasattr(args, "args"):
        return []

    result = []
    for arg in args.args:
        # Check for by-reference argument: .VAR
        if hasattr(arg, "byref") and arg.byref:
            var = arg.byref.var
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
    """

    def __init__(self, parent=None, value: str = ""):
        # Don't call super().__init__() with arguments - dataclass fields are set directly
        # textX will set parent automatically via the _tx_* attributes

        # Parse the numeric value
        try:
            if "." in value or "E" in value.upper():
                parsed_value = float(value)
                lit_type = LiteralType.DECIMAL
            else:
                parsed_value = int(value)
                lit_type = LiteralType.INTEGER
        except (ValueError, TypeError):
            parsed_value = value
            lit_type = LiteralType.STRING

        # Set dataclass fields directly
        object.__setattr__(self, "value", parsed_value)
        object.__setattr__(self, "literal_type", lit_type)
        object.__setattr__(self, "result_type", None)


class StringLiteral(MLiteral):
    """textX custom class for StringLiteral grammar rule.

    Grammar: StringLiteral: value=STRING_VALUE;
    """

    def __init__(self, parent=None, value: str = ""):
        # Remove surrounding quotes
        if value.startswith('"') and value.endswith('"'):
            parsed_value = value[1:-1]
            # Handle escaped quotes ("" -> ")
            parsed_value = parsed_value.replace('""', '"')
        else:
            parsed_value = value

        object.__setattr__(self, "value", parsed_value)
        object.__setattr__(self, "literal_type", LiteralType.STRING)
        object.__setattr__(self, "result_type", None)


class LocalVariable(MVariable):
    """textX custom class for LocalVariable grammar rule.

    Grammar: LocalVariable: name=VARNAME subscripts=Subscripts?;
    """

    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))
        object.__setattr__(self, "result_type", None)


class GlobalVariable(MGlobal):
    """textX custom class for GlobalVariable grammar rule.

    Grammar: GlobalVariable: '^' name=VARNAME subscripts=Subscripts?;
    """

    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))
        object.__setattr__(self, "result_type", None)


class NakedGlobal(MNakedGlobal):
    """textX custom class for NakedGlobal grammar rule.

    Grammar: NakedGlobal: '^' subscripts=Subscripts;
    """

    def __init__(self, parent=None, subscripts=None):
        object.__setattr__(self, "subscripts", _unwrap_subscripts(subscripts))
        object.__setattr__(self, "result_type", None)


class SpecialVariable(MSpecialVariable):
    """textX custom class for SpecialVariable grammar rule.

    Grammar: SpecialVariable: '$' name=SVARNAME;
    """

    def __init__(self, parent=None, name: str = ""):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "result_type", None)


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
        object.__setattr__(self, "result_type", None)


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
        object.__setattr__(self, "result_type", None)


class SelectFunction(MIntrinsicFunction):
    """textX custom class for SelectFunction grammar rule.

    Grammar: SelectFunction: '$' name=SELECTNAME args=SelectFunctionArgs;

    $SELECT uses special syntax with condition:value pairs.
    We map this to MIntrinsicFunction with the condition:value pairs
    stored as a list of tuples in the arguments.

    Note: Name is preserved as-is (not uppercased) for consistency with
    IntrinsicFunction. Code generators normalize function names as needed.
    """

    def __init__(self, parent=None, name: str = "", args=None):
        object.__setattr__(self, "name", name)  # Preserve as-is for consistency
        # args is a SelectFunctionArgs with args=[SelectArg, ...]
        # Each SelectArg has .condition and .value attributes
        arguments = []
        if args and hasattr(args, "args"):
            for select_arg in args.args:
                # Store as tuple (condition, value) for code generation
                arguments.append((select_arg.condition, select_arg.value))
        object.__setattr__(self, "arguments", arguments)
        object.__setattr__(self, "result_type", None)


class ExtrinsicFunction(MExtrinsicFunction):
    """textX custom class for ExtrinsicFunction grammar rule.

    Grammar: ExtrinsicFunction: '$$' label=VARNAME ('^' routine=VARNAME)? args=FunctionArgs?;

    Extrinsic functions support full parameter passing semantics including
    by-reference (.VAR syntax), so we preserve MActualParameter info.
    """

    def __init__(
        self, parent=None, label: str = "", routine: Optional[str] = None, args=None
    ):
        from m2py.asg.elements import MCall

        # Create an MCall target
        call = MCall()
        call.name = label
        call.routine = routine
        object.__setattr__(self, "target", call)
        # Use the helper that preserves by-ref passing mode
        object.__setattr__(
            self, "arguments", _unwrap_function_args_with_passing_mode(args)
        )

        object.__setattr__(self, "result_type", None)


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
        object.__setattr__(self, "requires_runtime_eval", True)
        object.__setattr__(self, "result_type", None)


# =============================================================================
# Class Registry
# =============================================================================

# List of all custom classes for registration with textX
EXPRESSION_CLASSES = [
    NumericLiteral,
    StringLiteral,
    LocalVariable,
    GlobalVariable,
    NakedGlobal,
    SpecialVariable,
    SelectFunction,
    IntrinsicFunction,
    IntrinsicFunctionNoArgs,
    ExtrinsicFunction,
    Indirection,
]


def get_expression_classes() -> List[Type]:
    """Get list of custom expression classes for textX registration."""
    return EXPRESSION_CLASSES.copy()


def get_class_for_rule(rule_name: str) -> Optional[Type]:
    """Get custom class for a grammar rule name.

    This can be passed as a callable to metamodel_from_file(classes=...).
    """
    class_map = {cls.__name__: cls for cls in EXPRESSION_CLASSES}
    return class_map.get(rule_name)
