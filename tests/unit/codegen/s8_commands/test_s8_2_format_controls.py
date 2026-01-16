"""Tests for WRITE format controls code generation (§8.2.25).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25

Tests the four MUMPS WRITE format controls:
- ! (NEWLINE): Output a line terminator
- # (FORMFEED): Output a form feed character
- ?n (TAB): Tab to column n (1-based)
- *n (CHARCODE): Output character with ASCII code n
"""

import pytest


@pytest.mark.codegen
class TestFormatControlsCodegen:
    """Codegen-level tests for WRITE format controls (§8.2.25).

    Spec 011 Phase 7: Format controls implemented.
    """

    # =========================================================================
    # NEWLINE Format Control (!) Tests
    # =========================================================================

    def test_write_newline_basic(self, execute_mumps):
        """WRITE ! outputs a newline character (§8.2.25).

        YDB verified: W "A",!,"B",! → "A\nB\n"
        """
        result = execute_mumps('TEST\n W "A",!,"B",!\n Q\n')
        assert result.output == "A\nB\n"
        assert result.success is True

    def test_write_multiple_newlines(self, execute_mumps):
        """WRITE !,! outputs multiple newlines (§8.2.25).

        YDB verified: W "A",!,!,"B" → "A\n\nB"
        """
        result = execute_mumps('TEST\n W "A",!,!,"B"\n Q\n')
        assert result.output == "A\n\nB"
        assert result.success is True

    def test_write_newline_only(self, execute_mumps):
        """WRITE ! alone outputs just a newline (§8.2.25).

        YDB verified: W ! → "\n"
        """
        result = execute_mumps("TEST\n W !\n Q\n")
        assert result.output == "\n"
        assert result.success is True

    # =========================================================================
    # FORMFEED Format Control (#) Tests
    # =========================================================================

    def test_write_formfeed_basic(self, execute_mumps):
        """WRITE # outputs a form feed character (§8.2.25).

        Form feed is ASCII 12 (\\x0c).
        """
        result = execute_mumps('TEST\n W "A",#,"B"\n Q\n')
        assert result.output == "A\x0cB"
        assert result.success is True

    def test_write_formfeed_only(self, execute_mumps):
        """WRITE # alone outputs just a form feed (§8.2.25)."""
        result = execute_mumps("TEST\n W #\n Q\n")
        assert result.output == "\x0c"
        assert result.success is True

    # =========================================================================
    # CHARCODE Format Control (*n) Tests
    # =========================================================================

    def test_write_charcode_ascii_65(self, execute_mumps):
        """WRITE *65 outputs 'A' (ASCII 65) (§8.2.25).

        YDB verified: W *65 → "A"
        """
        result = execute_mumps("TEST\n W *65\n Q\n")
        assert result.output == "A"
        assert result.success is True

    def test_write_charcode_newline(self, execute_mumps):
        """WRITE *10 outputs newline character (§8.2.25).

        ASCII 10 = linefeed/newline.
        """
        result = execute_mumps("TEST\n W *10\n Q\n")
        assert result.output == "\n"
        assert result.success is True

    def test_write_charcode_sequence(self, execute_mumps):
        """WRITE *72,*73 outputs "HI" (§8.2.25).

        ASCII 72='H', ASCII 73='I'.
        """
        result = execute_mumps("TEST\n W *72,*73\n Q\n")
        assert result.output == "HI"
        assert result.success is True

    def test_write_charcode_with_expression(self, execute_mumps):
        """WRITE *64+1 outputs 'A' (64+1=65) (§8.2.25).

        The argument to * is an expression, not just a literal.
        """
        result = execute_mumps("TEST\n W *64+1\n Q\n")
        assert result.output == "A"
        assert result.success is True

    # =========================================================================
    # TAB Format Control (?n) Tests
    # =========================================================================

    def test_write_tab_to_column(self, execute_mumps):
        """WRITE ?10 tabs to column 10 (§8.2.25).

        YDB verified: W "X",?10,"Y" → "X         Y" (9 spaces between)
        Column numbering is 1-based.
        """
        result = execute_mumps('TEST\n W "X",?10,"Y"\n Q\n')
        # "X" is at column 1, then tab to column 10, then "Y"
        # That's "X" + 9 spaces + "Y"
        assert result.output == "X         Y"
        assert result.success is True

    def test_write_tab_at_start(self, execute_mumps):
        """WRITE ?5 at start tabs to column 5 (§8.2.25).

        Tabs 5 spaces to reach column 5 (0-indexed).
        """
        result = execute_mumps('TEST\n W ?5,"X"\n Q\n')
        # 5 spaces + "X" = column 5
        assert result.output == "     X"
        assert result.success is True

    def test_write_tab_past_current(self, execute_mumps):
        """WRITE ?n when already past column n has no effect (§8.2.25).

        If current position is already >= n, ?n does nothing.
        """
        result = execute_mumps('TEST\n W "HELLO",?3,"X"\n Q\n')
        # "HELLO" is 5 chars, column 6 is current.
        # ?3 is less than 6, so no spaces added.
        assert result.output == "HELLOX"
        assert result.success is True

    def test_write_tab_with_expression(self, execute_mumps):
        """WRITE ?2+3 tabs to column 5 (§8.2.25).

        The argument to ? is an expression. 2+3=5, so tab to column 5.
        """
        result = execute_mumps('TEST\n W ?2+3,"X"\n Q\n')
        # 5 spaces + "X" = column 5
        assert result.output == "     X"
        assert result.success is True

    # =========================================================================
    # Combined Format Controls Tests
    # =========================================================================

    def test_write_mixed_format_controls(self, execute_mumps):
        """WRITE with mixed format controls (§8.2.25).

        Combines newline, charcode, and regular text.
        """
        result = execute_mumps('TEST\n W "Hi",!,*65,*66,*67,!\n Q\n')
        # "Hi" + newline + "ABC" + newline
        assert result.output == "Hi\nABC\n"
        assert result.success is True
