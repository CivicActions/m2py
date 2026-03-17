"""Variable access expression generators for 3-way strategy dispatch.

Consolidates inline 3-way variable-access dispatch patterns into
reusable helpers.

The three strategies are:
- SIMPLE_FUNCTIONS: variables live in ``_scope`` dict
- TRAMPOLINE + dynamic_locals: variables live in ``state._locals`` dict
- TRAMPOLINE + state_vars (static): variables are fields on ``state``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from m2py.codegen.names import translate_name

if TYPE_CHECKING:
    from m2py.codegen.routine import GeneratorContext


def _is_dynamic(ctx: "GeneratorContext") -> bool:
    """Check if context uses TRAMPOLINE with dynamic locals."""
    from m2py.codegen.enums import GotoStrategy

    return ctx.strategy == GotoStrategy.TRAMPOLINE and ctx.uses_dynamic_locals


def _is_static(ctx: "GeneratorContext", var_name: str) -> bool:
    """Check if context uses TRAMPOLINE with static state vars."""
    from m2py.codegen.enums import GotoStrategy

    return ctx.strategy == GotoStrategy.TRAMPOLINE and var_name in ctx.state_vars


def var_read_expr(var_name: str, ctx: "GeneratorContext") -> str:
    """Generate Python expression that reads a local variable's scalar value.

    Returns the appropriate expression based on the codegen strategy:

    - TRAMPOLINE + dynamic_locals: ``m_var_value(state._locals[name])``
    - TRAMPOLINE + state_vars: ``state.{python_name}``
    - SIMPLE_FUNCTIONS: ``m_var_value(_scope[name])``

    Uses ``[]`` (not ``.get()``) so that accessing an undefined variable
    raises ``KeyError``, which the label-level try/except maps to MUMPS
    error M6 (LVUNDEF) via ``_handle_etrap``.

    Args:
        var_name: MUMPS variable name (e.g., ``"X"``, ``"RESULT"``)
        ctx: Current generator context

    Returns:
        Python expression string for reading the variable's value.
    """
    py = translate_name(var_name)
    if _is_dynamic(ctx):
        return f"m_var_value(state._locals[{py!r}])"
    if _is_static(ctx, var_name):
        return f"state.{py}"
    return f"m_var_value(_scope[{py!r}])"


def var_write_stmt(var_name: str, value_expr: str, ctx: "GeneratorContext") -> str:
    """Generate Python statement that writes a scalar value to a local variable.

    Args:
        var_name: MUMPS variable name
        value_expr: Python expression for the value to write
        ctx: Current generator context

    Returns:
        Python statement string (e.g. ``state._locals.setdefault('X', MArray()).value = val``).
    """
    py = translate_name(var_name)
    if _is_dynamic(ctx):
        return f"state._locals.setdefault({py!r}, MArray()).value = {value_expr}"
    if _is_static(ctx, var_name):
        if var_name in ctx.array_vars:
            # Array vars use .value for scalar SET to preserve MArray type.
            # Without this, tuple SET like S (DIC,X)=19 would replace the
            # MArray at state.DIC with a plain string, breaking later
            # subscripted access like S DIC(0)="LX".
            return f"state.{py}.value = {value_expr}"
        return f"state.{py} = {value_expr}"
    return f"_scope.setdefault({py!r}, MArray()).value = {value_expr}"


def var_base_expr(
    var_name: str,
    ctx: "GeneratorContext",
    *,
    for_write: bool = False,
) -> str:
    """Generate Python expression for the base MArray of a local variable.

    Used when the caller needs the MArray container for subscripted
    operations (e.g., ``var_base_expr("X", ctx)[sub] = val``).

    Args:
        var_name: MUMPS variable name
        ctx: Current generator context
        for_write: If True, use ``setdefault`` (auto-vivify); if False,
            use ``get`` (returns default MArray without storing it).

    Returns:
        Python expression string for the MArray base object.
    """
    py = translate_name(var_name)
    if _is_dynamic(ctx):
        if for_write:
            return f"state._locals.setdefault({py!r}, MArray())"
        return f"state._locals.get({py!r}, MArray())"
    if _is_static(ctx, var_name):
        return f"state.{py}"
    if for_write:
        return f"_scope.setdefault({py!r}, MArray())"
    return f"_scope.get({py!r}, MArray())"


def scope_dict_expr(ctx: "GeneratorContext") -> str:
    """Return the Python expression for the scope dictionary.

    - TRAMPOLINE + dynamic_locals: ``state._locals``
    - Otherwise: ``_scope``

    Used e.g. by ``$DATA``, ``$ORDER``, ``$NAME`` and indirection helpers
    that need to pass the scope dict to a runtime function.
    """
    if _is_dynamic(ctx):
        return "state._locals"
    return "_scope"
