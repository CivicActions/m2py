"""Tests for Extrinsic Functions parsing (§7.1.6).

Tests verify the textX grammar correctly captures extrinsic function syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6
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
class TestExtrinsicFunctionsParsing:
    """Parser-level tests for Extrinsic Functions (§7.1.6).

    Extrinsic functions are user-defined functions called with $$ prefix.

    """

    def test_local_extrinsic(self, expr_metamodel):
        """Parse $$label() local extrinsic."""
        model = expr_metamodel.model_from_str("$$FUNC(X)", "Expr")
        assert model is not None

    def test_external_extrinsic(self, expr_metamodel):
        """Parse $$label^routine() external extrinsic."""
        model = expr_metamodel.model_from_str("$$FUNC^ROUTINE(X,Y)", "Expr")
        assert model is not None

    def test_extrinsic_function_by_ref(self, expr_metamodel):
        """$$FUNC(.var) pass by reference parses correctly (§7.1.6).

        The .var syntax passes a variable by reference, allowing the
        extrinsic function to modify the caller's variable.
        """
        model = expr_metamodel.model_from_str("$$FUNC(.X)", "Expr")
        assert model is not None
        ef = model.left.operand
        assert ef.__class__.__name__ == "ExtrinsicFunction"
        # Check the argument is a by-ref argument
        assert ef.args is not None
        # First argument should be by-ref
        first_arg = ef.args.first
        assert first_arg.byref is not None


@pytest.mark.parser
class TestExternalFunctionsParsing:
    """Parser-level tests for External Functions ($&func) (Phase 103).

    External functions call C functions linked into the MUMPS runtime.
    Syntax: $&name(args) or $&package.name(args)


    """

    def test_external_function_simple(self, expr_metamodel):
        """Parse $&RAND(1) - external function without package."""
        model = expr_metamodel.model_from_str("$&RAND(1)", "Expr")
        assert model is not None
        # The result is an ExternalFunction wrapped in UnaryExpr
        assert model.left.operand.__class__.__name__ == "ExternalFunction"
        assert model.left.operand.name == "RAND"
        assert model.left.operand.package is None

    def test_external_function_byref_arg(self, expr_metamodel):
        """Parse $&RAND(.var) - external function with by-reference argument."""
        model = expr_metamodel.model_from_str("$&RAND(.x)", "Expr")
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.name == "RAND"
        # Check that the argument is a by-ref arg
        assert ext_func.args.first.byref is not None

    def test_external_function_with_package(self, expr_metamodel):
        """Parse $&pkg.func(1) - external function with package prefix."""
        model = expr_metamodel.model_from_str("$&ydbposix.signalval(1)", "Expr")
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.package == "ydbposix"
        assert ext_func.name == "signalval"

    def test_external_function_complex_args(self, expr_metamodel):
        """Parse $&ydbposix.signalval("SIGTERM",.val) - with string and by-ref."""
        model = expr_metamodel.model_from_str(
            '$&ydbposix.signalval("SIGTERM",.val)', "Expr"
        )
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.package == "ydbposix"
        assert ext_func.name == "signalval"
        # First arg is string, second is by-ref
        assert ext_func.args.first.expr is not None  # string arg
        assert len(ext_func.args.rest) == 1
        assert ext_func.args.rest[0].arg.byref is not None  # by-ref arg


@pytest.mark.parser
class TestExtrinsicFunctionsBasicSyntax:
    """Basic extrinsic function syntax tests from grammar validation."""

    def test_simple_extrinsic(self, expr_metamodel):
        """$$FUNC - simple extrinsic call."""
        model = expr_metamodel.model_from_str("$$FUNC", "Expr")
        assert model is not None

    def test_extrinsic_with_routine(self, expr_metamodel):
        """$$FUNC^ROUTINE - external routine call."""
        model = expr_metamodel.model_from_str("$$FUNC^ROUTINE", "Expr")
        assert model is not None

    def test_extrinsic_with_args(self, expr_metamodel):
        """$$FUNC(A,B,C) - with arguments."""
        model = expr_metamodel.model_from_str("$$FUNC(A,B,C)", "Expr")
        assert model is not None

    def test_extrinsic_full(self, expr_metamodel):
        """$$FUNC^ROUTINE(A,B) - full syntax."""
        model = expr_metamodel.model_from_str("$$FUNC^ROUTINE(A,B)", "Expr")
        assert model is not None
