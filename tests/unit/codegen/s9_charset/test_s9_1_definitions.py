"""Tests for Character Set code generation (§9).

Reference: MUMPS 1995 ANSI Standard, Section 9

M character encoding maps to Python unicode. Characters are handled via
$CHAR (code point to character) and $ASCII (character to code point).
"""

import pytest


@pytest.mark.codegen
class TestCharacterSetCodegen:
    """Codegen-level tests for character set handling (§9)."""

    def test_m_character_encoding(self, execute_mumps):
        """M character set maps to Python unicode (§9.1).

        Spec 014 Task E4 (T082): M characters are represented as Python
        unicode strings. $CHAR produces characters from code points,
        $ASCII reads code points back from characters.
        """
        # Basic ASCII characters
        result = execute_mumps("TEST W $C(65,66,67) Q")
        assert result.success is True
        assert result.output == "ABC"

        # $ASCII reads back the code point
        result = execute_mumps('TEST W $A("A") Q')
        assert result.success is True
        assert result.output == "65"

        # Unicode characters (é = 233, € = 8364)
        result = execute_mumps("TEST W $C(233,8364) Q")
        assert result.success is True
        assert result.output == "é€"

        # Round-trip: $A($C(n)) == n
        result = execute_mumps("TEST W $A($C(8364)) Q")
        assert result.success is True
        assert result.output == "8364"

    def test_graphic_characters(self, execute_mumps):
        """Graphic characters (32-126) preserved in output (§9.2).

        Spec 014 Task E4 (T083): The printable ASCII range (space through tilde)
        is preserved in WRITE output without transformation.
        """
        # Space (32) and tilde (126) - boundaries
        result = execute_mumps("TEST W $C(32,126) Q")
        assert result.success is True
        assert result.output == " ~"

        # Sample of graphic characters
        result = execute_mumps("TEST W $C(33,64,90,97,122) Q")
        assert result.success is True
        assert result.output == "!@Zaz"

        # Direct string output
        result = execute_mumps('TEST W "Hello, World!" Q')
        assert result.success is True
        assert result.output == "Hello, World!"

    def test_control_characters(self, execute_mumps):
        """Control characters preserved in strings (§9.3).

        Spec 014 Task E4 (T083): Control characters (0-31, 127) are preserved
        in string variables and can be manipulated with string functions.
        """
        # NUL (0), SOH (1), ESC (27), DEL (127)
        result = execute_mumps("TEST S X=$C(0,1,27,127) W $L(X) Q")
        assert result.success is True
        assert result.output == "4"

        # Concatenate control chars with text
        result = execute_mumps('TEST S X=$C(0,1,27)_"ABC"_$C(127) W $L(X) Q')
        assert result.success is True
        assert result.output == "7"

        # $ASCII can read control characters
        result = execute_mumps("TEST W $A($C(27)) Q")
        assert result.success is True
        assert result.output == "27"
