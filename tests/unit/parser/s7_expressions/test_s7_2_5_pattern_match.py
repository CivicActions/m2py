"""Tests for Pattern Match parsing (§7.2.5).

Tests verify the textX grammar correctly captures pattern match syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.2.5
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture(scope="module")
def expr_metamodel():
    """Load the expression grammar metamodel with custom classes."""
    grammar_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


@pytest.mark.parser
class TestPatternMatchParsing:
    """Parser-level tests for Pattern Match (§7.2.5).

    Pattern matching uses the ? operator with pattern atoms.
    """

    def test_pattern_match_basic(self, expr_metamodel):
        """Basic pattern X?3N parses correctly (§7.2.5).

        Pattern matching tests if a string matches a pattern.
        '3N' means exactly 3 numeric characters.
        """
        model = expr_metamodel.model_from_str("X?3N", "Expr")
        assert model is not None
        # Verify pattern match tail exists
        assert len(model.tail) == 1
        tail = model.tail[0]
        assert tail.__class__.__name__ == "PatternMatchTail"
        assert tail.pattern is not None

    def test_pattern_with_codes(self, expr_metamodel):
        """Pattern codes (A, N, P, L, U, C, E) parse correctly (§7.2.5).

        MUMPS pattern codes:
        - A: alphabetic (a-z, A-Z)
        - N: numeric (0-9)
        - P: punctuation
        - L: lowercase (a-z)
        - U: uppercase (A-Z)
        - C: control characters
        - E: any character
        """
        # Test multiple pattern codes
        for code in ["A", "N", "P", "L", "U", "C", "E"]:
            pattern = f"X?1{code}"
            model = expr_metamodel.model_from_str(pattern, "Expr")
            assert model is not None, f"Failed to parse pattern with code {code}"
            assert model.tail[0].__class__.__name__ == "PatternMatchTail"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern quantifier range")
    def test_pattern_quantifier_range(self, parse_expression):
        """Pattern quantifier range 1.5N parses correctly (§7.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern quantifier unlimited")
    def test_pattern_quantifier_unlimited(self, parse_expression):
        """Pattern quantifier unlimited .N parses correctly (§7.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern with literal string")
    def test_pattern_with_literal(self, parse_expression):
        """Pattern with literal \"ABC\" parses correctly (§7.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern alternation")
    def test_pattern_alternation(self, parse_expression):
        """Pattern alternation (A,N) parses correctly (§7.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection")
    def test_pattern_indirection(self, parse_expression):
        """Pattern indirection X?@pattern parses correctly (§7.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: complex pattern")
    def test_complex_pattern(self, parse_expression):
        """Complex pattern 1A.E1\"-\"3N parses correctly (§7.2.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestPatternMatchGrammar:
    """Test pattern match expression parsing via MUMPSParser."""

    def test_pattern_match_simple(self):
        """Pattern match X?1A.N should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tI X?1A.N W "match"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        assert len(routine.labels) == 1

    def test_pattern_match_negated(self):
        """Negated pattern match X'?1N should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tI X\'?1N W "not numeric"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_complex(self):
        """Complex pattern X?1A.ANP should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tI NAME?1U.L W "valid"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_exact(self):
        """Pattern with exact repcount X?2N should parse (T576 fix)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=Y?2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_atleast(self):
        """Pattern with at-least repcount X?2.N should parse (T576 fix)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=Y?2.N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_atmost(self):
        """Pattern with at-most repcount X?.2N should parse (T576 fix)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=Y?.2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_numeric_repcount_range(self):
        """Pattern with range repcount X?1.2N should parse (T576 fix)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=Y?1.2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_pattern_match_multi_atom_with_repcounts(self):
        """Multi-atom pattern X?2.N.P.2N should parse (T576 fix)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=Y?2.N.P.2N\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestIndirectPatternMatchGrammar:
    """Test indirect pattern match expression parsing (T576)."""

    def test_indirect_pattern_match_simple(self):
        """Indirect pattern match X?@PAT should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=Y?@PAT\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_indirect_pattern_match_with_parens(self):
        """Indirect pattern match X?@(PAT) should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=Y?@(PAT)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_indirect_pattern_match_string_literal(self):
        """Indirect pattern match with string literal should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tS X="ABC"?@".4AN"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_indirect_pattern_with_concat(self):
        """Indirect pattern followed by concatenation should parse (VV2PAT2 line 155)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tS X="ABC"?@".4AN"_("12.34"?2.N.P.2N)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestPatternMatchDirectGrammar:
    """Direct grammar-level pattern match tests using expression metamodel."""

    @pytest.fixture(scope="class")
    def expression_metamodel(self):
        """Load the expression grammar metamodel."""
        from pathlib import Path
        from textx import metamodel_from_file

        grammar_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "m2py"
            / "grammar"
        )
        return metamodel_from_file(str(grammar_dir / "expressions.tx"), skipws=False)

    def test_pattern_operator_in_expr(self, expression_metamodel):
        """Pattern match operator ? is recognized with proper pattern syntax."""
        # X?1N - matches exactly 1 numeric character
        model = expression_metamodel.model_from_str("X?1N", "Expr")
        assert model is not None

    def test_negated_pattern(self, expression_metamodel):
        """Negated pattern '?."""
        model = expression_metamodel.model_from_str("X'?1A", "Expr")
        assert model is not None
