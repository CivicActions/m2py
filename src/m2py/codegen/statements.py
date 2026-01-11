"""Statement code generation for MUMPS-to-Python transpilation.

Generates Python statements from MUMPS ASG statement nodes.
Handles SET, WRITE, QUIT, IF, ELSE, FOR, and other basic commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from m2py.asg.enums import ForLoopType, ForParamType, GotoType, PassingMode
from m2py.asg.expressions import MActualParameter, MExpr, MVariable
from m2py.asg.statements import (
    MDoStatement,
    MElseStatement,
    MForStatement,
    MGotoStatement,
    MIfStatement,
    MQuitStatement,
    MSetStatement,
    MWriteStatement,
)
from m2py.codegen.expressions import generate_expr
from m2py.codegen.names import translate_name

if TYPE_CHECKING:
    from m2py.asg.statements import MStatement
    from m2py.codegen.routine import GeneratorContext


# =============================================================================
# Exceptions (imported locally to avoid circular import)
# =============================================================================


class UnsupportedFeatureError(Exception):
    """Raised when attempting to generate code for unsupported feature.

    Note: This is a local definition to avoid circular import.
    The canonical definition is in m2py.codegen.__init__.py.
    """

    pass


# =============================================================================
# Spec 005: Code Generation Context Helpers
# =============================================================================


def _generate_call_arguments(
    arguments: List[MActualParameter], ctx: "GeneratorContext"
) -> str:
    """Generate Python arguments from MUMPS call arguments.

    Handles:
    - BY_VALUE: Expression evaluated and passed
    - BY_REFERENCE: Variable passed (actual by-ref return tuple handled at call site)
    - OMITTED: None placeholder

    Note: Full by-reference semantics with return tuple destructuring
    is implemented in Phase 10 (US8). For now, by-ref passes the variable.

    Args:
        arguments: List of MActualParameter from MCall
        ctx: Generator context

    Returns:
        Comma-separated argument string for Python call
    """
    if not arguments:
        return ""

    parts = []
    for arg in arguments:
        if arg.passing_mode == PassingMode.OMITTED:
            parts.append("None")
        elif arg.passing_mode == PassingMode.BY_REFERENCE:
            # For by-ref, pass the variable value
            # Full tuple return pattern in Phase 10
            if arg.expression:
                parts.append(generate_expr(arg.expression, ctx))
            elif arg.variable_name:
                parts.append(translate_name(arg.variable_name))
            else:
                parts.append("None")
        else:  # BY_VALUE
            if arg.expression:
                parts.append(generate_expr(arg.expression, ctx))
            else:
                parts.append("None")

    return ", ".join(parts)


def _is_do_block(stmt: MDoStatement) -> bool:
    """Check if this is an argumentless DO block (with dot-indented body).

    Only argumentless DO blocks have $TEST stacking semantics - the caller's
    $TEST is saved before the block and restored after. This is the ONLY
    case where $TEST is stacked.

    Label calls (D SUB, D SUB(), D SUB(X)) do NOT stack $TEST - callee's
    $TEST changes are visible to the caller.

    Per MUMPS spec (verified against YottaDB):
    - D SUB      -> label call ($TEST NOT stacked)
    - D SUB()    -> label call with empty args ($TEST NOT stacked)
    - D SUB(X)   -> label call with args ($TEST NOT stacked)
    - D          -> DO block with dot lines ($TEST IS stacked)
              . cmd

    Args:
        stmt: The MDoStatement to check

    Returns:
        True if this is an argumentless DO block (body populated)
    """
    # DO block has no targets but has body statements
    return not stmt.targets and stmt.body and len(stmt.body.statements) > 0


@dataclass
class ForGenContext:
    """Context for FOR loop code generation decisions.

    Aggregates analysis results from MForStatement to guide
    which Python pattern to generate.

    Attributes:
        stmt: The MForStatement being generated
        loop_var: Translated Python name for loop variable
        use_while: True if loop_var_modified_in_body requires while loop
        needs_break: True if has_internal_quit or exit GOTOs need break
        is_infinite: True for argumentless FOR (F)
        loop_type: Classification from analysis for pattern selection
    """

    stmt: MForStatement
    loop_var: str
    use_while: bool  # True if loop_var_modified_in_body
    needs_break: bool  # True if has_internal_quit or has_internal_goto
    is_infinite: bool
    loop_type: ForLoopType

    @classmethod
    def from_statement(cls, stmt: MForStatement) -> "ForGenContext":
        """Create ForGenContext from an MForStatement.

        Args:
            stmt: The FOR statement to analyze

        Returns:
            ForGenContext with analysis results
        """
        # Get loop variable name
        if isinstance(stmt.loop_var, str):
            loop_var = translate_name(stmt.loop_var) if stmt.loop_var else "_"
        elif isinstance(stmt.loop_var, MVariable):
            loop_var = translate_name(stmt.loop_var.name)
        else:
            loop_var = "_"  # Fallback for complex expressions

        # Determine if we need a while loop (loop var modified in body)
        use_while = getattr(stmt, "loop_var_modified_in_body", False)

        # Determine if we need break statements
        needs_break = getattr(stmt, "has_internal_quit", False) or getattr(
            stmt, "has_internal_goto", False
        )

        # Check if this is an infinite/argumentless loop
        is_infinite = getattr(stmt, "is_infinite", False) or not stmt.parameters

        # Get loop type from analysis (default to BOUNDED if not set)
        loop_type = getattr(stmt, "loop_type", None)
        if loop_type is None:
            # Infer from parameters if not analyzed
            if not stmt.parameters:
                loop_type = ForLoopType.ARGUMENTLESS
            elif len(stmt.parameters) == 1:
                param = stmt.parameters[0]
                if param.param_type == ForParamType.VALUE:
                    loop_type = ForLoopType.STRING_LIST
                elif param.param_type == ForParamType.RANGE:
                    loop_type = ForLoopType.BOUNDED
                elif param.param_type == ForParamType.OPEN_RANGE:
                    loop_type = ForLoopType.OPEN_ENDED
                else:
                    loop_type = ForLoopType.BOUNDED
            else:
                loop_type = ForLoopType.MIXED

        return cls(
            stmt=stmt,
            loop_var=loop_var,
            use_while=use_while,
            needs_break=needs_break,
            is_infinite=is_infinite,
            loop_type=loop_type,
        )


def _for_needs_loop_exit_wrapper(stmt: MForStatement) -> bool:
    """Check if a FOR loop needs a try/except _LoopExit wrapper.

    T038: The wrapper is needed when this FOR is the outermost target
    of a MULTI_LOOP_EXIT GOTO. The GOTO raises _LoopExit() and the
    outermost FOR catches it to exit all nested loops.

    Args:
        stmt: The MForStatement to check

    Returns:
        True if this FOR needs try/except _LoopExit wrapper
    """
    exit_points = getattr(stmt, "exit_points", [])
    for exit_stmt in exit_points:
        if isinstance(exit_stmt, MGotoStatement):
            goto_type = getattr(exit_stmt, "goto_type", None)
            if goto_type == GotoType.MULTI_LOOP_EXIT:
                # Check if this FOR is the outermost (first in exits_loops)
                exits_loops = getattr(exit_stmt, "exits_loops", [])
                if exits_loops and exits_loops[0] is stmt:
                    return True
    return False


@dataclass
class GotoGenContext:
    """Context for GOTO code generation decisions.

    Aggregates analysis results from MGotoStatement to determine
    which Python pattern to generate.

    Attributes:
        stmt: The MGotoStatement being generated
        in_for_loop: True if GOTO is inside a FOR loop
        enclosing_loops: Stack of FOR loops containing this GOTO
        target_label: Translated Python name for target label
        pattern: Code pattern to generate:
            - 'continue': Loop continuation
            - 'break': Single loop exit
            - 'multi_break': Multiple loop exit (exception)
            - 'forward': Forward jump restructuring
            - 'function_call': Simple function call with return
            - 'unsupported': Cannot be transpiled statically
    """

    stmt: MGotoStatement
    in_for_loop: bool
    enclosing_loops: List[MForStatement]
    target_label: str
    pattern: (
        str  # 'break' | 'multi_break' | 'forward' | 'function_call' | 'unsupported'
    )

    @classmethod
    def from_statement(
        cls, stmt: MGotoStatement, loop_stack: List[MForStatement]
    ) -> "GotoGenContext":
        """Create GotoGenContext from an MGotoStatement.

        Args:
            stmt: The GOTO statement to analyze
            loop_stack: Current stack of enclosing FOR loops

        Returns:
            GotoGenContext with analysis results
        """
        in_for_loop = len(loop_stack) > 0
        enclosing_loops = list(loop_stack)

        # Get target label name
        target_label = ""
        if stmt.targets:
            target = stmt.targets[0]
            target_label = translate_name(target.name) if target.name else ""

        # Determine pattern based on analysis fields
        pattern = "function_call"  # Default: simple GOTO to label

        # Check for loop-related patterns
        # Note: There is no "continue" pattern - GOTO cannot create continue semantics.
        # Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
        # termination of all FORs in the line containing the GOTO."
        exits_loops = getattr(stmt, "exits_loops", [])
        goto_type = getattr(stmt, "goto_type", None)
        is_cross_label = getattr(stmt, "is_cross_label", False)

        if exits_loops:
            if len(exits_loops) == 1:
                pattern = "break"
            else:
                pattern = "multi_break"
        elif goto_type is not None:
            # Analysis has run - check goto_type for pattern
            from m2py.asg.enums import GotoType

            if goto_type in (GotoType.EXTERNAL, GotoType.UNRESOLVED):
                pattern = "unsupported"
            elif goto_type == GotoType.BACKWARD_JUMP:
                # Backward jumps are unsupported in Spec 005
                pattern = "unsupported"
            elif goto_type == GotoType.FORWARD_JUMP and not is_cross_label:
                # Intra-label forward jump - can be restructured
                pattern = "forward"
            # else: function_call (cross-label or other analyzed patterns)

        return cls(
            stmt=stmt,
            in_for_loop=in_for_loop,
            enclosing_loops=enclosing_loops,
            target_label=target_label,
            pattern=pattern,
        )


def _is_restructurable_goto(stmt: MGotoStatement) -> bool:
    """Check if a GOTO statement can be restructured to if/else.

    A GOTO is restructurable when:
    1. It is an intra-label jump (is_cross_label=False) - same label
    2. It is a forward jump (goto_type=FORWARD_JUMP) - not backward

    Intra-label forward GOTOs can be restructured by wrapping subsequent
    statements in if/else blocks, eliminating the need for actual jumps.

    Example:
        MUMPS:  S X=1 I X=1 G SKIP S X=2
                SKIP W X Q

        Python: X = 1
                if m_truth(m_compare(X, "=", 1)):
                    pass  # GOTO SKIP - skip X=2
                else:
                    X = 2
                _rt.write(str(X))
                return

    Backward intra-label GOTOs (G LABEL without offset) create implicit loops
    and are NOT restructurable - they require different handling (Spec 006).

    Args:
        stmt: The MGotoStatement to check

    Returns:
        True if the GOTO can be restructured to if/else
    """
    from m2py.asg.enums import GotoType

    goto_type = getattr(stmt, "goto_type", None)
    is_cross_label = getattr(stmt, "is_cross_label", True)  # Default to cross-label

    # Restructurable: intra-label (same label) forward jump
    return goto_type == GotoType.FORWARD_JUMP and not is_cross_label


def _find_forward_goto_in_if(if_stmt: MIfStatement) -> "MGotoStatement | None":
    """Find a restructurable forward GOTO in an IF's then_scope.

    Only checks the first statement (immediate GOTO pattern).
    More complex patterns could be supported in the future.

    Args:
        if_stmt: The MIfStatement to check

    Returns:
        The MGotoStatement if found and restructurable, None otherwise
    """
    if not if_stmt.then_scope or not if_stmt.then_scope.statements:
        return None

    # Check if there's a GOTO as the only/first statement
    for stmt in if_stmt.then_scope.statements:
        if isinstance(stmt, MGotoStatement) and _is_restructurable_goto(stmt):
            return stmt

    return None


def _restructure_forward_goto(
    if_stmt: MIfStatement,
    if_index: int,
    statements: List["MStatement"],
    goto: MGotoStatement,
    ctx: "GeneratorContext",
) -> int:
    """Generate restructured code for forward GOTO in an IF statement.

    Transforms:
        IF cond GOTO target       ; if_index
        ... statements to skip ... ; if_index+1 to target_idx-1
        target_statement           ; target_idx

    Into:
        _test = m_truth(cond)
        if not _test:
            ... statements to skip ...
        target_statement  # continues at same level

    The transformation inverts the IF condition so that statements between
    the IF and the GOTO target are executed only when the condition is FALSE.
    When the condition is TRUE, those statements are skipped (the original
    GOTO behavior).

    Args:
        if_stmt: The MIfStatement containing the GOTO
        if_index: Index of the IF statement in the statement list
        statements: Full list of statements at this scope level
        goto: The MGotoStatement being restructured
        ctx: Generator context

    Returns:
        The next statement index to continue generation from (skip consumed statements)
    """
    # Get target statement index from analysis
    target_idx = getattr(goto, "target_stmt_index", None)

    if target_idx is None:
        # Fall back to generating the IF normally
        _generate_if(if_stmt, ctx)
        return if_index + 1

    # Statements to skip are between IF (exclusive) and target (exclusive)
    skip_stmts = statements[if_index + 1 : target_idx]

    # Generate condition check and set _test
    # Handle single vs multiple conditions
    if if_stmt.condition is not None:
        cond_expr = generate_expr(if_stmt.condition, ctx)
        ctx.emitter.line(f"_test = m_truth({cond_expr})")
    elif if_stmt.conditions:
        cond_parts = [generate_expr(c, ctx) for c in if_stmt.conditions]
        cond_expr = " and ".join(f"m_truth({c})" for c in cond_parts)
        ctx.emitter.line(f"_test = {cond_expr}")
    else:
        # Argumentless IF - use existing _test (GOTO executes if _test is true)
        pass  # _test already set

    # Generate the restructured if/else
    # Skipped statements go in "if not _test:" (execute when GOTO doesn't fire)
    if skip_stmts:
        ctx.emitter.line("if not _test:")
        with ctx.emitter.indented():
            for stmt in skip_stmts:
                generate_statement(stmt, ctx)

    # Return the target index - generation continues from there
    return target_idx


def generate_scope_statements(
    statements: List["MStatement"],
    ctx: "GeneratorContext",
) -> None:
    """Generate statements for a scope, handling forward GOTO restructuring.

    This function should be used when generating a sequence of statements
    (e.g., label body, DO block body) to properly handle intra-label forward
    GOTOs by restructuring them to if/else blocks.

    The restructuring transforms:
        I cond G SKIP
        W "skipped"
        SKIP W "target"

    Into:
        _test = m_truth(cond)
        if not _test:
            _rt.write("skipped")
        _rt.write("target")

    Args:
        statements: List of statements to generate
        ctx: Generator context
    """
    i = 0
    while i < len(statements):
        stmt = statements[i]

        # Check for IF with restructurable forward GOTO
        if isinstance(stmt, MIfStatement):
            goto = _find_forward_goto_in_if(stmt)
            if goto:
                # Restructure and skip consumed statements
                i = _restructure_forward_goto(stmt, i, statements, goto, ctx)
                continue

        # Normal statement generation
        generate_statement(stmt, ctx)
        i += 1


def generate_statement(stmt: "MStatement", ctx: "GeneratorContext") -> None:
    """Generate Python statement from ASG statement node.

    Writes to ctx.emitter. Dispatches based on statement type:
    - MSetStatement → assignment
    - MWriteStatement → _rt.write() call
    - MQuitStatement → return
    - MIfStatement → if block with _test tracking
    - MElseStatement → if not _test block
    - MForStatement → for loop

    Args:
        stmt: ASG statement node
        ctx: Generator context with emitter

    Raises:
        NotImplementedError: For unsupported statement types
    """
    if isinstance(stmt, MSetStatement):
        _generate_set(stmt, ctx)
    elif isinstance(stmt, MWriteStatement):
        _generate_write(stmt, ctx)
    elif isinstance(stmt, MQuitStatement):
        _generate_quit(stmt, ctx)
    elif isinstance(stmt, MIfStatement):
        _generate_if(stmt, ctx)
    elif isinstance(stmt, MElseStatement):
        _generate_else(stmt, ctx)
    elif isinstance(stmt, MForStatement):
        _generate_for(stmt, ctx)
    elif isinstance(stmt, MGotoStatement):
        _generate_goto(stmt, ctx)
    elif isinstance(stmt, MDoStatement):
        _generate_do(stmt, ctx)
    else:
        raise NotImplementedError(f"Unsupported statement type: {type(stmt).__name__}")


def _generate_set(stmt: MSetStatement, ctx: "GeneratorContext") -> None:
    """Generate Python assignment from MSetStatement.

    Args:
        stmt: MSetStatement node
        ctx: Generator context
    """
    for assignment in stmt.assignments:
        if assignment.target is None or assignment.value is None:
            continue

        # Get target variable name
        if isinstance(assignment.target, MVariable):
            target_name = translate_name(assignment.target.name)

            # Subscripts not supported yet
            if assignment.target.subscripts:
                raise NotImplementedError("Subscripted assignments not yet supported")
        else:
            raise NotImplementedError(
                f"Unsupported SET target type: {type(assignment.target).__name__}"
            )

        # Generate value expression
        value_expr = generate_expr(assignment.value, ctx)

        # Emit assignment
        ctx.emitter.line(f"{target_name} = {value_expr}")


def _generate_write(stmt: MWriteStatement, ctx: "GeneratorContext") -> None:
    """Generate _rt.write() calls from MWriteStatement.

    Args:
        stmt: MWriteStatement node
        ctx: Generator context
    """
    for arg in stmt.arguments:
        if isinstance(arg, MExpr):
            # Generate expression and write it
            expr = generate_expr(arg, ctx)
            ctx.emitter.line(f"_rt.write(str({expr}))")
        # Skip format controls for now (!, #, ?n) - Phase 2 scope is basic only


def _generate_quit(stmt: MQuitStatement, ctx: "GeneratorContext") -> None:
    """Generate break or return statement from MQuitStatement.

    MUMPS QUIT has context-dependent behavior:
    - Inside a FOR loop: exits the FOR loop (Python: break)
    - Inside a DO block: returns from the block (Python: return)
    - With return value: returns value from extrinsic (Python: return value)

    Args:
        stmt: MQuitStatement node
        ctx: Generator context
    """
    if stmt.return_value is not None:
        # QUIT with return value (extrinsic function return)
        value_expr = generate_expr(stmt.return_value, ctx)
        ctx.emitter.line(f"return {value_expr}")
    elif ctx.loop_stack:
        # Inside a FOR loop - QUIT exits the innermost FOR
        ctx.emitter.line("break")
    else:
        # Plain QUIT outside FOR - return from function/block
        ctx.emitter.line("return")


def _generate_if(stmt: MIfStatement, ctx: "GeneratorContext") -> None:
    """Generate Python if statement from MIfStatement.

    MUMPS IF evaluates condition, sets $TEST, and conditionally executes body.
    Generated code: _test = m_truth(cond); if _test: ...

    Args:
        stmt: MIfStatement node
        ctx: Generator context
    """
    # Get condition(s) - single condition uses .condition, multiple uses .conditions
    if stmt.condition is not None:
        cond_expr = generate_expr(stmt.condition, ctx)
    elif stmt.conditions:
        # Multiple comma-separated conditions act as AND
        # Each condition is evaluated in sequence
        cond_parts = [generate_expr(c, ctx) for c in stmt.conditions]
        cond_expr = " and ".join(f"m_truth({c})" for c in cond_parts)
        # For multiple conditions, we evaluate as AND but still set _test at end
        ctx.emitter.line(f"_test = {cond_expr}")
        ctx.emitter.line("if _test:")
        with ctx.emitter.indented():
            if stmt.then_scope and stmt.then_scope.statements:
                for body_stmt in stmt.then_scope.statements:
                    generate_statement(body_stmt, ctx)
            else:
                ctx.emitter.line("pass")
        return
    else:
        # Argumentless IF uses existing $TEST
        ctx.emitter.line("if _test:")
        with ctx.emitter.indented():
            if stmt.then_scope and stmt.then_scope.statements:
                for body_stmt in stmt.then_scope.statements:
                    generate_statement(body_stmt, ctx)
            else:
                ctx.emitter.line("pass")
        return

    # Single condition case - evaluate and set _test
    ctx.emitter.line(f"_test = m_truth({cond_expr})")
    ctx.emitter.line("if _test:")

    with ctx.emitter.indented():
        if stmt.then_scope and stmt.then_scope.statements:
            for body_stmt in stmt.then_scope.statements:
                generate_statement(body_stmt, ctx)
        else:
            ctx.emitter.line("pass")


def _generate_else(stmt: MElseStatement, ctx: "GeneratorContext") -> None:
    """Generate Python if-not-_test statement from MElseStatement.

    MUMPS ELSE executes if $TEST is false.
    Generated code: if not _test: ...

    Args:
        stmt: MElseStatement node
        ctx: Generator context
    """
    ctx.emitter.line("if not _test:")

    with ctx.emitter.indented():
        if stmt.body and stmt.body.statements:
            for body_stmt in stmt.body.statements:
                generate_statement(body_stmt, ctx)
        else:
            ctx.emitter.line("pass")


def _generate_for(stmt: MForStatement, ctx: "GeneratorContext") -> None:
    """Generate Python for loop from MForStatement.

    Dispatches based on loop_type and analysis flags to generate
    the appropriate Python pattern:
    - BOUNDED: for loop with range() or while loop if loop var modified
    - OPEN_ENDED: for loop with itertools.count()
    - ARGUMENTLESS: while True
    - STRING_LIST: for loop with list
    - MIXED: for loop with itertools.chain()

    T038: If this FOR is the outermost target of a MULTI_LOOP_EXIT GOTO,
    wrap the entire loop in try/except _LoopExit.

    Args:
        stmt: MForStatement node
        ctx: Generator context
    """
    # T038: Check if this FOR needs try/except wrapper for multi-loop exit
    needs_wrapper = _for_needs_loop_exit_wrapper(stmt)

    if needs_wrapper:
        ctx.emitter.line("try:")
        ctx.emitter.indent()

    # Use ForGenContext for analysis-based dispatch
    for_ctx = ForGenContext.from_statement(stmt)

    # Dispatch based on loop type and analysis flags
    if for_ctx.loop_type == ForLoopType.ARGUMENTLESS:
        _generate_for_argumentless(stmt, for_ctx, ctx)
    elif for_ctx.loop_type == ForLoopType.OPEN_ENDED:
        _generate_for_open_ended(stmt, for_ctx, ctx)
    elif for_ctx.loop_type == ForLoopType.MIXED:
        _generate_for_mixed(stmt, for_ctx, ctx)
    elif for_ctx.use_while:
        # BOUNDED or STRING_LIST with loop var modification needs while loop
        _generate_for_while(stmt, for_ctx, ctx)
    elif for_ctx.loop_type == ForLoopType.STRING_LIST:
        _generate_for_string_list(stmt, for_ctx, ctx)
    else:
        # BOUNDED - standard for loop with range
        _generate_for_bounded(stmt, for_ctx, ctx)

    if needs_wrapper:
        ctx.emitter.dedent()
        ctx.emitter.line("except _LoopExit:")
        with ctx.emitter.indented():
            ctx.emitter.line("pass  # Multi-loop exit completed")


def _generate_for_body(stmt: MForStatement, ctx: "GeneratorContext") -> None:
    """Generate the body of a FOR loop.

    Manages the loop_stack to track FOR loop nesting for QUIT generation.

    Args:
        stmt: MForStatement node
        ctx: Generator context
    """
    # Push this FOR onto the loop stack
    ctx.loop_stack.append(stmt)
    try:
        if stmt.body and stmt.body.statements:
            for body_stmt in stmt.body.statements:
                generate_statement(body_stmt, ctx)
        else:
            ctx.emitter.line("pass")
    finally:
        # Pop the loop stack
        ctx.loop_stack.pop()


def _generate_for_bounded(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python for loop from bounded FOR (F I=1:1:10).

    Uses range() with adjusted end for MUMPS end-inclusive semantics.

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Get the single range parameter
    if not stmt.parameters or stmt.parameters[0].param_type != ForParamType.RANGE:
        raise NotImplementedError("Expected RANGE parameter for bounded FOR")

    param = stmt.parameters[0]
    if param.start is None or param.step is None or param.end is None:
        raise NotImplementedError("Incomplete FOR range parameters")

    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)
    end_expr = generate_expr(param.end, ctx)

    # MUMPS FOR is end-inclusive, Python range is end-exclusive
    # For positive step: range(start, end + 1, step)
    # For negative step: range(start, end - 1, step)
    ctx.emitter.line(f"_for_step = m_num({step_expr})")
    ctx.emitter.line(f"_for_end = m_num({end_expr}) + (1 if _for_step > 0 else -1)")
    ctx.emitter.line(
        f"for {for_ctx.loop_var} in range(m_num({start_expr}), _for_end, _for_step):"
    )

    with ctx.emitter.indented():
        _generate_for_body(stmt, ctx)


def _generate_for_string_list(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python for loop from string list FOR (F I="A","B","C").

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    values = []
    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE and param.value is not None:
            values.append(generate_expr(param.value, ctx))

    if not values:
        raise NotImplementedError("Empty string list FOR")

    values_str = ", ".join(values)
    ctx.emitter.line(f"for {for_ctx.loop_var} in [{values_str}]:")

    with ctx.emitter.indented():
        _generate_for_body(stmt, ctx)


def _generate_for_open_ended(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python for loop from open-ended FOR (F I=1:1).

    Uses itertools.count() for unbounded iteration.

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Get the open range parameter
    open_param = None
    for param in stmt.parameters:
        if param.param_type == ForParamType.OPEN_RANGE:
            open_param = param
            break

    if open_param is None or open_param.start is None or open_param.step is None:
        raise NotImplementedError("Invalid open-ended FOR parameters")

    start_expr = generate_expr(open_param.start, ctx)
    step_expr = generate_expr(open_param.step, ctx)

    ctx.emitter.line(
        f"for {for_ctx.loop_var} in count(m_num({start_expr}), m_num({step_expr})):"
    )

    with ctx.emitter.indented():
        _generate_for_body(stmt, ctx)


def _generate_for_argumentless(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python while True from argumentless FOR (F).

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    ctx.emitter.line("while True:")

    with ctx.emitter.indented():
        _generate_for_body(stmt, ctx)


def _generate_for_mixed(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python for loop from mixed FOR (F I=1:1:3,"X",10:2:14).

    Uses itertools.chain() to combine multiple iterables.

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Build list of iterables to chain together
    iterables = []

    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE:
            if param.value is not None:
                # Single value as a list
                value_expr = generate_expr(param.value, ctx)
                iterables.append(f"[{value_expr}]")
        elif param.param_type == ForParamType.RANGE:
            if param.start is None or param.step is None or param.end is None:
                raise NotImplementedError("Incomplete FOR range in mixed loop")
            start_expr = generate_expr(param.start, ctx)
            step_expr = generate_expr(param.step, ctx)
            end_expr = generate_expr(param.end, ctx)
            # Generate range with adjusted end for MUMPS end-inclusive semantics
            # We need to evaluate step to determine direction
            iterables.append(
                f"range(m_num({start_expr}), "
                f"m_num({end_expr}) + (1 if m_num({step_expr}) > 0 else -1), "
                f"m_num({step_expr}))"
            )
        elif param.param_type == ForParamType.OPEN_RANGE:
            if param.start is None or param.step is None:
                raise NotImplementedError("Incomplete open range in mixed loop")
            start_expr = generate_expr(param.start, ctx)
            step_expr = generate_expr(param.step, ctx)
            iterables.append(f"count(m_num({start_expr}), m_num({step_expr}))")

    if not iterables:
        raise NotImplementedError("Empty mixed FOR parameters")

    chain_args = ", ".join(iterables)
    ctx.emitter.line(f"for {for_ctx.loop_var} in chain({chain_args}):")

    with ctx.emitter.indented():
        _generate_for_body(stmt, ctx)


def _generate_for_while(
    stmt: MForStatement, for_ctx: ForGenContext, ctx: "GeneratorContext"
) -> None:
    """Generate Python while loop for FOR with modified loop variable.

    When the loop variable is modified inside the body, we can't use
    Python's for loop because it would overwrite the modification.
    Instead we use a while loop with explicit stepping.

    Args:
        stmt: MForStatement node
        for_ctx: FOR loop context with analysis
        ctx: Generator context
    """
    # Currently supports single RANGE parameter only
    if not stmt.parameters:
        raise NotImplementedError("While loop requires FOR parameters")

    param = stmt.parameters[0]
    if param.param_type != ForParamType.RANGE:
        raise NotImplementedError(
            "While loop for modified loop var only supports RANGE"
        )

    if param.start is None or param.step is None or param.end is None:
        raise NotImplementedError("Incomplete FOR range parameters for while loop")

    start_expr = generate_expr(param.start, ctx)
    step_expr = generate_expr(param.step, ctx)
    end_expr = generate_expr(param.end, ctx)

    # Initialize loop variable
    ctx.emitter.line(f"{for_ctx.loop_var} = m_num({start_expr})")
    ctx.emitter.line(f"_for_step = m_num({step_expr})")
    ctx.emitter.line(f"_for_end = m_num({end_expr})")

    # While condition: check bounds based on step direction
    # Positive step: loop_var <= end
    # Negative step: loop_var >= end
    ctx.emitter.line(
        f"while (_for_step > 0 and {for_ctx.loop_var} <= _for_end) or "
        f"(_for_step < 0 and {for_ctx.loop_var} >= _for_end):"
    )

    with ctx.emitter.indented():
        _generate_for_body(stmt, ctx)
        # Increment loop variable at end of iteration
        ctx.emitter.line(f"{for_ctx.loop_var} = {for_ctx.loop_var} + _for_step")


def _generate_goto(stmt: MGotoStatement, ctx: "GeneratorContext") -> None:
    """Generate code from MGotoStatement.

    GOTO transfers control to a label. The generated Python depends on context:
    - Single loop exit: generate `break`
    - Multi-loop exit: generate `raise _LoopExit()`
    - Cross-label jump: generate function call + return

    Note: There is no "continue" pattern. Per MUMPS spec (MDC 3.6.5):
    "Execution of GOTO effects the immediate termination of all FORs
    in the line containing the GOTO." A GOTO to the same label creates
    a function call/recursion, not continue semantics.

    Example patterns:
    - G DONE (cross-label) → DONE(); return
    - G DONE (inside FOR, exiting loop) → break
    - G DONE (inside nested FOR) → raise _LoopExit()

    Args:
        stmt: MGotoStatement node
        ctx: Generator context

    Raises:
        NotImplementedError: For unsupported GOTO patterns
        UnsupportedFeatureError: For backward intra-label GOTO (requires Spec 006)
    """
    if not stmt.targets:
        raise NotImplementedError("Argumentless GOTO not supported")

    if len(stmt.targets) > 1:
        raise NotImplementedError("Multiple GOTO targets not yet supported")

    target = stmt.targets[0]

    # Check for external routine reference
    if target.routine:
        raise NotImplementedError("External routine GOTO not yet supported")

    # Check for indirection
    if target.label_is_indirect or target.indirection:
        raise NotImplementedError("Indirect GOTO not yet supported")

    # Check for backward intra-label GOTO (creates implicit loops)
    # These cannot be restructured to simple if/else and require Spec 006
    goto_type = getattr(stmt, "goto_type", None)
    is_cross_label = getattr(stmt, "is_cross_label", True)
    exits_loops = getattr(stmt, "exits_loops", [])

    if goto_type == GotoType.BACKWARD_JUMP and not is_cross_label:
        raise UnsupportedFeatureError(
            "Backward intra-label GOTO creates implicit loop - not yet supported. "
            "See Spec 006 for loop detection patterns."
        )

    # Phase 7 (US5): Loop exit patterns
    # Note: There is no "continue" pattern - GOTO cannot create continue semantics.
    # Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
    # termination of all FORs in the line containing the GOTO."
    # Check if this GOTO is inside a FOR loop (from loop_stack)
    in_for_loop = len(ctx.loop_stack) > 0

    # T035/T037: exits_loops determines break vs raise _LoopExit()
    if exits_loops and in_for_loop:
        if len(exits_loops) == 1:
            # Single loop exit - generate break
            ctx.emitter.line("break")
            return
        else:
            # Multi-loop exit - generate raise _LoopExit()
            # The exception will be caught by the outermost FOR loop
            ctx.emitter.line("raise _LoopExit()")
            return

    # Default: cross-label GOTO as function call
    # Get the label name and translate it
    label_name = translate_name(target.name)

    # Generate: label(); return
    # The return ensures control doesn't continue after GOTO
    ctx.emitter.line(f"{label_name}()")
    ctx.emitter.line("return")


def _generate_do(stmt: MDoStatement, ctx: "GeneratorContext") -> None:
    """Generate function call from MDoStatement.

    DO calls a subroutine and returns to the caller.
    Unlike GOTO, control continues after DO returns.

    $TEST Stacking (verified against YottaDB):
    - Label calls (D SUB, D SUB(), D SUB(X)) do NOT stack $TEST
      Callee's $TEST changes ARE visible to caller
    - DO blocks (D followed by dot-indented lines) DO stack $TEST
      Caller's $TEST is saved before and restored after

    Example: D SUB → SUB()  (no save/restore)

    Args:
        stmt: MDoStatement node
        ctx: Generator context

    Raises:
        NotImplementedError: For unsupported DO patterns
    """
    # Check for argumentless DO block (inline block with body)
    # This is the ONLY case where $TEST is stacked
    if _is_do_block(stmt):
        # Save $TEST before block
        ctx.emitter.line("_saved_test = _test")
        # Generate block body
        for body_stmt in stmt.body.statements:
            generate_statement(body_stmt, ctx)
        # Restore $TEST after block
        ctx.emitter.line("_test = _saved_test")
        return

    # Check for argumentless DO without body (standalone D on a line)
    if not stmt.targets:
        raise NotImplementedError("Argumentless DO blocks not yet supported")

    # Label calls - NO $TEST save/restore
    # Handle each target (multiple targets allowed: D A,B,C)
    for target in stmt.targets:
        # Check for external routine reference
        if target.routine:
            raise NotImplementedError("External routine DO not yet supported")

        # Check for indirection
        if target.label_is_indirect or target.indirection:
            raise NotImplementedError("Indirect DO not yet supported")

        # Get the label name and translate it
        label_name = translate_name(target.name)

        # Generate arguments if any
        args = _generate_call_arguments(target.arguments, ctx)

        # Generate function call (no return - control continues after DO)
        ctx.emitter.line(f"{label_name}({args})")


__all__ = [
    "generate_statement",
    "generate_scope_statements",
    "ForGenContext",
    "GotoGenContext",
    "_is_do_block",
    "_is_restructurable_goto",
    "_generate_call_arguments",
]
