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

    def test_read_timeout_sets_test(self, generate_python):
        """READ with timeout assigns to $TEST (§8.2.17, FR-047).

        READ X:timeout generates code that assigns _test based on
        success/timeout from m_read_timeout().
        """
        code = generate_python("TEST R X:5 Q")
        # Generated code should call m_read_timeout and set _test
        assert "m_read_timeout" in code
        assert "_test" in code

    def test_read_without_timeout_no_test(self, generate_python):
        """READ without timeout does NOT modify $TEST (§8.2.17).

        Per MUMPS spec: untimed READ does not set $TEST.
        """
        code = generate_python("TEST R X Q")
        # Without timeout, should use input() not m_read_timeout
        assert "input()" in code
        # Should not have _test assignment from READ
        input_lines = [line for line in code.split("\n") if "input()" in line]
        for line in input_lines:
            assert "_test" not in line

    def test_lock_timeout_sets_test_true(self, execute_mumps):
        """LOCK success with timeout sets $TEST=1 (§8.2.12, FR-047).

        Spec 013 FR-019: Timed LOCK sets $TEST based on success.
        In single-process mode, lock always succeeds immediately.
        """
        result = execute_mumps("TEST\n I 0\n L +^A:0\n W $T\n Q")
        assert result.output == "1"

    def test_lock_timed_changes_test(self, execute_mumps):
        """Timed LOCK changes $TEST (§8.2.12, FR-047).

        Spec 013: L +^A:timeout modifies $TEST, but L +^A does not.
        """
        result = execute_mumps("TEST\n I 0\n W $T\n L +^A:0\n W $T\n Q")
        assert result.output == "01"

    def test_untimed_lock_preserves_test(self, execute_mumps):
        """Untimed LOCK does NOT change $TEST (§8.2.12).

        Spec 013: Per MUMPS spec, untimed LOCK does not modify $TEST.
        """
        result = execute_mumps("TEST\n I 0\n W $T\n L +^A\n W $T\n Q")
        assert result.output == "00"

    def test_open_timeout_sets_test(self, generate_python):
        """OPEN with timeout assigns to $TEST (§8.2.15, FR-047).

        OPEN device:timeout generates code that assigns _test based on success.
        """
        code = generate_python('TEST O "/tmp/test":5 Q')
        # Generated code should assign to _test for timed OPEN
        assert "_test = _rt.open_device" in code

    def test_open_without_timeout_no_test(self, generate_python):
        """OPEN without timeout does NOT modify $TEST (§8.2.15).

        Per MUMPS spec: untimed OPEN does not set $TEST.
        """
        code = generate_python('TEST O "/tmp/test" Q')
        # Without timeout, should NOT assign to _test
        assert "_test = _rt.open_device" not in code

    def test_lock_decrement_timed_always_true(self, execute_mumps):
        """LOCK -:timeout always sets $TEST=1 (§8.2.12, FR-047).

        Spec 013: L -name:timeout always sets $TEST to 1 per MUMPS spec.
        """
        result = execute_mumps("TEST\n I 0\n L -^A:0\n W $T\n Q")
        assert result.output == "1"

    def test_lock_decrement_untimed_preserves_test(self, execute_mumps):
        """Untimed LOCK - does NOT change $TEST (§8.2.12).

        Spec 013: L -name without timeout does not modify $TEST.
        """
        result = execute_mumps("TEST\n I 0\n L -^A\n W $T\n Q")
        assert result.output == "0"

    def test_job_timeout_sets_test_true(self, generate_python):
        """JOB with timeout sets $TEST based on result (§8.2.10, FR-047).

        Note: Actual job execution behavior varies - testing codegen structure.
        With timeout present, generated code must assign to _test.
        """
        code = generate_python("TEST J NOPE::0 W $T Q")
        # Generated code should assign to _test for timed JOB
        assert "_test = _rt.start_job" in code

    def test_job_without_timeout_no_test(self, generate_python):
        """JOB without timeout does NOT modify $TEST (§8.2.10).

        Per MUMPS spec: untimed JOB does not set $TEST.
        """
        code = generate_python("TEST J NOPE W $T Q")
        # Without timeout, should NOT assign to _test
        assert "_test = _rt.start_job" not in code

    def test_timeout_expression_evaluated(self, execute_mumps):
        """Timeout expression is evaluated at runtime (§8.2.12).

        SET T=0 LOCK +^X:T  ; T evaluated to get timeout value
        Uses LOCK since it's testable without stdin.
        """
        # Set T=0 (immediate timeout), use it in LOCK timeout
        result = execute_mumps("TEST\n S T=0\n L +^X:T\n W $T\n Q")
        assert result.output == "1"

    def test_zero_timeout_is_immediate(self, execute_mumps):
        """Timeout of 0 is immediate/non-blocking (§8.2.12).

        Per spec: timeout of 0 means immediate (non-blocking) attempt.
        In single-process mode, LOCK always succeeds.
        """
        result = execute_mumps("TEST\n L +^X:0\n W $T\n Q")
        assert result.output == "1"
