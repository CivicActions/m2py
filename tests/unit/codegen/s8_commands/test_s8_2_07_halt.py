"""Tests for HALT command code generation (§8.2.7).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.7
"""

import pytest


@pytest.mark.codegen
class TestHaltCommandCodegen:
    """Codegen-level tests for HALT command code generation (§8.2.7)."""

    def test_halt_generates_system_exit(self, generate_python):
        """HALT generates raise SystemExit(0) (§8.2.7)."""
        # Use full HALT command to avoid parsing ambiguity with HANG
        code = generate_python("TEST HALT")
        # Should have SystemExit for program termination
        assert "raise SystemExit(0)" in code

    def test_halt_stops_execution(self, execute_mumps):
        """HALT terminates program - code after HALT is not executed (§8.2.7).

        Note: MUMPS requires double-space between argumentless commands and
        the next command on the same line, or use separate lines.
        """
        # Use full HALT command name
        result = execute_mumps('TEST W "before",! HALT  W "after",! Q')
        # Only "before" should appear - HALT prevents "after"
        assert result.output == "before\n"
        assert "after" not in result.output

    def test_halt_from_subroutine(self, execute_mumps):
        """HALT from subroutine terminates entire program (§8.2.7)."""
        # HALT should terminate even when called from a subroutine
        # Use separate lines for clarity
        result = execute_mumps('TEST D SUB W "after sub",! Q\nSUB W "in sub",! HALT')
        assert result.output == "in sub\n"
        assert "after sub" not in result.output

    def test_halt_vs_hang_distinction(self, generate_python):
        """Argumentless HALT vs HANG with duration (§8.2.7 vs §8.2.8)."""
        # Full HALT should use SystemExit
        halt_code = generate_python("TEST HALT")
        assert "SystemExit" in halt_code
        assert "time.sleep" not in halt_code

        # H with argument should be HANG (time.sleep)
        hang_code = generate_python("TEST H 1 Q")
        assert "time.sleep" in hang_code
        assert "SystemExit" not in hang_code

    def test_halt_multiline_syntax(self, execute_mumps):
        """HALT on its own line terminates correctly (§8.2.7)."""
        # This is the standard way to write HALT in MUMPS
        result = execute_mumps('TEST W "start",!\n HALT\n W "end",!\n Q')
        assert result.output == "start\n"
        assert "end" not in result.output
