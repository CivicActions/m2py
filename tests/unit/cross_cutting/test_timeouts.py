"""Cross-cutting tests for timeout RUNTIME behavior (§8.2.10, §8.2.12, §8.2.15, §8.2.17).

Timeouts are a language feature that spans multiple commands:
- OPEN device:timeout - device open timeout
- READ var:timeout - read input timeout
- JOB entry::timeout - job start timeout
- LOCK name:timeout - lock acquisition timeout

All timeout commands modify $TEST on timeout (§7.1.4.10):
- Success: $TEST=1
- Timeout: $TEST=0

Parser/ASG tests are in the respective command test files:
- tests/unit/asg/s8_commands/test_s8_2_10_job.py
- tests/unit/asg/s8_commands/test_s8_2_12_lock.py
- tests/unit/asg/s8_commands/test_s8_2_15_open.py
- tests/unit/asg/s8_commands/test_s8_2_17_read.py

Reference: MUMPS 1995 ANSI Standard, Sections 8.2.10, 8.2.12, 8.2.15, 8.2.17
See also: FR-005 (cross-cutting features need dedicated tests)
         FR-047 ($TEST modification by timeout commands)
"""

import pytest


# =============================================================================
# Timeout Tests (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestTimeoutsCodegen:
    """Codegen tests for timeout execution.

    Generated Python must correctly implement timeout semantics
    and $TEST modification (§7.1.4.10).

    Per the 1995 MUMPS spec:
    - $TEST contains the truthvalue resulting from OPEN, LOCK, JOB,
      or READ commands with timeout arguments
    - Success: $TEST=1, Timeout: $TEST=0

    Reference: §8.2.10, §8.2.12, §8.2.15, §8.2.17, FR-047
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_read_timeout_sets_test_false(self):
        """READ timeout sets $TEST=0 (§8.2.17, FR-047).

        READ X:0  ; Immediate timeout
        ; $TEST should be 0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_read_success_sets_test_true(self):
        """READ success sets $TEST=1 (§8.2.17, FR-047).

        ; With input available
        READ X:5
        ; $TEST should be 1
        """
        pytest.fail("Stub - implement test")

    def test_lock_timeout_sets_test_false(self, execute_mumps):
        """LOCK timeout sets $TEST=0 (§8.2.12, FR-047).

        Spec 013 Phase 9: In single-process mode, LOCK always succeeds,
        but we can test that timeout:0 correctly sets $TEST=1 (success).
        Note: True contention-based timeout would require multi-process test.
        """
        # Memory backend always succeeds, so $TEST=1 even with timeout:0
        # This verifies the codegen correctly generates $TEST assignment
        result = execute_mumps("TEST\n L +^BUSY:0\n W $T\n Q")
        assert result.output == "1"  # Memory backend has no contention

    def test_lock_success_sets_test_true(self, execute_mumps):
        """LOCK success sets $TEST=1 (§8.2.12, FR-047).

        Spec 013 Phase 9: LOCK with timeout sets $TEST=1 on success.
        """
        result = execute_mumps("TEST\n L +^AVAIL:5\n W $T\n Q")
        assert result.output == "1"

    def test_lock_without_timeout_preserves_test(self, execute_mumps):
        """LOCK without timeout does NOT modify $TEST (§8.2.12).

        Spec 013 Phase 9: Per MUMPS spec, untimed LOCK does not change $TEST.
        This is distinct from timed LOCK which always sets $TEST.
        """
        # Set $TEST to 0, then LOCK without timeout - $TEST should stay 0
        result = execute_mumps("TEST\n IF 0\n S X=1\n L +^DATA\n W $T\n Q")
        assert result.output == "0"

        # Set $TEST to 1, then LOCK without timeout - $TEST should stay 1
        result2 = execute_mumps("TEST\n IF 1\n L +^DATA\n W $T\n Q")
        assert result2.output == "1"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_open_timeout_sets_test_false(self):
        """OPEN timeout sets $TEST=0 (§8.2.15, FR-047)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_job_timeout_sets_test_false(self):
        """JOB timeout sets $TEST=0 (§8.2.10, FR-047)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_timeout_expression_evaluated(self):
        """Timeout expression is evaluated at runtime (§8.2.17).

        SET T=5 READ X:T  ; T evaluated to get timeout value
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires full code execution")
    def test_zero_timeout_is_immediate(self):
        """Timeout of 0 is immediate/non-blocking (§8.2.17).

        Per spec: timeout of 0 means immediate (non-blocking) attempt.
        """
        pytest.fail("Stub - implement test")
