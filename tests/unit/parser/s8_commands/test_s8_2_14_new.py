"""Tests for NEW command parsing (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14
"""

import pytest


@pytest.mark.parser
class TestNewCommandParsing:
    """Parser-level tests for NEW command (§8.2.14)."""

    def test_simple_new(self, command_metamodel):
        """N X - NEW single variable (§8.2.14)."""
        model = command_metamodel.model_from_str("N X", "NewCommand")
        assert len(model.vars) == 1

    def test_new_multiple(self, command_metamodel):
        """N X,Y,Z - NEW multiple variables (§8.2.14)."""
        model = command_metamodel.model_from_str("N X,Y,Z", "NewCommand")
        assert len(model.vars) == 3

    def test_exclusive_new(self, command_metamodel):
        """N (X) - NEW all except X (§8.2.14)."""
        model = command_metamodel.model_from_str("N (X)", "NewCommand")
        assert model.exclusive is not None
