"""Tests for READ command ASG analysis (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17
"""

import pytest


@pytest.mark.asg
class TestReadCommandAnalysis:
    """ASG-level tests for READ command analysis (§8.2.17)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ variable tracking")
    def test_read_variable_tracking(self, analyze_routine):
        """READ variable is tracked in output_variables (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ format controls")
    def test_read_format_controls(self, analyze_routine):
        """READ format controls (!, ?, #) are analyzed (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ timeout")
    def test_read_timeout(self, analyze_routine):
        """READ timeout expression is analyzed (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ single character")
    def test_read_single_character(self, analyze_routine):
        """READ *X single character is analyzed (§8.2.17)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestReadFixedLength:
    """Tests for READ command with fixed-length syntax (R X#n)."""

    def test_read_fixed_length_basic(self):
        """R X#5 should produce MReadTarget with fixed_length."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MReadStatement, MReadTarget

        cmds = parse_commands_from_line("R X#5")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.variable.name == "X"
        assert read_target.fixed_length is not None
        assert read_target.fixed_length.value == 5
        assert read_target.timeout is None

    def test_read_fixed_length_with_timeout(self):
        """R X#5:10 should have both fixed_length and timeout."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MReadStatement, MReadTarget

        cmds = parse_commands_from_line("R X#5:10")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.variable.name == "X"
        assert read_target.fixed_length is not None
        assert read_target.fixed_length.value == 5
        assert read_target.timeout is not None
        assert read_target.timeout.value == 10

    def test_read_fixed_length_negative(self):
        """R X#-1 should parse (runtime error, not parse error)."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MReadStatement

        cmds = parse_commands_from_line("R X#-1")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert read_target.fixed_length is not None
        # Negative value captured in expression tree

    def test_read_fixed_length_variable(self):
        """R X#N should have variable as fixed_length."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MReadStatement, MReadTarget
        from m2py.asg.expressions import MVariable

        cmds = parse_commands_from_line("R X#N")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.fixed_length is not None
        # Length is a variable reference
        assert isinstance(read_target.fixed_length, MVariable)
        assert read_target.fixed_length.name == "N"

    def test_kill_followed_by_read_fixed_length(self):
        """K A R A#-1 should parse both KILL and READ correctly."""
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.statements import MKillStatement, MReadStatement, MReadTarget

        cmds = parse_commands_from_line("K A R A#-1")
        assert len(cmds) == 2

        analyzer = SemanticAnalyzer()
        kill_stmt = analyzer.analyze(cmds[0], None)
        read_stmt = analyzer.analyze(cmds[1], None)

        assert isinstance(kill_stmt, MKillStatement)
        assert isinstance(read_stmt, MReadStatement)

        read_target = read_stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.variable.name == "A"
        assert read_target.fixed_length is not None
