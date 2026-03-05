"""Test that MUMPSRuntime raises the Python recursion limit.

MUMPS has no recursion limit — deep DO/XECUTE nesting is normal
(e.g., DICOMP evaluating computed fields).  Python's default limit
of 1000 is too low.  The runtime raises it to at least 10,000.
"""

import sys


from m2py.runtime import MUMPSRuntime


class TestRecursionLimit:
    """MUMPSRuntime.__init__ raises sys.getrecursionlimit()."""

    def test_recursion_limit_at_least_10000(self):
        """After creating a runtime, recursion limit is >= 10000."""
        _rt = MUMPSRuntime()
        assert sys.getrecursionlimit() >= 10_000
        _rt.cleanup()

    def test_recursion_limit_not_lowered(self):
        """If recursion limit is already higher, it stays higher."""
        original = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(20_000)
            _rt = MUMPSRuntime()
            assert sys.getrecursionlimit() == 20_000
            _rt.cleanup()
        finally:
            sys.setrecursionlimit(original)

    def test_recursion_limit_raised_from_default(self):
        """If recursion limit is at Python default (1000), it gets raised."""
        original = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(1000)
            _rt = MUMPSRuntime()
            assert sys.getrecursionlimit() >= 10_000
            _rt.cleanup()
        finally:
            sys.setrecursionlimit(original)
