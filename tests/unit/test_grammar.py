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
