"""Tests for WRITE command code generation (§8.2.25).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25
"""

import pytest


@pytest.mark.codegen
class TestWriteCommandCodegen:
    """Codegen-level tests for WRITE command code generation (§8.2.25)."""

    def test_write_to_print(self, generate_python):
        """WRITE generates _rt.write() call (§8.2.25)."""
        code = generate_python('TEST\n W "HELLO"\n Q\n')
        assert "_rt.write" in code

    def test_write_string_literal(self, execute_mumps):
        """WRITE outputs string literal directly (§8.2.25).

        User Story 1 acceptance scenario 2:
        Given: TEST W "PASS" Q
        When: generated and executed
        Then: output is "PASS"
        """
        result = execute_mumps('TEST\n W "PASS"\n Q\n')
        assert result.output == "PASS"
        assert result.success is True

    def test_write_format_controls(self, execute_mumps):
        """WRITE !, # generate newlines/form feeds (§8.2.25).

        YDB verified: W "A",!,"B" → "A\\nB"
        """
        result = execute_mumps('TEST\n W "A",!,"B"\n Q\n')
        assert result.output == "A\nB"
        assert result.success is True

    def test_write_column(self, execute_mumps):
        """WRITE ?n generates column positioning (§8.2.25).

        YDB verified: W ?5,"X" → "     X"
        """
        result = execute_mumps('TEST\n W ?5,"X"\n Q\n')
        assert result.output == "     X"
        assert result.success is True

    def test_write_char_code(self, execute_mumps):
        """WRITE *n generates char output (§8.2.25).

        YDB verified: W *65 → "A"
        """
        result = execute_mumps("TEST\n W *65\n Q\n")
        assert result.output == "A"
        assert result.success is True

    def test_write_device_control_not_supported(self, generate_python):
        """WRITE device control (/mnemonic) raises NotImplementedError.

        Device control mnemonics like /CUP(row,col) are terminal-specific
        sequences that cannot be transpiled to pure Python.

        Spec 015: Document that device control mnemonics are not supported.
        """
        code = "TEST\n W /CUP(10,5)\n Q\n"
        with pytest.raises(NotImplementedError, match="DeviceControl"):
            generate_python(code)

    def test_write_device_control_with_string_raises_not_implemented(
        self, generate_python
    ):
        """WRITE with device control mnemonic and string raises NotImplementedError."""
        code = 'TEST\n W /BOLD,"text",/NORMAL\n Q\n'
        with pytest.raises(NotImplementedError, match="DeviceControl"):
            generate_python(code)


@pytest.mark.codegen
class TestFormatControlNumericCoercion:
    """Tests for ?intexpr and *intexpr with MUMPS numeric coercion.

    In MUMPS, format controls like ?intexpr and *intexpr expect a numeric
    expression. When a string is provided, it should be coerced using MUMPS
    rules: leading numeric portion extracted, non-numeric strings become 0.

    Fix: Changed from int(expr) to int(m_num(expr)) in codegen.
    """

    def test_tab_with_numeric_string(self, execute_mumps):
        """W ?"10" tabs to column 10 (string coerces to 10)."""
        result = execute_mumps('TEST\n W ?"10","X"\n Q\n')
        assert result.success is True
        assert result.output == "          X"  # 10 spaces + X

    def test_tab_with_non_numeric_string(self, execute_mumps):
        """W ?"ABC" tabs to column 0 (string coerces to 0).

        "ABC" has no leading numeric portion, so m_num("ABC") = 0.
        ?0 means column 0, so X appears at position 0 (no leading spaces).
        """
        result = execute_mumps('TEST\n W ?"ABC","X"\n Q\n')
        assert result.success is True
        assert result.output == "X"

    def test_tab_with_leading_numeric_string(self, execute_mumps):
        """W ?"3ABC" tabs to column 3 (string coerces to 3)."""
        result = execute_mumps('TEST\n W ?"3ABC","X"\n Q\n')
        assert result.success is True
        assert result.output == "   X"  # 3 spaces + X

    def test_tab_with_variable_string(self, execute_mumps):
        """W ?X where X="ABC" tabs to column 0."""
        result = execute_mumps('TEST\n S X="ABC" W ?X,"Y"\n Q\n')
        assert result.success is True
        assert result.output == "Y"

    def test_charcode_with_numeric_string(self, execute_mumps):
        """W *"65" outputs 'A' (string coerces to 65)."""
        result = execute_mumps('TEST\n W *"65"\n Q\n')
        assert result.success is True
        assert result.output == "A"

    def test_charcode_with_non_numeric_string(self, execute_mumps):
        """W *"XYZ" outputs NUL character (string coerces to 0)."""
        result = execute_mumps('TEST\n W *"XYZ"\n Q\n')
        assert result.success is True
        assert result.output == "\x00"  # chr(0) = NUL

    def test_charcode_with_leading_numeric_string(self, execute_mumps):
        """W *"66ABC" outputs 'B' (string coerces to 66)."""
        result = execute_mumps('TEST\n W *"66ABC"\n Q\n')
        assert result.success is True
        assert result.output == "B"


@pytest.mark.codegen
class TestMultipleNewlines:
    """Tests for WRITE with multiple consecutive newlines.

    These tests verify that m2py correctly outputs the exact number of newlines
    specified in MUMPS WRITE commands (W !, W !!, W !!!, etc.).

    This is important because:
    1. W ! outputs a single newline
    2. W !! outputs two newlines (one blank line between content)
    3. W !!! outputs three newlines (two blank lines between content)
    4. etc.

    These behaviors must match YDB exactly - no collapsing or normalization.
    """

    def test_single_newline(self, execute_mumps):
        """W ! outputs exactly one newline.

        YDB verified: W "A",!,"B" → "A\\nB"
        """
        result = execute_mumps('TEST\n W "A",!,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\nB"

    def test_double_newline(self, execute_mumps):
        """W !! outputs exactly two newlines.

        YDB verified: W "A",!!,"B" → "A\\n\\nB"
        """
        result = execute_mumps('TEST\n W "A",!!,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\nB"

    def test_triple_newline(self, execute_mumps):
        """W !!! outputs exactly three newlines.

        YDB verified: W "A",!!!,"B" → "A\\n\\n\\nB"
        This is a legitimate MUMPS construct - NOT a pagination artifact.
        """
        result = execute_mumps('TEST\n W "A",!!!,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\n\nB"

    def test_quadruple_newline(self, execute_mumps):
        """W !!!! outputs exactly four newlines.

        YDB verified: W "A",!!!!,"B" → "A\\n\\n\\n\\nB"
        This is a legitimate MUMPS construct - NOT a pagination artifact.
        """
        result = execute_mumps('TEST\n W "A",!!!!,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\n\n\nB"

    def test_five_newlines(self, execute_mumps):
        """W !!!!! outputs exactly five newlines.

        YDB verified: W "A",!!!!!,"B" → "A\\n\\n\\n\\n\\nB"
        """
        result = execute_mumps('TEST\n W "A",!!!!!,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\n\n\n\nB"

    def test_mixed_newlines_in_sequence(self, execute_mumps):
        """Multiple WRITE commands preserve newline counts.

        YDB verified: W "A" W !! W "B" W !!! W "C" → "A\\n\\nB\\n\\n\\nC"
        """
        result = execute_mumps('TEST\n W "A" W !! W "B" W !!! W "C"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\nB\n\n\nC"


@pytest.mark.codegen
class TestFormFeedBehavior:
    """Tests for WRITE # (form feed) behavior.

    Form feed (W #) outputs:
    1. A newline if not at column 0
    2. The form feed character (\\x0c)

    These tests verify correct form feed output and its interaction with newlines.
    """

    def test_formfeed_basic(self, execute_mumps):
        """W # outputs newline + form feed.

        YDB verified: W "A",#,"B" → "A\\n\\x0cB"
        """
        result = execute_mumps('TEST\n W "A",#,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\x0cB"

    def test_formfeed_with_preceding_newline(self, execute_mumps):
        """W !,# does NOT double the newline before form feed.

        YDB verified: W "A",!,#,"B" → "A\\n\\x0cB"
        The form feed after a newline doesn't add another newline.
        """
        result = execute_mumps('TEST\n W "A",!,#,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\x0cB"

    def test_formfeed_with_following_newline(self, execute_mumps):
        """W #,! outputs form feed then newline.

        YDB verified: W "A",#,!,"B" → "A\\n\\x0c\\nB"
        """
        result = execute_mumps('TEST\n W "A",#,!,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\x0c\nB"

    def test_formfeed_with_surrounding_newlines(self, execute_mumps):
        """W !!,#,!! outputs newlines, form feed, newlines.

        YDB verified: W "A",!!,#,!!,"B" → "A\\n\\n\\x0c\\n\\nB"
        """
        result = execute_mumps('TEST\n W "A",!!,#,!!,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\n\x0c\n\nB"

    def test_formfeed_at_column_zero(self, execute_mumps):
        """W # at column 0 outputs just form feed (no preceding newline).

        YDB verified: W #,"A" → "\\x0cA"
        Form feed only adds a newline when NOT at column 0.
        """
        result = execute_mumps('TEST\n W #,"A"\n Q\n')
        assert result.success is True
        assert result.output == "\x0cA"

    def test_formfeed_after_newline_at_column_zero(self, execute_mumps):
        """W !,# outputs newline + form feed (already at column 0 after !).

        YDB verified: W !,#,"A" → "\\n\\x0cA"
        After W !, we're at column 0, so W # adds no extra newline.
        """
        result = execute_mumps('TEST\n W !,#,"A"\n Q\n')
        assert result.success is True
        assert result.output == "\n\x0cA"

    def test_formfeed_after_double_newline(self, execute_mumps):
        """W !!,# outputs two newlines + form feed.

        YDB verified: W !!,#,"A" → "\\n\\n\\x0cA"
        After W !!, we're at column 0, so W # adds no extra newline.
        """
        result = execute_mumps('TEST\n W !!,#,"A"\n Q\n')
        assert result.success is True
        assert result.output == "\n\n\x0cA"

    def test_multiple_consecutive_formfeeds_at_start(self, execute_mumps):
        """W #,# at column 0 outputs two form feeds.

        YDB verified: W #,#,"A" → "\\x0c\\x0cA"
        Each form feed at column 0 outputs just the form feed character.
        """
        result = execute_mumps('TEST\n W #,#,"A"\n Q\n')
        assert result.success is True
        assert result.output == "\x0c\x0cA"

    def test_multiple_consecutive_formfeeds_after_text(self, execute_mumps):
        """W "A",#,# outputs text, newline, then two form feeds.

        YDB verified: W "A",#,#,"B" → "A\\n\\x0c\\x0cB"
        First # outputs newline + form feed (not at column 0).
        Second # outputs just form feed (at column 0 after first #).
        """
        result = execute_mumps('TEST\n W "A",#,#,"B"\n Q\n')
        assert result.success is True
        assert result.output == "A\n\x0c\x0cB"
