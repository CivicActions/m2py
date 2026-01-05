"""Tests for READ command parsing (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17
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
class TestReadCommandParsing:
    """Parser-level tests for READ command (§8.2.17)."""

    def test_read_basic(self, command_metamodel):
        """R X parses READ with single target (§8.2.17)."""
        model = command_metamodel.model_from_str("R X", "ReadCommand")
        assert model is not None
        assert len(model.args) == 1

    def test_read_with_prompt(self, command_metamodel):
        """READ \"prompt\",X parses correctly (§8.2.17).

        Per MUMPS spec §8.2.17: strlit form causes output to current device.
        Prompt strings are commonly used before reading input.
        """
        model = command_metamodel.model_from_str('R "Enter: ",X', "ReadCommand")
        assert model is not None
        # Should have 2 args: the prompt string and the variable
        assert len(model.args) == 2
        # First arg should be the string literal prompt
        assert model.args[0].arg.__class__.__name__ == "StringLiteral"
        # Second arg should have a target variable
        assert model.args[1].arg.target is not None

    def test_read_fixed_length(self, command_metamodel):
        """R X#5 reads exactly 5 characters (§8.2.17)."""
        model = command_metamodel.model_from_str("R X#5", "ReadCommand")
        assert len(model.args) == 1
        # fixed_length should be in the ReadTargetWithTimeout
        assert model.args[0].arg.fixed_length is not None

    def test_read_with_timeout(self, command_metamodel):
        """R X:30 reads with 30 second timeout (§8.2.17)."""
        model = command_metamodel.model_from_str("R X:30", "ReadCommand")
        # New structure: ReadArg.arg = ReadTargetWithTimeout
        assert model.args[0].arg.timeout is not None

    def test_read_single_char(self, command_metamodel):
        """R *X reads single character (§8.2.17)."""
        model = command_metamodel.model_from_str("R *X", "ReadCommand")
        assert len(model.args) == 1

    def test_read_format_control(self, command_metamodel):
        """READ !,?10,# format controls parse correctly (§8.2.17).

        Per MUMPS spec §8.2.17: format forms cause output operations.
        ! = newline, ?n = tab to column n, # = form feed.
        These are output operations before/between read targets.
        """
        # Newline format control
        model = command_metamodel.model_from_str("R !", "ReadCommand")
        assert len(model.args) == 1

        # Tab to column format control
        model = command_metamodel.model_from_str("R ?10", "ReadCommand")
        assert len(model.args) == 1

        # Mixed format controls with variable
        model = command_metamodel.model_from_str("R !,?10,X", "ReadCommand")
        assert len(model.args) == 3

    def test_read_multiple_targets(self, command_metamodel):
        """R X,Y,Z reads multiple variables (§8.2.17)."""
        model = command_metamodel.model_from_str("R X,Y,Z", "ReadCommand")
        assert len(model.args) == 3

    def test_read_fixed_length_with_timeout(self, command_metamodel):
        """R X#5:10 reads fixed length with timeout (§8.2.17)."""
        model = command_metamodel.model_from_str("R X#5:10", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None
        assert model.args[0].arg.timeout is not None

    def test_read_fixed_length_negative(self, command_metamodel):
        """R X#-1 - fixed length with negative value parses (§8.2.17)."""
        model = command_metamodel.model_from_str("R X#-1", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None

    def test_read_fixed_length_variable(self, command_metamodel):
        """R X#N - fixed length with variable as length (§8.2.17)."""
        model = command_metamodel.model_from_str("R X#N", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None

    def test_read_fixed_length_expression(self, command_metamodel):
        """R X#A+B - fixed length with expression as length (§8.2.17)."""
        model = command_metamodel.model_from_str("R X#A+B", "ReadCommand")
        assert len(model.args) == 1
        assert model.args[0].arg.fixed_length is not None


@pytest.mark.parser
class TestReadTargetsParsing:
    """Parser tests for READ target extensions (§8.2.17)."""

    def test_read_charread_with_indirection(self, command_metamodel):
        """R *@var - char read with indirection (§8.2.17)."""
        model = command_metamodel.model_from_str("R *@var", "ReadCommand")
        assert len(model.args) == 1

    def test_read_charread_with_name_indirection(self, command_metamodel):
        """R *@var@(2) - char read with name indirection subscript (§8.2.17)."""
        model = command_metamodel.model_from_str("R *@var@(2)", "ReadCommand")
        assert len(model.args) == 1

    def test_read_naked_global(self, command_metamodel):
        """R ^(\"naked\") - naked global read target (§8.2.17)."""
        model = command_metamodel.model_from_str('R ^("naked")', "ReadCommand")
        assert len(model.args) == 1
        target = model.args[0].arg.target
        assert target.__class__.__name__ == "NakedGlobal"

    def test_read_char_into_global(self, command_metamodel):
        """R *^VV(\"M\") - READ single char into global variable (§8.2.17)."""
        model = command_metamodel.model_from_str('R *^VV("M")', "ReadCommand")
        assert model is not None
        assert len(model.args) == 1
        # ReadArg.arg -> ReadTargetWithTimeout.target -> CharRead
        tat = model.args[0].arg  # ReadTargetWithTimeout
        target = tat.target  # CharRead
        assert target.__class__.__name__ == "CharRead"
        # The var inside CharRead is the actual GlobalVariable
        char_var = target.var
        assert char_var.__class__.__name__ == "GlobalVariable"
        assert char_var.name == "VV"


@pytest.mark.parser
class TestReadFormatControlGrammar:
    """Test READ command with format controls via MUMPSParser."""

    def test_read_variable_only(self):
        """R variable should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tR ans\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MReadStatement"

    def test_read_newline_only(self):
        """R ! (newline only) should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tR !\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MReadStatement"

    def test_read_tab_only(self):
        """R ?10 (column position only) should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tR ?10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MReadStatement"

    def test_read_format_then_variable(self):
        """R !,?10,ans should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tR !,?10,ans\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MReadStatement"

    def test_read_prompt_and_variable(self):
        """R "Prompt: ",ans should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tR "Prompt: ",ans\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1

    def test_read_complex_format(self):
        """R !,?10,"Prompt: ",ans,! should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tR !,?10,"Prompt: ",ans,!\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MReadStatement"

    def test_read_format_controls_as_asg_nodes(self):
        """READ format controls should be MFormatControl ASG nodes."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MFormatControl, FormatControlType, MReadTarget

        parser = MUMPSParser()
        source = 'LABEL\tR !!,"Prompt",ans\n'
        routine = parser.parse(source)

        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == "MReadStatement"

        # Should have 4 arguments: !, !, "Prompt", ans
        assert len(read_stmt.arguments) == 4

        # First two should be MFormatControl NEWLINE nodes
        assert isinstance(read_stmt.arguments[0], MFormatControl)
        assert read_stmt.arguments[0].control_type == FormatControlType.NEWLINE
        assert isinstance(read_stmt.arguments[1], MFormatControl)
        assert read_stmt.arguments[1].control_type == FormatControlType.NEWLINE

        # Third should be StringLiteral (prompt)
        assert read_stmt.arguments[2].__class__.__name__ == "StringLiteral"

        # Fourth should be MReadTarget wrapping the LocalVariable (target)
        assert isinstance(read_stmt.arguments[3], MReadTarget)
        assert read_stmt.arguments[3].variable.__class__.__name__ == "LocalVariable"
        assert read_stmt.arguments[3].variable.name == "ans"
        assert read_stmt.arguments[3].is_char_read is False
        assert read_stmt.arguments[3].timeout is None

    def test_read_with_timeout(self):
        """READ with timeout should preserve timeout in MReadTarget."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MReadTarget

        parser = MUMPSParser()
        source = "LABEL\tR X:10\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == "MReadStatement"
        assert len(read_stmt.arguments) == 1

        # Should be MReadTarget with timeout
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.variable.name == "X"
        assert target.is_char_read is False
        assert target.timeout is not None
        assert target.timeout.value == 10

    def test_read_char_read(self):
        """READ *VAR should set is_char_read=True in MReadTarget."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MReadTarget

        parser = MUMPSParser()
        source = "LABEL\tR *X\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == "MReadStatement"
        assert len(read_stmt.arguments) == 1

        # Should be MReadTarget with is_char_read=True
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.variable.name == "X"
        assert target.is_char_read is True
        assert target.timeout is None

    def test_read_char_read_with_timeout(self):
        """READ *VAR:timeout should preserve both flags."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MReadTarget

        parser = MUMPSParser()
        source = "LABEL\tR *X:0\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == "MReadStatement"
        assert len(read_stmt.arguments) == 1

        # Should be MReadTarget with is_char_read=True AND timeout
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.variable.name == "X"
        assert target.is_char_read is True
        assert target.timeout is not None
        assert target.timeout.value == 0

    def test_read_negative_timeout(self):
        """READ X:-1 should preserve negative timeout (V1READB1 tests)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MReadTarget

        parser = MUMPSParser()
        source = "LABEL\tR X:-1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == "MReadStatement"

        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.timeout is not None
        # Negative number is MUnaryOp('-', NumericLiteral(1))
        assert target.timeout.__class__.__name__ == "MUnaryOp"
        assert target.timeout.operator == "-"
        assert target.timeout.operand.value == 1

    def test_read_multiple_char_reads(self):
        """READ *A,*B,*C should handle multiple char reads (V1READA2 test 758)."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MReadTarget

        parser = MUMPSParser()
        source = "LABEL\tR *A,*B,*C\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == "MReadStatement"
        assert len(read_stmt.arguments) == 3

        for i, name in enumerate(["A", "B", "C"]):
            target = read_stmt.arguments[i]
            assert isinstance(target, MReadTarget)
            assert target.variable.name == name
            assert target.is_char_read is True
