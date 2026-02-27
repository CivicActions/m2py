"""Code generation for indirection expressions and XECUTE command.

This module provides code generation support for:
- Name indirection (@VAR): Dynamic variable access
- Subscript indirection (@VAR@(subs)): Dynamic variable with subscripts
- Multi-level indirection (@@VAR, @@@VAR): Chained indirection
- Argument indirection (D @CMD): Dynamic DO/GOTO targets
- Pattern matching: Handled inline via m_pattern_match() in expressions.py
- XECUTE command: Runtime code execution via execute_mumps()

Code generation strategy:
- XECUTE: Call _rt.execute_mumps() at runtime
- Name indirection: Call unified runtime methods (set_indirected, get_indirected,
  kill_indirected, resolve_for_target) which use IndirectionResolver internally
- Pattern matching: Handled inline in expressions.py via m_pattern_match()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from m2py.asg.elements import MCall
    from m2py.asg.expressions import MExpr, MIndirection
    from m2py.codegen.routine import GeneratorContext

from m2py.codegen.enums import GotoStrategy
from m2py.codegen.var_access import scope_dict_expr


def _generate_do_goto_indirection_string(ind: "MExpr", ctx: "GeneratorContext") -> str:
    """Generate Python expression for DO/GOTO indirection target string.

    For DO/GOTO indirection, we evaluate the variable at runtime to get the
    target label/routine name. For single-level indirection, we evaluate the
    variable directly. For nested indirection (@@), we build a string with
    @ prefixes for the runtime to resolve.

    Examples:
        @CMD where CMD="SUB" → evaluates to str(CMD) = "SUB"
        @@CMD where CMD="L", L="SUB" → builds "@" + str(CMD) = "@L"
        @CMD(1) where CMD(1)="SUB" → evaluates CMD(1) = "SUB"

    Args:
        ind: MIndirection ASG node (or MExpr that is an MIndirection)
        ctx: Generator context

    Returns:
        Python expression string that evaluates to the target name or "@NAME"
    """
    from m2py.asg.expressions import MIndirection as MIndirectionType
    from m2py.codegen.expressions import generate_expr

    # Handle case where ind is not MIndirection (shouldn't happen in practice,
    # but type system allows MExpr)
    if not isinstance(ind, MIndirectionType):
        # Fall back to direct expression evaluation
        return f"str({generate_expr(ind, ctx)})"  # pragma: no cover

    # Count indirection levels and get inner expression
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(ind)

    if levels == 1:
        # Single-level indirection: evaluate the variable directly
        # @CMD → str(CMD)
        inner_code = generate_expr(inner_expr, ctx)
        return f"str({inner_code})"
    else:
        # Multi-level indirection: need runtime to resolve remaining levels
        # @@CMD → "@" + str(CMD) (runtime then resolves @L where L=CMD's value)
        at_prefix = "@" * (levels - 1)  # One @ is resolved by this eval
        inner_code = generate_expr(inner_expr, ctx)
        return f'"{at_prefix}" + str({inner_code})'


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
    inner: MExpr = expr.expression  # type: ignore[assignment]

    while isinstance(inner, MIndirectionType):
        levels += 1
        inner = inner.expression  # type: ignore[assignment]

    return levels, inner


def _count_indirection_levels_with_subscripts(
    expr: "MIndirection",
) -> Tuple[int, "MExpr", List[List["MExpr"]]]:
    """Count nested indirection levels, find innermost expr, and collect all subscripts.

    For @X returns (1, X, [])
    For @@X returns (2, X, [])
    For @X@(3) returns (1, X, [[3]])
    For @@X@(3) returns (2, X, [[3]]) - subscripts from inner level
    For @(@X@(3))@(4) would return (2, X, [[3], [4]])

    This is needed to properly handle cases like @@^VV@(3)=99 where:
    - Outer indirection has NO subscripts
    - Inner indirection HAS subscripts [3]

    Args:
        expr: The outermost MIndirection node

    Returns:
        Tuple of (level_count, innermost_expr, all_subscripts_lists)
        where all_subscripts_lists contains subscripts from each level (inner to outer)

    Raises:
        ValueError: If indirection has no inner expression
    """
    # Import here to avoid circular import
    from m2py.asg.expressions import MIndirection as MIndirectionType

    levels = 1
    inner: MExpr = expr.expression  # type: ignore[assignment]
    all_subscripts: List[List["MExpr"]] = []

    # Collect outer level subscripts first
    if expr.name_indirection_subscripts:
        for sub_list in expr.name_indirection_subscripts:
            all_subscripts.append(sub_list)

    while isinstance(inner, MIndirectionType):
        levels += 1
        # Collect inner level subscripts
        if inner.name_indirection_subscripts:
            # Inner subscripts go at the beginning (they are applied first)
            for sub_list in reversed(inner.name_indirection_subscripts):
                all_subscripts.insert(0, sub_list)
        inner = inner.expression  # type: ignore[assignment]

    return levels, inner, all_subscripts


def _generate_inner_name_expr(inner_expr: "MExpr", ctx: "GeneratorContext") -> str:
    """Generate Python expression that evaluates to the indirection target variable name.

    This helper is used by commands that need to resolve an indirection to a variable
    name at runtime (e.g., NEW @A).

    For MVariable: Returns resolve_for_target call to get the VALUE of the variable,
    which is the target name for indirection.

    For other expressions: Uses generate_expr to evaluate the expression, which gives
    the target name directly.

    Args:
        inner_expr: The inner expression from an indirection
        ctx: Generator context

    Returns:
        Python expression string that evaluates to the target variable name
    """
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr

    scope_expr = scope_dict_expr(ctx)

    if isinstance(inner_expr, MVariable):
        var_name = inner_expr.name
        if inner_expr.subscripts:
            # Subscripted variable like A(1,2) - build dynamic name expression
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name string like "A(1,2)" at runtime and resolve
            full_name_expr = f'f"{var_name}(" + ",".join([_format_subscript(s) for s in [{subs_str}]]) + ")"'
            return f"_rt.resolve_for_target({full_name_expr}, {scope_expr}, levels=1)"
        else:
            # Simple variable - use resolve_for_target for validation + value
            return f'_rt.resolve_for_target("{var_name}", {scope_expr}, levels=1)'
    else:
        # Other expressions - generate_expr gives the value directly
        return generate_expr(inner_expr, ctx)


def _build_per_level_subs_arg(
    all_subscripts: List[List["MExpr"]], ctx: "GeneratorContext"
) -> str:
    """Build the ', per_level_subscripts=[...]' argument string from subscript lists.

    Returns empty string if no subscripts are present.
    """
    from m2py.codegen.expressions import generate_expr

    if not any(all_subscripts):
        return ""
    per_level_subs = []
    for sub_list in all_subscripts:
        if sub_list:
            sub_exprs = [generate_expr(s, ctx) for s in sub_list]
            per_level_subs.append(f"[{', '.join(sub_exprs)}]")
        else:
            per_level_subs.append("[]")
    return f", per_level_subscripts=[{', '.join(per_level_subs)}]"


def _build_source_expr(inner_expr: "MExpr", ctx: "GeneratorContext") -> str:
    """Build the source expression string from an inner expression node.

    Handles MVariable, LocalVariable, and GlobalVariable by constructing
    a name string expression. For MVariable/LocalVariable with subscripts,
    builds a runtime name expression like '"A(" + ... + ")"'.

    Does NOT handle NakedGlobal or complex expressions — callers must
    handle those before calling this function.

    Args:
        inner_expr: The innermost expression after unwrapping indirection levels
        ctx: Generator context

    Returns:
        Python expression string for the source variable name
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    if isinstance(inner_expr, (MVariable, MLocalVariable)):
        source_name = inner_expr.name
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            return f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        return f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            return f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        return f'"{source_name}"'
    else:
        raise TypeError(
            f"_build_source_expr expects MVariable/GlobalVariable, "
            f"got {type(inner_expr).__name__}"
        )


def _build_indirection_call(
    expr: "MIndirection",
    ctx: "GeneratorContext",
    runtime_method: str,
    *,
    extra_args_before_scope: str = "",
    extra_args_after_scope: str = "",
    extra_kwargs: str = "",
    handle_naked: bool = True,
    naked_adjust: int = -1,
    complex_adjust: int = -1,
    complex_wrapper: str = "str",
) -> str:
    """Shared template for building indirection runtime calls.

    Implements the 5-step indirection codegen pattern:
    1. Count indirection levels and collect per-level subscripts
    2. Get scope expression from context
    3. Type-switch on inner expression (NakedGlobal, complex, Variable/Global)
       to build source_expr and adjust levels
    4. Build per_level_subscripts argument string
    5. Format: _rt.{method}({source}{extra_before}, {scope}{extra_after},
       levels={levels}{subs}{extra_kwargs})

    Args:
        expr: MIndirection ASG node
        ctx: Generator context
        runtime_method: Name of runtime method (e.g., "get_indirected")
        extra_args_before_scope: Extra positional args after source, before scope
        extra_args_after_scope: Extra positional args after scope
        extra_kwargs: Extra keyword args at end (e.g., ", allow_undefined=True")
        handle_naked: Whether to handle NakedGlobal inner expressions
        naked_adjust: Levels adjustment for NakedGlobal (-1 = levels-1, 0 = full)
        complex_adjust: Levels adjustment for complex expr (-1 = levels-1, 0 = full)
        complex_wrapper: Wrapper for complex expressions ("str" or "m_str")

    Returns:
        Python expression string for the runtime call
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable, NakedGlobal
    from m2py.codegen.expressions import generate_expr

    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)
    scope_expr = scope_dict_expr(ctx)

    def _format_call(source: str, lvl: int, subs: str) -> str:
        return (
            f"_rt.{runtime_method}({source}{extra_args_before_scope}, "
            f"{scope_expr}{extra_args_after_scope}, "
            f"levels={lvl}{subs}{extra_kwargs})"
        )

    # Handle NakedGlobal
    if handle_naked and isinstance(inner_expr, NakedGlobal):
        naked_expr = generate_expr(inner_expr, ctx)
        subs_arg = _build_per_level_subs_arg(all_subscripts, ctx)
        return _format_call(naked_expr, levels + naked_adjust, subs_arg)

    # Handle complex expressions (not Variable/GlobalVariable)
    if not isinstance(inner_expr, (MVariable, MLocalVariable, GlobalVariable)):
        source_expr = f"{complex_wrapper}({generate_expr(inner_expr, ctx)})"
        subs_arg = _build_per_level_subs_arg(all_subscripts, ctx)
        adjusted = (
            max(0, levels + complex_adjust)
            if complex_adjust < 0
            else levels + complex_adjust
        )
        return _format_call(source_expr, adjusted, subs_arg)

    # Handle MVariable / LocalVariable / GlobalVariable
    source_expr = _build_source_expr(inner_expr, ctx)
    subs_arg = _build_per_level_subs_arg(all_subscripts, ctx)
    return _format_call(source_expr, levels, subs_arg)


def generate_argument_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
    if_condition: bool = False,
) -> str:
    """Generate Python code for argument-level indirection using unified components.

    Argument indirection evaluates the resolved value as an expression,
    not as a variable name to look up. For example:
    - I @A where A="1=0" → evaluates "1=0" → 0 (FALSE)
    - I @A where A="X>5" and X=10 → evaluates "X>5" → 1 (TRUE)

    Uses _rt.evaluate_argument_indirection() which:
    1. Resolves the indirection through all levels
    2. Parses the final string as a MUMPS expression
    3. Evaluates the expression with access to current scope
    4. Returns the evaluated result (not the string)

    Empty string handling depends on context:
    - IF condition (if_condition=True): Empty string → 1 (TRUE)
    - Other contexts (if_condition=False): Empty string → VarExpectedError

    Args:
        expr: MIndirection ASG node with indirection_type=ARGUMENT
        ctx: Generator context
        if_condition: If True, pass treat_empty_as_truthy=True for
            empty-string-as-truthy behavior

    Returns:
        Python expression string that calls _rt.evaluate_argument_indirection()
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Get the appropriate scope expression for this context
    scope_expr = scope_dict_expr(ctx)

    # Count indirection levels and collect per-level subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # Complex expression - generate and evaluate
        # For @$P(...), @$E(...), etc., the expression evaluates to a STRING
        # which is then used as the expression to evaluate.
        # Unlike variable sources, the expression result IS the first "level",
        # so we use levels-1 (but minimum 1).
        value_expr = generate_expr(inner_expr, ctx)
        effective_levels = max(1, levels - 1)

        # Build per-level subscripts argument if any exist
        if all_subscripts and any(all_subscripts):
            per_level_subs = []
            for subs in all_subscripts:
                if subs:
                    sub_exprs = [generate_expr(s, ctx) for s in subs]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            if per_level_subs:
                subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
            else:
                subs_arg = ""
        else:
            subs_arg = ""

        empty_flag = ", treat_empty_as_truthy=True" if if_condition else ""

        # For effective_levels=0 or 1, evaluate the expression result directly
        # as a MUMPS expression (no intermediate lookups needed)
        if effective_levels <= 1 and not subs_arg:
            # Direct evaluation: @$P(...) just evaluates the $P result as expression
            return (
                f"_rt.evaluate_mumps_expression({value_expr}, {scope_expr}{empty_flag})"
            )
        else:
            # Multi-level: @@$P(...) needs lookup chain
            return f"_rt.evaluate_argument_indirection({value_expr}, {scope_expr}, levels={effective_levels}{subs_arg}{empty_flag})"

    # Build per-level subscripts argument if needed
    if all_subscripts and any(all_subscripts):
        # Include ALL indirection subscripts from @X@(subs) syntax.
        # inner_expr.subscripts (variable subscripts like X(1,2)) are
        # already included in source_expr; all_subscripts contains only
        # indirection subscripts (after the @).
        per_level_subs = []
        for subs in all_subscripts:
            if subs:
                sub_exprs = [generate_expr(s, ctx) for s in subs]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")

        if per_level_subs:
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""
    else:
        subs_arg = ""

    # Generate call to unified evaluate_argument_indirection
    # For IF conditions, pass treat_empty_as_truthy=True so empty strings → TRUE
    empty_flag = ", treat_empty_as_truthy=True" if if_condition else ""
    return f"_rt.evaluate_argument_indirection({source_expr}, {scope_expr}, levels={levels}{subs_arg}{empty_flag})"


def generate_name_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection READ using _rt.get_indirected().

    Handles @X, @@X, @X@(1,2), @^(1), complex expressions.
    NakedGlobal and complex expressions consume one level (levels-1).
    """
    return _build_indirection_call(expr, ctx, "get_indirected")


def generate_indirection_marray_expr(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for indirected by-reference parameter using get_indirected_marray.

    Used for .@VAR by-ref parameters in DO calls where we need the MArray object.
    NakedGlobal and complex expressions consume one level (levels-1).
    """
    return _build_indirection_call(expr, ctx, "get_indirected_marray")


def generate_subscript_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for indirection in subscript context using _rt.get_subscript_indirected().

    Evaluates indirection for VALUE (not name validation). NakedGlobal uses
    full levels. Complex expressions consume one level (levels-1).
    """
    return _build_indirection_call(
        expr, ctx, "get_subscript_indirected", naked_adjust=0
    )


def generate_name_indirection_write(
    expr: "MIndirection",
    value_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection write using _rt.set_indirected().

    NakedGlobal uses full levels (naked_adjust=0). Complex expressions consume
    one level (levels-1).
    """
    return _build_indirection_call(
        expr,
        ctx,
        "set_indirected",
        extra_args_before_scope=f", {value_expr}",
        naked_adjust=0,
    )


def generate_name_indirection_kill(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection KILL using _rt.kill_indirected().

    No NakedGlobal handling. Complex expressions reduce levels by 1 because the
    expression result IS the kill list (not a variable to look up).
    """
    return _build_indirection_call(
        expr, ctx, "kill_indirected", handle_naked=False, complex_adjust=-1
    )


def generate_name_indirection_for(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for FOR loop indirection target using _rt.resolve_for_target().

    No NakedGlobal handling. Complex expressions use full levels.
    """
    return _build_indirection_call(
        expr, ctx, "resolve_for_target", handle_naked=False, complex_adjust=0
    )


def generate_merge_indirection_name(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for MERGE indirection target using _rt.resolve_for_target().

    No NakedGlobal handling. Complex expressions use full levels.
    """
    return _build_indirection_call(
        expr, ctx, "resolve_for_target", handle_naked=False, complex_adjust=0
    )


def generate_data_indirection_name(
    var: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for $DATA indirection.

    Resolves target name with proper subscript merging via data_indirected(),
    paralleling get_indirected() for $GET.  Uses _count_indirection_levels_with_subscripts
    and _build_per_level_subs_arg so that @VAR@(subs) correctly merges subscripts
    instead of producing split-parentheses like name("s1")("s2").
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(var)
    scope_expr = scope_dict_expr(ctx)

    # Build source expression with type-specific handling
    if isinstance(inner_expr, (MVariable, MLocalVariable, GlobalVariable)):
        source_expr = _build_source_expr(inner_expr, ctx)
    else:
        # Complex expression: result IS first level, so levels-1
        inner_expr_code = generate_expr(inner_expr, ctx)
        # For @$P(...)@(subs): apply first subscript set to source
        if all_subscripts and all_subscripts[0]:
            first_subs = all_subscripts[0]
            sub_exprs = [generate_expr(s, ctx) for s in first_subs]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f"_rt.append_subscripts_to_name(str({inner_expr_code}), [{subs_str}])"
            )
            all_subscripts = all_subscripts[1:]
        else:
            source_expr = f"str({inner_expr_code})"
        levels = levels - 1

    subs_arg = _build_per_level_subs_arg(all_subscripts, ctx)

    return (
        f"_rt.data_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg})"
    )


def generate_get_indirection_name(
    var: "MIndirection",
    ctx: "GeneratorContext",
    default_expr: str = '""',
) -> str:
    """Generate Python expression for $GET indirection using _rt.get_indirected().

    For complex expressions (e.g., @$P(...)@(subs)), the first subscript set
    is appended to the source before resolution. Uses allow_undefined=True.
    When default_expr != '""', wraps in a lambda for default substitution.
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(var)
    scope_expr = scope_dict_expr(ctx)

    # Build source expression with type-specific handling
    if isinstance(inner_expr, (MVariable, MLocalVariable, GlobalVariable)):
        source_expr = _build_source_expr(inner_expr, ctx)
    else:
        # Complex expression: result IS first level, so levels-1
        inner_expr_code = generate_expr(inner_expr, ctx)
        # For @$P(...)@(subs): apply first subscript set to source
        if all_subscripts and all_subscripts[0]:
            first_subs = all_subscripts[0]
            sub_exprs = [generate_expr(s, ctx) for s in first_subs]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f"_rt.append_subscripts_to_name(str({inner_expr_code}), [{subs_str}])"
            )
            all_subscripts = all_subscripts[1:]
        else:
            source_expr = f"str({inner_expr_code})"
        levels = levels - 1

    subs_arg = _build_per_level_subs_arg(all_subscripts, ctx)

    if default_expr == '""':
        return f"_rt.get_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg}, allow_undefined=True)"
    else:
        return (
            f"((lambda _v: _v if _v else {default_expr})"
            f"(_rt.get_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg}, allow_undefined=True)))"
        )


def generate_name_function_indirection(
    var: "MIndirection",
    ctx: "GeneratorContext",
    depth_expr: str | None = None,
) -> str:
    """Generate Python expression for $NAME function with indirection argument.

    Uses resolve_for_target + get_name. For complex expressions where
    levels adjusts to 0, skips resolution and uses source directly.
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(var)
    scope_expr = scope_dict_expr(ctx)
    subs_arg = _build_per_level_subs_arg(all_subscripts, ctx)

    if isinstance(inner_expr, (MVariable, MLocalVariable, GlobalVariable)):
        source_expr = _build_source_expr(inner_expr, ctx)
    else:
        inner_expr_code = generate_expr(inner_expr, ctx)
        source_expr = f"str({inner_expr_code})"
        levels = levels - 1

    # If levels is 0 after adjustment (for simple @func() case), skip resolve
    if levels == 0:
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            per_level_subs_code = f"[{', '.join(per_level_subs)}]"
            name_expr = (
                f"_rt._append_subscripts_to_name({source_expr}, {per_level_subs_code})"
            )
        else:
            name_expr = source_expr
    else:
        name_expr = f"_rt.resolve_for_target({source_expr}, {scope_expr}, levels={levels}{subs_arg})"

    depth_arg = f", depth=int(m_num({depth_expr}))" if depth_expr is not None else ""
    return f"_rt.get_name({name_expr}, (), {scope_expr}{depth_arg})"


def generate_query_indirection_name(
    var: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for $QUERY indirection.

    Resolves indirection target, then calls get_query for depth-first traversal.
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr
    from m2py.codegen.statements import gen_subscripts_tuple

    levels, inner_expr = _count_indirection_levels(var)

    # Build subscript tuple from name_indirection_subscripts
    all_subs = []
    for sub_list in var.name_indirection_subscripts or []:
        sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
        all_subs.extend(sub_exprs)
    subscripts_tuple = gen_subscripts_tuple(all_subs, ctx)

    scope_expr = scope_dict_expr(ctx)

    if isinstance(inner_expr, GlobalVariable):
        name_expr = f'str((_rt.globals.get({inner_expr.name!r}, ()) or ""))'
    elif isinstance(inner_expr, (MVariable, MLocalVariable)):
        name_expr = f'_rt.resolve_for_target("{inner_expr.name}", {scope_expr}, levels={levels})'
    else:
        inner_expr_code = generate_expr(inner_expr, ctx)
        name_expr = f"str({inner_expr_code})"

    return f"_rt.get_query({name_expr}, {subscripts_tuple}, {scope_expr})"


def _build_indirect_target_expr(target: "MCall", ctx: "GeneratorContext") -> str:
    """Build indirection target expression string for DO/GOTO dispatch.

    Shared by generate_indirect_do and generate_indirect_goto.
    May emit intermediate variable assignments via the emitter.
    Returns the Python expression string for the resolved target.
    """
    from m2py.codegen.expressions import generate_expr

    if target.label_is_indirect and target.indirection:
        label_expr = _generate_do_goto_indirection_string(target.indirection, ctx)
    elif target.name:
        label_expr = repr(target.name)
    else:
        label_expr = "''"

    if target.routine_is_indirect and target.routine_indirection:
        routine_expr = _generate_do_goto_indirection_string(
            target.routine_indirection, ctx
        )
    elif target.routine:
        routine_expr = repr(target.routine)
    else:
        routine_expr = None

    offset_expr = None
    if target.offset is not None:
        offset_expr = generate_expr(target.offset, ctx)

    if routine_expr is None and offset_expr is None:
        return label_expr

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

    return "_indirect_target"


def _emit_scope_to_state_sync(ctx: "GeneratorContext") -> None:
    """Emit code to sync _scope dict back into state (MArray wrapping).

    Uses state._locals for dynamic-locals routines, or syncs individual
    state vars for static-field routines.
    """
    from m2py.codegen.statements import (
        emit_scope_to_state_sync,
        emit_scope_var_to_state,
    )

    if ctx.uses_dynamic_locals:
        emit_scope_to_state_sync(ctx)
    elif ctx.state_vars:
        from m2py.codegen.names import translate_name

        for var_name in sorted(ctx.state_vars):
            py_name = translate_name(var_name)
            emit_scope_var_to_state(ctx, var_name, py_name, scope_key=var_name)


def _emit_goto_external_catch(ctx: "GeneratorContext") -> None:
    """Emit 'except GotoExternal' block: sync state→scope, run external, sync back."""
    from m2py.codegen.statements import (
        emit_state_to_scope_sync,
        emit_state_var_to_scope,
    )

    ctx.emitter.line("except GotoExternal as _goto:")
    with ctx.emitter.indented():
        if ctx.uses_dynamic_locals:
            emit_state_to_scope_sync(ctx)
        elif ctx.state_vars:
            from m2py.codegen.names import translate_name

            for var_name in sorted(ctx.state_vars):
                py_name = translate_name(var_name)
                emit_state_var_to_scope(ctx, var_name, py_name, scope_key=var_name)
        ctx.emitter.line(
            "run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)"
        )
        _emit_scope_to_state_sync(ctx)
        ctx.emitter.line("_do_target = None")


def _emit_fallthrough_loop(ctx: "GeneratorContext") -> None:
    """Emit else/while fall-through loop with GotoExternal handling."""
    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        ctx.emitter.line("while _do_target is not None:")
        with ctx.emitter.indented():
            ctx.emitter.line("try:")
            with ctx.emitter.indented():
                ctx.emitter.line("assert isinstance(_do_target, str)")
                ctx.emitter.line("_do_func = _labels[_do_target]")
                ctx.emitter.line("_do_target, state = _do_func(_rt, state, _scope)")
            _emit_goto_external_catch(ctx)


def _emit_trampoline_call_with_fallthrough(
    ctx: "GeneratorContext", initial_call: str
) -> None:
    """Emit try/except GotoExternal/else fall-through pattern for TRAMPOLINE DO calls."""
    ctx.emitter.line("try:")
    with ctx.emitter.indented():
        ctx.emitter.line(initial_call)
    _emit_goto_external_catch(ctx)
    _emit_fallthrough_loop(ctx)


def generate_indirect_do(
    target: "MCall",
    ctx: "GeneratorContext",
) -> None:
    """Generate Python code for indirect DO (D @CMD, D LABEL^@RTN, etc.)."""
    target_str_expr = _build_indirect_target_expr(target, ctx)

    ctx.emitter.line(
        f"_call_targets = _rt.resolve_do_targets({target_str_expr}, {scope_dict_expr(ctx)})"
    )

    ctx.emitter.line("for _call_target in _call_targets:")
    with ctx.emitter.indented():
        # Lazy postcondition evaluation
        scope_ref = scope_dict_expr(ctx)
        ctx.emitter.line("if _call_target.postcondition:")
        with ctx.emitter.indented():
            ctx.emitter.line("_pc_temp_var = 'ZPOSTCOND'")
            ctx.emitter.line(f"_pc_scope = dict({scope_ref})")
            ctx.emitter.line(
                "_rt.execute_mumps(f'S {_pc_temp_var}={_call_target.postcondition}', _pc_scope)"
            )
            ctx.emitter.line("_pc_result = _pc_scope.get(_pc_temp_var)")
            ctx.emitter.line("if isinstance(_pc_result, MArray):")
            with ctx.emitter.indented():
                ctx.emitter.line("_pc_result = _pc_result.value")
            ctx.emitter.line("if _pc_result in (0, '', '0', None):")
            with ctx.emitter.indented():
                ctx.emitter.line("continue")

        # External vs local dispatch
        # When args_str is present (e.g., target was 'GREET("World")^RTN'),
        # use execute_mumps to handle argument passing via MUMPS evaluation.
        # The grammar requires standard MUMPS order: D LABEL^ROUTINE(args)
        # (args come AFTER the routine reference, not before it).
        ctx.emitter.line("if _call_target.args_str:")
        with ctx.emitter.indented():
            ctx.emitter.line('_xecute_target = (_call_target.label or "")')
            ctx.emitter.line("if _call_target.routine:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    '_xecute_target = _xecute_target + "^" + _call_target.routine'
                )
            ctx.emitter.line("_xecute_target = _xecute_target + _call_target.args_str")
            ctx.emitter.line(f'_rt.execute_mumps("D " + _xecute_target, {scope_ref})')

        ctx.emitter.line(
            "elif _call_target.routine and _call_target.routine != _routine_name:"
        )
        with ctx.emitter.indented():
            _emit_external_do_call(ctx)

        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            _emit_local_do_call(ctx)


def _emit_external_do_call(ctx: "GeneratorContext") -> None:
    """Emit external DO call dispatch (import module, find function, call)."""
    _sd = scope_dict_expr(ctx)
    ctx.emitter.line("import importlib")
    ctx.emitter.line("from m2py.core.names import NameTranslator")
    ctx.emitter.line("_module = importlib.import_module(_call_target.routine)")

    # Find function by label or routine name
    ctx.emitter.line("if _call_target.label:")
    with ctx.emitter.indented():
        ctx.emitter.line(
            "_func = getattr(_module, NameTranslator.to_python(_call_target.label), None)"
        )
        ctx.emitter.line("if _func is None:")
        with ctx.emitter.indented():
            ctx.emitter.line("from m2py.runtime import LabelNotFoundError")
            ctx.emitter.line(
                "raise LabelNotFoundError(_call_target.label, _call_target.routine, "
                "list(getattr(_module, '_label_lines', {}).keys()))"
            )
    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        ctx.emitter.line(
            "_func = getattr(_module, NameTranslator.to_python(_call_target.routine), None)"
        )
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
        ctx.emitter.line("_target_line = (_label_line + 1) + _call_target.offset")
        ctx.emitter.line("_label_name, _line_offset = _module._line_map[_target_line]")
        ctx.emitter.line(
            f"getattr(_module, _label_name)(_rt, _scope={_sd}, _start_offset=_line_offset)"
        )
    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        ctx.emitter.line(f"_func(_rt, _scope={_sd})")

    # Sync scope back to state after external call in TRAMPOLINE mode
    if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
        _emit_scope_to_state_sync(ctx)


def _emit_local_do_call(ctx: "GeneratorContext") -> None:
    """Emit local DO call dispatch (find in _labels or globals, call with fallthrough)."""
    is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE
    if is_trampoline:
        ctx.emitter.line("_func = _labels.get(_call_target.label)")
    else:
        ctx.emitter.line("from m2py.core.names import NameTranslator")
        ctx.emitter.line(
            "_func = globals().get(NameTranslator.to_python(_call_target.label))"
        )

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
        ctx.emitter.line("_label_line = _label_lines.get(_call_target.label, 0)")
        ctx.emitter.line("_target_line = (_label_line + 1) + _call_target.offset")
        ctx.emitter.line("if _target_line in _line_map:")
        with ctx.emitter.indented():
            ctx.emitter.line("_label_name, _line_offset = _line_map[_target_line]")
            if is_trampoline:
                _emit_trampoline_call_with_fallthrough(
                    ctx,
                    "_do_target, state = _globals['_' + _label_name]"
                    "(_rt, state, _scope, _start_offset=_line_offset)",
                )
            else:
                ctx.emitter.line(
                    "_globals[_label_name](_rt, _scope=_scope, _start_offset=_line_offset)"
                )
        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            ctx.emitter.line(
                'raise ValueError(f"Entry point {_call_target.label}+{_call_target.offset} not valid")'
            )

    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        if is_trampoline:
            _emit_trampoline_call_with_fallthrough(
                ctx, "_do_target, state = _func(_rt, state, _scope)"
            )
        else:
            ctx.emitter.line("_func(_rt, _scope=_scope)")


def generate_indirect_goto(
    target: "MCall",
    ctx: "GeneratorContext",
) -> None:
    """Generate Python code for indirect GOTO (G @TARGET, G LABEL^@RTN, etc.)."""
    target_str_expr = _build_indirect_target_expr(target, ctx)

    ctx.emitter.line(
        f"_call_targets = _rt.resolve_do_targets({target_str_expr}, {scope_dict_expr(ctx)})"
    )

    # GOTO takes only the first matching target
    ctx.emitter.line("if not _call_targets:")
    with ctx.emitter.indented():
        ctx.emitter.line("pass  # No matching target - fall through")
    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        ctx.emitter.line("_call_target = _call_targets[0]")

        # External vs local dispatch
        ctx.emitter.line(
            "if _call_target.routine and _call_target.routine != _routine_name:"
        )
        with ctx.emitter.indented():
            # External GOTO: raise GotoExternal
            ctx.emitter.line("import importlib")
            ctx.emitter.line("_module = importlib.import_module(_call_target.routine)")
            ctx.emitter.line("if _call_target.offset is not None:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    "raise GotoExternal(_module, _call_target.label, "
                    "offset=_call_target.offset, _rt=_rt)"
                )
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    "raise GotoExternal(_module, _call_target.label, _rt=_rt)"
                )

        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE

            # Validate label exists
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

            # Handle offset
            ctx.emitter.line("if _call_target.offset is not None:")
            with ctx.emitter.indented():
                ctx.emitter.line(
                    "_label_line = _label_lines.get(_call_target.label, 0)"
                )
                ctx.emitter.line(
                    "_target_line = (_label_line + 1) + _call_target.offset"
                )
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
                    ctx.emitter.line("return (_target_line, state)")
                else:
                    ctx.emitter.line(
                        "_label_name, _line_offset = _line_map[_target_line]"
                    )
                    ctx.emitter.line(
                        "_globals[_label_name](_rt, _scope=_scope, _start_offset=_line_offset)"
                    )
                    ctx.emitter.line("return")
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                if is_trampoline:
                    ctx.emitter.line("return (_call_target.label, state)")
                else:
                    ctx.emitter.line("_globals[_call_target.label](_rt, _scope=_scope)")
                    ctx.emitter.line("return")


def generate_set_argument_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> None:
    """Generate code for SET argument indirection (S @A).

    Evaluates expression to get SET argument string, executes via execute_mumps.
    """
    from m2py.codegen.expressions import generate_expr

    if expr.expression is None:
        raise ValueError("Argument indirection requires an expression")

    target_expr = generate_expr(expr.expression, ctx)
    scope_expr = scope_dict_expr(ctx)
    ctx.emitter.line(f'_rt.execute_mumps("S " + str({target_expr}), {scope_expr})')


def generate_increment_indirection(
    var: "MIndirection",
    ctx: "GeneratorContext",
    incr_expr: str = '"1"',
) -> str:
    """Generate Python expression for $INCREMENT with indirection.

    Delegates to _rt.increment_indirected(). No NakedGlobal handling.
    Complex expressions wrapped with m_str() and consume one level.
    """
    return _build_indirection_call(
        var,
        ctx,
        "increment_indirected",
        extra_args_after_scope=f", {incr_expr}",
        handle_naked=False,
        complex_wrapper="m_str",
    )


def generate_lock_indirection(
    lock_expr: str,
    lockop: str,
    timeout_expr: "str | None",
    subscripts_expr: "str | None",
    levels: int = 1,
) -> str:
    """Generate Python code for an indirected LOCK target.

    Follows the same pattern as other indirection generators.

    Args:
        lock_expr: Python expression for the indirection source variable name
        lockop: Lock operation: "", "+", "-"
        timeout_expr: Optional Python expression for timeout value
        subscripts_expr: Optional Python expression for per-level subscripts
        levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)

    Returns:
        Python code string that calls _rt.lock_indirected()
    """
    parts = [f"_rt.lock_indirected({lock_expr}, _scope"]

    # Add lockop
    parts.append(f', lockop="{lockop}"')

    # Add optional timeout
    if timeout_expr is not None:
        parts.append(f", timeout={timeout_expr}")

    # Add levels if not the default (1)
    if levels != 1:
        parts.append(f", levels={levels}")

    # Add subscripts if present
    if subscripts_expr is not None:
        parts.append(f", per_level_subscripts={subscripts_expr}")

    parts.append(")")
    return "".join(parts)


__all__ = [
    "generate_name_indirection",
    "generate_argument_indirection",
    "generate_name_indirection_write",
    "generate_name_indirection_kill",
    "generate_name_indirection_for",
    "generate_merge_indirection_name",
    "generate_data_indirection_name",
    "generate_get_indirection_name",
    "generate_increment_indirection",
    "generate_query_indirection_name",
    "generate_indirect_do",
    "generate_indirect_goto",
    "generate_set_argument_indirection",
    "generate_lock_indirection",
]
