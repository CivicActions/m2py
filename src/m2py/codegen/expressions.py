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
    MSelectArg,
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

    Spec 010 (T020): Handle by-reference parameters. When arguments are passed
    by reference (.VAR), the caller's variables are updated when the callee
    modifies them. This is handled by:
    1. Callee returns tuple (value, *byref_outputs) when has by-ref outputs
    2. Caller passes _byref list with variable names for by-ref args
    3. _call_extrinsic helper unpacks and updates caller's scope

    Generated pattern (internal):
        _call_extrinsic(_rt, LABEL, arg1, arg2)
        _call_extrinsic(_rt, LABEL, arg1, arg2, _scope=_scope, _byref=['A', 'B'])

    Generated pattern (external - Spec 008 Phase 7):
        _call_extrinsic(_rt, ext2.ADD, arg1, arg2, _scope=_scope, _byref=['A', 'B'])

    The _call_extrinsic helper handles save/restore of _test and by-ref unpacking.
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

    # Generate arguments and collect by-ref info
    args, byref_names = _generate_extrinsic_arguments_with_byref(expr.arguments, ctx)

    # Build _byref parameter if there are by-ref arguments
    byref_param = ""
    if byref_names:
        # Format: _byref=['A', 'B', None] - None for by-value positions
        byref_list = ", ".join(repr(name) for name in byref_names)
        byref_param = f", _byref=[{byref_list}]"

    # Spec 008 Phase 7 (T043-T046): Handle external routine extrinsic
    if expr.target.routine:
        routine_name = expr.target.routine

        # T044: Generate import statement for external routine
        ctx.emitter.line(f"import {routine_name}")

        # Translate label name to Python function name
        func_name = translate_name(label_name)

        # T045-T046: Generate call via _call_extrinsic with module prefix and _scope
        # The _call_extrinsic helper provides $TEST save/restore and by-ref unpacking
        # Phase 13 (T081): Pass _rt as first parameter
        if args:
            return f"_call_extrinsic(_rt, {routine_name}.{func_name}, {args}, _scope=_scope{byref_param})"
        else:
            return f"_call_extrinsic(_rt, {routine_name}.{func_name}, _scope=_scope{byref_param})"

    # Internal extrinsic (within same routine)
    # Translate label name to Python function name
    func_name = translate_name(label_name)

    # Spec 010 (T020): For internal calls with by-ref, need _scope for by-ref unpacking
    if byref_names:
        if args:
            return (
                f"_call_extrinsic(_rt, {func_name}, {args}, _scope=_scope{byref_param})"
            )
        else:
            return f"_call_extrinsic(_rt, {func_name}, _scope=_scope{byref_param})"

    # Generate: _call_extrinsic(_rt, FUNC, arg1, arg2)
    # Phase 13 (T081): Pass _rt as first parameter
    if args:
        return f"_call_extrinsic(_rt, {func_name}, {args})"
    else:
        return f"_call_extrinsic(_rt, {func_name})"


def _generate_extrinsic_arguments_with_byref(
    arguments: List[MActualParameter], ctx: "GeneratorContext"
) -> tuple[str, list[str | None]]:
    """Generate Python arguments for extrinsic function call with by-ref info.

    Spec 010 (T020): Returns both the argument string and a list of by-ref
    variable names. The by-ref list has the variable name for BY_REFERENCE
    arguments and None for BY_VALUE arguments.

    Args:
        arguments: List of MActualParameter
        ctx: Generator context

    Returns:
        Tuple of (comma-separated argument string, list of by-ref names)
    """
    if not arguments:
        return "", []

    parts = []
    byref_names: list[str | None] = []
    has_byref = False

    for arg in arguments:
        if arg.passing_mode == PassingMode.OMITTED:
            parts.append("None")
            byref_names.append(None)
        elif arg.passing_mode == PassingMode.BY_REFERENCE:
            # By-reference: pass the variable value, record name for unpacking
            has_byref = True
            if arg.variable_name:
                # Spec 009 (T021): Use MArray.value for SIMPLE_FUNCTIONS
                var_name = arg.variable_name
                parts.append(f"_scope.get({var_name!r}, MArray()).value")
                byref_names.append(var_name)
            elif arg.expression:
                # Expression passed by-ref (unusual but possible)
                parts.append(generate_expr(arg.expression, ctx))
                byref_names.append(None)  # Can't write back to expression
            else:
                parts.append("None")
                byref_names.append(None)
        else:  # BY_VALUE
            if arg.expression:
                parts.append(generate_expr(arg.expression, ctx))
            elif arg.variable_name:
                var_name = arg.variable_name
                parts.append(f"_scope.get({var_name!r}, MArray()).value")
            else:
                parts.append("None")
            byref_names.append(None)

    # Only return byref_names if there were actually by-ref arguments
    return ", ".join(parts), byref_names if has_byref else []


def _generate_extrinsic_arguments(
    arguments: List[MActualParameter], ctx: "GeneratorContext"
) -> str:
    """Generate Python arguments for extrinsic function call.

    Note: This is the legacy version that doesn't handle by-ref.
    Use _generate_extrinsic_arguments_with_byref for full by-ref support.

    Args:
        arguments: List of MActualParameter
        ctx: Generator context

    Returns:
        Comma-separated argument string
    """
    args, _ = _generate_extrinsic_arguments_with_byref(arguments, ctx)
    return args


def _gen_data(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $DATA/$D function.

    Spec 009 Phase 8, Spec 010 Phase 6: Generate m_data() or m_data_global()
    calls based on whether the argument is a local or global variable.

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


def _gen_get(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $GET/$G function.

    Spec 010 Phase 6 (T040): Generate m_get() or m_get_global() calls based on
    whether the argument is a local or global variable.

    $GET returns the variable's value if defined, otherwise the default value.
    It distinguishes between undefined and defined-as-empty-string.

    Args:
        expr: MIntrinsicFunction ASG node with 1-2 arguments:
              - arg[0]: variable to retrieve
              - arg[1]: optional default value (defaults to "")
        ctx: Generator context

    Returns:
        Python code calling m_get() or m_get_global()

    Examples:
        $G(X) → m_get(_scope.get('X', None), (), "")
        $G(X,"DEF") → m_get(_scope.get('X', None), (), "DEF")
        $G(X(1)) → m_get(_scope.get('X', None), (str(1),), "")
        $G(^G) → m_get_global(_rt.globals, 'G', (), "")
        $G(^G(1),"DEF") → m_get_global(_rt.globals, 'G', (str(1),), "DEF")
    """
    from m2py.parser.textx_classes import LocalVariable

    # Get arguments
    args = getattr(expr, "arguments", [])
    if not args:
        # No argument - return empty string
        return '""'

    var = args[0]

    # Get default value if provided
    if len(args) >= 2:
        default_expr = generate_expr(args[1], ctx)
        default_code = f"str({default_expr})"
    else:
        default_code = '""'

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
        # Local variable: m_get(_scope.get('VAR', None), subscripts, default)
        python_name = translate_name(var_name)
        return f"m_get(_scope.get({python_name!r}), {subscripts_tuple}, {default_code})"
    elif isinstance(var, GlobalVariable):
        # Global variable: m_get_global(_rt.globals, 'NAME', subscripts, default)
        return f"m_get_global(_rt.globals, {var_name!r}, {subscripts_tuple}, {default_code})"
    else:
        # Fallback for any other variable type - treat as local
        python_name = translate_name(var_name)
        return f"m_get(_scope.get({python_name!r}), {subscripts_tuple}, {default_code})"


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


def _gen_select(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $SELECT/$S function.

    Spec 010 Phase 3: Generate chained conditional expression that evaluates
    condition:value pairs left-to-right, returning the value for the first
    true condition. If no condition is true, raises MRuntimeError("SELECTFALSE").

    $SELECT(cond1:val1, cond2:val2, ..., 1:default) evaluates conditions
    left-to-right and returns the value associated with the first true condition.

    Args:
        expr: IntrinsicFunction ASG node with arguments as list of MSelectArg
        ctx: Generator context

    Returns:
        Python chained conditional expression with SELECTFALSE fallback

    Examples:
        $S(1=1:"YES",1:"NO") →
            ("YES" if m_truth((1 == 1)) else "NO" if m_truth(1) else _raise_select_false())

        $S(X=1:"ONE",X=2:"TWO",1:"OTHER") →
            ("ONE" if m_truth((X == 1)) else "TWO" if m_truth((X == 2)) else
             "OTHER" if m_truth(1) else _raise_select_false())
    """
    from m2py.runtime.exceptions import MRuntimeError  # noqa: F401 - for docstring

    args = getattr(expr, "arguments", [])
    if not args:
        # Empty $SELECT - error
        return "_raise_select_false()"

    # Build the chained conditional expression
    # Each MSelectArg has condition and value
    parts = []
    for arg in args:
        if not isinstance(arg, MSelectArg):
            # Skip non-MSelectArg arguments (shouldn't happen but defensive)
            continue

        # Generate condition and value expressions
        if arg.condition is not None:
            cond_expr = generate_expr(arg.condition, ctx)
        else:
            # No condition - treat as always false (shouldn't happen)
            cond_expr = "0"

        if arg.value is not None:
            val_expr = generate_expr(arg.value, ctx)
        else:
            # No value - use empty string
            val_expr = '""'

        parts.append((cond_expr, val_expr))

    if not parts:
        # No valid parts - error
        return "_raise_select_false()"

    # Build chained conditional: (val1 if m_truth(cond1) else val2 if m_truth(cond2) else ... else _raise_select_false())
    # We need to build from the inside out, starting with the fallback
    result = "_raise_select_false()"

    # Build backwards from the last condition
    for cond_expr, val_expr in reversed(parts):
        result = f"({val_expr} if m_truth({cond_expr}) else {result})"

    return result


# =============================================================================
# Phase 5: String Functions ($LENGTH, $PIECE, $EXTRACT)
# =============================================================================


def _gen_length(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $LENGTH/$L function.

    Spec 010 Phase 5 (T024-T026): $LENGTH has two forms:
    1. $L(string) - returns character count (len())
    2. $L(string, delimiter) - returns piece count (count + 1)

    Args:
        expr: MIntrinsicFunction ASG node with 1 or 2 arguments
        ctx: Generator context

    Returns:
        Python expression for length or piece count

    Examples:
        $L("HELLO") → len("HELLO")
        $L("A^B^C","^") → (str("A^B^C").count("^") + 1)
        $L("","^") → 1 (empty string has 1 piece)
    """
    args = getattr(expr, "arguments", [])

    if not args:
        # No arguments - return 0 (edge case)
        return "0"

    # First argument is the string
    string_expr = generate_expr(args[0], ctx)

    if len(args) == 1:
        # Single argument - character count
        return f"len(str({string_expr}))"
    else:
        # Two arguments - piece count
        # Piece count = delimiter occurrences + 1
        delimiter_expr = generate_expr(args[1], ctx)
        return f"(str({string_expr}).count(str({delimiter_expr})) + 1)"


def _gen_piece(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $PIECE/$P function.

    Spec 010 Phase 5 (T027-T030): $PIECE extracts delimited pieces.
    $P(string, delimiter, from [, to])

    Args:
        expr: MIntrinsicFunction ASG node with 2-4 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_piece() helper

    Examples:
        $P("A^B^C","^",2) → m_piece("A^B^C", "^", 2)
        $P("A^B^C","^",2,3) → m_piece("A^B^C", "^", 2, 3)
    """
    args = getattr(expr, "arguments", [])

    if len(args) < 3:
        # Not enough arguments - return empty string
        return '""'

    string_expr = generate_expr(args[0], ctx)
    delimiter_expr = generate_expr(args[1], ctx)
    from_expr = generate_expr(args[2], ctx)

    if len(args) >= 4:
        to_expr = generate_expr(args[3], ctx)
        return f"m_piece(str({string_expr}), str({delimiter_expr}), int(m_num({from_expr})), int(m_num({to_expr})))"
    else:
        return f"m_piece(str({string_expr}), str({delimiter_expr}), int(m_num({from_expr})))"


def _gen_extract(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $EXTRACT/$E function.

    Spec 010 Phase 5 (T031-T034): $EXTRACT extracts substrings by position.
    $E(string [, from [, to]])

    MUMPS uses 1-based indexing. Default from=1, default to=from.

    Args:
        expr: MIntrinsicFunction ASG node with 1-3 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_extract() helper

    Examples:
        $E("HELLO") → m_extract("HELLO", 1, 1)
        $E("HELLO",2) → m_extract("HELLO", 2, 2)
        $E("HELLO",2,4) → m_extract("HELLO", 2, 4)
    """
    args = getattr(expr, "arguments", [])

    if not args:
        # No arguments - return empty string
        return '""'

    string_expr = generate_expr(args[0], ctx)

    if len(args) == 1:
        # $E(string) - default to first character
        return f"m_extract(str({string_expr}), 1, 1)"
    elif len(args) == 2:
        # $E(string, from) - single character at position from
        from_expr = generate_expr(args[1], ctx)
        return f"m_extract(str({string_expr}), int(m_num({from_expr})), int(m_num({from_expr})))"
    else:
        # $E(string, from, to) - substring
        from_expr = generate_expr(args[1], ctx)
        to_expr = generate_expr(args[2], ctx)
        return f"m_extract(str({string_expr}), int(m_num({from_expr})), int(m_num({to_expr})))"


def _gen_find(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $FIND/$F function.

    Spec 010 Phase 7 (T044): $FIND locates substring and returns position
    AFTER the match. $F(string, target [, start])

    Returns 0 if not found, or position AFTER the match (1-indexed).

    Args:
        expr: MIntrinsicFunction ASG node with 2-3 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_find() helper

    Examples:
        $F("HELLO","LL") → m_find("HELLO", "LL", 1) → 5
        $F("HELLO","L",4) → m_find("HELLO", "L", 4) → 5
    """
    args = getattr(expr, "arguments", [])

    if len(args) < 2:
        # Not enough arguments - return 0
        return "0"

    string_expr = generate_expr(args[0], ctx)
    target_expr = generate_expr(args[1], ctx)

    if len(args) >= 3:
        start_expr = generate_expr(args[2], ctx)
        return (
            f"m_find(str({string_expr}), str({target_expr}), int(m_num({start_expr})))"
        )
    else:
        return f"m_find(str({string_expr}), str({target_expr}), 1)"


def _gen_translate(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $TRANSLATE/$TR function.

    Spec 010 Phase 7 (T047): $TRANSLATE performs character-by-character
    replacement or deletion. $TR(string, from [, to])

    Characters in 'from' are replaced by corresponding characters in 'to'.
    If 'to' is shorter than 'from', extra characters in 'from' are deleted.
    If 'to' is omitted, all characters in 'from' are deleted.

    Args:
        expr: MIntrinsicFunction ASG node with 2-3 arguments
        ctx: Generator context

    Returns:
        Python expression using str.translate() with str.maketrans()

    Examples:
        $TR("HELLO","L") → "HEO" (delete all L's)
        $TR("HELLO","LO","XY") → "HEXXY" (L→X, O→Y)
        $TR("HELLO","HEL","ABC") → "ABCCO" (H→A, E→B, L→C)
    """
    args = getattr(expr, "arguments", [])

    if len(args) < 2:
        # Not enough arguments - return original string
        if args:
            return f"str({generate_expr(args[0], ctx)})"
        return '""'

    string_expr = generate_expr(args[0], ctx)
    from_expr = generate_expr(args[1], ctx)

    if len(args) >= 3:
        to_expr = generate_expr(args[2], ctx)
        # Build translation table with replacement
        return f"str({string_expr}).translate(str.maketrans(str({from_expr}), str({to_expr}).ljust(len(str({from_expr})), chr(0)), ''.join(chr(0) if i < len(str({to_expr})) else c for i, c in enumerate(str({from_expr})))))"
    else:
        # No 'to' argument - delete all characters in 'from'
        return f"str({string_expr}).translate(str.maketrans('', '', str({from_expr})))"


def _gen_ascii(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ASCII/$A function.

    Spec 010 Phase 7 (T050): $ASCII returns ASCII code of character.
    $A(string [, position])

    Returns -1 if position is out of range or string is empty.

    Args:
        expr: MIntrinsicFunction ASG node with 1-2 arguments
        ctx: Generator context

    Returns:
        Python expression using ord() with bounds checking

    Examples:
        $A("ABC") → 65 (A)
        $A("ABC",2) → 66 (B)
        $A("ABC",4) → -1 (out of range)
        $A("") → -1 (empty string)
    """
    args = getattr(expr, "arguments", [])

    if not args:
        return "-1"

    string_expr = generate_expr(args[0], ctx)

    if len(args) >= 2:
        pos_expr = generate_expr(args[1], ctx)
        # 1-indexed position, -1 if out of range
        return f"(ord(str({string_expr})[int(m_num({pos_expr}))-1]) if 0 < int(m_num({pos_expr})) <= len(str({string_expr})) else -1)"
    else:
        # Default position 1 (first character)
        return f"(ord(str({string_expr})[0]) if str({string_expr}) else -1)"


def _gen_char(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $CHAR/$C function.

    Spec 010 Phase 7 (T051): $CHAR converts ASCII codes to characters.
    $C(code1 [, code2, ...])

    Multiple arguments produce concatenated characters.
    Negative codes produce empty string (per YottaDB behavior).

    Args:
        expr: MIntrinsicFunction ASG node with 1+ arguments
        ctx: Generator context

    Returns:
        Python expression using chr() for each argument

    Examples:
        $C(65) → "A"
        $C(65,66,67) → "ABC"
        $C(-1) → "" (empty for negative)
        $C(256) → "Ā" (Unicode)
    """
    args = getattr(expr, "arguments", [])

    if not args:
        return '""'

    # Generate chr() for each argument, with negative check
    parts = []
    for arg in args:
        arg_expr = generate_expr(arg, ctx)
        # chr() for non-negative, empty string for negative
        parts.append(
            f"(chr(int(m_num({arg_expr}))) if int(m_num({arg_expr})) >= 0 else '')"
        )

    if len(parts) == 1:
        return parts[0]
    else:
        return "(" + " + ".join(parts) + ")"


def _gen_random(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $RANDOM/$R function.

    Spec 010 Phase 8 (T055): $RANDOM generates random integers from 0 to limit-1.
    $R(limit) returns a random integer in range [0, limit-1].

    Raises MRuntimeError("RANDARGNEG") if limit <= 0.

    Args:
        expr: MIntrinsicFunction ASG node with 1 argument
        ctx: Generator context

    Returns:
        Python expression using random.randint() with error check

    Examples:
        $R(10) → random int 0-9
        $R(1) → always 0
        $R(0) → raises RANDARGNEG
    """
    args = getattr(expr, "arguments", [])

    if not args:
        # No argument - raise error
        return "_m_random_checked(0)"

    limit_expr = generate_expr(args[0], ctx)
    return f"_m_random_checked(int(m_num({limit_expr})))"


def _m_random_checked(limit: int) -> int:
    """Generate random integer with RANDARGNEG check.

    Helper function called by generated code for $RANDOM.
    Must be imported into generated code.

    Args:
        limit: Upper bound (exclusive), must be >= 1

    Returns:
        Random integer from 0 to limit-1

    Raises:
        MRuntimeError: If limit <= 0
    """
    import random

    from m2py.runtime.exceptions import MRuntimeError

    if limit <= 0:
        raise MRuntimeError(
            "RANDARGNEG",
            "Random number generator argument must be greater than or equal to one",
        )
    return random.randint(0, limit - 1)


def _gen_name(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $NAME/$NA function.

    Spec 010 Phase 9 (T062): $NAME converts a variable reference to a canonical
    name string representation.

    $NAME(varref [, depth]) returns the canonical name of the variable:
    - depth omitted or > subscript count: all subscripts
    - depth = 0: variable name only
    - depth = n: first n subscripts

    Args:
        expr: MIntrinsicFunction ASG node with 1-2 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_name() helper

    Examples:
        $NA(A(1,2,3)) → m_name("A", ("1", "2", "3"))
        $NA(A(1,2,3),2) → m_name("A", ("1", "2", "3"), depth=2)
        $NA(^GLO(1,2)) → m_name("GLO", ("1", "2"), is_global=True)
    """

    args = getattr(expr, "arguments", [])
    if not args:
        return '""'

    var = args[0]
    var_name = getattr(var, "name", "")
    subscripts = getattr(var, "subscripts", [])

    # Build subscripts tuple - evaluate at runtime
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"(str({subscript_exprs[0]}),)"
        else:
            subscripts_tuple = f"({', '.join(f'str({s})' for s in subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

    # Get depth argument if present
    depth_arg = ""
    if len(args) >= 2:
        depth_expr = generate_expr(args[1], ctx)
        depth_arg = f", depth=int(m_num({depth_expr}))"

    # Check if it's a global variable
    if isinstance(var, GlobalVariable):
        return f"m_name({var_name!r}, {subscripts_tuple}{depth_arg}, is_global=True)"
    else:
        return f"m_name({var_name!r}, {subscripts_tuple}{depth_arg})"


def _gen_qlength(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $QLENGTH/$QL function.

    Spec 010 Phase 9 (T063): $QLENGTH counts subscripts in a name string.

    $QLENGTH(name) returns the number of subscripts in the name string.

    Args:
        expr: MIntrinsicFunction ASG node with 1 argument
        ctx: Generator context

    Returns:
        Python expression calling m_qlength() helper

    Examples:
        $QL("A") → 0
        $QL("A(1,2,3)") → 3
    """
    args = getattr(expr, "arguments", [])
    if not args:
        return "0"

    name_expr = generate_expr(args[0], ctx)
    return f"m_qlength(str({name_expr}))"


def _gen_qsubscript(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $QSUBSCRIPT/$QS function.

    Spec 010 Phase 9 (T064): $QSUBSCRIPT extracts a subscript from a name string.

    $QSUBSCRIPT(name, position) returns:
    - position=0: variable name (with ^ for globals)
    - position>0: subscript at that position (1-indexed)
    - position<0 or out of range: empty string

    Args:
        expr: MIntrinsicFunction ASG node with 2 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_qsubscript() helper

    Examples:
        $QS("A(1,2,3)",0) → "A"
        $QS("A(1,2,3)",2) → "2"
    """
    args = getattr(expr, "arguments", [])
    if len(args) < 2:
        return '""'

    name_expr = generate_expr(args[0], ctx)
    pos_expr = generate_expr(args[1], ctx)
    return f"m_qsubscript(str({name_expr}), int(m_num({pos_expr})))"


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
INTRINSIC_GENERATORS["S"] = _gen_select
INTRINSIC_GENERATORS["SELECT"] = _gen_select

# Phase 5: String functions ($LENGTH, $PIECE, $EXTRACT)
INTRINSIC_GENERATORS["L"] = _gen_length
INTRINSIC_GENERATORS["LENGTH"] = _gen_length
INTRINSIC_GENERATORS["P"] = _gen_piece
INTRINSIC_GENERATORS["PIECE"] = _gen_piece
INTRINSIC_GENERATORS["E"] = _gen_extract
INTRINSIC_GENERATORS["EXTRACT"] = _gen_extract

# Phase 6: Data functions ($DATA, $GET)
INTRINSIC_GENERATORS["D"] = _gen_data
INTRINSIC_GENERATORS["DATA"] = _gen_data
INTRINSIC_GENERATORS["G"] = _gen_get
INTRINSIC_GENERATORS["GET"] = _gen_get

# Phase 7: String search and transform functions ($FIND, $TRANSLATE, $ASCII, $CHAR)
INTRINSIC_GENERATORS["F"] = _gen_find
INTRINSIC_GENERATORS["FIND"] = _gen_find
INTRINSIC_GENERATORS["TR"] = _gen_translate
INTRINSIC_GENERATORS["TRANSLATE"] = _gen_translate
INTRINSIC_GENERATORS["A"] = _gen_ascii
INTRINSIC_GENERATORS["ASCII"] = _gen_ascii
INTRINSIC_GENERATORS["C"] = _gen_char
INTRINSIC_GENERATORS["CHAR"] = _gen_char

# Phase 8: Numeric functions ($RANDOM)
INTRINSIC_GENERATORS["R"] = _gen_random
INTRINSIC_GENERATORS["RANDOM"] = _gen_random

# Phase 9: Array utility functions ($NAME, $QLENGTH, $QSUBSCRIPT)
INTRINSIC_GENERATORS["NA"] = _gen_name
INTRINSIC_GENERATORS["NAME"] = _gen_name
INTRINSIC_GENERATORS["QL"] = _gen_qlength
INTRINSIC_GENERATORS["QLENGTH"] = _gen_qlength
INTRINSIC_GENERATORS["QS"] = _gen_qsubscript
INTRINSIC_GENERATORS["QSUBSCRIPT"] = _gen_qsubscript


__all__ = [
    "generate_expr",
    "generate_intrinsic_function",
    "INTRINSIC_GENERATORS",
    "_m_random_checked",
]
