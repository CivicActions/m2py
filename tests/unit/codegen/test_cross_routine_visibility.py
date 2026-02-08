"""Unit tests for cross-routine variable visibility (T075b).

These tests verify that variables are properly synced between
RoutineState (static or dynamic locals) and _scope dict when:
1. A routine is entered from another routine via DO
2. A routine returns to its caller

The fix ensures that:
- On entry: state is initialized from _scope (variables set by caller are visible)
- On return: _scope is updated from state (changes made are visible to caller)

This applies to both:
- Static state vars (state.VAR pattern for simple routines)
- Dynamic locals (state._locals dict for routines with argumentless KILL/NEW)
"""

import pytest

from m2py.codegen.routine import RoutineGenerator
from m2py.codegen.enums import GotoStrategy
from m2py.parser import MUMPSParser


def parse(code: str):
    """Helper to parse MUMPS code into a routine ASG."""
    parser = MUMPSParser()
    return parser.parse(code)


@pytest.mark.codegen
class TestCrossRoutineVisibilityCodegen:
    """Tests for cross-routine visibility codegen patterns."""

    def test_routine_with_state_vars_generates_state_class(self):
        """Routine with cross-label access creates RoutineState class.

        When variables are accessed across labels (GOTO), they become state vars.
        """
        # X is accessed across labels (set in TEST, GOTOed to NEXT)
        code = """
TEST
 S X=1
 G NEXT
NEXT
 W X
 S Y=2
 Q
"""
        routine = parse(code)
        generator = RoutineGenerator(routine, strategy=GotoStrategy.TRAMPOLINE)
        python_code = generator.generate()

        # Check that RoutineState class is generated
        assert "class RoutineState:" in python_code
        # Entry function should be generated
        assert "def TEST(_rt, _scope=None):" in python_code

    def test_label_functions_set_runtime_context(self):
        """Label functions set runtime context for $TEXT support.

        T075f: Each label entry point should set _rt._current_routine,
        _rt._current_source_lines, and _rt._current_label_lines so that
        $TEXT works correctly when the routine is called externally.
        """
        code = """
TEST
 W "hello"
 Q
SUB
 W "world"
 Q
"""
        routine = parse(code)
        generator = RoutineGenerator(routine, strategy=GotoStrategy.SIMPLE_FUNCTIONS)
        python_code = generator.generate()

        # Should set runtime context in label functions
        assert "_rt._current_routine = _routine_name" in python_code
        assert "_rt._current_source_lines = _source_lines" in python_code
        assert "_rt._current_label_lines = _label_lines" in python_code

    def test_external_do_generates_import(self):
        """D ^ROUTINE generates import statement."""
        code = """
TEST
 D ^OTHER
 Q
"""
        routine = parse(code)
        generator = RoutineGenerator(routine, strategy=GotoStrategy.TRAMPOLINE)
        python_code = generator.generate()

        # Should have import for external routine
        assert "import OTHER" in python_code

    def test_external_do_generates_context_save_restore(self):
        """D ^ROUTINE generates save/restore of runtime context for $TEXT.

        T075f: When calling an external routine, the current routine's
        $TEXT context must be saved and restored so $TEXT(+N) works
        correctly after the call returns.
        """
        code = """
TEST
 D ^OTHER
 Q
"""
        routine = parse(code)
        generator = RoutineGenerator(routine, strategy=GotoStrategy.TRAMPOLINE)
        python_code = generator.generate()

        # Should save context before call
        assert "_saved_routine = _rt._current_routine" in python_code
        assert "_saved_source_lines = _rt._current_source_lines" in python_code
        assert "_saved_label_lines = _rt._current_label_lines" in python_code

        # Should restore context after call
        assert "_rt._current_routine = _saved_routine" in python_code
        assert "_rt._current_source_lines = _saved_source_lines" in python_code
        assert "_rt._current_label_lines = _saved_label_lines" in python_code


@pytest.mark.codegen
class TestCrossRoutineVisibilityExecution:
    """Integration tests for cross-routine visibility at runtime.

    These tests verify the actual behavior works correctly, regardless
    of the specific codegen patterns used to implement it.
    """

    def test_variable_visible_in_called_routine(self, execute_mumps):
        """Variable set by caller is visible in callee via DO.

        S X=1 D SUB → SUB sees X=1
        """
        code = """TEST
 S X=42
 D SUB
 Q
SUB
 W "X=",X
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        assert "X=42" in result.output

    def test_variable_modified_by_callee_visible_to_caller(self, execute_mumps):
        """Variable modified by callee is visible to caller after DO returns.

        D SUB where SUB sets X=99 → caller sees X=99
        """
        code = """TEST
 D SUB
 W "X=",X
 Q
SUB
 S X=99
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        assert "X=99" in result.output

    def test_variable_round_trip_through_subroutine(self, execute_mumps):
        """Variable survives set→call→modify→return→read cycle.

        S X=10 D SUB(adds 5) W X → outputs 15
        """
        code = """TEST
 S X=10
 D SUB
 W X
 Q
SUB
 S X=X+5
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "15"

    def test_multiple_variables_visible_across_call(self, execute_mumps):
        """Multiple variables all visible in callee."""
        code = """TEST
 S A=1,B=2,C=3
 D SUB
 Q
SUB
 W A+B+C
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "6"

    def test_visibility_with_argumentless_kill(self, execute_mumps):
        """Variables visible even when routine has argumentless KILL.

        Argumentless KILL uses dynamic _locals pattern.
        """
        code = """TEST
 K
 S X=100
 D SUB
 W ",Y=",Y
 Q
SUB
 W "X=",X
 S Y=200
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        assert "X=100" in result.output
        assert "Y=200" in result.output

    def test_nested_do_calls_preserve_visibility(self, execute_mumps):
        """Variables visible through multiple levels of DO calls.

        TEST→SUB1→SUB2: X set in TEST visible in SUB2
        """
        code = """TEST
 S X=42
 D SUB1
 Q
SUB1
 D SUB2
 Q
SUB2
 W "X=",X
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        assert "X=42" in result.output

    def test_goto_after_do_preserves_vars(self, execute_mumps):
        """Variables set before DO are preserved after GOTO within routine."""
        code = """TEST
 S X=10
 D SUB
 G END
SUB
 S Y=20
 Q
END
 W "X=",X,",Y=",Y
 Q
"""
        result = execute_mumps(code)
        assert result.success is True
        assert "X=10" in result.output
        assert "Y=20" in result.output
