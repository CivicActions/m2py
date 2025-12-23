"""Unit tests for MUMPS grammar acceptance.

Tests that various MUMPS syntax constructs parse successfully through
MUMPSParser.parse(). These tests verify grammar coverage - that the
parser accepts valid MUMPS syntax without error.

For detailed ASG structure verification, see test_command_analysis.py.
For MUMPSParser API tests, see test_parser.py.
"""

import pytest
from m2py.parser import MUMPSParser
from m2py.asg import MRoutine


class TestSetStatementGrammar:
    """Test SET command parsing (T028)."""
    
    def test_simple_set(self):
        """SET with single variable and literal value."""
        parser = MUMPSParser()
        source = "LABEL\tS X=1\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        # Grammar captures the line with SET
        assert len(routine.labels) == 1
        # TODO: Verify SET statement in ASG once grammar expanded
    
    def test_set_abbreviated(self):
        """S abbreviation should work same as SET."""
        parser = MUMPSParser()
        source = "LABEL\tS Y=2\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_set_multiple_targets(self):
        """SET with multiple comma-separated targets."""
        parser = MUMPSParser()
        source = "LABEL\tS A=1,B=2,C=3\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_set_string_value(self):
        """SET with quoted string value."""
        parser = MUMPSParser()
        source = 'LABEL\tS MSG="Hello"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestWriteStatementGrammar:
    """Test WRITE command parsing (T029)."""
    
    def test_simple_write(self):
        """WRITE with single string argument."""
        parser = MUMPSParser()
        source = 'LABEL\tW "Hello"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_write_abbreviated(self):
        """W abbreviation should work same as WRITE."""
        parser = MUMPSParser()
        source = "LABEL\tW !!\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_write_format_codes(self):
        """WRITE with format codes (!, #, ?n)."""
        parser = MUMPSParser()
        source = 'LABEL\tW !!,"Test",!\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_write_variable(self):
        """WRITE with variable reference."""
        parser = MUMPSParser()
        source = "LABEL\tW X\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestBoundedForGrammar:
    """Test bounded FOR command parsing (T030)."""
    
    def test_bounded_for_simple(self):
        """FOR var=start:step:end basic form."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1:1:10 W I\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_for_abbreviated(self):
        """F abbreviation should work same as FOR."""
        parser = MUMPSParser()
        source = "LABEL\tF J=0:1:5 W J\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_bounded_for_expression(self):
        """FOR with expressions in bounds."""
        parser = MUMPSParser()
        source = "LABEL\tF K=N:1:M W K\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_bounded_for_negative_step(self):
        """FOR with negative step (countdown)."""
        parser = MUMPSParser()
        source = "LABEL\tF L=10:-1:1 W L\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestSimpleIfGrammar:
    """Test simple IF command parsing (T031)."""
    
    def test_simple_if(self):
        """IF with single condition."""
        parser = MUMPSParser()
        source = "LABEL\tI X=1 W X\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_if_abbreviated(self):
        """I abbreviation should work same as IF."""
        parser = MUMPSParser()
        source = "LABEL\tI Y W Y\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_if_comparison(self):
        """IF with comparison operator."""
        parser = MUMPSParser()
        source = 'LABEL\tI A>B W "A is greater"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_if_argumentless(self):
        """IF without explicit condition (uses $T)."""
        parser = MUMPSParser()
        source = "LABEL\tI  W $T\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


# ============================================================================
# Phase 4 Tests (T049-T052): Complex FOR Loop Patterns
# ============================================================================

class TestStringListForGrammar:
    """Test string-list FOR command parsing (T049)."""
    
    def test_string_list_for_simple(self):
        """FOR var="A","B","C" string list form."""
        parser = MUMPSParser()
        source = 'LABEL\tF I="A","B","C" W I\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_string_list_for_numbers(self):
        """FOR with numeric values as list: F I=1,3,5 W I."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1,3,5,7 W I\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_string_list_for_mixed_values(self):
        """FOR with mixed string and numeric values: F I=1,"ABC",3."""
        parser = MUMPSParser()
        source = 'LABEL\tF I=1,3,4,5.5,7,-1,"ABC",-2.3 W I\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_string_list_for_with_expressions(self):
        """FOR with expression values: F I=$D(X),$L(Y)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=$D(X),$L(Y),Z+1 W I\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestOpenEndedForGrammar:
    """Test open-ended FOR command parsing (T050)."""
    
    def test_open_ended_for_simple(self):
        """FOR var=start:step without end (F I=1:1)."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1:1 W I Q:I>10\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_open_ended_for_decimal_step(self):
        """FOR with decimal step: F I=.1:-.02."""
        parser = MUMPSParser()
        source = "LABEL\tF I=.1:-.02 W I Q:I<0\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_open_ended_for_expression_step(self):
        """FOR with expression as step: F I=X:Y."""
        parser = MUMPSParser()
        source = "LABEL\tF I=X:Y S X=X+1 Q:I>100\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestMixedForGrammar:
    """Test mixed FOR command parsing (T051)."""
    
    def test_mixed_for_values_and_range(self):
        """FOR with mixed values and range: F I="A",1:1:3."""
        parser = MUMPSParser()
        source = 'LABEL\tF I="A",1:1:3 W I\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_mixed_for_complex(self):
        """FOR with complex mixture: F I=-10.1,3*I,"ABC",2:-0.5:1."""
        parser = MUMPSParser()
        source = 'LABEL\tF I=-10.1,3*I,"ABC",2:-0.5:1,"1E0",5:2.5 W I\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_mixed_for_ranges_only(self):
        """FOR with multiple ranges: F I=1:1:3,5:2:10."""
        parser = MUMPSParser()
        source = "LABEL\tF I=1.5:0.1:2.1,1:-0.3:-1 W I\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_mixed_for_open_ranges(self):
        """FOR with open and closed ranges: F I=.1:-.02,1:2."""
        parser = MUMPSParser()
        source = "LABEL\tF I=.1:-.02,1:2 W I Q:I<0\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestArgumentlessForGrammar:
    """Test argumentless FOR command parsing (T052)."""
    
    def test_argumentless_for(self):
        """FOR without arguments (infinite loop): F  W X Q:Y."""
        parser = MUMPSParser()
        source = 'LABEL\tF  W "loop" Q:X>10\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_argumentless_for_with_read(self):
        """Argumentless FOR with READ command: F  R X Q:X=""."""
        parser = MUMPSParser()
        source = 'LABEL\tF  R X Q:X=""\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_argumentless_for_with_kill(self):
        """Argumentless FOR with KILL in body."""
        parser = MUMPSParser()
        source = "LABEL\tF  K I S I=1 Q\n"
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


# ============================================================================
# Phase 10 Tests (T317-T321): Special MUMPS Features Grammar Acceptance
# ============================================================================

class TestPatternMatchGrammar:
    """Test pattern match expression parsing (T317)."""
    
    def test_pattern_match_simple(self):
        """Pattern match X?1A.N should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tI X?1A.N W "match"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        assert len(routine.labels) == 1
    
    def test_pattern_match_negated(self):
        """Negated pattern match X'?1N should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tI X\'?1N W "not numeric"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_pattern_match_complex(self):
        """Complex pattern X?1A.ANP should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tI NAME?1U.L W "valid"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_pattern_match_numeric_repcount_exact(self):
        """Pattern with exact repcount X?2N should parse (T576 fix)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=Y?2N\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_pattern_match_numeric_repcount_atleast(self):
        """Pattern with at-least repcount X?2.N should parse (T576 fix)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=Y?2.N\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_pattern_match_numeric_repcount_atmost(self):
        """Pattern with at-most repcount X?.2N should parse (T576 fix)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=Y?.2N\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_pattern_match_numeric_repcount_range(self):
        """Pattern with range repcount X?1.2N should parse (T576 fix)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=Y?1.2N\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_pattern_match_multi_atom_with_repcounts(self):
        """Multi-atom pattern X?2.N.P.2N should parse (T576 fix)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=Y?2.N.P.2N\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestIndirectPatternMatchGrammar:
    """Test indirect pattern match expression parsing (T576)."""
    
    def test_indirect_pattern_match_simple(self):
        """Indirect pattern match X?@PAT should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=Y?@PAT\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_indirect_pattern_match_with_parens(self):
        """Indirect pattern match X?@(PAT) should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=Y?@(PAT)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_indirect_pattern_match_string_literal(self):
        """Indirect pattern match with string literal should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS X="ABC"?@".4AN"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_indirect_pattern_with_concat(self):
        """Indirect pattern followed by concatenation should parse (VV2PAT2 line 155)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X="ABC"?@".4AN"_("12.34"?2.N.P.2N)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestIntrinsicFunctionGrammar:
    """Test intrinsic function parsing (T318-T319)."""
    
    def test_piece_function(self):
        """$PIECE function should parse (T318)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$PIECE(STR,"^",1)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_piece_function_abbreviated(self):
        """$P abbreviation should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$P(STR,",",2)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_select_function(self):
        """$SELECT function should parse (T319)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$SELECT(A=1:B,1:C)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_select_function_abbreviated(self):
        """$S abbreviation should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$S(X>0:"positive",1:"other")\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_length_function(self):
        """$LENGTH function should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS LEN=$LENGTH(STR)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_nested_functions(self):
        """Nested function calls should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$LENGTH($PIECE(STR,"^",1))\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestSpecialVariableGrammar:
    """Test special variable parsing (T320)."""
    
    def test_test_variable(self):
        """$TEST special variable should parse (T320)."""
        parser = MUMPSParser()
        source = 'LABEL\tI $TEST W "true"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_test_abbreviated(self):
        """$T abbreviation should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tI $T W "true"\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_horolog_variable(self):
        """$HOROLOG should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS TIME=$HOROLOG\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_job_variable(self):
        """$JOB should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS PID=$JOB\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestIndirectionGrammar:
    """Test indirection parsing (T321)."""
    
    def test_simple_indirection(self):
        """@variable indirection should parse (T321)."""
        parser = MUMPSParser()
        source = 'LABEL\tS @VAR=1\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_subscripted_indirection(self):
        """@variable(subscripts) should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @VAR@(1,2)=3\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_name_indirection(self):
        """@"varname" string indirection should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @"X"=1\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_do_indirection(self):
        """D @ROUTINE indirection should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tD @ROUTINE\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_goto_indirection(self):
        """G @LABEL indirection should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tG @TARGET\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_name_indirection_single_subscript(self):
        """@X@(1) name indirection with single subscript should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @X@(1)=2\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert stmt.__class__.__name__ == 'MSetStatement'
        # Verify target is an indirection with name_indirection_subscripts
        target = stmt.assignments[0].target
        # Could be 'Indirection' (textX class) or 'MIndirection' (ASG class)
        assert 'Indirection' in target.__class__.__name__
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) == 1
    
    def test_name_indirection_multiple_subscripts(self):
        """@X@(1,2,3) name indirection with multiple subscripts should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @X@(1,2,3)=4\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        target = label.body.statements[0].assignments[0].target
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) == 1
        assert len(target.name_indirection_subscripts[0]) == 3
    
    def test_name_indirection_chained(self):
        """@X@(1)@(2) chained name indirection should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @X@(1)@(2)=3\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        target = label.body.statements[0].assignments[0].target
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) == 2
    
    def test_name_indirection_with_double_indirection(self):
        """@@X@(1) double indirection with name subscripts should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @@X@(1)=2\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_name_indirection_global(self):
        """@^VV@(1) global variable name indirection should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @^VV@(1,2)=3\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
    
    def test_name_indirection_complex_mugj_pattern(self):
        """Complex MUGJ pattern @@X@(1,2)@(5,6) should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tS @@X@(1,2)@(5,6)=1\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestReadFormatControlGrammar:
    """Test READ command with format controls (T405)."""
    
    def test_read_variable_only(self):
        """R variable should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tR ans\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MReadStatement'
    
    def test_read_newline_only(self):
        """R ! (newline only) should parse (T403)."""
        parser = MUMPSParser()
        source = 'LABEL\tR !\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MReadStatement'
    
    def test_read_tab_only(self):
        """R ?10 (column position only) should parse (T404)."""
        parser = MUMPSParser()
        source = 'LABEL\tR ?10\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MReadStatement'
    
    def test_read_format_then_variable(self):
        """R !,?10,ans should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tR !,?10,ans\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MReadStatement'
    
    def test_read_prompt_and_variable(self):
        """R "Prompt: ",ans should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tR "Prompt: ",ans\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
    
    def test_read_complex_format(self):
        """R !,?10,"Prompt: ",ans,! should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tR !,?10,"Prompt: ",ans,!\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MReadStatement'

    def test_read_format_controls_as_asg_nodes(self):
        """READ format controls should be MFormatControl ASG nodes (T533)."""
        from m2py.asg import MFormatControl, FormatControlType, MReadTarget
        parser = MUMPSParser()
        source = 'LABEL\tR !!,"Prompt",ans\n'
        routine = parser.parse(source)
        
        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == 'MReadStatement'
        
        # Should have 4 arguments: !, !, "Prompt", ans
        assert len(read_stmt.arguments) == 4
        
        # First two should be MFormatControl NEWLINE nodes
        assert isinstance(read_stmt.arguments[0], MFormatControl)
        assert read_stmt.arguments[0].control_type == FormatControlType.NEWLINE
        assert isinstance(read_stmt.arguments[1], MFormatControl)
        assert read_stmt.arguments[1].control_type == FormatControlType.NEWLINE
        
        # Third should be StringLiteral (prompt)
        assert read_stmt.arguments[2].__class__.__name__ == 'StringLiteral'
        
        # Fourth should be MReadTarget wrapping the LocalVariable (target)
        assert isinstance(read_stmt.arguments[3], MReadTarget)
        assert read_stmt.arguments[3].variable.__class__.__name__ == 'LocalVariable'
        assert read_stmt.arguments[3].variable.name == 'ans'
        assert read_stmt.arguments[3].is_char_read == False
        assert read_stmt.arguments[3].timeout is None

    def test_read_with_timeout(self):
        """READ with timeout should preserve timeout in MReadTarget (T535)."""
        from m2py.asg import MReadTarget
        parser = MUMPSParser()
        source = 'LABEL\tR X:10\n'
        routine = parser.parse(source)
        
        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == 'MReadStatement'
        assert len(read_stmt.arguments) == 1
        
        # Should be MReadTarget with timeout
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.variable.name == 'X'
        assert target.is_char_read == False
        assert target.timeout is not None
        assert target.timeout.value == 10

    def test_read_char_read(self):
        """READ *VAR should set is_char_read=True in MReadTarget (T536)."""
        from m2py.asg import MReadTarget
        parser = MUMPSParser()
        source = 'LABEL\tR *X\n'
        routine = parser.parse(source)
        
        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == 'MReadStatement'
        assert len(read_stmt.arguments) == 1
        
        # Should be MReadTarget with is_char_read=True
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.variable.name == 'X'
        assert target.is_char_read == True
        assert target.timeout is None

    def test_read_char_read_with_timeout(self):
        """READ *VAR:timeout should preserve both flags (T535/T536)."""
        from m2py.asg import MReadTarget
        parser = MUMPSParser()
        source = 'LABEL\tR *X:0\n'
        routine = parser.parse(source)
        
        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == 'MReadStatement'
        assert len(read_stmt.arguments) == 1
        
        # Should be MReadTarget with is_char_read=True AND timeout
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.variable.name == 'X'
        assert target.is_char_read == True
        assert target.timeout is not None
        assert target.timeout.value == 0

    def test_read_negative_timeout(self):
        """READ X:-1 should preserve negative timeout (V1READB1 tests)."""
        from m2py.asg import MReadTarget
        parser = MUMPSParser()
        source = 'LABEL\tR X:-1\n'
        routine = parser.parse(source)
        
        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == 'MReadStatement'
        
        target = read_stmt.arguments[0]
        assert isinstance(target, MReadTarget)
        assert target.timeout is not None
        # Negative number is MUnaryOp('-', NumericLiteral(1))
        assert target.timeout.__class__.__name__ == 'MUnaryOp'
        assert target.timeout.operator == '-'
        assert target.timeout.operand.value == 1

    def test_read_multiple_char_reads(self):
        """READ *A,*B,*C should handle multiple char reads (V1READA2 test 758)."""
        from m2py.asg import MReadTarget
        parser = MUMPSParser()
        source = 'LABEL\tR *A,*B,*C\n'
        routine = parser.parse(source)
        
        label = routine.labels[0]
        read_stmt = label.body.statements[0]
        assert read_stmt.__class__.__name__ == 'MReadStatement'
        assert len(read_stmt.arguments) == 3
        
        for i, name in enumerate(['A', 'B', 'C']):
            target = read_stmt.arguments[i]
            assert isinstance(target, MReadTarget)
            assert target.variable.name == name
            assert target.is_char_read == True


class TestOpenDeviceParametersGrammar:
    """Test OPEN command with device parameters (T409)."""
    
    def test_open_simple(self):
        """O device should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tO DEV\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MOpenStatement'
    
    def test_open_with_timeout(self):
        """O device:timeout should parse (T407)."""
        parser = MUMPSParser()
        source = 'LABEL\tO DEV:10\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MOpenStatement'
    
    def test_open_with_params(self):
        """O device:(params) should parse (T408)."""
        parser = MUMPSParser()
        source = 'LABEL\tO DEV:(1)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MOpenStatement'
    
    def test_open_with_multiple_params(self):
        """O device:(param:param:param) should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tO DEV:("AVL4":0:2048)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MOpenStatement'
    
    def test_open_with_params_and_timeout(self):
        """O device:(params):timeout should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tO DEV:("RW"):30\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1


class TestNotContainsOperatorGrammar:
    """Test 'not contains' operator '[ (T403 related)."""
    
    def test_not_contains_variables(self):
        """X'[Y should parse as not-contains binary op."""
        parser = MUMPSParser()
        source = 'LABEL\tI X\'[Y\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MIfStatement'
    
    def test_not_contains_string(self):
        """'"12345678"'[ans should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tI "12345678"\'[ans\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)


class TestDoIndirectionGrammar:
    """Test DO with various indirection forms (T411-T413)."""
    
    def test_do_indirect_variable(self):
        """D @VAR should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tD @ROUTINE\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MDoStatement'
    
    def test_do_indirect_expression(self):
        """D @(expr) should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tD @(X)\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MDoStatement'
    
    def test_do_indirect_complex_expression(self):
        """D @($P($T(X),";",2)) should parse."""
        parser = MUMPSParser()
        source = 'LABEL\tD @($P($T(X),";",2))\n'
        routine = parser.parse(source)
        
        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == 'MDoStatement'
