"""Tests for FOR command parsing (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
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
class TestForCommandParsing:
    """Parser-level tests for FOR command (§8.2.5)."""

    def test_for_bounded(self, command_metamodel):
        """F I=1:1:10 parses bounded FOR loop (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=1:1:10", "ForCommand")
        assert model.var.name == "I"
        assert len(model.params) == 1

    def test_for_string_list(self, command_metamodel):
        """F I=1,2,3 parses FOR with value list (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=1,2,3", "ForCommand")
        assert len(model.params) == 3

    def test_for_open_ended(self, command_metamodel):
        """F I=1:1 parses FOR infinite loop with step (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=1:1", "ForCommand")
        assert model.var.name == "I"

    def test_for_argumentless(self, command_metamodel):
        """F parses FOR infinite loop (§8.2.5)."""
        model = command_metamodel.model_from_str("F", "ForCommand")
        assert model.var is None

    def test_for_mixed_forms(self, command_metamodel):
        """FOR i=1:1:5,10,20:5:50 mixed forms parse correctly (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=1:1:5,10,20:5:50", "ForCommand")
        assert model.var.name == "I"
        assert len(model.params) == 3

    def test_for_negative_increment(self, command_metamodel):
        """FOR i=10:-1:1 negative increment parses correctly (§8.2.5)."""
        model = command_metamodel.model_from_str("F L=10:-1:1", "ForCommand")
        assert model.var.name == "L"
        assert len(model.params) == 1

    def test_for_decimal_increment(self, command_metamodel):
        """FOR i=0:.5:5 decimal increment parses correctly (§8.2.5)."""
        model = command_metamodel.model_from_str("F I=.1:-.02", "ForCommand")
        assert model.var.name == "I"

    def test_for_subscripted_var(self, command_metamodel):
        """F J(1,2,3)=1:1:3 parses FOR with subscripted loop variable (§8.2.5)."""
        model = command_metamodel.model_from_str("F J(1,2,3)=1:1:3", "ForCommand")
        assert model.var.name == "J"
        assert len(model.var.subscripts) == 3
        assert len(model.params) == 1

    def test_for_single_subscripted_var(self, command_metamodel):
        """F ARR(I)=1:1:10 parses FOR with single subscript on loop variable (§8.2.5)."""
        model = command_metamodel.model_from_str("F ARR(I)=1:1:10", "ForCommand")
        assert model.var.name == "ARR"
        assert len(model.var.subscripts) == 1


@pytest.mark.parser
class TestBoundedForGrammar:
    """Test bounded FOR command parsing via MUMPSParser."""

    def test_bounded_for_simple(self):
        """FOR var=start:step:end basic form."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=1:1:10 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_for_abbreviated(self):
        """F abbreviation should work same as FOR."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF J=0:1:5 W J\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_bounded_for_expression(self):
        """FOR with expressions in bounds."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF K=N:1:M W K\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_bounded_for_negative_step(self):
        """FOR with negative step (countdown)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF L=10:-1:1 W L\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestStringListForGrammar:
    """Test string-list FOR command parsing."""

    def test_string_list_for_simple(self):
        """FOR var="A","B","C" string list form."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tF I="A","B","C" W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_string_list_for_numbers(self):
        """FOR with numeric values as list: F I=1,3,5 W I."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=1,3,5,7 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_string_list_for_mixed_values(self):
        """FOR with mixed string and numeric values: F I=1,"ABC",3."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tF I=1,3,4,5.5,7,-1,"ABC",-2.3 W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_string_list_for_with_expressions(self):
        """FOR with expression values: F I=$D(X),$L(Y)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=$D(X),$L(Y),Z+1 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestOpenEndedForGrammar:
    """Test open-ended FOR command parsing."""

    def test_open_ended_for_simple(self):
        """FOR var=start:step without end (F I=1:1)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=1:1 W I Q:I>10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_ended_for_decimal_step(self):
        """FOR with decimal step: F I=.1:-.02."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=.1:-.02 W I Q:I<0\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_ended_for_expression_step(self):
        """FOR with expression as step: F I=X:Y."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=X:Y S X=X+1 Q:I>100\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestMixedForGrammar:
    """Test mixed FOR command parsing."""

    def test_mixed_for_values_and_range(self):
        """FOR with mixed values and range: F I="A",1:1:3."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tF I="A",1:1:3 W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_mixed_for_complex(self):
        """FOR with complex mixture: F I=-10.1,3*I,"ABC",2:-0.5:1."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tF I=-10.1,3*I,"ABC",2:-0.5:1,"1E0",5:2.5 W I\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_mixed_for_ranges_only(self):
        """FOR with multiple ranges: F I=1:1:3,5:2:10."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=1.5:0.1:2.1,1:-0.3:-1 W I\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_mixed_for_open_ranges(self):
        """FOR with open and closed ranges: F I=.1:-.02,1:2."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF I=.1:-.02,1:2 W I Q:I<0\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestArgumentlessForGrammar:
    """Test argumentless FOR command parsing."""

    def test_argumentless_for(self):
        """FOR without arguments (infinite loop): F  W X Q:Y."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tF  W "loop" Q:X>10\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_argumentless_for_with_read(self):
        """Argumentless FOR with READ command: F  R X Q:X=""."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tF  R X Q:X=""\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_argumentless_for_with_kill(self):
        """Argumentless FOR with KILL in body."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tF  K I S I=1 Q\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
