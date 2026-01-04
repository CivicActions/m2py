"""Tests for Special Variables parsing (§7.1.7).

Tests verify the textX grammar correctly captures special variable syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.7
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture(scope="module")
def expr_metamodel():
    """Create expression metamodel for parsing."""
    grammar_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


@pytest.mark.parser
class TestSpecialVariablesParsing:
    """Parser-level tests for Special Variables (§7.1.7)."""

    def test_test(self, expr_metamodel):
        """Parse $TEST."""
        model = expr_metamodel.model_from_str("$TEST", "Expr")
        assert model is not None

    def test_horolog(self, expr_metamodel):
        """Parse $HOROLOG."""
        model = expr_metamodel.model_from_str("$HOROLOG", "Expr")
        assert model is not None

    def test_x(self, expr_metamodel):
        """Parse $X."""
        model = expr_metamodel.model_from_str("$X", "Expr")
        assert model is not None

    def test_abbreviated_horolog(self, expr_metamodel):
        """Parse $H as abbreviated $HOROLOG (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$H", "Expr")
        assert model is not None
        # Navigate: Expr -> left (UnaryExpr) -> operand (PrimaryExpr)
        # PrimaryExpr should be SpecialVariable
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "H"

    def test_abbreviated_storage(self, expr_metamodel):
        """Parse $S as abbreviated $STORAGE (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$S", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "S"

    def test_abbreviated_test(self, expr_metamodel):
        """Parse $T as abbreviated $TEST (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$T", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "T"

    def test_abbreviated_job(self, expr_metamodel):
        """Parse $J as abbreviated $JOB (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$J", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "J"

    def test_abbreviated_io(self, expr_metamodel):
        """Parse $I as abbreviated $IO (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$I", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "I"

    def test_abbreviated_device(self, expr_metamodel):
        """Parse $D as abbreviated $DEVICE (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$D", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "D"

    def test_select_function_still_works(self, expr_metamodel):
        """Parse $SELECT(cond:val) as SelectFunction, not special variable.

        $S alone is $STORAGE special variable, but $S(cond:val) is $SELECT function.
        $SELECT uses special syntax with condition:value pairs.
        """
        model = expr_metamodel.model_from_str("$SELECT(1:1)", "Expr")
        assert model is not None
        operand = model.left.operand
        # Should be SelectFunction since it has condition:value arguments
        assert operand.__class__.__name__ == "SelectFunction", (
            f"Expected SelectFunction, got {operand.__class__.__name__}"
        )
        assert operand.name in ("SELECT", "S")


@pytest.mark.parser
class TestSpecialVariablesStubs:
    """Tests for Special Variables (§7.1.7) - full and abbreviated forms."""

    def test_device_variable(self, expr_metamodel):
        """$DEVICE parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$DEVICE", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "DEVICE"

    def test_ecode_variable(self, expr_metamodel):
        """$ECODE parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$ECODE", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ECODE"

    def test_eref_variable(self, expr_metamodel):
        """$EREF parses correctly (§7.1.7).

        Note: $EREF is implementation-specific (Caché/IRIS), but the parser
        accepts it via the generic special variable pattern.
        """
        model = expr_metamodel.model_from_str("$EREF", "Expr")
        assert model is not None
        operand = model.left.operand
        # May parse as SpecialVariable or IntrinsicFunctionNoArgs depending on grammar
        assert operand.__class__.__name__ in (
            "SpecialVariable",
            "IntrinsicFunctionNoArgs",
        )
        assert operand.name == "EREF"

    def test_estack_variable(self, expr_metamodel):
        """$ESTACK parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$ESTACK", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ESTACK"

    def test_etrap_variable(self, expr_metamodel):
        """$ETRAP parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$ETRAP", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ETRAP"

    def test_ioreference_variable(self, expr_metamodel):
        """$IOREFERENCE parses correctly (§7.1.7).

        Note: $IOREFERENCE is implementation-specific, but the parser
        accepts it via the generic special variable pattern.
        """
        model = expr_metamodel.model_from_str("$IOREFERENCE", "Expr")
        assert model is not None
        operand = model.left.operand
        # May parse as SpecialVariable or IntrinsicFunctionNoArgs
        assert operand.__class__.__name__ in (
            "SpecialVariable",
            "IntrinsicFunctionNoArgs",
        )
        assert operand.name == "IOREFERENCE"

    def test_key_variable(self, expr_metamodel):
        """$KEY parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$KEY", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "KEY"

    def test_pdisplay_variable(self, expr_metamodel):
        """$PDISPLAY parses correctly (§7.1.7).

        Note: $PDISPLAY is implementation-specific (GT.M/YDB), but the parser
        accepts it via the generic special variable pattern.
        """
        model = expr_metamodel.model_from_str("$PDISPLAY", "Expr")
        assert model is not None
        operand = model.left.operand
        # May parse as SpecialVariable or IntrinsicFunctionNoArgs
        assert operand.__class__.__name__ in (
            "SpecialVariable",
            "IntrinsicFunctionNoArgs",
        )
        assert operand.name == "PDISPLAY"

    def test_pioreference_variable(self, expr_metamodel):
        """$PIOREFERENCE parses correctly (§7.1.7).

        Note: $PIOREFERENCE is implementation-specific, but the parser
        accepts it via the generic special variable pattern.
        """
        model = expr_metamodel.model_from_str("$PIOREFERENCE", "Expr")
        assert model is not None
        operand = model.left.operand
        # May parse as SpecialVariable or IntrinsicFunctionNoArgs
        assert operand.__class__.__name__ in (
            "SpecialVariable",
            "IntrinsicFunctionNoArgs",
        )
        assert operand.name == "PIOREFERENCE"

    def test_principal_variable(self, expr_metamodel):
        """$PRINCIPAL parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$PRINCIPAL", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "PRINCIPAL"

    def test_quit_variable(self, expr_metamodel):
        """$QUIT parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$QUIT", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "QUIT"

    def test_reference_variable(self, expr_metamodel):
        """$REFERENCE parses correctly (§7.1.7).

        Note: $REFERENCE is implementation-specific (Caché), but the parser
        accepts it via the generic special variable pattern.
        """
        model = expr_metamodel.model_from_str("$REFERENCE", "Expr")
        assert model is not None
        operand = model.left.operand
        # May parse as SpecialVariable or IntrinsicFunctionNoArgs
        assert operand.__class__.__name__ in (
            "SpecialVariable",
            "IntrinsicFunctionNoArgs",
        )
        assert operand.name == "REFERENCE"

    def test_stack_variable(self, expr_metamodel):
        """$STACK parses correctly (§7.1.7).

        Note: As a special variable (no args), $STACK returns current stack level.
        With args like $STACK(level), it becomes the $STACK function.
        """
        model = expr_metamodel.model_from_str("$STACK", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "STACK"

    def test_system_variable(self, expr_metamodel):
        """$SYSTEM parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$SYSTEM", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "SYSTEM"

    def test_tlevel_variable(self, expr_metamodel):
        """$TLEVEL parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$TLEVEL", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "TLEVEL"

    def test_trestart_variable(self, expr_metamodel):
        """$TRESTART parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$TRESTART", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "TRESTART"

    def test_y_variable(self, expr_metamodel):
        """$Y parses correctly (§7.1.7)."""
        model = expr_metamodel.model_from_str("$Y", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "Y"


@pytest.mark.parser
class TestSpecialVariableGrammar:
    """Test special variable parsing via MUMPSParser."""

    def test_test_variable(self):
        """$TEST special variable should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tI $TEST W "true"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_test_abbreviated(self):
        """$T abbreviation should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tI $T W "true"\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_horolog_variable(self):
        """$HOROLOG should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS TIME=$HOROLOG\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_job_variable(self):
        """$JOB should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS PID=$JOB\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestIORefSpecialVariableGrammar:
    """Test $IOREFERENCE and related long ISV names via MUMPSParser.

    Per MUMPS 1995 spec 7.1.4.10.7, $IOREFERENCE tracks the current
    I/O device. The grammar must match the full name, not just $IO.
    """

    def test_ioreference_full(self):
        """$IOREFERENCE should parse as single special variable."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MSpecialVariable

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
        """$IOR should parse as IOREFERENCE."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MSpecialVariable

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
        """$PIOREFERENCE should parse as single special variable."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MSpecialVariable

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
        """$IO should still parse correctly."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MSpecialVariable

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
