"""Expression code generation for MUMPS-to-Python transpilation.

Generates Python expression strings from MUMPS ASG expression nodes.
Handles literals, variables, binary operations, unary operations, and extrinsic functions.

Spec 010: Extended with intrinsic function dispatch table for $LENGTH, $PIECE, etc.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, List

from m2py.asg.enums import LiteralType, PassingMode
from m2py.asg.expressions import (
    MActualParameter,
    MBinaryOp,
    MExpr,
    MExtrinsicFunction,
    MIntrinsicFunction,
    MLiteral,
    MSpecialVariable,
    MUnaryOp,
    MVariable,
)
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.names import translate_name
from m2py.parser.textx_classes import GlobalVariable, NakedGlobal

if TYPE_CHECKING:
    from m2py.codegen.routine import GeneratorContext


# =============================================================================
# Intrinsic Function Dispatch Table (Spec 010)
# =============================================================================

# Type alias for intrinsic function generator functions
IntrinsicGenerator = Callable[["MIntrinsicFunction", "GeneratorContext"], str]

# Dispatch table mapping function names (uppercase) to generator functions.
# Both full names and abbreviations are registered.
# Populated at module load time after functions are defined.
INTRINSIC_GENERATORS: Dict[str, IntrinsicGenerator] = {}


def generate_intrinsic_function(
    expr: MIntrinsicFunction, ctx: "GeneratorContext"
) -> str:
    """Generate Python code for MUMPS intrinsic function.

    Dispatches to function-specific generators based on the function name.
    Falls back to existing special-case handlers for $DATA and $TEXT until
    they are migrated to this dispatch table.

    Args:
        expr: MIntrinsicFunction ASG node
        ctx: Generator context

    Returns:
        Python expression string

    Raises:
        NotImplementedError: For unsupported function names
    """
    # Normalize function name to uppercase for dispatch
    func_name = expr.name.upper()

    # Check dispatch table first
    if func_name in INTRINSIC_GENERATORS:
        return INTRINSIC_GENERATORS[func_name](expr, ctx)

    # Fall back to existing special-case handlers until migrated
    # $DATA/$D is handled by existing _generate_data
    if func_name in ("DATA", "D"):
        return _generate_data(expr, ctx)

    # $TEXT/$T is handled by existing _generate_text
    if func_name in ("TEXT", "T"):
        return _generate_text(expr, ctx)

    raise NotImplementedError(f"Intrinsic function ${expr.name} not yet implemented")


def generate_expr(expr: MExpr, ctx: "GeneratorContext") -> str:
    """Generate Python expression from ASG expression node.

    Dispatches based on expression type:
    - MLiteral → literal value
    - MVariable → translated variable name
    - MBinaryOp → operation with coercion
    - MUnaryOp → unary operation
    - MExtrinsicFunction → function call with $TEST save/restore
    - MIntrinsicFunction → intrinsic function dispatch table

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
    elif isinstance(expr, GlobalVariable):
        return _generate_global_variable(expr, ctx)
    elif isinstance(expr, NakedGlobal):
        return _generate_naked_global_variable(expr, ctx)
    elif isinstance(expr, MBinaryOp):
        return _generate_binary_op(expr, ctx)
    elif isinstance(expr, MUnaryOp):
        return _generate_unary_op(expr, ctx)
    elif isinstance(expr, MExtrinsicFunction):
        return _generate_extrinsic(expr, ctx)
    elif isinstance(expr, MSpecialVariable):
        return _generate_special_variable(expr, ctx)
    # Spec 010: Dispatch all intrinsic functions through unified handler
    # This handles both MIntrinsicFunction ASG nodes and parser textx classes
    # (IntrinsicFunction, TextFunction, SelectFunction) which all inherit
    # from MIntrinsicFunction.
    elif isinstance(expr, MIntrinsicFunction):
        return generate_intrinsic_function(expr, ctx)
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

    Spec 008 (T085): For SIMPLE_FUNCTIONS strategy, read variables from _scope
    dictionary for cross-routine visibility: _scope.get('VAR', '')

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
        elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Spec 009 (T022-T023): Access arrays from _scope using MArray
            # MArray.get(*subscripts) returns "" for undefined (MUMPS semantics)
            base = f"_scope.get({python_name!r}, MArray())"
        else:
            # Plain Python local variable (TRAMPOLINE without state_vars)
            base = python_name

        # Use .get() for reading - returns value or "" if undefined
        return f"{base}.get({', '.join(subscript_exprs)})"

    # Spec 006: Check if variable should be accessed via state (TRAMPOLINE)
    if ctx.strategy == GotoStrategy.TRAMPOLINE and var.name in ctx.state_vars:
        return f"state.{python_name}"

    # Spec 008 (T085): Read variables from _scope for SIMPLE_FUNCTIONS strategy
    # Spec 009 (T022): Use MArray.value to read simple variables (consistency with subscripted)
    # Return empty string for undefined variables (MUMPS semantics via MArray.value)
    if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
        return f"_scope.get({python_name!r}, MArray()).value"

    # Fallback: plain Python variable (TRAMPOLINE without state_vars)
    return python_name


def _generate_global_variable(var: GlobalVariable, ctx: "GeneratorContext") -> str:
    """Generate Python expression for global variable READ.

    Spec 009 (T027): Generate _rt.globals.get() call for global variable reads.

    Args:
        var: GlobalVariable node
        ctx: Generator context

    Returns:
        Python expression string: _rt.globals.get("NAME", (subscripts,)) or ""

    The generated code reads from the global storage backend and returns
    empty string for undefined globals (MUMPS implicit $GET semantics).
    """
    # Get global name (without caret)
    global_name = var.name

    # Generate subscript expressions
    if var.subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]
        # Format as tuple: (sub1, sub2, ...) or (sub1,) for single element
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"(str({subscript_exprs[0]}),)"
        else:
            subscripts_tuple = f"({', '.join(f'str({s})' for s in subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

    # Spec 009 (T028): Return empty string for undefined globals
    # _rt.globals.get() returns None for undefined, convert to ""
    return f"(_rt.globals.get({global_name!r}, {subscripts_tuple}) or '')"


def _generate_naked_global_variable(var: NakedGlobal, ctx: "GeneratorContext") -> str:
    """Generate Python expression for naked global reference READ.

    Spec 009 (T032): Generate resolve_naked + get for naked global reads.

    Args:
        var: NakedGlobal node
        ctx: Generator context

    Returns:
        Python expression string that resolves and reads the naked global:
        (_rt.globals.get(*_rt.globals.resolve_naked((subscripts,))) or '')

    The naked indicator holds (name, base_subscripts) from the last global access.
    resolve_naked() returns (name, base_subscripts + new_subscripts).
    """
    # Generate subscript expressions
    if var.subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]
        # Format as tuple: (sub1, sub2, ...) or (sub1,) for single element
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"(str({subscript_exprs[0]}),)"
        else:
            subscripts_tuple = f"({', '.join(f'str({s})' for s in subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

    # Spec 009 (T028): Return empty string for undefined globals
    # resolve_naked returns (name, subscripts), use * to unpack into get()
    return f"(_rt.globals.get(*_rt.globals.resolve_naked({subscripts_tuple})) or '')"


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
        _call_extrinsic(_rt, LABEL, arg1, arg2)

    Generated pattern (external - Spec 008 Phase 7):
        _call_extrinsic(_rt, ext2.ADD, arg1, arg2, _scope=_scope)

    The _call_extrinsic helper handles save/restore of _test.
    Phase 13 (T081): _rt is passed explicitly as first parameter.

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
        # Phase 13 (T081): Pass _rt as first parameter
        if args:
            return f"_call_extrinsic(_rt, {routine_name}.{func_name}, {args}, _scope=_scope)"
        else:
            return f"_call_extrinsic(_rt, {routine_name}.{func_name}, _scope=_scope)"

    # Internal extrinsic (within same routine)
    # Translate label name to Python function name
    func_name = translate_name(label_name)

    # Generate arguments
    args = _generate_extrinsic_arguments(expr.arguments, ctx)

    # Generate: _call_extrinsic(_rt, FUNC, arg1, arg2)
    # Phase 13 (T081): Pass _rt as first parameter
    if args:
        return f"_call_extrinsic(_rt, {func_name}, {args})"
    else:
        return f"_call_extrinsic(_rt, {func_name})"


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


def _generate_data(expr, ctx: "GeneratorContext") -> str:
    """Generate Python code for $DATA/$D function.

    Spec 009 Phase 8: Generate m_data() or m_data_global() calls based on
    whether the argument is a local or global variable.

    $DATA returns:
    - 0: Undefined, no descendants
    - 1: Defined, no descendants
    - 10: Undefined, has descendants
    - 11: Defined AND has descendants

    Args:
        expr: IntrinsicFunction ASG node with arguments[0] being the variable
        ctx: Generator context

    Returns:
        Python code calling m_data() or m_data_global()

    Examples:
        $D(X) → m_data(_scope.get('X', MArray()), ())
        $D(X(1)) → m_data(_scope.get('X', MArray()), (str(1),))
        $D(^G) → m_data_global(_rt.globals, 'G', ())
        $D(^G(1)) → m_data_global(_rt.globals, 'G', (str(1),))
    """
    from m2py.parser.textx_classes import LocalVariable

    # Get first argument (the variable to check)
    args = getattr(expr, "arguments", [])
    if not args:
        # No argument - return 0 for undefined
        return "0"

    var = args[0]

    # Generate subscript tuple
    subscripts = getattr(var, "subscripts", [])
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"(str({subscript_exprs[0]}),)"
        else:
            subscripts_tuple = f"({', '.join(f'str({s})' for s in subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        # Local variable: m_data(_scope.get('VAR', MArray()), subscripts)
        python_name = translate_name(var_name)
        return f"m_data(_scope.get({python_name!r}, MArray()), {subscripts_tuple})"
    elif isinstance(var, GlobalVariable):
        # Global variable: m_data_global(_rt.globals, 'NAME', subscripts)
        return f"m_data_global(_rt.globals, {var_name!r}, {subscripts_tuple})"
    else:
        # Fallback for any other variable type - treat as local
        python_name = translate_name(var_name)
        return f"m_data(_scope.get({python_name!r}, MArray()), {subscripts_tuple})"


def _gen_order(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ORDER/$O function.

    Spec 010 Phase 2: Generate m_order() or m_order_global() calls based on
    whether the argument is a local or global variable.

    $ORDER returns the next subscript in MUMPS collation order:
    - Negative numbers (most negative first)
    - Zero
    - Positive numbers (ascending)
    - Strings (ASCII/UTF-8 order)

    Args:
        expr: IntrinsicFunction ASG node with:
              arguments[0]: Variable reference (array to traverse)
              arguments[1]: Optional direction (1=forward, -1=reverse)
        ctx: Generator context

    Returns:
        Python code calling m_order() or m_order_global()

    Examples:
        $O(A("")) → m_order(_scope.get('A', MArray()), ("",))
        $O(A(1)) → m_order(_scope.get('A', MArray()), (str(1),))
        $O(A(""),-1) → m_order(_scope.get('A', MArray()), ("",), -1)
        $O(^G("")) → m_order_global(_rt.globals, 'G', ("",))
    """
    from m2py.parser.textx_classes import LocalVariable

    # Get arguments
    args = getattr(expr, "arguments", [])
    if not args:
        # No argument - return empty string
        return '""'

    var = args[0]

    # Get direction argument if present (second argument)
    direction_code = "1"  # Default to forward
    if len(args) >= 2:
        direction_code = generate_expr(args[1], ctx)

    # Generate subscript tuple
    # For $ORDER, subscripts include the starting point for iteration
    subscripts = getattr(var, "subscripts", [])
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"(str({subscript_exprs[0]}),)"
        else:
            subscripts_tuple = f"({', '.join(f'str({s})' for s in subscript_exprs)},)"
    else:
        # If no subscripts, use ("",) to get first key at root level
        subscripts_tuple = '("",)'

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        # Local variable: m_order(_scope.get('VAR', MArray()), subscripts, direction)
        python_name = translate_name(var_name)
        return f"m_order(_scope.get({python_name!r}, MArray()), {subscripts_tuple}, {direction_code})"
    elif isinstance(var, GlobalVariable):
        # Global variable: m_order_global(_rt.globals, 'NAME', subscripts, direction)
        return f"m_order_global(_rt.globals, {var_name!r}, {subscripts_tuple}, {direction_code})"
    else:
        # Fallback for any other variable type - treat as local
        python_name = translate_name(var_name)
        return f"m_order(_scope.get({python_name!r}, MArray()), {subscripts_tuple}, {direction_code})"


def _gen_query(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $QUERY/$Q function.

    Spec 010 Phase 2: Generate m_query() or m_query_global() calls based on
    whether the argument is a local or global variable.

    $QUERY returns the full reference of the next node with a value in
    depth-first traversal order.

    Args:
        expr: IntrinsicFunction ASG node with:
              arguments[0]: Variable reference (starting point for traversal)
        ctx: Generator context

    Returns:
        Python code calling m_query() or m_query_global()

    Examples:
        $Q(A("")) → m_query(_scope.get('A', MArray()), 'A', ("",))
        $Q(A(1,1)) → m_query(_scope.get('A', MArray()), 'A', (str(1), str(1)))
        $Q(^G("")) → m_query_global(_rt.globals, 'G', ("",))
    """
    from m2py.parser.textx_classes import LocalVariable

    # Get arguments
    args = getattr(expr, "arguments", [])
    if not args:
        # No argument - return empty string
        return '""'

    var = args[0]

    # Generate subscript tuple
    subscripts = getattr(var, "subscripts", [])
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"(str({subscript_exprs[0]}),)"
        else:
            subscripts_tuple = f"({', '.join(f'str({s})' for s in subscript_exprs)},)"
    else:
        # If no subscripts, use ("",) to start from beginning
        subscripts_tuple = '("",)'

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        # Local variable: m_query(_scope.get('VAR', MArray()), 'VAR', subscripts)
        python_name = translate_name(var_name)
        return f"m_query(_scope.get({python_name!r}, MArray()), {var_name!r}, {subscripts_tuple})"
    elif isinstance(var, GlobalVariable):
        # Global variable: m_query_global(_rt.globals, 'NAME', subscripts)
        return f"m_query_global(_rt.globals, {var_name!r}, {subscripts_tuple})"
    else:
        # Fallback for any other variable type - treat as local
        python_name = translate_name(var_name)
        return f"m_query(_scope.get({python_name!r}, MArray()), {var_name!r}, {subscripts_tuple})"


def _generate_text(expr, ctx: "GeneratorContext") -> str:
    """Generate Python code for $TEXT/$T function.

    Supports both current routine and external routine patterns:
    - $T(+0) → routine name
    - $T(+N) → Nth line of current routine
    - $T(LABEL) → label line in current routine
    - $T(LABEL+N) → label+offset in current routine
    - $T(+N^ROUTINE) → Nth line of external routine
    - $T(LABEL^ROUTINE) → label line in external routine
    - $T(LABEL+N^ROUTINE) → label+offset in external routine

    Args:
        expr: TextFunction ASG node with line_ref dictionary
        ctx: Generator context

    Returns:
        Python code calling _rt.get_text()
    """
    from m2py.asg.expressions import MLiteral

    # TextFunction stores line reference info in line_ref dict, not arguments
    line_ref = getattr(expr, "line_ref", {})

    # Check if this is an external routine reference
    routine = line_ref.get("routine")
    label = line_ref.get("label")
    offset = line_ref.get("offset")
    offset_sign = line_ref.get("offset_sign", "+")  # Default to + if not specified

    # Build the get_text() call parameters
    params = []

    # Handle offset parameter
    if offset is not None:
        if isinstance(offset, MLiteral):
            # Apply sign to literal value
            offset_val = offset.value if offset_sign == "+" else -offset.value
            params.append(f"offset={offset_val}")
        else:
            # Offset is an expression (variable, etc.)
            offset_code = generate_expr(offset, ctx)
            if offset_sign == "-":
                params.append(f"offset=-({offset_code})")
            else:
                params.append(f"offset={offset_code}")
    elif offset_sign is not None and label is None:
        # Sign without offset value - $T(+) or $T(-) defaults to 0
        # This handles $T(+0) or $T(-0) which both equal 0
        params.append("offset=0")
    elif label is None:
        # No label, no offset - must be $T() which defaults to +0
        params.append("offset=0")
    else:
        # Label with no offset - defaults to 0
        params.append("offset=0")

    # Handle label parameter
    if label is not None:
        params.append(f'label="{label}"')

    # Handle external routine
    if routine is not None:
        # Use __import__() to get module reference inline
        params.append(f"module=__import__('{routine}')")

    return f"_rt.get_text({', '.join(params)})"


# =============================================================================
# Register Intrinsic Function Generators
# =============================================================================
# Registration happens at module load time after all functions are defined.

# Phase 2: $ORDER, $QUERY
INTRINSIC_GENERATORS["O"] = _gen_order
INTRINSIC_GENERATORS["ORDER"] = _gen_order
INTRINSIC_GENERATORS["Q"] = _gen_query
INTRINSIC_GENERATORS["QUERY"] = _gen_query

# Phase 3: $SELECT
# INTRINSIC_GENERATORS["S"] = _gen_select
# INTRINSIC_GENERATORS["SELECT"] = _gen_select

# Phase 5: String functions
# INTRINSIC_GENERATORS["L"] = _gen_length
# INTRINSIC_GENERATORS["LENGTH"] = _gen_length
# INTRINSIC_GENERATORS["P"] = _gen_piece
# INTRINSIC_GENERATORS["PIECE"] = _gen_piece
# ... more to be added


__all__ = ["generate_expr", "generate_intrinsic_function", "INTRINSIC_GENERATORS"]
