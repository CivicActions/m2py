"""Tests for SSVNs code generation (§7.1.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.3
"""

import pytest


@pytest.mark.codegen
class TestSsvnsCodegen:
    """Codegen-level tests for structured system variables code generation (§7.1.3)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$GLOBAL codegen")
    def test_ssvn_global(self, generate_python):
        """^$GLOBAL generates system global access (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$JOB codegen")
    def test_ssvn_job(self, generate_python):
        """^$JOB generates job info access (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$LOCK codegen")
    def test_ssvn_lock(self, generate_python):
        """^$LOCK generates lock info access (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$ROUTINE codegen")
    def test_ssvn_routine(self, generate_python):
        """^$ROUTINE generates routine info access (§7.1.3)."""
        pytest.fail("Stub - implement test")


# Out-of-scope SSVNs - "Parses OK" limitations.
# These parse and analyze correctly but runtime semantics are undefined.
# Parser/ASG tests exist to verify parsing works. No codegen tests needed.
#
# - ^$EVENT, ^$WINDOW, ^$DISPLAY: LIM-003 (MWAPI SSVNs)
# - ^$LIBRARY: LIM-011 (zero real-world usage)
