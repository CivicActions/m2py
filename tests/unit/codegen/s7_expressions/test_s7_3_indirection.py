"""Tests for Indirection code generation (§7.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.3
Spec 012: Phase 3 - User Story 1: Name Indirection
"""

import pytest


@pytest.mark.codegen
class TestIndirectionCodegen:
    """Codegen-level tests for indirection code generation (§7.3)."""

    def test_name_indirection_read(self, generate_python):
        """Name indirection read generates _rt.get_var call (T020).

        In MUMPS, @X where X contains a variable name accesses that variable.
        Example: S X="VAR",Y=@X means Y gets the value of VAR
        """
        code = generate_python('TEST S X="VAR",VAR=5,Y=@X Q\n')

        # Should generate runtime get_var call for @X
        assert "_rt.get_var" in code
        # Should include scope reference
        assert "_scope" in code

    def test_name_indirection_write(self, generate_python):
        """Name indirection write generates _rt.set_var call (T021).

        In MUMPS, S @X=1 where X contains a variable name sets that variable.
        Example: S X="VAR",@X=1 means VAR gets the value 1
        """
        code = generate_python('TEST S X="VAR",@X=1 Q\n')

        # Should generate runtime set_var call for @X=1
        assert "_rt.set_var" in code
        # Should include scope reference
        assert "_scope" in code

    def test_multi_level_indirection(self, generate_python):
        """Multi-level indirection generates resolve_indirection call (T022).

        In MUMPS, @@X means double indirection.
        Example: S A="B",B="C",C=100,X=@@A means X gets 100
        """
        code = generate_python('TEST S A="B",B="C",C=100,X=@@A Q\n')

        # Should generate runtime resolve_indirection call for @@A
        assert "_rt.resolve_indirection" in code
        # Should include levels=2 for double indirection
        assert ", 2," in code
        # Should include scope reference
        assert "_scope" in code

    def test_subscript_indirection(self, execute_mumps):
        """Subscript indirection @VAR as subscript evaluates VAR's value (§7.3).

        In MUMPS: S X(@VAR) where VAR="A" and A=999 → sets X(999)
        The @VAR is evaluated first (getting the value of A), then that value
        is used as the subscript.
        """
        result = execute_mumps('TEST S SUB="A" S A=999 S X(@SUB)=2 W X(999) Q')
        assert result.output == "2"

    def test_subscript_indirection_read(self, execute_mumps):
        """Subscript indirection works for reading subscripted values (§7.3)."""
        result = execute_mumps('TEST S SUB="KEY" S KEY=1 S X(1)=42 W X(@SUB) Q')
        assert result.output == "42"

    def test_argument_indirection(self, execute_mumps):
        """Argument indirection @VAR where VAR contains variable name (§7.3).

        In MUMPS: W @ARG where ARG="X" writes the value of X.
        The @ARG is evaluated (getting "X"), then X's value is retrieved.
        """
        result = execute_mumps('TEST S ARG="X" S X=123 W @ARG Q')
        assert result.output == "123"

    def test_argument_indirection_in_set(self, execute_mumps):
        """Argument indirection works as SET target (§7.3).

        In MUMPS: S @ARG=5 where ARG="X=5" executes SET X=5
        """
        result = execute_mumps('TEST S ARG="X=5" S @ARG W X Q')
        assert result.output == "5"


@pytest.mark.codegen
class TestPatternIndirectionCodegen:
    """Codegen-level tests for pattern indirection (§7.3, §7.2.5.5).

    Spec 012 Phase 10 (T063): Pattern indirection (X?@PAT) generates
    runtime pattern matching via m_pattern_match() helper.
    """

    def test_pattern_indirection_basic(self, generate_python):
        """Pattern indirection generates m_pattern_match call (T063).

        In MUMPS, X?@PAT compiles the pattern from PAT at runtime.
        Example: S PAT="1N.N" I "123"?@PAT compiles "1N.N" and matches "123"
        """
        code = generate_python('TEST S PAT="1N.N" I "123"?@PAT W "MATCH" Q\n')

        # Should generate m_pattern_match helper call for indirect patterns
        assert "m_pattern_match" in code

    def test_pattern_indirection_with_variable_subject(self, generate_python):
        """Pattern indirection with variable subject (T063).

        Example: S PAT="1A.A",VAL="ABC" I VAL?@PAT
        """
        code = generate_python('TEST S PAT="1A.A",VAL="ABC" I VAL?@PAT W "Y" Q\n')

        # Should use m_pattern_match helper for pattern indirection
        assert "m_pattern_match" in code
        # Should read subject from VAL variable
        assert "_scope" in code

    def test_negated_pattern_indirection(self, generate_python):
        """Negated pattern indirection uses '? operator (T063).

        Example: S PAT="1N" I "A"'?@PAT W "NOT NUMERIC"
        """
        code = generate_python('TEST S PAT="1N" I "A"\'?@PAT W "NOT" Q\n')

        # Should generate m_pattern_match call
        assert "m_pattern_match" in code
        # Negated match uses int(not ...) wrapper
        assert "int(not" in code

    def test_literal_pattern_uses_m_pattern_match(self, generate_python):
        """Literal pattern (not indirect) also uses m_pattern_match (T063).

        m_pattern_match helper handles both direct and indirect patterns.
        Example: I "123"?1N.N uses m_pattern_match
        """
        code = generate_python('TEST I "123"?1N.N W "MATCH" Q\n')

        # Should use m_pattern_match helper
        assert "m_pattern_match" in code
