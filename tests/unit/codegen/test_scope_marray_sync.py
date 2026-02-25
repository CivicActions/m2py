"""Tests for MArray preservation in scope-to-state sync after DO calls.

When a MUMPS variable has subscripts (e.g., IO with IO(0)), the codegen
must preserve the MArray object through scope-to-state synchronization
after DO calls.  Previously, the codegen always extracted ``.value`` from
MArray variables, flattening them to plain strings and losing subscript
data.  This caused ``$DATA(IO(0))`` to crash with
``'str' object has no attribute '_children'``.

Fix: ``emit_scope_var_to_state()`` in statements.py now checks
``ctx.array_vars`` to decide whether to preserve the full MArray
(for subscripted variables) or extract ``.value`` (for simple variables).
"""

from __future__ import annotations

import pytest


@pytest.mark.codegen
class TestMArrayScopeSync:
    """Verify subscripted variables survive DO calls across routines."""

    def test_subscripted_var_preserved_after_do(self, execute_mumps):
        """A subscripted variable set before DO is accessible after DO returns.

        MUMPS: Set X(1)="hello", DO a subroutine that doesn't touch X,
        then $DATA(X(1)) should still be 1 (data exists, no children).
        """
        source = """\
TEST S X(1)="hello" D SUB W $D(X(1))," ",X(1) Q
SUB W "" Q"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "1 hello"

    def test_subscripted_var_survives_cross_routine_do(self, execute_mumps):
        """Subscripted variable accessible after DO ^ROUTINE call.

        When the called routine runs in its own scope context, the
        array variable must be synced back as an MArray, not flattened.
        """
        source = """\
TEST S IO="device",IO(0)="term" D SUB W $D(IO(0))," ",$D(IO)," ",IO(0) Q
SUB W "" Q"""
        result = execute_mumps(source)
        assert result.success is True
        # $D(IO(0))=1, $D(IO)=11 (has value and children), IO(0)="term"
        assert result.output == "1 11 term"

    def test_simple_var_value_extracted_after_do(self, execute_mumps):
        """A simple (non-subscripted) variable works normally after DO.

        Simple variables should still have their .value extracted
        (backwards compatibility).
        """
        source = """\
TEST S X="hello" D SUB W X Q
SUB S Y=1 Q"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "hello"

    def test_data_on_array_root_after_do(self, execute_mumps):
        """$DATA on root of array variable returns 11 after DO call.

        After DO, IO should still be an MArray with both a value and
        children, so $DATA returns 11.
        """
        source = """\
TEST S IO="main",IO(0)="sub0",IO(1)="sub1" D SUB W $D(IO) Q
SUB Q"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "11"

    def test_mixed_vars_after_do(self, execute_mumps):
        """Both simple and subscripted variables correct after DO.

        Tests that scope sync handles a mix of simple and subscripted
        variables correctly in the same routine.
        """
        source = """\
TEST S A="simple",B(1)="arr1",B(2)="arr2" D SUB W A," ",$D(B(1))," ",B(2) Q
SUB Q"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "simple 1 arr2"

    def test_subroutine_modifies_subscripted_var(self, execute_mumps):
        """Subscripted variable modified by subroutine is visible after return.

        When a NEW-less subroutine modifies a subscripted variable,
        the changes should propagate back through scope sync.
        """
        source = """\
TEST S X(1)="before" D SUB W X(1) Q
SUB S X(1)="after" Q"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "after"
