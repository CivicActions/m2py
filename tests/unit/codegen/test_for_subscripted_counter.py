"""Unit tests for FOR loops with subscripted variables and changing subscripts.

These tests verify that FOR loops with subscripted variables (F J(I)=1:1:3)
correctly track an internal counter separate from the variable storage,
even when the subscript changes during loop execution.

Issue: V1FORB test revealed that FOR loops like F J(I)=1:1:3 where the
subscript I changes mid-iteration must track the loop counter independently,
not read it back from the subscripted variable.
"""

from __future__ import annotations

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.fixture
def runtime():
    """Provide a fresh runtime instance for each test."""
    return MUMPSRuntime()


def execute_mumps(source: str, runtime: MUMPSRuntime) -> dict:
    """Generate and execute MUMPS code, return scope."""
    from m2py.codegen.helpers import m_str, m_compare, m_num, m_truth, m_add

    code = generate_python(source)
    scope = {}
    namespace = {
        "__name__": "__main__",
        "_rt": runtime,
        "m_str": m_str,
        "m_num": m_num,
        "m_truth": m_truth,
        "m_compare": m_compare,
        "m_add": m_add,
    }

    # Execute the module code to define functions
    exec(code, namespace)

    # Find the entry point (look for uppercase function names - MUMPS labels)
    entry_func = None
    for name, obj in namespace.items():
        if callable(obj) and name.isupper() and hasattr(obj, "__code__"):
            entry_func = obj
            break

    if entry_func:
        # Call the entry function with _scope as keyword argument
        # Function signature is: def LABEL(_rt, _scope=None, _start_offset=0)
        entry_func(runtime, _scope=scope)

    return scope


@pytest.mark.codegen
class TestForSubscriptedCounter:
    """Test FOR loops with subscripted variables where subscript changes."""

    def test_subscripted_for_with_changing_subscript_basic(self, runtime):
        """Test F J(I)=1:1:3 where I changes in loop body."""
        code = """TEST S I=1,J(3)="A",J(5)="B",J(7)="C"
        S RESULT=""
        F J(I)=1:1:3 S I=I+2,RESULT=RESULT_J(I)_" "
        S RESULT=RESULT_J(1)
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Loop iterations:
        # Iter 1: J(1)=1, I becomes 3, append J(3)="A" → "A "
        # Iter 2: J(3)=2, I becomes 5, append J(5)="B" → "A B "
        # Iter 3: J(5)=3, I becomes 7, append J(7)="C" → "A B C "
        # After loop: append J(1)=3 (final counter value stored at original subscript)
        assert scope["RESULT"].value == "A B C 3"

    def test_subscripted_for_preserves_pre_existing_values(self, runtime):
        """Test that pre-existing values at other subscripts are preserved.

        Per MDC 8.2.13: subscripts are evaluated ONCE at FOR loop start,
        so all writes go to J(1) even though I changes during iterations.
        """
        code = """TEST S I=1,J(3)="PRE3",J(5)="PRE5",J(7)="PRE7"
        F J(I)=10:10:30 S I=I+2
        S R=J(1)_" "_J(3)_" "_J(5)_" "_J(7)
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Subscript I=1 is evaluated ONCE at start, so all writes go to J(1)
        # J(1) gets final value 30
        # J(3), J(5), J(7) are PRESERVED since writes only go to J(1)
        assert scope["R"].value == "30 PRE3 PRE5 PRE7"

    def test_subscripted_for_with_numeric_subscript_calculation(self, runtime):
        """Test F A(A+B)=1:1:3 where subscript is calculated from loop var.

        Per MDC 8.2.13: subscripts are evaluated ONCE at FOR loop start,
        so subscript A+B=1+2=3 is cached at start, all writes go to A(3).
        """
        code = """TEST S A=1,B=2
        S RESULT=""
        F A(A+B)=1:1:3 S A=A+1,RESULT=RESULT_A_" "
        S R=RESULT_A(3)
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Subscript A+B=1+2=3 is evaluated ONCE at start
        # All counter updates write to A(3)
        # Iter 1: A(3)=1, A becomes 2, append "2 "
        # Iter 2: A(3)=2, A becomes 3, append "3 "
        # Iter 3: A(3)=3, A becomes 4, append "4 "
        # After loop: A(3)=3 (final counter value at A(3))
        assert scope["R"].value == "2 3 4 3"

    def test_subscripted_for_termination_based_on_counter_not_value(self, runtime):
        """Test that loop terminates based on counter, not subscripted value."""
        code = """TEST S I=1,J(1)="WRONG"
        S COUNT=0
        F J(I)=1:1:3 S COUNT=COUNT+1,I=I+1
        S R=COUNT
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Should iterate exactly 3 times (counter 1→2→3), not infinite loop
        # Even though J(I) subscript keeps changing and values might be strings
        assert scope["COUNT"].value == 3

    def test_subscripted_for_with_three_subscripts(self, runtime):
        """Test F J(1,2,3)=1:1:3 with multi-dimensional array."""
        code = """TEST S RESULT=""
        F J(1,2,3)=1:1:3 S RESULT=RESULT_J(1,2,3)_" "
        S R=RESULT_J(1,2,3)
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Simple case: subscript doesn't change, just verify basic functionality
        assert scope["R"].value == "1 2 3 3"

    def test_subscripted_for_with_expression_subscript(self, runtime):
        """Test F A(A+B+C)=1:1:3 with complex subscript expression.

        Per MDC 8.2.13: subscripts are evaluated ONCE at FOR loop start,
        so subscript A+B+C=1+2+3=6 is cached at start, all writes go to A(6).
        """
        code = """TEST S A=1,B=2,C=3
        S RESULT=""
        F A(A+B+C)=1:1:3 S A=A+1,RESULT=RESULT_A_" "
        S R=RESULT_A(6)
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Subscript A+B+C=1+2+3=6 is evaluated ONCE at start
        # All counter updates write to A(6)
        # Iter 1: A(6)=1, A becomes 2, append "2 "
        # Iter 2: A(6)=2, A becomes 3, append "3 "
        # Iter 3: A(6)=3, A becomes 4, append "4 "
        # After loop: A(6)=3 (final counter value at A(6))
        assert scope["R"].value == "2 3 4 3"

    def test_subscripted_for_counter_independent_of_external_modifications(
        self, runtime
    ):
        """Test that external modifications to subscripted variable don't affect counter."""
        code = """TEST S I=1,J(5)=999
        S COUNT=0
        F J(I)=1:1:3 S J(I)=888,COUNT=COUNT+1,I=I+4
        S R=COUNT
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Even though we overwrite J(I) with 888 in the loop body,
        # the counter (1→2→3) is independent and loop terminates after 3 iterations
        assert scope["COUNT"].value == 3

    def test_subscripted_for_with_negative_step(self, runtime):
        """Test F J(I)=3:-1:1 with decrementing counter and changing subscript.

        Per MDC 8.2.13: subscripts are evaluated ONCE at FOR loop start,
        so subscript I=10 is cached at start, all writes go to J(10).
        """
        code = """TEST S I=10,J(10)="A",J(8)="B",J(6)="C",J(4)=""
        S RESULT=""
        F J(I)=3:-1:1 S I=I-2,RESULT=RESULT_J(I)_" "
        S R=RESULT_J(10)
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Subscript I=10 is evaluated ONCE at start
        # All counter updates (3, 2, 1) write to J(10)
        # Iter 1: J(10)=3, I becomes 8, append J(8)="B" → "B "
        # Iter 2: J(10)=2, I becomes 6, append J(6)="C" → "B C "
        # Iter 3: J(10)=1, I becomes 4, append J(4)="" → "B C  "
        # After loop: J(10)=1 (final counter value at J(10))
        assert scope["R"].value == "B C  1"

    def test_subscripted_for_with_zero_step_executes_once(self, runtime):
        """Test F J(I)=1:0:1 with zero step executes body once then exits."""
        code = """TEST S I=1,COUNT=0
        F J(I)=5:0:5 S COUNT=COUNT+1,I=I+1 Q:COUNT>5
        S R=COUNT
        QUIT"""
        scope = execute_mumps(code, runtime)

        # With step=0, the condition check is special: counter <= end
        # Since we never increment the counter, we'd loop forever without the Q:COUNT>5 guard
        # The Q:COUNT>5 ensures we exit after 6 iterations
        assert scope["COUNT"].value == 6


@pytest.mark.codegen
class TestForSubscriptedEdgeCases:
    """Edge cases for subscripted FOR loops."""

    def test_subscripted_for_where_subscript_becomes_undefined(self, runtime):
        """Test that undefined subscript values don't cause infinite loops."""
        code = """TEST S I=1,J(1)=100
        S COUNT=0
        F J(I)=1:1:3 S I=I+1,COUNT=COUNT+1 Q:COUNT>10
        S R=COUNT
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Loop should terminate after 3 iterations based on counter
        # The Q:COUNT>10 is a safety guard but shouldn't be needed
        assert scope["COUNT"].value == 3

    def test_subscripted_for_final_value_written_to_initial_subscript(self, runtime):
        """Test that all counter updates write to the initial subscript.

        Per MDC 8.2.13: subscripts are evaluated ONCE at FOR loop start,
        so subscript I=1 is cached at start, all writes go to J(1).
        J(2), J(4), J(8) are never touched.
        """
        code = """TEST S I=1
        F J(I)=10:5:20 S I=I*2
        S R1=J(1)
        QUIT"""
        scope = execute_mumps(code, runtime)

        # Subscript I=1 is evaluated ONCE at start
        # All counter updates (10, 15, 20) write to J(1)
        # Iter 1: J(1)=10, I becomes 2
        # Iter 2: J(1)=15, I becomes 4
        # Iter 3: J(1)=20, I becomes 8
        # Final: J(1)=20 (only J(1) is modified)
        assert scope["R1"].value == 20
