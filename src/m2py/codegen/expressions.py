"""Expression code generation for MUMPS-to-Python transpilation.

Generates Python expression strings from MUMPS ASG expression nodes.
Handles literals, variables, binary operations, unary operations,
extrinsic functions, and intrinsic function dispatch ($LENGTH, $PIECE, etc.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, List

from m2py.asg.enums import LiteralType, PassingMode
from m2py.asg.expressions import (
    MActualParameter,
    MBinaryOp,
    MExpr,
    MExternalFunction,
    MExtrinsicFunction,
    MGlobal,
    MIndirection,
    MIntrinsicFunction,
    MLiteral,
    MPatternMatch,
    MSpecialVariable,
    MStructuredSystemVariable,
    MUnaryOp,
    MVariable,
)
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.names import translate_name
from m2py.codegen.var_access import var_base_expr, scope_dict_expr
from m2py.parser.textx_classes import (
    ExtendedGlobalBracket,
    ExtendedGlobalPipe,
    GlobalVariable,
    NakedGlobal,
)


def gen_subscripts_tuple(
    subscripts: list,
    ctx: "GeneratorContext",
    *,
    subscript_context: bool = False,
    str_wrap: bool = False,
    empty: str = "()",
) -> str:
    """Thin wrapper that defers to m2py.codegen.statements.gen_subscripts_tuple.

    Avoids circular import (statements imports expressions at module level).
    """
    from m2py.codegen.statements import (
        gen_subscripts_tuple as _gen_subscripts_tuple,
    )

    return _gen_subscripts_tuple(
        subscripts,
        ctx,
        subscript_context=subscript_context,
        str_wrap=str_wrap,
        empty=empty,
    )


if TYPE_CHECKING:
    from m2py.codegen.routine import GeneratorContext


# =============================================================================
# Limitation Constants
# =============================================================================

# ANSI Standard Library routines (LIM-014)
# STRING and CHARACTER libraries have zero VistA usage - all functions blocked.
# MATH library has basic functions implemented; others blocked.
ANSI_LIBRARY_ROUTINES_BLOCKED: frozenset[str] = frozenset({"STRING", "CHARACTER"})

# Implemented MATH library functions (defined in m2py/runtime/routines/MATH.py)
MATH_FUNCTIONS_IMPLEMENTED: frozenset[str] = frozenset(
    {
        "%EXP",
        "%LOG",
        "%LN",
        "%SQRT",
        "%SIN",
        "%COS",
        "%TAN",
        "%ARCSIN",
        "%ASIN",
        "%ARCCOS",
        "%ACOS",
        "%ARCTAN",
        "%ATAN",
    }
)

# YDB Z-functions with zero VistA usage (LIM-015)
# These are implementation-defined and parsed but not implemented.
# Codegen raises NotImplementedError for these functions.
Z_FUNCTIONS_UNIMPLEMENTED: frozenset[str] = frozenset({"ZWIDTH"})


# =============================================================================
# Intrinsic Function Dispatch Table
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

    Dispatches to function-specific generators based on the function name
    using the INTRINSIC_GENERATORS dispatch table.

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

    # LIM-015: Unimplemented Z-functions
    if func_name in Z_FUNCTIONS_UNIMPLEMENTED:
        raise NotImplementedError(f"LIM-015: ${expr.name} function not supported")

    raise NotImplementedError(f"Intrinsic function ${expr.name} not yet implemented")


def generate_expr(
    expr: MExpr,
    ctx: "GeneratorContext",
    if_condition: bool = False,
    subscript_context: bool = False,
) -> str:
    """Generate Python expression from ASG expression node.

    Dispatches based on expression type:
    - MLiteral → literal value
    - MVariable → translated variable name
    - MBinaryOp → operation with coercion
    - MUnaryOp → unary operation
    - MExtrinsicFunction → function call with $TEST save/restore
    - MIntrinsicFunction → intrinsic function dispatch table
    - MIndirection → runtime indirection call

    Args:
        expr: ASG expression node
        ctx: Generator context (for name translation, etc.)
        if_condition: If True, this expression is an IF condition, which
                     affects how argument indirection handles empty strings
        subscript_context: If True, this expression is in a subscript position.
                     Affects indirection: @VAR returns VALUE (for use as subscript)
                     instead of resolving to NAME

    Returns:
        Python expression string

    Raises:
        NotImplementedError: For unsupported expression types
    """
    if isinstance(expr, MLiteral):
        return _generate_literal(expr)
    elif isinstance(expr, MVariable):
        return _generate_variable(expr, ctx)
    # Check MGlobal before GlobalVariable since GlobalVariable inherits from MGlobal
    # and MGlobal can appear directly in some contexts (e.g., GOTO offsets)
    elif isinstance(expr, MGlobal):
        return _generate_global_variable(expr, ctx)
    elif isinstance(expr, NakedGlobal):
        return _generate_naked_global_variable(expr, ctx)
    elif isinstance(expr, MBinaryOp):
        return _generate_binary_op(expr, ctx)
    elif isinstance(expr, MUnaryOp):
        return _generate_unary_op(expr, ctx)
    elif isinstance(expr, MExtrinsicFunction):
        return _generate_extrinsic(expr, ctx)
    # External C functions ($&name, $&package.name)
    elif isinstance(expr, MExternalFunction):
        return _generate_external_function(expr, ctx)
    elif isinstance(expr, MSpecialVariable):
        return _generate_special_variable(expr, ctx)
    # Dispatch all intrinsic functions through unified handler.
    # This handles both MIntrinsicFunction ASG nodes and parser textx classes
    # (IntrinsicFunction, TextFunction, SelectFunction) which all inherit
    # from MIntrinsicFunction.
    elif isinstance(expr, MIntrinsicFunction):
        return generate_intrinsic_function(expr, ctx)
    # Pattern match expressions
    elif isinstance(expr, MPatternMatch):
        return _generate_pattern_match(expr, ctx)
    # Name indirection (@VAR)
    # subscript_context generates VALUE instead of NAME resolution
    elif isinstance(expr, MIndirection):
        return _generate_indirection(
            expr, ctx, if_condition=if_condition, subscript_context=subscript_context
        )
    # Structured system variables (^$GLOBAL, ^$JOB, etc.)
    elif isinstance(expr, MStructuredSystemVariable):
        return _generate_ssvn(expr, ctx)
    else:
        # Defensive handlers for textX parser nodes that should have been
        # unwrapped by the semantic analyzer but survived into codegen.
        # These are dynamically-typed textX classes, not MExpr subclasses,
        # so we cast to Any to access their attributes without type errors.
        expr_type = type(expr).__name__
        textx_node: Any = expr  # type: ignore[assignment]
        if expr_type == "ParenExpr":
            # ParenExpr wraps (expr) — unwrap and recurse
            return generate_expr(
                textx_node.expr,
                ctx,
                if_condition=if_condition,
                subscript_context=subscript_context,
            )
        elif expr_type in ("UnaryPrefixedExpr", "UnaryExpr"):
            # UnaryPrefixedExpr / UnaryExpr: has operators list + operand
            # Build MUnaryOp chain from operators and operand
            inner = generate_expr(
                textx_node.operand,
                ctx,
                if_condition=if_condition,
                subscript_context=subscript_context,
            )
            # Apply operators right-to-left (innermost first)
            # Operators may be raw strings or UnaryOp objects with .op attribute
            for op_item in reversed(textx_node.operators):
                op = op_item.op if hasattr(op_item, "op") else str(op_item)
                if op == "'":
                    inner = f"int(not m_truth({inner}))"
                elif op == "-":
                    inner = f"m_sub(0, {inner})"
                elif op == "+":
                    inner = f"m_num({inner})"
                else:
                    raise NotImplementedError(f"Unsupported unary operator: {op}")
            return inner
        elif expr_type == "OffsetParenExpr":
            # OffsetParenExpr: same as ParenExpr but in offset context
            return generate_expr(
                textx_node.expr,
                ctx,
                if_condition=if_condition,
                subscript_context=subscript_context,
            )
        elif expr_type == "Expr":
            # Expr: grammar base rule with left=UnaryExpr and tail=ExprTail*
            # When no tail, just delegate to left. With tail, run through analyzer.
            if not (hasattr(textx_node, "tail") and textx_node.tail):
                return generate_expr(
                    textx_node.left,
                    ctx,
                    if_condition=if_condition,
                    subscript_context=subscript_context,
                )
            # Has tail — run through semantic analyzer to build proper ASG nodes
            from m2py.analysis.semantic_analyzer import analyze_expression

            analyzed = analyze_expression(textx_node)
            return generate_expr(
                analyzed,
                ctx,
                if_condition=if_condition,
                subscript_context=subscript_context,
            )
        elif expr_type == "OffsetExpr":
            # OffsetExpr: offset version of Expr (same structure: left + tail)
            if not (hasattr(textx_node, "tail") and textx_node.tail):
                return generate_expr(
                    textx_node.left,
                    ctx,
                    if_condition=if_condition,
                    subscript_context=subscript_context,
                )
            from m2py.analysis.semantic_analyzer import analyze_expression

            analyzed = analyze_expression(textx_node)
            return generate_expr(
                analyzed,
                ctx,
                if_condition=if_condition,
                subscript_context=subscript_context,
            )
        elif expr_type == "OffsetUnaryExpr":
            # OffsetUnaryExpr: offset version of UnaryExpr (operators + operand)
            inner = generate_expr(
                textx_node.operand,
                ctx,
                if_condition=if_condition,
                subscript_context=subscript_context,
            )
            for op_item in reversed(getattr(textx_node, "operators", [])):
                op = op_item.op if hasattr(op_item, "op") else str(op_item)
                if op == "'":
                    inner = f"int(not m_truth({inner}))"
                elif op == "-":
                    inner = f"m_sub(0, {inner})"
                elif op == "+":
                    inner = f"m_num({inner})"
                else:
                    raise NotImplementedError(f"Unsupported unary operator: {op}")
            return inner
        raise NotImplementedError(f"Unsupported expression type: {expr_type}")


def contains_naked_global(expr: MExpr) -> bool:
    """Check if expression contains any naked global references.

    Delegates to analysis.variables.contains_naked_global which handles
    the recursive traversal and caches results as ASG annotations.
    """
    from m2py.analysis.variables import (
        contains_naked_global as _contains_naked_global,
    )

    return _contains_naked_global(expr)


def _generate_literal(lit: MLiteral) -> str:
    """Generate Python literal from MLiteral.

    For decimal numbers, we generate a Decimal representation to preserve
    precision. This is critical for:
    - Large numbers that exceed float64 precision
    - High-precision decimal literals (e.g., 1.00000000111111111)
    - String operations like concatenation and the follows operator

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
        # Check if literal has stored original string (for precise numbers)
        original = getattr(lit, "_original_string", None)
        if original:
            # Use Decimal for exact precision - this avoids float precision loss
            # for numbers like 1.00000000111111111 or 9999997799E14
            return f'Decimal("{original}")'
        # Fallback: use the already-parsed value (may have lost precision)
        return str(lit.value)
    else:
        return str(lit.value)


def _generate_variable(var: MVariable, ctx: "GeneratorContext") -> str:
    """Generate Python variable reference from MVariable.

    Variable access depends on code generation strategy:
    - TRAMPOLINE with state_vars: access via `state.VAR`
    - TRAMPOLINE with dynamic locals (argumentless KILL/NEW): access via
      `state._locals` dict for dynamic variable resolution
    - TRAMPOLINE with subscripted arrays: access via `state.A.get(subscripts)`
    - SIMPLE_FUNCTIONS: read from `_scope` dict for cross-routine visibility
    - Fallback: plain Python variable name

    Args:
        var: MVariable node
        ctx: Generator context

    Returns:
        Python expression string for the variable reference
    """
    # Translate name to valid Python identifier
    python_name = translate_name(var.name)

    # Dynamic locals for argumentless KILL/NEW support
    if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
        if var.subscripts:
            # Generate subscript expressions
            # subscript_context=True so indirection in subscripts
            # returns VALUE instead of validating as NAME
            subscript_exprs = [
                generate_expr(sub, ctx, subscript_context=True)
                for sub in var.subscripts
            ]
            # Access MArray from _locals dict, default to empty MArray
            base = f"state._locals.get({python_name!r}, MArray())"
            return f"{base}.get({', '.join(subscript_exprs)})"
        else:
            # Simple variable - get value from _locals dict.
            # state._locals may contain MArray objects (from SET) or plain values
            # (from external TRAMPOLINE routine returns), so m_var_value
            # handles both cases uniformly.
            return f"m_var_value(state._locals[{python_name!r}])"

    # Handle subscripted array access
    if var.subscripts:
        # Generate subscript expressions
        # subscript_context=True so indirection in subscripts
        # returns VALUE instead of validating as NAME
        subscript_exprs = [
            generate_expr(sub, ctx, subscript_context=True) for sub in var.subscripts
        ]

        # Determine base variable access
        if ctx.strategy == GotoStrategy.TRAMPOLINE and var.name in ctx.array_vars:
            if ctx.uses_dynamic_locals:
                # Dynamic locals: arrays are in state._locals dict
                base = f"state._locals.get({python_name!r}, MArray())"
            else:
                # MArray in RoutineState: state.A.get(subscripts)
                base = f"state.{python_name}"
        elif (
            ctx.strategy == GotoStrategy.TRAMPOLINE and var.name in ctx.input_only_vars
        ):
            # Input-only vars come from caller's scope, not RoutineState
            base = f"_scope.get({python_name!r}, MArray())"
        elif ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
            # Access arrays from _scope using MArray.
            # MArray.get(*subscripts) returns "" for undefined (MUMPS semantics).
            # Uses python_name (translated) to match SET statement key format.
            base = f"_scope.get({python_name!r}, MArray())"
        else:
            # TRAMPOLINE var not in state_vars — read from _scope for
            # consistency with SET which stores there
            base = f"_scope.get({python_name!r}, MArray())"

        # Use .get() for reading - returns value or "" if undefined
        return f"{base}.get({', '.join(subscript_exprs)})"

    # Check if variable should be accessed via state (TRAMPOLINE)
    if ctx.strategy == GotoStrategy.TRAMPOLINE and var.name in ctx.state_vars:
        return f"state.{python_name}"

    # Read variables from _scope for SIMPLE_FUNCTIONS strategy.
    # Uses m_var_value to handle both MArray and plain values (external
    # TRAMPOLINE routines may return plain strings in _scope).
    # Uses python_name (translated) to match SET statement key format.
    if ctx.strategy == GotoStrategy.SIMPLE_FUNCTIONS:
        return f"m_var_value(_scope[{python_name!r}])"

    # TRAMPOLINE var not in state_vars (including input-only vars from caller's
    # scope) — read from _scope for consistency with SET which stores there
    return f"m_var_value(_scope[{python_name!r}])"


def _generate_global_variable(var: MGlobal, ctx: "GeneratorContext") -> str:
    """Generate Python expression for global variable READ.

    Generates _rt.globals.get() calls for global variable reads.

    Args:
        var: MGlobal or GlobalVariable node (GlobalVariable inherits from MGlobal)
        ctx: Generator context

    Returns:
        Python expression string: _rt.globals.get("NAME", (subscripts,)) or ""

    The generated code reads from the global storage backend and returns
    empty string for undefined globals (MUMPS implicit $GET semantics).

    Extended globals (^|env| or ^[gld]) use namespace-aware get_ns() calls.
    """
    # Get global name (without caret)
    global_name = var.name

    # Generate subscript expressions
    # DO NOT wrap in str() - let the runtime's _canonicalize_subscript handle
    # the type distinction. Numeric literals (Decimal, int, float) should
    # canonicalize differently than string literals.
    # Example: Decimal("1.0") → "1" (numeric), but "1.0" → "1.0" (string)
    # subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    subscripts_tuple = gen_subscripts_tuple(
        var.subscripts or [], ctx, subscript_context=True
    )

    # Handle extended global references with namespace
    if isinstance(var, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
        ns = getattr(var.environment, "value", "") if var.environment else ""
        return (
            f"(_rt.globals.get_ns({global_name!r}, {subscripts_tuple}, "
            f"namespace={ns!r}) or '')"
        )

    # Return empty string for undefined globals
    # _rt.globals.get() returns None for undefined, convert to ""
    return f"(_rt.globals.get({global_name!r}, {subscripts_tuple}) or '')"


def _generate_naked_global_variable(var: NakedGlobal, ctx: "GeneratorContext") -> str:
    """Generate Python expression for naked global reference READ.

    Generates resolve_naked + get calls for naked global reads.

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
    # DO NOT wrap in str() - let the runtime's _canonicalize_subscript handle it
    # subscript_context=True so indirection in subscripts
    # returns VALUE instead of validating as NAME
    subscripts_tuple = gen_subscripts_tuple(
        var.subscripts or [], ctx, subscript_context=True
    )

    # Return empty string for undefined globals
    # resolve_naked returns (name, subscripts), use * to unpack into get()
    return f"(_rt.globals.get(*_rt.globals.resolve_naked({subscripts_tuple})) or '')"


def _generate_ssvn(ssvn: MStructuredSystemVariable, ctx: "GeneratorContext") -> str:
    """Generate Python expression for MUMPS structured system variable (SSVN).

    Generates calls to database abstraction layer for SSVNs
    ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE, etc.

    Args:
        ssvn: MStructuredSystemVariable node (name without ^$)
        ctx: Generator context

    Returns:
        Python expression string: _rt.globals.ssvn_*() call

    Raises:
        NotImplementedError: For unsupported SSVNs (MWAPI, etc.)
    """
    name = ssvn.name.upper()

    # Generate subscript expression (SSVNs typically have exactly one subscript)
    if ssvn.subscripts:
        # SSVNs use first subscript as the lookup key
        subscript_expr = generate_expr(ssvn.subscripts[0], ctx)
    else:
        # No subscript - use empty string
        subscript_expr = "''"

    # Dispatch to appropriate SSVN query method
    if name in ("GLOBAL", "G"):
        return f"_rt.globals.ssvn_global(str({subscript_expr}))"
    elif name in ("JOB", "J"):
        return f"_rt.globals.ssvn_job(str({subscript_expr}))"
    elif name in ("LOCK", "L"):
        return f"_rt.globals.ssvn_lock(str({subscript_expr}))"
    elif name in ("ROUTINE", "R"):
        return f"_rt.globals.ssvn_routine(str({subscript_expr}))"
    elif name in ("SYSTEM", "S"):
        # ^$SYSTEM returns implementation info - delegate to runtime
        return "_rt.system()"
    elif name in ("DEVICE", "D", "CHARACTER", "C"):
        # ^$DEVICE and ^$CHARACTER - return empty (not implemented)
        return "''"
    elif name in ("EVENT", "E", "WINDOW", "W", "DISPLAY", "DI"):
        # MWAPI SSVNs - documented limitation (LIM-003)
        raise NotImplementedError(
            "LIM-003: MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY) not supported"
        )
    elif name in ("LIBRARY", "LI"):
        # ^$LIBRARY - documented limitation (LIM-011)
        raise NotImplementedError("LIM-011: ^$LIBRARY SSVN not supported")
    else:
        raise NotImplementedError(f"Unsupported SSVN: ^${name}")


def _generate_special_variable(var: MSpecialVariable, ctx: "GeneratorContext") -> str:
    """Generate Python expression for MUMPS special variable.

    Currently supported:
    - $TEST ($T): Returns int(_test) for MUMPS-style 0/1 output
    - $HOROLOG ($H): Returns days,seconds since MUMPS epoch
    - $JOB ($J): Returns process ID
    - $IO: Returns current I/O device name
    - $X: Returns current column position
    - $Y: Returns current line position
    - $STORAGE ($S): Returns available memory (large constant)
    - $STACK ($ST): Returns call stack level
    - $QUIT ($Q): Returns 1 if in extrinsic, 0 otherwise
    - $TLEVEL ($TL): Returns transaction nesting level
    - $ZJOB ($ZJ): Returns last JOB'd process ID
    - $ECODE ($EC): Returns comma-delimited error code list
    - $ETRAP ($ET): Returns error trap code string
    - $ZERROR ($ZE): Returns application error message

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

    # $HOROLOG / $H - days since Dec 31, 1840, seconds since midnight
    if name in ("HOROLOG", "H"):
        return "_rt.horolog()"

    # $JOB / $J - current process ID
    if name in ("JOB", "J"):
        return "_rt.job()"

    # $IO / $I - current I/O device
    if name in ("IO", "I"):
        return "_rt.io()"

    # $X - current column position
    if name == "X":
        return "_rt.x()"

    # $Y - current line position
    if name == "Y":
        return "_rt.y()"

    # $STORAGE / $S - available memory (return large constant)
    # MUMPS $STORAGE reports available memory; we return a reasonable large value
    if name in ("STORAGE", "S"):
        return "2147483647"  # Max 32-bit signed integer as placeholder

    # $STACK / $ST - call stack level
    if name in ("STACK", "ST"):
        return "_rt.stack_level()"

    # $QUIT / $Q - extrinsic function context flag
    if name in ("QUIT", "Q"):
        return "_rt.quit_flag()"

    # $TLEVEL / $TL - transaction nesting level
    # Returns current transaction depth (0 = no transaction)
    if name in ("TLEVEL", "TL"):
        return "_rt.tlevel()"

    # $ZJOB / $ZJ - last JOB'd process ID
    # Returns PID of last process started by JOB command
    if name in ("ZJOB", "ZJ"):
        return "_rt.zjob()"

    # $ECODE / $EC - error code list
    # Comma-delimited list of active error codes
    if name in ("ECODE", "EC"):
        return "_rt.ecode()"

    # $ETRAP / $ET - error trap code
    # M code to execute on error
    if name in ("ETRAP", "ET"):
        return "_rt.etrap()"

    # $ZERROR / $ZE - application error message
    # Application-supplied error message text
    if name in ("ZERROR", "ZE"):
        return "_rt.zerror()"

    # $ZTRAP / $ZT - error trap code (alternate form)
    # M code to execute on error when $ETRAP is empty
    if name in ("ZTRAP", "ZT"):
        return "_rt.ztrap()"

    # $ZSTATUS / $ZS - last error status
    # Error status in YDB format
    if name in ("ZSTATUS", "ZS"):
        return "_rt.zstatus()"

    # $ZPOSITION / $ZP - current code position
    # Current position as "label+offset^routine"
    if name in ("ZPOSITION", "ZP"):
        return "_rt.zposition()"

    # $SYSTEM / $SY - system identification
    # Returns "V,S" where V is MDC-assigned implementor number
    if name in ("SYSTEM", "SY"):
        return "_rt.system()"

    # $ESTACK / $ES - relative error stack depth
    # Returns $STACK minus the level where NEW $ESTACK was done
    if name in ("ESTACK", "ES"):
        return "str(_rt.estack())"

    # $PRINCIPAL / $P - principal I/O device
    # Returns the principal device identifier.
    # $P without arguments is $PRINCIPAL (not $PIECE which requires args).
    if name in ("PRINCIPAL", "P", "PIOR", "PIOREFERENCE"):
        return "_rt.principal()"

    # $KEY / $K - terminal input key
    # Returns terminator from last READ command
    if name in ("KEY", "K"):
        return "_rt.key()"

    # $ZEOF / $ZE(OF) - end-of-file indicator
    # Returns 1 if current device is at EOF, 0 otherwise.
    # $ZE is ambiguous ($ZERROR vs $ZEOF). YDB resolves $ZE to $ZERROR,
    # $ZEOF requires at least 4 chars. We match full name only.
    if name == "ZEOF":
        return "_rt.zeof()"

    # IRIS/Caché Special Variables

    # $ZVERSION / $ZV - IRIS version string
    if name in ("ZVERSION", "ZV"):
        return "_rt.zversion()"

    # $ZA - last I/O activity status (read-only, default 0)
    if name == "ZA":
        return "str(_rt.za())"

    # $ZREFERENCE / $ZR - last global reference
    if name in ("ZREFERENCE", "ZR"):
        return "_rt.zreference()"

    # $NAMESPACE / $NSPACE - current namespace
    if name in ("NAMESPACE", "NSPACE"):
        return "_rt.namespace()"

    # -----------------------------------------------------------------
    # Miscellaneous ISVs (024-vista-transpilation-fixes, US5)
    # -----------------------------------------------------------------

    # $DEVICE / $D - current device error status
    # Note: $D() with arguments is $DATA (intrinsic function), handled separately.
    # $D without arguments is $DEVICE (special variable).
    if name in ("DEVICE", "D"):
        return "_rt.device_status()"

    # $REFERENCE / $R - last global reference (standard MUMPS equivalent of $ZR)
    if name in ("REFERENCE", "R"):
        return "_rt.reference()"

    # $ZGBLDIR - global directory file path
    if name == "ZGBLDIR":
        return "_rt.zgbldir()"

    # $ZINTERRUPT / $ZINT - interrupt handler code string
    if name in ("ZINTERRUPT", "ZINT"):
        return "_rt.zinterrupt()"

    # $ZHOROLOG / $ZH - high-resolution timestamp (microseconds since epoch)
    # As SVN, $ZH returns the current timestamp value
    if name in ("ZHOROLOG", "ZH"):
        return "str(int(time.time() * 1000000))"

    # $ZCMDLINE - command line arguments (returns "" in transpiled context)
    if name == "ZCMDLINE":
        return '""'

    # $ZMODE - process mode (INTERACTIVE, OTHER, etc.)
    if name == "ZMODE":
        return '"OTHER"'

    # Add other special variables as needed
    raise NotImplementedError(f"Special variable ${var.name} not yet supported")


def _generate_indirection(
    ind: MIndirection,
    ctx: "GeneratorContext",
    if_condition: bool = False,
    subscript_context: bool = False,
) -> str:
    """Generate Python expression for name indirection (@VAR).

    Dispatches to codegen/indirection.py for runtime indirection handling.
    Uses unified runtime methods:
    - Simple NAME: @X → _rt.get_indirected("X", _scope, levels=1)
    - Multi-level NAME: @@X → _rt.get_indirected("X", _scope, levels=2)
    - With subscripts: @NAME@(1,2) → handled via per_level_subscripts
    - ARGUMENT type: @A in IF → evaluates value of A as expression

    subscript_context changes indirection behavior:
    - subscript_context=False (default): Resolves to NAME, validates result
    - subscript_context=True: Evaluates indirection and returns VALUE for subscript use
      Example: ^V1A(@^(4)) where ^(4)="^V1A(5)" and ^V1A(5)=55
      Returns 55 (the value), not validates "55" as a name

    Args:
        ind: MIndirection ASG node
        ctx: Generator context
        if_condition: If True, this is an IF condition - affects empty string handling
        subscript_context: If True, return VALUE instead of resolving NAME

    Returns:
        Python expression string
    """
    from m2py.asg.enums import IndirectionType
    from m2py.codegen.indirection import (
        generate_name_indirection,
        generate_argument_indirection,
        generate_subscript_indirection,
    )

    # Dispatch based on indirection type
    if ind.indirection_type == IndirectionType.ARGUMENT:
        return generate_argument_indirection(ind, ctx, if_condition=if_condition)
    elif subscript_context:
        # Subscript context - get VALUE for use as subscript
        return generate_subscript_indirection(ind, ctx)
    else:
        # NAME type (default) - look up variable by resolved name
        return generate_name_indirection(ind, ctx)


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

    if op.operator == "+":
        # Addition: use m_add for Decimal precision
        return f"m_add({left}, {right})"
    elif op.operator == "-":
        # Subtraction: use m_sub for Decimal precision
        return f"m_sub({left}, {right})"
    elif op.operator == "*":
        # Multiplication: use m_mul for Decimal precision
        return f"m_mul({left}, {right})"
    elif op.operator == "/":
        # Division: use m_div for 18-digit precision (MUMPS standard)
        return f"m_div({left}, {right})"
    elif op.operator == "\\":
        # Integer division in MUMPS - uses truncation towards zero, not floor division
        return f"m_int_div({left}, {right})"
    elif op.operator == "#":
        # Modulo in MUMPS - uses floor division semantics (unlike Decimal %)
        return f"m_mod({left}, {right})"
    elif op.operator == "**":
        # Exponentiation in MUMPS - base ** exponent
        return f"m_pow({left}, {right})"
    elif op.operator in ("=", "<", ">"):
        # Comparison: use m_compare helper
        return f'm_compare({left}, "{op.operator}", {right})'
    elif op.operator == "_":
        # String concatenation - use m_str for MUMPS-style number formatting
        return f"(m_str({left}) + m_str({right}))"
    elif op.operator == "&":
        # Logical AND - must return int (0/1), not Python bool
        return f"int(m_truth({left}) and m_truth({right}))"
    elif op.operator == "!":
        # Logical OR - must return int (0/1), not Python bool
        return f"int(m_truth({left}) or m_truth({right}))"
    elif op.operator == "'=":
        # Negated equals - must return int (0/1)
        return f'int(not m_compare({left}, "=", {right}))'
    elif op.operator == "'<":
        # Negated less-than (greater than or equal) - must return int (0/1)
        return f'int(not m_compare({left}, "<", {right}))'
    elif op.operator == "'>":
        # Negated greater-than (less than or equal) - must return int (0/1)
        return f'int(not m_compare({left}, ">", {right}))'
    elif op.operator == "[":
        # Contains: A[B returns 1 if B is substring of A
        # Use m_str for MUMPS-style number formatting
        return f"int(m_str({right}) in m_str({left}))"
    elif op.operator == "'[":
        # Not contains: A'[B returns 1 if B is NOT substring of A
        return f"int(m_str({right}) not in m_str({left}))"
    elif op.operator == "]":
        # Follows: A]B returns 1 if A sorts after B (ASCII string comparison)
        # Use m_str for MUMPS-style number formatting (critical for large numbers)
        return f"int(m_str({left}) > m_str({right}))"
    elif op.operator == "']":
        # Not follows: A']B returns 1 if A does NOT sort after B
        return f"int(m_str({left}) <= m_str({right}))"
    elif op.operator == "]]":
        # Sorts after: A]]B returns 1 if A strictly sorts after B
        # Uses MUMPS collation (numerics before strings), empty string never sorts after
        return f"m_sorts_after({left}, {right})"
    elif op.operator == "']]":
        # Not sorts after: A']]B returns 1 if A does NOT strictly sort after B
        return f"int(not m_sorts_after({left}, {right}))"
    elif op.operator == "'&":
        # NAND: returns 1 if NOT (A AND B)
        return f"int(not (m_truth({left}) and m_truth({right})))"
    elif op.operator == "'!":
        # NOR: returns 1 if NOT (A OR B)
        return f"int(not (m_truth({left}) or m_truth({right})))"
    elif op.operator == ">=":
        # Greater-than-or-equal: A>=B equivalent to A'<B (NOT less than)
        # YDB extension — not in ANSI standard but widely used in VistA
        return f'int(not m_compare({left}, "<", {right}))'
    elif op.operator == "<=":
        # Less-than-or-equal: A<=B equivalent to A'>B (NOT greater than)
        # YDB extension — not in ANSI standard but widely used in VistA
        return f'int(not m_compare({left}, ">", {right}))'
    elif op.operator == "?":
        # Pattern match: A?pattern returns 1 if A matches pattern
        return f"m_pattern_match({left}, {right})"
    else:
        raise NotImplementedError(
            f"Unsupported binary operator: {op.operator}"
        )  # pragma: no cover


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
        # Logical NOT in MUMPS - must return int (0/1), not Python bool
        return f"int(not m_truth({operand}))"
    else:
        raise NotImplementedError(
            f"Unsupported unary operator: {op.operator}"
        )  # pragma: no cover


def _generate_pattern_match(expr: MPatternMatch, ctx: "GeneratorContext") -> str:
    """Generate Python pattern match expression from MPatternMatch.

    Handles the MUMPS pattern match operator (?). Uses pre-compiled regex
    for direct patterns to avoid runtime re-compilation.

    Supports both direct patterns (literal) and indirect patterns (@X).
    Also handles negated pattern match ('?) which returns the inverse.

    Args:
        expr: MPatternMatch node
        ctx: Generator context

    Returns:
        Python expression string that evaluates to 1 (match) or 0 (no match)
    """
    subject = generate_expr(expr.subject, ctx) if expr.subject else '""'

    if expr.pattern_indirect:
        # Indirect pattern: X?@Y - pattern determined at runtime
        # Use runtime helper which compiles the pattern dynamically
        pattern = generate_expr(expr.pattern_indirect, ctx)
        result = f"m_pattern_match({subject}, {pattern})"
    elif expr.compiled_regex is not None:
        # Direct pattern with pre-compiled regex - inline the fullmatch call
        # Use re.DOTALL so E pattern code matches newlines per MUMPS spec
        # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
        regex = repr(expr.compiled_regex)
        result = f"(1 if re.fullmatch({regex}, m_str({subject}), re.DOTALL) else 0)"
    else:
        # Direct pattern without compiled regex — pattern compiler always produces
        # compiled_regex, so this branch is unreachable in practice.
        pattern = repr(expr.pattern)  # pragma: no cover
        result = f"m_pattern_match({subject}, {pattern})"  # pragma: no cover

    # Handle negated pattern match ('?)
    if expr.operator == "'?":
        return f"int(not {result})"
    return result


def _generate_extrinsic(expr: MExtrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python extrinsic function call from MExtrinsicFunction.

    Extrinsic functions ($$label) require $TEST save/restore semantics.
    Per MUMPS spec, the caller's $TEST is saved before the call and restored
    after, so the callee's $TEST changes don't leak back.

    By-reference parameters: When arguments are passed by reference (.VAR),
    the caller's variables are updated when the callee modifies them.
    This is handled by:
    1. Callee returns tuple (value, *byref_outputs) when has by-ref outputs
    2. Caller passes _byref list with variable names for by-ref args
    3. _call_extrinsic helper unpacks and updates caller's scope

    Generated pattern (internal):
        _call_extrinsic(_rt, LABEL, arg1, arg2)
        _call_extrinsic(_rt, LABEL, arg1, arg2, _scope=_scope, _byref=['A', 'B'])

    Generated pattern (external):
        _call_extrinsic(_rt, ext2.ADD, arg1, arg2, _scope=_scope, _byref=['A', 'B'])

    The _call_extrinsic helper handles save/restore of _test and by-ref unpacking.
    _rt is passed explicitly as first parameter.

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
    # $$^ROUTINE means call the routine's entry point (routine name as label)
    if not label_name and expr.target.routine:
        label_name = expr.target.routine
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

    # Handle external routine extrinsic
    if expr.target.routine:
        routine_name = expr.target.routine

        # LIM-014: ANSI library routines with zero VistA usage
        # STRING and CHARACTER libraries are completely blocked.
        # MATH library: only unimplemented functions are blocked (implemented ones pass through).
        if label_name.startswith("%"):
            upper_routine = routine_name.upper()
            if upper_routine in ANSI_LIBRARY_ROUTINES_BLOCKED:
                # STRING and CHARACTER: completely blocked
                raise NotImplementedError(
                    f"LIM-014: ANSI library routine ^{routine_name} not supported "
                    f"(use VistA Kernel Library Functions instead)"
                )
            elif (
                upper_routine == "MATH"
                and label_name.upper() not in MATH_FUNCTIONS_IMPLEMENTED
            ):
                # MATH: only unimplemented functions blocked
                raise NotImplementedError(
                    f"LIM-014: ANSI library function {label_name}^MATH not implemented "
                    f"(only basic trig/exp/log functions supported)"
                )

        # Check for bundled routines first (e.g., MATH for $$%SIN^MATH)
        # Bundled routines are in m2py.runtime.routines package
        bundled_routines = {"MATH"}  # Add more as needed

        # Translate routine name to valid Python module name
        # %ROUTINE becomes _pct_ROUTINE for Python import compatibility
        python_module_name = translate_name(routine_name)

        if routine_name in bundled_routines:
            # Import from bundled routines package
            ctx.emitter.line(f"from m2py.runtime.routines import {routine_name}")
            # Bundled routines don't need name translation (they're Python modules)
            module_ref = routine_name
        else:
            # Generate import statement for external routine
            ctx.emitter.line(f"import {python_module_name}")
            module_ref = python_module_name

        # Translate label name to Python function name
        func_name = translate_name(label_name)

        # Generate call via _call_extrinsic with module prefix and _scope.
        # The _call_extrinsic helper provides $TEST save/restore and by-ref unpacking.
        if args:
            return f"_call_extrinsic(_rt, {module_ref}.{func_name}, {args}, _scope=_scope{byref_param})"
        else:
            return f"_call_extrinsic(_rt, {module_ref}.{func_name}, _scope=_scope{byref_param})"

    # Internal extrinsic (within same routine)
    # Translate label name to Python function name
    func_name = translate_name(label_name)

    # For internal calls with by-ref, need _scope for by-ref unpacking
    if byref_names:
        if args:
            return (
                f"_call_extrinsic(_rt, {func_name}, {args}, _scope=_scope{byref_param})"
            )
        else:
            return f"_call_extrinsic(_rt, {func_name}, _scope=_scope{byref_param})"

    # Generate: _call_extrinsic(_rt, FUNC, arg1, arg2, _scope=_scope)
    # Always pass _scope for cross-routine variable visibility
    if args:
        return f"_call_extrinsic(_rt, {func_name}, {args}, _scope=_scope)"
    else:
        return f"_call_extrinsic(_rt, {func_name}, _scope=_scope)"


def _generate_external_function(
    expr: MExternalFunction, ctx: "GeneratorContext"
) -> str:
    """Generate Python call for external C function ($&name, $&package.name).

    External C functions call native code linked into the MUMPS runtime.
    These are implementation-specific and cannot be directly transpiled to Python.

    For Python transpilation, these return a stub that issues a warning and
    returns empty string, rather than raising NotImplementedError which would
    halt transpilation of routines that reference external functions.

    Args:
        expr: MExternalFunction node with package, name, and arguments
        ctx: Generator context

    Returns:
        Python expression calling m_zcall_stub() with identifier
    """
    # Build function identifier for warning message
    if expr.package:
        func_id = f"$&{expr.package}.{expr.name}"
    else:
        func_id = f"$&{expr.name}"

    return f"m_zcall_stub({func_id!r})"


def _generate_extrinsic_arguments_with_byref(
    arguments: List[MActualParameter], ctx: "GeneratorContext"
) -> tuple[str, list[str | None]]:
    """Generate Python arguments for extrinsic function call with by-ref info.

    Returns both the argument string and a list of by-ref variable names.
    The by-ref list has the variable name for BY_REFERENCE arguments and
    None for BY_VALUE arguments.

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
            # By-reference: pass the MArray object directly for aliasing.
            # The callee shares the same MArray, so $D(param) sees
            # descendants and param(sub) accesses caller's tree.
            has_byref = True
            if arg.variable_name:
                # Direct by-ref (.X): pass the MArray object from scope
                var_name = arg.variable_name
                parts.append(f"_scope.get({var_name!r}, MArray())")
                byref_names.append(var_name)
            elif arg.expression and isinstance(arg.expression, MIndirection):
                # Indirected by-ref (.@IX): resolve indirection to MArray.
                # Uses runtime to resolve name then get MArray.
                ind_expr = generate_expr(arg.expression, ctx)
                # Replace get_indirected with get_indirected_marray for by-ref
                marray_expr = ind_expr.replace(
                    "_rt.get_indirected(", "_rt.get_indirected_marray("
                )
                parts.append(marray_expr)
                byref_names.append(None)  # Resolved at runtime
            elif arg.expression:
                # Other expression passed by-ref (unusual)
                parts.append(generate_expr(arg.expression, ctx))
                byref_names.append(None)
            else:
                parts.append("None")
                byref_names.append(None)
        else:  # BY_VALUE
            if arg.expression:
                parts.append(generate_expr(arg.expression, ctx))
            elif arg.variable_name:
                var_name = arg.variable_name
                parts.append(f"m_var_value(_scope[{var_name!r}])")
            else:
                parts.append("None")
            byref_names.append(None)

    # Only return byref_names if there were actually by-ref arguments
    return ", ".join(parts), byref_names if has_byref else []


def _gen_data(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $DATA/$D function.

    Generates m_data() or m_data_global() calls based on whether
    the argument is a local or global variable.

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
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.parser.textx_classes import LocalVariable

    # Get first argument (the variable to check)
    args = getattr(expr, "arguments", [])
    var = args[0]

    # Handle MIndirection: $D(@A@(1)) needs runtime resolution
    if isinstance(var, MIndirectionType):
        # For indirection, use unified resolve_for_target API via helper
        from m2py.codegen.indirection import generate_data_indirection_name

        return generate_data_indirection_name(var, ctx)

    # Generate subscript tuple for non-indirection cases
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    subscripts_tuple = gen_subscripts_tuple(subscripts, ctx)

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        return f"m_data({var_base_expr(var_name, ctx)}, {subscripts_tuple})"
    elif isinstance(var, GlobalVariable):
        # Global variable: m_data_global(_rt.globals, 'NAME', subscripts)
        return f"m_data_global(_rt.globals, {var_name!r}, {subscripts_tuple})"
    elif isinstance(var, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
        # Extended global $DATA with namespace prefix
        ns = getattr(var.environment, "value", "") if var.environment else ""
        ns_name = f"{ns}:{var_name}" if ns else var_name
        return f"m_data_global(_rt.globals, {ns_name!r}, {subscripts_tuple})"
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve then call m_data_global
        return (
            f"(lambda _n, _s: m_data_global(_rt.globals, _n, _s))"
            f"(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
    else:
        return f"m_data({var_base_expr(var_name, ctx)}, {subscripts_tuple})"


def _gen_get(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $GET/$G function.

    Generates m_get() or m_get_global() calls based on whether
    the argument is a local or global variable.

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
        $G(@A) → get_indirected("A", _scope, levels=1)
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.parser.textx_classes import LocalVariable

    # Get arguments
    args = getattr(expr, "arguments", [])
    var = args[0]

    # Get default value if provided
    if len(args) >= 2:
        default_expr = generate_expr(args[1], ctx)
        default_code = f"m_str({default_expr})"
    else:
        default_code = '""'

    # Handle MIndirection: $G(@A) needs runtime resolution
    if isinstance(var, MIndirectionType):
        # For indirection, use unified get_indirected API via helper
        from m2py.codegen.indirection import generate_get_indirection_name

        return generate_get_indirection_name(var, ctx, default_code)

    # Generate subscript tuple
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    subscripts_tuple = gen_subscripts_tuple(subscripts, ctx)

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        # Local variable: m_get(_scope.get('VAR', None), subscripts, default)
        python_name = translate_name(var_name)
        return f"m_get(_scope.get({python_name!r}), {subscripts_tuple}, {default_code})"
    elif isinstance(var, GlobalVariable):
        # Global variable: use lambda to evaluate subscripts once and pre-set
        # naked indicator before evaluating default, so global refs in default
        # correctly override naked. Subscripts may contain naked refs or other
        # globals with side effects, so they must be evaluated exactly once.
        return (
            f"(lambda _subs: (_rt.globals.set_order_naked({var_name!r}, _subs), "
            f"m_get_global(_rt.globals, {var_name!r}, _subs, "
            f"{default_code}, update_naked=False))[1])({subscripts_tuple})"
        )
    elif isinstance(var, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
        # Extended global $GET with namespace prefix
        ns = getattr(var.environment, "value", "") if var.environment else ""
        ns_name = f"{ns}:{var_name}" if ns else var_name
        return (
            f"m_get_global(_rt.globals, {ns_name!r}, {subscripts_tuple}, "
            f"{default_code})"
        )
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve, pre-set naked, then call m_get_global
        return (
            f"(lambda _n, _s: (_rt.globals.set_order_naked(_n, _s), "
            f"m_get_global(_rt.globals, _n, _s, {default_code}, "
            f"update_naked=False))[1])(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
    else:
        # Fallback for any other variable type - treat as local
        python_name = translate_name(var_name)
        return f"m_get(_scope.get({python_name!r}), {subscripts_tuple}, {default_code})"


def _gen_order(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ORDER/$O function.

    Generates m_order() or m_order_global() calls based on whether
    the argument is a local or global variable.

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
        $O(@X) → _rt.get_order(X_value, _scope, direction)
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.parser.textx_classes import LocalVariable

    # Get arguments
    args = getattr(expr, "arguments", [])
    var = args[0]

    # Get direction argument if present (second argument)
    direction_code = "1"  # Default to forward
    if len(args) >= 2:
        direction_code = generate_expr(args[1], ctx)

    # Handle MIndirection: $O(@X) needs runtime resolution
    if isinstance(var, MIndirectionType):
        from m2py.codegen.indirection import (
            _count_indirection_levels_with_subscripts,
        )

        levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(
            var
        )

        # Build subscript expressions for ALL levels (inner to outer)
        # _count_indirection_levels_with_subscripts collects subscripts from
        # every @ level, including inner ones that var.name_indirection_subscripts misses
        per_level_sub_exprs: list[list[str]] = []
        for sub_list in all_subscripts:
            sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
            per_level_sub_exprs.append(sub_exprs)

        # Generate the variable name resolution
        from m2py.asg.expressions import MVariable
        from m2py.parser.textx_classes import LocalVariable as MLocalVariable

        if isinstance(inner_expr, GlobalVariable):
            # Global variable as indirection source: @^V or @^V(0)
            global_name = inner_expr.name
            # Include subscripts from the GlobalVariable itself (e.g., ^V(0))
            inner_global_subs = getattr(inner_expr, "subscripts", [])
            if inner_global_subs:
                subs_tuple = gen_subscripts_tuple(inner_global_subs, ctx)
                name_expr = (
                    f'str((_rt.globals.get({global_name!r}, {subs_tuple}) or ""))'
                )
            else:
                name_expr = f'str((_rt.globals.get({global_name!r}, ()) or ""))'

            # For levels > 1, use resolve_order_name to do multi-level resolution
            if levels > 1:
                # Build per_level_subscripts arg for runtime
                if per_level_sub_exprs:
                    pls_parts = []
                    for sub_exprs_level in per_level_sub_exprs:
                        pls_parts.append(f"[{', '.join(sub_exprs_level)}]")
                    pls_arg = f", per_level_subscripts=[{', '.join(pls_parts)}]"
                else:
                    pls_arg = ""

                return (
                    f"_rt.get_order("
                    f"_rt.resolve_order_name({name_expr}, _scope, "
                    f"levels_remaining={levels - 1}{pls_arg}), "
                    f"_scope, {direction_code})"
                )
            else:
                # Single level: use get_order with additional_subscripts
                if per_level_sub_exprs:
                    # Flatten all subscripts for single-level
                    all_subs_flat = []
                    for sub_exprs_level in per_level_sub_exprs:
                        all_subs_flat.extend(sub_exprs_level)
                    additional_subs_arg = f", additional_subscripts={gen_subscripts_tuple(all_subs_flat, ctx)}"
                else:
                    additional_subs_arg = ""

                return (
                    f"_rt.get_order({name_expr}, _scope, "
                    f"{direction_code}{additional_subs_arg})"
                )
        elif isinstance(inner_expr, (MVariable, MLocalVariable)):
            base_name = inner_expr.name
            # Check if inner_expr has subscripts (e.g., @@@A(0) -> A(0), not A)
            inner_subscripts = getattr(inner_expr, "subscripts", [])
            if inner_subscripts:
                # Build the subscripted variable name at runtime
                # For @@@A(0): base_name="A", subscripts=[0] -> "A(0)"
                sub_exprs = [generate_expr(sub, ctx) for sub in inner_subscripts]
                if len(sub_exprs) == 1:
                    full_name_expr = (
                        "'" + base_name + "(' + str(" + sub_exprs[0] + ") + ')'"
                    )
                else:
                    subs_parts = " + ',' + ".join("str(" + s + ")" for s in sub_exprs)
                    full_name_expr = "'" + base_name + "(' + " + subs_parts + " + ')'"
            else:
                full_name_expr = f'"{base_name}"'

            # Use resolve_for_target (unified method) to get the variable NAME.
            # $ORDER/$NEXT just need the name to find the next subscript.
            name_expr = (
                f"_rt.resolve_for_target({full_name_expr}, _scope, levels={levels})"
            )
        else:
            name_expr_base = generate_expr(inner_expr, ctx)
            name_expr = f"str({name_expr_base})"

        # For non-GlobalVariable cases, use get_order with additional_subscripts
        # (GlobalVariable cases were already handled above with early return)
        additional_subs_arg = ""
        if not isinstance(inner_expr, GlobalVariable):
            if per_level_sub_exprs:
                all_subs_flat = []
                for sub_exprs_level in per_level_sub_exprs:
                    all_subs_flat.extend(sub_exprs_level)
                additional_subs_arg = f", additional_subscripts={gen_subscripts_tuple(all_subs_flat, ctx)}"
            else:
                additional_subs_arg = ""

        # Use _rt.get_order which handles indirected variable names
        # Pass additional_subscripts separately for proper merging
        return (
            f"_rt.get_order({name_expr}, _scope, {direction_code}{additional_subs_arg})"
        )

    # Generate subscript tuple for non-indirection cases
    # For $ORDER, subscripts include the starting point for iteration
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    subscripts_tuple = gen_subscripts_tuple(subscripts, ctx, empty='("",)')

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        return f"m_order({var_base_expr(var_name, ctx)}, {subscripts_tuple}, {direction_code})"
    elif isinstance(var, GlobalVariable):
        # Global variable: use lambda to evaluate subscripts once and pre-set
        # naked indicator before evaluating direction, so global refs in
        # direction correctly override naked. Subscripts may contain naked refs
        # or other globals with side effects, so they must be evaluated once.
        return (
            f"(lambda _subs: (_rt.globals.set_order_naked({var_name!r}, _subs), "
            f"m_order_global(_rt.globals, {var_name!r}, _subs, "
            f"{direction_code}, update_naked=False))[1])({subscripts_tuple})"
        )
    elif isinstance(var, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
        # Extended global $ORDER with namespace prefix
        ns = getattr(var.environment, "value", "") if var.environment else ""
        ns_name = f"{ns}:{var_name}" if ns else var_name
        return (
            f"m_order_global(_rt.globals, {ns_name!r}, {subscripts_tuple}, "
            f"{direction_code})"
        )
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve, pre-set naked, then call m_order_global.
        # Use tuple expression for naked indicator ordering like GlobalVariable.
        return (
            f"(lambda _n, _s: (_rt.globals.set_order_naked(_n, _s), "
            f"m_order_global(_rt.globals, _n, _s, {direction_code}, "
            f"update_naked=False))[1])(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
    else:
        return f"m_order({var_base_expr(var_name, ctx)}, {subscripts_tuple}, {direction_code})"


def _gen_query(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $QUERY/$Q function.

    Generates m_query() or m_query_global() calls based on whether
    the argument is a local or global variable.

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
        $Q(@A@("")) → _rt.get_query(resolved_name, ("",), _scope)
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.parser.textx_classes import LocalVariable

    # Get arguments
    args = getattr(expr, "arguments", [])
    var = args[0]

    # Handle MIndirection: $Q(@A@("")) needs runtime resolution
    if isinstance(var, MIndirectionType):
        # For indirection, use unified API via helper
        from m2py.codegen.indirection import generate_query_indirection_name

        return generate_query_indirection_name(var, ctx)

    # Generate subscript tuple
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    subscripts_tuple = gen_subscripts_tuple(subscripts, ctx, empty='("",)')

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        return (
            f"m_query({var_base_expr(var_name, ctx)}, {var_name!r}, {subscripts_tuple})"
        )
    elif isinstance(var, GlobalVariable):
        # Global variable: m_query_global(_rt.globals, 'NAME', subscripts)
        return f"m_query_global(_rt.globals, {var_name!r}, {subscripts_tuple})"
    elif isinstance(var, (ExtendedGlobalPipe, ExtendedGlobalBracket)):
        # Extended global $QUERY with namespace prefix
        ns = getattr(var.environment, "value", "") if var.environment else ""
        ns_name = f"{ns}:{var_name}" if ns else var_name
        return f"m_query_global(_rt.globals, {ns_name!r}, {subscripts_tuple})"
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve then call m_query_global
        return (
            f"(lambda _n, _s: m_query_global(_rt.globals, _n, _s))"
            f"(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
    else:
        return (
            f"m_query({var_base_expr(var_name, ctx)}, {var_name!r}, {subscripts_tuple})"
        )


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
    - $T(@X) → indirected label
    - $T(@X+N) → indirected label with offset

    Args:
        expr: TextFunction ASG node with line_ref dictionary
        ctx: Generator context

    Returns:
        Python code calling _rt.get_text() or _rt.get_text_indirect()
    """
    from m2py.asg.expressions import MLiteral
    from m2py.asg.enums import LiteralType

    # TextFunction stores line reference info in line_ref dict, not arguments
    line_ref = getattr(expr, "line_ref", {})

    # Check for label indirection ($T(@X) or $T(@X+N))
    label_indirect = line_ref.get("label_indirect")

    # Resolve routine (static or indirected)
    routine = line_ref.get("routine")
    routine_indirect = line_ref.get("routine_indirect")
    label = line_ref.get("label")
    offset = line_ref.get("offset")
    offset_sign = line_ref.get("offset_sign")

    # Build module expression for external routines
    module_expr = None
    if routine is not None and routine_indirect is None:
        # Static routine name
        module_expr = f"_rt._get_module_safe('{routine}')"
    elif routine_indirect is not None:
        # Indirected routine name: ^@ROU or ^@^VAR
        from m2py.asg.expressions import MIndirection

        if isinstance(routine_indirect, MIndirection) and routine_indirect.expression:
            inner_expr = generate_expr(routine_indirect.expression, ctx)
            rout_val = f"m_str({inner_expr})"
        else:
            rout_val = f"m_str({generate_expr(routine_indirect, ctx)})"
        module_expr = f"_rt._get_module_safe({rout_val})"

    if label_indirect is not None:
        # For $TEXT(@X), we need the VALUE of X (as a string), not variable indirection.
        # The indirection just means "use the value of this expression as the label name."
        # Extract the inner expression from the indirection and evaluate it directly.
        from m2py.asg.expressions import MIndirection

        if isinstance(label_indirect, MIndirection) and label_indirect.expression:
            # Get the value of the inner expression (e.g., X in @X)
            inner_expr = generate_expr(label_indirect.expression, ctx)
            label_expr = f"m_str({inner_expr})"
        else:
            label_expr = (
                f"m_str({generate_expr(label_indirect, ctx)})"  # pragma: no cover
            )

        # Build params for get_text_indirect
        params = [label_expr]

        # Handle offset if present
        if offset is not None:
            if isinstance(offset, MLiteral) and offset.literal_type in (
                LiteralType.INTEGER,
                LiteralType.DECIMAL,
            ):
                offset_val = (
                    int(offset.value) if offset_sign == "+" else -int(offset.value)
                )
                params.append(f"offset={offset_val}")
            else:
                offset_code = generate_expr(offset, ctx)
                if offset_sign == "-":
                    params.append(f"offset=-int(m_num({offset_code}))")
                else:
                    params.append(f"offset=int(m_num({offset_code}))")

        # Pass module for external routine references
        if module_expr is not None:
            params.append(f"module={module_expr}")

        return f"_rt.get_text_indirect({', '.join(params)})"

    # Non-indirected label path
    # Build the get_text() call parameters
    params = []

    # Handle offset parameter
    if offset is not None:
        if isinstance(offset, MLiteral) and offset.literal_type in (
            LiteralType.INTEGER,
            LiteralType.DECIMAL,
        ):
            # Numeric literal - apply sign and truncate to integer for MUMPS semantics
            offset_val = int(offset.value) if offset_sign == "+" else -int(offset.value)
            params.append(f"offset={offset_val}")
        else:
            # Offset is an expression (variable, string literal, etc.)
            # Must convert to int via m_num() since MUMPS coerces non-numeric strings to 0
            offset_code = generate_expr(offset, ctx)
            if offset_sign == "-":
                params.append(f"offset=-int(m_num({offset_code}))")
            else:
                params.append(f"offset=int(m_num({offset_code}))")
    elif offset_sign is not None and label is None:
        # Explicit sign without offset value - $T(+) or $T(-) defaults to 0
        # This handles $T(+0) or $T(-0) which both equal 0
        params.append("offset=0")
    elif label is None and module_expr is not None:
        # $T(^ROUTINE) — no label, no offset, but has routine
        # This means "first line of routine" = offset 1
        params.append("offset=1")
    elif label is None:
        # No label, no offset, no routine - must be $T() which defaults to +0
        params.append("offset=0")
    else:
        # Label with no offset - defaults to 0
        params.append("offset=0")

    # Handle label parameter
    if label is not None:
        params.append(f'label="{label}"')

    # Handle external routine
    if module_expr is not None:
        params.append(f"module={module_expr}")
        params.append("is_external=True")

    return f"_rt.get_text({', '.join(params)})"


def _gen_select(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $SELECT/$S function.

    Generates a chained conditional expression that evaluates
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

    # Build the chained conditional expression
    # Each MSelectArg has condition and value
    parts = []
    for arg in args:
        cond_expr = generate_expr(arg.condition, ctx)
        val_expr = generate_expr(arg.value, ctx)
        parts.append((cond_expr, val_expr))

    # Build chained conditional: (val1 if m_truth(cond1) else val2 if m_truth(cond2) else ... else _raise_select_false())
    # We need to build from the inside out, starting with the fallback
    result = "_raise_select_false()"

    # Build backwards from the last condition
    for cond_expr, val_expr in reversed(parts):
        result = f"({val_expr} if m_truth({cond_expr}) else {result})"

    return result


# =============================================================================
# String Functions ($LENGTH, $PIECE, $EXTRACT)
# =============================================================================


def _gen_length(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $LENGTH/$L function.

    $LENGTH has two forms:
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
        $L("ABC","") → 0 (empty delimiter returns 0)
    """
    args = getattr(expr, "arguments", [])

    # First argument is the string
    string_expr = generate_expr(args[0], ctx)

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) == 1:
        # Single argument - character count
        return f"len(m_str({string_expr}))"
    else:
        # Two arguments - piece count
        # Per MUMPS spec: empty delimiter returns 0
        # Otherwise: piece count = delimiter occurrences + 1
        delimiter_expr = generate_expr(args[1], ctx)
        return f"(0 if m_str({delimiter_expr}) == '' else m_str({string_expr}).count(m_str({delimiter_expr})) + 1)"


def _gen_piece(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $PIECE/$P function.

    $PIECE extracts delimited pieces.
    $P(string, delimiter [, from [, to]])

    Per MUMPS spec, `from` defaults to 1 when omitted.
    $P("A^B","^") is equivalent to $P("A^B","^",1) and returns "A".

    Args:
        expr: MIntrinsicFunction ASG node with 2-4 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_piece() helper

    Examples:
        $P("A^B^C","^") → m_piece("A^B^C", "^", 1)
        $P("A^B^C","^",2) → m_piece("A^B^C", "^", 2)
        $P("A^B^C","^",2,3) → m_piece("A^B^C", "^", 2, 3)
    """
    args = getattr(expr, "arguments", [])

    if len(args) < 2:
        # Not enough arguments - return empty string
        return '""'

    string_expr = generate_expr(args[0], ctx)
    delimiter_expr = generate_expr(args[1], ctx)

    # Default from=1 when only 2 arguments provided
    if len(args) >= 3:
        from_expr = generate_expr(args[2], ctx)
    else:
        from_expr = "1"

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) >= 4:
        to_expr = generate_expr(args[3], ctx)
        return f"m_piece(m_str({string_expr}), m_str({delimiter_expr}), int(m_num({from_expr})), int(m_num({to_expr})))"
    else:
        return f"m_piece(m_str({string_expr}), m_str({delimiter_expr}), int(m_num({from_expr})))"


def _gen_extract(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $EXTRACT/$E function.

    $EXTRACT extracts substrings by position.
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

    string_expr = generate_expr(args[0], ctx)

    if len(args) == 1:
        # $E(string) - default to first character
        # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
        return f"m_extract(m_str({string_expr}), 1, 1)"
    elif len(args) == 2:
        # $E(string, from) - single character at position from
        from_expr = generate_expr(args[1], ctx)
        return f"m_extract(m_str({string_expr}), int(m_num({from_expr})), int(m_num({from_expr})))"
    else:
        # $E(string, from, to) - substring
        # Handle empty 'to' argument: $E(X,3,) means extract from pos 3 to end
        from_expr = generate_expr(args[1], ctx)
        if args[2] is None:
            # Empty 'to' arg → extract to end of string
            return f"m_extract(m_str({string_expr}), int(m_num({from_expr})), len(m_str({string_expr})))"
        to_expr = generate_expr(args[2], ctx)
        return f"m_extract(m_str({string_expr}), int(m_num({from_expr})), int(m_num({to_expr})))"


def _gen_find(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $FIND/$F function.

    $FIND locates a substring and returns the position AFTER the match.
    $F(string, target [, start])

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

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) >= 3:
        start_expr = generate_expr(args[2], ctx)
        return f"m_find(m_str({string_expr}), m_str({target_expr}), int(m_num({start_expr})))"
    else:
        return f"m_find(m_str({string_expr}), m_str({target_expr}), 1)"


def _gen_translate(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $TRANSLATE/$TR function.

    $TRANSLATE performs character-by-character replacement or deletion.
    $TR(string, from [, to])

    Characters in 'from' are replaced by corresponding characters in 'to'.
    If 'to' is shorter than 'from', extra characters in 'from' are deleted.
    If 'to' is longer than 'from', extra characters in 'to' are ignored.
    If 'to' is omitted, all characters in 'from' are deleted.

    Args:
        expr: MIntrinsicFunction ASG node with 2-3 arguments
        ctx: Generator context

    Returns:
        Python expression using m_translate() runtime helper

    Examples:
        $TR("HELLO","L") → "HEO" (delete all L's)
        $TR("HELLO","LO","XY") → "HEXXY" (L→X, O→Y)
        $TR("HELLO","HEL","ABC") → "ABCCO" (H→A, E→B, L→C)
        $TR("ABCDEFGHIJ","ABC","abcdef") → "abcDEFGHIJ" (extra to_chars ignored)
    """
    args = getattr(expr, "arguments", [])

    if len(args) < 2:
        # Not enough arguments - return original string
        if args:
            return f"m_str({generate_expr(args[0], ctx)})"
        return '""'

    string_expr = generate_expr(args[0], ctx)
    from_expr = generate_expr(args[1], ctx)

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) >= 3:
        to_expr = generate_expr(args[2], ctx)
        return (
            f"m_translate(m_str({string_expr}), m_str({from_expr}), m_str({to_expr}))"
        )
    else:
        # No 'to' argument - delete all characters in 'from'
        return f"m_translate(m_str({string_expr}), m_str({from_expr}))"


def _gen_ascii(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ASCII/$A function.

    $ASCII returns the ASCII code of a character.
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

    string_expr = generate_expr(args[0], ctx)

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) >= 2:
        pos_expr = generate_expr(args[1], ctx)
        # 1-indexed position, -1 if out of range
        return f"(ord(m_str({string_expr})[int(m_num({pos_expr}))-1]) if 0 < int(m_num({pos_expr})) <= len(m_str({string_expr})) else -1)"
    else:
        # Default position 1 (first character)
        return f"(ord(m_str({string_expr})[0]) if m_str({string_expr}) else -1)"


def _gen_char(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $CHAR/$C function.

    $CHAR converts ASCII codes to characters.
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

    $RANDOM generates random integers from 0 to limit-1.
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

    $NAME converts a variable reference to a canonical name string
    representation.

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
        $NA(@A) → _rt.get_name(resolved_name, (), _scope)
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType

    args = getattr(expr, "arguments", [])
    var = args[0]

    # Handle MIndirection: $NA(@A) needs runtime resolution
    if isinstance(var, MIndirectionType):
        from m2py.codegen.indirection import generate_name_function_indirection

        # Get depth argument if present
        depth_expr = None
        if len(args) >= 2:
            depth_expr = generate_expr(args[1], ctx)

        return generate_name_function_indirection(var, ctx, depth_expr)

    # Handle NakedGlobal: $NA(^(1)) needs runtime naked resolution first
    if isinstance(var, NakedGlobal):
        subscripts = getattr(var, "subscripts", [])
        subscripts_tuple = gen_subscripts_tuple(subscripts, ctx)

        # Get depth argument if present
        depth_arg = ""
        if len(args) >= 2:
            depth_expr = generate_expr(args[1], ctx)
            depth_arg = f", depth=int(m_num({depth_expr}))"

        # Resolve naked reference first, then apply $NAME
        # resolve_naked returns (name, full_subscripts)
        return f"(lambda _n, _s: m_name(_n, _s{depth_arg}, is_global=True))(*_rt.globals.resolve_naked({subscripts_tuple}))"

    var_name = getattr(var, "name", "")
    subscripts = getattr(var, "subscripts", [])

    # Build subscripts tuple - evaluate at runtime
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts_tuple = gen_subscripts_tuple(subscripts, ctx)

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

    $QLENGTH counts subscripts in a name string.

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

    name_expr = generate_expr(args[0], ctx)
    return f"m_qlength(str({name_expr}))"


def _gen_qsubscript(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $QSUBSCRIPT/$QS function.

    $QSUBSCRIPT extracts a subscript from a name string.

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


def _gen_justify(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $JUSTIFY/$J function.

    $JUSTIFY right-justifies a value within a field width.

    $JUSTIFY(expr, width [, decimals]):
    - Right-justify expr within width characters
    - Optional decimals: format as number with specified decimal places

    Args:
        expr: MIntrinsicFunction ASG node with 2-3 arguments
        ctx: Generator context

    Returns:
        Python expression using string formatting

    Examples:
        $J(12,5) → "   12"
        $J("ABC",6) → "   ABC"
        $J(3.14159,10,2) → "      3.14"
    """
    args = getattr(expr, "arguments", [])
    if len(args) < 2:
        # Not enough arguments
        if args:
            return f"str({generate_expr(args[0], ctx)})"
        return '""'

    value_expr = generate_expr(args[0], ctx)
    width_expr = generate_expr(args[1], ctx)

    if len(args) >= 3:
        # With decimals - use helper function for proper formatting
        decimals_expr = generate_expr(args[2], ctx)
        return f"m_justify(m_num({value_expr}), int(m_num({width_expr})), int(m_num({decimals_expr})))"
    else:
        # Simple right-justify - use m_str for MUMPS canonical formatting
        # This ensures E-notation is expanded, trailing .0 removed, etc.
        return f"m_str({value_expr}).rjust(int(m_num({width_expr})))"


def _gen_reverse(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $REVERSE/$RE function.

    $REVERSE reverses a string.

    Args:
        expr: MIntrinsicFunction ASG node with 1 argument
        ctx: Generator context

    Returns:
        Python expression using string slicing

    Examples:
        $RE("HELLO") → "OLLEH"
        $RE("") → ""
    """
    args = getattr(expr, "arguments", [])

    string_expr = generate_expr(args[0], ctx)
    return f"m_str({string_expr})[::-1]"


def _gen_fnumber(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $FNUMBER/$FN function.

    $FNUMBER formats a number with various options.

    $FNUMBER(number, codes [, decimals]):
    - codes: string containing formatting codes
      - "," = add comma separators
      - "+" = show + sign for positive numbers
      - "-" = trailing minus for negative
      - "P" = parentheses for negative
      - "T" = trailing sign (space for positive, - for negative)

    Args:
        expr: MIntrinsicFunction ASG node with 2-3 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_fnumber() helper

    Examples:
        $FN(12345.67,",") → "12,345.67"
        $FN(-42,"P") → "(42)"
    """
    args = getattr(expr, "arguments", [])
    if len(args) < 2:
        if args:
            return f"str(m_num({generate_expr(args[0], ctx)}))"
        return '""'

    value_expr = generate_expr(args[0], ctx)
    codes_expr = generate_expr(args[1], ctx)

    if len(args) >= 3:
        decimals_expr = generate_expr(args[2], ctx)
        return f"m_fnumber(m_num({value_expr}), str({codes_expr}), int(m_num({decimals_expr})))"
    else:
        return f"m_fnumber(m_num({value_expr}), str({codes_expr}))"


# =============================================================================
# Register Intrinsic Function Generators
# =============================================================================
# Registration happens at module load time after all functions are defined.

# $ORDER, $QUERY
INTRINSIC_GENERATORS["O"] = _gen_order
INTRINSIC_GENERATORS["ORDER"] = _gen_order
INTRINSIC_GENERATORS["Q"] = _gen_query
INTRINSIC_GENERATORS["QUERY"] = _gen_query

# $SELECT
INTRINSIC_GENERATORS["S"] = _gen_select
INTRINSIC_GENERATORS["SELECT"] = _gen_select

# String functions ($LENGTH, $PIECE, $EXTRACT)
INTRINSIC_GENERATORS["L"] = _gen_length
INTRINSIC_GENERATORS["LENGTH"] = _gen_length
INTRINSIC_GENERATORS["P"] = _gen_piece
INTRINSIC_GENERATORS["PIECE"] = _gen_piece
INTRINSIC_GENERATORS["E"] = _gen_extract
INTRINSIC_GENERATORS["EXTRACT"] = _gen_extract

# Data functions ($DATA, $GET)
INTRINSIC_GENERATORS["D"] = _gen_data
INTRINSIC_GENERATORS["DATA"] = _gen_data
INTRINSIC_GENERATORS["G"] = _gen_get
INTRINSIC_GENERATORS["GET"] = _gen_get

# String search and transform functions ($FIND, $TRANSLATE, $ASCII, $CHAR)
INTRINSIC_GENERATORS["F"] = _gen_find
INTRINSIC_GENERATORS["FIND"] = _gen_find
INTRINSIC_GENERATORS["TR"] = _gen_translate
INTRINSIC_GENERATORS["TRANSLATE"] = _gen_translate
INTRINSIC_GENERATORS["A"] = _gen_ascii
INTRINSIC_GENERATORS["ASCII"] = _gen_ascii
INTRINSIC_GENERATORS["C"] = _gen_char
INTRINSIC_GENERATORS["CHAR"] = _gen_char

# Numeric functions ($RANDOM)
INTRINSIC_GENERATORS["R"] = _gen_random
INTRINSIC_GENERATORS["RANDOM"] = _gen_random

# Array utility functions ($NAME, $QLENGTH, $QSUBSCRIPT)
INTRINSIC_GENERATORS["NA"] = _gen_name
INTRINSIC_GENERATORS["NAME"] = _gen_name
INTRINSIC_GENERATORS["QL"] = _gen_qlength
INTRINSIC_GENERATORS["QLENGTH"] = _gen_qlength
INTRINSIC_GENERATORS["QS"] = _gen_qsubscript
INTRINSIC_GENERATORS["QSUBSCRIPT"] = _gen_qsubscript

# Formatting functions ($JUSTIFY, $FNUMBER, $REVERSE)
INTRINSIC_GENERATORS["J"] = _gen_justify
INTRINSIC_GENERATORS["JUSTIFY"] = _gen_justify
INTRINSIC_GENERATORS["FN"] = _gen_fnumber
INTRINSIC_GENERATORS["FNUMBER"] = _gen_fnumber
INTRINSIC_GENERATORS["RE"] = _gen_reverse
INTRINSIC_GENERATORS["REVERSE"] = _gen_reverse


# =============================================================================
# $ZDATE function
# =============================================================================


def _gen_zdate(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZDATE/$ZD function.

    $ZDATE formats $HOROLOG values into human-readable date/time strings.

    $ZDATE(horolog[,format[,months[,days]]]):
    - horolog: $HOROLOG value (days or days,seconds)
    - format: Format string (default "MM/DD/YY")
    - months: Comma-separated custom month names
    - days: Comma-separated custom day names

    Args:
        expr: MIntrinsicFunction ASG node with 1-4 arguments
        ctx: Generator context

    Returns:
        Python expression calling _rt_helpers.m_zdate()

    Examples:
        $ZD(66337) → "08/16/22"
        $ZD(66337,"YYYY-MM-DD") → "2022-08-16"
        $ZD("66337,45296","24:60:SS") → "12:34:56"
    """
    args = getattr(expr, "arguments", [])
    if not args:
        # No arguments - return empty string
        return '""'

    horolog_expr = generate_expr(args[0], ctx)

    if len(args) == 1:
        # $ZD(horolog) - default format
        return f"m_zdate(m_str({horolog_expr}))"
    elif len(args) == 2:
        # $ZD(horolog, format)
        fmt_expr = generate_expr(args[1], ctx)
        return f"m_zdate(m_str({horolog_expr}), m_str({fmt_expr}))"
    elif len(args) == 3:
        # $ZD(horolog, format, months)
        fmt_expr = generate_expr(args[1], ctx)
        months_expr = generate_expr(args[2], ctx)
        return (
            f"m_zdate(m_str({horolog_expr}), m_str({fmt_expr}), m_str({months_expr}))"
        )
    else:
        # $ZD(horolog, format, months, days)
        fmt_expr = generate_expr(args[1], ctx)
        months_expr = generate_expr(args[2], ctx)
        days_expr = generate_expr(args[3], ctx)
        return f"m_zdate(m_str({horolog_expr}), m_str({fmt_expr}), m_str({months_expr}), m_str({days_expr}))"


INTRINSIC_GENERATORS["ZD"] = _gen_zdate
INTRINSIC_GENERATORS["ZDATE"] = _gen_zdate

# $TEXT
INTRINSIC_GENERATORS["T"] = _generate_text
INTRINSIC_GENERATORS["TEXT"] = _generate_text


# $NEXT (pre-1995 deprecated, similar to $ORDER but returns -1 when no next)
def _gen_next(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $NEXT function.

    $NEXT is a pre-1995 deprecated function similar to $ORDER, but:
    - Returns -1 instead of "" when there is no next subscript
    - Uses -1 as special "start from beginning" marker (like $ORDER uses "")

    So $NEXT(A(-1)) is equivalent to $ORDER(A("")) - returns FIRST subscript.

    Implementation: Generate runtime call that handles -1 ↔ "" conversion.
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.parser.textx_classes import GlobalVariable, LocalVariable

    args = getattr(expr, "arguments", [])
    var = args[0]

    # For locals and globals, generate the appropriate runtime call
    # The runtime helper will handle -1 ↔ "" conversion
    if isinstance(var, GlobalVariable):
        global_name = var.name
        subscripts = getattr(var, "subscripts", [])
        subs_code = gen_subscripts_tuple(subscripts, ctx)
        return f"_rt.m_next_global({global_name!r}, {subs_code})"
    elif isinstance(var, MIndirectionType):
        # For indirection, fall back to $ORDER with -1 conversion
        order_code = _gen_order(expr, ctx)
        return f"(lambda _r: -1 if _r == '' else _r)({order_code})"
    elif isinstance(var, LocalVariable):
        var_name = var.name
        subscripts = getattr(var, "subscripts", [])
        subs_code = gen_subscripts_tuple(subscripts, ctx)
        return f"_rt.m_next_local({var_base_expr(var_name, ctx)}, {subs_code})"
    else:
        # Fallback for MVariable or any other variable type - treat as local
        from m2py.asg.expressions import MVariable

        if isinstance(var, MVariable):
            var_name = var.name
            subscripts = getattr(var, "subscripts", [])
            subs_code = gen_subscripts_tuple(subscripts, ctx)
            return f"_rt.m_next_local({var_base_expr(var_name, ctx)}, {subs_code})"

    # Fallback to $ORDER-based implementation
    order_code = _gen_order(expr, ctx)
    return f"(lambda _r: -1 if _r == '' else _r)({order_code})"


INTRINSIC_GENERATORS["N"] = _gen_next
INTRINSIC_GENERATORS["NEXT"] = _gen_next


def _gen_increment(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $INCREMENT/$I/$INCR function.

    $INCREMENT atomically reads, adds, and writes back a variable value.
    If the variable is undefined, treats its current value as 0.

    Args:
        expr: MIntrinsicFunction ASG node with 1-2 arguments:
              - arg[0]: variable to increment (local, global, or naked global)
              - arg[1]: optional increment amount (defaults to 1)
        ctx: Generator context

    Returns:
        Python code calling m_increment() or m_increment_global()

    Examples:
        $I(X) → m_increment(_scope.get('X'), (), "1", _scope, 'X')
        $I(X,3) → m_increment(_scope.get('X'), (), m_str(3), _scope, 'X')
        $I(^G) → m_increment_global(_rt.globals, 'G', ())
        $I(^G(1),5) → m_increment_global(_rt.globals, 'G', (str(1),), m_str(5))
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.parser.textx_classes import LocalVariable

    args = getattr(expr, "arguments", [])
    var = args[0]

    # Get increment expression if provided
    if len(args) >= 2:
        incr_expr = f"m_str({generate_expr(args[1], ctx)})"
    else:
        incr_expr = '"1"'

    # Handle MIndirection: $I(@A) needs runtime resolution
    if isinstance(var, MIndirectionType):
        from m2py.codegen.indirection import generate_increment_indirection

        return generate_increment_indirection(var, ctx, incr_expr)

    # Generate subscript tuple
    subscripts = getattr(var, "subscripts", [])
    subscripts_tuple = gen_subscripts_tuple(subscripts, ctx)

    var_name = getattr(var, "name", "")

    if isinstance(var, LocalVariable):
        python_name = translate_name(var_name)

        # For TRAMPOLINE with state vars — static field, no scope dict needed
        if ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
            return f"m_increment(state.{python_name}, {subscripts_tuple}, {incr_expr})"

        # Dynamic locals or SIMPLE_FUNCTIONS — use scope dict
        scope = scope_dict_expr(ctx)
        return (
            f"m_increment({scope}.get({python_name!r}), "
            f"{subscripts_tuple}, {incr_expr}, {scope}, {python_name!r})"
        )
    elif isinstance(var, GlobalVariable):
        # Global variable: use backend's atomic incr()
        return (
            f"m_increment_global(_rt.globals, {var_name!r}, "
            f"{subscripts_tuple}, {incr_expr})"
        )
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve then increment
        return (
            f"(lambda _n, _s: m_increment_global(_rt.globals, _n, _s, {incr_expr}))"
            f"(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
    else:
        # Fallback — treat as local
        python_name = translate_name(var_name)
        scope = scope_dict_expr(ctx)
        return (
            f"m_increment({scope}.get({python_name!r}), "
            f"{subscripts_tuple}, {incr_expr}, {scope}, {python_name!r})"
        )


# $I is context-dependent: $I (no args) = $IO, $I(args) = $INCREMENT
# Since IntrinsicFunction always has args, mapping "I" here is correct —
# the no-args $I case is handled by the SpecialVariable path ($IO).
INTRINSIC_GENERATORS["I"] = _gen_increment
INTRINSIC_GENERATORS["INCR"] = _gen_increment
INTRINSIC_GENERATORS["INCREMENT"] = _gen_increment


def _gen_stack(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $STACK/$ST function.

    $STACK returns information about the call stack.
    - $STACK(-1): returns current stack depth
    - $STACK(n): returns frame type at level n ("DO", "$$", "XECUTE", etc.)
    - $STACK(n,"PLACE"): returns "LABEL+offset^ROUTINE"
    - $STACK(n,"MCODE"): returns MUMPS source line
    - $STACK(n,"ECODE"): returns error codes at that level

    Args:
        expr: MIntrinsicFunction ASG node with 1-2 arguments:
              - arg[0]: stack level (-1 for depth, 0-n for specific level)
              - arg[1]: optional info code ("PLACE", "MCODE", "ECODE")
        ctx: Generator context

    Returns:
        Python expression that evaluates to stack information
    """
    if not expr.arguments:
        # $STACK with no args - return depth (same as $STACK(-1))
        return "_rt.stack_function(-1)"

    level_expr = generate_expr(expr.arguments[0], ctx)

    if len(expr.arguments) >= 2:
        info_expr = generate_expr(expr.arguments[1], ctx)
        return f"_rt.stack_function(int(m_num({level_expr})), m_str({info_expr}))"
    else:
        return f"_rt.stack_function(int(m_num({level_expr})))"


INTRINSIC_GENERATORS["STACK"] = _gen_stack
INTRINSIC_GENERATORS["ST"] = _gen_stack


def _gen_zsystem(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZSYSTEM special variable.

    $ZSYSTEM returns the exit code from the last ZSYSTEM command
    as a string. No arguments.

    Returns:
        Python expression that evaluates to exit code string
    """
    return "m_str(_rt.zsystem_exit())"


INTRINSIC_GENERATORS["ZSYSTEM"] = _gen_zsystem
INTRINSIC_GENERATORS["ZSY"] = _gen_zsystem


def _gen_zsearch(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZSEARCH function.

    $ZSEARCH(pattern) searches for files matching pattern.
    Subsequent calls with "" return next match.

    Returns:
        Python expression that evaluates to matching file path
    """
    if expr.arguments:
        pattern_expr = generate_expr(expr.arguments[0], ctx)
        return f"_rt.zsearch(m_str({pattern_expr}))"
    return '_rt.zsearch("")'


INTRINSIC_GENERATORS["ZSEARCH"] = _gen_zsearch
INTRINSIC_GENERATORS["ZSE"] = _gen_zsearch


def _gen_zmessage(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZMESSAGE function.

    $ZMESSAGE(code) returns error message text for a YDB error code.

    Returns:
        Python expression that evaluates to error message string
    """
    if not expr.arguments:
        return '""'
    code_expr = generate_expr(expr.arguments[0], ctx)
    return f"m_zmessage({code_expr})"


INTRINSIC_GENERATORS["ZMESSAGE"] = _gen_zmessage
INTRINSIC_GENERATORS["ZM"] = _gen_zmessage


def _gen_zro(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZRO special variable.

    $ZRO returns routine search path.

    Returns:
        Python expression that evaluates to search path string
    """
    return "_rt.zro()"


INTRINSIC_GENERATORS["ZRO"] = _gen_zro
INTRINSIC_GENERATORS["ZROUTINES"] = _gen_zro


# =============================================================================
# IRIS/Caché Vendor Functions
# =============================================================================


def _gen_replace(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $REPLACE function (IRIS/Caché).

    $REPLACE(string, search, replace[, start[, count[, case]]])

    Args:
        expr: MIntrinsicFunction ASG node with 3-6 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_replace()
    """
    args = getattr(expr, "arguments", [])
    if len(args) < 3:
        return '""'

    str_expr = generate_expr(args[0], ctx)
    search_expr = generate_expr(args[1], ctx)
    replace_expr = generate_expr(args[2], ctx)

    parts = [f"m_str({str_expr})", f"m_str({search_expr})", f"m_str({replace_expr})"]

    if len(args) >= 4:
        parts.append(f"int(m_num({generate_expr(args[3], ctx)}))")
    if len(args) >= 5:
        parts.append(f"int(m_num({generate_expr(args[4], ctx)}))")
    if len(args) >= 6:
        parts.append(f"int(m_num({generate_expr(args[5], ctx)}))")

    return f"m_replace({', '.join(parts)})"


INTRINSIC_GENERATORS["REPLACE"] = _gen_replace


def _gen_zboolean(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZBOOLEAN/$ZB function (IRIS/Caché).

    $ZBOOLEAN(arg1, arg2, op) — 16-operation bitwise Boolean.

    Args:
        expr: MIntrinsicFunction ASG node with 3 arguments
        ctx: Generator context

    Returns:
        Python expression calling m_zboolean()
    """
    args = getattr(expr, "arguments", [])
    if len(args) < 3:
        return '""'

    arg1 = generate_expr(args[0], ctx)
    arg2 = generate_expr(args[1], ctx)
    op = generate_expr(args[2], ctx)

    return f"m_zboolean(m_str({arg1}), m_str({arg2}), int(m_num({op})))"


INTRINSIC_GENERATORS["ZBOOLEAN"] = _gen_zboolean
INTRINSIC_GENERATORS["ZB"] = _gen_zboolean


def _gen_zu(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZU function (IRIS/Caché).

    $ZU(code[, args...]) — utility dispatch.

    Args:
        expr: MIntrinsicFunction ASG node with 1+ arguments
        ctx: Generator context

    Returns:
        Python expression calling m_zu()
    """
    args = getattr(expr, "arguments", [])
    if not args:
        return '""'

    code_expr = generate_expr(args[0], ctx)
    extra_args = ", ".join(f"m_str({generate_expr(a, ctx)})" for a in args[1:])

    if extra_args:
        return f"m_zu(int(m_num({code_expr})), {extra_args})"
    return f"m_zu(int(m_num({code_expr})))"


INTRINSIC_GENERATORS["ZU"] = _gen_zu
INTRINSIC_GENERATORS["ZUTIL"] = _gen_zu


def _gen_zf(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZF function (IRIS/Caché).

    $ZF(code[, args...]) — subprocess/VMS function dispatch.

    Args:
        expr: MIntrinsicFunction ASG node with 1+ arguments
        ctx: Generator context

    Returns:
        Python expression calling m_zf()
    """
    args = getattr(expr, "arguments", [])
    if not args:
        return '""'

    code_expr = generate_expr(args[0], ctx)
    extra_args = ", ".join(f"m_str({generate_expr(a, ctx)})" for a in args[1:])

    if extra_args:
        return f"m_zf(int(m_num({code_expr})), {extra_args})"
    return f"m_zf(int(m_num({code_expr})))"


INTRINSIC_GENERATORS["ZF"] = _gen_zf


def _gen_view_func(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $VIEW/$V function.

    Stub — returns "" for all arguments.
    """
    return "m_view_func_stub()"


INTRINSIC_GENERATORS["VIEW"] = _gen_view_func
INTRINSIC_GENERATORS["V"] = _gen_view_func


def _gen_zconvert(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZCONVERT/$ZCVT function (IRIS/Caché).

    $ZCONVERT(string, mode) — string case conversion.
    mode: "U" (upper), "L" (lower), "T" (title)

    Falls through to m_zconvert() helper.
    """
    args = getattr(expr, "arguments", [])
    if len(args) < 2:
        return '""'

    str_expr = generate_expr(args[0], ctx)
    mode_expr = generate_expr(args[1], ctx)

    return f"m_zconvert(m_str({str_expr}), m_str({mode_expr}))"


INTRINSIC_GENERATORS["ZCONVERT"] = _gen_zconvert
INTRINSIC_GENERATORS["ZCVT"] = _gen_zconvert


# =============================================================================
# IRIS/Caché Special Variables as No-Args Intrinsic Functions
# =============================================================================
# The parser's SVARNAME regex doesn't include IRIS-specific SVNs like $ZV, $ZR,
# $ZA, $NAMESPACE. These get parsed as IntrinsicFunctionNoArgs. We handle them
# here in the dispatch table so they work from both paths.


def _gen_svn_zversion(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZVERSION/$ZV as no-args intrinsic function."""
    return "_rt.zversion()"


INTRINSIC_GENERATORS["ZVERSION"] = _gen_svn_zversion
INTRINSIC_GENERATORS["ZV"] = _gen_svn_zversion


def _gen_svn_za(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZA as no-args intrinsic function."""
    return "str(_rt.za())"


INTRINSIC_GENERATORS["ZA"] = _gen_svn_za


def _gen_svn_zreference(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZREFERENCE/$ZR as no-args intrinsic function."""
    return "_rt.zreference()"


INTRINSIC_GENERATORS["ZREFERENCE"] = _gen_svn_zreference
INTRINSIC_GENERATORS["ZR"] = _gen_svn_zreference


def _gen_svn_namespace(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$NAMESPACE/$NSPACE as no-args intrinsic function."""
    return "_rt.namespace()"


INTRINSIC_GENERATORS["NAMESPACE"] = _gen_svn_namespace
INTRINSIC_GENERATORS["NSPACE"] = _gen_svn_namespace


# --- US5 ISV shims (parsed as IntrinsicFunctionNoArgs when not in SVARNAME) ---


def _gen_svn_zsource(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZSOURCE/$ZSO as no-args intrinsic function."""
    return "_rt.zsource()"


INTRINSIC_GENERATORS["ZSOURCE"] = _gen_svn_zsource
INTRINSIC_GENERATORS["ZSO"] = _gen_svn_zsource


def _gen_svn_zerr(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZERR as no-args intrinsic function (non-standard abbreviation of $ZERROR)."""
    return "_rt.zerror()"


INTRINSIC_GENERATORS["ZERR"] = _gen_svn_zerr


# =============================================================================
# Phase 10: Vendor Function Aliases & Stubs (024-vista-transpilation-fixes)
# =============================================================================


# --- T053: Function Aliases ---

# $ZS → alias for $ZSEARCH (6 routines: ZBCK, ZRODSM, ZRRBAC1, ZTMS, ZU, ZUGTM)
# NOTE: $ZS as an SVN is $ZSTATUS (handled in _generate_special_variable()).
# When $ZS is used with arguments (i.e., as a function), INTRINSIC_GENERATORS
# takes priority, so this correctly dispatches $ZS(x) → ZSEARCH.
INTRINSIC_GENERATORS["ZS"] = _gen_zsearch

# $ZCHAR/$ZCH → alias for $CHAR (DSM/MSM vendors)
INTRINSIC_GENERATORS["ZCHAR"] = _gen_char
INTRINSIC_GENERATORS["ZCH"] = _gen_char


def _gen_zprevious(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZPREVIOUS/$ZP function.

    $ZPREVIOUS(var) is equivalent to $ORDER(var,-1).
    We delegate to _gen_order after injecting a -1 direction argument.
    """
    from m2py.asg.expressions import MLiteral

    args = list(getattr(expr, "arguments", []))
    if args:
        # If no direction argument, inject -1
        if len(args) < 2:
            neg1 = MLiteral(value="-1", literal_type=LiteralType.INTEGER)
            args.append(neg1)
        # Create a shallow copy of expr with modified arguments
        import copy

        modified = copy.copy(expr)
        modified.arguments = args
        return _gen_order(modified, ctx)
    return '""'


INTRINSIC_GENERATORS["ZPREVIOUS"] = _gen_zprevious
# $ZP as function → $ZPREVIOUS. As SVN, $ZP is $ZPOSITION (handled elsewhere).
INTRINSIC_GENERATORS["ZP"] = _gen_zprevious


def _gen_svn_zjob_func(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZJOB as no-args intrinsic function (returns last JOB'd process PID)."""
    return "_rt.zjob()"


INTRINSIC_GENERATORS["ZJOB"] = _gen_svn_zjob_func
INTRINSIC_GENERATORS["ZJ"] = _gen_svn_zjob_func


# IRIS $LIST functions — stub returning ""
def _gen_list_stub(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Stub for IRIS $LIST/$LISTBUILD/$LISTGET etc.

    These are IRIS-specific serialization functions with no Python equivalent.
    Returns "" for all invocations.
    """
    return '""'


INTRINSIC_GENERATORS["LIST"] = _gen_list_stub
INTRINSIC_GENERATORS["LI"] = _gen_list_stub
INTRINSIC_GENERATORS["LISTBUILD"] = _gen_list_stub
INTRINSIC_GENERATORS["LB"] = _gen_list_stub
INTRINSIC_GENERATORS["LISTGET"] = _gen_list_stub
INTRINSIC_GENERATORS["LG"] = _gen_list_stub
INTRINSIC_GENERATORS["LISTLENGTH"] = _gen_list_stub
INTRINSIC_GENERATORS["LL"] = _gen_list_stub


# --- T054: $ZC/$ZCALL stubs (DSM/VMS — 33 routines) ---


def _gen_zcall(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZC/$ZCALL function (DSM/VMS).

    $ZCALL invokes external library routines — not available in Python.
    Returns "" and emits a runtime warning via m_zcall_stub().
    """
    args = getattr(expr, "arguments", [])
    arg_exprs = ", ".join(f"m_str({generate_expr(a, ctx)})" for a in args)
    if arg_exprs:
        return f'm_zcall_stub("$ZCALL", {arg_exprs})'
    return 'm_zcall_stub("$ZCALL")'


INTRINSIC_GENERATORS["ZC"] = _gen_zcall
INTRINSIC_GENERATORS["ZCALL"] = _gen_zcall


# --- T055: $ZHOROLOG/$ZH function + SVN ---


def _gen_zhorolog(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $ZHOROLOG/$ZH function.

    $ZHOROLOG returns a high-resolution timestamp (microseconds since epoch).
    In YDB, $ZH with no args returns "$ZHOROLOG" as an ISV.
    With args, it's the function form.

    We return str(time.time()) for both cases since the function is typically
    called with zero args anyway.
    """
    return "str(int(time.time() * 1000000))"


INTRINSIC_GENERATORS["ZHOROLOG"] = _gen_zhorolog
INTRINSIC_GENERATORS["ZH"] = _gen_zhorolog


# --- T056: Remaining vendor function stubs ---


def _gen_zio(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZIO — current I/O device. Alias for $IO."""
    return "_rt.io()"


INTRINSIC_GENERATORS["ZIO"] = _gen_zio


def _gen_pd(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$PD — IRIS padding function. Returns "1" (enabled)."""
    return '"1"'


INTRINSIC_GENERATORS["PD"] = _gen_pd


def _gen_zdev(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZDEV — DSM device info. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZDEV"] = _gen_zdev


def _gen_zorder(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZO/$ZORDER — DSM/MSM order variant. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZO"] = _gen_zorder
INTRINSIC_GENERATORS["ZORDER"] = _gen_zorder


def _gen_ztimestamp(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZTIMESTAMP — YDB $H-format UTC timestamp.

    Returns "days,seconds" in $HOROLOG format based on UTC time.
    """
    return "_rt.horolog()"


INTRINSIC_GENERATORS["ZTIMESTAMP"] = _gen_ztimestamp
INTRINSIC_GENERATORS["ZTS"] = _gen_ztimestamp
INTRINSIC_GENERATORS["ZTSTAMP"] = _gen_ztimestamp
INTRINSIC_GENERATORS["ZUT"] = _gen_ztimestamp


def _gen_ztrnlnm(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZTRNLNM — translate logical name (VMS/YDB).

    $ZTRNLNM(name) returns the value of an environment variable.
    Maps to os.environ.get(name, "").
    """
    args = getattr(expr, "arguments", [])
    if args:
        name_expr = generate_expr(args[0], ctx)
        return f"_rt_os_environ_get(m_str({name_expr}))"
    return '""'


INTRINSIC_GENERATORS["ZTRNLNM"] = _gen_ztrnlnm


def _gen_zname(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZN/$ZNAME — routine name function. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZN"] = _gen_zname
INTRINSIC_GENERATORS["ZNAME"] = _gen_zname


def _gen_zclose(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZCLOSE — close device. Returns "0" (success)."""
    return '"0"'


INTRINSIC_GENERATORS["ZCLOSE"] = _gen_zclose


def _gen_zgetjpi(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZGETJPI — get job/process info (YDB).

    When first arg is "" and second arg is "ISPROCALIVE", checks if
    current process is alive. Otherwise returns stub.
    """
    args = getattr(expr, "arguments", [])
    if len(args) >= 2:
        pid_expr = generate_expr(args[0], ctx)
        item_expr = generate_expr(args[1], ctx)
        return f"m_zgetjpi(m_str({pid_expr}), m_str({item_expr}))"
    if len(args) == 1:
        pid_expr = generate_expr(args[0], ctx)
        return f'm_zgetjpi(m_str({pid_expr}), "")'
    return 'm_zgetjpi("", "")'


INTRINSIC_GENERATORS["ZGETJPI"] = _gen_zgetjpi


def _gen_zios(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZIOS — I/O status. Returns "0" (no error)."""
    return '"0"'


INTRINSIC_GENERATORS["ZIOS"] = _gen_zios


def _gen_zver(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZVER — version string (MSM). Returns empty string."""
    return '""'


INTRINSIC_GENERATORS["ZVER"] = _gen_zver


def _gen_zparse(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZPARSE — file path parsing (YDB/GT.M).

    $ZPARSE(expr[,item[,default[,type]]]) parses file paths.
    Maps to os.path operations for basic usage.
    """
    args = getattr(expr, "arguments", [])
    if not args:
        return '""'
    path_expr = generate_expr(args[0], ctx)
    if len(args) >= 2:
        item_expr = generate_expr(args[1], ctx)
        return f"m_zparse(m_str({path_expr}), m_str({item_expr}))"
    return f"m_zparse(m_str({path_expr}))"


INTRINSIC_GENERATORS["ZPARSE"] = _gen_zparse


def _gen_zlength(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZL/$ZLENGTH — byte length of string.

    $ZLENGTH(string) returns the byte length (not character length).
    """
    args = getattr(expr, "arguments", [])
    if args:
        str_expr = generate_expr(args[0], ctx)
        return f'str(len(m_str({str_expr}).encode("utf-8")))'
    return '"0"'


INTRINSIC_GENERATORS["ZL"] = _gen_zlength
INTRINSIC_GENERATORS["ZLENGTH"] = _gen_zlength


def _gen_roles(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ROLES — IRIS security roles. Returns "%All"."""
    return '"%All"'


INTRINSIC_GENERATORS["ROLES"] = _gen_roles


def _gen_zdefnsp(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZDEFNSP/$ZNSPACE — default namespace. Returns "VISTA"."""
    return '"VISTA"'


INTRINSIC_GENERATORS["ZDEFNSP"] = _gen_zdefnsp
INTRINSIC_GENERATORS["ZNSPACE"] = _gen_zdefnsp


def _gen_number(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$NUM/$NUMBER — format number. Delegates to m_num for canonical form."""
    args = getattr(expr, "arguments", [])
    if args:
        num_expr = generate_expr(args[0], ctx)
        return f"m_str(m_num({num_expr}))"
    return '"0"'


INTRINSIC_GENERATORS["NUM"] = _gen_number
INTRINSIC_GENERATORS["NUMBER"] = _gen_number


def _gen_zdateh(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZDATEH — date to $H conversion. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZDATEH"] = _gen_zdateh


def _gen_zbitand(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZBITAND — bitwise AND on bit strings.

    $ZBITAND(str1, str2) performs bitwise AND.
    """
    args = getattr(expr, "arguments", [])
    if len(args) >= 2:
        s1 = generate_expr(args[0], ctx)
        s2 = generate_expr(args[1], ctx)
        return f"m_zbitand(m_str({s1}), m_str({s2}))"
    return '""'


INTRINSIC_GENERATORS["ZBITAND"] = _gen_zbitand


def _gen_zdatetime(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZDATETIME — date/time formatting. Stub returning empty string."""
    args = getattr(expr, "arguments", [])
    if args:
        h_expr = generate_expr(args[0], ctx)
        return f'm_zcall_stub("$ZDATETIME", m_str({h_expr}))'
    return '""'


INTRINSIC_GENERATORS["ZDATETIME"] = _gen_zdatetime
INTRINSIC_GENERATORS["ZDT"] = _gen_zdatetime


def _gen_eref(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$EREF — extended reference. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["EREF"] = _gen_eref


def _gen_zos(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZOS — operating system info. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZOS"] = _gen_zos


def _gen_zdevspeed(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$zdevspeed — device speed. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZDEVSPEED"] = _gen_zdevspeed


def _gen_zeo(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZEO — end of file (DSM variant of $ZEOF). Returns "0"."""
    return '"0"'


INTRINSIC_GENERATORS["ZEO"] = _gen_zeo


def _gen_zwa(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZWA — write-after count. Returns "0"."""
    return '"0"'


INTRINSIC_GENERATORS["ZWA"] = _gen_zwa


def _gen_zmode(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZMODE — process mode. Returns "OTHER"."""
    return '"OTHER"'


INTRINSIC_GENERATORS["ZMODE"] = _gen_zmode


def _gen_zuci(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZUCI — UCI (User Class Identification). Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZUCI"] = _gen_zuci


def _gen_zcmd(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZCMD — last command. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZCMD"] = _gen_zcmd


def _gen_zgd(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """$ZGD — global directory. Stub returning empty string."""
    return '""'


INTRINSIC_GENERATORS["ZGD"] = _gen_zgd

# Additional vendor aliases discovered during validation:
# $ZEXTRACT/$ZE → alias for $EXTRACT (DSM/IRIS)
INTRINSIC_GENERATORS["ZEXTRACT"] = _gen_extract
INTRINSIC_GENERATORS["ZE"] = _gen_extract

# $ZLENGTH as function already registered above,
# but $ZL also used for $ZLENGTH (already registered)
