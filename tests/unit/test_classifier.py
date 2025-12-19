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

# =============================================================================
# GOTO Statement Parsing Tests (T065-T067 - Phase 5)
# =============================================================================

class TestParseGotoStatement:
    """Test parse_goto_statement function (T065-T067)."""
    
    def test_parse_goto_local_label(self):
        """Parse G LABEL into MGotoStatement with local target (T065)."""
        from m2py.analysis import parse_goto_statement
        from m2py.asg.statements import MGotoStatement
        
        stmt = parse_goto_statement("LABEL")
        
        assert isinstance(stmt, MGotoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine is None
        assert stmt.targets[0].offset is None
    
    def test_parse_goto_percent_label(self):
        """Parse G %LABEL into MGotoStatement (T065)."""
        from m2py.analysis import parse_goto_statement
        
        stmt = parse_goto_statement("%LABEL")
        
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "%LABEL"
    
    def test_parse_goto_label_offset(self):
        """Parse G LABEL+2 into MGotoStatement with offset (T066)."""
        from m2py.analysis import parse_goto_statement
        
        stmt = parse_goto_statement("LABEL+2")
        
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].offset is not None
        assert stmt.targets[0].offset.raw_value == "2"
    
    def test_parse_goto_label_expression_offset(self):
        """Parse G LABEL+$D(A) into MGotoStatement with expression offset (T066)."""
        from m2py.analysis import parse_goto_statement
        
        stmt = parse_goto_statement("LABEL+$D(A)")
        
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].offset is not None
        # Complex expression preserved
        assert "$D(A)" in stmt.targets[0].offset.raw_value
    
    def test_parse_goto_external_routine(self):
        """Parse G LABEL^ROUTINE into MGotoStatement with external target (T067)."""
        from m2py.analysis import parse_goto_statement
        
        stmt = parse_goto_statement("LABEL^ROUTINE")
        
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine == "ROUTINE"
    
    def test_parse_goto_external_only_routine(self):
        """Parse G ^ROUTINE into MGotoStatement (entry point) (T067)."""
        from m2py.analysis import parse_goto_statement
        
        stmt = parse_goto_statement("^ROUTINE")
        
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == ""
        assert stmt.targets[0].routine == "ROUTINE"
    
    def test_parse_goto_multiple_targets(self):
        """Parse G A,B,C into MGotoStatement with multiple targets."""
        from m2py.analysis import parse_goto_statement
        
        stmt = parse_goto_statement("A,B,C")
        
        assert len(stmt.targets) == 3
        assert stmt.targets[0].name == "A"
        assert stmt.targets[1].name == "B"
        assert stmt.targets[2].name == "C"
    
    def test_parse_goto_postconditioned(self):
        """Parse G:X>0 LABEL into MGotoStatement with postcondition."""
        from m2py.analysis import parse_goto_statement
        
        # The postcondition is on the target, not the command
        stmt = parse_goto_statement("LABEL:X>0")
        
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].postcondition is not None


class TestExtractGotoFromLine:
    """Test extract_goto_from_line function."""
    
    def test_extract_goto_abbreviated(self):
        """G abbreviation should be recognized."""
        from m2py.analysis import extract_goto_from_line
        
        result = extract_goto_from_line("\tG LABEL")
        assert result is not None
        name, routine, offset = result
        assert name == "LABEL"
        assert routine is None
    
    def test_extract_goto_full(self):
        """GOTO full keyword should be recognized."""
        from m2py.analysis import extract_goto_from_line
        
        result = extract_goto_from_line("\tGOTO LABEL")
        assert result is not None
        name, routine, offset = result
        assert name == "LABEL"
    
    def test_extract_no_goto(self):
        """Line without GOTO should return None."""
        from m2py.analysis import extract_goto_from_line
        
        result = extract_goto_from_line("\tS X=1 W X")
        assert result is None


# =============================================================================
# GOTO Classification Tests (T080-T087 - Phase 5)
# =============================================================================

class TestClassifyGotos:
    """Test classify_gotos function (T080-T085)."""
    
    def _create_routine_with_goto(self, target_label_name: str, 
                                   source_label_name: str = "MAIN",
                                   routine_name: str = None,
                                   enclosing_for: bool = False) -> "MRoutine":
        """Create a routine with a GOTO for testing."""
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement, MForStatement
        
        routine = MRoutine(name="TEST")
        
        # Source label with GOTO
        source_label = MLabel(name=source_label_name)
        source_label.body = MScope()
        
        # Create GOTO statement
        goto_stmt = MGotoStatement()
        call = MCall(name=target_label_name, routine=routine_name)
        goto_stmt.targets.append(call)
        
        if enclosing_for:
            # Put GOTO inside a FOR loop
            for_stmt = MForStatement()
            for_stmt.body = MScope()
            for_stmt.body.add_statement(goto_stmt)
            source_label.body.add_statement(for_stmt)
        else:
            source_label.body.add_statement(goto_stmt)
        
        routine.add_label(source_label)
        
        # Target label
        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        routine.add_label(target_label)
        
        return routine
    
    def test_classify_external_goto(self):
        """GOTO ^ROUTINE should be classified as EXTERNAL (T085)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.enums import GotoType
        
        routine = self._create_routine_with_goto("LABEL", routine_name="OTHER")
        resolve_references(routine)
        classify_gotos(routine)
        
        # Find the GOTO statement
        goto_stmt = list(routine.labels[0].body.walk_statements())[0]
        assert goto_stmt.goto_type == GotoType.EXTERNAL
    
    def test_classify_forward_jump(self):
        """GOTO to later label should be FORWARD_JUMP (T080)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.enums import GotoType
        
        routine = self._create_routine_with_goto("TARGET")
        resolve_references(routine)
        classify_gotos(routine)
        
        goto_stmt = list(routine.labels[0].body.walk_statements())[0]
        # TARGET comes after MAIN, so forward jump
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
    
    def test_classify_backward_jump(self):
        """GOTO to earlier label should be BACKWARD_JUMP (T081)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.asg.enums import GotoType
        
        routine = MRoutine(name="TEST")
        
        # First label
        first = MLabel(name="FIRST")
        first.body = MScope()
        routine.add_label(first)
        
        # Second label with GOTO FIRST (backward)
        second = MLabel(name="SECOND")
        second.body = MScope()
        goto_stmt = MGotoStatement()
        call = MCall(name="FIRST")
        goto_stmt.targets.append(call)
        second.body.add_statement(goto_stmt)
        routine.add_label(second)
        
        resolve_references(routine)
        classify_gotos(routine)
        
        # Should be backward jump
        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP
    
    def test_classify_loop_exit(self):
        """GOTO inside single FOR should be LOOP_EXIT (T082)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.enums import GotoType
        
        routine = self._create_routine_with_goto("TARGET", enclosing_for=True)
        resolve_references(routine)
        classify_gotos(routine)
        
        # Find the GOTO inside the FOR
        for_stmt = routine.labels[0].body.statements[0]
        goto_stmt = for_stmt.body.statements[0]
        
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 1
    
    def test_classify_multi_loop_exit(self):
        """GOTO inside nested FORs should be MULTI_LOOP_EXIT (T083)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement, MForStatement
        from m2py.asg.enums import GotoType
        
        routine = MRoutine(name="TEST")
        
        # Source label with nested FOR
        source = MLabel(name="MAIN")
        source.body = MScope()
        
        # Outer FOR
        outer_for = MForStatement()
        outer_for.body = MScope()
        
        # Inner FOR with GOTO
        inner_for = MForStatement()
        inner_for.body = MScope()
        
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        inner_for.body.add_statement(goto_stmt)
        outer_for.body.add_statement(inner_for)
        
        source.body.add_statement(outer_for)
        routine.add_label(source)
        
        # Target label
        target = MLabel(name="TARGET")
        target.body = MScope()
        routine.add_label(target)
        
        resolve_references(routine)
        classify_gotos(routine)
        
        assert goto_stmt.goto_type == GotoType.MULTI_LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 2
    
    def test_classify_unresolved(self):
        """GOTO to missing label should be UNRESOLVED (T080)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.asg.enums import GotoType
        
        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()
        
        goto_stmt = MGotoStatement()
        call = MCall(name="MISSING")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)
        
        routine.add_label(label)
        
        resolve_references(routine)
        classify_gotos(routine)
        
        assert goto_stmt.goto_type == GotoType.UNRESOLVED


class TestGetLoopExitingGotos:
    """Test get_loop_exiting_gotos function (T086)."""
    
    def test_returns_gotos_with_exits_loops(self):
        """Should return GOTOs that exit FOR loops."""
        from m2py.analysis import resolve_references, classify_gotos, get_loop_exiting_gotos
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement, MForStatement
        
        routine = MRoutine(name="TEST")
        
        # Label with FOR containing GOTO
        label = MLabel(name="MAIN")
        label.body = MScope()
        
        for_stmt = MForStatement()
        for_stmt.body = MScope()
        
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)
        
        label.body.add_statement(for_stmt)
        routine.add_label(label)
        
        target = MLabel(name="TARGET")
        target.body = MScope()
        routine.add_label(target)
        
        resolve_references(routine)
        classify_gotos(routine)
        
        result = get_loop_exiting_gotos(routine)
        assert len(result) == 1
        assert result[0] is goto_stmt
