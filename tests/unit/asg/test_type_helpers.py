"""Tests for ASG type helper functions."""

import pytest

from m2py.asg.elements import MScope
from m2py.asg.statements import MForStatement, MIfStatement, MStatement
from m2py.asg.type_helpers import (
    get_body_scope,
    get_else_scope,
    get_then_scope,
    has_body,
    has_then_scope,
)


pytestmark = pytest.mark.asg


class TestHasBody:
    """Tests for has_body() type guard."""

    def test_for_statement_has_body(self):
        """MForStatement with body returns True."""
        # Create a minimal FOR statement with a body
        scope = MScope()
        stmt = MForStatement()
        stmt.body = scope
        assert has_body(stmt) is True

    def test_statement_without_body(self):
        """Generic statement without body returns False."""
        stmt = MStatement()
        assert has_body(stmt) is False


class TestHasThenScope:
    """Tests for has_then_scope() type guard."""

    def test_if_statement_has_then_scope(self):
        """MIfStatement has then_scope."""
        stmt = MIfStatement()
        stmt.then_scope = MScope()
        assert has_then_scope(stmt) is True

    def test_statement_without_then_scope(self):
        """Generic statement without then_scope returns False."""
        stmt = MStatement()
        assert has_then_scope(stmt) is False


class TestGetBodyScope:
    """Tests for get_body_scope() helper."""

    def test_returns_scope_when_present(self):
        """Returns MScope when statement has body."""
        scope = MScope()
        stmt = MForStatement()
        stmt.body = scope
        assert get_body_scope(stmt) is scope

    def test_returns_none_when_no_body(self):
        """Returns None when statement has no body."""
        stmt = MStatement()
        assert get_body_scope(stmt) is None


class TestGetThenScope:
    """Tests for get_then_scope() helper."""

    def test_returns_scope_when_present(self):
        """Returns MScope when statement has then_scope."""
        scope = MScope()
        stmt = MIfStatement()
        stmt.then_scope = scope
        assert get_then_scope(stmt) is scope

    def test_returns_none_when_no_then_scope(self):
        """Returns None when statement has no then_scope."""
        stmt = MStatement()
        assert get_then_scope(stmt) is None


class TestGetElseScope:
    """Tests for get_else_scope() helper."""

    def test_returns_none_for_generic_statement(self):
        """Returns None for generic statement (no else_scope defined)."""
        stmt = MStatement()
        assert get_else_scope(stmt) is None
