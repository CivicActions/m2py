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

    def test_double_level_indirection_execution(self, execute_mumps):
        """@@X chains two levels of dereference at runtime (T023).

        Example: S A="B",B="C",C=100,X=@@A W X => outputs 100
        Because @@A -> @B -> C -> 100
        """
        result = execute_mumps('TEST S A="B",B="C",C=100,X=@@A W X Q\n')
        assert result.output == "100"

    def test_subscripted_indirection_resolves_correctly(self, execute_mumps):
        """Subscripted indirection @VAR@(1,2) works correctly (§7.3.1).

        Per 1984 addition (1995__a901027.md):
        "@ARRAY@(1,2,3) where ARRAY='PRICES' refers to PRICES(1,2,3)"
        The base is resolved first, then subscripts are appended.

        YDB verified: S ARRAY="Y" S @ARRAY@(1,2)=5 W Y(1,2) → "5"
        """
        result = execute_mumps('TEST S ARRAY="Y" S @ARRAY@(1,2)=5 W Y(1,2) Q')
        assert result.output == "5"

    def test_name_indirection_subscripts_edge(self, execute_mumps):
        """Name indirection with subscripts @X@(subs) (§7.3).

        T060: Name indirection with additional subscripts
        Given: S Y(1)=99 S X="Y" W @X@(1)
        When: executed
        Then: output is "99" - @X evaluates to "Y", then @(1) adds subscript

        Reference: Finding 39 from research.md
        The @X@(subs) syntax evaluates X to get the variable name, then
        appends the subscripts to form the final variable reference.
        This exercises semantic_analyzer.py lines 267-275.
        """
        result = execute_mumps('TEST\n S Y(1)=99 S X="Y" W @X@(1),!\n Q\n')
        assert result.output == "99\n"
        assert result.success is True


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

    def test_literal_pattern_uses_inline_regex(self, generate_python):
        """Literal pattern (not indirect) uses inline re.fullmatch (T063).

        Direct patterns are pre-compiled during analysis and use inline
        re.fullmatch() for better performance. Only indirect patterns
        use m_pattern_match() runtime helper.
        Example: I "123"?1N.N uses re.fullmatch with pre-compiled regex
        """
        code = generate_python('TEST I "123"?1N.N W "MATCH" Q\n')

        # Direct patterns use inline re.fullmatch (not m_pattern_match)
        assert "re.fullmatch(" in code
        # The pattern match expression should NOT call m_pattern_match function
        # (it may still be in imports, but not used for the expression)
        assert "m_pattern_match(_scope" not in code
        assert "m_pattern_match(str(" not in code


# =============================================================================
# Argument Indirection Execution Tests (Spec 012 Phase 9, T059)
# =============================================================================


@pytest.mark.codegen
class TestArgumentIndirectionExecution:
    """Execution tests for SET argument indirection runtime behavior (T059).

    Spec 012 Phase 9: Support S @A where A contains "X=1,Y=2".
    These tests execute generated Python code to verify argument
    indirection works correctly at runtime.
    """

    def test_argument_indirection_multiple_vars(self, execute_mumps):
        """S A="X=1",B="Y=2" S @A,@B sets both X and Y (T059).

        Spec 012 Phase 9 acceptance scenario:
        Given: S A="X=1",B="Y=2" S @A,@B
        When: executed
        Then: X=1 and Y=2
        """
        result = execute_mumps('TEST S A="X=1",B="Y=2" S @A,@B W X,Y Q\n')
        assert result.output == "12"

    def test_argument_indirection_string_with_multiple_assigns(self, execute_mumps):
        """S A="X=1,Y=2" S @A processes entire string as SET args (T059).

        Given: S A="X=1,Y=2" S @A
        When: executed
        Then: Both X=1 and Y=2 are set from single indirection
        """
        result = execute_mumps('TEST S A="X=1,Y=2" S @A W X,Y Q\n')
        assert result.output == "12"

    def test_argument_indirection_order_preserved(self, execute_mumps):
        """S Z=9,@A,@B,W=4 processes all in left-to-right order (T059).

        Given: S A="X=1",B="Y=2" S Z=9,@A,@B,W=4
        When: executed
        Then: Z=9, X=1, Y=2, W=4 in that order
        """
        result = execute_mumps('TEST S A="X=1",B="Y=2" S Z=9,@A,@B,W=4 W Z,X,Y,W Q\n')
        assert result.output == "9124"


# =============================================================================
# Pattern Indirection Execution Tests (Spec 012 Phase 10, T064)
# =============================================================================


@pytest.mark.codegen
class TestPatternIndirectionExecution:
    """Execution tests for pattern indirection runtime behavior (T064).

    Spec 012 Phase 10: Support X?@PAT for dynamic pattern matching.
    These tests execute generated Python code to verify pattern
    indirection works correctly at runtime.
    """

    def test_pattern_indirection_numeric(self, execute_mumps):
        """S PAT="1N.N" I "123"?@PAT W "MATCH" outputs MATCH (T064).

        Spec 012 Phase 10 acceptance scenario:
        Given: S PAT="1N.N" I "123"?@PAT W "MATCH"
        When: executed
        Then: "123" matches "1N.N" (one digit, followed by any digits)
        """
        result = execute_mumps('TEST S PAT="1N.N" I "123"?@PAT W "MATCH" Q\n')
        assert result.output == "MATCH"

    def test_pattern_indirection_alpha(self, execute_mumps):
        """S PAT="1A.A" I "ABC"?@PAT W "MATCH" outputs MATCH (T064).

        Given: S PAT="1A.A" I "ABC"?@PAT W "MATCH"
        When: executed
        Then: "ABC" matches "1A.A" (one letter, followed by any letters)
        """
        result = execute_mumps('TEST S PAT="1A.A" I "ABC"?@PAT W "MATCH" Q\n')
        assert result.output == "MATCH"

    def test_pattern_indirection_no_match(self, execute_mumps):
        """S PAT="1N" I "A"?@PAT W "MATCH" outputs nothing (T064).

        Given: S PAT="1N" I "A"?@PAT W "MATCH"
        When: executed
        Then: "A" does not match "1N" (one digit), no output
        """
        result = execute_mumps('TEST S PAT="1N" I "A"?@PAT W "MATCH" Q\n')
        assert result.output == ""

    def test_negated_pattern_indirection(self, execute_mumps):
        """S PAT="1N" I "A"'?@PAT W "NOT" outputs NOT (T064).

        Negated pattern match: '?@PAT matches when pattern does NOT match.
        Given: S PAT="1N" I "A"'?@PAT W "NOT"
        When: executed
        Then: "A" does not match "1N", negation is true
        """
        result = execute_mumps('TEST S PAT="1N" I "A"\'?@PAT W "NOT" Q\n')
        assert result.output == "NOT"

    def test_pattern_indirection_with_variable_subject(self, execute_mumps):
        """Subject from variable, pattern from variable (T064).

        Given: S PAT="1N.N",VAL="42" I VAL?@PAT W "OK"
        When: executed
        Then: "42" matches "1N.N", outputs "OK"
        """
        result = execute_mumps('TEST S PAT="1N.N",VAL="42" I VAL?@PAT W "OK" Q\n')
        assert result.output == "OK"

    def test_pattern_indirection_phone_format(self, execute_mumps):
        """Complex pattern indirection for phone number format (T064).

        Given: S PAT="3N1""-""3N1""-""4N" I "555-123-4567"?@PAT W "VALID"
        When: executed
        Then: Matches phone format nnn-nnn-nnnn

        Note: MUMPS uses doubled quotes for literal strings in patterns.
        """
        result = execute_mumps(
            'TEST S PAT="3N1""-""3N1""-""4N" I "555-123-4567"?@PAT W "VALID" Q\n'
        )
        assert result.output == "VALID"
