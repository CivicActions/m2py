from m2py.analysis.semantic_analyzer import analyze_statement
from m2py.asg.expressions import (
    MBinaryOp,
    MActualParameter,
    MSelectArg,
    MDeviceControl,
    MExternalFunction,
    MIntrinsicFunction,
)


def test_select_function_analysis():
    """Test that $SELECT arguments are correctly analyzed."""
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


def test_device_control_analysis():
    """Test that DeviceControl parameters are correctly analyzed."""
    # Use WRITE command which supports DeviceControl
    stmt = analyze_statement("W", "/KEY(A+1)")

    from m2py.asg.statements import MWriteStatement

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


def test_external_function_analysis():
    """Test that $&func arguments are correctly analyzed."""
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
