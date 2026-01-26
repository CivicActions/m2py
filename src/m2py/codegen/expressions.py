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
    MExternalFunction,
    MExtrinsicFunction,
    MGlobal,
    MIndirection,
    MIntrinsicFunction,
    MLiteral,
    MPatternMatch,
    MSelectArg,
    MSpecialVariable,
    MStructuredSystemVariable,
    MUnaryOp,
    MVariable,
)
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.names import translate_name
from m2py.parser.textx_classes import GlobalVariable, NakedGlobal

if TYPE_CHECKING:
    from m2py.codegen.routine import GeneratorContext


# =============================================================================
# Limitation Constants (Spec 014)
# =============================================================================

# ANSI Standard Library routines (LIM-014)
# STRING and CHARACTER libraries have zero VistA usage - all functions blocked.
# MATH library has basic functions implemented (Spec 013), others blocked.
ANSI_LIBRARY_ROUTINES_BLOCKED: frozenset[str] = frozenset({"STRING", "CHARACTER"})

# Implemented MATH library functions (Spec 013 Phase 13)
# These are the functions defined in m2py/runtime/routines/MATH.py
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
# These are implementation-defined per FR-017 and parsed but not implemented.
# Codegen raises NotImplementedError for these functions.
Z_FUNCTIONS_UNIMPLEMENTED: frozenset[str] = frozenset({"ZDATE", "ZMESSAGE", "ZWIDTH"})


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

    # LIM-015: Unimplemented Z-functions
    if func_name in Z_FUNCTIONS_UNIMPLEMENTED:
        raise NotImplementedError(f"LIM-015: ${expr.name} function not supported")

    raise NotImplementedError(f"Intrinsic function ${expr.name} not yet implemented")


def generate_expr(
    expr: MExpr, ctx: "GeneratorContext", if_condition: bool = False
) -> str:
    """Generate Python expression from ASG expression node.

    Dispatches based on expression type:
    - MLiteral → literal value
    - MVariable → translated variable name
    - MBinaryOp → operation with coercion
    - MUnaryOp → unary operation
    - MExtrinsicFunction → function call with $TEST save/restore
    - MIntrinsicFunction → intrinsic function dispatch table
    - MIndirection → runtime indirection call (Spec 012)

    Args:
        expr: ASG expression node
        ctx: Generator context (for name translation, etc.)
        if_condition: If True, this expression is an IF condition, which
                     affects how argument indirection handles empty strings (T052)

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
    # Spec 015: External C functions ($&name, $&package.name)
    elif isinstance(expr, MExternalFunction):
        return _generate_external_function(expr, ctx)
    elif isinstance(expr, MSpecialVariable):
        return _generate_special_variable(expr, ctx)
    # Spec 010: Dispatch all intrinsic functions through unified handler
    # This handles both MIntrinsicFunction ASG nodes and parser textx classes
    # (IntrinsicFunction, TextFunction, SelectFunction) which all inherit
    # from MIntrinsicFunction.
    elif isinstance(expr, MIntrinsicFunction):
        return generate_intrinsic_function(expr, ctx)
    # Spec 011 Phase 12: Pattern match expressions
    elif isinstance(expr, MPatternMatch):
        return _generate_pattern_match(expr, ctx)
    # Spec 012 Phase 3 (T016): Handle name indirection (@VAR)
    elif isinstance(expr, MIndirection):
        return _generate_indirection(expr, ctx, if_condition=if_condition)
    # Spec 013 Phase 16 (FR-029): Handle structured system variables (^$GLOBAL etc)
    elif isinstance(expr, MStructuredSystemVariable):
        return _generate_ssvn(expr, ctx)
    else:
        raise NotImplementedError(f"Unsupported expression type: {type(expr).__name__}")


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

    Spec 017 (T014): For routines with argumentless KILL/NEW in TRAMPOLINE strategy,
    use state._locals dict for dynamic variable access.

    Args:
        var: MVariable node
        ctx: Generator context

    Returns:
        Python expression string for the variable reference
    """
    # Translate name to valid Python identifier
    python_name = translate_name(var.name)

    # Spec 017 (T014): Dynamic locals for argumentless KILL/NEW support
    if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
        if var.subscripts:
            # Generate subscript expressions
            subscript_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]
            # Access MArray from _locals dict, default to empty MArray
            base = f"state._locals.get({python_name!r}, MArray())"
            return f"{base}.get({', '.join(subscript_exprs)})"
        else:
            # T075h: Simple variable - get MArray from _locals dict, access .value
            # state._locals stores MArray objects for SET consistency, so we need
            # to get the MArray (or create empty one) and return its .value
            # This ensures S X=Y correctly copies Y's value, not the MArray object
            return f"state._locals.get({python_name!r}, MArray()).value"

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


def _generate_global_variable(var: MGlobal, ctx: "GeneratorContext") -> str:
    """Generate Python expression for global variable READ.

    Spec 009 (T027): Generate _rt.globals.get() call for global variable reads.

    Args:
        var: MGlobal or GlobalVariable node (GlobalVariable inherits from MGlobal)
        ctx: Generator context

    Returns:
        Python expression string: _rt.globals.get("NAME", (subscripts,)) or ""

    The generated code reads from the global storage backend and returns
    empty string for undefined globals (MUMPS implicit $GET semantics).

    Raises:
        NotImplementedError: For extended globals (^|env| or ^[gld]) which have
        an environment field - these are not yet implemented.
    """
    # Check for extended global references (not yet supported)
    if hasattr(var, "environment") and var.environment is not None:
        raise NotImplementedError(
            f"Extended global references not implemented: {type(var).__name__}"
        )

    # Get global name (without caret)
    global_name = var.name

    # Generate subscript expressions
    # DO NOT wrap in str() - let the runtime's _canonicalize_subscript handle
    # the type distinction. Numeric literals (Decimal, int, float) should
    # canonicalize differently than string literals.
    # Example: Decimal("1.0") → "1" (numeric), but "1.0" → "1.0" (string)
    if var.subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]
        # Format as tuple: (sub1, sub2, ...) or (sub1,) for single element
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
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
    # DO NOT wrap in str() - let the runtime's _canonicalize_subscript handle it
    if var.subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]
        # Format as tuple: (sub1, sub2, ...) or (sub1,) for single element
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

    # Spec 009 (T028): Return empty string for undefined globals
    # resolve_naked returns (name, subscripts), use * to unpack into get()
    return f"(_rt.globals.get(*_rt.globals.resolve_naked({subscripts_tuple})) or '')"


def _generate_ssvn(ssvn: MStructuredSystemVariable, ctx: "GeneratorContext") -> str:
    """Generate Python expression for MUMPS structured system variable (SSVN).

    Spec 013 Phase 16 (FR-029): Generates calls to database abstraction layer
    for SSVNs ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE.

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
        # ^$SYSTEM returns implementation info - return constant
        return "'m2py'"
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
    # Spec 013 FR-015: Returns current transaction depth (0 = no transaction)
    if name in ("TLEVEL", "TL"):
        return "_rt.tlevel()"

    # $ZJOB / $ZJ - last JOB'd process ID
    # Spec 013 Phase 11: Returns PID of last process started by JOB command
    if name in ("ZJOB", "ZJ"):
        return "_rt.zjob()"

    # $ECODE / $EC - error code list
    # Spec 013 Phase 12 (FR-026): Comma-delimited list of active error codes
    if name in ("ECODE", "EC"):
        return "_rt.ecode()"

    # $ETRAP / $ET - error trap code
    # Spec 013 Phase 12 (FR-026): M code to execute on error
    if name in ("ETRAP", "ET"):
        return "_rt.etrap()"

    # $ZERROR / $ZE - application error message
    # Spec 013 Phase 12 (FR-045): Application-supplied error message text
    if name in ("ZERROR", "ZE"):
        return "_rt.zerror()"

    # Add other special variables as needed
    raise NotImplementedError(f"Special variable ${var.name} not yet supported")


def _generate_indirection(
    ind: MIndirection, ctx: "GeneratorContext", if_condition: bool = False
) -> str:
    """Generate Python expression for name indirection (@VAR).

    Spec 012 Phase 3 (T016): Dispatches to codegen/indirection.py for
    runtime indirection handling.

    Handles:
    - Simple NAME: @X → _rt.get_var(_scope.get("X", ""), _scope)
    - Multi-level NAME: @@X → _rt.resolve_indirection("X", 2, _scope)
    - With subscripts: @NAME@(1,2) → _rt.get_var(f'{...}(1,2)', _scope)
    - ARGUMENT type: @A in IF → evaluates value of A as expression

    Args:
        ind: MIndirection ASG node
        ctx: Generator context
        if_condition: If True, this is an IF condition - affects T052 empty handling

    Returns:
        Python expression string
    """
    from m2py.asg.enums import IndirectionType
    from m2py.codegen.indirection import (
        generate_name_indirection,
        generate_argument_indirection,
    )

    # Dispatch based on indirection type
    if ind.indirection_type == IndirectionType.ARGUMENT:
        return generate_argument_indirection(ind, ctx, if_condition=if_condition)
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
        return f"(int(m_num({left}) / m_num({right})))"
    elif op.operator == "#":
        # Modulo in MUMPS - uses floor division semantics (unlike Decimal %)
        return f"m_mod({left}, {right})"
    elif op.operator == "**":
        # Exponentiation in MUMPS - base ** exponent
        return f"(m_num({left}) ** m_num({right}))"
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
    elif op.operator == "?":
        # Pattern match: A?pattern returns 1 if A matches pattern
        return f"m_pattern_match({left}, {right})"
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
        # Logical NOT in MUMPS - must return int (0/1), not Python bool
        return f"int(not m_truth({operand}))"
    else:
        raise NotImplementedError(f"Unsupported unary operator: {op.operator}")


def _generate_pattern_match(expr: MPatternMatch, ctx: "GeneratorContext") -> str:
    """Generate Python pattern match expression from MPatternMatch.

    Spec 011 Phase 12: Pattern match operator.
    Spec 015 Phase 3: Uses pre-compiled regex for direct patterns to avoid
    runtime re-compilation.

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
        # Direct pattern without compiled regex (shouldn't happen normally)
        # Fall back to runtime helper
        pattern = repr(expr.pattern)
        result = f"m_pattern_match({subject}, {pattern})"

    # Handle negated pattern match ('?)
    if expr.operator == "'?":
        return f"int(not {result})"
    return result


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

        # Spec 013 Phase 13: Check for bundled routines first (e.g., MATH for $$%SIN^MATH)
        # Bundled routines are in m2py.runtime.routines package
        bundled_routines = {"MATH"}  # Add more as needed

        # T068-T070: Translate routine name to valid Python module name
        # %ROUTINE becomes _pct_ROUTINE for Python import compatibility
        python_module_name = translate_name(routine_name)

        if routine_name in bundled_routines:
            # Import from bundled routines package
            ctx.emitter.line(f"from m2py.runtime.routines import {routine_name}")
            # Bundled routines don't need name translation (they're Python modules)
            module_ref = routine_name
        else:
            # T044: Generate import statement for external routine
            ctx.emitter.line(f"import {python_module_name}")
            module_ref = python_module_name

        # Translate label name to Python function name
        func_name = translate_name(label_name)

        # T045-T046: Generate call via _call_extrinsic with module prefix and _scope
        # The _call_extrinsic helper provides $TEST save/restore and by-ref unpacking
        # Phase 13 (T081): Pass _rt as first parameter
        if args:
            return f"_call_extrinsic(_rt, {module_ref}.{func_name}, {args}, _scope=_scope{byref_param})"
        else:
            return f"_call_extrinsic(_rt, {module_ref}.{func_name}, _scope=_scope{byref_param})"

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

    # Generate: _call_extrinsic(_rt, FUNC, arg1, arg2, _scope=_scope)
    # Phase 13 (T081): Pass _rt as first parameter
    # T076-T078: Always pass _scope for cross-routine variable visibility
    if args:
        return f"_call_extrinsic(_rt, {func_name}, {args}, _scope=_scope)"
    else:
        return f"_call_extrinsic(_rt, {func_name}, _scope=_scope)"


def _generate_external_function(
    expr: MExternalFunction, ctx: "GeneratorContext"
) -> str:
    """Generate Python call for external C function ($&name, $&package.name).

    Spec 015: External C functions call native code linked into the MUMPS runtime.
    These are implementation-specific and cannot be directly transpiled to Python.

    Examples:
        $&RAND(1)                          - Simple external function
        $&ydbposix.signalval("SIGTERM",.x) - Package-qualified external function

    For Python transpilation, these raise NotImplementedError since they require
    native C bindings that don't exist in the pure Python runtime.

    Args:
        expr: MExternalFunction node with package, name, and arguments
        ctx: Generator context

    Raises:
        NotImplementedError: External C functions are not supported in Python transpilation
    """
    # Build function identifier for error message
    if expr.package:
        func_id = f"$&{expr.package}.{expr.name}"
    else:
        func_id = f"$&{expr.name}"

    raise NotImplementedError(
        f"External C function '{func_id}' not supported. "
        f"External functions ($&) call native C code linked into the MUMPS runtime "
        f"and cannot be transpiled to pure Python."
    )


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
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.parser.textx_classes import LocalVariable

    # Get first argument (the variable to check)
    args = getattr(expr, "arguments", [])
    if not args:
        # No argument - return 0 for undefined
        return "0"

    var = args[0]

    # Handle MIndirection: $D(@A@(1)) needs runtime resolution
    if isinstance(var, MIndirectionType):
        # For indirection, we need to use _rt.get_data which resolves the variable name at runtime
        from m2py.codegen.indirection import _count_indirection_levels

        levels, inner_expr = _count_indirection_levels(var)

        # Build subscript expressions from name_indirection_subscripts if present
        if var.name_indirection_subscripts:
            all_subs = []
            for sub_list in var.name_indirection_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                all_subs.extend(sub_exprs)
            # Use single quotes for the f-string so double-quoted strings inside work
            if len(all_subs) == 1:
                subs_fstr = f"f'({{{all_subs[0]}}})'"
            else:
                subs_parts = ", ".join(f"{{{s}}}" for s in all_subs)
                subs_fstr = f"f'({subs_parts})'"
        else:
            # No subscripts - use empty string, not "()"
            subs_fstr = "''"

        # Generate the variable name resolution
        # Must distinguish between local variables (use get_indirection_source)
        # and global variables (read value directly)
        from m2py.asg.expressions import MVariable
        from m2py.parser.textx_classes import LocalVariable as MLocalVariable

        if isinstance(inner_expr, GlobalVariable):
            # Global variable as indirection source: @^V reads ^V value
            global_name = inner_expr.name
            # Read the global variable value - this returns the string to use as var name
            name_expr = f'str((_rt.globals.get({global_name!r}, ()) or ""))'
        elif isinstance(inner_expr, (MVariable, MLocalVariable)):
            base_name = inner_expr.name
            python_name = translate_name(base_name)
            if levels > 1:
                # Multi-level indirection: @@X
                if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                    name_expr = f'str(_rt.resolve_indirection("{base_name}", {levels}, state._locals))'
                elif ctx.strategy == GotoStrategy.TRAMPOLINE:
                    # Python locals - build a temporary scope dict with the variable
                    name_expr = f'str(_rt.resolve_indirection("{base_name}", {levels}, {{"{base_name}": MArray(value={python_name})}}))'
                else:
                    name_expr = (
                        f'str(_rt.resolve_indirection("{base_name}", {levels}, _scope))'
                    )
            else:
                # Single-level indirection: @X
                if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                    name_expr = (
                        f'_rt.get_indirection_source("{base_name}", state._locals)'
                    )
                elif ctx.strategy == GotoStrategy.TRAMPOLINE:
                    # Python locals - use the variable directly as string
                    name_expr = f"str({python_name})"
                else:
                    name_expr = f'_rt.get_indirection_source("{base_name}", _scope)'
        else:
            name_expr_base = generate_expr(inner_expr, ctx)
            name_expr = f"str({name_expr_base})"

        # Use _rt.get_data which handles indirected variable names
        return f"_rt.get_data({name_expr} + {subs_fstr}, _scope)"

    # Generate subscript tuple for non-indirection cases
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
    else:
        subscripts_tuple = "()"

    var_name = getattr(var, "name", "")

    # Check if it's a local or global variable
    if isinstance(var, LocalVariable):
        # Spec 017 (T014): Use state._locals for dynamic locals in TRAMPOLINE
        python_name = translate_name(var_name)
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            return f"m_data(state._locals.get({python_name!r}, MArray()), {subscripts_tuple})"
        return f"m_data(_scope.get({python_name!r}, MArray()), {subscripts_tuple})"
    elif isinstance(var, GlobalVariable):
        # Global variable: m_data_global(_rt.globals, 'NAME', subscripts)
        return f"m_data_global(_rt.globals, {var_name!r}, {subscripts_tuple})"
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve then call m_data_global
        # Spec 014 (T061): Naked references in $DATA
        return (
            f"(lambda _n, _s: m_data_global(_rt.globals, _n, _s))"
            f"(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
    else:
        # Fallback for any other variable type - treat as local
        # Spec 017 (T014): Use state._locals for dynamic locals in TRAMPOLINE
        python_name = translate_name(var_name)
        if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
            return f"m_data(state._locals.get({python_name!r}, MArray()), {subscripts_tuple})"
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
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
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
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve then call m_get_global
        # Spec 014 (T061): Naked references in $GET
        return (
            f"(lambda _n, _s: m_get_global(_rt.globals, _n, _s, {default_code}))"
            f"(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
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
        $O(@X) → _rt.get_order(X_value, _scope, direction)
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
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

    # Handle MIndirection: $O(@X) needs runtime resolution
    if isinstance(var, MIndirectionType):
        from m2py.codegen.indirection import _count_indirection_levels

        levels, inner_expr = _count_indirection_levels(var)

        # Build subscript expressions from name_indirection_subscripts if present
        # For $O(@X@(1)), we need to append the extra subscripts to the resolved name
        if var.name_indirection_subscripts:
            all_subs = []
            for sub_list in var.name_indirection_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                all_subs.extend(sub_exprs)
            # Build f-string to append subscripts: f'({sub1}, {sub2})'
            if len(all_subs) == 1:
                subs_fstr = f"f'({{{all_subs[0]}}})'"
            else:
                subs_parts = ", ".join(f"{{{s}}}" for s in all_subs)
                subs_fstr = f"f'({subs_parts})'"
            # We'll append these subscripts to the resolved name
            append_subs = f" + {subs_fstr}"
        else:
            append_subs = ""

        # Generate the variable name resolution
        from m2py.asg.expressions import MVariable
        from m2py.parser.textx_classes import LocalVariable as MLocalVariable

        if isinstance(inner_expr, GlobalVariable):
            # Global variable as indirection source: @^V reads ^V value
            global_name = inner_expr.name
            name_expr = f'str((_rt.globals.get({global_name!r}, ()) or ""))'
        elif isinstance(inner_expr, (MVariable, MLocalVariable)):
            base_name = inner_expr.name
            # Check if inner_expr has subscripts (e.g., @@@A(0) -> A(0), not A)
            inner_subscripts = getattr(inner_expr, "subscripts", [])
            if inner_subscripts:
                # Build the subscripted variable name at runtime
                # For @@@A(0): base_name="A", subscripts=[0] -> "A(0)"
                sub_exprs = [generate_expr(sub, ctx) for sub in inner_subscripts]
                if len(sub_exprs) == 1:
                    full_name_expr = f'f"{base_name}({{{sub_exprs[0]}}})"'
                else:
                    subs_parts = ",".join(f"{{{s}}}" for s in sub_exprs)
                    full_name_expr = f'f"{base_name}({subs_parts})"'
            else:
                full_name_expr = f'"{base_name}"'

            if levels > 1:
                # Use resolve_indirection_name (not resolve_indirection) because
                # $ORDER/$NEXT don't need the target variable to exist - they just
                # need the name. resolve_indirection validates existence which fails
                # for cases like $N(@@C) where C(1)="^V1A(22,44,-1)" since that exact
                # subscript may not exist (but $NEXT finds the next one).
                name_expr = f"str(_rt.resolve_indirection_name({full_name_expr}, {levels}, _scope))"
            else:
                name_expr = f"_rt.get_indirection_source({full_name_expr}, _scope)"
        else:
            name_expr_base = generate_expr(inner_expr, ctx)
            name_expr = f"str({name_expr_base})"

        # Use _rt.get_order which handles indirected variable names
        return f"_rt.get_order({name_expr}{append_subs}, _scope, {direction_code})"

    # Generate subscript tuple for non-indirection cases
    # For $ORDER, subscripts include the starting point for iteration
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
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
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve then call m_order_global
        # Spec 014 (T061): Naked references in $ORDER
        return (
            f"(lambda _n, _s: m_order_global(_rt.globals, _n, _s, {direction_code}))"
            f"(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
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
    # DO NOT wrap in str() - let runtime handle canonicalization
    subscripts = getattr(var, "subscripts", [])
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
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
    elif isinstance(var, NakedGlobal):
        # Naked global: resolve then call m_query_global
        # Spec 014 (T061): Naked references in $QUERY
        return (
            f"(lambda _n, _s: m_query_global(_rt.globals, _n, _s))"
            f"(*_rt.globals.resolve_naked({subscripts_tuple}))"
        )
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
            # Apply sign to literal value, truncating to integer for MUMPS semantics
            offset_val = int(offset.value) if offset_sign == "+" else -int(offset.value)
            params.append(f"offset={offset_val}")
        else:
            # Offset is an expression (variable, etc.)
            # Must convert to int since expressions return strings
            offset_code = generate_expr(offset, ctx)
            if offset_sign == "-":
                params.append(f"offset=-int(m_num({offset_code}))")
            else:
                params.append(f"offset=int(m_num({offset_code}))")
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
        # Use importlib.import_module() for reliable module loading in exec() contexts
        # __import__() has issues with dynamically modified sys.path
        params.append(f"module=__import__('importlib').import_module('{routine}')")

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

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) == 1:
        # Single argument - character count
        return f"len(m_str({string_expr}))"
    else:
        # Two arguments - piece count
        # Piece count = delimiter occurrences + 1
        delimiter_expr = generate_expr(args[1], ctx)
        return f"(m_str({string_expr}).count(m_str({delimiter_expr})) + 1)"


def _gen_piece(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $PIECE/$P function.

    Spec 010 Phase 5 (T027-T030): $PIECE extracts delimited pieces.
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
        # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
        return f"m_extract(m_str({string_expr}), 1, 1)"
    elif len(args) == 2:
        # $E(string, from) - single character at position from
        from_expr = generate_expr(args[1], ctx)
        return f"m_extract(m_str({string_expr}), int(m_num({from_expr})), int(m_num({from_expr})))"
    else:
        # $E(string, from, to) - substring
        from_expr = generate_expr(args[1], ctx)
        to_expr = generate_expr(args[2], ctx)
        return f"m_extract(m_str({string_expr}), int(m_num({from_expr})), int(m_num({to_expr})))"


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

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) >= 3:
        start_expr = generate_expr(args[2], ctx)
        return f"m_find(m_str({string_expr}), m_str({target_expr}), int(m_num({start_expr})))"
    else:
        return f"m_find(m_str({string_expr}), m_str({target_expr}), 1)"


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
            return f"m_str({generate_expr(args[0], ctx)})"
        return '""'

    string_expr = generate_expr(args[0], ctx)
    from_expr = generate_expr(args[1], ctx)

    # Use m_str() for MUMPS canonical formatting (no leading zeros, no E-notation)
    if len(args) >= 3:
        to_expr = generate_expr(args[2], ctx)
        # Build translation table with replacement
        return f"m_str({string_expr}).translate(str.maketrans(m_str({from_expr}), m_str({to_expr}).ljust(len(m_str({from_expr})), chr(0)), ''.join(chr(0) if i < len(m_str({to_expr})) else c for i, c in enumerate(m_str({from_expr})))))"
    else:
        # No 'to' argument - delete all characters in 'from'
        return (
            f"m_str({string_expr}).translate(str.maketrans('', '', m_str({from_expr})))"
        )


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
    # DO NOT wrap in str() - let runtime handle canonicalization
    if subscripts:
        subscript_exprs = [generate_expr(sub, ctx) for sub in subscripts]
        if len(subscript_exprs) == 1:
            subscripts_tuple = f"({subscript_exprs[0]},)"
        else:
            subscripts_tuple = f"({', '.join(subscript_exprs)},)"
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


def _gen_justify(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $JUSTIFY/$J function.

    Spec 010 Phase 10 (T067): $JUSTIFY right-justifies a value within a field width.

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
        # Simple right-justify
        return f"str({value_expr}).rjust(int(m_num({width_expr})))"


def _gen_reverse(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $REVERSE/$RE function.

    Spec 010 Phase 10 (T068): $REVERSE reverses a string.

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
    if not args:
        return '""'

    string_expr = generate_expr(args[0], ctx)
    return f"str({string_expr})[::-1]"


def _gen_fnumber(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $FNUMBER/$FN function.

    Spec 010 Phase 10 (T070): $FNUMBER formats a number with various options.

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

# Phase 10: Formatting functions ($JUSTIFY, $FNUMBER, $REVERSE)
INTRINSIC_GENERATORS["J"] = _gen_justify
INTRINSIC_GENERATORS["JUSTIFY"] = _gen_justify
INTRINSIC_GENERATORS["FN"] = _gen_fnumber
INTRINSIC_GENERATORS["FNUMBER"] = _gen_fnumber
INTRINSIC_GENERATORS["RE"] = _gen_reverse
INTRINSIC_GENERATORS["REVERSE"] = _gen_reverse

# $TEXT (Spec 008, migrated to dispatch table for consistency)
INTRINSIC_GENERATORS["T"] = _generate_text
INTRINSIC_GENERATORS["TEXT"] = _generate_text


# $NEXT (pre-1995 deprecated, similar to $ORDER but returns -1 when no next)
def _gen_next(expr: MIntrinsicFunction, ctx: "GeneratorContext") -> str:
    """Generate Python code for $NEXT function.

    $NEXT is a pre-1995 deprecated function similar to $ORDER, but returns
    -1 instead of empty string when there is no next subscript.

    Implementation: Generate $ORDER and wrap with a conditional to convert
    empty string results to -1.
    """
    order_code = _gen_order(expr, ctx)
    # Wrap the $ORDER call: if result is "", return -1, else return result
    return f"(lambda _r: -1 if _r == '' else _r)({order_code})"


INTRINSIC_GENERATORS["N"] = _gen_next
INTRINSIC_GENERATORS["NEXT"] = _gen_next
