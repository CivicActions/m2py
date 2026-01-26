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

# UNIFIED_VAR_DEPRECATED: Several functions in this module will be replaced
# by core/indirection.py (IndirectionResolver):
#   - generate_name_indirection (T003) - wrapper removed, unified function active
#   - generate_argument_indirection (T003, T128-T130) - wrapper removed, unified function active
#   - _get_scope_expr (T003)
# Spec: 018-unified-variable-system, Phase 2
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from m2py.asg.elements import MCall
    from m2py.asg.expressions import MExpr, MIndirection
    from m2py.asg.statements import MXecuteStatement
    from m2py.codegen.routine import GeneratorContext

from m2py.codegen.enums import GotoStrategy


# UNIFIED_VAR_DEPRECATED: T003 - Replace with CurrentScope.scope_expr()
def _get_scope_expr(ctx: "GeneratorContext") -> str:
    """Get the appropriate scope expression for the current context.

    In TRAMPOLINE mode with dynamic_locals, local variables are stored in
    state._locals dict. Otherwise they're in _scope (cross-routine visibility).

    Returns:
        "state._locals" in TRAMPOLINE+dynamic_locals mode, "_scope" otherwise
    """
    is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE
    if is_trampoline and ctx.uses_dynamic_locals:
        return "state._locals"
    return "_scope"


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
    inner = expr.expression
    all_subscripts: List[List["MExpr"]] = []

    # Collect outer level subscripts first
    if expr.name_indirection_subscripts:
        for sub_list in expr.name_indirection_subscripts:
            all_subscripts.append(sub_list)

    if inner is None:
        raise ValueError("Indirection has no inner expression")

    while isinstance(inner, MIndirectionType):
        levels += 1
        # Collect inner level subscripts
        if inner.name_indirection_subscripts:
            # Inner subscripts go at the beginning (they are applied first)
            for sub_list in reversed(inner.name_indirection_subscripts):
                all_subscripts.insert(0, sub_list)
        if inner.expression is None:
            raise ValueError("Nested indirection has no inner expression")
        inner = inner.expression

    return levels, inner, all_subscripts


def _generate_inner_name_expr(inner_expr: "MExpr", ctx: "GeneratorContext") -> str:
    """Generate the Python expression for the variable name to look up.

    For a simple variable like X, generates a call to _rt.get_indirection_source
    which validates that the source variable exists (T065: error for @UNDEF).

    For TRAMPOLINE mode without dynamic_locals, variables are Python locals,
    so we use the Python variable directly.

    For a subscripted variable like A(1,2), generates the full variable reference
    to get the value at that location using get_var.

    Args:
        inner_expr: The innermost expression inside indirection
        ctx: Generator context

    Returns:
        Python expression string that evaluates to the variable name
    """
    # Import here to avoid circular import
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr
    from m2py.codegen.names import translate_name
    from m2py.codegen.enums import GotoStrategy

    # Get the appropriate scope expression for this context
    scope_expr = _get_scope_expr(ctx)

    if isinstance(inner_expr, MVariable):
        var_name = inner_expr.name
        python_name = translate_name(var_name)
        if inner_expr.subscripts:
            # Subscripted variable like A(1,2) - need to get the value at that location
            # Generate the subscript expressions
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build the full variable name like "A(1,2)" and use get_var
            # We need to build the name string dynamically
            return f'str(_rt.get_var("{var_name}(" + ",".join([str(s) for s in [{subs_str}]]) + ")", {scope_expr}))'
        else:
            # Simple variable reference
            # In TRAMPOLINE mode without dynamic_locals, variables are Python locals
            if ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals:
                # Dynamic locals - use state._locals dict
                return f'_rt.get_indirection_source("{var_name}", state._locals)'
            elif ctx.strategy == GotoStrategy.TRAMPOLINE:
                # Python locals - use the variable directly
                return f"str({python_name})"
            else:
                # Use get_indirection_source to validate existence and get value
                # (T065: error for undefined indirection source)
                return f'_rt.get_indirection_source("{var_name}", _scope)'
    else:
        # Other expression - generate and convert to string if needed
        return generate_expr(inner_expr, ctx)


def _build_subscripted_name_expr(
    base_name: str, subscripts: list, ctx: "GeneratorContext", is_global: bool = False
) -> str:
    """Build a Python expression that evaluates to a subscripted variable name string.

    For example, for base_name="B" and subscripts=[1], generates code that
    produces the string "B(1)" at runtime.

    For subscripts containing variable references or complex expressions,
    generates string concatenation code that evaluates subscripts at runtime.

    Args:
        base_name: The variable name (e.g., "B" or "^GLO")
        subscripts: List of subscript expressions (ASG nodes)
        ctx: Generator context
        is_global: True if this is a global variable

    Returns:
        Python expression string that evaluates to the full variable name
    """
    from m2py.codegen.expressions import generate_expr

    if not subscripts:
        # No subscripts - just return the name
        return f'"{base_name}"'

    # Generate expressions for each subscript
    sub_exprs = [generate_expr(sub, ctx) for sub in subscripts]

    # Build string concatenation that constructs the name with subscripts at runtime
    # E.g., "B(" + ",".join([str(s) for s in [sub1, sub2]]) + ")"
    # This approach handles complex expressions (including nested indirections)
    # that can't be safely embedded in f-strings
    subs_joined = ", ".join(sub_exprs)
    return f'"{base_name}(" + ",".join([str(s) for s in [{subs_joined}]]) + ")"'


# UNIFIED_VAR_DEPRECATED: T003 - Replace with IndirectionResolver.resolve() calls
def generate_name_indirection(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection read (@VAR).

    Feature: 018-unified-variable-system (T108)
    Delegates to unified implementation which uses get_indirected().

    Args:
        expr: MIndirection ASG node with indirection_type=NAME
        ctx: Generator context

    Returns:
        Python expression string
    """
    return generate_name_indirection_unified(expr, ctx)


def _generate_name_indirection_legacy(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Legacy implementation of name indirection read (@VAR).

    DEPRECATED: Used only as fallback for complex cases that
    generate_name_indirection_unified() cannot handle.

    Spec 012 Phase 3 (T014): Generates runtime call to resolve variable
    name at runtime and read its value.

    Handles:
    - Simple indirection: @X → _rt.get_var(_rt.get_indirection_source("X", scope), scope)
    - Multi-level: @@X → _rt.resolve_indirection("X", 2, scope)
    - With subscripts: @NAME@(1,2) → _rt.get_var(append_subscripts(...), scope)
    - Multi-level with per-level subscripts: @@X@(1,2)@(5,6) → _rt.get_var(resolve_with_per_level_subscripts(...), scope)
    - Innermost subscripts: @@@B(1) → _rt.resolve_indirection("B(1)", 3, scope)

    Where 'scope' is state._locals in TRAMPOLINE+dynamic_locals mode, _scope otherwise.

    Args:
        expr: MIndirection ASG node with indirection_type=NAME
        ctx: Generator context

    Returns:
        Python expression string
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Get the appropriate scope expression for this context
    scope_expr = _get_scope_expr(ctx)

    # Count indirection levels and collect ALL subscripts (inner and outer)
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Count how many levels have subscripts
    levels_with_subs = sum(1 for s in all_subscripts if s)

    # Check if innermost expression has subscripts (e.g., B(1) in @@@B(1))
    innermost_subscripts = getattr(inner_expr, "subscripts", None) or []

    # Get the base name expression and check if it's a global variable
    # Track whether base_name_expr retrieves a VALUE vs just builds a NAME string
    # - is_simple_name: True if just a literal name string like "B"
    # - retrieves_value: True if base_name_expr already does a lookup (like for globals)
    is_global = isinstance(inner_expr, GlobalVariable)
    retrieves_value = False  # Does base_name_expr retrieve a value vs just a name?

    if isinstance(inner_expr, MVariable):
        base_name = inner_expr.name
        # If innermost has subscripts, build a name expression that includes them
        if innermost_subscripts:
            base_name_expr = _build_subscripted_name_expr(
                base_name, innermost_subscripts, ctx, is_global
            )
            is_simple_name = False  # Now it's a dynamic expression
            # But it's still just building a NAME string, not retrieving a value
        else:
            base_name_expr = f'"{base_name}"'
            is_simple_name = True
    elif is_global:
        # Global variable - generate_expr retrieves the VALUE
        # For example, generate_expr(^V(1)) produces code that gets the value at ^V(1)
        # This is what we want even if there are innermost subscripts,
        # because the value retrieval handles those subscripts correctly
        base_name_expr = generate_expr(inner_expr, ctx)
        is_simple_name = False
        retrieves_value = True  # generate_expr for global retrieves the VALUE
    else:
        base_name_expr = generate_expr(inner_expr, ctx)
        is_simple_name = False
        retrieves_value = True  # Complex expression likely retrieves a value

    # Handle different cases
    if levels_with_subs > 0:
        if levels > 1 and levels_with_subs > 1:
            # Multi-level with subscripts at MULTIPLE levels: @@X@(1,2)@(5,6)
            # Need to use per-level subscript handling and then get the final value
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_per_level_str = ", ".join(per_level_subs)
            # For global variables, the value is already resolved (skip initial resolution)
            skip_flag = "True" if is_global else "False"
            return f"_rt.get_var(str(_rt.resolve_with_per_level_subscripts({base_name_expr}, [{subs_per_level_str}], {scope_expr}, {skip_flag})), {scope_expr})"
        elif levels > 1:
            # Multi-level with subscripts at only one level
            all_subs_exprs = []
            for sub_list in all_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                all_subs_exprs.extend(sub_exprs)
            subs_args = ", ".join(all_subs_exprs)

            return f"_rt.get_var(_rt.append_subscripts(str(_rt.resolve_indirection({base_name_expr}, {levels}, {scope_expr})), {subs_args}, _scope={scope_expr}), {scope_expr})"
        else:
            # Single level with subscripts: @NAME@(1,2)
            all_subs_exprs = []
            for sub_list in all_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                all_subs_exprs.extend(sub_exprs)
            subs_args = ", ".join(all_subs_exprs)

            if is_simple_name:
                return f"_rt.get_var(_rt.append_subscripts(_rt.get_indirection_source({base_name_expr}, {scope_expr}), {subs_args}, _scope={scope_expr}), {scope_expr})"
            else:
                return f"_rt.get_var(_rt.append_subscripts(str({base_name_expr}), {subs_args}, _scope={scope_expr}), {scope_expr})"
    else:
        # No subscripts (from name_indirection_subscripts)
        if levels > 1:
            if retrieves_value:
                # base_name_expr already retrieves a VALUE (e.g., for globals)
                # so we need one less level of resolution
                return f"_rt.resolve_indirection(str({base_name_expr}), {levels - 1}, {scope_expr})"
            else:
                # base_name_expr is just a NAME string (literal or f-string)
                # need full levels of resolution
                return (
                    f"_rt.resolve_indirection({base_name_expr}, {levels}, {scope_expr})"
                )
        else:
            # Simple single-level indirection: @X
            name_expr = _generate_inner_name_expr(inner_expr, ctx)
            return f"_rt.get_var({name_expr}, {scope_expr})"

    # Simple single-level indirection: @X
    name_expr = _generate_inner_name_expr(inner_expr, ctx)
    return f"_rt.get_var({name_expr}, {scope_expr})"


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
    scope_expr = _get_scope_expr(ctx)

    # Count indirection levels and collect per-level subscripts
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    else:
        # Complex expression - generate and evaluate directly
        # This handles cases like @(expr) where expr is computed
        value_expr = generate_expr(inner_expr, ctx)
        # For computed expressions, we still need to evaluate them
        empty_flag = ", treat_empty_as_truthy=True" if if_condition else ""
        return f"_rt.evaluate_argument_indirection({value_expr}, {scope_expr}, levels=1{empty_flag})"

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


def generate_name_indirection_unified(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection READ using unified components.

    Feature: 018-unified-variable-system (T106, T111)
    Uses _rt.get_indirected() which internally uses IndirectionResolver.

    This replaces the complex logic in generate_name_indirection() with
    a single unified call that handles all cases:
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
    scope_expr = _get_scope_expr(ctx)

    # Handle NakedGlobal: @^(1) or @@^(1) or @@^(1)@(subs)
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
        return (
            f"_rt.get_indirected({naked_expr}, {scope_expr}, levels={levels}{subs_arg})"
        )

    # For other complex inner expressions (nested indirection, etc.),
    # fall back to the legacy function which handles runtime resolution
    if not isinstance(inner_expr, (MVariable, GlobalVariable)):
        # Complex case - use legacy function
        return _generate_name_indirection_legacy(expr, ctx)

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    else:
        # For complex expressions (like $EXTRACT), use the legacy function
        return _generate_name_indirection_legacy(expr, ctx)

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


def generate_name_indirection_write_unified(
    expr: "MIndirection",
    value_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection write using unified components.

    Feature: 018-unified-variable-system (T041, T111)
    Uses _rt.set_indirected() which internally uses IndirectionResolver.

    This replaces the complex logic in generate_name_indirection_write() with
    a single unified call that handles all cases:
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
    scope_expr = _get_scope_expr(ctx)

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
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
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


def generate_name_indirection_kill_unified(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection KILL using unified components.

    Feature: 018-unified-variable-system (T086)
    Uses _rt.kill_indirected() which internally uses IndirectionResolver.

    This handles all KILL indirection cases:
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
    scope_expr = _get_scope_expr(ctx)

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
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


def generate_name_indirection_for_unified(
    expr: "MIndirection",
    ctx: "GeneratorContext",
) -> str:
    """Generate Python expression for FOR loop indirection target using unified components.

    Feature: 018-unified-variable-system (T089)
    Uses _rt.resolve_for_target() which internally uses IndirectionResolver.

    FOR loop indirection like F @A=1:1:3 requires resolving the target variable
    name. For example, if A="B", the loop iterates over B.

    This handles all FOR indirection cases:
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
    scope_expr = _get_scope_expr(ctx)

    # Get the source variable name
    if isinstance(inner_expr, MVariable):
        source_name = inner_expr.name
        # Include innermost subscripts in the source name if present
        if inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            # Build name with subscripts at runtime
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
        else:
            source_expr = f'"{source_name}"'
    elif isinstance(inner_expr, GlobalVariable):
        source_name = f"^{inner_expr.name}"
        if hasattr(inner_expr, "subscripts") and inner_expr.subscripts:
            sub_exprs = [generate_expr(s, ctx) for s in inner_expr.subscripts]
            subs_str = ", ".join(sub_exprs)
            source_expr = (
                f'"{source_name}(" + ",".join(str(s) for s in [{subs_str}]) + ")"'
            )
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


def generate_name_indirection_write(
    expr: "MIndirection",
    value_expr: str,
    ctx: "GeneratorContext",
) -> str:
    """Generate Python code for name indirection write (S @VAR=value).

    .. deprecated::
        Use `generate_name_indirection_write_unified()` instead. This function
        is kept for complex cases (e.g., naked global references) that require
        runtime resolution logic not yet migrated to the unified approach.
        Feature: 018-unified-variable-system (T043)

    Spec 012 Phase 3 (T015): Generates runtime call to resolve variable
    name at runtime and write a value to it.

    Handles:
    - Simple indirection: S @X=1 → _rt.set_var(_rt.get_indirection_source("X", scope), 1, scope)
    - Multi-level: S @@X=1 → _rt.set_var(_rt.resolve_indirection("X", 1, scope), 1, scope)
    - With subscripts: S @NAME@(1,2)=5 → _rt.set_var(append_subscripts(...), 5, scope)
    - Multi-level with inner subscripts: S @@^VV@(3)=99
      The inner @^VV@(3) has subscripts that need to be applied BEFORE the outer resolution

    Where 'scope' is state._locals in TRAMPOLINE+dynamic_locals mode, _scope otherwise.

    Args:
        expr: MIndirection ASG node with indirection_type=NAME
        value_expr: Python expression for the value to set
        ctx: Generator context

    Returns:
        Python statement string
    """
    from m2py.asg.expressions import MVariable
    from m2py.parser.textx_classes import GlobalVariable
    from m2py.codegen.expressions import generate_expr

    # Get the appropriate scope expression for this context
    scope_expr = _get_scope_expr(ctx)

    # Count indirection levels and collect ALL subscripts (inner and outer)
    # all_subscripts is a list of lists, one per level (inner to outer)
    levels, inner_expr, all_subscripts = _count_indirection_levels_with_subscripts(expr)

    # Count how many levels have subscripts
    levels_with_subs = sum(1 for s in all_subscripts if s)

    # Check if innermost expression has subscripts (e.g., B(1) in S @@@B(1)=val)
    innermost_subscripts = getattr(inner_expr, "subscripts", None) or []

    # Get the base name expression - need the NAME string, not the value
    # For local variables: use get_indirection_source to get the name from the local
    # For global variables: use get_var to get the value (which is the target name)
    is_global_var = False
    if isinstance(inner_expr, MVariable):
        base_name = inner_expr.name
        # If innermost has subscripts, build a name expression that includes them
        if innermost_subscripts:
            base_name_expr = _build_subscripted_name_expr(
                base_name, innermost_subscripts, ctx, is_global=False
            )
            is_simple_name = False  # Now it's a dynamic expression
        else:
            base_name_expr = f'"{base_name}"'
            is_simple_name = True
    elif isinstance(inner_expr, GlobalVariable):
        # For global variables like ^VV, we need to GET the VALUE, which is the target name
        # Example: ^V="^VV", then @^V means "get value of ^V and use as name"
        base_name = f"^{inner_expr.name}"
        is_global_var = True
        if innermost_subscripts:
            # Has subscripts like ^VV(1) - need to include them in the name
            base_name_expr = _build_subscripted_name_expr(
                base_name, innermost_subscripts, ctx, is_global=True
            )
            is_simple_name = False
        else:
            base_name_expr = f'"{base_name}"'
            is_simple_name = True
    else:
        base_name_expr = f"str({generate_expr(inner_expr, ctx)})"
        is_simple_name = False

    # Build the target name resolution
    if levels_with_subs > 0:
        # We have subscripts to append
        if levels > 1 and levels_with_subs > 1:
            # Multi-level with subscripts at MULTIPLE levels: @@X@(1,2)@(5,6)=val
            # Need to use per-level subscript handling
            # Build the subscripts_per_level list: [[1, 2], [5, 6]]
            per_level_subs = []
            for sub_list in all_subscripts:
                if sub_list:
                    sub_exprs = [generate_expr(s, ctx) for s in sub_list]
                    per_level_subs.append(f"[{', '.join(sub_exprs)}]")
                else:
                    per_level_subs.append("[]")
            subs_per_level_str = ", ".join(per_level_subs)
            # For WRITE, base_name_expr is always a literal name string, so we DON'T skip initial resolution
            return f"_rt.set_var(str(_rt.resolve_with_per_level_subscripts({base_name_expr}, [{subs_per_level_str}], {scope_expr})), {value_expr}, {scope_expr})"
        elif levels > 1:
            # Multi-level with subscripts at only one level: @@^VV@(3)=val (subs only at outer level)
            # Flatten all subscripts (there's only one non-empty level anyway)
            all_subs_exprs = []
            for sub_list in all_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                all_subs_exprs.extend(sub_exprs)
            subs_args = ", ".join(all_subs_exprs)

            # Process:
            # 1. Get value of inner variable (^VV) → "^VV(1)"
            # 2. Append subscripts (3) → "^VV(1,3)"
            # 3. Resolve (levels-1) more times → value of "^VV(1,3)" = "^VV(2,3)"
            # 4. SET that target
            if is_simple_name:
                return f"_rt.set_var(str(_rt.resolve_with_subscripts({base_name_expr}, [{subs_args}], {levels - 1}, {scope_expr})), {value_expr}, {scope_expr})"
            else:
                return f"_rt.set_var(str(_rt.resolve_with_subscripts({base_name_expr}, [{subs_args}], {levels - 1}, {scope_expr})), {value_expr}, {scope_expr})"
        else:
            # Single level with subscripts: @NAME@(1,2)=val
            # Get the name from variable, append subscripts, set
            all_subs_exprs = []
            for sub_list in all_subscripts:
                sub_exprs = [generate_expr(sub, ctx) for sub in sub_list]
                all_subs_exprs.extend(sub_exprs)
            subs_args = ", ".join(all_subs_exprs)

            if is_global_var:
                # Global variable: get its VALUE (which is the target name), append subscripts
                # @^V@(1)=0 where ^V="^VV" → SET ^VV(1)=0
                return f"_rt.set_var(_rt.append_subscripts(str(_rt.get_var({base_name_expr}, {scope_expr})), {subs_args}, _scope={scope_expr}), {value_expr}, {scope_expr})"
            elif is_simple_name:
                # Local variable: use get_indirection_source to get the name from local var
                return f"_rt.set_var(_rt.append_subscripts(_rt.get_indirection_source({base_name_expr}, {scope_expr}), {subs_args}, _scope={scope_expr}), {value_expr}, {scope_expr})"
            else:
                return f"_rt.set_var(_rt.append_subscripts(str({base_name_expr}), {subs_args}, _scope={scope_expr}), {value_expr}, {scope_expr})"
    else:
        # No subscripts
        if levels > 1:
            # Multi-level without subscripts: @@X=val
            # Resolve levels-1 times to get the target variable name
            if is_simple_name:
                resolved_name = f"_rt.resolve_indirection({base_name_expr}, {levels - 1}, {scope_expr})"
            else:
                resolved_name = f"_rt.resolve_indirection({base_name_expr}, {levels - 1}, {scope_expr})"
            return f"_rt.set_var(str({resolved_name}), {value_expr}, {scope_expr})"
        else:
            # Simple single-level indirection: @X=val
            name_expr = _generate_inner_name_expr(inner_expr, ctx)
            return f"_rt.set_var({name_expr}, {value_expr}, {scope_expr})"


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
        Python expression string like: _rt.resolve_indirection("X", 2, scope)

    Raises:
        ValueError: If indirection has no inner expression
    """
    from m2py.asg.expressions import MVariable
    from m2py.codegen.expressions import generate_expr

    # Get the appropriate scope expression for this context
    scope_expr = _get_scope_expr(ctx)

    # Get the innermost expression by unwrapping all indirection levels
    inner_expr = expr.expression

    if inner_expr is None:
        raise ValueError("Indirection has no inner expression")

    if isinstance(inner_expr, MVariable):
        var_name = inner_expr.name
        return f'_rt.resolve_indirection("{var_name}", {levels}, {scope_expr})'
    else:
        name_expr = generate_expr(inner_expr, ctx)
        return f"_rt.resolve_indirection(str({name_expr}), {levels}, {scope_expr})"


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

    # Resolve and parse all targets (handles comma-separated multiple targets)
    # This also handles nested indirection like @L where L="@L(1),^@R"
    is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE
    if is_trampoline and ctx.uses_dynamic_locals:
        ctx.emitter.line(
            f"_call_targets = _rt.resolve_do_targets({target_str_expr}, state._locals)"
        )
    else:
        ctx.emitter.line(
            f"_call_targets = _rt.resolve_do_targets({target_str_expr}, _scope)"
        )

    # Loop over all targets (usually just one, but argument indirection can produce multiple)
    ctx.emitter.line("for _call_target in _call_targets:")
    with ctx.emitter.indented():
        # Generate dispatch code
        # Check if it's an external or local call
        ctx.emitter.line("if _call_target.routine:")
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
                        ctx.emitter.line(
                            "globals()['_' + _label_name](_rt, state, _scope, _start_offset=_line_offset)"
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
                if is_trampoline:
                    # In TRAMPOLINE mode, pass state to the function
                    ctx.emitter.line("_func(_rt, state, _scope)")
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

    # Resolve nested indirection (e.g., @L where L="@L(1)")
    # This handles MUMPS's recursive indirection resolution
    # In TRAMPOLINE mode, variables are in state._locals; in SIMPLE mode, they're in _scope
    is_trampoline = ctx.strategy == GotoStrategy.TRAMPOLINE
    if is_trampoline and ctx.uses_dynamic_locals:
        ctx.emitter.line(
            f"_resolved_target = _rt.resolve_nested_indirection({target_str_expr}, state._locals)"
        )
    else:
        ctx.emitter.line(
            f"_resolved_target = _rt.resolve_nested_indirection({target_str_expr}, _scope)"
        )

    # Parse the resolved target string
    ctx.emitter.line("_call_target = _rt.parse_call_target(_resolved_target)")

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
    scope_expr = _get_scope_expr(ctx)
    ctx.emitter.line(f'_rt.execute_mumps("S " + str({target_expr}), {scope_expr})')


def generate_pattern_indirection(
    subject_expr: str,
    pattern_expr: str,
    ctx: "GeneratorContext",
    negated: bool = False,
) -> str:
    """Generate Python code for pattern indirection (X?@PAT).

    Spec 012 Phase 10 (T060): Generate runtime call to compile the pattern
    from a variable and match against the subject.

    The generated code:
    1. Retrieves the pattern string from the variable
    2. Calls _rt.compile_pattern_indirect() to convert to regex
    3. Uses re.fullmatch() to test the subject

    Args:
        subject_expr: Python expression for the subject string
        pattern_expr: Python expression for the pattern variable/expression
        ctx: Generator context
        negated: True if this is negated match ('?), False for regular match (?)

    Returns:
        Python expression string for pattern match result (1 or 0)

    Example:
        For `I "123"?@PAT` where PAT="1N.N":
        - subject_expr: '"123"'
        - pattern_expr: '_scope.get("PAT", "")'
        - Returns: '(1 if re.fullmatch(_rt.compile_pattern_indirect(...), ...) else 0)'
    """
    # The pattern match operator sets $TEST and returns 1 or 0
    # For indirect patterns, we compile at runtime
    match_expr = (
        f"re.fullmatch(_rt.compile_pattern_indirect(str({pattern_expr})), "
        f"str({subject_expr}), re.DOTALL)"
    )

    if negated:
        # '? operator: true if pattern does NOT match
        return f"(1 if {match_expr} is None else 0)"
    else:
        # ? operator: true if pattern matches
        return f"(1 if {match_expr} is not None else 0)"


__all__ = [
    "generate_name_indirection",
    "generate_argument_indirection",
    "generate_name_indirection_write",
    "generate_name_indirection_write_unified",
    "generate_name_indirection_kill_unified",
    "generate_name_indirection_for_unified",
    "generate_multi_level_indirection",
]
