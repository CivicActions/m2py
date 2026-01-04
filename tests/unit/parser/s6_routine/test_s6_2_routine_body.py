"""Tests for Routine Body parsing (§6.2).

Tests verify the textX grammar correctly captures routine body structure,
including level lines, formal lines, labels, and line body.

Reference: MUMPS 1995 ANSI Standard, Sections 6.2.1-6.2.5
"""

import pytest

from m2py.asg import MDoStatement, MScope, MSetStatement


@pytest.mark.parser
class TestRoutineBodyParsing:
    """Parser-level tests for Routine Body (§6.2).

    Covers:
    - §6.2.1 Level Line
    - §6.2.2 Formal Line
    - §6.2.3 Label
    - §6.2.4 Label Separator
    - §6.2.5 Line Body
    """

    def test_level_line_parsing(self, parse_mumps):
        """Level line with proper dot indentation parses correctly (§6.2.1).

        Dot blocks indicate code that executes under argumentless DO.
        """
        result = parse_mumps("TEST\n D\n . S X=1\n . S Y=2\n Q")
        assert result is not None
        label = result.labels[0]
        # First statement is argumentless DO
        do_stmt = label.body.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        # DO body contains the dot-level statements
        assert isinstance(do_stmt.body, MScope)
        assert len(do_stmt.body.statements) == 2
        assert isinstance(do_stmt.body.statements[0], MSetStatement)

    def test_formal_line_parsing(self, parse_mumps):
        """Formal line with parameter list parses correctly (§6.2.2).

        A formal line is a label with a parameter list for passing arguments.
        """
        result = parse_mumps("ADD(A,B)\n S X=A+B\n Q X")
        assert result is not None
        label = result.labels[0]
        assert label.name == "ADD"
        assert label.formal_list == ["A", "B"]

    def test_label_parsing(self, parse_mumps):
        """Label on a line parses correctly (§6.2.3).

        Labels provide entry points into the routine.
        """
        result = parse_mumps("MAIN\n S X=1\nSUB1\n S Y=2\nSUB2\n S Z=3\n Q")
        assert result is not None
        assert len(result.labels) == 3
        assert result.labels[0].name == "MAIN"
        assert result.labels[1].name == "SUB1"
        assert result.labels[2].name == "SUB2"

    def test_label_separator(self, parse_mumps):
        """Label separator (space or tab) parses correctly (§6.2.4).

        A label line can have code after the label, separated by space/tab.
        """
        # Tab separator
        result = parse_mumps("TEST\tS X=1\n Q")
        assert result is not None
        label = result.labels[0]
        assert label.name == "TEST"
        assert len(label.body.statements) >= 1

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: line body parsing")
    def test_line_body_parsing(self, parse_mumps):
        """Line body with commands parses correctly (§6.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: multiple commands on line")
    def test_multiple_commands_on_line(self, parse_mumps):
        """Multiple commands separated by spaces parse correctly (§6.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: comment after commands")
    def test_comment_after_commands(self, parse_mumps):
        """Comment (;) after commands parses correctly (§6.2.5)."""
        pytest.fail("Stub - implement test")
