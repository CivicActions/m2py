"""Tests for MERGE command code generation (§8.2.13).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.13
"""

import pytest


@pytest.mark.codegen
class TestMergeCommandCodegen:
    """Codegen-level tests for MERGE command code generation (§8.2.13)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE to deep copy")
    def test_merge_to_deep_copy(self, generate_python):
        """MERGE generates deep copy operation (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE global")
    def test_merge_global(self, generate_python):
        """MERGE with globals generates global copy (§8.2.13)."""
        pytest.fail("Stub - implement test")
