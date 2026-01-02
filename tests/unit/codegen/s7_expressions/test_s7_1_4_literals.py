"""Tests for Literals code generation (§7.1.4).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4
"""

import pytest


@pytest.mark.codegen
class TestLiteralsCodegen:
    """Codegen-level tests for literals code generation (§7.1.4)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: integer literal")
    def test_integer_literal(self, generate_python):
        """Integer literals generate Python integers (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: decimal literal")
    def test_decimal_literal(self, generate_python):
        """Decimal literals generate Python floats (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: string literal")
    def test_string_literal(self, generate_python):
        """String literals generate Python strings (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: escaped quotes")
    def test_escaped_quotes(self, generate_python):
        """Escaped quotes generate properly escaped strings (§7.1.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: scientific notation")
    def test_scientific_notation(self, generate_python):
        """Scientific notation generates Python exponential (§7.1.4)."""
        pytest.fail("Stub - implement test")
