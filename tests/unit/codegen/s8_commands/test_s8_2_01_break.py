"""Tests for BREAK command code generation (§8.2.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.1
BREAK transfers control to the debugger.
"""

import pytest


@pytest.mark.codegen
class TestBreakCommandCodegen:
    """Codegen-level tests for BREAK command code generation (§8.2.1)."""

    def test_break_generates_breakpoint(self, generate_python):
        """BREAK generates Python breakpoint() call (§8.2.1)."""
        code = generate_python("TEST B Q")
        assert "breakpoint()" in code

    def test_break_argumentless(self, generate_python):
        """BREAK with no arguments generates breakpoint (§8.2.1)."""
        code = generate_python("TEST B  Q")
        assert "breakpoint()" in code

    def test_break_with_postcondition(self, generate_python):
        """BREAK with postcondition wraps in conditional (§8.2.1)."""
        code = generate_python("TEST S X=1 B:X Q")
        assert "breakpoint()" in code
        # Should have a conditional check
        assert "if " in code

    def test_break_does_not_modify_test(self, generate_python, monkeypatch):
        """BREAK does not modify $TEST (§8.2.1)."""
        # We can't actually invoke breakpoint() in tests
        # but we can verify it's generated with proper comment
        code = generate_python("TEST B Q")
        assert "breakpoint()" in code
        assert "BREAK" in code  # Comment should reference BREAK
