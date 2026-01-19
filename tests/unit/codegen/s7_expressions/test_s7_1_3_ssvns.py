"""Tests for SSVNs code generation (§7.1.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.3

Spec 013 Phase 16 (FR-029): Implements ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE via
database abstraction layer. YDB does not support SSVNs natively, so m2py provides
an in-memory implementation.
"""

import pytest


@pytest.mark.codegen
class TestSsvnsCodegen:
    """Codegen-level tests for structured system variables code generation (§7.1.3)."""

    def test_ssvn_global_exists(self, execute_mumps):
        """^$GLOBAL returns non-empty when global exists (§7.1.3).

        Spec 013 FR-029: Returns "1" for existing globals.
        """
        result = execute_mumps('TEST\n S ^MYTEST=1\n W ^$GLOBAL("MYTEST")\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_ssvn_global_not_exists(self, execute_mumps):
        """^$GLOBAL returns empty when global does not exist (§7.1.3).

        Spec 013 FR-029: Returns "" for non-existent globals.
        """
        result = execute_mumps('TEST\n W ^$GLOBAL("NONEXISTENT")\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_ssvn_job_current(self, execute_mumps):
        """^$JOB returns non-empty for current process (§7.1.3).

        Spec 013 FR-029: Returns "1" when queried with $JOB (current PID).
        """
        result = execute_mumps("TEST\n W ^$JOB($J)\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_ssvn_job_not_exists(self, execute_mumps):
        """^$JOB returns empty for non-existent process (§7.1.3).

        Spec 013 FR-029: Returns "" for non-existent PIDs.
        """
        result = execute_mumps("TEST\n W ^$JOB(99999999)\n Q\n")
        assert result.output == ""
        assert result.success is True

    def test_ssvn_lock_not_held(self, execute_mumps):
        """^$LOCK returns empty when lock not held (§7.1.3).

        Spec 013 FR-029: Returns "" when no lock exists.
        """
        result = execute_mumps('TEST\n W ^$LOCK("TESTLOCK")\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_ssvn_routine(self, execute_mumps):
        """^$ROUTINE returns empty (not implemented) (§7.1.3).

        Spec 013 FR-029: Routine metadata not available in transpiler context.
        """
        result = execute_mumps('TEST\n W ^$ROUTINE("MYROUTINE")\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_ssvn_abbreviation(self, execute_mumps):
        """SSVN names can be abbreviated (§7.1.3).

        Spec 013: ^$G is valid abbreviation for ^$GLOBAL.
        """
        result = execute_mumps('TEST\n S ^X=1\n W ^$G("X")\n Q\n')
        assert result.output == "1"
        assert result.success is True


# Out-of-scope SSVNs - "Parses OK" limitations.
# These parse and analyze correctly but runtime semantics are undefined.
# Parser/ASG tests exist to verify parsing works. No codegen tests needed.
#
# - ^$EVENT, ^$WINDOW, ^$DISPLAY: LIM-003 (MWAPI SSVNs)
# - ^$LIBRARY: LIM-011 (zero real-world usage)
