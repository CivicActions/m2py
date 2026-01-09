"""Statement code generation for MUMPS-to-Python transpilation.

Generates Python statements from MUMPS ASG statement nodes.
Handles SET, WRITE, QUIT, IF, ELSE, FOR, and other basic commands.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from m2py.asg.enums import ForParamType
from m2py.asg.expressions import MExpr, MVariable
from m2py.asg.statements import (
    MElseStatement,
    MForStatement,
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


__all__ = ["generate_statement"]
