"""Type helpers for ASG types.

Provides scope-access helpers used for recursive walking and analysis
of ASG statement trees.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from m2py.asg.elements import MScope
    from m2py.asg.statements import MStatement


def get_body_scope(stmt: "MStatement") -> "MScope | None":
    """Get the body scope of a statement if it has one.

    Args:
        stmt: The statement to get the body from

    Returns:
        The body MScope if present, None otherwise
    """
    if hasattr(stmt, "body"):
        return getattr(stmt, "body", None)
    return None


def get_then_scope(stmt: "MStatement") -> "MScope | None":
    """Get the then_scope of a statement if it has one.

    Args:
        stmt: The statement to get the then_scope from

    Returns:
        The then_scope MScope if present, None otherwise
    """
    if hasattr(stmt, "then_scope"):
        return getattr(stmt, "then_scope", None)
    return None


def get_else_scope(stmt: "MStatement") -> "MScope | None":
    """Get the else_scope of a statement if it has one.

    Note: No ASG statement type defines an else_scope attribute.
    In MUMPS, ELSE is a separate command that checks $TEST, not a structural
    part of IF. MElseStatement uses ``body``. This helper exists for
    completeness in recursive walking but always returns None.

    Args:
        stmt: The statement to get the else_scope from

    Returns:
        Always None (no ASG statement type defines else_scope)
    """
    return None
