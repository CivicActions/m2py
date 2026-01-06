"""Tests for READ command ASG analysis (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import SemanticAnalyzer
from m2py.asg.statements import MReadStatement, MReadTarget, MKillStatement
from m2py.asg.expressions import MVariable


@pytest.mark.asg
class TestReadCommandAnalysis:
    """ASG-level tests for READ command analysis (§8.2.17)."""

    def test_read_fixed_length_basic(self):
        """R X#5 produces MReadTarget with fixed_length (§8.2.17)."""
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

    def test_read_simple_timeout(self):
        """R X:5 produces MReadTarget with timeout only (§8.2.17)."""
        cmds = parse_commands_from_line("R X:5")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.variable.name == "X"
        assert read_target.fixed_length is None  # No fixed length
        assert read_target.timeout is not None
        assert read_target.timeout.value == 5

    def test_read_timeout(self):
        """READ timeout expression is analyzed (§8.2.17)."""
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
        """R X#-1 should parse (runtime error, not parse error) (§8.2.17)."""
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
        """R X#N has variable as fixed_length expression (§8.2.17)."""
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

    def test_read_after_kill(self):
        """K A R A#-1 should parse both KILL and READ correctly (§8.2.17)."""
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

    def test_read_variable_tracking(self):
        """READ variable is tracked in output_variables (§8.2.17).

        Verifies that READ targets are captured as MReadTarget with
        the correct variable reference for output tracking.
        """
        cmds = parse_commands_from_line("R X")
        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert isinstance(read_target.variable, MVariable)
        assert read_target.variable.name == "X"

        # Multiple READ targets
        cmds2 = parse_commands_from_line("R A,B,C")
        stmt2 = analyzer.analyze(cmds2[0], None)
        assert len(stmt2.arguments) == 3
        for i, name in enumerate(["A", "B", "C"]):
            assert isinstance(stmt2.arguments[i], MReadTarget)
            assert stmt2.arguments[i].variable.name == name

    def test_read_format_controls(self):
        """READ format controls (!, ?, #) are analyzed (§8.2.17).

        Verifies that READ format controls are captured as MFormatControl:
        - ! = NEWLINE (line feed)
        - ?n = TAB (column position)
        - # = FORMFEED (page break)
        """
        from m2py.asg.expressions import MFormatControl
        from m2py.asg.enums import FormatControlType

        # Newline format control
        cmds = parse_commands_from_line("R !")
        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.NEWLINE

        # Tab format control with column position
        cmds2 = parse_commands_from_line("R ?10")
        stmt2 = analyzer.analyze(cmds2[0], None)
        assert len(stmt2.arguments) == 1
        assert isinstance(stmt2.arguments[0], MFormatControl)
        assert stmt2.arguments[0].control_type == FormatControlType.TAB
        assert stmt2.arguments[0].expression is not None

        # Formfeed format control
        cmds3 = parse_commands_from_line("R #")
        stmt3 = analyzer.analyze(cmds3[0], None)
        assert len(stmt3.arguments) == 1
        assert isinstance(stmt3.arguments[0], MFormatControl)
        assert stmt3.arguments[0].control_type == FormatControlType.FORMFEED

        # Mixed format controls and variable
        cmds4 = parse_commands_from_line("R !,?5,X,#")
        stmt4 = analyzer.analyze(cmds4[0], None)
        assert len(stmt4.arguments) == 4
        assert isinstance(stmt4.arguments[0], MFormatControl)
        assert isinstance(stmt4.arguments[1], MFormatControl)
        assert isinstance(stmt4.arguments[2], MReadTarget)
        assert isinstance(stmt4.arguments[3], MFormatControl)

    def test_read_single_character(self):
        """READ *X single character is analyzed (§8.2.17)."""
        cmds = parse_commands_from_line("R *X")
        assert len(cmds) == 1

        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1

        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.is_char_read is True
        assert isinstance(read_target.variable, MVariable)
        assert read_target.variable.name == "X"

        # Single char read with timeout
        cmds2 = parse_commands_from_line("R *X:5")
        stmt2 = analyzer.analyze(cmds2[0], None)
        assert isinstance(stmt2, MReadStatement)
        read_target2 = stmt2.arguments[0]
        assert read_target2.is_char_read is True
        assert read_target2.timeout is not None

    def test_read_timeout_expression_analyzed(self):
        """READ timeout expression is fully analyzed (§8.2.17).

        Timeout can be a complex expression like T*2.
        """
        from m2py.asg.expressions import MBinaryOp

        cmds = parse_commands_from_line("R X:T*2")
        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.timeout is not None
        # Expression type is MBinaryOp for T*2
        assert isinstance(read_target.timeout, MBinaryOp)
        assert read_target.timeout.operator == "*"

    def test_read_char_into_global(self):
        """R *^VV("M") - READ single char into global variable (§8.2.17)."""
        cmds = parse_commands_from_line('R *^VV("M")')
        analyzer = SemanticAnalyzer()
        stmt = analyzer.analyze(cmds[0], None)

        assert isinstance(stmt, MReadStatement)
        read_target = stmt.arguments[0]
        assert isinstance(read_target, MReadTarget)
        assert read_target.is_char_read is True
        assert read_target.variable.name == "VV"
