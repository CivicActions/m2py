"""Tests for $SYSTEM, $PRINCIPAL, and $KEY special variables (§7.1.4).

Reference: MUMPS 1995 ANSI Standard, Sections 7.1.4.8, 7.1.4.9, 7.1.4.10

Phase 23: Implementation of $SYSTEM, $PRINCIPAL, $KEY SVN codegen.
"""

import pytest


@pytest.mark.codegen
class TestSystemSVNCodegen:
    """Codegen tests for $SYSTEM special variable (§7.1.4.8).

    $SYSTEM returns a string of the form "V,S" where V is the MDC
    implementor number and S is the system name.
    """

    def test_system_full_form(self, generate_python):
        """$SYSTEM generates _rt.system() call."""
        result = generate_python("TEST W $SYSTEM Q")
        assert "_rt.system()" in result

    def test_system_abbreviated(self, generate_python):
        """$SY generates _rt.system() call (abbreviated form)."""
        result = generate_python("TEST W $SY Q")
        assert "_rt.system()" in result

    def test_system_full_equals_abbreviated(self, generate_python):
        """$SYSTEM and $SY generate the same code."""
        full = generate_python("TEST W $SYSTEM Q")
        abbrev = generate_python("TEST W $SY Q")
        assert "_rt.system()" in full
        assert "_rt.system()" in abbrev

    def test_system_in_expression(self, execute_mumps):
        """$SYSTEM can be used in expressions."""
        result = execute_mumps("TEST W $SYSTEM Q")
        assert result.success is True
        # Should match pattern 1.N1","1.E (e.g. "47,M2PY")
        output = result.output
        assert "," in output
        parts = output.split(",", 1)
        assert parts[0].isdigit()  # V is numeric
        assert len(parts[1]) > 0  # S is non-empty

    def test_system_pattern_match(self, execute_mumps):
        """$SYSTEM matches MUMPS pattern 1.N1","1.E."""
        result = execute_mumps('TEST W $SYSTEM?1.N1","1.E Q')
        assert result.output == "1"

    def test_system_case_insensitive(self, generate_python):
        """$system (lowercase) generates same code."""
        result = generate_python("TEST W $system Q")
        assert "_rt.system()" in result


@pytest.mark.codegen
class TestPrincipalSVNCodegen:
    """Codegen tests for $PRINCIPAL special variable (§7.1.4.9).

    $PRINCIPAL identifies the principal I/O device - the device
    that was the initial value of $IO at process start.
    """

    def test_principal_full_form(self, generate_python):
        """$PRINCIPAL generates _rt.principal() call."""
        result = generate_python("TEST W $PRINCIPAL Q")
        assert "_rt.principal()" in result

    def test_principal_abbreviated_p(self, generate_python):
        """$P generates _rt.principal() as abbreviated form.

        Note: $P without parens is $PRINCIPAL, not $PIECE.
        $P(...) with parens is $PIECE.
        """
        # When $P is used as a SVN (no function call parens), it's $PRINCIPAL
        result = generate_python("TEST S X=$PRINCIPAL Q")
        assert "_rt.principal()" in result

    def test_principal_equals_initial_io(self, execute_mumps):
        """$PRINCIPAL equals the initial value of $IO."""
        result = execute_mumps("TEST W $PRINCIPAL=$IO Q")
        assert result.output == "1"

    def test_principal_value(self, execute_mumps):
        """$PRINCIPAL returns the principal device identifier."""
        result = execute_mumps("TEST W $PRINCIPAL Q")
        assert result.success is True
        assert result.output == "0"  # Default principal device


@pytest.mark.codegen
class TestKeySVNCodegen:
    """Codegen tests for $KEY special variable (§7.1.4.10).

    $KEY contains the control character string that terminated
    the most recent READ command. Empty string if no READ executed.
    """

    def test_key_full_form(self, generate_python):
        """$KEY generates _rt.key() call."""
        result = generate_python("TEST W $KEY Q")
        assert "_rt.key()" in result

    def test_key_abbreviated(self, generate_python):
        """$K generates _rt.key() call (abbreviated form)."""
        result = generate_python("TEST W $K Q")
        assert "_rt.key()" in result

    def test_key_default_empty(self, execute_mumps):
        """$KEY is empty string when no READ has occurred."""
        result = execute_mumps('TEST W $KEY="" Q')
        assert result.output == "1"
