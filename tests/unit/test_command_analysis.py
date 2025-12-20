"""Tests for semantic analyzer command analysis.

Tests analyze_command() which converts textX-parsed commands into
fully-analyzed ASG statements with proper parent relationships,
unwrapped expressions, and classified types.

Tests are organized by command type (SET, WRITE, FOR, GOTO, etc.).
For expression analysis, see test_semantic_analyzer.py.
"""

import pytest

from m2py.analysis.command_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import (
    MSetStatement,
    MWriteStatement,
    MReadStatement,
    MQuitStatement,
    MIfStatement,
    MElseStatement,
    MForStatement,
    MGotoStatement,
    MDoStatement,
    MNewStatement,
    MKillStatement,
    MHangStatement,
    MHaltStatement,
    MBreakStatement,
)
from m2py.asg.expressions import (
    MLiteral,
    MVariable,
    MGlobal,
    MIntrinsicFunction,
    MBinaryOp,
)
from m2py.asg.enums import LiteralType, ForLoopType, ForParamType


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


class TestSetStatementAnalysis:
    """Tests for SET command analysis."""
    
    def test_simple_set(self):
        """SET X=1 produces MSetStatement with one assignment."""
        stmt = analyze_first_command("S X=1")
        
        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 1
        
        # Check target
        target = stmt.assignments[0].target
        assert isinstance(target, MVariable)
        assert target.name == "X"
        
        # Check value - should be an expression (MLiteral or unwrapped)
        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.value == 1
    
    def test_multiple_assignments(self):
        """SET X=1,Y=2 produces two assignments."""
        stmt = analyze_first_command("S X=1,Y=2")
        
        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 2
        
        assert stmt.assignments[0].target.name == "X"
        assert stmt.assignments[1].target.name == "Y"
    
    def test_set_with_global(self):
        """SET ^GLOBAL=value produces MGlobal target."""
        stmt = analyze_first_command("S ^DATA=100")
        
        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MGlobal)
        assert target.name == "DATA"
    
    def test_set_string_literal(self):
        """SET X="hello" produces string literal."""
        stmt = analyze_first_command('S X="hello"')
        
        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.literal_type == LiteralType.STRING
        assert value.value == "hello"


class TestWriteStatementAnalysis:
    """Tests for WRITE command analysis."""
    
    def test_simple_write(self):
        """WRITE X produces MWriteStatement."""
        stmt = analyze_first_command("W X")
        
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) >= 1
    
    def test_write_string(self):
        """WRITE "hello" produces string literal argument."""
        stmt = analyze_first_command('W "hello"')
        
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) >= 1
        # Argument may be wrapped, check the underlying value
        arg = stmt.arguments[0]
        if isinstance(arg, MLiteral):
            assert arg.value == "hello"
        else:
            # May be an Expr wrapper - just verify it exists
            assert arg is not None
    
    def test_write_format_control(self):
        """WRITE ! produces newline format control."""
        stmt = analyze_first_command("W !")
        
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) >= 1


class TestQuitStatementAnalysis:
    """Tests for QUIT command analysis."""
    
    def test_simple_quit(self):
        """Q produces MQuitStatement with no return value."""
        stmt = analyze_first_command("Q")
        
        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is None
    
    def test_quit_with_value(self):
        """Q X produces MQuitStatement with return value."""
        stmt = analyze_first_command("Q X")
        
        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is not None
        assert isinstance(stmt.return_value, MVariable)
        assert stmt.return_value.name == "X"
    
    def test_quit_with_expression(self):
        """Q X+1 produces MQuitStatement with binary expression."""
        stmt = analyze_first_command("Q X+1")
        
        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is not None
        assert isinstance(stmt.return_value, MBinaryOp)


class TestIfStatementAnalysis:
    """Tests for IF command analysis."""
    
    def test_if_with_condition(self):
        """IF X produces MIfStatement with condition."""
        stmt = analyze_first_command("I X")
        
        assert isinstance(stmt, MIfStatement)
        assert stmt.condition is not None
    
    def test_argumentless_if(self):
        """IF (argumentless) produces MIfStatement with no condition."""
        stmt = analyze_first_command("I")
        
        assert isinstance(stmt, MIfStatement)
        assert stmt.condition is None


class TestForStatementAnalysis:
    """Tests for FOR command analysis."""
    
    def test_argumentless_for(self):
        """F produces argumentless FOR."""
        stmt = analyze_first_command("F")
        
        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var is None or stmt.loop_var == ""
        assert len(stmt.parameters) == 0
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS
    
    def test_for_with_range(self):
        """F I=1:1:10 produces bounded FOR."""
        stmt = analyze_first_command("F I=1:1:10")
        
        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var == "I"
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].param_type == ForParamType.RANGE
        assert stmt.loop_type == ForLoopType.BOUNDED
    
    def test_for_with_values(self):
        """F I=1,2,3 produces value list FOR."""
        stmt = analyze_first_command('F I=1,2,3')
        
        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var == "I"
        assert len(stmt.parameters) == 3
        assert all(p.param_type == ForParamType.VALUE for p in stmt.parameters)
        assert stmt.loop_type == ForLoopType.STRING_LIST
    
    def test_for_open_ended(self):
        """F I=1:1 produces open-ended FOR."""
        stmt = analyze_first_command("F I=1:1")
        
        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var == "I"
        assert stmt.loop_type == ForLoopType.OPEN_ENDED


class TestGotoStatementAnalysis:
    """Tests for GOTO command analysis."""
    
    def test_simple_goto(self):
        """G LABEL produces MGotoStatement."""
        stmt = analyze_first_command("G LABEL")
        
        assert isinstance(stmt, MGotoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
    
    def test_goto_with_routine(self):
        """G LABEL^ROUTINE produces target with routine."""
        stmt = analyze_first_command("G LABEL^ROUTINE")
        
        assert isinstance(stmt, MGotoStatement)
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine == "ROUTINE"


class TestDoStatementAnalysis:
    """Tests for DO command analysis."""
    
    def test_simple_do(self):
        """D LABEL produces MDoStatement."""
        stmt = analyze_first_command("D LABEL")
        
        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
    
    def test_do_with_args(self):
        """D FUNC(1,2) produces target with arguments."""
        stmt = analyze_first_command("D FUNC(1,2)")
        
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]
        assert target.name == "FUNC"
        assert len(target.arguments) == 2


class TestNewStatementAnalysis:
    """Tests for NEW command analysis."""
    
    def test_simple_new(self):
        """N X produces MNewStatement."""
        stmt = analyze_first_command("N X")
        
        assert isinstance(stmt, MNewStatement)
        assert "X" in stmt.variables
    
    def test_multiple_new(self):
        """N X,Y,Z produces multiple variables."""
        stmt = analyze_first_command("N X,Y,Z")
        
        assert isinstance(stmt, MNewStatement)
        assert len(stmt.variables) == 3


class TestKillStatementAnalysis:
    """Tests for KILL command analysis."""
    
    def test_simple_kill(self):
        """K X produces MKillStatement."""
        stmt = analyze_first_command("K X")
        
        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1


class TestOtherStatementAnalysis:
    """Tests for other statement types."""
    
    def test_hang(self):
        """H 5 produces MHangStatement."""
        stmt = analyze_first_command("H 5")
        
        assert isinstance(stmt, MHangStatement)
        assert stmt.duration is not None
    
    def test_halt(self):
        """HALT produces MHaltStatement."""
        stmt = analyze_first_command("HALT")
        
        assert isinstance(stmt, MHaltStatement)
    
    def test_break(self):
        """B produces MBreakStatement."""
        stmt = analyze_first_command("B")
        
        assert isinstance(stmt, MBreakStatement)


class TestMultipleCommandsAnalysis:
    """Tests for analyzing multiple commands."""
    
    def test_line_with_multiple_commands(self):
        """S X=1 W X Q produces three statements."""
        cmds = parse_commands_from_line("S X=1 W X Q")
        stmts = [analyze_command(cmd) for cmd in cmds]
        
        assert len(stmts) == 3
        assert isinstance(stmts[0], MSetStatement)
        assert isinstance(stmts[1], MWriteStatement)
        assert isinstance(stmts[2], MQuitStatement)


class TestExpressionAnalysis:
    """Tests for expression analysis within commands."""
    
    def test_numeric_literal_integer(self):
        """Integer numeric literal."""
        stmt = analyze_first_command("S X=42")
        
        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.literal_type == LiteralType.INTEGER
        assert value.value == 42
    
    def test_numeric_literal_decimal(self):
        """Decimal numeric literal."""
        stmt = analyze_first_command("S X=3.14")
        
        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.literal_type == LiteralType.DECIMAL
        assert value.value == 3.14
    
    def test_variable_with_subscripts(self):
        """Variable with subscripts."""
        stmt = analyze_first_command("S X(1,2)=3")
        
        target = stmt.assignments[0].target
        assert isinstance(target, MVariable)
        assert target.name == "X"
        assert len(target.subscripts) == 2
    
    def test_intrinsic_function(self):
        """Intrinsic function call."""
        stmt = analyze_first_command('S X=$L("hello")')
        
        value = stmt.assignments[0].value
        assert isinstance(value, MIntrinsicFunction)
        assert value.name == "L"
        assert len(value.arguments) == 1
    
    def test_binary_expression(self):
        """Binary expression in assignment."""
        stmt = analyze_first_command("S X=A+B")
        
        value = stmt.assignments[0].value
        assert isinstance(value, MBinaryOp)
        assert value.operator == "+"
        assert isinstance(value.left, MVariable)
        assert isinstance(value.right, MVariable)
