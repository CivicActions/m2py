"""Tests for JOB command code generation (§8.2.10).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.10
"""

import pytest


@pytest.mark.codegen
class TestJobCommandCodegen:
    """Codegen-level tests for JOB command code generation (§8.2.10)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: JOB to subprocess")
    def test_job_to_subprocess(self, generate_python):
        """JOB generates subprocess or threading (§8.2.10)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: JOB timeout")
    def test_job_timeout(self, generate_python):
        """JOB timeout generates timeout handling (§8.2.10)."""
        pytest.fail("Stub - implement test")
