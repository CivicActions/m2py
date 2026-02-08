"""Tests for $TEST synchronization to runtime (_rt._test = _test).

Verifies that commands which modify $TEST properly sync the value
to _rt._test so it's visible across module boundaries. This is
needed because each routine has a module-level _test variable, but
cross-module calls need the value to be accessible via _rt._test.

Fixed suites: V3DWP (test 31084), V4PRIN (test 40746)
"""

import pytest


@pytest.mark.codegen
class TestTestSyncAfterIf:
    """$TEST is synced to _rt._test after IF evaluates condition."""

    def test_if_syncs_test_to_runtime(self, generate_python):
        """IF generates _rt._test = _test after evaluating condition."""
        code = generate_python("TEST I 1 Q")
        assert "_rt._test = _test" in code

    def test_if_multi_condition_syncs(self, generate_python):
        """Multi-condition IF (I a,b) also syncs $TEST."""
        code = generate_python("TEST I 1,1 Q")
        assert "_rt._test = _test" in code

    def test_if_visible_across_do(self, execute_mumps):
        """$TEST set by IF is visible after DO to external subroutine.

        V3DWP test 31084: IF in called routine affects $TEST in caller.
        """
        result = execute_mumps(
            'TEST\n I 0\n D SUB\n I  W "YES"\n E  W "NO"\n Q\nSUB I 1 Q\n'
        )
        # After SUB sets $TEST=1, caller should see it via _rt._test
        assert result.output == "YES"


@pytest.mark.codegen
class TestTestSyncAfterLock:
    """$TEST is synced to _rt._test after timed LOCK."""

    def test_timed_lock_syncs_test(self, generate_python):
        """LOCK +^X:0 generates _rt._test = _test after lock."""
        code = generate_python("TEST L +^X:0 Q")
        assert "_rt._test = _test" in code

    def test_lock_decrement_timed_syncs(self, generate_python):
        """LOCK -^X:0 generates _rt._test = _test."""
        code = generate_python("TEST L -^X:0 Q")
        assert "_rt._test = _test" in code


@pytest.mark.codegen
class TestTestSyncAfterRead:
    """$TEST is synced to _rt._test after timed READ."""

    def test_timed_read_syncs_test(self, generate_python):
        """READ X:0 generates _rt._test = _test."""
        code = generate_python("TEST R X:0 Q")
        assert "_rt._test = _test" in code


@pytest.mark.codegen
class TestTestSyncAfterOpen:
    """$TEST is synced to _rt._test after timed OPEN."""

    def test_timed_open_syncs_test(self, generate_python):
        """OPEN "file"::0 generates _rt._test = _test."""
        code = generate_python('TEST O "file"::0 Q')
        assert "_rt._test = _test" in code


@pytest.mark.codegen
class TestTestSyncAfterJob:
    """$TEST is synced to _rt._test after timed JOB."""

    def test_timed_job_syncs_test(self, generate_python):
        """JOB label^routine::0 generates _rt._test = _test."""
        code = generate_python("TEST J SUB^ROU::0 Q")
        assert "_rt._test = _test" in code


@pytest.mark.codegen
class TestTestSyncAfterDo:
    """$TEST is synced from _rt._test after DO returns from external call."""

    def test_do_block_syncs_test_after_restore(self, generate_python):
        """DO block restores $TEST then syncs to _rt._test."""
        code = generate_python("TEST D  W 1 Q")
        assert "_rt._test = _test" in code

    def test_external_do_syncs_test_from_runtime(self, generate_python):
        """DO label^routine syncs _test = _rt._test after return.

        This ensures callee's $TEST changes are visible to caller.
        """
        code = generate_python("TEST D SUB^ROU Q")
        assert "_test = _rt._test" in code
