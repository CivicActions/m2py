"""Unit tests for FOR loop classification.

Tests the classifier's ability to identify FOR loop types from line content.
"""

import pytest
from m2py.analysis import (
    classify_for_loop, 
    extract_for_from_line, 
    parse_for_statement,
    parse_set_statement,
    parse_write_statement,
    parse_quit_statement,
    parse_if_statement,
)
from m2py.asg.enums import ForLoopType, ForParamType
from m2py.asg.statements import MForStatement, MForParameter, MSetStatement, MWriteStatement, MQuitStatement, MIfStatement


class TestClassifyForLoop:
    """Test classify_for_loop function."""
    
    def test_bounded_for_simple(self):
        """FOR I=1:1:10 should be BOUNDED."""
        loop_type, var = classify_for_loop("I=1:1:10 W I")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "I"
    
    def test_bounded_for_expressions(self):
        """FOR J=N:1:M should be BOUNDED."""
        loop_type, var = classify_for_loop("J=N:1:M D PROC")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "J"
    
    def test_bounded_for_negative_step(self):
        """FOR K=10:-1:1 should be BOUNDED."""
        loop_type, var = classify_for_loop("K=10:-1:1 W K")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "K"
    
    def test_bounded_for_zero_step(self):
        """FOR J=4:0:5 should be BOUNDED (semantically infinite)."""
        loop_type, var = classify_for_loop("J=4:0:5 S I=I+1")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "J"
    
    def test_open_ended_for(self):
        """FOR I=1:1 should be OPEN_ENDED."""
        loop_type, var = classify_for_loop("I=1:1 W I")
        assert loop_type == ForLoopType.OPEN_ENDED
        assert var == "I"
    
    def test_string_list_single_value(self):
        """FOR I=7 should be STRING_LIST (single value)."""
        loop_type, var = classify_for_loop("I=7 S X=X_I")
        assert loop_type == ForLoopType.STRING_LIST
        assert var == "I"
    
    def test_string_list_multiple_values(self):
        """FOR I="A","B","C" should be STRING_LIST."""
        loop_type, var = classify_for_loop('I="A","B","C"')
        assert loop_type == ForLoopType.STRING_LIST
        assert var == "I"
    
    def test_argumentless_for_space(self):
        """FOR followed by space should be ARGUMENTLESS."""
        loop_type, var = classify_for_loop(' W "hello"')
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert var is None
    
    def test_argumentless_for_empty(self):
        """Empty content after FOR should be ARGUMENTLESS."""
        loop_type, var = classify_for_loop('')
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert var is None
    
    def test_percent_variable(self):
        """FOR %=1:1:10 should handle % variable."""
        loop_type, var = classify_for_loop("%=1:1:10 W %")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "%"


class TestExtractForFromLine:
    """Test extract_for_from_line function."""
    
    def test_extract_for_abbreviated(self):
        """F abbreviation should be recognized."""
        result = extract_for_from_line("\tF I=1:1:10 W I")
        assert result is not None
        loop_type, var, rest = result
        assert loop_type == ForLoopType.BOUNDED
        assert var == "I"
    
    def test_extract_for_full(self):
        """FOR full keyword should be recognized."""
        result = extract_for_from_line("\tFOR J=1:1:5 D ^PROC")
        assert result is not None
        loop_type, var, rest = result
        assert loop_type == ForLoopType.BOUNDED
        assert var == "J"
    
    def test_extract_for_case_insensitive(self):
        """for should be recognized (case insensitive)."""
        result = extract_for_from_line("\tfor K=1:1 W K")
        assert result is not None
        loop_type, var, rest = result
        assert loop_type == ForLoopType.OPEN_ENDED
        assert var == "K"
    
    def test_extract_no_for(self):
        """Line without FOR should return None."""
        result = extract_for_from_line("\tS X=1 W X")
        assert result is None
    
    def test_extract_argumentless(self):
        """F followed by double space should be ARGUMENTLESS."""
        result = extract_for_from_line('\tF  W "loop"')
        assert result is not None
        loop_type, var, rest = result
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert var == ""


class TestParseForStatement:
    """Test parse_for_statement function - builds MForStatement ASG nodes."""
    
    def test_parse_bounded_for(self):
        """Parse FOR I=1:1:10 into MForStatement."""
        stmt = parse_for_statement("I=1:1:10 W I")
        
        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1
        
        param = stmt.parameters[0]
        assert param.param_type == ForParamType.RANGE
        assert param.start.value == 1
        assert param.step.value == 1
        assert param.end.value == 10
    
    def test_parse_open_ended_for(self):
        """Parse FOR I=1:1 into MForStatement with OPEN_RANGE."""
        stmt = parse_for_statement("I=1:1 W I")
        
        assert stmt.loop_var == "I"
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert len(stmt.parameters) == 1
        
        param = stmt.parameters[0]
        assert param.param_type == ForParamType.OPEN_RANGE
        assert param.start.value == 1
        assert param.step.value == 1
        assert param.end is None
    
    def test_parse_string_list_for(self):
        """Parse FOR I="A","B","C" into MForStatement with VALUE params."""
        stmt = parse_for_statement('I="A","B","C" W I')
        
        assert stmt.loop_var == "I"
        assert stmt.loop_type == ForLoopType.STRING_LIST
        assert len(stmt.parameters) == 3
        
        assert stmt.parameters[0].param_type == ForParamType.VALUE
        assert stmt.parameters[0].value.value == "A"
        assert stmt.parameters[1].value.value == "B"
        assert stmt.parameters[2].value.value == "C"
    
    def test_parse_mixed_for(self):
        """Parse FOR I="A",1:1:3 into MForStatement with MIXED type."""
        stmt = parse_for_statement('I="A",1:1:3 W I')
        
        assert stmt.loop_var == "I"
        assert stmt.loop_type == ForLoopType.MIXED
        assert len(stmt.parameters) == 2
        
        assert stmt.parameters[0].param_type == ForParamType.VALUE
        assert stmt.parameters[0].value.value == "A"
        
        assert stmt.parameters[1].param_type == ForParamType.RANGE
        assert stmt.parameters[1].start.value == 1
        assert stmt.parameters[1].end.value == 3
    
    def test_parse_argumentless_for(self):
        """Parse argumentless FOR into MForStatement."""
        stmt = parse_for_statement(' W "loop"')
        
        assert stmt.loop_var is None
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS
        assert len(stmt.parameters) == 0
    
    def test_parse_for_has_body_scope(self):
        """MForStatement should have body MScope."""
        stmt = parse_for_statement("I=1:1:10 W I")
        
        assert stmt.body is not None
        from m2py.asg.elements import MScope
        assert isinstance(stmt.body, MScope)
    
    def test_parse_for_decimal_step(self):
        """Parse FOR with decimal values."""
        stmt = parse_for_statement("I=0.1:0.1:1.0 W I")
        
        assert stmt.loop_type == ForLoopType.BOUNDED
        param = stmt.parameters[0]
        assert param.start.value == 0.1
        assert param.step.value == 0.1
        assert param.end.value == 1.0
    
    def test_parse_for_negative_values(self):
        """Parse FOR with negative values."""
        stmt = parse_for_statement("I=10:-1:0 W I")
        
        assert stmt.loop_type == ForLoopType.BOUNDED
        param = stmt.parameters[0]
        assert param.start.value == 10
        assert param.step.value == -1
        assert param.end.value == 0
    
    def test_parse_for_multiple_ranges(self):
        """Parse FOR with multiple range forparameters."""
        stmt = parse_for_statement("I=1:1:3,5:1:7 W I")
        
        assert stmt.loop_type == ForLoopType.BOUNDED  # All RANGE = BOUNDED
        assert len(stmt.parameters) == 2
        
        assert stmt.parameters[0].start.value == 1
        assert stmt.parameters[0].end.value == 3
        assert stmt.parameters[1].start.value == 5
        assert stmt.parameters[1].end.value == 7


class TestQuitDetection:
    """Test QUIT exit point detection in FOR loops."""
    
    def test_open_ended_for_with_quit(self):
        """Open-ended FOR with QUIT should set has_internal_quit."""
        stmt = parse_for_statement("I=1:1 W I Q:I>10")
        
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.has_internal_quit is True
    
    def test_open_ended_for_with_full_quit(self):
        """QUIT spelled out should be detected."""
        stmt = parse_for_statement("I=1:1 W I QUIT:I>10")
        
        assert stmt.has_internal_quit is True
    
    def test_bounded_for_no_quit(self):
        """Bounded FOR without QUIT should have has_internal_quit=False."""
        stmt = parse_for_statement("I=1:1:10 W I")
        
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert stmt.has_internal_quit is False
    
    def test_quit_inside_string_not_counted(self):
        """Q inside string should not count as QUIT."""
        stmt = parse_for_statement('I=1:1:10 W "Q value"')
        
        assert stmt.has_internal_quit is False
    
    def test_argumentless_for_with_quit(self):
        """Argumentless FOR with QUIT should detect it."""
        stmt = parse_for_statement(' W X Q:X>10')
        
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS
        assert stmt.has_internal_quit is True
    
    def test_postconditioned_quit(self):
        """Postconditioned QUIT (Q:cond) should be detected."""
        stmt = parse_for_statement("I=1:1 S X=I*2 Q:X>100")
        
        assert stmt.has_internal_quit is True
    
    def test_unconditional_quit(self):
        """Unconditional QUIT should be detected."""
        stmt = parse_for_statement("I=1:1:10 W I Q")
        
        assert stmt.has_internal_quit is True
    
    def test_quit_with_return_value(self):
        """QUIT with return value should be detected."""
        stmt = parse_for_statement("I=1:1 Q I*2")
        
        assert stmt.has_internal_quit is True


class TestParseSetStatement:
    """Test parse_set_statement function (T041)."""
    
    def test_parse_simple_set(self):
        """Parse SET X=1 into MSetStatement."""
        stmt = parse_set_statement("X=1")
        
        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"
        assert stmt.assignments[0].value.value == 1
    
    def test_parse_set_string(self):
        """Parse SET X="Hello" into MSetStatement."""
        stmt = parse_set_statement('X="Hello"')
        
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"
        assert stmt.assignments[0].value.value == "Hello"
    
    def test_parse_set_multiple_assignments(self):
        """Parse SET A=1,B=2,C=3 into MSetStatement."""
        stmt = parse_set_statement("A=1,B=2,C=3")
        
        assert len(stmt.assignments) == 3
        assert stmt.assignments[0].target.name == "A"
        assert stmt.assignments[1].target.name == "B"
        assert stmt.assignments[2].target.name == "C"
    
    def test_parse_set_empty(self):
        """Empty SET content returns empty statement."""
        stmt = parse_set_statement("")
        
        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 0
    
    def test_parse_set_with_expression(self):
        """Parse SET X=A+B into MSetStatement."""
        stmt = parse_set_statement("X=A+B")
        
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"
        # Value is stored as literal (expression string for now)
        assert stmt.assignments[0].value is not None


class TestParseWriteStatement:
    """Test parse_write_statement function (T042)."""
    
    def test_parse_write_string(self):
        """Parse WRITE "Hello" into MWriteStatement."""
        stmt = parse_write_statement('"Hello"')
        
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) == 1
        assert stmt.arguments[0].value == "Hello"
    
    def test_parse_write_newline(self):
        """Parse WRITE ! into MWriteStatement."""
        stmt = parse_write_statement("!")
        
        assert len(stmt.arguments) == 1
        assert stmt.arguments[0] == {'type': 'newline'}
    
    def test_parse_write_tab(self):
        """Parse WRITE ?10 into MWriteStatement."""
        stmt = parse_write_statement("?10")
        
        assert len(stmt.arguments) == 1
        assert stmt.arguments[0] == {'type': 'tab', 'column': '10'}
    
    def test_parse_write_multiple(self):
        """Parse WRITE !,"Hello",! into MWriteStatement."""
        stmt = parse_write_statement('!,"Hello",!')
        
        assert len(stmt.arguments) == 3
        assert stmt.arguments[0] == {'type': 'newline'}
        assert stmt.arguments[1].value == "Hello"
        assert stmt.arguments[2] == {'type': 'newline'}
    
    def test_parse_write_empty(self):
        """Empty WRITE content returns empty statement."""
        stmt = parse_write_statement("")
        
        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) == 0


class TestParseQuitStatement:
    """Test parse_quit_statement function (T042)."""
    
    def test_parse_quit_simple(self):
        """Parse QUIT with no arguments."""
        stmt = parse_quit_statement("")
        
        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is None
    
    def test_parse_quit_with_value(self):
        """Parse QUIT X*2 into MQuitStatement."""
        stmt = parse_quit_statement("X*2")
        
        assert stmt.return_value is not None
    
    def test_parse_quit_with_postcondition(self):
        """Parse Q:X>10 into MQuitStatement."""
        stmt = parse_quit_statement(":X>10")
        
        assert stmt.postcondition is not None
        assert stmt.return_value is None
    
    def test_parse_quit_postcondition_with_value(self):
        """Parse Q:X>10 Y into MQuitStatement."""
        stmt = parse_quit_statement(":X>10 Y")
        
        assert stmt.postcondition is not None
        assert stmt.return_value is not None


class TestParseIfStatement:
    """Test parse_if_statement function (T043)."""
    
    def test_parse_if_simple(self):
        """Parse IF X=1 into MIfStatement."""
        stmt = parse_if_statement("X=1 W Y")
        
        assert isinstance(stmt, MIfStatement)
        assert stmt.condition is not None
        assert stmt.then_scope is not None
    
    def test_parse_if_argumentless(self):
        """Parse IF with no arguments (uses $TEST)."""
        stmt = parse_if_statement("")
        
        assert stmt.condition is None
    
    def test_parse_if_complex_condition(self):
        """Parse IF with complex condition."""
        stmt = parse_if_statement("(X>0)&(Y<10) D SOMETHING")
        
        assert stmt.condition is not None
    
    def test_parse_if_has_body_content(self):
        """IF statement should capture body content."""
        stmt = parse_if_statement("X=1 W Y")
        
        assert hasattr(stmt, '_body_content')
        assert stmt._body_content == "W Y"
