"""FOR loop analysis functions.

High-level ASG analysis functions for FOR statements:
- analyze_for_loops: Analyze all FOR loops in a routine
- detect_loop_var_modification: Check if loop variable is modified in body
- detect_internal_quit: Check if QUIT is present in FOR body

These functions operate on ASG nodes (MRoutine, MForStatement)
and do not perform any text parsing.
"""

from typing import TYPE_CHECKING, Dict, List, Optional, Union

from ..asg.elements import MCall, MRoutine, MScope
from ..asg.enums import ForLoopType, ForParamType, PassingMode
from ..asg.expressions import MActualParameter, MGlobal, MIntrinsicFunction, MVariable
from ..asg.statements import (
    MDoStatement,
    MElseStatement,
    MForStatement,
    MQuitStatement,
    MSetStatement,
    OrderIterInfo,
)
from ..asg.type_helpers import get_body_scope, get_else_scope, get_then_scope
from .variables import statement_modifies_variable

if TYPE_CHECKING:
    from .variables import FunctionSignature


def _check_value_params_contain_variables(stmt: MForStatement) -> bool:
    """Check if any VALUE parameter expression contains variable references.

    MUMPS FOR evaluates each parameter when it becomes the current iteration,
    NOT upfront like Python's `for x in [...]`. This means:

    1. Loop var reference: F I=1,I+1,3*I - I is evaluated with current value
    2. Other var reference: F I=A,B,B,C - variables evaluated when current

    If any VALUE parameter contains a variable reference, we cannot use
    Python's `for...in[...]` pattern because:
    - The list would evaluate all values upfront
    - But MUMPS evaluates each value when it becomes current
    - Variables may be modified during the loop body

    Args:
        stmt: The MForStatement to check

    Returns:
        True if any VALUE parameter contains any variable reference
    """
    from .variables import _extract_expression_variables

    # Check each VALUE parameter for any variable reference
    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE and param.value is not None:
            # Extract variables referenced in this expression
            vars_in_expr = _extract_expression_variables(param.value)
            if vars_in_expr:
                # Any variable reference requires sequential evaluation
                return True

    return False


def _classify_for_loop_type(stmt: MForStatement) -> ForLoopType:
    """Classify the loop type based on FOR parameters.

    Determines which Python pattern to use for code generation:
    - ARGUMENTLESS: No parameters (F) - while True
    - BOUNDED: Single range with start:step:end (F I=1:1:10) - for with range()
    - OPEN_ENDED: Single open range with start:step (F I=1:1) - for with count()
    - STRING_LIST: Single values (F I="A","B","C") - for with list
    - MIXED: Multiple parameters of different types - for with chain()

    Args:
        stmt: The MForStatement to classify

    Returns:
        ForLoopType enum value
    """
    if not stmt.parameters:
        return ForLoopType.ARGUMENTLESS

    if len(stmt.parameters) == 1:
        param = stmt.parameters[0]
        if param.param_type == ForParamType.VALUE:
            return ForLoopType.STRING_LIST
        elif param.param_type == ForParamType.RANGE:
            return ForLoopType.BOUNDED
        # ForParamType.OPEN_RANGE is the only remaining case
        return ForLoopType.OPEN_ENDED

    # Multiple parameters - check if all same type for potential optimization
    param_types = {p.param_type for p in stmt.parameters}
    if len(param_types) == 1:
        # All same type
        single_type = next(iter(param_types))
        if single_type == ForParamType.VALUE:
            return ForLoopType.STRING_LIST
        # Multiple ranges are still MIXED (need chain)
    return ForLoopType.MIXED


def _detect_order_iteration(stmt: MForStatement) -> Optional[OrderIterInfo]:
    """Detect if a FOR statement implements a canonical $ORDER iteration.

    Recognises the two common MUMPS patterns that iterate all subscripts
    at one level of a global (or local) array:

    **Pattern A — open-range FOR:**

        F VAR=0:0  S VAR=$O(^GLOBAL(s1,...,VAR)) Q:VAR=""  <body>

    **Pattern B — argumentless FOR (pre-set outside loop):**

        F  S VAR=$O(^GLOBAL(s1,...,VAR)) Q:VAR=""  <body>

    Requirements for detection:
    - Exactly one loop variable (simple ``MVariable``, no subscripts).
    - Loop ``is_infinite`` (step=0 open-range or argumentless).
    - First body statement: SET ``loop_var = $ORDER( ref(..., loop_var) )``
      where the $ORDER argument is a *named* global or local array (not a
      naked global) and the last subscript is the loop variable itself.
    - Second body statement: ``QUIT:loop_var=""`` (unconditional string
      equality against ``""``).
    - The loop variable is **not** modified anywhere else in the body (i.e.
      ``loop_var_modified_in_body`` must be False after the SET/QUIT pair).

    Local-array iteration ($O(K(I))) is supported but less common.

    Args:
        stmt: The ``MForStatement`` to inspect (``loop_var_modified_in_body``
              must already be set by the regular ``_analyze_fors_in_scope``
              pass before this helper is called).

    Returns:
        ``OrderIterInfo`` when the pattern is matched; ``None`` otherwise.
    """
    from ..asg.expressions import MBinaryOp, MLiteral
    from ..asg.statements import MAssignment

    # --- Guard: loop variable must be a plain named local (no subscripts) ----
    if not isinstance(stmt.loop_var, MVariable):
        return None
    if stmt.loop_var.subscripts:
        return None  # Subscripted loop var — skip
    loop_var_name: str = stmt.loop_var.name

    # --- Guard: must be an infinite / open-ended loop -----------------------
    if not stmt.is_infinite:
        return None

    # --- Guard: loop var must not be modified elsewhere in the body ---------
    # (loop_var_modified_in_body is set to True because the SET at position 0
    # does modify it — we re-check only the *real* body, i.e. stmts[2:])
    body_stmts = stmt.body.statements
    if len(body_stmts) < 2:
        return None

    # --- stmt[0]: must be  S loop_var = $ORDER( ref(..., loop_var) ) ---------
    first = body_stmts[0]
    if not isinstance(first, MSetStatement):
        return None
    if len(first.assignments) != 1:
        return None
    assign: MAssignment = first.assignments[0]

    # LHS must be the loop variable (plain, no subscripts)
    lhs = assign.target
    if not isinstance(lhs, MVariable) or lhs.name != loop_var_name or lhs.subscripts:
        return None

    # RHS must be $ORDER(...)
    rhs = assign.value
    if not isinstance(rhs, MIntrinsicFunction):
        return None
    if rhs.name.upper() not in ("O", "ORDER"):
        return None

    # $ORDER can have 1 or 2 arguments: $O(ref) or $O(ref, direction)
    if not rhs.arguments:
        return None
    order_ref = rhs.arguments[0]

    # Determine direction
    direction = 1
    if len(rhs.arguments) >= 2:
        dir_arg = rhs.arguments[1]
        if isinstance(dir_arg, MLiteral):
            try:
                direction = int(dir_arg.value)
            except (ValueError, TypeError):
                return None
        else:
            # Dynamic direction — can't optimise statically
            return None

    # order_ref must be a named global or local variable (not naked)
    is_local = False
    global_name = ""
    local_name = ""
    prefix_exprs: List = []

    if isinstance(order_ref, MGlobal):
        if not order_ref.name:
            return None  # Naked global — skip
        global_name = order_ref.name
        subscripts = order_ref.subscripts
    elif isinstance(order_ref, MVariable):
        is_local = True
        local_name = order_ref.name
        subscripts = order_ref.subscripts
    else:
        return None  # Indirection, extended ref, etc. — skip

    # Last subscript must be exactly the loop variable
    if not subscripts:
        return None
    last_sub = subscripts[-1]
    if not isinstance(last_sub, MVariable):
        return None
    if last_sub.name != loop_var_name or last_sub.subscripts:
        return None

    # All prefix subscripts must not reference the loop variable themselves
    # (they are evaluated once before the loop in our generated code)
    prefix_exprs = list(subscripts[:-1])

    # --- stmt[1]: must be  Q:loop_var="" --------------------------------
    second = body_stmts[1]
    if not isinstance(second, MQuitStatement):
        return None
    cond = second.postcondition
    if cond is None:
        return None

    # Condition must be an equality against literal ""
    # Pattern: loop_var = "" expressed as MBinaryOp("=", MVariable(loop_var), MLiteral(""))
    if not isinstance(cond, MBinaryOp):
        return None
    if getattr(cond, "operator", None) != "=":
        return None
    left = getattr(cond, "left", None)
    right = getattr(cond, "right", None)

    # Allow either order: VAR="" or ""=VAR
    def _is_loop_var(node) -> bool:
        return (
            isinstance(node, MVariable)
            and node.name == loop_var_name
            and not node.subscripts
        )

    def _is_empty_string(node) -> bool:
        return isinstance(node, MLiteral) and str(getattr(node, "value", "__x__")) == ""

    if not (
        (_is_loop_var(left) and _is_empty_string(right))
        or (_is_loop_var(right) and _is_empty_string(left))
    ):
        return None

    # --- Guard: loop var must not be modified in stmts[2:] ------------------
    if len(body_stmts) > 2:
        tail_scope = MScope()
        tail_scope.statements = body_stmts[2:]
        if _check_var_modified_in_scope(stmt.loop_var, tail_scope):
            return None

    return OrderIterInfo(
        global_name=global_name,
        prefix_exprs=prefix_exprs,
        is_local=is_local,
        local_name=local_name,
        direction=direction,
        body_stmt_offset=2,
    )


def analyze_for_loops(
    routine: MRoutine, signatures: Optional[Dict[str, "FunctionSignature"]] = None
) -> None:
    """Analyze all FOR loops in a routine.

    This function scans each MForStatement and:
    1. Detects if loop variable is modified inside the body
    2. Sets loop_var_modified_in_body accordingly
    3. Detects if QUIT is present in the body
    4. Sets has_internal_quit accordingly

    When signatures are provided (from analyze_variables), the by-ref check
    uses callee signatures for precise detection. Otherwise falls back to
    conservative (any by-ref = potentially modified).

    Args:
        routine: The MRoutine to analyze
        signatures: Optional dict of label signatures for precise by-ref detection

    Side Effects:
        - Sets MForStatement.loop_var_modified_in_body for each FOR
        - Sets MForStatement.has_internal_quit for each FOR
    """
    for label in routine.labels:
        _analyze_fors_in_scope(label.body, routine, signatures)


def _analyze_fors_in_scope(
    scope: MScope,
    routine: MRoutine,
    signatures: Optional[Dict[str, "FunctionSignature"]] = None,
) -> None:
    """Recursively analyze FOR loops in a scope.

    Args:
        scope: The scope to scan for FOR statements
        routine: The routine being analyzed (for signature lookup)
        signatures: Optional dict of label signatures for precise by-ref detection
    """
    for stmt in scope.statements:
        if isinstance(stmt, MForStatement):
            # Always set loop_type during analysis
            stmt.loop_type = _classify_for_loop_type(stmt)

            # Check if VALUE parameters contain variable references
            # This is needed because F I=A,B,B,C must evaluate each param
            # when it becomes current, not upfront like Python's for...in[...]
            stmt.value_params_reference_loop_var = (
                _check_value_params_contain_variables(stmt)
            )

            # Analyze this FOR's body for loop var modification and internal QUIT
            if stmt.body:
                if stmt.loop_var:
                    # Extract loop variable name for modification checks
                    if isinstance(stmt.loop_var, str):
                        loop_var_name = stmt.loop_var
                        loop_var_for_check: Union[str, MVariable] = stmt.loop_var
                    elif isinstance(stmt.loop_var, MVariable):
                        loop_var_name = stmt.loop_var.name
                        loop_var_for_check = stmt.loop_var
                    else:
                        # MExpr case (e.g., indirection) - assume modified for safety
                        stmt.loop_var_modified_in_body = True
                        loop_var_name = None
                        loop_var_for_check = None

                    if loop_var_name and loop_var_for_check is not None:
                        # Check for SET, READ, KILL modifications
                        modified_in_body = _check_var_modified_in_scope(
                            loop_var_for_check, stmt.body
                        )
                        # Check for pass-by-reference in DO calls
                        # Use signatures for precise check if available
                        passed_byref = _check_var_passed_byref_in_scope(
                            loop_var_name, stmt.body, routine, signatures
                        )
                        stmt.loop_var_modified_in_body = (
                            modified_in_body or passed_byref
                        )
                stmt.has_internal_quit = _check_quit_in_scope(stmt.body)
                # Recurse into nested structures within FOR body
                _analyze_fors_in_scope(stmt.body, routine, signatures)

            # After regular analysis: try to detect the $ORDER iteration pattern.
            # Only attempt when the FOR meets the basic structural requirements.
            # Note: loop_var_modified_in_body will be True (the SET modifies it),
            # but _detect_order_iteration guards that the tail body doesn't modify it.
            if stmt.is_infinite and isinstance(stmt.loop_var, MVariable):
                stmt.order_iter_info = _detect_order_iteration(stmt)
        # Recurse into other nested scopes using type-safe helpers
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            _analyze_fors_in_scope(then_scope, routine, signatures)
        else:
            else_scope = get_else_scope(stmt)
            if else_scope is not None:
                _analyze_fors_in_scope(else_scope, routine, signatures)
            else:
                body = get_body_scope(stmt)
                if body is not None and not isinstance(stmt, MForStatement):
                    _analyze_fors_in_scope(body, routine, signatures)


def _check_var_modified_in_scope(
    loop_var: Union[str, MVariable], scope: MScope
) -> bool:
    """Check if a loop variable is modified in a scope.

    Delegates to ``scope.walk_statements()`` for recursive traversal and
    ``statement_modifies_variable()`` for per-statement write detection
    (SET, READ, KILL including kill-all and exclusive kill).

    Args:
        loop_var: The loop variable (string name or MVariable)
        scope: The scope to check

    Returns:
        True if the variable is SET, READ, or KILLED within the scope
    """
    # Extract the variable name for comparison
    if isinstance(loop_var, str):
        var_name = loop_var
    elif isinstance(loop_var, MVariable):
        var_name = loop_var.name
    else:
        # Complex case (indirection) - assume modified to be safe
        return True

    return any(
        statement_modifies_variable(stmt, var_name) for stmt in scope.walk_statements()
    )


def _get_callee_signature(
    call: MCall,
    routine: MRoutine,
    signatures: Optional[Dict[str, "FunctionSignature"]],
) -> Optional["FunctionSignature"]:
    """Get the FunctionSignature for a callee, if available.

    Args:
        call: The MCall to look up
        routine: The routine being analyzed
        signatures: Dict of label signatures, if computed

    Returns:
        FunctionSignature if available, None otherwise
    """
    if not signatures:
        return None

    # External calls (label^routine) - signature not available
    if call.routine:
        return None

    # Get callee name
    callee_name = call.name
    if not callee_name:
        return None

    return signatures.get(callee_name)


def _check_var_passed_byref_in_scope(
    var_name: str,
    scope: MScope,
    routine: MRoutine,
    signatures: Optional[Dict[str, "FunctionSignature"]] = None,
) -> bool:
    """Check if a variable is passed by reference in a DO call within a scope.

    Delegates to ``scope.walk_statements()`` for recursive traversal.

    When signatures are available, this function uses precise detection:
    only returns True if the callee actually modifies the formal parameter
    (i.e., the formal param is in callee's byref_outputs).

    When signatures are not available (external calls, or analyze_variables
    wasn't run), falls back to conservative: any by-ref = potentially modified.

    Args:
        var_name: The variable name to check
        scope: The scope to check
        routine: The routine being analyzed (for signature lookup)
        signatures: Optional dict of label signatures for precise detection

    Returns:
        True if the variable is passed by reference AND potentially modified
    """
    for stmt in scope.walk_statements():
        # Check DO statements for by-ref parameters
        if not isinstance(stmt, MDoStatement):
            continue
        for call in stmt.targets:
            for i, arg in enumerate(call.arguments):
                if isinstance(arg, MActualParameter):
                    if arg.passing_mode == PassingMode.BY_REFERENCE:
                        if arg.variable_name == var_name:
                            # Found by-ref parameter - check if callee modifies it
                            callee_sig = _get_callee_signature(
                                call, routine, signatures
                            )
                            if callee_sig is None:
                                # No signature (external call or not computed)
                                # Fall back to conservative: assume modified
                                return True

                            # Get the formal parameter name for this position
                            if i < len(callee_sig.formal_params):
                                formal_name = callee_sig.formal_params[i]
                                # Check if callee modifies this formal param
                                if formal_name in callee_sig.byref_outputs:
                                    return True
                                # Callee doesn't modify it - don't flag as modified
                            else:
                                # More args than formals - conservative
                                return True

    return False


def _check_quit_in_scope(scope: MScope) -> bool:
    """Check if a QUIT statement is present in a scope (not just nested FORs).

    Only detects QUIT that would exit THIS scope, not QUITs in nested
    FOR loops (which would exit those inner loops instead).

    Args:
        scope: The scope to check

    Returns:
        True if QUIT is found in this scope
    """
    for stmt in scope.statements:
        if isinstance(stmt, MQuitStatement):
            return True

        # Check in IF/ELSE scopes - QUIT there would still exit the FOR
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            if _check_quit_in_scope(then_scope):
                return True
        else_scope = get_else_scope(stmt)
        if else_scope is not None:
            if _check_quit_in_scope(else_scope):
                return True

        # ELSE is a separate statement type with its own body scope
        if isinstance(stmt, MElseStatement) and stmt.body:
            if _check_quit_in_scope(stmt.body):
                return True

        # Do NOT recurse into nested FOR bodies - their QUIT exits THEM, not us
        # Also don't recurse into DO blocks - separate scope

    return False


def analyze_quit_context(routine: MRoutine) -> None:
    """Analyze QUIT statement context for all QUITs in a routine.

    This function walks through all statements and sets the context fields
    on each MQuitStatement:
    - exits_for: Set to enclosing MForStatement if QUIT is inside a FOR loop
    - exits_do_block: Set to enclosing MDoStatement if QUIT is inside an inline DO block

    This enables codegen to use ASG fields directly instead of runtime tracking.

    Args:
        routine: The MRoutine to analyze

    Side Effects:
        - Sets MQuitStatement.exits_for for QUITs inside FOR loops
        - Sets MQuitStatement.exits_do_block for QUITs inside DO blocks
    """
    for label in routine.labels:
        _analyze_quit_context_in_scope(
            label.body, enclosing_for=None, enclosing_do_block=None
        )


def analyze_quit_context_for_statements(statements: list) -> None:
    """Analyze QUIT context for a flat list of ASG statements.

    Used for inline XECUTE code that is parsed at codegen time and
    doesn't go through the routine-level analysis phase. Without this,
    QUIT inside FOR inside XECUTE would generate raise _XecuteExit()
    instead of break.

    Args:
        statements: List of MStatement objects (already structured)
    """
    scope = MScope()
    scope.statements = statements
    _analyze_quit_context_in_scope(scope, enclosing_for=None, enclosing_do_block=None)


def _analyze_quit_context_in_scope(
    scope: MScope,
    enclosing_for: Optional[MForStatement],
    enclosing_do_block: Optional[MDoStatement],
) -> None:
    """Recursively analyze QUIT context in a scope.

    Args:
        scope: The scope to analyze
        enclosing_for: The innermost enclosing FOR loop, if any
        enclosing_do_block: The innermost enclosing DO block, if any
    """
    for stmt in scope.statements:
        if isinstance(stmt, MQuitStatement):
            # A QUIT inside a FOR exits that FOR (takes priority over DO block)
            if enclosing_for is not None:
                stmt.exits_for = enclosing_for
            elif enclosing_do_block is not None:
                stmt.exits_do_block = enclosing_do_block
            # Otherwise exits_for and exits_do_block remain None (plain return)

        elif isinstance(stmt, MForStatement):
            # FOR body: QUIT inside exits this FOR
            if stmt.body:
                _analyze_quit_context_in_scope(
                    stmt.body, enclosing_for=stmt, enclosing_do_block=None
                )

        elif isinstance(stmt, MDoStatement) and stmt.is_inline_block:
            # Inline DO block: QUIT inside exits this block
            if stmt.body:
                _analyze_quit_context_in_scope(
                    stmt.body, enclosing_for=None, enclosing_do_block=stmt
                )

        # Recurse into IF/ELSE scopes - they don't change the QUIT context
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            _analyze_quit_context_in_scope(
                then_scope, enclosing_for, enclosing_do_block
            )
        else_scope = get_else_scope(stmt)
        if else_scope is not None:
            _analyze_quit_context_in_scope(
                else_scope, enclosing_for, enclosing_do_block
            )

        # ELSE is a separate statement type with its own body scope
        # (MUMPS ELSE is not structurally part of IF - it checks $TEST)
        if isinstance(stmt, MElseStatement) and stmt.body:
            _analyze_quit_context_in_scope(stmt.body, enclosing_for, enclosing_do_block)
