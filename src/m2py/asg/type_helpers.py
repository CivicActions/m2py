"""Type narrowing helpers for ASG types.

Provides TypeGuard functions that help pyright understand
that certain MStatement subclasses have specific attributes.
"""

from typing import TYPE_CHECKING, TypeGuard, Union

if TYPE_CHECKING:
    from m2py.asg.elements import MScope
    from m2py.asg.statements import (
        MDoBlockStatement,
        MDoStatement,
        MElseStatement,
        MForStatement,
        MIfStatement,
        MStatement,
    )


# Type aliases for statement categories
StatementWithBody = Union[
    "MForStatement",
    "MDoStatement",
    "MDoBlockStatement",
    "MElseStatement",
]
StatementWithThenScope = Union["MIfStatement"]
StatementWithScopes = Union["MIfStatement", "MElseStatement"]


def has_body(stmt: "MStatement") -> TypeGuard[StatementWithBody]:
    """Check if statement has a body attribute.

    This TypeGuard narrows the type to statements that have a body:
    - MForStatement
    - MDoStatement
    - MDoBlockStatement
    - MElseStatement

    Args:
        stmt: The statement to check

    Returns:
        True if stmt has a body attribute (MScope)
    """
    return hasattr(stmt, "body") and isinstance(getattr(stmt, "body", None), MScope)


def has_then_scope(stmt: "MStatement") -> TypeGuard[StatementWithThenScope]:
    """Check if statement has a then_scope attribute.

    This TypeGuard narrows the type to MIfStatement.

    Args:
        stmt: The statement to check

    Returns:
        True if stmt has a then_scope attribute
    """
    return hasattr(stmt, "then_scope")


def has_else_scope(stmt: "MStatement") -> bool:
    """Check if statement has an else_scope attribute that is not None.

    Note: Currently no ASG statement type defines an else_scope attribute.
    In MUMPS, IF and ELSE are independent commands - ELSE checks $TEST rather
    than being structurally linked to IF. MElseStatement uses `body`, not `else_scope`.
    This helper is provided for future extensibility.

    Args:
        stmt: The statement to check

    Returns:
        True if stmt has an else_scope that is not None (currently always False)
    """
    return hasattr(stmt, "else_scope") and getattr(stmt, "else_scope", None) is not None


def get_body_scope(stmt: "MStatement") -> "MScope | None":
    """Get the body scope of a statement if it has one.

    Args:
        stmt: The statement to get the body from

    Returns:
        The body MScope if present, None otherwise
    """
    if hasattr(stmt, "body"):
        body = getattr(stmt, "body", None)
        if isinstance(body, MScope):
            return body
    return None


def get_then_scope(stmt: "MStatement") -> "MScope | None":
    """Get the then_scope of a statement if it has one.

    Args:
        stmt: The statement to get the then_scope from

    Returns:
        The then_scope MScope if present, None otherwise
    """
    if hasattr(stmt, "then_scope"):
        scope = getattr(stmt, "then_scope", None)
        if isinstance(scope, MScope):
            return scope
    return None


def get_else_scope(stmt: "MStatement") -> "MScope | None":
    """Get the else_scope of a statement if it has one.

    Note: Currently no ASG statement type defines an else_scope attribute.
    In MUMPS, ELSE is a separate command that checks $TEST, not a structural
    part of IF. MElseStatement uses `body`. This helper is for future extensibility.

    Args:
        stmt: The statement to get the else_scope from

    Returns:
        The else_scope MScope if present, None otherwise (currently always None)
    """
    if hasattr(stmt, "else_scope"):
        scope = getattr(stmt, "else_scope", None)
        if isinstance(scope, MScope):
            return scope
    return None


# Import MScope at runtime for isinstance checks
from m2py.asg.elements import MScope  # noqa: E402
