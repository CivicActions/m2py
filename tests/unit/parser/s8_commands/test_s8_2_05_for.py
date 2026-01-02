"""Tests for FOR command parsing (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5

Migrated from:
- tests/unit/test_command_grammar.py::TestForCommand
- tests/unit/test_grammar.py::TestBoundedForGrammar
- tests/unit/test_grammar.py::TestStringListForGrammar
- tests/unit/test_grammar.py::TestOpenEndedForGrammar
- tests/unit/test_grammar.py::TestMixedForGrammar
- tests/unit/test_grammar.py::TestArgumentlessForGrammar
- tests/unit/test_line_parser.py::TestParseForCommand
- tests/unit/test_line_parser.py::TestExtractForCommands
- tests/unit/test_line_parser.py::TestClassifyForFromTextx
- tests/unit/test_line_parser.py::TestParseForCommandToAsg
- tests/unit/test_line_parser.py::TestDetectQuitAfterFor
"""

import pytest

from m2py.asg import MRoutine
from m2py.asg.enums import ForLoopType, ForParamType
from m2py.analysis import analyze_command
from m2py.parser import MUMPSParser
from m2py.parser.line_parser import (
    parse_commands_from_line,
    extract_for_commands,
    classify_for_command,
    detect_quit_after_for,
)


@pytest.mark.parser
class TestForCommandParsing:
    """Parser-level tests for FOR command (§8.2.5)."""

    def test_simple_for(self, command_metamodel):
        """F I=1:1:10 - bounded loop (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=1:1:10", "ForCommand")
        assert model.var.name == "I"
        assert len(model.params) == 1

    def test_for_step_only(self, command_metamodel):
        """F I=1:1 - open-ended loop with step (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=1:1", "ForCommand")
        assert model.var.name == "I"

    def test_for_values(self, command_metamodel):
        """F I=1,2,3 - value list (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=1,2,3", "ForCommand")
        assert len(model.params) == 3

    def test_argumentless_for(self, command_metamodel):
        """F - argumentless infinite loop (§8.2.5)."""
        model = command_metamodel.model_from_str("F", "ForCommand")
        assert model.var is None

    def test_subscripted_for_var(self, command_metamodel):
        """F J(1,2,3)=1:1:3 - subscripted loop variable (§8.2.5, BUG-003)."""
        model = command_metamodel.model_from_str("F J(1,2,3)=1:1:3", "ForCommand")
        assert model.var.name == "J"
        assert len(model.var.subscripts) == 3
        assert len(model.params) == 1

    def test_single_subscripted_for_var(self, command_metamodel):
        """F ARR(I)=1:1:10 - single subscript on loop variable (§8.2.5)."""
        model = command_metamodel.model_from_str("F ARR(I)=1:1:10", "ForCommand")
        assert model.var.name == "ARR"
        assert len(model.var.subscripts) == 1


@pytest.mark.parser
class TestBoundedForGrammar:
    """Test bounded FOR command parsing (§8.2.5).

    Migrated from: tests/unit/test_grammar.py::TestBoundedForGrammar
    """

    def test_bounded_for_simple(self):
        """FOR var=start:step:end basic form (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1:1:10 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_for_abbreviated(self):
        """F abbreviation should work same as FOR (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF J=0:1:5 W J\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_bounded_for_expression(self):
        """FOR with expressions in bounds (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF K=N:1:M W K\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_bounded_for_negative_step(self):
        """FOR with negative step (countdown) (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF L=10:-1:1 W L\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestStringListForGrammar:
    """Test string-list FOR command parsing (§8.2.5).

    Migrated from: tests/unit/test_grammar.py::TestStringListForGrammar
    """

    def test_string_list_for_simple(self):
        """FOR var=\"A\",\"B\",\"C\" string list form (§8.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tF I="A","B","C" W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_string_list_for_numbers(self):
        """FOR with numeric values as list: F I=1,3,5 W I (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1,3,5,7 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_string_list_for_mixed_values(self):
        """FOR with mixed string and numeric values: F I=1,\"ABC\",3 (§8.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tF I=1,3,4,5.5,7,-1,"ABC",-2.3 W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_string_list_for_with_expressions(self):
        """FOR with expression values: F I=$D(X),$L(Y) (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=$D(X),$L(Y),Z+1 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestOpenEndedForGrammar:
    """Test open-ended FOR command parsing (§8.2.5).

    Migrated from: tests/unit/test_grammar.py::TestOpenEndedForGrammar
    """

    def test_open_ended_for_simple(self):
        """FOR var=start:step without end (F I=1:1) (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1:1 W I Q:I>10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_ended_for_decimal_step(self):
        """FOR with decimal step: F I=.1:-.02 (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=.1:-.02 W I Q:I<0\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_ended_for_expression_step(self):
        """FOR with expression as step: F I=X:Y (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=X:Y S X=X+1 Q:I>100\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestMixedForGrammar:
    """Test mixed FOR command parsing (§8.2.5).

    Migrated from: tests/unit/test_grammar.py::TestMixedForGrammar
    """

    def test_mixed_for_values_and_range(self):
        """FOR with mixed values and range: F I=\"A\",1:1:3 (§8.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tF I="A",1:1:3 W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_mixed_for_complex(self):
        """FOR with complex mixture: F I=-10.1,3*I,\"ABC\",2:-0.5:1 (§8.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tF I=-10.1,3*I,"ABC",2:-0.5:1,"1E0",5:2.5 W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_mixed_for_ranges_only(self):
        """FOR with multiple ranges: F I=1:1:3,5:2:10 (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1.5:0.1:2.1,1:-0.3:-1 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_mixed_for_open_ranges(self):
        """FOR with open and closed ranges: F I=.1:-.02,1:2 (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=.1:-.02,1:2 W I Q:I<0\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestArgumentlessForGrammar:
    """Test argumentless FOR command parsing (§8.2.5).

    Migrated from: tests/unit/test_grammar.py::TestArgumentlessForGrammar
    """

    def test_argumentless_for(self):
        """FOR without arguments (infinite loop): F  W X Q:Y (§8.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tF  W "loop" Q:X>10\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_argumentless_for_with_read(self):
        """Argumentless FOR with READ command: F  R X Q:X=\"\" (§8.2.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tF  R X Q:X=""\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_argumentless_for_with_kill(self):
        """Argumentless FOR with KILL in body (§8.2.5)."""
        parser = MUMPSParser()
        source = "LABEL\tF  K I S I=1 Q\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestParseForCommand:
    """Test FOR command parsing to full-fidelity ASG.

    Migrated from: tests/unit/test_line_parser.py::TestParseForCommand
    """

    def test_bounded_for(self):
        """F I=1:1:10 parses as bounded."""
        cmds = parse_commands_from_line("F I=1:1:10")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].param_type == ForParamType.RANGE

    def test_open_ended_for(self):
        """F I=1:1 parses as open-ended."""
        cmds = parse_commands_from_line("F I=1:1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.parameters[0].param_type == ForParamType.OPEN_RANGE

    def test_value_list_for(self):
        """F I=1,2,3 parses as string list."""
        cmds = parse_commands_from_line("F I=1,2,3")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.STRING_LIST
        assert len(stmt.parameters) == 3

    def test_argumentless_for(self):
        """F (infinite loop) parses."""
        cmds = parse_commands_from_line("F")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS


@pytest.mark.parser
class TestExtractForCommands:
    """Test extracting FOR commands from line content.

    Migrated from: tests/unit/test_line_parser.py::TestExtractForCommands
    """

    def test_single_for(self):
        """Extract FOR from line with one FOR."""
        fors = extract_for_commands("F I=1:1:10 W I")
        assert len(fors) == 1
        assert fors[0].__class__.__name__ == "ForCommand"
        # fors[0].var is now a LocalVariable object
        assert fors[0].var.name == "I"

    def test_no_for(self):
        """No FOR returns empty list."""
        fors = extract_for_commands("S X=1 W X")
        assert fors == []

    def test_multiple_for(self):
        """Multiple FORs (rare but possible in MUMPS)."""
        # Note: In MUMPS, multiple FORs on a line are sequential
        fors = extract_for_commands("F I=1:1:5 S X=I F J=1:1:3 W J")
        assert len(fors) == 2

    def test_for_in_string_not_extracted(self):
        """FOR in string literal shouldn't be extracted."""
        # The string "FOR" shouldn't match
        fors = extract_for_commands('W "FOR I=1:1:10"')
        assert fors == []


@pytest.mark.parser
class TestClassifyForFromTextx:
    """Test FOR loop classification from textX models.

    Migrated from: tests/unit/test_line_parser.py::TestClassifyForFromTextx
    """

    def test_bounded_for(self):
        """Bounded FOR I=1:1:10 classification."""
        fors = extract_for_commands("F I=1:1:10")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.BOUNDED
        assert loop_var == "I"

    def test_open_ended_for(self):
        """Open-ended FOR I=1:1 classification."""
        fors = extract_for_commands("F I=1:1")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.OPEN_ENDED
        assert loop_var == "I"

    def test_string_list_for(self):
        """String list FOR I=1,2,3 classification."""
        fors = extract_for_commands("F I=1,2,3")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.STRING_LIST
        assert loop_var == "I"

    def test_argumentless_for(self):
        """Argumentless FOR classification."""
        fors = extract_for_commands("F")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert loop_var == ""

    def test_mixed_for(self):
        """Mixed FOR I="A",1:1:3 classification."""
        fors = extract_for_commands('F I="A",1:1:3')
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.MIXED
        assert loop_var == "I"


@pytest.mark.parser
class TestParseForCommandToAsg:
    """Test converting textX ForCommand to MForStatement ASG via analyze_command.

    Migrated from: tests/unit/test_line_parser.py::TestParseForCommandToAsg
    """

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


@pytest.mark.parser
class TestDetectQuitAfterFor:
    """Test QUIT detection after FOR command.

    Migrated from: tests/unit/test_line_parser.py::TestDetectQuitAfterFor
    """

    def test_quit_after_for(self):
        """Detect QUIT after FOR on same line."""
        result = detect_quit_after_for("F I=1:1:10 W I Q")
        assert result is True

    def test_no_quit(self):
        """No QUIT returns False."""
        result = detect_quit_after_for("F I=1:1:10 W I")
        assert result is False

    def test_quit_without_for(self):
        """QUIT without FOR returns False."""
        result = detect_quit_after_for("S X=1 Q")
        assert result is False

    def test_quit_before_for(self):
        """QUIT before FOR doesn't count."""
        result = detect_quit_after_for("Q F I=1:1:10 W I")
        assert result is False

    def test_postconditioned_quit(self):
        """Postconditioned QUIT still detected."""
        result = detect_quit_after_for("F I=1:1:10 W I Q:I>5")
        assert result is True


# =============================================================================
# Phase 12: Control Flow Body Population Tests
# =============================================================================


@pytest.mark.parser
class TestForBodyPopulation:
    """T347-T353: Tests for FOR body population.

    These tests verify that FOR block bodies are properly populated
    with following commands.

    Migrated from: tests/unit/test_parser.py::TestControlFlowBodyPopulation
    """

    def test_for_body_single_command(self):
        """T347: FOR captures single following command in body."""
        from m2py.asg.statements import MForStatement, MSetStatement

        parser = MUMPSParser()
        source = "TEST\tF I=1:1:3 S X=I\n"
        routine = parser.parse(source)

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1
        assert isinstance(for_stmt.body.statements[0], MSetStatement)

    def test_for_body_multiple_commands(self):
        """T347: FOR captures multiple following commands in body."""
        from m2py.asg.statements import MForStatement, MSetStatement, MWriteStatement

        parser = MUMPSParser()
        source = "TEST\tF I=1:1:3 S X=I W X\n"
        routine = parser.parse(source)

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 2
        assert isinstance(for_stmt.body.statements[0], MSetStatement)
        assert isinstance(for_stmt.body.statements[1], MWriteStatement)

    def test_for_nested_for(self):
        """T353: Nested FOR loops are properly structured."""
        from m2py.asg.statements import MForStatement, MSetStatement

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

    def test_for_with_nested_if(self):
        """T354: FOR with nested IF is properly structured."""
        from m2py.asg.statements import MForStatement, MIfStatement, MSetStatement

        parser = MUMPSParser()
        source = "TEST\tF I=1:1:10 I I#2 S X=I\n"
        routine = parser.parse(source)

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1

        if_stmt = for_stmt.body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)
