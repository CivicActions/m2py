"""Integration tests for ZLINK command (FR-035 verification).

Spec 021 Phase 11 (T117): Verify existing ZLINK implementation against
FR-035 acceptance scenarios.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
class TestZlinkIntegration:
    """Verify ZLINK generates valid Python code."""

    def test_zlink_basic_generates_code(self):
        """ZLINK with routine name generates _rt.zlink() call."""
        source = 'TEST ZLINK "MYROUTINE" Q\n'
        code = generate_python(source)
        assert '_rt.zlink("MYROUTINE")' in code

    def test_zlink_no_args_generates_pass(self):
        """ZLINK with no args generates pass."""
        source = "TEST\n ZLINK\n Q\n"
        code = generate_python(source)
        assert "pass  # ZLINK (no args)" in code

    def test_zlink_variable_generates_code(self):
        """ZLINK with variable generates _rt.zlink() call."""
        source = 'TEST S X="MYROUTINE" ZLINK X Q\n'
        code = generate_python(source)
        assert "_rt.zlink(" in code
