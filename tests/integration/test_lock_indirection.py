"""Integration tests for LOCK indirection.

Spec 021-correctness-features Phase 6 Task T113:
Integration tests that transpile LOCK indirection routines and verify
end-to-end functionality.

These tests verify that:
1. LOCK @X resolves the indirected name correctly
2. Locks are actually acquired/released
3. $TEST is set correctly for timed locks
4. Multi-level indirection works (@@A)
5. Subscript indirection works (@A@(subs))
"""

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


class TestLockIndirectionIntegration:
    """Integration tests for LOCK indirection end-to-end."""

    def _run_routine(self, mumps_code: str) -> tuple[MUMPSRuntime, str]:
        """Transpile and execute MUMPS code, return runtime and output."""
        python_code = generate_python(mumps_code)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=True)
        return runtime, result.output

    def test_lock_indirection_basic(self):
        """L +@X where X="^GLO" acquires lock on ^GLO."""
        mumps = """TEST
 S X="^GLO"
 L +@X
 Q
"""
        rt, output = self._run_routine(mumps)

        # Verify lock was acquired
        assert ("GLO", ()) in rt.globals._lock_table

    def test_lock_indirection_release(self):
        """L -@X releases the lock."""
        mumps = """TEST
 S X="^GLO"
 L +@X
 L -@X
 Q
"""
        rt, output = self._run_routine(mumps)

        # Lock should be released
        assert ("GLO", ()) not in rt.globals._lock_table

    def test_lock_indirection_with_subscripts_in_value(self):
        """L +@X where X="^GLO(1,2)" locks ^GLO(1,2)."""
        mumps = """TEST
 S X="^GLO(1,2)"
 L +@X
 Q
"""
        rt, output = self._run_routine(mumps)

        assert ("GLO", ("1", "2")) in rt.globals._lock_table

    def test_lock_indirection_timeout_success(self):
        """L +@X:0 sets $TEST=1 on success."""
        mumps = """TEST
 S X="^AVAIL"
 L +@X:0
 Q
"""
        rt, output = self._run_routine(mumps)

        # Lock acquired, $TEST should be 1
        assert rt._test is True
        assert ("AVAIL", ()) in rt.globals._lock_table

    def test_lock_multi_level_indirection(self):
        """L +@@A where A="B", B="^DEEP" locks ^DEEP."""
        mumps = """TEST
 S A="B"
 S B="^DEEP"
 L +@@A
 Q
"""
        rt, output = self._run_routine(mumps)

        assert ("DEEP", ()) in rt.globals._lock_table

    def test_lock_indirection_exclusive_releases_all(self):
        """L @X (exclusive) releases existing locks first."""
        mumps = """TEST
 L +^OLD
 S X="^NEW"
 L @X
 Q
"""
        rt, output = self._run_routine(mumps)

        # OLD should be released, NEW should be acquired
        assert ("OLD", ()) not in rt.globals._lock_table
        assert ("NEW", ()) in rt.globals._lock_table

    def test_lock_indirection_local_name(self):
        """L +@X where X="LOCALVAR" locks local variable name."""
        mumps = """TEST
 S X="LOCALVAR"
 L +@X
 Q
"""
        rt, output = self._run_routine(mumps)

        assert ("LOCALVAR", ()) in rt.globals._lock_table

    def test_lock_indirection_from_global_source(self):
        """L +@^CFG("LOCK") where ^CFG("LOCK")="^DATA" locks ^DATA."""
        mumps = """TEST
 S ^CFG("LOCK")="^DATA"
 L +@^CFG("LOCK")
 Q
"""
        rt, output = self._run_routine(mumps)

        assert ("DATA", ()) in rt.globals._lock_table


class TestLockIndirectionSubscriptMerging:
    """Tests for @A@(subs) subscript indirection in LOCK."""

    def _run_routine(self, mumps_code: str) -> tuple[MUMPSRuntime, str]:
        """Transpile and execute MUMPS code."""
        python_code = generate_python(mumps_code)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=True)
        return runtime, result.output

    def test_subscript_indirection_appends(self):
        """L +@A@(1) where A="^GLO" locks ^GLO(1)."""
        mumps = """TEST
 S A="^GLO"
 L +@A@(1)
 Q
"""
        rt, output = self._run_routine(mumps)

        assert ("GLO", ("1",)) in rt.globals._lock_table

    def test_subscript_indirection_merges(self):
        """L +@A@(3) where A="^GLO(1,2)" locks ^GLO(1,2,3)."""
        mumps = """TEST
 S A="^GLO(1,2)"
 L +@A@(3)
 Q
"""
        rt, output = self._run_routine(mumps)

        assert ("GLO", ("1", "2", "3")) in rt.globals._lock_table


class TestLockIndirectionTestVariable:
    """Tests for $TEST behavior with LOCK indirection."""

    def _run_routine(self, mumps_code: str) -> tuple[MUMPSRuntime, str]:
        """Transpile and execute MUMPS code."""
        python_code = generate_python(mumps_code)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=True)
        return runtime, result.output

    def test_untimed_lock_preserves_test(self):
        """L +@X (no timeout) does NOT change $TEST from a prior timed lock."""
        # First set up $TEST to false via a failing IF, then untimed lock shouldn't change it
        mumps = """TEST
 I 0 ; sets $TEST=0
 S X="^GLO"
 L +@X
 Q
"""
        rt, output = self._run_routine(mumps)

        # $TEST should still be 0 (unchanged by untimed lock)
        assert rt._test is False

    def test_timed_lock_success_sets_test_true(self):
        """L +@X:0 sets $TEST=1 on immediate success."""
        mumps = """TEST
 I 0 ; sets $TEST=0
 S X="^GLO"
 L +@X:0
 Q
"""
        rt, output = self._run_routine(mumps)

        # $TEST should be 1 (success)
        assert rt._test is True

    def test_timed_unlock_sets_test_true(self):
        """L -@X:0 always sets $TEST=1 (unlock never fails)."""
        mumps = """TEST
 I 0 ; sets $TEST=0
 S X="^GLO"
 L +@X
 L -@X:0
 Q
"""
        rt, output = self._run_routine(mumps)

        # $TEST should be 1 (unlock always succeeds)
        assert rt._test is True
