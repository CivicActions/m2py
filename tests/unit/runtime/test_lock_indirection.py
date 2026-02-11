"""Unit tests for LOCK indirection runtime support.

Spec 021-correctness-features Phase 6 Task T036:
Tests for lock_indirected() runtime method.

LOCK indirection (@X) resolves the indirected name and acquires/releases
the lock instead of silently skipping. Tests cover:
- Basic name resolution for single-level indirection
- Multi-level indirection (@@A where A="B", B="^GLO")
- Timeout with $TEST update
- Incremental lock (+) and unlock (-) forms
- Subscript indirection (@A@(1,2))
"""

import pytest

from m2py.runtime import MUMPSRuntime, MArray


class TestLockIndirectedBasic:
    """Tests for basic lock indirection resolution."""

    def test_single_level_local_lock(self):
        """L +@X where X="GLO" acquires lock on GLO."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("GLO")}

        # Should resolve X to "GLO" and lock it
        rt.lock_indirected("X", scope, lockop="+")

        # Verify lock was acquired
        assert ("GLO", ()) in rt.globals._lock_table

    def test_single_level_global_lock(self):
        """L +@X where X="^PATIENT(1)" acquires lock on ^PATIENT(1)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^PATIENT(1)")}

        rt.lock_indirected("X", scope, lockop="+")

        # Should parse "^PATIENT(1)" and lock PATIENT with subscript 1
        assert ("PATIENT", ("1",)) in rt.globals._lock_table

    def test_single_level_global_subscripted(self):
        """L +@X where X="^GLO(1,2)" acquires lock on ^GLO(1,2)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^GLO(1,2)")}

        rt.lock_indirected("X", scope, lockop="+")

        assert ("GLO", ("1", "2")) in rt.globals._lock_table

    def test_unlock_single_level(self):
        """L -@X releases the lock."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^TEST")}

        # First acquire
        rt.lock_indirected("X", scope, lockop="+")
        assert ("TEST", ()) in rt.globals._lock_table

        # Then release
        rt.lock_indirected("X", scope, lockop="-")
        assert ("TEST", ()) not in rt.globals._lock_table

    def test_exclusive_lock_releases_first(self):
        """L @X (no + or -) releases all then acquires."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^NEW")}

        # Pre-acquire a different lock
        rt.globals.lock("OLD", (), lock_type="+")
        assert ("OLD", ()) in rt.globals._lock_table

        # Exclusive lock (no +/-) should release all first
        rt.lock_indirected("X", scope, lockop="")

        # OLD should be released, NEW should be acquired
        assert ("OLD", ()) not in rt.globals._lock_table
        assert ("NEW", ()) in rt.globals._lock_table


class TestLockIndirectedMultiLevel:
    """Tests for multi-level indirection (@@A)."""

    def test_two_level_indirection(self):
        """L +@@A where A="B", B="^GLO" locks ^GLO."""
        rt = MUMPSRuntime()
        scope = {
            "A": MArray("B"),
            "B": MArray("^GLO"),
        }

        rt.lock_indirected("A", scope, lockop="+", levels=2)

        assert ("GLO", ()) in rt.globals._lock_table

    def test_three_level_indirection(self):
        """L +@@@A where A="B", B="C", C="^DEEP" locks ^DEEP."""
        rt = MUMPSRuntime()
        scope = {
            "A": MArray("B"),
            "B": MArray("C"),
            "C": MArray("^DEEP"),
        }

        rt.lock_indirected("A", scope, lockop="+", levels=3)

        assert ("DEEP", ()) in rt.globals._lock_table


class TestLockIndirectedTimeout:
    """Tests for lock timeout with $TEST update."""

    def test_lock_timeout_success(self):
        """L +@X:0 sets $TEST=1 on immediate success."""
        rt = MUMPSRuntime()
        rt._test = False  # Reset $TEST
        scope = {"X": MArray("^AVAIL")}

        rt.lock_indirected("X", scope, lockop="+", timeout=0)

        # Lock acquired immediately, $TEST should be 1
        assert rt._test is True
        assert ("AVAIL", ()) in rt.globals._lock_table

    def test_unlock_with_timeout_sets_test(self):
        """L -@X:0 always sets $TEST=1 (unlock never fails)."""
        rt = MUMPSRuntime()
        rt._test = False
        scope = {"X": MArray("^TEST")}

        # Pre-acquire
        rt.globals.lock("TEST", (), lock_type="+")

        # Unlock with timeout
        rt.lock_indirected("X", scope, lockop="-", timeout=0)

        # Unlock always succeeds
        assert rt._test is True

    def test_lock_no_timeout_preserves_test(self):
        """L +@X (no timeout) does NOT modify $TEST."""
        rt = MUMPSRuntime()
        rt._test = False  # Set to False initially
        scope = {"X": MArray("^GLO")}

        rt.lock_indirected("X", scope, lockop="+")

        # $TEST should be unchanged (still False)
        assert rt._test is False


class TestLockIndirectedSubscripts:
    """Tests for subscript indirection @A@(subs)."""

    def test_subscript_indirection_single(self):
        """L +@A@(1) where A="^GLO" locks ^GLO(1)."""
        rt = MUMPSRuntime()
        scope = {"A": MArray("^GLO")}

        rt.lock_indirected("A", scope, lockop="+", per_level_subscripts=[["1"]])

        assert ("GLO", ("1",)) in rt.globals._lock_table

    def test_subscript_indirection_multiple(self):
        """L +@A@(1,2) where A="^GLO" locks ^GLO(1,2)."""
        rt = MUMPSRuntime()
        scope = {"A": MArray("^GLO")}

        rt.lock_indirected("A", scope, lockop="+", per_level_subscripts=[["1", "2"]])

        assert ("GLO", ("1", "2")) in rt.globals._lock_table

    def test_subscript_merges_with_resolved(self):
        """L +@A@(3) where A="^GLO(1,2)" locks ^GLO(1,2,3)."""
        rt = MUMPSRuntime()
        scope = {"A": MArray("^GLO(1,2)")}

        rt.lock_indirected("A", scope, lockop="+", per_level_subscripts=[["3"]])

        assert ("GLO", ("1", "2", "3")) in rt.globals._lock_table


class TestLockIndirectedLocalNames:
    """Tests for local variable lock names (without ^)."""

    def test_local_name_lock(self):
        """L +@X where X="LOCALVAR" locks LOCALVAR."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("LOCALVAR")}

        rt.lock_indirected("X", scope, lockop="+")

        assert ("LOCALVAR", ()) in rt.globals._lock_table

    def test_local_name_with_subscripts(self):
        """L +@X where X="A(1,2)" locks A(1,2)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("A(1,2)")}

        rt.lock_indirected("X", scope, lockop="+")

        assert ("A", ("1", "2")) in rt.globals._lock_table


class TestLockIndirectedGlobalFromExpression:
    """Tests using global reference in indirection source."""

    def test_global_source_variable(self):
        """L +@^CFG("LOCK") where ^CFG("LOCK")="^DATA" locks ^DATA."""
        rt = MUMPSRuntime()
        scope = {}

        # Set up global value
        rt.globals.set("CFG", ("LOCK",), "^DATA")

        rt.lock_indirected('^CFG("LOCK")', scope, lockop="+")

        assert ("DATA", ()) in rt.globals._lock_table
