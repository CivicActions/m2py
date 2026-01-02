"""Tests for Special Variables parsing (§7.1.7).

Tests verify the textX grammar correctly captures special variable syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.7
Migrated from:
- tests/unit/test_expression_grammar.py::TestSpecialVariables
- tests/unit/test_grammar.py::TestSpecialVariableGrammar
- tests/unit/test_grammar.py::TestIORefSpecialVariableGrammar
"""

import pytest

from m2py.asg import MRoutine, MSpecialVariable
from m2py.parser import MUMPSParser


@pytest.mark.parser
class TestSpecialVariablesParsing:
    """Parser-level tests for Special Variables (§7.1.7).

    Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
    """

    def test_test_variable(self, parse_expression):
        """$TEST parses correctly (§7.1.7).

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$TEST")
        assert model is not None

    def test_horolog_variable(self, parse_expression):
        """$HOROLOG parses correctly (§7.1.7).

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$HOROLOG")
        assert model is not None

    def test_x_variable(self, parse_expression):
        """$X parses correctly (§7.1.7).

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$X")
        assert model is not None

    def test_abbreviated_horolog(self, parse_expression):
        """$H parses as abbreviated $HOROLOG (§7.1.7).

        Single-letter forms allowed per MUMPS spec.

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$H")
        assert model is not None
        # Navigate: Expr -> left (UnaryExpr) -> operand (PrimaryExpr)
        # PrimaryExpr should be SpecialVariable
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "H"

    def test_abbreviated_storage(self, parse_expression):
        """$S parses as abbreviated $STORAGE (§7.1.7).

        Single-letter forms allowed per MUMPS spec.

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$S")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "S"

    def test_abbreviated_test(self, parse_expression):
        """$T parses as abbreviated $TEST (§7.1.7).

        Single-letter forms allowed per MUMPS spec.

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$T")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "T"

    def test_abbreviated_job(self, parse_expression):
        """$J parses as abbreviated $JOB (§7.1.7).

        Single-letter forms allowed per MUMPS spec.

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$J")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "J"

    def test_abbreviated_io(self, parse_expression):
        """$I parses as abbreviated $IO (§7.1.7).

        Single-letter forms allowed per MUMPS spec.

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$I")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "I"

    def test_abbreviated_device(self, parse_expression):
        """$D parses as abbreviated $DEVICE (§7.1.7).

        Single-letter forms allowed per MUMPS spec.

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$D")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "D"

    def test_device_variable(self, parse_expression):
        """$DEVICE parses correctly (§7.1.7)."""
        model = parse_expression("$DEVICE")
        assert model is not None

    def test_ecode_variable(self, parse_expression):
        """$ECODE parses correctly (§7.1.7)."""
        model = parse_expression("$ECODE")
        assert model is not None

    def test_estack_variable(self, parse_expression):
        """$ESTACK parses correctly (§7.1.7)."""
        model = parse_expression("$ESTACK")
        assert model is not None

    def test_etrap_variable(self, parse_expression):
        """$ETRAP parses correctly (§7.1.7)."""
        model = parse_expression("$ETRAP")
        assert model is not None

    def test_io_variable(self, parse_expression):
        """$IO parses correctly (§7.1.7)."""
        model = parse_expression("$IO")
        assert model is not None

    def test_job_variable(self, parse_expression):
        """$JOB parses correctly (§7.1.7)."""
        model = parse_expression("$JOB")
        assert model is not None

    def test_key_variable(self, parse_expression):
        """$KEY parses correctly (§7.1.7)."""
        model = parse_expression("$KEY")
        assert model is not None

    def test_principal_variable(self, parse_expression):
        """$PRINCIPAL parses correctly (§7.1.7)."""
        model = parse_expression("$PRINCIPAL")
        assert model is not None

    def test_quit_variable(self, parse_expression):
        """$QUIT parses correctly (§7.1.7)."""
        model = parse_expression("$QUIT")
        assert model is not None

    def test_reference_variable(self, parse_expression):
        """$REFERENCE parses correctly (§7.1.7)."""
        model = parse_expression("$REFERENCE")
        assert model is not None

    def test_stack_variable(self, parse_expression):
        """$STACK parses correctly (§7.1.7)."""
        model = parse_expression("$STACK")
        assert model is not None

    def test_storage_variable(self, parse_expression):
        """$STORAGE parses correctly (§7.1.7)."""
        model = parse_expression("$STORAGE")
        assert model is not None

    def test_system_variable(self, parse_expression):
        """$SYSTEM parses correctly (§7.1.7)."""
        model = parse_expression("$SYSTEM")
        assert model is not None

    def test_tlevel_variable(self, parse_expression):
        """$TLEVEL parses correctly (§7.1.7)."""
        model = parse_expression("$TLEVEL")
        assert model is not None

    def test_trestart_variable(self, parse_expression):
        """$TRESTART parses correctly (§7.1.7)."""
        model = parse_expression("$TRESTART")
        assert model is not None

    def test_y_variable(self, parse_expression):
        """$Y parses correctly (§7.1.7)."""
        model = parse_expression("$Y")
        assert model is not None


@pytest.mark.parser
class TestSpecialVariableGrammar:
    """Test special variable parsing full-routine acceptance (§7.1.7).

    Migrated from: tests/unit/test_grammar.py::TestSpecialVariableGrammar
    """

    def test_test_variable(self):
        """$TEST special variable should parse (§7.1.7)."""
        parser = MUMPSParser()
        source = 'LABEL\tI $TEST W "true"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_test_abbreviated(self):
        """$T abbreviation should parse (§7.1.7)."""
        parser = MUMPSParser()
        source = 'LABEL\tI $T W "true"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_horolog_variable(self):
        """$HOROLOG should parse (§7.1.7)."""
        parser = MUMPSParser()
        source = "LABEL\tS TIME=$HOROLOG\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_job_variable(self):
        """$JOB should parse (§7.1.7)."""
        parser = MUMPSParser()
        source = "LABEL\tS PID=$JOB\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestIORefSpecialVariableGrammar:
    """Test $IOREFERENCE and related long ISV names (§7.1.7).

    Per MUMPS 1995 spec 7.1.4.10.7, $IOREFERENCE tracks the current
    I/O device. The grammar must match the full name, not just $IO.

    Migrated from: tests/unit/test_grammar.py::TestIORefSpecialVariableGrammar
    """

    def test_ioreference_full(self):
        """$IOREFERENCE should parse as single special variable (§7.1.7)."""
        parser = MUMPSParser()
        source = "LABEL\tW $IOREFERENCE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        # Should have exactly one WRITE argument
        assert len(stmt.arguments) == 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MSpecialVariable)
        assert arg.name.upper() == "IOREFERENCE"

    def test_ioreference_abbreviated(self):
        """$IOR should parse as IOREFERENCE (§7.1.7)."""
        parser = MUMPSParser()
        source = "LABEL\tW $IOR\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert len(stmt.arguments) == 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MSpecialVariable)
        # IOR is the abbreviated form
        assert arg.name.upper() == "IOR"

    def test_pioreference_full(self):
        """$PIOREFERENCE should parse as single special variable (§7.1.7)."""
        parser = MUMPSParser()
        source = "LABEL\tW $PIOREFERENCE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert len(stmt.arguments) == 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MSpecialVariable)
        assert arg.name.upper() == "PIOREFERENCE"

    def test_io_still_works(self):
        """$IO should still parse correctly (§7.1.7)."""
        parser = MUMPSParser()
        source = "LABEL\tW $IO\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert len(stmt.arguments) == 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MSpecialVariable)
        assert arg.name.upper() == "IO"
