"""Tests for HANG command code generation (§8.2.8).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.8
"""

import pytest


@pytest.mark.codegen
class TestHangCommandCodegen:
    """Codegen-level tests for HANG command code generation (§8.2.8)."""

    def test_hang_generates_time_sleep(self, generate_python):
        """HANG generates time.sleep() call (§8.2.8)."""
        code = generate_python("TEST H 1 Q")
        # Should have time.sleep with m_num() for numeric coercion
        assert "time.sleep" in code
        assert "m_num" in code

    def test_hang_with_fractional_seconds(self, generate_python):
        """HANG with fractional seconds generates proper sleep (§8.2.8)."""
        code = generate_python("TEST H 0.5 Q")
        assert "time.sleep" in code
        # 0.5 should appear in the output (either raw or as part of expression)
        assert "0.5" in code or ".5" in code

    def test_hang_with_variable_duration(self, generate_python):
        """HANG with variable generates time.sleep with var evaluation (§8.2.8)."""
        code = generate_python("TEST S X=2 H X Q")
        assert "time.sleep" in code

    def test_hang_zero_seconds_execution(self, execute_mumps):
        """HANG 0 returns immediately without error (§8.2.8)."""
        result = execute_mumps('TEST H 0 W "done",! Q')
        assert result.output == "done\n"

    def test_hang_brief_pause_execution(self, execute_mumps):
        """HANG with small duration executes correctly (§8.2.8)."""
        result = execute_mumps('TEST H 0.01 W "done",! Q')
        assert result.output == "done\n"

    def test_hang_with_variable_execution(self, execute_mumps):
        """HANG with variable duration executes correctly (§8.2.8)."""
        result = execute_mumps('TEST S X=0.01 H X W "var",! Q')
        assert result.output == "var\n"
