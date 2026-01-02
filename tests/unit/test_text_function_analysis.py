from m2py.analysis.semantic_analyzer import analyze_statement
from m2py.asg.expressions import MLiteral, MBinaryOp, MIndirection
from m2py.asg.statements import MSetStatement
from m2py.parser.textx_classes import TextFunction


def test_text_function_analysis_offset():
    """Test that $TEXT(label+offset^routine) analyzes the offset expression."""
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


def test_text_function_analysis_complex_offset():
    """Test that $TEXT(label+1+2^routine) analyzes the complex offset expression."""
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


def test_text_function_analysis_indirect_routine():
    """Test that $TEXT(label^@expr) analyzes the routine indirection."""
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
