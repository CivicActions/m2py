"""Tests for Literals code generation (§7.1.4).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4
Spec 011 Phase 9: Decimal numeric literal tests
"""

import pytest


@pytest.mark.codegen
class TestLiteralsCodegen:
    """Codegen-level tests for literals code generation (§7.1.4)."""

    def test_integer_literal(self, execute_mumps):
        """Integer literals generate Python integers (§7.1.4)."""
        # Simple integer
        result = execute_mumps("TEST W 42 Q")
        assert result.output == "42"

        # Zero
        result = execute_mumps("TEST W 0 Q")
        assert result.output == "0"

        # Negative integer
        result = execute_mumps("TEST W -123 Q")
        assert result.output == "-123"

    def test_decimal_literal(self, execute_mumps):
        """Decimal literals generate Python floats with MUMPS formatting (§7.1.4).

        Spec 011 Phase 9: Verifies decimal literals work in expressions
        and produce correctly formatted output.
        """
        # Basic decimal
        result = execute_mumps("TEST W 3.14 Q")
        assert result.output == "3.14"

        # Decimal arithmetic - scenario 1: 1.5+2.7 = 4.2
        result = execute_mumps("TEST W 1.5+2.7 Q")
        assert result.output == "4.2"

        # Decimal arithmetic - scenario 2: 3.14*2 = 6.28
        result = execute_mumps("TEST W 3.14*2 Q")
        assert result.output == "6.28"

    def test_decimal_leading_dot(self, execute_mumps):
        """Decimal literals with leading dot (.5) work correctly (§7.1.4).

        Spec 011 Phase 9: Verifies .5 is equivalent to 0.5 and
        arithmetic produces canonical output (no trailing .0).
        """
        # Leading dot decimal - scenario 3: .5+.5 = 1 (not 1.0)
        result = execute_mumps("TEST S X=.5 W X+X Q")
        assert result.output == "1"

        # Direct leading dot
        result = execute_mumps("TEST W .5 Q")
        assert result.output == ".5"

        # Negative leading dot
        result = execute_mumps("TEST W -.5 Q")
        assert result.output == "-.5"

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
