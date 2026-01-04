"""Tests for FOR command ASG analysis (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line, extract_for_commands
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MForStatement, MSetStatement, MWriteStatement
from m2py.asg.enums import ForLoopType, ForParamType


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestForCommandAnalysis:
    """ASG-level tests for FOR command analysis (§8.2.5)."""

    def test_for_loop_type_classification(self):
        """FOR loop_type is correctly classified for all types (§8.2.5, FR-012)."""
        # Bounded FOR
        stmt = analyze_first_command("F I=1:1:10")
        assert stmt.loop_type == ForLoopType.BOUNDED

        # Open-ended FOR
        stmt = analyze_first_command("F I=1:1")
        assert stmt.loop_type == ForLoopType.OPEN_ENDED

        # String list FOR
        stmt = analyze_first_command("F I=1,2,3")
        assert stmt.loop_type == ForLoopType.STRING_LIST

        # Argumentless FOR
        stmt = analyze_first_command("F")
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS

    def test_for_counted_loop(self):
        """FOR counted loop (start:increment:limit) is analyzed (§8.2.5)."""
        stmt = analyze_first_command("F I=1:2:10")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1

        param = stmt.parameters[0]
        assert param.param_type == ForParamType.RANGE
        assert param.start.value == 1
        assert param.step.value == 2
        assert param.end.value == 10

    def test_for_list_loop(self):
        """FOR list loop (val1,val2,val3) is analyzed (§8.2.5)."""
        stmt = analyze_first_command("F I=1,2,3")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert len(stmt.parameters) == 3
        assert all(p.param_type == ForParamType.VALUE for p in stmt.parameters)
        assert stmt.loop_type == ForLoopType.STRING_LIST

    def test_for_infinite_loop(self):
        """FOR infinite loop (argumentless) is analyzed (§8.2.5)."""
        stmt = analyze_first_command("F")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var is None or stmt.loop_var == ""
        assert len(stmt.parameters) == 0
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS

    def test_for_loop_variable(self):
        """FOR loop variable is tracked (§8.2.5)."""
        stmt = analyze_first_command("F I=1:1:10")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var is not None
        assert stmt.loop_var.name == "I"

        # String list also tracks variable
        stmt2 = analyze_first_command('F I="A","B","C"')
        assert stmt2.loop_var.name == "I"

    def test_for_nested_loops(self):
        """Nested FOR loops are correctly analyzed (§8.2.5)."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:3 F J=1:1:3 S X=I*J\n"
        routine = parser.parse(source)

        outer_for = routine.labels[0].body.statements[0]
        assert isinstance(outer_for, MForStatement)
        assert outer_for.loop_var.name == "I"
        assert len(outer_for.body.statements) == 1

        inner_for = outer_for.body.statements[0]
        assert isinstance(inner_for, MForStatement)
        assert inner_for.loop_var.name == "J"
        assert len(inner_for.body.statements) == 1
        assert isinstance(inner_for.body.statements[0], MSetStatement)

    def test_for_open_ended_loop(self):
        """FOR open-ended loop (start:increment) is analyzed (§8.2.5)."""
        stmt = analyze_first_command("F I=1:1")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.parameters[0].param_type == ForParamType.OPEN_RANGE

    def test_for_string_list_values(self):
        """FOR string list creates VALUE params (§8.2.5)."""
        fors = extract_for_commands('F I="A","B","C"')
        assert len(fors) == 1
        stmt = analyze_command(fors[0])

        assert len(stmt.parameters) == 3
        for p in stmt.parameters:
            assert p.param_type == ForParamType.VALUE


@pytest.mark.asg
class TestForBodyPopulation:
    """Tests for FOR body statement collection (§8.2.5)."""

    def test_for_body_single_command(self):
        """FOR captures single following command in body."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:3 S X=I\n"
        routine = parser.parse(source)

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1
        assert isinstance(for_stmt.body.statements[0], MSetStatement)

    def test_for_body_multiple_commands(self):
        """FOR captures multiple following commands in body."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:3 S X=I W X\n"
        routine = parser.parse(source)

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 2
        assert isinstance(for_stmt.body.statements[0], MSetStatement)
        assert isinstance(for_stmt.body.statements[1], MWriteStatement)

    def test_for_nested_for(self):
        """Nested FOR loops are properly structured."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:3 F J=1:1:3 S X=I*J\n"
        routine = parser.parse(source)

        outer_for = routine.labels[0].body.statements[0]
        assert isinstance(outer_for, MForStatement)
        assert outer_for.loop_var.name == "I"
        assert len(outer_for.body.statements) == 1

        inner_for = outer_for.body.statements[0]
        assert isinstance(inner_for, MForStatement)
        assert inner_for.loop_var.name == "J"
        assert len(inner_for.body.statements) == 1
        assert isinstance(inner_for.body.statements[0], MSetStatement)


@pytest.mark.asg
class TestForStatementAnalysis:
    """Tests for FOR command analysis."""

    def test_argumentless_for(self):
        """F produces argumentless FOR."""
        stmt = analyze_first_command("F")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var is None or stmt.loop_var == ""
        assert len(stmt.parameters) == 0
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS

    def test_for_with_range(self):
        """F I=1:1:10 produces bounded FOR."""
        stmt = analyze_first_command("F I=1:1:10")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].param_type == ForParamType.RANGE
        assert stmt.loop_type == ForLoopType.BOUNDED

    def test_for_with_values(self):
        """F I=1,2,3 produces value list FOR."""
        stmt = analyze_first_command("F I=1,2,3")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert len(stmt.parameters) == 3
        assert all(p.param_type == ForParamType.VALUE for p in stmt.parameters)
        assert stmt.loop_type == ForLoopType.STRING_LIST

    def test_for_open_ended(self):
        """F I=1:1 produces open-ended FOR."""
        stmt = analyze_first_command("F I=1:1")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.OPEN_ENDED


@pytest.mark.asg
class TestParseForCommand:
    """Test FOR command parsing to full-fidelity ASG."""

    def test_bounded_for(self):
        """F I=1:1:10 parses as bounded"""
        cmds = parse_commands_from_line("F I=1:1:10")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].param_type == ForParamType.RANGE

    def test_open_ended_for(self):
        """F I=1:1 parses as open-ended"""
        cmds = parse_commands_from_line("F I=1:1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.parameters[0].param_type == ForParamType.OPEN_RANGE

    def test_value_list_for(self):
        """F I=1,2,3 parses as string list"""
        cmds = parse_commands_from_line("F I=1,2,3")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.STRING_LIST
        assert len(stmt.parameters) == 3

    def test_argumentless_for(self):
        """F (infinite loop) parses"""
        cmds = parse_commands_from_line("F")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS


@pytest.mark.asg
class TestParseForCommandToAsg:
    """Test converting textX ForCommand to MForStatement ASG via analyze_command."""

    def test_bounded_for_asg(self):
        """Bounded FOR creates MForStatement with parameters."""
        fors = extract_for_commands("F I=1:2:10")
        assert len(fors) == 1
        stmt = analyze_command(fors[0])

        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1

        param = stmt.parameters[0]
        assert param.param_type == ForParamType.RANGE
        assert param.start.value == 1
        assert param.step.value == 2
        assert param.end.value == 10

    def test_string_list_for_asg(self):
        """String list FOR creates MForStatement with VALUE params."""
        fors = extract_for_commands('F I="A","B","C"')
        assert len(fors) == 1
        stmt = analyze_command(fors[0])

        assert len(stmt.parameters) == 3
        for p in stmt.parameters:
            assert p.param_type == ForParamType.VALUE

    def test_open_ended_for_asg(self):
        """Open-ended FOR creates MForStatement with OPEN_RANGE param."""
        fors = extract_for_commands("F I=1:1")
        assert len(fors) == 1
        stmt = analyze_command(fors[0])

        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.parameters[0].param_type == ForParamType.OPEN_RANGE
