"""Code generation for indirection expressions and XECUTE command.

Spec 012: This module provides code generation support for:
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

Spec 018-unified-variable-system: All indirection handling now uses the unified
variable system. Legacy functions have been removed or migrated.
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

    Feature: 018-unified-variable-system
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


def generate_argument_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
    if_condition: bool = False,
) -> str:
    """Generate Python code for argument-level indirection using unified components.

    Feature: 018-unified-variable-system (T049, T050, T128-T130)
    This is the FIX for Challenge 6 bug.

    Argument indirection evaluates the resolved value AS AN EXPRESSION,
    NOT as a variable name to look up. For example:
    - I @A where A="1=0" → evaluates "1=0" → 0 (FALSE)
    - I @A where A="X>5" and X=10 → evaluates "X>5" → 1 (TRUE)

    The OLD behavior passed the string "1=0" to m_truth(), which
    converted to 1 (TRUE) because it starts with "1".

    The CORRECT behavior uses _rt.evaluate_argument_indirection() which:
    1. Resolves the indirection through all levels
    2. Parses the final string as a MUMPS expression
    3. Evaluates the expression with access to current scope
    4. Returns the evaluated result (not the string)

    T052: Empty string handling depends on context:
    - IF condition (if_condition=True): Empty string → 1 (TRUE)
    - Other contexts (if_condition=False): Empty string → VarExpectedError

    Args:
        expr: MIndirection ASG node with indirection_type=ARGUMENT
        ctx: Generator context
        if_condition: If True, pass treat_empty_as_truthy=True for T052 behavior

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
        # Include ALL indirection subscripts from @X@(subs) syntax
        # Note: inner_expr.subscripts (variable subscripts like X(1,2)) are
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
    # T052: For IF conditions, pass treat_empty_as_truthy=True so empty strings → TRUE
    empty_flag = ", treat_empty_as_truthy=True" if if_condition else ""
    return f"_rt.evaluate_argument_indirection({source_expr}, {scope_expr}, levels={levels}{subs_arg}{empty_flag})"


def generate_name_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection READ using unified components.

    Feature: 018-unified-variable-system (T106, T108, T111)
    Uses _rt.get_indirected() which internally uses IndirectionResolver.

    Handles all cases:
    - Simple: @X → _rt.get_indirected("X", _scope, levels=1)
    - Multi-level: @@X → _rt.get_indirected("X", _scope, levels=2)
    - With subscripts: @X@(1,2) → _rt.get_indirected("X", _scope, levels=1, per_level_subscripts=[[1,2]])
    - NakedGlobal: @^(1) → _rt.get_indirected(resolved_name, _scope, levels=0)
    - Multi-level NakedGlobal: @@^(1) → _rt.get_indirected(resolved_name, _scope, levels=1)

    Args:
        expr: MIndirection ASG node with indirection_type=NAME
        ctx: Generator context

    Returns:
        Python expression string for get_indirected call
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable, NakedGlobal
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the appropriate scope expression
    scope_expr = scope_dict_expr(ctx)

    # Handle NakedGlobal: @^(1) or @@^(1) or @@^(1)@(subs)
    # The inner expression is a NakedGlobal, which when evaluated gives a VALUE
    # that is already the name string (e.g., "C(1,2)"). This is equivalent to
    # one level of indirection already being resolved.
    # Feature: 017-ydb-test-failures Phase 19 fix
    if isinstance(inner_expr, NakedGlobal):
        # Generate the expression that evaluates the naked global
        # This produces: (_rt.globals.get(*_rt.globals.resolve_naked((subs,))) or '')
        naked_expr = generate_expr(inner_expr, ctx)

        # Build per_level_subscripts argument if needed
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""

        # Use levels-1 because the naked evaluation already gives us a name directly
        # (like complex expressions). For @^(naked), levels=1 becomes 0.
        effective_levels = levels - 1
        return f"_rt.get_indirected({naked_expr}, {scope_expr}, levels={effective_levels}{subs_arg})"

    # For complex inner expressions (intrinsic functions, binary ops, etc.),
    # the expression evaluates to the target name directly. This is equivalent
    # to one level of indirection already being resolved, so we use levels-1.
    # Feature: 018-unified-variable-system (T140)
    if not isinstance(inner_expr, (MVariable, GlobalVariable)):
        source_expr = f"str({generate_expr(inner_expr, ctx)})"
        # Build per_level_subscripts argument if needed
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""
        # Use levels-1 because the expression evaluation = 1 level of resolution
        return f"_rt.get_indirected({source_expr}, {scope_expr}, levels={levels - 1}{subs_arg})"

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:  # GlobalVariable - only remaining case after earlier checks
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'

    # Build per_level_subscripts argument if needed
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
    else:
        subs_arg = ""

    return f"_rt.get_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg})"


def generate_indirection_marray_expr(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for indirected by-reference parameter using get_indirected_marray.

    This is similar to generate_name_indirection but calls _rt.get_indirected_marray()
    instead of _rt.get_indirected(). Used for .@VAR by-ref parameters in DO calls,
    where we need the MArray object (not the value) so the callee can alias it.

    Example:
        .@IX where IX="X" → _rt.get_indirected_marray("IX", _scope, levels=1)
        Returns the MArray for variable X, not its value.

    Args:
        expr: MIndirection ASG node
        ctx: Generator context

    Returns:
        Python expression string for get_indirected_marray call
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable, NakedGlobal
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the appropriate scope expression
    scope_expr = scope_dict_expr(ctx)

    # Handle NakedGlobal
    if isinstance(inner_expr, NakedGlobal):
        naked_expr = generate_expr(inner_expr, ctx)
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""
        effective_levels = levels - 1
        return f"_rt.get_indirected_marray({naked_expr}, {scope_expr}, levels={effective_levels}{subs_arg})"

    # For complex inner expressions
    if not isinstance(inner_expr, (MVariable, GlobalVariable)):
        source_expr = f"str({generate_expr(inner_expr, ctx)})"
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""
        return f"_rt.get_indirected_marray({source_expr}, {scope_expr}, levels={levels - 1}{subs_arg})"

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:  # GlobalVariable
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'

    # Build per_level_subscripts argument if needed
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
    else:
        subs_arg = ""

    return f"_rt.get_indirected_marray({source_expr}, {scope_expr}, levels={levels}{subs_arg})"


def generate_subscript_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for indirection in subscript context (T087).

    When indirection appears within a subscript position like ^V1A(@^(4)),
    we need to evaluate the indirection and return its VALUE for use as
    a subscript, NOT validate it as a variable name.

    Example: ^V1A(@^(4)) where ^(4)="^V1A(5)" and ^V1A(5)=55
    - @^(4) should return 55 (the value), not validate "55" as a name
    - The 55 is then used as the subscript: ^V1A(55)

    This differs from NAME indirection which:
    - Resolves the indirection to a NAME
    - Validates the result is a valid variable name
    - Returns the value of THAT variable

    Args:
        expr: MIndirection ASG node
        ctx: Generator context

    Returns:
        Python expression string that evaluates the indirection for VALUE
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable, NakedGlobal
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the appropriate scope expression
    scope_expr = scope_dict_expr(ctx)

    # Handle NakedGlobal: @^(1) in subscript context
    # The naked global evaluates to a string like "^V1A(5)"
    # We need to get the VALUE at that location
    if isinstance(inner_expr, NakedGlobal):
        # Generate the expression that evaluates the naked global
        naked_expr = generate_expr(inner_expr, ctx)

        # Build per_level_subscripts argument if needed
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""

        # Use get_subscript_indirected for VALUE resolution without name validation
        return f"_rt.get_subscript_indirected({naked_expr}, {scope_expr}, levels={levels}{subs_arg})"

    # For complex inner expressions, evaluate and use levels-1
    if not isinstance(inner_expr, (MVariable, GlobalVariable)):
        source_expr = f"str({generate_expr(inner_expr, ctx)})"
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""
        return f"_rt.get_subscript_indirected({source_expr}, {scope_expr}, levels={levels - 1}{subs_arg})"

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:  # GlobalVariable
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'

    # Build per_level_subscripts argument if needed
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
    else:
        subs_arg = ""

    return f"_rt.get_subscript_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg})"


def generate_name_indirection_write(
    expr: "MIndirection",
    value_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection write using unified components.

    Feature: 018-unified-variable-system (T041, T111, T132)
    Uses _rt.set_indirected() which internally uses IndirectionResolver.

    Handles all cases:
    - Simple: @X=val → _rt.set_indirected("X", val, _scope, levels=1)
    - Multi-level: @@X=val → _rt.set_indirected("X", val, _scope, levels=2)
    - With subscripts: @X@(1,2)=val → _rt.set_indirected("X", val, _scope, levels=1, per_level_subscripts=[[1,2]])
    - NakedGlobal: @^(1)=val → _rt.set_indirected(resolved_name, val, _scope, levels=0)
    - Multi-level NakedGlobal: @@^(1)=val → _rt.set_indirected(resolved_name, val, _scope, levels=1)

    Args:
        expr: MIndirection ASG node
        value_expr: Python expression for the value to set
        ctx: Generator context

    Returns:
        Python statement string
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable, NakedGlobal
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the appropriate scope expression
    scope_expr = scope_dict_expr(ctx)

    # Handle NakedGlobal: @^(1)=val or @@^(1)=val or @@^(1)@(subs)=val
    # The inner expression is a NakedGlobal, which when evaluated gives a value
    # that serves as the source for the indirection resolution.
    # The resolved value (a naked reference string like "^(5)") goes through
    # all indirection levels - the naked expansion happens inside the resolver.
    if isinstance(inner_expr, NakedGlobal):
        # Generate the expression that evaluates the naked global
        # This produces: (_rt.globals.get(*_rt.globals.resolve_naked((subs,))) or '')
        naked_expr = generate_expr(inner_expr, ctx)

        # Build per_level_subscripts argument if needed
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""

        # Use full levels - the resolver handles naked reference expansion internally
        return f"_rt.set_indirected({naked_expr}, {value_expr}, {scope_expr}, levels={levels}{subs_arg})"

    # For complex inner expressions (concatenation, etc.) that aren't simple variables,
    # evaluate the expression at runtime and use levels=0 since the result IS the target
    if not isinstance(inner_expr, (MVariable, GlobalVariable)):
        # Generate the expression evaluation - this will be the target name string
        inner_expr_code = generate_expr(inner_expr, ctx)
        # Convert to string to handle non-string expressions
        target_expr = f"str({inner_expr_code})"

        # Build per_level_subscripts argument if any subscripts at intermediate levels
        # Note: For levels=0 with complex expressions, we need to handle subscripts
        # that were attached to the outer indirection levels
        if any(all_subscripts):
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
        else:
            subs_arg = ""

        # Use levels-1 since evaluating the inner expression already resolves one level
        # Example: @(A_B)=1 → evaluate A_B="XY", then set XY=1 (levels=0)
        # Example: @@(A_B)=1 → evaluate A_B="XY", then resolve @XY → target (levels=1)
        effective_levels = levels - 1
        return f"_rt.set_indirected({target_expr}, {value_expr}, {scope_expr}, levels={effective_levels}{subs_arg})"

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # Should not reach here - complex expressions are handled above
        raise NotImplementedError(
            f"Unexpected inner_expr type in SET indirection: {type(inner_expr).__name__}"
        )

    # Build per_level_subscripts argument if needed
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
    else:
        subs_arg = ""

    return f"_rt.set_indirected({source_expr}, {value_expr}, {scope_expr}, levels={levels}{subs_arg})"


def generate_name_indirection_kill(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection KILL using unified components.

    Feature: 018-unified-variable-system (T086, T133)
    Uses _rt.kill_indirected() which internally uses IndirectionResolver.

    Handles all KILL indirection cases:
    - Simple: K @X → _rt.kill_indirected("X", _scope, levels=1)
    - Multi-level: K @@X → _rt.kill_indirected("X", _scope, levels=2)
    - With subscripts: K @X@(1,2) → _rt.kill_indirected("X", _scope, levels=1, per_level_subscripts=[[1,2]])

    Args:
        expr: MIndirection ASG node representing KILL target
        ctx: Generator context

    Returns:
        Python statement string for kill_indirected call
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the appropriate scope expression
    scope_expr = scope_dict_expr(ctx)

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # For complex expressions, fall back to generating the inner expression
        inner_expr_code = generate_expr(inner_expr, ctx)
        source_expr = f"str({inner_expr_code})"

    # Build per_level_subscripts argument if needed
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
    else:
        subs_arg = ""

    return (
        f"_rt.kill_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg})"
    )


def generate_name_indirection_for(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for FOR loop indirection target using unified components.

    Feature: 018-unified-variable-system (T089, T134)
    Uses _rt.resolve_for_target() which internally uses IndirectionResolver.

    FOR loop indirection like F @A=1:1:3 requires resolving the target variable
    name. For example, if A="B", the loop iterates over B.

    Handles all FOR indirection cases:
    - Simple: F @A → _rt.resolve_for_target("A", _scope, levels=1)
    - Multi-level: F @@A → _rt.resolve_for_target("A", _scope, levels=2)
    - With subscripts: F @A@(1) → _rt.resolve_for_target("A", _scope, levels=1, per_level_subscripts=[[1]])

    Args:
        expr: MIndirection ASG node representing FOR loop variable
        ctx: Generator context

    Returns:
        Python expression string that evaluates to the final variable name
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the appropriate scope expression
    scope_expr = scope_dict_expr(ctx)

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # For complex expressions, fall back to generating the inner expression
        inner_expr_code = generate_expr(inner_expr, ctx)
        source_expr = f"str({inner_expr_code})"

    # Build per_level_subscripts argument if needed
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
    else:
        subs_arg = ""

    return f"_rt.resolve_for_target({source_expr}, {scope_expr}, levels={levels}{subs_arg})"


def generate_merge_indirection_name(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for MERGE indirection target name using unified API.

    Feature: 018-unified-variable-system (T143e)
    Uses _rt.resolve_for_target() which uses IndirectionResolver internally.

    MERGE indirection like M @A=B or M B=@A requires resolving the target variable
    name. For example, if A="X", we need to get "X" as the variable name.

    Handles all MERGE indirection cases:
    - Simple: M @A=B → _rt.resolve_for_target("A", _scope, levels=1)
    - Multi-level: M @@A=B → _rt.resolve_for_target("A", _scope, levels=2)
    - With subscripts: M @A@(1)=B → _rt.resolve_for_target("A", _scope, levels=1, per_level_subscripts=[[1]])

    Args:
        expr: MIndirection ASG node representing MERGE variable
        ctx: Generator context

    Returns:
        Python expression string that evaluates to the target variable name
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the appropriate scope expression
    scope_expr = scope_dict_expr(ctx)

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
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # For complex expressions, fall back to generating the inner expression
        inner_expr_code = generate_expr(inner_expr, ctx)
        source_expr = f"str({inner_expr_code})"

    # Build per_level_subscripts argument if needed
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        subs_arg = f", per_level_subscripts=[{', '.join(per_level_subs)}]"
    else:
        subs_arg = ""

    return f"_rt.resolve_for_target({source_expr}, {scope_expr}, levels={levels}{subs_arg})"


def generate_data_indirection_name(
    var: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for $DATA indirection target name using unified API.

    Feature: 018-unified-variable-system (T143f)
    Uses _rt.resolve_for_target() which uses IndirectionResolver internally.

    $DATA indirection like $D(@A) requires resolving the target variable
    name. For example, if A="X", we need to get "X" as the variable name.

    For $D(@A@(1,2)), we resolve @A to get "ARR", then append (1,2) to get "ARR(1,2)".
    The subscripts from name_indirection_subscripts are POST-resolution appendages,
    not per-level subscripts for the resolver.

    Handles TRAMPOLINE strategy compatibility by using appropriate scope.

    Args:
        var: MIndirection ASG node representing $DATA argument
        ctx: Generator context

    Returns:
        Python expression string for _rt.get_data() call
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels - we DON'T use per_level_subscripts for $DATA
    # because name_indirection_subscripts are appended AFTER resolution
    levels, inner_expr = _count_indirection_levels(var)

    # Build subscript string for name concatenation (applied AFTER resolution)
    # Uses _format_subscript() to properly quote string subscripts in the
    # constructed name string. Without this, f'({"A"})' evaluates to '(A)'
    # instead of '("A")', causing get_data to misinterpret the subscript.
    if var.name_indirection_subscripts:
        all_subs = []
        for sub_list in var.name_indirection_subscripts:
            sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
            all_subs.extend(sub_exprs)
        if len(all_subs) == 1:
            subs_fstr = f"f'({{_format_subscript({all_subs[0]})}})'"
        else:
            subs_parts = ",".join(f"{{_format_subscript({s})}}" for s in all_subs)
            subs_fstr = f"f'({subs_parts})'"
    else:
        subs_fstr = "''"

    # Get the appropriate scope expression based on strategy
    scope_expr = scope_dict_expr(ctx)

    # Get the source expression
    if isinstance(inner_expr, GlobalVariable):
        # Global variable as indirection source: @^V1A(@A) reads value from ^V1A(subscript)
        # then resolves that as a variable name
        global_name = inner_expr.name
        # Check if the global has subscripts that need to be evaluated
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            # Build the full global reference string: "^NAME(sub1,sub2,...)"
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"^{global_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            # No subscripts: just "^NAME"
            source_expr = f'"^{global_name}"'
        # Use resolve_for_target to get the resolved name, then call get_data
        name_expr = (
            f"_rt.resolve_for_target({source_expr}, {scope_expr}, levels={levels})"
        )
        return f"_rt.get_data({name_expr} + {subs_fstr}, {scope_expr})"
    elif isinstance(inner_expr, (MVariable, MLocalVariable)):
        source_name = inner_expr.name

        # Use resolve_for_target to get the name, then call get_data
        # No per_level_subscripts needed - name_indirection_subscripts are appended after
        name_expr = (
            f'_rt.resolve_for_target("{source_name}", {scope_expr}, levels={levels})'
        )
        return f"_rt.get_data({name_expr} + {subs_fstr}, {scope_expr})"
    else:
        # For complex expressions, fall back to generating the inner expression
        inner_expr_code = generate_expr(inner_expr, ctx)
        name_expr = f"str({inner_expr_code})"
        return f"_rt.get_data({name_expr} + {subs_fstr}, {scope_expr})"


def generate_get_indirection_name(
    var: "MIndirection",
    ctx: "GeneratorContext",
    default_expr: str = '""',
) -> str:
    """Generate Python expression for $GET indirection using unified API.

    Feature: 018-unified-variable-system
    Uses _rt.get_indirected() which uses IndirectionResolver internally.

    $GET indirection like $G(@A) requires resolving the target variable
    and returning its value (or default if undefined).

    For $G(@A@(1,2)), we resolve @A to get "ARR", then get ARR(1,2).
    For $G(@@B(3)@(4,67)), we resolve @B(3) twice then append (4,67).
    For $G(@@$E("NAME",2,3)), the function evaluates to "AM" directly,
    so we use levels-1 since the expression itself is one level.

    Args:
        var: MIndirection ASG node representing $GET argument
        ctx: Generator context
        default_expr: Python expression for the default value

    Returns:
        Python expression string for the $GET result
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect all subscripts from all levels
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(var)

    # Get the appropriate scope expression based on strategy
    scope_expr = scope_dict_expr(ctx)

    # Get the source expression - include subscripts from inner variable
    if isinstance(inner_expr, GlobalVariable):
        # Global variable as indirection source - pass the NAME, not the value
        # The resolver will do the value lookup
        global_name = inner_expr.name
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"^{global_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            # Pass the global name as a string, not its value
            source_expr = f'"^{global_name}"'
    elif isinstance(inner_expr, (MVariable, MLocalVariable)):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # Complex expression (intrinsic function, binary op, etc.)
        # The expression evaluates to a STRING that is the SOURCE for indirection.
        # Unlike variable sources, the expression result IS the first "level",
        # so we use levels-1 for the actual resolution count.
        inner_expr_code = generate_expr(inner_expr, ctx)

        # For complex expressions with subscripts at level 0, we need to apply
        # those subscripts to the source BEFORE any resolution.
        # This is because @$P(...)@(subs) means: $P result + subs = target name
        if all_subscripts and all_subscripts[0]:
            # Apply first subscript set to the source expression
            first_subs = all_subscripts[0]
            sub_exprs = [generate_expr(s, ctx) for s in first_subs]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f"_rt.append_subscripts_to_name(str({inner_expr_code}), [{subs_str}])"
            )
            # Remove the first subscript set since it's now in the source
            all_subscripts = all_subscripts[1:]
        else:
            source_expr = f"str({inner_expr_code})"

        # Adjust levels: function result IS the first "level" (like one lookup already done)
        # For @$func(), levels=1 → levels-1=0 (just use result as name)
        # For @@$func(), levels=2 → levels-1=1 (one lookup needed)
        levels = levels - 1

    # Build per_level_subscripts from all collected subscripts
    per_level_subs_code = None
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        per_level_subs_code = f"[{', '.join(per_level_subs)}]"

    # Build the get_indirected call
    subs_arg = (
        f", per_level_subscripts={per_level_subs_code}" if per_level_subs_code else ""
    )

    # For $GET, we need to handle the default case
    # get_indirected returns "" for undefined, but $GET should return the specified default
    # We use allow_undefined=True to suppress LVUNDEF error for $GET
    # Then use a conditional: value if value != "" or not using default, else default
    if default_expr == '""':
        # Simple case - default is empty string, same as get_indirected default
        return f"_rt.get_indirected({source_expr}, {scope_expr}, levels={levels}{subs_arg}, allow_undefined=True)"
    else:
        # Need to check for empty string and substitute default
        # Note: This is not 100% correct because it can't distinguish between
        # "undefined" and "defined as empty string" - but this matches standard $GET behavior
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

    Feature: 018-unified-variable-system
    Uses _rt.get_name() to resolve the variable name and build canonical form.

    $NAME indirection like $NA(@A) requires resolving the target variable
    name and returning it in canonical form.

    For $NA(@A@(1,2)) where A="X", we want to return "X(1,2)".
    For $NA(@A,2) where A="X(1,2,3)", we want to return "X(1,2)".
    For $NA(@@@VV(0)@(12,456)), we need to:
      - Use source "VV(0)" (with inner subscripts)
      - Pass per_level_subscripts=[[12, 456]] for the @(12,456)
      - levels=3 for the @@@

    Args:
        var: MIndirection ASG node representing $NAME argument
        ctx: Generator context
        depth_expr: Optional Python expression for the depth parameter

    Returns:
        Python expression string for the $NAME result
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect all subscripts from all levels
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(var)

    # Get the appropriate scope expression based on strategy
    scope_expr = scope_dict_expr(ctx)

    # Build per_level_subscripts from all collected subscripts
    per_level_subs_code = None
    if any(all_subscripts):
        per_level_subs = []
        for sub_list in all_subscripts:
            if sub_list:
                sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                per_level_subs.append(f"[{', '.join(sub_exprs)}]")
            else:
                per_level_subs.append("[]")
        per_level_subs_code = f"[{', '.join(per_level_subs)}]"

    # Build the source expression with inner subscripts
    if isinstance(inner_expr, GlobalVariable):
        global_name = inner_expr.name
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"^{global_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"^{global_name}"'
    elif isinstance(inner_expr, (MVariable, MLocalVariable)):
        source_name = inner_expr.name
        # Include inner subscripts in the source expression
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        # Complex expression (function call, etc.) - evaluate directly
        # The expression result IS a name string, so for $NAME(@func()):
        # - If levels=1, the function result IS the name (no lookup needed)
        # - If levels>1, we need levels-1 lookups (one level consumed by the expression)
        inner_expr_code = generate_expr(inner_expr, ctx)
        source_expr = f"str({inner_expr_code})"
        # Reduce levels by 1 since the expression itself provides the first "level"
        levels = levels - 1

    # Build resolve_for_target call with all parameters
    subs_arg = (
        f", per_level_subscripts={per_level_subs_code}" if per_level_subs_code else ""
    )

    # If levels is 0 after adjustment (for simple @func() case), skip resolve
    if levels == 0:
        # No resolution needed - the source expression IS the name
        if per_level_subs_code:
            # Need to append subscripts to the name
            name_expr = (
                f"_rt._append_subscripts_to_name({source_expr}, {per_level_subs_code})"
            )
        else:
            name_expr = source_expr
    else:
        name_expr = f"_rt.resolve_for_target({source_expr}, {scope_expr}, levels={levels}{subs_arg})"

    # Build the get_name call
    # Note: extra_subscripts is () now since all subscripts go through per_level_subscripts
    if depth_expr is not None:
        depth_arg = f", depth=int(m_num({depth_expr}))"
    else:
        depth_arg = ""

    return f"_rt.get_name({name_expr}, (), {scope_expr}{depth_arg})"


def generate_query_indirection_name(
    var: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for $QUERY indirection using unified API.

    Feature: 018-unified-variable-system
    Uses _rt.resolve_for_target() to resolve the variable name, then
    calls m_query_by_name for the traversal.

    $QUERY indirection like $Q(@A) requires resolving the target variable
    name, then finding the next node in depth-first traversal.

    For $Q(@A@("")), we resolve @A to get "ARR", then query from ARR("").

    Args:
        var: MIndirection ASG node representing $QUERY argument
        ctx: Generator context

    Returns:
        Python expression string for the $QUERY result
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr
    from m2py.codegen.statements import gen_subscripts_tuple

    # Count indirection levels
    levels, inner_expr = _count_indirection_levels(var)

    # Build subscript tuple for the starting point
    # Only include subscripts if explicitly provided via @var@(subs) syntax
    all_subs = []
    for sub_list in var.name_indirection_subscripts or []:
        sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
        all_subs.extend(sub_exprs)
    subscripts_tuple = gen_subscripts_tuple(all_subs, ctx)

    # Get the appropriate scope expression based on strategy
    scope_expr = scope_dict_expr(ctx)

    # Get the source expression
    if isinstance(inner_expr, GlobalVariable):
        # Global variable as indirection source
        global_name = inner_expr.name
        name_expr = f'str((_rt.globals.get({global_name!r}, ()) or ""))'
        return f"_rt.get_query({name_expr}, {subscripts_tuple}, {scope_expr})"
    elif isinstance(inner_expr, (MVariable, MLocalVariable)):
        source_name = inner_expr.name
        # Use resolve_for_target to get the name
        name_expr = (
            f'_rt.resolve_for_target("{source_name}", {scope_expr}, levels={levels})'
        )
        return f"_rt.get_query({name_expr}, {subscripts_tuple}, {scope_expr})"
    else:
        inner_expr_code = generate_expr(inner_expr, ctx)
        name_expr = f"str({inner_expr_code})"
        return f"_rt.get_query({name_expr}, {subscripts_tuple}, {scope_expr})"


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
    # For DO/GOTO indirection, we generate a string like "@CMD" that
    # resolve_do_targets can parse, NOT the evaluated value.
    if label_is_indirect and target.indirection:
        # Label comes from indirection: D @CMD or D @CMD^ROUTINE
        # Generate "@CMD" string that resolve_do_targets will handle
        label_expr = _generate_do_goto_indirection_string(target.indirection, ctx)
    elif target.name:
        # Static label name
        label_expr = repr(target.name)
    else:
        label_expr = "''"

    if routine_is_indirect and target.routine_indirection:
        # Routine comes from indirection: D LABEL^@RTN or D @LBL^@RTN
        # Generate "@RTN" string that resolve_do_targets will handle
        routine_expr = _generate_do_goto_indirection_string(
            target.routine_indirection, ctx
        )
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

    # Resolve and parse all targets (handles comma-separated multiple targets)
    # This also handles nested indirection like @L where L="@L(1),^@R"
    ctx.emitter.line(
        f"_call_targets = _rt.resolve_do_targets({target_str_expr}, {scope_dict_expr(ctx)})"
    )

    # Loop over all targets (usually just one, but argument indirection can produce multiple)
    ctx.emitter.line("for _call_target in _call_targets:")
    with ctx.emitter.indented():
        # Lazy postcondition evaluation - check just before executing each target
        # This is required because the postcondition may depend on state set by previous targets
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
                ctx.emitter.line(
                    "continue  # Skip this target - postcondition is false"
                )

        # Generate dispatch code
        # Check if it's an external or local call
        # Note: if _call_target.routine == _routine_name, it's still a local call
        ctx.emitter.line(
            "if _call_target.routine and _call_target.routine != _routine_name:"
        )
        with ctx.emitter.indented():
            # External call: import routine and call label
            ctx.emitter.line("import importlib")
            # Import NameTranslator for numeric/% label lookup
            ctx.emitter.line("from m2py.core.names import NameTranslator")
            ctx.emitter.line("_module = importlib.import_module(_call_target.routine)")
            ctx.emitter.line("if _call_target.label:")
            with ctx.emitter.indented():
                # Translate label (e.g., "1" → "_n_1", "%X" → "_pct_X")
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
                # Entry label (same name as routine) - also needs translation
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
                # Note: _label_lines is 0-indexed, _line_map is 1-indexed, so add 1
                ctx.emitter.line(
                    "_target_line = (_label_line + 1) + _call_target.offset"
                )
                ctx.emitter.line(
                    "_label_name, _line_offset = _module._line_map[_target_line]"
                )
                ctx.emitter.line(
                    "getattr(_module, _label_name)(_rt, _scope=_scope, _start_offset=_line_offset)"
                )
            ctx.emitter.line("else:")
            with ctx.emitter.indented():
                ctx.emitter.line("_func(_rt, _scope=_scope)")

            # Sync _scope back to state._locals after external call in TRAMPOLINE mode
            # so the caller can see variables modified by the callee
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                ctx.emitter.line("for _k, _v in _scope.items():")
                with ctx.emitter.indented():
                    ctx.emitter.line("if isinstance(_v, MArray):")
                    with ctx.emitter.indented():
                        ctx.emitter.line("state._locals[_k] = _v")
                    ctx.emitter.line("else:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("_m = MArray()")
                        ctx.emitter.line("_m.value = _v")
                        ctx.emitter.line("state._locals[_k] = _m")

        ctx.emitter.line("else:")
        with ctx.emitter.indented():
            # Local call: use current module's functions
            # In TRAMPOLINE mode, functions are in _labels dict; in SIMPLE mode, in globals()
            is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE
            if is_trampoline:
                # _labels dict uses MUMPS label names as keys
                ctx.emitter.line("_func = _labels.get(_call_target.label)")
            else:
                # globals() uses Python function names (e.g., _n_1 for label "1")
                # Import NameTranslator for translation
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
                # _label_lines uses 0-indexed line numbers, _line_map uses 1-indexed
                # So we need to add 1 to convert before adding offset
                ctx.emitter.line(
                    "_label_line = _label_lines.get(_call_target.label, 0)"
                )
                ctx.emitter.line(
                    "_target_line = (_label_line + 1) + _call_target.offset"
                )
                ctx.emitter.line("if _target_line in _line_map:")
                with ctx.emitter.indented():
                    ctx.emitter.line(
                        "_label_name, _line_offset = _line_map[_target_line]"
                    )
                    if is_trampoline:
                        # In TRAMPOLINE mode, call internal function with state
                        # _line_map stores Python function names (e.g., "_n_1"), and we need
                        # to call the internal function (e.g., "__n_1") with an extra underscore
                        # T091d/T091e: Follow fall-through chain and catch GotoExternal
                        ctx.emitter.line("try:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "_do_target, state = _globals['_' + _label_name](_rt, state, _scope, _start_offset=_line_offset)"
                            )
                        ctx.emitter.line("except GotoExternal as _goto:")
                        with ctx.emitter.indented():
                            ctx.emitter.line(
                                "_scope.update({k: v for k, v in state._locals.items()})"
                            )
                            ctx.emitter.line(
                                "run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)"
                            )
                            ctx.emitter.line("for _k, _v in _scope.items():")
                            with ctx.emitter.indented():
                                ctx.emitter.line("if isinstance(_v, MArray):")
                                with ctx.emitter.indented():
                                    ctx.emitter.line("state._locals[_k] = _v")
                                ctx.emitter.line("else:")
                                with ctx.emitter.indented():
                                    ctx.emitter.line("_m = MArray()")
                                    ctx.emitter.line("_m.value = _v")
                                    ctx.emitter.line("state._locals[_k] = _m")
                            ctx.emitter.line("_do_target = None")
                        ctx.emitter.line("else:")
                        with ctx.emitter.indented():
                            ctx.emitter.line("while _do_target is not None:")
                            with ctx.emitter.indented():
                                ctx.emitter.line("try:")
                                with ctx.emitter.indented():
                                    ctx.emitter.line("_do_func = _labels[_do_target]")
                                    ctx.emitter.line(
                                        "_do_target, state = _do_func(_rt, state, _scope)"
                                    )
                                ctx.emitter.line("except GotoExternal as _goto:")
                                with ctx.emitter.indented():
                                    # Sync state to scope before external call
                                    ctx.emitter.line(
                                        "_scope.update({k: v for k, v in state._locals.items()})"
                                    )
                                    # Run external routine to completion
                                    ctx.emitter.line(
                                        "run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)"
                                    )
                                    # Sync scope back to state
                                    ctx.emitter.line("for _k, _v in _scope.items():")
                                    with ctx.emitter.indented():
                                        ctx.emitter.line("if isinstance(_v, MArray):")
                                        with ctx.emitter.indented():
                                            ctx.emitter.line("state._locals[_k] = _v")
                                        ctx.emitter.line("else:")
                                        with ctx.emitter.indented():
                                            ctx.emitter.line("_m = MArray()")
                                            ctx.emitter.line("_m.value = _v")
                                            ctx.emitter.line("state._locals[_k] = _m")
                                    # GotoExternal handled, exit fall-through loop
                                    ctx.emitter.line("_do_target = None")
                    else:
                        # In SIMPLE mode, call function directly (must support _start_offset)
                        # Note: SIMPLE mode doesn't support offset calls by design
                        # This should not be reached as offset calls force TRAMPOLINE
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
                    # In TRAMPOLINE mode, pass state to the function
                    # T091d: Wrap in try/except to catch GotoExternal from internal labels
                    # that do external GOTOs. This allows DO to continue after the
                    # external routine completes.
                    # T091e: Follow fall-through chain - internal functions return
                    # (next_label, state) where next_label is the label to fall through to,
                    # or None if the function explicitly returned.
                    ctx.emitter.line("try:")
                    with ctx.emitter.indented():
                        ctx.emitter.line(
                            "_do_target, state = _func(_rt, state, _scope)"
                        )
                    ctx.emitter.line("except GotoExternal as _goto:")
                    with ctx.emitter.indented():
                        # GotoExternal from initial call - handle it
                        ctx.emitter.line(
                            "_scope.update({k: v for k, v in state._locals.items()})"
                        )
                        ctx.emitter.line(
                            "run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)"
                        )
                        ctx.emitter.line("for _k, _v in _scope.items():")
                        with ctx.emitter.indented():
                            ctx.emitter.line("if isinstance(_v, MArray):")
                            with ctx.emitter.indented():
                                ctx.emitter.line("state._locals[_k] = _v")
                            ctx.emitter.line("else:")
                            with ctx.emitter.indented():
                                ctx.emitter.line("_m = MArray()")
                                ctx.emitter.line("_m.value = _v")
                                ctx.emitter.line("state._locals[_k] = _m")
                        ctx.emitter.line("_do_target = None")
                    ctx.emitter.line("else:")
                    with ctx.emitter.indented():
                        ctx.emitter.line("while _do_target is not None:")
                        with ctx.emitter.indented():
                            ctx.emitter.line("try:")
                            with ctx.emitter.indented():
                                ctx.emitter.line("_do_func = _labels[_do_target]")
                                ctx.emitter.line(
                                    "_do_target, state = _do_func(_rt, state, _scope)"
                                )
                            ctx.emitter.line("except GotoExternal as _goto:")
                            with ctx.emitter.indented():
                                # Sync state to scope before external call
                                ctx.emitter.line(
                                    "_scope.update({k: v for k, v in state._locals.items()})"
                                )
                                # Run external routine to completion
                                ctx.emitter.line(
                                    "run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)"
                                )
                                # Sync scope back to state
                                ctx.emitter.line("for _k, _v in _scope.items():")
                                with ctx.emitter.indented():
                                    ctx.emitter.line("if isinstance(_v, MArray):")
                                    with ctx.emitter.indented():
                                        ctx.emitter.line("state._locals[_k] = _v")
                                    ctx.emitter.line("else:")
                                    with ctx.emitter.indented():
                                        ctx.emitter.line("_m = MArray()")
                                        ctx.emitter.line("_m.value = _v")
                                        ctx.emitter.line("state._locals[_k] = _m")
                                # GotoExternal handled, exit fall-through loop
                                ctx.emitter.line("_do_target = None")
                else:
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
        # Use the DO/GOTO helper to generate "@VAR" string for resolve_do_targets
        label_expr = _generate_do_goto_indirection_string(target.indirection, ctx)
    elif target.name:
        # Static label name
        label_expr = repr(target.name)
    else:
        label_expr = "''"

    if routine_is_indirect and target.routine_indirection:
        # Routine comes from indirection: G LABEL^@RTN or G @LBL^@RTN
        # Use the DO/GOTO helper to generate "@VAR" string for resolve_do_targets
        routine_expr = _generate_do_goto_indirection_string(
            target.routine_indirection, ctx
        )
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

    # Resolve and parse all targets (handles comma-separated multiple targets)
    # This also handles nested indirection like @L where L="@L(1),^@R"
    # GOTO takes only the first matching target (unlike DO which loops over all)
    ctx.emitter.line(
        f"_call_targets = _rt.resolve_do_targets({target_str_expr}, {scope_dict_expr(ctx)})"
    )

    # GOTO takes only the first matching target (postconditions already evaluated)
    ctx.emitter.line("if not _call_targets:")
    with ctx.emitter.indented():
        ctx.emitter.line("pass  # No matching target - fall through")
    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        ctx.emitter.line("_call_target = _call_targets[0]")

        # Generate dispatch code
        # Check if it's an external or local GOTO
        # Note: If the target routine is the same as the current routine, treat as local
        ctx.emitter.line(
            "if _call_target.routine and _call_target.routine != _routine_name:"
        )
        with ctx.emitter.indented():
            # External GOTO: import routine and raise GotoExternal
            ctx.emitter.line("import importlib")
            ctx.emitter.line("_module = importlib.import_module(_call_target.routine)")
            # GotoExternal is imported at module level, not locally (avoids scoping issues)
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
                    # Return line number to trampoline for offset-based dispatch
                    ctx.emitter.line("return (_target_line, state)")
                else:
                    # SIMPLE mode with offset - not typically supported
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
                    # Return label name to trampoline
                    ctx.emitter.line("return (_call_target.label, state)")
                else:
                    # SIMPLE mode: call function and return
                    ctx.emitter.line("_globals[_call_target.label](_rt, _scope=_scope)")
                    ctx.emitter.line("return")


def generate_set_argument_indirection(
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
    # Use appropriate scope based on context (state._locals in TRAMPOLINE mode)
    scope_expr = scope_dict_expr(ctx)
    ctx.emitter.line(f'_rt.execute_mumps("S " + str({target_expr}), {scope_expr})')


def generate_increment_indirection(
    var: "MIndirection",
    ctx: "GeneratorContext",
    incr_expr: str = '"1"',
) -> str:
    """Generate Python expression for $INCREMENT with indirection.

    Delegates to _rt.increment_indirected() which resolves the
    indirection target and atomically increments it.

    Args:
        var: MIndirection ASG node representing $INCREMENT argument
        ctx: Generator context
        incr_expr: Python expression for the increment amount

    Returns:
        Python expression string for the $INCREMENT result
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import LocalVariable as MLocalVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Count indirection levels and collect subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(var)

    # Get scope expression
    scope_expr = scope_dict_expr(ctx)

    # Build source expression
    if isinstance(inner_expr, GlobalVariable):
        global_name = inner_expr.name
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"^{global_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"^{global_name}"'
    elif isinstance(inner_expr, (MVariable, MLocalVariable)):
        source_name = inner_expr.name
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = f'"{source_name}(" + ",".join(_format_subscript(s) for s in [{subs_str}]) + ")"'
        else:
            source_expr = f'"{source_name}"'
    else:
        inner_expr_code = generate_expr(inner_expr, ctx)
        source_expr = f"m_str({inner_expr_code})"
        levels = max(0, levels - 1)

    # Build per_level_subscripts
    per_level_parts = []
    for level_subs in all_subscripts:
        if level_subs:
            sub_exprs = [generate_expr(s, ctx) for s in level_subs]
            per_level_parts.append(f"[{', '.join(sub_exprs)}]")
        else:
            per_level_parts.append("[]")

    if any(s for s in all_subscripts):
        per_level_code = f"[{', '.join(per_level_parts)}]"
    else:
        per_level_code = "None"

    return (
        f"_rt.increment_indirected("
        f"{source_expr}, {scope_expr}, {incr_expr}, "
        f"levels={levels}, per_level_subscripts={per_level_code})"
    )


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
]
