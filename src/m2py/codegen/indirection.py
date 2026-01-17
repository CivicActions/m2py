"""Code generation for indirection expressions and XECUTE command.

Spec 012: This module provides code generation support for:
- Name indirection (@VAR): Dynamic variable access
- Subscript indirection (@VAR@(subs)): Dynamic variable with subscripts
- Multi-level indirection (@@VAR, @@@VAR): Chained indirection
- Argument indirection (D @CMD): Dynamic DO/GOTO targets
- Pattern indirection (X?@PAT): Dynamic pattern matching
- XECUTE command: Runtime code execution

Code generation strategy:
- Constant XECUTE strings: Inline the generated Python code
- Dynamic XECUTE: Call _rt.execute() at runtime
- Name indirection: Call _rt.get_var()/_rt.set_var() at runtime
- Pattern indirection: Call _rt.compile_pattern_indirect() at runtime
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from m2py.asg.expressions import MExpr, MIndirection
    from m2py.asg.statements import MXecuteStatement
    from m2py.codegen.routine import GeneratorContext


def _count_indirection_levels(expr: "MIndirection") -> Tuple[int, "MExpr"]:
    """Count nested indirection levels and find the innermost expression.

    For @X returns (1, X)
    For @@X returns (2, X)
    For @@@X returns (3, X)

    Args:
        expr: The outermost MIndirection node

    Returns:
        Tuple of (level_count, innermost_expr)

    Raises:
        ValueError: If indirection has no inner expression
    """
    # Import here to avoid circular import
    from m2py.asg.expressions import MIndirection as MIndirectionType

    levels = 1
    inner = expr.expression

    if inner is None:
        raise ValueError("Indirection has no inner expression")

    while isinstance(inner, MIndirectionType):
        levels += 1
        if inner.expression is None:
            raise ValueError("Nested indirection has no inner expression")
        inner = inner.expression

    return levels, inner


def _generate_inner_name_expr(inner_expr: "MExpr", ctx: "GeneratorContext") -> str:
    """Generate the Python expression for the variable name to look up.

    For a simple variable like X, generates: _scope.get("X", MArray()).value
    For other expressions, uses generate_expr.

    Args:
        inner_expr: The innermost expression inside indirection
        ctx: Generator context

    Returns:
        Python expression string that evaluates to the variable name
    """
    # Import here to avoid circular import
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr

    if isinstance(inner_expr, MVariable):
        # Direct variable reference - look up by name and get value
        # Variables are stored as MArray objects, so we need .value
        var_name = inner_expr.name
        return f'_scope.get("{var_name}", MArray()).value'
    else:
        # Other expression - generate and convert to string if needed
        return generate_expr(inner_expr, ctx)


def generate_name_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection read (@VAR).

    Spec 012 Phase 3 (T014): Generates runtime call to resolve variable
    name at runtime and read its value.

    Handles:
    - Simple indirection: @X → _rt.get_var(_scope.get("X", ""), _scope)
    - Multi-level: @@X → _rt.resolve_indirection("X", 2, _scope)
    - With subscripts: @NAME@(1,2) → _rt.get_var(f'{_scope.get("NAME", "")}(1,2)', _scope)

    Args:
        expr: MIndirection ASG node with indirection_type=NAME
        ctx: Generator context

    Returns:
        Python expression string
    """
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels
    levels, inner_expr = _count_indirection_levels(expr)

    # Handle name+subscript syntax: @NAME@(1,2)
    if expr.name_indirection_subscripts:
        # Generate subscript expressions
        all_subs = []
        for sub_list in expr.name_indirection_subscripts:
            sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
            all_subs.extend(sub_exprs)

        # Build the subscript string
        if len(all_subs) == 1:
            subs_str = f"({all_subs[0]})"
        else:
            subs_str = f"({', '.join(all_subs)})"

        # Get the base name expression
        if isinstance(inner_expr, MVariable):
            base_name = inner_expr.name
            if levels > 1:
                # Multi-level with subscripts: resolve first, then add subscripts
                return f'_rt.get_var(str(_rt.resolve_indirection("{base_name}", {levels}, _scope)) + "{subs_str}", _scope)'
            else:
                # Single level with subscripts
                return f"_rt.get_var(f'{{_scope.get(\"{base_name}\", MArray()).value}}{subs_str}', _scope)"
        else:
            # Complex expression
            name_expr = generate_expr(inner_expr, ctx)
            return f'_rt.get_var(f"{{str({name_expr})}}{subs_str}", _scope)'

    # Handle multi-level indirection (@@X, @@@X)
    if levels > 1:
        if isinstance(inner_expr, MVariable):
            var_name = inner_expr.name
            return f'_rt.resolve_indirection("{var_name}", {levels}, _scope)'
        else:
            # Complex expression - evaluate first
            name_expr = generate_expr(inner_expr, ctx)
            return f"_rt.resolve_indirection(str({name_expr}), {levels}, _scope)"

    # Simple single-level indirection: @X
    name_expr = _generate_inner_name_expr(inner_expr, ctx)
    return f"_rt.get_var({name_expr}, _scope)"


def generate_name_indirection_write(
    expr: "MIndirection",
    value_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection write (S @VAR=value).

    Spec 012 Phase 3 (T015): Generates runtime call to resolve variable
    name at runtime and write a value to it.

    Handles:
    - Simple indirection: S @X=1 → _rt.set_var(_scope.get("X", ""), 1, _scope)
    - Multi-level: S @@X=1 → _rt.set_var(_rt.resolve_indirection("X", 1, _scope), 1, _scope)
    - With subscripts: S @NAME@(1,2)=5 → _rt.set_var(f'{_scope.get("NAME", "")}(1,2)', 5, _scope)

    Args:
        expr: MIndirection ASG node with indirection_type=NAME
        value_expr: Python expression for the value to set
        ctx: Generator context

    Returns:
        Python statement string
    """
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels
    levels, inner_expr = _count_indirection_levels(expr)

    # Handle name+subscript syntax: @NAME@(1,2)
    if expr.name_indirection_subscripts:
        # Generate subscript expressions
        all_subs = []
        for sub_list in expr.name_indirection_subscripts:
            sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
            all_subs.extend(sub_exprs)

        # Build the subscript string
        if len(all_subs) == 1:
            subs_str = f"({all_subs[0]})"
        else:
            subs_str = f"({', '.join(all_subs)})"

        # Get the base name expression
        if isinstance(inner_expr, MVariable):
            base_name = inner_expr.name
            if levels > 1:
                # Multi-level with subscripts
                return f'_rt.set_var(str(_rt.resolve_indirection("{base_name}", {levels}, _scope)) + "{subs_str}", {value_expr}, _scope)'
            else:
                # Single level with subscripts
                return f"_rt.set_var(f'{{_scope.get(\"{base_name}\", MArray()).value}}{subs_str}', {value_expr}, _scope)"
        else:
            # Complex expression
            name_expr = generate_expr(inner_expr, ctx)
            return (
                f'_rt.set_var(f"{{str({name_expr})}}{subs_str}", {value_expr}, _scope)'
            )

    # Handle multi-level indirection (@@X, @@@X) for write
    # For @@X=val, we resolve one fewer level to get the target variable name
    if levels > 1:
        if isinstance(inner_expr, MVariable):
            var_name = inner_expr.name
            # Resolve levels-1 times to get the target variable name
            resolved_name = (
                f'_rt.resolve_indirection("{var_name}", {levels - 1}, _scope)'
            )
            return f"_rt.set_var(str({resolved_name}), {value_expr}, _scope)"
        else:
            name_expr = generate_expr(inner_expr, ctx)
            resolved_name = (
                f"_rt.resolve_indirection(str({name_expr}), {levels - 1}, _scope)"
            )
            return f"_rt.set_var(str({resolved_name}), {value_expr}, _scope)"

    # Simple single-level indirection: @X
    name_expr = _generate_inner_name_expr(inner_expr, ctx)
    return f"_rt.set_var({name_expr}, {value_expr}, _scope)"


def generate_multi_level_indirection(
    expr: "MIndirection",
    levels: int,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for multi-level indirection (@@VAR, @@@VAR).

    Spec 012 Phase 3 (T018): Generates runtime call to resolve multiple
    levels of indirection before accessing the final variable.

    Note: This is now handled directly in generate_name_indirection(),
    which counts indirection levels automatically. This function is
    kept for explicit level control when needed.

    Args:
        expr: MIndirection ASG node
        levels: Number of @ symbols (2 for @@, 3 for @@@, etc.)
        ctx: Generator context

    Returns:
        Python expression string like: _rt.resolve_indirection("X", 2, _scope)

    Raises:
        ValueError: If indirection has no inner expression
    """
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr

    # Get the innermost expression by unwrapping all indirection levels
    inner_expr = expr.expression

    if inner_expr is None:
        raise ValueError("Indirection has no inner expression")

    if isinstance(inner_expr, MVariable):
        var_name = inner_expr.name
        return f'_rt.resolve_indirection("{var_name}", {levels}, _scope)'
    else:
        name_expr = generate_expr(inner_expr, ctx)
        return f"_rt.resolve_indirection(str({name_expr}), {levels}, _scope)"


def generate_subscripted_indirection(
    expr: "MIndirection",
    subscript_exprs: List[str],
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for subscripted indirection (@NAME@(1,2)).

    Spec 012 Phase 3 (T019): Generates runtime call to resolve variable
    name and then access with explicit subscripts.

    Note: This is now handled directly in generate_name_indirection(),
    which handles name_indirection_subscripts. This function is kept
    for explicit subscript control when needed.

    Args:
        expr: MIndirection ASG node with name_indirection_subscripts
        subscript_exprs: List of Python expressions for subscripts
        ctx: Generator context

    Returns:
        Python expression string
    """
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels
    levels, inner_expr = _count_indirection_levels(expr)

    # Build the subscript string
    if len(subscript_exprs) == 1:
        subs_str = f"({subscript_exprs[0]})"
    else:
        subs_str = f"({', '.join(subscript_exprs)})"

    if isinstance(inner_expr, MVariable):
        base_name = inner_expr.name
        if levels > 1:
            return f'_rt.get_var(str(_rt.resolve_indirection("{base_name}", {levels}, _scope)) + "{subs_str}", _scope)'
        else:
            return f"_rt.get_var(f'{{_scope.get(\"{base_name}\", MArray()).value}}{subs_str}', _scope)"
    else:
        name_expr = generate_expr(inner_expr, ctx)
        return f'_rt.get_var(f"{{str({name_expr})}}{subs_str}", _scope)'


def generate_xecute_constant(
    stmt: "MXecuteStatement",
    ctx: "GeneratorContext",
) -> List[str]:
    """Generate Python code for XECUTE with constant string.

    Spec 012 Phase 4 (T024): For constant string XECUTE (X "S X=1"),
    inline the generated Python code for better performance and
    debuggability.

    Args:
        stmt: MXecuteStatement ASG node with is_constant=True
        ctx: Generator context

    Returns:
        List of Python statement strings (inlined code)

    Note:
        This is a Phase 4 placeholder - implementation pending.
    """
    raise NotImplementedError("Constant XECUTE codegen not yet implemented")


def generate_xecute_dynamic(
    stmt: "MXecuteStatement",
    code_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for XECUTE with dynamic code string.

    Spec 012 Phase 5 (T032): For dynamic XECUTE (X CODE where CODE is
    a variable), generate a runtime call to parse and execute the code.

    Args:
        stmt: MXecuteStatement ASG node with is_constant=False
        code_expr: Python expression that evaluates to the MUMPS code string
        ctx: Generator context

    Returns:
        Python statement string like: _rt.execute(_scope.get("CODE", ""), _scope)

    Note:
        This is a Phase 5 placeholder - implementation pending.
    """
    raise NotImplementedError("Dynamic XECUTE codegen not yet implemented")


def generate_indirect_do(
    target_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for indirect DO (D @CMD).

    Spec 012 Phase 6 (T041): Generate runtime call to parse the target
    string and dispatch to the appropriate label/routine.

    Args:
        target_expr: Python expression for the target string
        ctx: Generator context

    Returns:
        Python statement string for indirect DO dispatch

    Note:
        This is a Phase 6 placeholder - implementation pending.
    """
    raise NotImplementedError("Indirect DO codegen not yet implemented")


def generate_indirect_goto(
    target_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for indirect GOTO (G @TARGET).

    Spec 012 Phase 7 (T049): Generate runtime call to parse the target
    string and perform GOTO transfer.

    Args:
        target_expr: Python expression for the target string
        ctx: Generator context

    Returns:
        Python statement string for indirect GOTO

    Note:
        This is a Phase 7 placeholder - implementation pending.
    """
    raise NotImplementedError("Indirect GOTO codegen not yet implemented")


def generate_argument_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for argument indirection.

    Spec 012 Phase 8 (T056): Generate runtime call to evaluate indirection
    expression and use result as command argument.

    Args:
        expr: MIndirection ASG node with indirection_type=ARGUMENT
        ctx: Generator context

    Returns:
        Python expression string

    Note:
        This is a Phase 8 placeholder - implementation pending.
    """
    raise NotImplementedError("Argument indirection codegen not yet implemented")


def generate_pattern_indirection(
    subject_expr: str,
    pattern_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for pattern indirection (X?@PAT).

    Spec 012 Phase 9 (T062): Generate runtime call to compile the pattern
    from a variable and match against the subject.

    Args:
        subject_expr: Python expression for the subject string
        pattern_expr: Python expression for the pattern variable
        ctx: Generator context

    Returns:
        Python expression string for pattern match

    Note:
        This is a Phase 9 placeholder - implementation pending.
    """
    raise NotImplementedError("Pattern indirection codegen not yet implemented")


__all__ = [
    "generate_name_indirection",
    "generate_name_indirection_write",
    "generate_multi_level_indirection",
    "generate_subscripted_indirection",
    "generate_xecute_constant",
    "generate_xecute_dynamic",
    "generate_indirect_do",
    "generate_indirect_goto",
    "generate_argument_indirection",
    "generate_pattern_indirection",
]
