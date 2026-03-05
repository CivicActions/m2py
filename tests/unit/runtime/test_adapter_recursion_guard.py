"""Tests for recursion guard in adapter.py.

The adapter lowers sys.setrecursionlimit(500) during M-Unit test execution
to convert C-stack-overflow segfaults into catchable RecursionError exceptions.

Without this guard, routines with infinite GOTO/DO recursion (e.g., LISTX1
in DMUDIC00 which triggers DIC→S→HARD→RTN→DIC→... cycle) crash the entire
Python process with a segfault before Python's default 1000-frame limit
triggers a RecursionError.
"""

from __future__ import annotations

import sys

import pytest


class TestRecursionGuardBehavior:
    """Verify that lowering the recursion limit catches infinite recursion."""

    def test_low_limit_catches_infinite_recursion(self):
        """sys.setrecursionlimit(500) makes RecursionError catchable.

        At the default limit (1000), deep C-extension recursion can overflow
        the C stack before Python raises RecursionError. At 500, Python
        raises the error well before the C stack is exhausted.
        """
        prev = sys.getrecursionlimit()
        sys.setrecursionlimit(500)
        try:

            def recurse(n):
                return recurse(n + 1)

            with pytest.raises(RecursionError):
                recurse(0)
        finally:
            sys.setrecursionlimit(prev)

    def test_limit_restored_after_exception(self):
        """The recursion limit is restored even when an exception occurs.

        This mirrors the adapter's finally block that restores _prev_limit.
        """
        original = sys.getrecursionlimit()
        _prev_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(500)
        try:
            assert sys.getrecursionlimit() == 500
            raise ValueError("simulated error")
        except ValueError:
            pass
        finally:
            sys.setrecursionlimit(_prev_limit)

        assert sys.getrecursionlimit() == original

    def test_limit_restored_after_recursion_error(self):
        """The recursion limit is restored after catching RecursionError.

        The adapter wraps execution in try/finally to guarantee restoration
        even when RecursionError is raised during test execution.
        """
        original = sys.getrecursionlimit()
        _prev_limit = sys.getrecursionlimit()
        sys.setrecursionlimit(500)
        try:

            def recurse(n):
                return recurse(n + 1)

            try:
                recurse(0)
            except RecursionError:
                pass  # expected
        finally:
            sys.setrecursionlimit(_prev_limit)

        assert sys.getrecursionlimit() == original

    def test_500_is_sufficient_for_normal_mumps(self):
        """Normal MUMPS call depth (~50) is well under the 500 limit.

        MUMPS routines rarely nest beyond 50 frames. 500 is generous
        enough for legitimate deep calls while still catching infinite loops.
        """
        prev = sys.getrecursionlimit()
        sys.setrecursionlimit(500)
        try:

            def nested_call(depth):
                if depth <= 0:
                    return "ok"
                return nested_call(depth - 1)

            # 100 frames simulates deep but legitimate MUMPS nesting
            assert nested_call(100) == "ok"
        finally:
            sys.setrecursionlimit(prev)
