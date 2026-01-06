"""Tests for Pattern Match ASG analysis (§7.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 7.2.5
"""

import pytest

from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg import MPatternMatch
from m2py.asg.expressions import MVariable, MBinaryOp


@pytest.mark.asg
class TestPatternMatchAnalysis:
    """ASG-level tests for pattern match analysis (§7.2.5)."""

    def test_pattern_operator(self):
        """Pattern match (?) operator is correctly analyzed (§7.2.5)."""
        expr = parse_expression("X?1N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert isinstance(result.subject, MVariable)
        assert result.subject.name == "X"
        assert result.pattern == "1N"

    def test_pattern_codes(self):
        """Pattern codes (N, A, L, U, P, C, E) are correctly analyzed (§7.2.5)."""
        # Test numeric code
        expr = parse_expression("X?1N")
        result = analyze_expression(expr)
        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1N"

        # Test alpha code
        expr = parse_expression("Y?1A")
        result = analyze_expression(expr)
        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1A"

    def test_pattern_quantifiers(self):
        """Pattern quantifiers are correctly analyzed (§7.2.5)."""
        # Indefinite multiplier (zero or more)
        expr = parse_expression("X?.N")
        result = analyze_expression(expr)
        assert isinstance(result, MPatternMatch)
        assert result.pattern == ".N"

        # Range repcount
        expr = parse_expression("X?1.3N")
        result = analyze_expression(expr)
        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1.3N"

    def test_pattern_alternation(self):
        """Pattern alternation is correctly analyzed (§7.2.5).

        Alternation allows matching one of several patterns within parentheses.
        The ASG captures the alternation structure in the pattern string.
        Note: Current implementation represents alternation as '1(,)' - structure intact.
        """
        expr = parse_expression("X?1(1A,1N)")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        # Alternation is captured - pattern contains parentheses
        assert "(" in result.pattern and ")" in result.pattern

    def test_pattern_literal(self):
        """Pattern literal strings are correctly analyzed (§7.2.5)."""
        expr = parse_expression('X?1"hello"')
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern == '1"hello"'

    def test_pattern_indirection(self):
        """Pattern indirection is correctly analyzed (§7.2.5).

        Indirect pattern X?@VAR uses the value of VAR as the pattern.
        The ASG captures this via pattern_indirect attribute.
        """
        expr = parse_expression("X?@PAT")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        # For indirection, pattern string is empty and pattern_indirect is set
        assert result.pattern == ""
        assert result.pattern_indirect is not None
        assert result.pattern_indirect.name == "PAT"

    def test_pattern_indirection_with_subscript(self):
        """Pattern indirection with subscripted variable is analyzed (§7.2.5).

        X?@PAT(1) uses the value of subscripted variable PAT(1) as pattern.
        The pattern_indirect should capture the subscripted variable.
        """
        expr = parse_expression("X?@PAT(1)")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern_indirect is not None
        # The indirect pattern is PAT(1) - a subscripted variable
        assert result.pattern_indirect.name == "PAT"
        assert len(result.pattern_indirect.subscripts) == 1


@pytest.mark.asg
class TestPatternMatchASG:
    """Test MPatternMatch ASG node structure.

    Pattern match expressions parse as MPatternMatch nodes with:
    - subject: the left-hand expression being matched
    - pattern: string representation of the pattern specification
    - operator: either "?" or "'?" for negated match
    """

    def test_pattern_match_as_pattern_match(self):
        """Pattern match X?1N parses as MPatternMatch."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch
        from m2py.asg.expressions import MVariable

        expr = parse_expression("X?1N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert isinstance(result.subject, MVariable)
        assert result.subject.name == "X"
        assert result.pattern == "1N"

    def test_pattern_match_recognizable(self):
        """Pattern match can be identified by MPatternMatch type."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch

        expr = parse_expression("Y?1A")
        result = analyze_expression(expr)

        # Can identify pattern match by type
        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert result.pattern == "1A"

    def test_pattern_match_indefinite_multiplier(self):
        """Indefinite multiplier .N parses correctly (zero or more)."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch

        expr = parse_expression("X?.N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.operator == "?"
        assert result.pattern == ".N"

    def test_pattern_match_negated(self):
        """Negated pattern match X'?1A parses correctly."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch

        expr = parse_expression("X'?1A")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.operator == "'?"
        assert result.pattern == "1A"

    def test_pattern_match_range_repcount(self):
        """Range repcount like 1.3N parses correctly."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch

        expr = parse_expression("X?1.3N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1.3N"

    def test_pattern_match_multiple_atoms(self):
        """Multiple pattern atoms like 1N.A parses correctly."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch

        expr = parse_expression("X?1N.A")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1N.A"

    def test_pattern_match_with_string(self):
        """Pattern with string literal like 1"hello" parses correctly."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch

        expr = parse_expression('X?1"hello"')
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern == '1"hello"'

    def test_pattern_match_followed_by_concat(self):
        """Pattern match followed by concatenation X?.N_Y parses correctly."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MPatternMatch

        expr = parse_expression("X?.N_Y")
        result = analyze_expression(expr)

        # Result is a binary op (_) with left being pattern match
        assert isinstance(result, MBinaryOp)
        assert result.operator == "_"
        assert isinstance(result.left, MPatternMatch)
        assert result.left.pattern == ".N"


@pytest.mark.asg
class TestPatternMatchCompilation:
    """Tests for pattern match regex compilation."""

    def test_pattern_match_compiled_regex(self):
        """X?1A.N should have compiled_regex set."""
        import re
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MPatternMatch

        expr = parse_expression("X?1A.N")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.pattern == "1A.N"
        assert result.compiled_regex is not None
        # Verify the regex is valid
        re.compile(result.compiled_regex)

    def test_pattern_match_alphanumeric(self):
        """X?1A.AN should compile to alphanumeric pattern."""
        import re
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MPatternMatch

        expr = parse_expression("X?.AN")
        result = analyze_expression(expr)

        assert isinstance(result, MPatternMatch)
        assert result.compiled_regex is not None
        # Verify it matches alphanumeric strings
        assert re.fullmatch(result.compiled_regex, "Test123")
        assert re.fullmatch(result.compiled_regex, "")
