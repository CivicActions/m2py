"""Tests for Intrinsic Functions ASG analysis (§7.1.5).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5

Migrated from:
- tests/unit/test_semantic_analyzer.py::TestIntrinsicFunctionASG
- tests/unit/test_complex_expressions_analysis.py
- tests/unit/test_text_function_analysis.py
"""

import pytest
from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression, analyze_statement
from m2py.asg.expressions import (
    MIntrinsicFunction,
    MVariable,
    MLiteral,
    MBinaryOp,
    MActualParameter,
    MSelectArg,
    MDeviceControl,
    MExternalFunction,
    MIndirection,
)
from m2py.asg.statements import MSetStatement
from m2py.parser.textx_classes import TextFunction


@pytest.mark.asg
class TestIntrinsicFunctionsAnalysis:
    """ASG-level tests for intrinsic functions analysis (§7.1.5).

    Migrated from: TestIntrinsicFunctionASG
    """

    def test_piece_function_args(self):
        """$PIECE(str,delim,pos) has 3 arguments (§7.1.5)."""
        expr = parse_expression('$PIECE(X,":",2)')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "PIECE"
        assert len(result.arguments) == 3

    def test_length_function_args(self):
        """$LENGTH(str) has 1 argument (§7.1.5)."""
        expr = parse_expression("$LENGTH(X)")
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "LENGTH"
        assert len(result.arguments) == 1

    def test_nested_function_args(self):
        """Nested function $L($P(X,",",1)) has nested arguments (§7.1.5)."""
        expr = parse_expression('$L($P(X,",",1))')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name in ("L", "LENGTH")
        assert len(result.arguments) == 1

        inner = result.arguments[0]
        assert isinstance(inner, MIntrinsicFunction)
        assert inner.name in ("P", "PIECE")

    def test_binary_expression_in_function_arg(self):
        """$E(X,I+1) has a binary expression argument - regression test for T582 (§7.1.5).

        This tests that binary expressions inside function arguments are correctly
        preserved and not dropped during unwrapping. Previously, _unwrap_expr()
        checked for '.ops' attribute but the grammar uses '.tail' for BinaryOpTail.

        Note: We use $E (EXTRACT) instead of $T (TEXT) because $TEXT has special
        line reference syntax where TEX+I means "label TEX plus I lines", not
        a binary expression.
        """
        expr = parse_expression("$E(X,I+1)")
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "E"
        assert len(result.arguments) == 2

        # First argument is just X
        assert isinstance(result.arguments[0], MVariable)
        assert result.arguments[0].name == "X"

        # Second argument should be an MBinaryOp, not just LocalVariable
        arg = result.arguments[1]
        assert isinstance(arg, MBinaryOp), (
            f"Expected MBinaryOp, got {type(arg).__name__}"
        )
        assert arg.operator == "+"

        # Left should be I, right should be 1
        assert isinstance(arg.left, MVariable)
        assert arg.left.name == "I"
        assert isinstance(arg.right, MLiteral)
        assert arg.right.value == 1

    def test_text_function_line_reference(self):
        """$T(TEX+I) is parsed as a line reference, not a binary expression (§7.1.5).

        In MUMPS, $TEXT takes a line reference argument where:
        - TEX is the label name
        - +I is the offset (number of lines from the label)

        This is distinct from a binary expression argument.
        """
        expr = parse_expression("$T(TEX+I)")
        result = analyze_expression(expr)

        assert isinstance(result, TextFunction)
        assert result.name == "T"
        # Arguments list is empty because line_ref is stored separately
        assert len(result.arguments) == 0

        # Check line_ref contains the label and offset
        assert hasattr(result, "line_ref")
        assert result.line_ref["label"] == "TEX"
        # Offset should be a variable reference to I
        assert isinstance(result.line_ref["offset"], MVariable)
        assert result.line_ref["offset"].name == "I"

    def test_complex_expression_in_function_arg(self):
        """$P(A," ;",2,99) preserves all arguments including string literals (§7.1.5)."""
        expr = parse_expression('$P(A," ;",2,99)')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "P"
        assert len(result.arguments) == 4

        # First arg is variable A
        assert isinstance(result.arguments[0], MVariable)
        assert result.arguments[0].name == "A"

        # Second arg is string literal " ;"
        assert isinstance(result.arguments[1], MLiteral)
        assert result.arguments[1].value == " ;"

        # Third and fourth args are numeric literals
        assert isinstance(result.arguments[2], MLiteral)
        assert result.arguments[2].value == 2
        assert isinstance(result.arguments[3], MLiteral)
        assert result.arguments[3].value == 99

    # ---- Stub tests for unimplemented functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ASCII function")
    def test_function_ascii(self):
        """$ASCII function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $CHAR function")
    def test_function_char(self):
        """$CHAR function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DATA function")
    def test_function_data(self):
        """$DATA function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.xfail(reason="Deprecated but used in VistA: $DEXTRACT (6 uses)")
    def test_function_dextract(self):
        """$DEXTRACT function is deprecated but used in VistA (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.xfail(reason="Deprecated but used in VistA: $DPIECE (12 uses)")
    def test_function_dpiece(self):
        """$DPIECE function is deprecated but used in VistA (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $FIND function")
    def test_function_find(self):
        """$FIND function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $FNUMBER function")
    def test_function_fnumber(self):
        """$FNUMBER function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $GET function")
    def test_function_get(self):
        """$GET function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $JUSTIFY function")
    def test_function_justify(self):
        """$JUSTIFY function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $NAME function")
    def test_function_name(self):
        """$NAME function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.skip(reason="Deprecated: $NEXT is pre-1995, use $ORDER")
    def test_function_next(self):
        """$NEXT function is deprecated (§7.1.5)."""
        pass

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ORDER function")
    def test_function_order(self):
        """$ORDER function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QLENGTH function")
    def test_function_qlength(self):
        """$QLENGTH function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QSUBSCRIPT function")
    def test_function_qsubscript(self):
        """$QSUBSCRIPT function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUERY function")
    def test_function_query(self):
        """$QUERY function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $RANDOM function")
    def test_function_random(self):
        """$RANDOM function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $REVERSE function")
    def test_function_reverse(self):
        """$REVERSE function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $SELECT function")
    def test_function_select(self):
        """$SELECT function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STACK function")
    def test_function_stack(self):
        """$STACK function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRANSLATE function")
    def test_function_translate(self):
        """$TRANSLATE function is correctly analyzed (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.xfail(reason="Used in VistA: $VIEW function (190+ uses)")
    def test_function_view(self):
        """$VIEW function is implementation-defined but used in VistA (§7.1.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestSelectFunctionAnalysis:
    """ASG-level tests for $SELECT function analysis (§7.1.5).

    Migrated from: tests/unit/test_complex_expressions_analysis.py
    """

    def test_select_function_analysis(self):
        """$SELECT arguments are correctly analyzed (§7.1.5).

        Migrated from: test_complex_expressions_analysis.py::test_select_function_analysis
        """
        stmt = analyze_statement("S", "X=$S(A=1:10,1:20)")
        expr = stmt.assignments[0].value
        assert isinstance(expr, MIntrinsicFunction)
        assert expr.name == "S"

        args = expr.arguments
        assert len(args) == 2
        assert isinstance(args[0], MSelectArg)
        assert isinstance(args[1], MSelectArg)

        # Check first arg condition (A=1)
        cond = args[0].condition
        assert isinstance(cond, MBinaryOp)
        assert cond.operator == "="
        assert cond.left.name == "A"
        assert cond.right.value == 1

        # Check first arg value (10)
        val = args[0].value
        assert val.value == 10


@pytest.mark.asg
class TestDeviceControlAnalysis:
    """ASG-level tests for DeviceControl parameter analysis (§7.1.5).

    Migrated from: tests/unit/test_complex_expressions_analysis.py
    """

    def test_device_control_analysis(self):
        """DeviceControl parameters are correctly analyzed (§7.1.5).

        Migrated from: test_complex_expressions_analysis.py::test_device_control_analysis
        """
        from m2py.asg.statements import MWriteStatement

        # Use WRITE command which supports DeviceControl
        stmt = analyze_statement("W", "/KEY(A+1)")

        assert isinstance(stmt, MWriteStatement)

        # stmt.arguments is list of Any (MExpr, MFormatControl, MDeviceControl)
        assert len(stmt.arguments) == 1
        dc = stmt.arguments[0]

        assert isinstance(dc, MDeviceControl)
        assert dc.keyword == "KEY"

        # Check param analysis
        assert len(dc.params) == 1
        p = dc.params[0]
        assert isinstance(p, MBinaryOp)
        assert p.operator == "+"
        assert p.left.name == "A"


@pytest.mark.asg
class TestExternalFunctionAnalysis:
    """ASG-level tests for $& external function analysis (§7.1.5).

    Migrated from: tests/unit/test_complex_expressions_analysis.py
    """

    def test_external_function_analysis(self):
        """$&func arguments are correctly analyzed (§7.1.5).

        Migrated from: test_complex_expressions_analysis.py::test_external_function_analysis
        """
        stmt = analyze_statement("S", "X=$&lib.func(A+1)")
        expr = stmt.assignments[0].value

        assert isinstance(expr, MExternalFunction)
        assert expr.package == "lib"
        assert expr.name == "func"

        args = expr.arguments
        assert len(args) == 1
        arg = args[0]

        assert isinstance(arg, MActualParameter)
        assert isinstance(arg.expression, MBinaryOp)
        assert arg.expression.operator == "+"
        assert arg.expression.left.name == "A"


@pytest.mark.asg
class TestTextFunctionAnalysis:
    """ASG-level tests for $TEXT function analysis (§7.1.5).

    Migrated from: tests/unit/test_text_function_analysis.py
    """

    def test_text_function_analysis_offset(self):
        """$TEXT(label+offset^routine) analyzes the offset expression (§7.1.5).

        Migrated from: test_text_function_analysis.py::test_text_function_analysis_offset
        """
        stmt = analyze_statement("S", "X=$TEXT(label+1^routine)")
        assert isinstance(stmt, MSetStatement)
        expr = stmt.assignments[0].value
        assert isinstance(expr, TextFunction)

        # Check line_ref
        line_ref = expr.line_ref
        assert line_ref["label"] == "label"
        assert line_ref["routine"] == "routine"

        # Check offset is analyzed (should be MLiteral, not textX object)
        offset = line_ref["offset"]
        assert isinstance(offset, MLiteral)
        assert offset.value == 1

    def test_text_function_analysis_complex_offset(self):
        """$TEXT(label+1+2^routine) analyzes the complex offset expression (§7.1.5).

        Migrated from: test_text_function_analysis.py::test_text_function_analysis_complex_offset
        """
        stmt = analyze_statement("S", "X=$TEXT(label+1+2^routine)")
        expr = stmt.assignments[0].value

        offset = expr.line_ref["offset"]
        # Should be MBinaryOp, not textX Expr
        assert isinstance(offset, MBinaryOp)
        assert offset.operator == "+"
        assert isinstance(offset.left, MLiteral)
        assert offset.left.value == 1
        assert isinstance(offset.right, MLiteral)
        assert offset.right.value == 2

    def test_text_function_analysis_indirect_routine(self):
        """$TEXT(label^@expr) analyzes the routine indirection (§7.1.5).

        Migrated from: test_text_function_analysis.py::test_text_function_analysis_indirect_routine
        """
        # Use complex expression inside indirection to verify analysis recursion
        stmt = analyze_statement("S", 'X=$TEXT(label^@("rout"_"ine"))')
        expr = stmt.assignments[0].value

        line_ref = expr.line_ref
        assert "routine_indirect" in line_ref

        rout_ind = line_ref["routine_indirect"]
        assert isinstance(rout_ind, MIndirection)

        # The expression inside indirection should be analyzed (MBinaryOp)
        assert isinstance(rout_ind.expression, MBinaryOp)
        assert rout_ind.expression.operator == "_"
        assert rout_ind.expression.left.value == "rout"
        assert rout_ind.expression.right.value == "ine"
