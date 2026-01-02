"""Tests for Extrinsic Functions parsing (§7.1.6).

Tests verify the textX grammar correctly captures extrinsic function syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6
"""

import pytest


@pytest.mark.parser
class TestExtrinsicFunctionsParsing:
    """Parser-level tests for Extrinsic Functions (§7.1.6).

    Extrinsic functions are user-defined functions called with $$ prefix.

    Migrated from: tests/unit/test_expression_grammar.py::TestExtrinsicFunctions
    """

    def test_local_extrinsic(self, parse_expression):
        """$$label() local extrinsic parses correctly (§7.1.6).

        Migrated from: tests/unit/test_expression_grammar.py::TestExtrinsicFunctions
        """
        model = parse_expression("$$FUNC(X)")
        assert model is not None

    def test_external_extrinsic(self, parse_expression):
        """$$label^routine() external extrinsic parses correctly (§7.1.6).

        Migrated from: tests/unit/test_expression_grammar.py::TestExtrinsicFunctions
        """
        model = parse_expression("$$FUNC^ROUTINE(X,Y)")
        assert model is not None

    def test_extrinsic_function_basic(self, parse_expression):
        """$$FUNC parses correctly (§7.1.6)."""
        model = parse_expression("$$FUNC")
        assert model is not None

    def test_extrinsic_function_with_args(self, parse_expression):
        """$$FUNC(arg1,arg2) parses correctly (§7.1.6)."""
        model = parse_expression("$$FUNC(A,B)")
        assert model is not None

    def test_extrinsic_function_by_ref(self, parse_expression):
        """$$FUNC(.var) pass by reference parses correctly (§7.1.6)."""
        model = parse_expression("$$FUNC(.X)")
        assert model is not None


@pytest.mark.parser
class TestExternalFunction:
    """Tests for external function call syntax $&func() (Phase 103).

    External functions call C functions linked into the MUMPS runtime.
    Syntax: $&name(args) or $&package.name(args)

    Migrated from: tests/unit/test_expression_grammar.py::TestExternalFunctions
    """

    def test_external_function_simple(self, parse_expression):
        """$&RAND(1) - external function without package (§7.1.6).

        Migrated from: tests/unit/test_expression_grammar.py::TestExternalFunctions
        """
        model = parse_expression("$&RAND(1)")
        assert model is not None
        # The result is an ExternalFunction wrapped in UnaryExpr
        assert model.left.operand.__class__.__name__ == "ExternalFunction"
        assert model.left.operand.name == "RAND"
        assert model.left.operand.package is None

    def test_external_function_byref_arg(self, parse_expression):
        """$&RAND(.var) - external function with by-reference argument (§7.1.6).

        Migrated from: tests/unit/test_expression_grammar.py::TestExternalFunctions
        """
        model = parse_expression("$&RAND(.x)")
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.name == "RAND"
        # Check that the argument is a by-ref arg
        assert ext_func.args.first.byref is not None

    def test_external_function_with_package(self, parse_expression):
        """$&pkg.func(1) - external function with package prefix (§7.1.6).

        Migrated from: tests/unit/test_expression_grammar.py::TestExternalFunctions
        """
        model = parse_expression("$&ydbposix.signalval(1)")
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.package == "ydbposix"
        assert ext_func.name == "signalval"

    def test_external_function_complex_args(self, parse_expression):
        """$&ydbposix.signalval("SIGTERM",.val) - with string and by-ref (§7.1.6).

        Migrated from: tests/unit/test_expression_grammar.py::TestExternalFunctions
        """
        model = parse_expression('$&ydbposix.signalval("SIGTERM",.val)')
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.package == "ydbposix"
        assert ext_func.name == "signalval"
        # First arg is string, second is by-ref
        assert ext_func.args.first.expr is not None  # string arg
        assert len(ext_func.args.rest) == 1
        assert ext_func.args.rest[0].arg.byref is not None  # by-ref arg
