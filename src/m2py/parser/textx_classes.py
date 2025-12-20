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
    - Expr: Contains left=UnaryExpr (ops+=BinaryOp right+=UnaryExpr)*
    - UnaryExpr: Contains operator + operand
    
    For simple expressions, we want just the operand (our custom class).
    For expressions with operators, we keep the structure for now.
    """
    if expr is None:
        return None
    
    # If it's already one of our ASG classes, return it
    if isinstance(expr, MExpr):
        return expr
    
    # Expr with left attribute (new grammar)
    if hasattr(expr, 'left'):
        # If no binary ops, just unwrap the left
        if not hasattr(expr, 'ops') or not expr.ops:
            return _unwrap_expr(expr.left)
        # Has binary ops - keep for now (semantic analyzer will handle)
        return expr
    
    # UnaryExpr without operator -> unwrap to operand
    if hasattr(expr, 'operand') and (not hasattr(expr, 'operator') or expr.operator is None):
        return _unwrap_expr(expr.operand)
    
    # UnaryExpr with operator -> keep it (unary operation)
    if hasattr(expr, 'operator') and expr.operator is not None:
        # Could create MUnaryOp here, but that requires more work
        return expr
    
    return expr


def _unwrap_subscripts(subscripts):
    """Extract and unwrap subscript expressions.
    
    Subscripts is a Subscripts object with args list of Expr objects.
    Returns list of unwrapped expressions.
    """
    if subscripts is None:
        return []
    
    if not hasattr(subscripts, 'args'):
        return []
    
    return [_unwrap_expr(arg) for arg in subscripts.args]


def _unwrap_function_args(args):
    """Extract and unwrap function argument expressions.
    
    FunctionArgs is similar to Subscripts.
    """
    return _unwrap_subscripts(args)


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
            if '.' in value or 'E' in value.upper():
                parsed_value = float(value)
                lit_type = LiteralType.DECIMAL
            else:
                parsed_value = int(value)
                lit_type = LiteralType.INTEGER
        except (ValueError, TypeError):
            parsed_value = value
            lit_type = LiteralType.STRING
        
        # Set dataclass fields directly
        object.__setattr__(self, 'value', parsed_value)
        object.__setattr__(self, 'literal_type', lit_type)
        object.__setattr__(self, 'result_type', None)


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
        
        object.__setattr__(self, 'value', parsed_value)
        object.__setattr__(self, 'literal_type', LiteralType.STRING)
        object.__setattr__(self, 'result_type', None)


class LocalVariable(MVariable):
    """textX custom class for LocalVariable grammar rule.
    
    Grammar: LocalVariable: name=VARNAME subscripts=Subscripts?;
    """
    
    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'subscripts', _unwrap_subscripts(subscripts))
        object.__setattr__(self, 'result_type', None)


class GlobalVariable(MGlobal):
    """textX custom class for GlobalVariable grammar rule.
    
    Grammar: GlobalVariable: '^' name=VARNAME subscripts=Subscripts?;
    """
    
    def __init__(self, parent=None, name: str = "", subscripts=None):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'subscripts', _unwrap_subscripts(subscripts))
        object.__setattr__(self, 'result_type', None)


class NakedGlobal(MNakedGlobal):
    """textX custom class for NakedGlobal grammar rule.
    
    Grammar: NakedGlobal: '^' subscripts=Subscripts;
    """
    
    def __init__(self, parent=None, subscripts=None):
        object.__setattr__(self, 'subscripts', _unwrap_subscripts(subscripts))
        object.__setattr__(self, 'requires_runtime_tracking', True)
        object.__setattr__(self, 'result_type', None)


class SpecialVariable(MSpecialVariable):
    """textX custom class for SpecialVariable grammar rule.
    
    Grammar: SpecialVariable: '$' name=SVARNAME;
    """
    
    def __init__(self, parent=None, name: str = ""):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'result_type', None)


class IntrinsicFunction(MIntrinsicFunction):
    """textX custom class for IntrinsicFunction grammar rule.
    
    Grammar: IntrinsicFunction: '$' name=FUNCNAME args=FunctionArgs?;
    """
    
    def __init__(self, parent=None, name: str = "", args=None):
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'arguments', _unwrap_function_args(args))
        object.__setattr__(self, 'result_type', None)


class ExtrinsicFunction(MExtrinsicFunction):
    """textX custom class for ExtrinsicFunction grammar rule.
    
    Grammar: ExtrinsicFunction: '$$' label=VARNAME ('^' routine=VARNAME)? args=FunctionArgs?;
    """
    
    def __init__(self, parent=None, label: str = "", routine: str = None, args=None):
        from m2py.asg.elements import MCall
        
        # Create an MCall target
        call = MCall()
        call.name = label
        call.routine = routine
        object.__setattr__(self, 'target', call)
        object.__setattr__(self, 'arguments', _unwrap_function_args(args))
        
        object.__setattr__(self, 'result_type', None)


class Indirection(MIndirection):
    """textX custom class for Indirection grammar rule.
    
    Grammar: Indirection: '@' expr=PrimaryExpr subscripts=Subscripts?;
    """
    
    def __init__(self, parent=None, expr=None, subscripts=None):
        object.__setattr__(self, 'expression', _unwrap_expr(expr))
        # Note: MIndirection doesn't have a subscripts field in ASG
        # But we should probably add it for completeness
        object.__setattr__(self, 'requires_runtime_eval', True)
        object.__setattr__(self, 'result_type', None)


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
    IntrinsicFunction,
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
