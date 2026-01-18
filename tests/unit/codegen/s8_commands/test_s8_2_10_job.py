"""Tests for JOB command code generation (§8.2.10).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.10

JOB command starts a new process executing a routine:
- J label           ; Start job at label in current routine
- J label^routine   ; Start job at label in external routine
- J label::5        ; Start job with 5-second timeout
- J label:():5      ; Start job with empty params and timeout

Timeout behavior per MUMPS spec:
- No timeout: Does not affect $TEST
- Timeout present: Sets $TEST=1 on success, $TEST=0 on timeout

Note: In Python transpilation, JOB is simulated since we can't actually
spawn MUMPS processes. The runtime.job() method sets $ZJOB and returns
success/failure for timeout handling.
"""

import pytest


@pytest.mark.codegen
class TestJobCommandCodegen:
    """Codegen-level tests for JOB command code generation (§8.2.10)."""

    def test_job_simple_label(self, execute_mumps):
        """JOB generates runtime.job() call for simple label (§8.2.10).

        J LABEL  ; Start job at LABEL in current routine
        """
        result = execute_mumps('TEST\n J LABEL\n W "done"\n Q\nLABEL\n W "job"\n Q')
        # Note: Job doesn't execute synchronously, so we just see "done"
        assert result.output == "done"

    def test_job_with_routine(self, generate_python):
        """JOB generates routine reference for external call (§8.2.10).

        J LABEL^ROUTINE  ; Start job at LABEL in ROUTINE
        """
        code = "TEST\n J LABEL^ROUTINE\n Q"
        result = generate_python(code)
        # Should generate _rt.start_job('LABEL', 'ROUTINE', ...)
        assert "_rt.start_job('LABEL', 'ROUTINE'" in result

    def test_job_timeout_sets_test_true_on_success(self, execute_mumps):
        """JOB with timeout sets $TEST=1 on success (§8.2.10).

        J LABEL::5  ; With timeout, $TEST=1 if job starts successfully
        """
        result = execute_mumps("TEST\n I 0\n J LABEL::5\n W $T\n Q\nLABEL\n Q")
        # Timeout present + success = $TEST=1
        assert result.output == "1"

    def test_job_no_timeout_preserves_test(self, execute_mumps):
        """JOB without timeout does not affect $TEST (§8.2.10).

        J LABEL  ; Without timeout, $TEST is unchanged
        """
        result = execute_mumps("TEST\n I 0\n J LABEL\n W $T\n Q\nLABEL\n Q")
        # No timeout = $TEST unchanged (was 0 from I 0)
        assert result.output == "0"

    def test_job_with_empty_params_and_timeout(self, generate_python):
        """JOB with empty params and timeout (§8.2.10).

        J LABEL:():5  ; Empty process parameters, 5 second timeout
        """
        code = "TEST\n J LABEL:():5\n Q"
        result = generate_python(code)
        # Should generate _rt.start_job with timeout=5
        assert "_rt.start_job('LABEL', None, []" in result
        assert "5)" in result

    def test_job_zjob_set(self, execute_mumps):
        """JOB sets $ZJOB to spawned process ID (§8.2.10).

        After JOB, $ZJOB contains the PID of the spawned process.
        In simulation mode, it returns the current process ID.
        """
        result = execute_mumps("TEST\n J LABEL\n W $ZJ\n Q\nLABEL\n Q")
        # $ZJOB should be a positive integer (process ID)
        assert result.output.isdigit()
        assert int(result.output) > 0
