"""Statement code generation for MUMPS-to-Python transpilation.

Generates Python statements from MUMPS ASG statement nodes.
Handles SET, WRITE, QUIT, IF, ELSE, FOR, and other basic commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from m2py.asg.enums import ForLoopType, ForParamType
from m2py.asg.expressions import MExpr, MVariable
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
# Spec 005: Code Generation Context Helpers
# =============================================================================


def _is_argumentless_do(stmt: MDoStatement) -> bool:
    """Check if this is an argumentless DO (label call without parameters).

    Argumentless DO calls have $TEST stacking semantics - the caller's $TEST
    is saved before the call and restored after. This differs from DO with
    arguments where $TEST changes are visible to the caller.

    This function detects DO calls where the target has no argument list,
    NOT the argumentless DO block (which has no targets at all).

    Per MUMPS spec:
    - D SUB      -> argumentless (no args, $TEST stacked)
    - D SUB()    -> with empty args ($TEST NOT stacked)
    - D SUB(X)   -> with args ($TEST NOT stacked)
    - D          -> DO block (different handling, body not empty)

    Args:
        stmt: The MDoStatement to check

    Returns:
        True if this is an argumentless DO label call
    """
    # DO block (body populated) is handled separately
    if not stmt.targets:
        return False

    # Check first target for arguments
    for target in stmt.targets:
        # If target has an argument list (even empty), it's NOT argumentless
        # MCall uses 'arguments' field, not 'args'
        if target.arguments:
            return False

    return True


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
    pattern: str  # 'continue' | 'break' | 'multi_break' | 'forward' | 'function_call' | 'unsupported'

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
        is_loop_continue = getattr(stmt, "is_loop_continue", False)
        exits_loops = getattr(stmt, "exits_loops", [])
        goto_type = getattr(stmt, "goto_type", None)
        is_cross_label = getattr(stmt, "is_cross_label", False)

        if is_loop_continue and in_for_loop:
            pattern = "continue"
        elif exits_loops:
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
    """Generate return statement from MQuitStatement.

    Args:
        stmt: MQuitStatement node
        ctx: Generator context
    """
    if stmt.return_value is not None:
        # QUIT with return value (extrinsic function return)
        value_expr = generate_expr(stmt.return_value, ctx)
        ctx.emitter.line(f"return {value_expr}")
    else:
        # Plain QUIT - just return
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

    Handles bounded ranges (FOR I=1:1:10) and value lists (FOR I="A","B","C").
    MUMPS FOR is end-inclusive; Python range is end-exclusive, so we adjust.

    Args:
        stmt: MForStatement node
        ctx: Generator context
    """
    # Get loop variable name
    if isinstance(stmt.loop_var, str):
        loop_var = translate_name(stmt.loop_var)
    elif isinstance(stmt.loop_var, MVariable):
        loop_var = translate_name(stmt.loop_var.name)
    else:
        raise NotImplementedError(
            f"Unsupported FOR loop variable type: {type(stmt.loop_var).__name__}"
        )

    # Collect all values from parameters (for list iteration)
    # or generate range for bounded loops
    values: list[str] = []

    for param in stmt.parameters:
        if param.param_type == ForParamType.VALUE:
            # Single value - add to list
            if param.value is not None:
                values.append(generate_expr(param.value, ctx))
        elif param.param_type == ForParamType.RANGE:
            # Bounded range - generate Python range
            if param.start is None or param.step is None or param.end is None:
                raise NotImplementedError("Incomplete FOR range parameters")

            start_expr = generate_expr(param.start, ctx)
            step_expr = generate_expr(param.step, ctx)
            end_expr = generate_expr(param.end, ctx)

            # MUMPS FOR is end-inclusive, Python range is end-exclusive
            # For positive step: range(start, end + 1, step)
            # For negative step: range(start, end - 1, step)
            # We need runtime check for step sign, so use a helper expression
            # For simplicity in Phase 5, we generate code that handles both cases
            ctx.emitter.line(f"_for_step = m_num({step_expr})")
            ctx.emitter.line(
                f"_for_end = m_num({end_expr}) + (1 if _for_step > 0 else -1)"
            )
            ctx.emitter.line(
                f"for {loop_var} in range(m_num({start_expr}), _for_end, _for_step):"
            )

            with ctx.emitter.indented():
                if stmt.body and stmt.body.statements:
                    for body_stmt in stmt.body.statements:
                        generate_statement(body_stmt, ctx)
                else:
                    ctx.emitter.line("pass")
            return
        elif param.param_type == ForParamType.OPEN_RANGE:
            raise NotImplementedError("Open-ended FOR loops not yet supported")

    # If we have values (string list or mixed), generate for-in loop
    if values:
        values_str = ", ".join(values)
        ctx.emitter.line(f"for {loop_var} in [{values_str}]:")

        with ctx.emitter.indented():
            if stmt.body and stmt.body.statements:
                for body_stmt in stmt.body.statements:
                    generate_statement(body_stmt, ctx)
            else:
                ctx.emitter.line("pass")
        return

    # Argumentless FOR (infinite loop) - not supported in Phase 5
    if not stmt.parameters:
        raise NotImplementedError("Argumentless FOR loops not yet supported")


def _generate_goto(stmt: MGotoStatement, ctx: "GeneratorContext") -> None:
    """Generate function call with return from MGotoStatement.

    GOTO transfers control to a label. In Spec 004, we handle simple
    intra-routine GOTO by generating a function call followed by return.

    Example: G DONE → DONE(); return

    Args:
        stmt: MGotoStatement node
        ctx: Generator context

    Raises:
        NotImplementedError: For unsupported GOTO patterns
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

    For argumentless DO (no args), $TEST is saved before and restored after:
        _saved_test = _test
        SUB()
        _test = _saved_test

    For DO with arguments, $TEST changes in callee ARE visible to caller:
        SUB(arg1, arg2)
        # No save/restore - callee's _test persists

    Example: D SUB → SUB()

    Args:
        stmt: MDoStatement node
        ctx: Generator context

    Raises:
        NotImplementedError: For unsupported DO patterns
    """
    # Check for argumentless DO block (inline block with body)
    if not stmt.targets:
        raise NotImplementedError("Argumentless DO blocks not yet supported")

    # Check if this is an argumentless DO label call ($TEST stacked)
    is_argumentless = _is_argumentless_do(stmt)

    # For argumentless DO, save $TEST before all calls
    if is_argumentless:
        ctx.emitter.line("_saved_test = _test")

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

        # Generate function call (no return - control continues after DO)
        ctx.emitter.line(f"{label_name}()")

    # For argumentless DO, restore $TEST after all calls
    if is_argumentless:
        ctx.emitter.line("_test = _saved_test")


__all__ = [
    "generate_statement",
    "ForGenContext",
    "GotoGenContext",
    "_is_argumentless_do",
]
