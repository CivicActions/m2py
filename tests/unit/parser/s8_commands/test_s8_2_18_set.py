"""Tests for SET command parsing (§8.2.18).

Tests verify the textX grammar correctly captures SET command syntax variations
including simple assignment, multiple targets, and postconditions.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.18

Migrated from:
- tests/unit/test_command_grammar.py::TestSetCommand
- tests/unit/test_grammar.py::TestSetStatementGrammar
- tests/unit/test_grammar.py::TestSetSpecialVariableGrammar
- tests/unit/test_line_parser.py::TestParseSetCommand
"""

import pytest

from m2py.asg import MRoutine
from m2py.asg.expressions import MGlobal
from m2py.analysis import analyze_command
from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line


@pytest.mark.parser
class TestSetCommandParsing:
    """Parser-level tests for SET command (§8.2.18).

    The SET command assigns values to variables. Forms include:
    - Simple: SET X=1 or S X=1 (abbreviated)
    - Multiple: SET X=1,Y=2
    - With postcondition: SET:condition X=1
    - Indirect: SET @var=value

    Migrated from legacy test_command_grammar.py::TestSetCommand
    """

    def test_simple_set(self, command_metamodel):
        """SET X=1 produces SetCommand with single assignment (§8.2.18)."""
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        assert model is not None
        assert len(model.assignments) == 1
        assert model.assignments[0].targets.name == "X"

    def test_set_full_keyword(self, command_metamodel):
        """SET with full keyword (§8.1 abbreviations)."""
        model = command_metamodel.model_from_str("SET X=1", "SetCommand")
        assert model is not None

    def test_set_multiple_assignments(self, command_metamodel):
        """S X=1,Y=2,Z=3 - multiple assignments in single command (§8.2.18)."""
        model = command_metamodel.model_from_str("S X=1,Y=2,Z=3", "SetCommand")
        assert len(model.assignments) == 3

    def test_set_with_expression(self, command_metamodel):
        """S X=A+B*C - expression value (§8.2.18)."""
        model = command_metamodel.model_from_str("S X=A+B*C", "SetCommand")
        assert model.assignments[0].value is not None

    def test_set_global(self, command_metamodel):
        """S ^GLOBAL=1 - global variable target (§8.2.18)."""
        model = command_metamodel.model_from_str("S ^GLOBAL=1", "SetCommand")
        assert model.assignments[0].targets.name == "GLOBAL"

    def test_set_subscripted_global(self, command_metamodel):
        """S ^DATA(1,2)=X - subscripted global (§8.2.18)."""
        model = command_metamodel.model_from_str("S ^DATA(1,2)=X", "SetCommand")
        assert model is not None

    def test_set_with_postcondition(self, command_metamodel):
        """S:X>0 Y=1 - command-level postcondition (§8.1)."""
        model = command_metamodel.model_from_str("S:X>0 Y=1", "SetCommand")
        assert model.postcond is not None

    def test_set_parenthesized_targets(self, command_metamodel):
        """S (A,B,C)=X - parenthesized multiple targets (§8.2.18)."""
        model = command_metamodel.model_from_str("S (A,B,C)=X", "SetCommand")
        targets = model.assignments[0].targets
        assert len(targets.targets) == 3

    def test_set_naked_global_target(self, command_metamodel):
        """S ^(1)=value - naked global as SET target (T526 fix)."""
        model = command_metamodel.model_from_str("S ^(1)=100", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "NakedGlobal"
        assert len(target.subscripts) == 1

    def test_set_naked_global_multiple_subscripts(self, command_metamodel):
        """S ^(1,2,3)=value - naked global with multiple subscripts (T526 fix)."""
        model = command_metamodel.model_from_str("S ^(1,2,3)=100", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "NakedGlobal"
        assert len(target.subscripts) == 3

    def test_set_mixed_global_naked_global(self, command_metamodel):
        """S ^V1(1)=1,^(2)=2 - mix of global and naked global (T526 fix)."""
        model = command_metamodel.model_from_str("S ^V1(1)=1,^(2)=2", "SetCommand")
        assert len(model.assignments) == 2

        # First is GlobalVariable
        target1 = model.assignments[0].targets
        assert target1.__class__.__name__ == "GlobalVariable"
        assert target1.name == "V1"

        # Second is NakedGlobal
        target2 = model.assignments[1].targets
        assert target2.__class__.__name__ == "NakedGlobal"


@pytest.mark.parser
class TestSetStatementGrammar:
    """Test SET command parsing full-routine acceptance (§8.2.18).

    Migrated from: tests/unit/test_grammar.py::TestSetStatementGrammar
    """

    def test_simple_set(self):
        """SET with single variable and literal value (§8.2.18)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=1\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        assert len(routine.labels) == 1

    def test_set_abbreviated(self):
        """S abbreviation should work same as SET (§8.2.18)."""
        parser = MUMPSParser()
        source = "LABEL\tS Y=2\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_multiple_targets(self):
        """SET with multiple comma-separated targets (§8.2.18)."""
        parser = MUMPSParser()
        source = "LABEL\tS A=1,B=2,C=3\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_string_value(self):
        """SET with quoted string value (§8.2.18)."""
        parser = MUMPSParser()
        source = 'LABEL\tS MSG="Hello"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestSetSpecialVariableGrammar:
    """Test SET command with special variables (§8.2.18).

    Per MUMPS 1995 spec 8.2.18, SET can assign to special variables
    like $X and $Y (cursor position). Not all ISVs are assignable,
    but the parser should accept the syntax.

    Migrated from: tests/unit/test_grammar.py::TestSetSpecialVariableGrammar
    """

    def test_set_special_variable_x(self):
        """SET $X=0 should parse - sets cursor column to 0 (§8.2.18)."""
        parser = MUMPSParser()
        source = "LABEL\tS $X=0\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        stmt = label.body.statements[0]
        assert stmt.__class__.__name__ == "MSetStatement"

    def test_set_special_variable_y(self):
        """SET $Y=10 should parse - sets cursor row to 10 (§8.2.18)."""
        parser = MUMPSParser()
        source = "LABEL\tS $Y=10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_special_variable_mixed(self):
        """SET with multiple targets including special variables (§8.2.18)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=1,$X=0,Y=2\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_special_variable_expression(self):
        """SET $X=LEN+1 should parse - expression on right side (§8.2.18)."""
        parser = MUMPSParser()
        source = "LABEL\tS $X=LEN+1\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestParseSetCommand:
    """Test SET command parsing to full-fidelity ASG.

    Migrated from: tests/unit/test_line_parser.py::TestParseSetCommand
    """

    def test_simple_set(self):
        """S X=1 creates MSetStatement."""
        cmds = parse_commands_from_line("S X=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"

    def test_set_multiple(self):
        """S X=1,Y=2 creates two assignments."""
        cmds = parse_commands_from_line("S X=1,Y=2")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.assignments) == 2

    def test_set_global(self):
        """S ^GLOBAL=1 parses global variable."""
        cmds = parse_commands_from_line("S ^GLOBAL=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert isinstance(stmt.assignments[0].target, MGlobal)
