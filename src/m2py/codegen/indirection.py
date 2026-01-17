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
    from m2py.asg.elements import MCall
    from m2py.asg.expressions import MExpr, MIndirection
    from m2py.asg.statements import MXecuteStatement
    from m2py.codegen.routine import GeneratorContext

from m2py.codegen.enums import GotoStrategy


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
    target: "MCall",
    ctx: "GeneratorContext",
) -> None:
    """Generate Python code for indirect DO (D @CMD).

    Spec 012 Phase 7 (T042-T045): Generate runtime dispatch for indirect DO.
    Handles various patterns:
    - D @CMD: Full indirection (label comes from variable)
    - D LABEL^@RTN: Partial indirection (routine from variable)
    - D @LBL^@RTN: Double indirection (both from variables)
    - D @CMD+5: Indirection with offset

    Generated code pattern:
    1. Resolve indirection expression(s) to get target string
    2. Call _rt.parse_call_target() to parse label/routine/offset
    3. Dispatch: local call or import + external call

    Args:
        target: MCall ASG node with indirection set
        ctx: Generator context
    """
    from m2py.codegen.expressions import generate_expr

    # Determine what's indirect and what's static
    label_is_indirect = target.label_is_indirect
    routine_is_indirect = target.routine_is_indirect

    # Generate the target expression
    if label_is_indirect and target.indirection:
        # Label comes from indirection: D @CMD or D @CMD^ROUTINE
        label_expr = generate_expr(target.indirection, ctx)
    elif target.name:
        # Static label name
        label_expr = repr(target.name)
    else:
        label_expr = "''"

    if routine_is_indirect and target.routine_indirection:
        # Routine comes from indirection: D LABEL^@RTN or D @LBL^@RTN
        routine_expr = generate_expr(target.routine_indirection, ctx)
    elif target.routine:
        # Static routine name
        routine_expr = repr(target.routine)
    else:
        routine_expr = None

    # Handle offset (D @CMD+5)
    offset_expr = None
    if target.offset is not None:
        offset_expr = generate_expr(target.offset, ctx)

    # Build the target string for parsing
    # Format: "LABEL+OFFSET^ROUTINE" (any part may be absent)
    if routine_expr is None and offset_expr is None:
        # Simple case: just label (D @CMD)
        target_str_expr = label_expr
    else:
        # Need to build a compound target string
        ctx.emitter.line(f"_indirect_label = str({label_expr})")
        if offset_expr is not None:
            ctx.emitter.line(f"_indirect_offset = int(m_num({offset_expr}))")
            ctx.emitter.line(
                '_indirect_target = _indirect_label + "+" + str(_indirect_offset)'
            )
        else:
            ctx.emitter.line("_indirect_target = _indirect_label")

        if routine_expr is not None:
            ctx.emitter.line(f"_indirect_routine = str({routine_expr})")
            ctx.emitter.line(
                '_indirect_target = _indirect_target + "^" + _indirect_routine'
            )

        target_str_expr = "_indirect_target"

    # Parse the target string
    ctx.emitter.line(f"_call_target = _rt.parse_call_target({target_str_expr})")

    # Generate dispatch code
    # Check if it's an external or local call
    ctx.emitter.line("if _call_target.routine:")
    with ctx.emitter.indented():
        # External call: import routine and call label
        ctx.emitter.line("import importlib")
        ctx.emitter.line("_module = importlib.import_module(_call_target.routine)")
        ctx.emitter.line("if _call_target.label:")
        with ctx.emitter.indented():
            ctx.emitter.line("_func = getattr(_module, _call_target.label, None)")
            ctx.emitter.line("if _func is None:")
            with ctx.emitter.indented():
                ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                ctx.emitter.line(
                    "raise LabelNotFoundError(_call_target.label, _call_target.routine, "
                    "list(getattr(_module, '_label_lines', {}).keys()))"
                )
        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            # Entry label (same name as routine)
            ctx.emitter.line("_func = getattr(_module, _call_target.routine, None)")
            ctx.emitter.line("if _func is None:")
            with ctx.emitter.indented():
                ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
                ctx.emitter.line(
                    "raise LabelNotFoundError(_call_target.routine, _call_target.routine, "
                    "list(getattr(_module, '_label_lines', {}).keys()))"
                )
        # Handle offset for external calls
        ctx.emitter.line("if _call_target.offset is not None:")
        with ctx.emitter.indented():
            ctx.emitter.line(
                "_label_line = _module._label_lines.get(_call_target.label or _call_target.routine, 0)"
            )
            ctx.emitter.line("_target_line = _label_line + _call_target.offset")
            ctx.emitter.line(
                "_label_name, _line_offset = _module._line_map[_target_line]"
            )
            ctx.emitter.line(
                "getattr(_module, _label_name)(_rt, _scope=_scope, _start_offset=_line_offset)"
            )
        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            ctx.emitter.line("_func(_rt, _scope=_scope)")

    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        # Local call: use current module's functions
        # In TRAMPOLINE mode, functions are in _labels dict; in SIMPLE mode, in globals()
        is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE
        if is_trampoline:
            ctx.emitter.line("_func = _labels.get(_call_target.label)")
        else:
            ctx.emitter.line("_func = globals().get(_call_target.label)")
        ctx.emitter.line("if _func is None:")
        with ctx.emitter.indented():
            ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
            ctx.emitter.line(
                "raise LabelNotFoundError(_call_target.label, _routine_name, "
                "list(_label_lines.keys()))"
            )
        # Handle offset for local calls
        ctx.emitter.line("if _call_target.offset is not None:")
        with ctx.emitter.indented():
            # _label_lines uses 0-indexed line numbers, _line_map uses 1-indexed
            # So we need to add 1 to convert before adding offset
            ctx.emitter.line("_label_line = _label_lines.get(_call_target.label, 0)")
            ctx.emitter.line("_target_line = (_label_line + 1) + _call_target.offset")
            ctx.emitter.line("if _target_line in _line_map:")
            with ctx.emitter.indented():
                ctx.emitter.line("_label_name, _line_offset = _line_map[_target_line]")
                if is_trampoline:
                    # In TRAMPOLINE mode, call internal function with state
                    ctx.emitter.line(
                        "_labels[_label_name](_rt, state, _scope, _start_offset=_line_offset)"
                    )
                else:
                    # In SIMPLE mode, call function directly (must support _start_offset)
                    # Note: SIMPLE mode doesn't support offset calls by design
                    # This should not be reached as offset calls force TRAMPOLINE
                    ctx.emitter.line(
                        "globals()[_label_name](_rt, _scope=_scope, _start_offset=_line_offset)"
                    )
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    'raise ValueError(f"Entry point {_call_target.label}+{_call_target.offset} not valid")'
                )
        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            ctx.emitter.line("_func(_rt, _scope=_scope)")


def generate_indirect_goto(
    target: "MCall",
    ctx: "GeneratorContext",
) -> None:
    """Generate Python code for indirect GOTO (G @TARGET).

    Spec 012 Phase 8 (T049-T052): Generate runtime dispatch for indirect GOTO.
    Handles various patterns:
    - G @TARGET: Full indirection (label comes from variable)
    - G LABEL^@RTN: Partial indirection (routine from variable)
    - G @LBL^@RTN: Double indirection (both from variables)
    - G @TARGET+5: Indirection with offset

    Unlike DO (which calls and returns), GOTO transfers control completely:
    - For local targets: return (label_name, state) to trampoline
    - For external targets: raise GotoExternal exception

    Args:
        target: MCall ASG node with indirection set
        ctx: Generator context
    """
    from m2py.codegen.expressions import generate_expr

    # Determine what's indirect and what's static
    label_is_indirect = target.label_is_indirect
    routine_is_indirect = target.routine_is_indirect

    # Generate the target expression
    if label_is_indirect and target.indirection:
        # Label comes from indirection: G @TARGET or G @TARGET^ROUTINE
        label_expr = generate_expr(target.indirection, ctx)
    elif target.name:
        # Static label name
        label_expr = repr(target.name)
    else:
        label_expr = "''"

    if routine_is_indirect and target.routine_indirection:
        # Routine comes from indirection: G LABEL^@RTN or G @LBL^@RTN
        routine_expr = generate_expr(target.routine_indirection, ctx)
    elif target.routine:
        # Static routine name
        routine_expr = repr(target.routine)
    else:
        routine_expr = None

    # Handle offset (G @TARGET+5)
    offset_expr = None
    if target.offset is not None:
        offset_expr = generate_expr(target.offset, ctx)

    # Build the target string for parsing
    # Format: "LABEL+OFFSET^ROUTINE" (any part may be absent)
    if routine_expr is None and offset_expr is None:
        # Simple case: just label (G @TARGET)
        target_str_expr = label_expr
    else:
        # Need to build a compound target string
        ctx.emitter.line(f"_indirect_label = str({label_expr})")
        if offset_expr is not None:
            ctx.emitter.line(f"_indirect_offset = int(m_num({offset_expr}))")
            ctx.emitter.line(
                '_indirect_target = _indirect_label + "+" + str(_indirect_offset)'
            )
        else:
            ctx.emitter.line("_indirect_target = _indirect_label")

        if routine_expr is not None:
            ctx.emitter.line(f"_indirect_routine = str({routine_expr})")
            ctx.emitter.line(
                '_indirect_target = _indirect_target + "^" + _indirect_routine'
            )

        target_str_expr = "_indirect_target"

    # Parse the target string
    ctx.emitter.line(f"_call_target = _rt.parse_call_target({target_str_expr})")

    # Generate dispatch code
    # Check if it's an external or local GOTO
    ctx.emitter.line("if _call_target.routine:")
    with ctx.emitter.indented():
        # External GOTO: import routine and raise GotoExternal
        ctx.emitter.line("import importlib")
        ctx.emitter.line("_module = importlib.import_module(_call_target.routine)")
        ctx.emitter.line("from m2py.runtime import GotoExternal")
        ctx.emitter.line("if _call_target.offset is not None:")
        with ctx.emitter.indented():
            ctx.emitter.line(
                "raise GotoExternal(_module, _call_target.label, "
                "offset=_call_target.offset, _rt=_rt)"
            )
        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            ctx.emitter.line("raise GotoExternal(_module, _call_target.label, _rt=_rt)")

    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        # Local GOTO: return to trampoline with label name
        # In TRAMPOLINE mode, return (label_name, state) or (line_number, state)
        is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE

        # Validate the label exists
        if is_trampoline:
            ctx.emitter.line("if _call_target.label not in _label_lines:")
        else:
            ctx.emitter.line("if _call_target.label not in globals():")
        with ctx.emitter.indented():
            ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
            ctx.emitter.line(
                "raise LabelNotFoundError(_call_target.label, _routine_name, "
                "list(_label_lines.keys()))"
            )

        # Handle offset for local GOTO
        ctx.emitter.line("if _call_target.offset is not None:")
        with ctx.emitter.indented():
            # _label_lines uses 0-indexed line numbers, _line_map uses 1-indexed
            # So we need to add 1 to convert before adding offset
            ctx.emitter.line("_label_line = _label_lines.get(_call_target.label, 0)")
            ctx.emitter.line("_target_line = (_label_line + 1) + _call_target.offset")
            ctx.emitter.line("if _target_line not in _line_map:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    "_next = min((ln for ln in _line_map if ln > _target_line), default=None)"
                )
                ctx.emitter.line("if _next is None:")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        'raise ValueError(f"Entry point {_call_target.label}+{_call_target.offset} not valid")'
                    )
                ctx.emitter.line("_target_line = _next")
            if is_trampoline:
                # Return line number to trampoline for offset-based dispatch
                ctx.emitter.line("return (_target_line, state)")
            else:
                # SIMPLE mode with offset - not typically supported
                ctx.emitter.line("_label_name, _line_offset = _line_map[_target_line]")
                ctx.emitter.line(
                    "globals()[_label_name](_rt, _scope=_scope, _start_offset=_line_offset)"
                )
                ctx.emitter.line("return")
        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            if is_trampoline:
                # Return label name to trampoline
                ctx.emitter.line("return (_call_target.label, state)")
            else:
                # SIMPLE mode: call function and return
                ctx.emitter.line("globals()[_call_target.label](_rt, _scope=_scope)")
                ctx.emitter.line("return")


def generate_argument_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> None:
    """Generate Python code for SET argument indirection.

    Spec 012 Phase 9 (T055): Generate runtime code that evaluates the
    indirection expression to get a SET argument string, then executes
    it dynamically using execute_mumps().

    For `S @A` where A="X=1":
      - Gets value of A: "X=1"
      - Executes: _rt.execute_mumps("S X=1", _scope)

    For nested `S @A` where A="@B" and B="X=5":
      - Gets value of A: "@B"
      - Executes: _rt.execute_mumps("S @B", _scope)
      - The execute_mumps handles the nested indirection

    Args:
        expr: MIndirection ASG node representing the argument indirection
        ctx: Generator context

    Note:
        This generates a statement, not an expression. The caller must
        ensure this is emitted at statement level.
    """
    from m2py.codegen.expressions import generate_expr

    # Argument indirection must have an expression
    if expr.expression is None:
        raise ValueError("Argument indirection requires an expression")

    # Generate expression to get the indirection target value
    # For @A, this is _scope.get("A", "")
    target_expr = generate_expr(expr.expression, ctx)

    # Generate the SET command string and execute it
    # Use execute_mumps which handles parsing and execution
    ctx.emitter.line(f'_rt.execute_mumps("S " + str({target_expr}), _scope)')


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
