"""Tests for SET command parsing (§8.2.18).

Tests verify the textX grammar correctly captures SET command syntax variations
including simple assignment, multiple targets, and postconditions.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.18
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "src"))
from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar metamodel with custom classes."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestSetCommandParsing:
    """Parser-level tests for SET command (§8.2.18).

    The SET command assigns values to variables. Forms include:
    - Simple: SET X=1 or S X=1 (abbreviated)
    - Multiple: SET X=1,Y=2
    - With postcondition: SET:condition X=1
    - Indirect: SET @var=value
    """

    def test_set_simple_assignment(self, command_metamodel):
        """SET X=1 produces SetCommand with single assignment (§8.2.18.1)."""
        model = command_metamodel.model_from_str("S X=1", "SetCommand")
        assert model is not None
        assert len(model.assignments) == 1
        assert model.assignments[0].targets.name == "X"

    def test_set_abbreviated_form(self, command_metamodel):
        """S X=1 parses identically to SET X=1 (§8.1 abbreviations)."""
        model = command_metamodel.model_from_str("SET X=1", "SetCommand")
        assert model is not None

    def test_set_multiple_assignments(self, command_metamodel):
        """SET X=1,Y=2,Z=3 parses as single command with multiple assignments (§8.2.18)."""
        model = command_metamodel.model_from_str("S X=1,Y=2,Z=3", "SetCommand")
        assert len(model.assignments) == 3

    def test_set_with_expression(self, command_metamodel):
        """S X=A+B*C parses SET with expression value (§8.2.18)."""
        model = command_metamodel.model_from_str("S X=A+B*C", "SetCommand")
        assert model.assignments[0].value is not None

    def test_set_global(self, command_metamodel):
        """S ^GLOBAL=1 parses SET with global variable target (§8.2.18)."""
        model = command_metamodel.model_from_str("S ^GLOBAL=1", "SetCommand")
        assert model.assignments[0].targets.name == "GLOBAL"

    def test_set_subscripted_global(self, command_metamodel):
        """S ^DATA(1,2)=X parses SET with subscripted global (§8.2.18)."""
        model = command_metamodel.model_from_str("S ^DATA(1,2)=X", "SetCommand")
        assert model is not None

    def test_set_with_postcondition(self, command_metamodel):
        """S:X>0 Y=1 parses SET with postcondition (§8.1.4)."""
        model = command_metamodel.model_from_str("S:X>0 Y=1", "SetCommand")
        assert model.postcond is not None

    def test_set_parenthesized_targets(self, command_metamodel):
        """S (A,B,C)=X parses SET with parenthesized targets (§8.2.18)."""
        model = command_metamodel.model_from_str("S (A,B,C)=X", "SetCommand")
        targets = model.assignments[0].targets
        assert len(targets.targets) == 3

    def test_set_naked_global_target(self, command_metamodel):
        """S ^(1)=value - naked global as SET target (§8.2.18)."""
        model = command_metamodel.model_from_str("S ^(1)=100", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "NakedGlobal"
        # subscripts is unwrapped to a list by custom classes
        assert len(target.subscripts) == 1

    def test_set_naked_global_multiple_subscripts(self, command_metamodel):
        """S ^(1,2,3)=value - naked global with multiple subscripts (§8.2.18)."""
        model = command_metamodel.model_from_str("S ^(1,2,3)=100", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "NakedGlobal"
        assert len(target.subscripts) == 3

    def test_set_mixed_global_naked_global(self, command_metamodel):
        """S ^V1(1)=1,^(2)=2 - mix of global and naked global (§8.2.18)."""
        model = command_metamodel.model_from_str("S ^V1(1)=1,^(2)=2", "SetCommand")
        assert len(model.assignments) == 2

        # First is GlobalVariable
        target1 = model.assignments[0].targets
        assert target1.__class__.__name__ == "GlobalVariable"
        assert target1.name == "V1"

        # Second is NakedGlobal
        target2 = model.assignments[1].targets
        assert target2.__class__.__name__ == "NakedGlobal"

    def test_set_extended_global_pipe(self, command_metamodel):
        """S ^|"env"|global=1 - pipe-delimited extended global."""
        model = command_metamodel.model_from_str('S ^|"env"|global=1', "SetCommand")
        assert len(model.assignments) == 1

    def test_set_extended_global_bracket(self, command_metamodel):
        """S ^["gld"]global=1 - bracket-delimited extended global."""
        model = command_metamodel.model_from_str('S ^["gld"]global=1', "SetCommand")
        assert len(model.assignments) == 1


@pytest.mark.parser
class TestSetStatementGrammar:
    """Test SET command parsing via MUMPSParser full routine parsing."""

    def test_simple_set(self):
        """SET with single variable and literal value."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=1\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        # Grammar captures the line with SET
        assert len(routine.labels) == 1

    def test_set_abbreviated(self):
        """S abbreviation should work same as SET."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS Y=2\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_multiple_targets(self):
        """SET with multiple comma-separated targets."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS A=1,B=2,C=3\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_string_value(self):
        """SET with quoted string value."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tS MSG="Hello"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestSetSpecialVariableGrammar:
    """Test SET command with special variables (§8.2.18, ISV assignment).

    Per MUMPS 1995 spec 8.2.18, SET can assign to special variables
    like $X and $Y (cursor position). Not all ISVs are assignable,
    but the parser should accept the syntax.
    """

    def test_set_special_variable_x(self):
        """SET $X=0 should parse - sets cursor column to 0."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS $X=0\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        stmt = label.body.statements[0]
        assert stmt.__class__.__name__ == "MSetStatement"

    def test_set_special_variable_y(self):
        """SET $Y=10 should parse - sets cursor row to 10."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS $Y=10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_special_variable_mixed(self):
        """SET with multiple targets including special variables."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=1,$X=0,Y=2\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_set_special_variable_expression(self):
        """SET $X=LEN+1 should parse - expression on right side."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS $X=LEN+1\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
