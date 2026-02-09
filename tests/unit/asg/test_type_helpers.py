"""Unit tests for ASG type helpers (type_helpers.py).

Tests for scope helpers used in codegen and recursive walking.
"""

import pytest

from m2py.asg.elements import MScope
from m2py.asg.statements import (
    MForStatement,
    MElseStatement,
    MIfStatement,
    MWriteStatement,
)
from m2py.asg.type_helpers import (
    get_body_scope,
    get_then_scope,
    get_else_scope,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def empty_scope():
    """Create an empty MScope for testing."""
    return MScope(statements=[])


# =============================================================================
# Tests for get_body_scope()
# =============================================================================


@pytest.mark.asg
class TestGetBodyScope:
    """Tests for get_body_scope() helper function."""

    def test_returns_body_when_present(self, empty_scope):
        """Returns body scope when present."""
        stmt = MForStatement(
            loop_var=None,
            parameters=[],
            body=empty_scope,
        )
        assert get_body_scope(stmt) is empty_scope

    def test_returns_none_when_no_body(self):
        """Returns None when no body attribute."""
        stmt = MWriteStatement(arguments=[])
        assert get_body_scope(stmt) is None


# =============================================================================
# Tests for get_then_scope()
# =============================================================================


@pytest.mark.asg
class TestGetThenScope:
    """Tests for get_then_scope() helper function."""

    def test_returns_then_scope_when_present(self, empty_scope):
        """Returns then_scope when present on MIfStatement."""
        stmt = MIfStatement(
            condition=None,
            then_scope=empty_scope,
        )
        assert get_then_scope(stmt) is empty_scope

    def test_returns_none_when_no_then_scope(self):
        """Returns None when statement has no then_scope."""
        stmt = MWriteStatement(arguments=[])
        assert get_then_scope(stmt) is None


# =============================================================================
# Tests for get_else_scope()
# =============================================================================


@pytest.mark.asg
class TestGetElseScope:
    """Tests for get_else_scope() helper function."""

    def test_returns_none_for_standard_statements(self):
        """Returns None for standard statements (no else_scope)."""
        stmt = MWriteStatement(arguments=[])
        assert get_else_scope(stmt) is None

    def test_returns_none_for_if_statement(self, empty_scope):
        """Returns None for MIfStatement (no else_scope attribute)."""
        stmt = MIfStatement(
            condition=None,
            then_scope=empty_scope,
        )
        assert get_else_scope(stmt) is None

    def test_returns_none_for_else_statement(self, empty_scope):
        """Returns None for MElseStatement (uses body, not else_scope)."""
        stmt = MElseStatement(body=empty_scope)
        assert get_else_scope(stmt) is None


# =============================================================================
# Tests for Edge Cases
# =============================================================================


@pytest.mark.asg
class TestEdgeCases:
    """Tests for edge cases and branch coverage."""

    def test_get_else_scope_with_non_scope_else_scope(self):
        """get_else_scope returns None regardless of statement attributes."""

        # Create a mock-like object with else_scope that's not an MScope
        class FakeStatement:
            else_scope = "not a scope"

        stmt = FakeStatement()
        assert get_else_scope(stmt) is None
