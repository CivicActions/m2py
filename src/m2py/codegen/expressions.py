"""Expression code generation for MUMPS-to-Python transpilation.

Generates Python expression strings from MUMPS ASG expression nodes.
Handles literals, variables, binary operations, unary operations, and extrinsic functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from m2py.asg.enums import LiteralType, PassingMode
from m2py.asg.expressions import (
    MActualParameter,
    MBinaryOp,
    MExpr,
    MExtrinsicFunction,
    MLiteral,
    MSpecialVariable,
    MUnaryOp,
    MVariable,
)
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.names import translate_name

if TYPE_CHECKING:
    from m2py.codegen.routine import GeneratorContext


def generate_expr(expr: MExpr, ctx: "GeneratorContext") -> str:
    """Generate Python expression from ASG expression node.

    Dispatches based on expression type:
    - MLiteral → literal value
    - MVariable → translated variable name
    - MBinaryOp → operation with coercion
    - MUnaryOp → unary operation
    - MExtrinsicFunction → function call with $TEST save/restore

    Args:
        expr: ASG expression node
        ctx: Generator context (for name translation, etc.)

    Returns:
        Python expression string

    Raises:
        NotImplementedError: For unsupported expression types
    """
    if isinstance(expr, MLiteral):
        return _generate_literal(expr)
    elif isinstance(expr, MVariable):
        return _generate_variable(expr, ctx)
    elif isinstance(expr, MBinaryOp):
        return _generate_binary_op(expr, ctx)
    elif isinstance(expr, MUnaryOp):
        return _generate_unary_op(expr, ctx)
    elif isinstance(expr, MExtrinsicFunction):
        return _generate_extrinsic(expr, ctx)
    elif isinstance(expr, MSpecialVariable):
        return _generate_special_variable(expr, ctx)
    # Phase 8: $TEXT/$T support for current routine (handle multiple ASG node types)
    elif (
        expr.__class__.__name__ in ("TextFunction", "IntrinsicFunction")
        and getattr(expr, "name", "").upper() in ("TEXT", "T")
    ) or (hasattr(expr, "name") and getattr(expr, "name", "").upper() in ("TEXT", "T")):
        args = getattr(expr, "arguments", [])
        # $T() with no args: treat as $T(+0) (routine name)
        if len(args) == 0:
            return "_rt.get_text(offset=0)"
        if len(args) == 1:
            arg = args[0]
            # $T(+N) or $T(-N): arg is a literal or unary op
            if hasattr(arg, "value") and isinstance(arg.value, int):
                return f"_rt.get_text(offset={arg.value})"
            elif hasattr(arg, "operator") and arg.operator in ("+", "-"):
                val = generate_expr(arg.operand, ctx)
                sign = "-" if arg.operator == "-" else ""
                return f"_rt.get_text(offset={sign}{val})"
            elif hasattr(arg, "name"):
                # $T(LABEL)
                label = arg.name
                return f'_rt.get_text(label="{label}")'
            elif hasattr(arg, "left") and hasattr(arg, "right"):
                # $T(LABEL+N)
                label = getattr(arg.left, "name", None)
                offset = getattr(arg.right, "value", None)
                if label is not None and offset is not None:
                    return f'_rt.get_text(label="{label}", offset={offset})'
        raise NotImplementedError("Unsupported $TEXT/$T argument pattern")
    else:
        raise NotImplementedError(f"Unsupported expression type: {type(expr).__name__}")


def _generate_literal(lit: MLiteral) -> str:
    """Generate Python literal from MLiteral.

    Args:
        lit: MLiteral node

    Returns:
        Python literal string
    """
    if lit.literal_type == LiteralType.STRING:
        # Escape special characters and wrap in quotes
        escaped = str(lit.value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    elif lit.literal_type == LiteralType.INTEGER:
        return str(lit.value)
    elif lit.literal_type == LiteralType.DECIMAL:
        return str(lit.value)
    else:
        # Default: treat as string
        escaped = str(lit.value).replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'


def _generate_variable(var: MVariable, ctx: "GeneratorContext") -> str:
    """Generate Python variable reference from MVariable.

    Spec 006: When using TRAMPOLINE strategy and the variable is in state_vars,
    access it via `state.VAR` instead of just `VAR`.

    Spec 006 (T075): Handle subscripted variable reads for MArray-backed variables.
    For array variables, generate: state.A.get(subscripts)

    Args:
        var: MVariable node
        ctx: Generator context

    Returns:
        Python expression string for the variable reference
    """
    # Translate name to valid Python identifier
    python_name = translate_name(var.name)

    # Spec 006 (T075): Handle subscripted array access
    if var.subscripts:
        # Generate subscript expressions
        subscript_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]

        # Determine base variable access
        if ctx.strategy == GotoStrategy.TRAMPOLINE and var.name in ctx.array_vars:
            # MArray in RoutineState: state.A.get(subscripts)
            base = f"state.{python_name}"
        else:
            # Local MArray variable: A.get(subscripts)
            base = python_name

        # Use .get() for reading - returns value directly (or "" if undefined)
        return f"{base}.get({', '.join(subscript_exprs)})"

    # Spec 006: Check if variable should be accessed via state
    if ctx.strategy == GotoStrategy.TRAMPOLINE and var.name in ctx.state_vars:
        return f"state.{python_name}"

    return python_name


def _generate_special_variable(var: MSpecialVariable, ctx: "GeneratorContext") -> str:
    """Generate Python expression for MUMPS special variable.

    Currently supported:
    - $TEST ($T): Returns int(_test) for MUMPS-style 0/1 output

    Args:
        var: MSpecialVariable node (name without $ prefix)
        ctx: Generator context

    Returns:
        Python expression string

    Raises:
        NotImplementedError: For unsupported special variables
    """
    name = var.name.upper()  # Normalize to uppercase

    # $TEST / $T - returns the _test global as integer (0 or 1)
    # MUMPS $TEST is always 0 or 1, not Python True/False
    if name in ("TEST", "T"):
        return "int(_test)"

    # Add other special variables as needed
    raise NotImplementedError(f"Special variable ${var.name} not yet supported")


def _generate_binary_op(op: MBinaryOp, ctx: "GeneratorContext") -> str:
    """Generate Python binary operation from MBinaryOp.

    MUMPS operators and their Python translations:
    - Arithmetic (+, -): Use m_num() coercion on operands
    - Comparison (=, <, >): Use m_compare() helper
    - String concatenation (_): Use + on strings

    Args:
        op: MBinaryOp node
        ctx: Generator context

    Returns:
        Python expression string
    """
    left = generate_expr(op.left, ctx) if op.left else "0"
    right = generate_expr(op.right, ctx) if op.right else "0"

    if op.operator in ("+", "-"):
        # Arithmetic: coerce both operands to numeric
        return f"(m_num({left}) {op.operator} m_num({right}))"
    elif op.operator in ("*", "/"):
        # Multiplication/Division: coerce both operands
        return f"(m_num({left}) {op.operator} m_num({right}))"
    elif op.operator == "\\":
        # Integer division in MUMPS
        return f"(int(m_num({left}) // m_num({right})))"
    elif op.operator == "#":
        # Modulo in MUMPS
        return f"(m_num({left}) % m_num({right}))"
    elif op.operator in ("=", "<", ">"):
        # Comparison: use m_compare helper
        return f'm_compare({left}, "{op.operator}", {right})'
    elif op.operator == "_":
        # String concatenation
        return f"(str({left}) + str({right}))"
    else:
        raise NotImplementedError(f"Unsupported binary operator: {op.operator}")


def _generate_unary_op(op: MUnaryOp, ctx: "GeneratorContext") -> str:
    """Generate Python unary operation from MUnaryOp.

    Args:
        op: MUnaryOp node
        ctx: Generator context

    Returns:
        Python expression string
    """
    operand = generate_expr(op.operand, ctx) if op.operand else "0"

    if op.operator == "-":
        # Numeric negation
        return f"(-m_num({operand}))"
    elif op.operator == "+":
        # Unary plus (force numeric)
        return f"(+m_num({operand}))"
    elif op.operator == "'":
        # Logical NOT in MUMPS
        return f"(not m_truth({operand}))"
    else:
        raise NotImplementedError(f"Unsupported unary operator: {op.operator}")


def _generate_extrinsic(expr: MExtrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python extrinsic function call from MExtrinsicFunction.

    T066: Extrinsic functions ($$label) require $TEST save/restore semantics.
    Per MUMPS spec, the caller's $TEST is saved before the call and restored
    after, so the callee's $TEST changes don't leak back.

    Generated pattern (internal):
        _call_extrinsic(LABEL, arg1, arg2)

    Generated pattern (external - Spec 008 Phase 7):
        _call_extrinsic(ext2.ADD, arg1, arg2, _scope=_scope)

    The _call_extrinsic helper handles save/restore of _test.

    Args:
        expr: MExtrinsicFunction node
        ctx: Generator context

    Returns:
        Python expression string

    Raises:
        NotImplementedError: For unsupported patterns
    """
    # Get the target label
    if expr.target is None:
        raise NotImplementedError("Extrinsic function without target not supported")

    label_name = expr.target.name
    if not label_name:
        raise NotImplementedError("Extrinsic function with empty label not supported")

    # Spec 008 Phase 7 (T043-T046): Handle external routine extrinsic
    if expr.target.routine:
        routine_name = expr.target.routine

        # T044: Generate import statement for external routine
        ctx.emitter.line(f"import {routine_name}")

        # Translate label name to Python function name
        func_name = translate_name(label_name)

        # Generate arguments
        args = _generate_extrinsic_arguments(expr.arguments, ctx)

        # T045-T046: Generate call via _call_extrinsic with module prefix and _scope
        # The _call_extrinsic helper provides $TEST save/restore
        if args:
            return f"_call_extrinsic({routine_name}.{func_name}, {args}, _scope=_scope)"
        else:
            return f"_call_extrinsic({routine_name}.{func_name}, _scope=_scope)"

    # Internal extrinsic (within same routine)
    # Translate label name to Python function name
    func_name = translate_name(label_name)

    # Generate arguments
    args = _generate_extrinsic_arguments(expr.arguments, ctx)

    # Generate: _call_extrinsic(FUNC, arg1, arg2)
    if args:
        return f"_call_extrinsic({func_name}, {args})"
    else:
        return f"_call_extrinsic({func_name})"


def _generate_extrinsic_arguments(
    arguments: List[MActualParameter], ctx: "GeneratorContext"
) -> str:
    """Generate Python arguments for extrinsic function call.

    Note: By-reference parameters in extrinsic functions would need special
    handling (similar to DO calls in Phase 10), but for Spec 005 we just
    pass values. Full by-ref support for extrinsics is Spec 010.

    Args:
        arguments: List of MActualParameter
        ctx: Generator context

    Returns:
        Comma-separated argument string
    """
    if not arguments:
        return ""

    parts = []
    for arg in arguments:
        if arg.passing_mode == PassingMode.OMITTED:
            parts.append("None")
        elif arg.expression:
            parts.append(generate_expr(arg.expression, ctx))
        elif arg.variable_name:
            parts.append(translate_name(arg.variable_name))
        else:
            parts.append("None")

    return ", ".join(parts)


__all__ = ["generate_expr"]
