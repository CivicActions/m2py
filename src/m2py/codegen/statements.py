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
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.expressions import generate_expr
from m2py.codegen.names import translate_name

if TYPE_CHECKING:
    from m2py.asg.elements import MCall
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
    def from_statement(
        cls,
        stmt: MForStatement,
        ctx: "GeneratorContext | None" = None,
    ) -> "ForGenContext":
        """Create ForGenContext from an MForStatement.

        Args:
            stmt: The FOR statement to analyze
            ctx: Optional generator context for strategy-aware naming

        Returns:
            ForGenContext with analysis results

        Raises:
            ValueError: If loop_type was not set by analysis
        """
        # Get loop variable name
        if isinstance(stmt.loop_var, str):
            var_name = stmt.loop_var if stmt.loop_var else "_"
            loop_var = translate_name(var_name)
        elif isinstance(stmt.loop_var, MVariable):
            var_name = stmt.loop_var.name
            loop_var = translate_name(var_name)
        else:
            var_name = "_"
            loop_var = "_"  # Fallback for complex expressions

        # Spec 006: Check if loop var should use state for trampoline
        if (
            ctx
            and ctx.strategy == GotoStrategy.TRAMPOLINE
            and var_name in ctx.state_vars
        ):
            loop_var = f"state.{translate_name(var_name)}"

        # Read analysis results - ASG fields have defaults, analysis passes populate them
        use_while = stmt.loop_var_modified_in_body
        needs_break = stmt.has_internal_quit or stmt.has_internal_goto
        is_infinite = stmt.is_infinite or not stmt.parameters

        # T095: loop_type is now always set by analysis - no fallback needed
        loop_type = stmt.loop_type
        if loop_type is None:
            raise ValueError(
                "MForStatement.loop_type not set - ensure analyze_for_loops() was called"
            )

        return cls(
            stmt=stmt,
            loop_var=loop_var,
            use_while=use_while,
            needs_break=needs_break,
            is_infinite=is_infinite,
            loop_type=loop_type,
        )


# T092-T094: Removed _for_needs_loop_exit_wrapper(), _for_has_cross_label_exit(),
# and _get_multi_loop_exit_target() - now using pre-computed ASG fields:
# - MForStatement.needs_exception_wrapper
# - MForStatement.has_cross_label_exit
# - MForStatement.exit_target


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
    def from_statement(cls, stmt: MGotoStatement) -> "GotoGenContext":
        """Create GotoGenContext from an MGotoStatement.

        Uses ASG fields populated by classify_gotos() analysis.

        Args:
            stmt: The GOTO statement to analyze

        Returns:
            GotoGenContext with analysis results
        """
        # exits_loops is populated by classify_gotos() analysis
        exits_loops = stmt.exits_loops or []
        in_for_loop = len(exits_loops) > 0
        enclosing_loops = list(exits_loops)

        # Get target label name
        target_label = ""
        if stmt.targets:
            target = stmt.targets[0]
            target_label = translate_name(target.name) if target.name else ""

        # T101: Read pre-computed codegen_pattern from analysis instead of recomputing
        # Map GotoCodegenPattern enum to string pattern for backward compatibility
        from m2py.asg.enums import GotoCodegenPattern

        pattern_map = {
            GotoCodegenPattern.BREAK: "break",
            GotoCodegenPattern.MULTI_BREAK: "multi_break",
            GotoCodegenPattern.FORWARD: "forward",
            GotoCodegenPattern.FUNCTION_CALL: "function_call",
            GotoCodegenPattern.UNSUPPORTED: "unsupported",
        }

        if stmt.codegen_pattern is not None:
            pattern = pattern_map.get(stmt.codegen_pattern, "function_call")
        else:
            # Fallback for GOTOs where analysis hasn't run (shouldn't happen)
            pattern = "function_call"

        return cls(
            stmt=stmt,
            in_for_loop=in_for_loop,
            enclosing_loops=enclosing_loops,
            target_label=target_label,
            pattern=pattern,
        )


# T100: Removed _is_restructurable_goto() - now using pre-computed
# MGotoStatement.is_restructurable field populated by classify_gotos()


def _find_forward_goto_in_if(if_stmt: MIfStatement) -> "MGotoStatement | None":
    """Find a restructurable forward GOTO in an IF's then_scope.

    Uses pre-computed MIfStatement.restructurable_goto field set by
    classify_gotos() analysis. Avoids scanning at codegen time.

    Args:
        if_stmt: The MIfStatement to check

    Returns:
        The MGotoStatement if found and restructurable, None otherwise
    """
    return if_stmt.restructurable_goto


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
    # Get target statement index from analysis (populated by classify_gotos)
    target_idx = goto.target_stmt_index

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


def generate_offset_guarded_statements(
    statements: List["MStatement"],
    label_line: int,
    ctx: "GeneratorContext",
) -> None:
    """Generate statements with offset guards for computed offset support.

    Spec 007 (T021): Each statement is wrapped with an offset guard that
    checks if the statement should be skipped based on _start_offset.

    The guard is: if _start_offset <= offset:
    where offset = statement.line_number - label.line_number

    This ensures that when entering a label at offset N, statements
    at offsets 0 through N-1 are skipped.

    Args:
        statements: List of statements to generate
        label_line: Line number of the containing label (for offset calculation)
        ctx: Generator context
    """
    for stmt in statements:
        stmt_line = stmt.line_number
        if stmt_line is not None:
            # Calculate offset from label line
            offset = stmt_line - label_line
            ctx.emitter.line(f"if _start_offset <= {offset}:")
            with ctx.emitter.indented():
                generate_statement(stmt, ctx)
        else:
            # No line number - always execute (shouldn't happen normally)
            generate_statement(stmt, ctx)


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

    Spec 006: When using TRAMPOLINE strategy and the variable is in state_vars,
    assign to `state.VAR` instead of just `VAR`.

    Spec 006 (T075): Handle subscripted assignments for MArray-backed variables.
    For array variables, generate: state.A[subscripts] = value

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
            var_name = assignment.target.name

            # Spec 006 (T075): Handle subscripted array assignments
            if assignment.target.subscripts:
                # Generate subscript expressions
                subscript_exprs = [
                    generate_expr(sub, ctx) for sub in assignment.target.subscripts
                ]

                # Determine base variable access
                if (
                    ctx.strategy == GotoStrategy.TRAMPOLINE
                    and var_name in ctx.array_vars
                ):
                    # MArray in RoutineState: state.A[subscripts] = value
                    base = f"state.{target_name}"
                else:
                    # Local MArray variable: A[subscripts] = value
                    base = target_name

                # Format subscripts: single key or tuple
                if len(subscript_exprs) == 1:
                    target_expr = f"{base}[{subscript_exprs[0]}]"
                else:
                    target_expr = f"{base}[{', '.join(subscript_exprs)}]"

                # Generate value expression and emit assignment
                value_expr = generate_expr(assignment.value, ctx)
                ctx.emitter.line(f"{target_expr} = {value_expr}")
                continue

            # Spec 006: Check if variable should be accessed via state
            if ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars:
                target_name = f"state.{target_name}"
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
            # Runtime handles None -> empty string conversion (MUMPS undefined semantics)
            expr = generate_expr(arg, ctx)
            ctx.emitter.line(f"_rt.write({expr})")
        # Skip format controls for now (!, #, ?n) - Phase 2 scope is basic only


def _generate_quit(stmt: MQuitStatement, ctx: "GeneratorContext") -> None:
    """Generate break or return statement from MQuitStatement.

    MUMPS QUIT has context-dependent behavior:
    - With return value: returns value from extrinsic (Python: return value)
    - Inside a FOR loop: exits the FOR loop (Python: break)
    - Inside a DO block: exits the DO block only (Python: break from while True)
    - Otherwise: returns from label/routine (Python: return or return (None, state))

    Priority order (checked first to last):
    1. return_value -> return <expr>
    2. exits_for (from ASG) -> break
    3. exits_do_block (from ASG) -> break (exit DO block's while True)
    4. default -> return (or return (None, state) for trampoline)

    Args:
        stmt: MQuitStatement node
        ctx: Generator context
    """
    # T045: QUIT with return value (extrinsic function return)
    if stmt.return_value is not None:
        value_expr = generate_expr(stmt.return_value, ctx)
        ctx.emitter.line(f"return {value_expr}")
        return

    # T108: exits_for is set by analyze_quit_context() for QUITs inside FOR loops
    if stmt.exits_for is not None:
        # Inside a FOR loop - QUIT exits the innermost FOR
        ctx.emitter.line("break")
        return

    # T109: exits_do_block is set by analyze_quit_context() for QUITs inside DO blocks
    if stmt.exits_do_block is not None:
        # Inside a DO block - QUIT exits only the block (break from while True)
        ctx.emitter.line("break")
        return

    # Spec 006 (T069a): Self-loop pattern - QUIT exits the while True: loop
    if ctx.current_label and ctx.current_label.has_self_loop:
        ctx.emitter.line("break")
        return

    # T059: Plain QUIT with by-ref outputs - return modified params as tuple
    # Check if current label has byref_outputs that need to be returned
    if (
        ctx.current_label
        and ctx.current_label.signature
        and ctx.current_label.signature.byref_outputs
    ):
        byref_outputs = ctx.current_label.signature.byref_outputs
        # Return byref params in formal_params order (for consistent tuple unpacking)
        formal_params = ctx.current_label.signature.formal_params
        return_vars = [translate_name(p) for p in formal_params if p in byref_outputs]
        if return_vars:
            ctx.emitter.line(f"return {', '.join(return_vars)}")
            return

    # Spec 006: Trampoline pattern - return (None, state) to signal exit
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        ctx.emitter.line("return (None, state)")
        return

    # Plain QUIT outside FOR/DO block - return from function/routine
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

    FR-018: Cross-label loop exits must call the target label after exiting.

    Args:
        stmt: MForStatement node
        ctx: Generator context
    """
    # T038: Check if this FOR needs try/except wrapper for multi-loop exit
    # T091: Use pre-computed field from analysis instead of helper function
    needs_wrapper = stmt.needs_exception_wrapper

    # FR-018: Check if this FOR has cross-label single-loop exits
    # T091: Use pre-computed field from analysis instead of helper function
    has_cross_label_exit = stmt.has_cross_label_exit

    # FR-018: Initialize goto tracking before loop if needed
    if has_cross_label_exit and not needs_wrapper:
        if ctx.strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("_goto_label = None")
        else:
            ctx.emitter.line("_goto_target = None")

    if needs_wrapper:
        ctx.emitter.line("try:")
        ctx.emitter.indent()

    # Use ForGenContext for analysis-based dispatch
    for_ctx = ForGenContext.from_statement(stmt, ctx)

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
        ctx.emitter.line("except _LoopExit as _e:")
        with ctx.emitter.indented():
            # FR-018: Call/return to target label if provided
            ctx.emitter.line("if _e.target is not None:")
            with ctx.emitter.indented():
                if ctx.strategy == GotoStrategy.TRAMPOLINE:
                    ctx.emitter.line("return (_e.target, state)")
                else:
                    ctx.emitter.line("_e.target()")
                    ctx.emitter.line("return")

    # FR-018: Handle target after single-loop exit if set
    if has_cross_label_exit and not needs_wrapper:
        if ctx.strategy == GotoStrategy.TRAMPOLINE:
            ctx.emitter.line("if _goto_label is not None:")
            with ctx.emitter.indented():
                ctx.emitter.line("return (_goto_label, state)")
        else:
            ctx.emitter.line("if _goto_target is not None:")
            with ctx.emitter.indented():
                ctx.emitter.line("_goto_target()")
                ctx.emitter.line("return")


def _generate_for_body(stmt: MForStatement, ctx: "GeneratorContext") -> None:
    """Generate the body of a FOR loop.

    The QUIT context (exits_for) is set by analyze_quit_context() during analysis,
    so no runtime tracking is needed here.

    Args:
        stmt: MForStatement node
        ctx: Generator context
    """
    if stmt.body and stmt.body.statements:
        for body_stmt in stmt.body.statements:
            generate_statement(body_stmt, ctx)
    else:
        ctx.emitter.line("pass")


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
    - Cross-label jump (SIMPLE_FUNCTIONS): generate function call + return
    - Cross-label jump (TRAMPOLINE): generate return (label_name, state)

    Multiple targets (Phase 11):
    - Targets evaluated left-to-right
    - If target has postcondition and it's false, try next target
    - If postcondition is true or no postcondition, go to that target
    - If all postconditions false, no jump (continue to next command)

    Note: There is no "continue" pattern. Per MUMPS spec (MDC 3.6.5):
    "Execution of GOTO effects the immediate termination of all FORs
    in the line containing the GOTO." A GOTO to the same label creates
    a function call/recursion, not continue semantics.

    Example patterns:
    - G DONE (cross-label, SIMPLE) → DONE(); return
    - G DONE (cross-label, TRAMPOLINE) → return ("DONE", state)
    - G A,B → go to A (targets evaluated left-to-right)
    - G A:cond,B → if cond: go to A, else: go to B
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

    # Phase 11 (T098-T100): Handle multiple targets
    if len(stmt.targets) > 1:
        _generate_multi_target_goto(stmt, ctx)
        return

    target = stmt.targets[0]
    _generate_single_target_goto(target, stmt, ctx)


def _generate_single_target_goto(
    target: "MCall", stmt: MGotoStatement, ctx: "GeneratorContext"
) -> None:
    """Generate GOTO code for a single target.

    This handles all single-target cases including loop exits and cross-label jumps.

    Args:
        target: The MCall target to jump to
        stmt: The parent MGotoStatement (for classification info)
        ctx: Generator context
    """
    # Check for external routine reference
    if target.routine:
        raise NotImplementedError("External routine GOTO not yet supported")

    # Check for indirection
    if target.label_is_indirect or target.indirection:
        raise NotImplementedError("Indirect GOTO not yet supported")

    # Check for backward intra-label GOTO (creates implicit loops)
    # These cannot be restructured to simple if/else and require Spec 006
    # ASG fields populated by classify_gotos() analysis
    goto_type = stmt.goto_type
    is_cross_label = stmt.is_cross_label
    exits_loops = stmt.exits_loops

    # Spec 006 (T069a): Self-loop pattern - backward intra-label GOTO
    # When label has has_self_loop=True, body is wrapped in while True:
    # and this GOTO becomes continue to restart the loop
    if goto_type == GotoType.BACKWARD_JUMP and not is_cross_label:
        # Self-loop: generate continue to restart the while True: loop
        ctx.emitter.line("continue")
        return

    # Phase 7 (US5): Loop exit patterns
    # Note: There is no "continue" pattern - GOTO cannot create continue semantics.
    # Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
    # termination of all FORs in the line containing the GOTO."
    # exits_loops is populated by classify_gotos() analysis
    in_for_loop = bool(exits_loops)

    # T035/T037: exits_loops determines break vs raise _LoopExit()
    if exits_loops and in_for_loop:
        if len(exits_loops) == 1:
            # Single loop exit - generate break
            # FR-018: For cross-label exits, track target so it can be called after loop
            if is_cross_label and target is not None:
                if ctx.strategy == GotoStrategy.TRAMPOLINE:
                    # Trampoline: store label name as string
                    ctx.emitter.line(f'_goto_label = "{target.name}"')
                else:
                    # Simple functions: store function reference
                    label_name = translate_name(target.name)
                    ctx.emitter.line(f"_goto_target = {label_name}")
            ctx.emitter.line("break")
            return
        else:
            # Multi-loop exit - generate raise _LoopExit()
            # The exception will be caught by the outermost FOR loop
            # FR-018: Pass target label name so it can be called in except block
            if is_cross_label and target is not None:
                if ctx.strategy == GotoStrategy.TRAMPOLINE:
                    # Trampoline: pass label name as string
                    ctx.emitter.line(f'raise _LoopExit("{target.name}")')
                else:
                    # Simple functions: pass function reference
                    label_name = translate_name(target.name)
                    ctx.emitter.line(f"raise _LoopExit({label_name})")
            else:
                ctx.emitter.line("raise _LoopExit()")
            return

    # Cross-label GOTO: pattern depends on strategy
    # Spec 006 (T055): Check strategy and generate appropriate pattern
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        # Spec 007 (T015-T017): Check for offset and emit line-based dispatch
        if target.offset is not None:
            # Offset GOTO: compute target line = label_line + offset
            # The dispatcher will look up (label, offset) in _line_map
            if target.target is None or target.target.line_number is None:
                raise UnsupportedFeatureError(
                    f"Cannot resolve offset GOTO target: {target.name}"
                )
            label_line = target.target.line_number
            offset_code = generate_expr(target.offset, ctx)
            # Spec 007 Phase 7 (T035-T037): Validate offset and raise descriptive error
            # Spec 007 Phase 9 (T045-T046): Skip non-executable lines (comments/blanks)
            # Spec 007: Check for negative offset (must resolve to non-negative integer)
            # Use m_num() to apply MUMPS numeric coercion (string→number) before int()
            ctx.emitter.line(f"_offset_val = int(m_num({offset_code}))")
            ctx.emitter.line("if _offset_val < 0:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    f'raise ValueError("Entry point {target.name}+" '
                    '+ str(_offset_val) + " not valid")'
                )
            ctx.emitter.line(f"_target = {label_line} + _offset_val")
            ctx.emitter.line("if _target not in _line_map:")
            with ctx.emitter.indented():
                # Find next executable line after target
                ctx.emitter.line(
                    "_next = min((ln for ln in _line_map if ln > _target), default=None)"
                )
                ctx.emitter.line("if _next is None:")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        f'raise ValueError("Entry point {target.name}+" '
                        '+ str(_offset_val) + " not valid")'
                    )
                ctx.emitter.line("_target = _next")
            ctx.emitter.line("return (_target, state)")
        else:
            # Trampoline pattern: return (label_name, state) tuple
            # The trampoline dispatcher will call the target label
            ctx.emitter.line(f'return ("{target.name}", state)')
    else:
        # SIMPLE_FUNCTIONS pattern: function call + return
        # Get the label name and translate it
        label_name = translate_name(target.name)

        # Generate: label(); return
        # The return ensures control doesn't continue after GOTO
        ctx.emitter.line(f"{label_name}()")
        ctx.emitter.line("return")


def _generate_multi_target_goto(stmt: MGotoStatement, ctx: "GeneratorContext") -> None:
    """Generate GOTO code for multiple targets (Phase 11).

    Multiple targets are evaluated left-to-right:
    - If target has no postcondition, jump to it unconditionally
    - If target has postcondition and it's true, jump to it
    - If postcondition is false, try next target
    - If all postconditions are false, no jump (fall through)

    Generated pattern (for G A:cond1,B:cond2,C):
        if m_truth(cond1):
            return ("A", state)
        elif m_truth(cond2):
            return ("B", state)
        else:
            return ("C", state)

    Args:
        stmt: MGotoStatement with multiple targets
        ctx: Generator context
    """
    targets = stmt.targets

    # Check for unsupported patterns in multi-target GOTO
    for target in targets:
        if target.routine:
            raise NotImplementedError(
                "External routine in multi-target GOTO not supported"
            )
        if target.label_is_indirect or target.indirection:
            raise NotImplementedError(
                "Indirect target in multi-target GOTO not supported"
            )

    # Check if any targets have postconditions
    has_postconditions = any(t.postcondition is not None for t in targets)

    if not has_postconditions:
        # No postconditions: just go to first target
        # This is semantically equivalent to single-target GOTO
        first_target = targets[0]
        _generate_single_target_goto(first_target, stmt, ctx)
        return

    # Generate if/elif chain for postconditioned targets
    first = True
    last_unconditional = None

    for i, target in enumerate(targets):
        if target.postcondition is not None:
            # Generate condition check
            cond_expr = generate_expr(target.postcondition, ctx)

            if first:
                ctx.emitter.line(f"if m_truth({cond_expr}):")
                first = False
            else:
                ctx.emitter.line(f"elif m_truth({cond_expr}):")

            # Generate jump inside condition block
            with ctx.emitter.indented():
                _generate_goto_jump(target, ctx)
        else:
            # Unconditional target (no postcondition) - save for else block
            # This should be the last one if there are conditional targets before it
            last_unconditional = target

    # If there's an unconditional target at the end, it goes in else block
    if last_unconditional is not None:
        if first:
            # No conditions at all - just jump (shouldn't happen, but handle it)
            _generate_goto_jump(last_unconditional, ctx)
        else:
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                _generate_goto_jump(last_unconditional, ctx)
    elif not first:
        # All targets had postconditions - need to handle "no match" case
        # This means no GOTO taken, execution continues
        # We need a pass to make the if/elif syntactically correct, but
        # actually we don't need an else at all - just let it fall through
        pass


def _generate_goto_jump(target: "MCall", ctx: "GeneratorContext") -> None:
    """Generate the actual jump code for a GOTO target.

    This generates just the jump statement without any condition checks.
    For trampoline: return (label_name, state)
    For simple functions: function_call(); return

    Args:
        target: The MCall target to jump to
        ctx: Generator context
    """
    if ctx.strategy == GotoStrategy.TRAMPOLINE:
        ctx.emitter.line(f'return ("{target.name}", state)')
    else:
        label_name = translate_name(target.name)
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
    # The is_inline_block field is set by the parser when dot-indented lines are collected
    if stmt.is_inline_block:
        # Save $TEST before block
        ctx.emitter.line("_saved_test = _test")

        # Wrap in while True: so QUIT can use break to exit only the block
        # This is a single-iteration "loop" used for early exit support
        # The exits_do_block field is set by analyze_quit_context() during analysis,
        # so no runtime depth tracking is needed here.
        ctx.emitter.line("while True:  # DO block")
        with ctx.emitter.indented():
            # Generate block body
            for body_stmt in stmt.body.statements:
                generate_statement(body_stmt, ctx)
            # Always break at end to ensure single iteration
            ctx.emitter.line("break")

        # Restore $TEST after block
        ctx.emitter.line("_test = _saved_test")
        return

    # Check for argumentless DO without body (standalone D on a line)
    if not stmt.targets:
        raise NotImplementedError("Argumentless DO blocks not yet supported")

    # Label calls - NO $TEST save/restore
    # Handle each target (multiple targets allowed: D A,B,C)
    for target in stmt.targets:
        # Check for indirection
        if target.label_is_indirect or target.indirection:
            raise NotImplementedError("Indirect DO not yet supported")

        # Spec 008 (T018-T029): Handle external routine reference D ^ROUTINE
        if target.routine:
            routine_name = target.routine

            # Generate import statement
            ctx.emitter.line(f"import {routine_name}")

            # Handle different external DO patterns
            if target.offset is not None:
                # D LABEL+N^ROUTINE or D +N^ROUTINE - uses line dispatch
                offset_code = generate_expr(target.offset, ctx)

                if target.name:
                    # T024: D LABEL+N^ROUTINE - label + offset
                    # Check label exists in _label_lines
                    ctx.emitter.line(
                        f"if {target.name!r} not in {routine_name}._label_lines:"
                    )
                    with ctx.emitter.indented():
                        ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                        ctx.emitter.line(
                            f"raise LabelNotFoundError({target.name!r}, {routine_name!r}, "
                            f"list({routine_name}._label_lines.keys()))"
                        )
                    # Calculate target line from label's line + offset
                    ctx.emitter.line(
                        f"_target_line = {routine_name}._label_lines[{target.name!r}] + {offset_code}"
                    )
                else:
                    # T025: D +N^ROUTINE - absolute line offset (1-based to 0-indexed)
                    ctx.emitter.line(f"_target_line = {offset_code} - 1")

                # T029: Call via line dispatch map, passing _scope for cross-routine visibility
                ctx.emitter.line(
                    f"{routine_name}._line_map[_target_line](_scope=_scope)"
                )
            elif target.name:
                # T022-T023: D LABEL^ROUTINE - call specific label
                label_name = translate_name(target.name)
                # T026: Generate LabelNotFoundError check
                ctx.emitter.line(f"if not hasattr({routine_name}, {label_name!r}):")
                with ctx.emitter.indented():
                    ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                    ctx.emitter.line(
                        f"raise LabelNotFoundError({target.name!r}, {routine_name!r}, "
                        f"list({routine_name}._label_lines.keys()))"
                    )
                # T029: Pass _scope for cross-routine variable visibility (as keyword arg)
                args = _generate_call_arguments(target.arguments, ctx)
                if args:
                    ctx.emitter.line(
                        f"{routine_name}.{label_name}({args}, _scope=_scope)"
                    )
                else:
                    ctx.emitter.line(f"{routine_name}.{label_name}(_scope=_scope)")
            else:
                # D ^ROUTINE - call entry label (same name as routine)
                entry_label = translate_name(routine_name)
                # T029: Pass _scope for cross-routine variable visibility (as keyword arg)
                args = _generate_call_arguments(target.arguments, ctx)
                if args:
                    ctx.emitter.line(
                        f"{routine_name}.{entry_label}({args}, _scope=_scope)"
                    )
                else:
                    ctx.emitter.line(f"{routine_name}.{entry_label}(_scope=_scope)")
            continue

        # Get the label name and translate it
        label_name = translate_name(target.name)

        # Generate arguments if any
        args = _generate_call_arguments(target.arguments, ctx)

        # Spec 007 (T025-T028c): Handle DO with offset
        # In TRAMPOLINE strategy, call the internal function with _start_offset
        if target.offset is not None and ctx.strategy == GotoStrategy.TRAMPOLINE:
            # Prefix with _ for internal trampoline function
            internal_func = "_" + label_name
            # Generate offset expression code
            offset_code = generate_expr(target.offset, ctx)

            # Spec 007 Phase 7 (T035-T037): Validate offset for DO as well
            # Spec 007 Phase 9 (T045-T046): Skip non-executable lines (comments/blanks)
            # Get the label's line number for validation
            if target.target is not None and target.target.line_number is not None:
                label_line = target.target.line_number
                # Spec 007: Check for negative offset (must resolve to non-negative integer)
                # Use m_num() to apply MUMPS numeric coercion (string→number) before int()
                ctx.emitter.line(f"_offset_val = int(m_num({offset_code}))")
                ctx.emitter.line("if _offset_val < 0:")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        f'raise ValueError("Entry point {target.name}+" '
                        '+ str(_offset_val) + " not valid")'
                    )
                ctx.emitter.line(f"_target = {label_line} + _offset_val")
                ctx.emitter.line("if _target not in _line_map:")
                with ctx.emitter.indented():
                    # Find next executable line after target
                    ctx.emitter.line(
                        "_next = min((ln for ln in _line_map if ln > _target), "
                        "default=None)"
                    )
                    ctx.emitter.line("if _next is None:")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            f'raise ValueError("Entry point {target.name}+" '
                            '+ str(_offset_val) + " not valid")'
                        )
                    ctx.emitter.line("_target = _next")
                # Now update the offset based on the new target line
                ctx.emitter.line(
                    f"_offset = _line_map[_target][1] if _target != {label_line} + "
                    "_offset_val else _offset_val"
                )

            # Build call with state and _start_offset
            # Note: args handling with offset is complex - for now just handle simple case
            if args:
                ctx.emitter.line(
                    f"{internal_func}(state, {args}, _start_offset=_offset_val)"
                )
            else:
                ctx.emitter.line(f"{internal_func}(state, _start_offset=_offset_val)")
            continue

        # T060-T062: Check callee signature for byref_outputs and generate destructuring
        callee_signature = None
        if hasattr(target, "target") and target.target:
            callee_label = target.target
            if hasattr(callee_label, "signature") and callee_label.signature:
                callee_signature = callee_label.signature

        if callee_signature and callee_signature.byref_outputs:
            # Map byref formal params to actual variables passed by reference
            # The callee returns byref params in formal_params order
            formal_params = callee_signature.formal_params
            byref_outputs = callee_signature.byref_outputs
            actual_args = target.arguments or []

            # Build list of caller variables that receive returned values
            # Only include params that are both:
            # 1. In byref_outputs (callee modifies them)
            # 2. Passed by reference at call site (.VAR syntax)
            return_vars = []
            for i, formal_name in enumerate(formal_params):
                if formal_name in byref_outputs:
                    # Check if corresponding actual was passed by reference
                    if i < len(actual_args):
                        actual = actual_args[i]
                        if actual.passing_mode == PassingMode.BY_REFERENCE:
                            # Get the caller's variable name
                            if actual.variable_name:
                                return_vars.append(translate_name(actual.variable_name))

            if return_vars:
                # Generate tuple destructuring: X = INCR(X) or A, B = SWAP(A, B)
                lhs = ", ".join(return_vars)
                ctx.emitter.line(f"{lhs} = {label_name}({args})")
            else:
                # No by-ref params at call site - just call
                ctx.emitter.line(f"{label_name}({args})")
        else:
            # No byref_outputs - simple call
            ctx.emitter.line(f"{label_name}({args})")


__all__ = [
    "generate_statement",
    "generate_scope_statements",
    "ForGenContext",
    "GotoGenContext",
    "_generate_call_arguments",
]
