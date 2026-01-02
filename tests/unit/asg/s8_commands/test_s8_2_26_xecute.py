"""Tests for XECUTE command ASG analysis (§8.2.26).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.26

Migrated from: tests/unit/test_semantic_analyzer.py::TestXecuteConstantDetection
"""

import pytest
from tests.helpers.parsing import parse_command
from m2py.analysis.semantic_analyzer import SemanticAnalyzer
from m2py.asg.statements import MXecuteStatement


@pytest.mark.asg
class TestXecuteCommandAnalysis:
    """ASG-level tests for XECUTE command analysis (§8.2.26).

    Migrated from: TestXecuteConstantDetection
    """

    def test_xecute_constant_string(self):
        """X "S X=1" should be detected as constant (§8.2.26)."""
        cmd = parse_command('X "S X=1"')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is True
        assert result.constant_values == ["S X=1"]

    def test_xecute_multiple_constants(self):
        """X "S X=1","S Y=2" should detect both as constant (§8.2.26)."""
        cmd = parse_command('X "S X=1","S Y=2"')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is True
        assert result.constant_values == ["S X=1", "S Y=2"]

    def test_xecute_variable_expression(self):
        """X CODE should not be detected as constant (§8.2.26)."""
        cmd = parse_command("X CODE")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is False
        assert result.constant_values == []

    def test_xecute_mixed_args(self):
        """X "S X=1",CODE should not be detected as constant (§8.2.26)."""
        cmd = parse_command('X "S X=1",CODE')
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(cmd, None)

        assert isinstance(result, MXecuteStatement)
        assert result.is_constant is False

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: XECUTE static analysis limitation")
    def test_xecute_static_analysis_limitation(self, analyze_routine):
        """XECUTE limits static analysis (§8.2.26)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: XECUTE postcondition")
    def test_xecute_postcondition(self, analyze_routine):
        """XECUTE expr:condition is analyzed (§8.2.26)."""
        pytest.fail("Stub - implement test")
