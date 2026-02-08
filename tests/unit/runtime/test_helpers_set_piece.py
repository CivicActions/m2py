"""Tests for m_set_piece runtime helper function (Spec 017 Phase 6).

Tests the fixes to m_set_piece:
1. Proper handling of piece_from <= 0 with piece_to >= 1 (clamp to 1)
2. No modification when piece_from > piece_to
3. No modification when both piece_from and piece_to <= 0
4. Empty delimiter special handling

Reference: MUMPS 1995 ANSI Standard, Section 8.2.18 (LHS $PIECE)
"""

from m2py.runtime.helpers import m_set_piece


# =============================================================================
# m_set_piece Basic Functionality
# =============================================================================


class TestMSetPieceBasic:
    """Basic m_set_piece functionality tests."""

    def test_replace_second_piece(self):
        """Replace piece 2 of a delimited string."""
        result = []
        m_set_piece(lambda: "A^B^C", lambda v: result.append(v), "^", 2, None, "NEW")
        assert result[0] == "A^NEW^C"

    def test_replace_first_piece(self):
        """Replace piece 1 of a delimited string."""
        result = []
        m_set_piece(lambda: "A^B^C", lambda v: result.append(v), "^", 1, None, "NEW")
        assert result[0] == "NEW^B^C"

    def test_replace_last_piece(self):
        """Replace last piece of a delimited string."""
        result = []
        m_set_piece(lambda: "A^B^C", lambda v: result.append(v), "^", 3, None, "NEW")
        assert result[0] == "A^B^NEW"

    def test_replace_beyond_existing_adds_padding(self):
        """Setting piece beyond existing adds delimiter padding."""
        result = []
        m_set_piece(lambda: "A^B", lambda v: result.append(v), "^", 4, None, "D")
        assert result[0] == "A^B^^D"

    def test_undefined_variable_padding(self):
        """Setting piece on empty string pads with delimiters."""
        result = []
        m_set_piece(lambda: "", lambda v: result.append(v), "^", 3, None, "C")
        assert result[0] == "^^C"


# =============================================================================
# m_set_piece Range Replacement
# =============================================================================


class TestMSetPieceRange:
    """Tests for m_set_piece range replacement (piece_from to piece_to)."""

    def test_range_replacement_collapses_pieces(self):
        """Range replacement collapses multiple pieces into one."""
        result = []
        m_set_piece(lambda: "A^B^C^D^E", lambda v: result.append(v), "^", 2, 4, "X")
        assert result[0] == "A^X^E"

    def test_range_all_pieces(self):
        """Range covering all pieces replaces entire string."""
        result = []
        m_set_piece(lambda: "A^B^C", lambda v: result.append(v), "^", 1, 3, "X")
        assert result[0] == "X"

    def test_range_beyond_existing(self):
        """Range ending beyond existing pieces."""
        result = []
        m_set_piece(lambda: "A^B", lambda v: result.append(v), "^", 2, 5, "X")
        assert result[0] == "A^X"


# =============================================================================
# m_set_piece Edge Cases with Negative/Zero Indices (Spec 017 Fixes)
# =============================================================================


class TestMSetPieceEdgeCases:
    """Tests for m_set_piece edge cases with invalid piece numbers.

    Bug fixes:
    - piece_from <= 0 and piece_to <= 0: no modification
    - piece_from <= 0 and piece_to >= 1: clamp piece_from to 1
    - piece_from > piece_to: no modification
    """

    def test_piece_zero_no_modification(self):
        """piece_from=0 with no piece_to results in no modification."""
        result = []
        m_set_piece(
            lambda: "A^B^C",
            lambda v: result.append(v),
            "^",
            0,
            None,  # This becomes piece_to=0
            "NEW",
        )
        # Both are 0, no modification
        assert len(result) == 0

    def test_negative_piece_no_modification(self):
        """Negative piece_from with no piece_to results in no modification."""
        result = []
        m_set_piece(
            lambda: "A^B^C",
            lambda v: result.append(v),
            "^",
            -1,
            None,  # This becomes piece_to=-1
            "NEW",
        )
        # Both negative, no modification
        assert len(result) == 0

    def test_piece_from_zero_piece_to_positive_clamps(self):
        """piece_from=0 with positive piece_to clamps piece_from to 1.

        VV2LHP1 II-106: S $P(X,"^",0,2)="NEW" should replace pieces 1-2.
        """
        result = []
        m_set_piece(lambda: "A^B^C", lambda v: result.append(v), "^", 0, 2, "NEW")
        assert result[0] == "NEW^C"

    def test_piece_from_negative_piece_to_positive_clamps(self):
        """Negative piece_from with positive piece_to clamps to 1.

        VV2LHP1 II-106: S $P(X,"/",-3,2)="D" should replace pieces 1-2.
        """
        result = []
        m_set_piece(lambda: "A/B/C", lambda v: result.append(v), "/", -3, 2, "D")
        assert result[0] == "D/C"

    def test_very_negative_piece_from_clamps(self):
        """Very negative piece_from clamps to 1.

        VV2LHP1 II-106: S $P(X,"/",-99999,33)="D" replaces all pieces.
        """
        result = []
        m_set_piece(lambda: "A/B/C", lambda v: result.append(v), "/", -99999, 33, "D")
        assert result[0] == "D"

    def test_both_negative_no_modification(self):
        """Both piece_from and piece_to negative results in no modification."""
        result = []
        m_set_piece(lambda: "A^B^C", lambda v: result.append(v), "^", -2, -1, "NEW")
        assert len(result) == 0

    def test_piece_from_greater_than_piece_to_no_modification(self):
        """piece_from > piece_to results in no modification.

        VV2LHP2 II-109: When intexpr2>intexpr3, no modification occurs.
        """
        result = []
        m_set_piece(lambda: "A^B^C", lambda v: result.append(v), "^", 5, 3, "NEW")
        assert len(result) == 0


# =============================================================================
# m_set_piece Empty Delimiter
# =============================================================================


class TestMSetPieceEmptyDelimiter:
    """Tests for m_set_piece with empty delimiter."""

    def test_empty_delimiter_piece_one_replaces_all(self):
        """Empty delimiter with piece_from=1 replaces entire string."""
        result = []
        m_set_piece(lambda: "ABC", lambda v: result.append(v), "", 1, None, "NEW")
        assert result[0] == "NEW"

    def test_empty_delimiter_piece_two_appends(self):
        """Empty delimiter with piece_from>1 appends to string."""
        result = []
        m_set_piece(lambda: "ABC", lambda v: result.append(v), "", 2, None, "NEW")
        assert result[0] == "ABCNEW"


# =============================================================================
# m_set_piece with Numeric String Values
# =============================================================================


class TestMSetPieceNumericStrings:
    """Tests for m_set_piece when getter returns numeric-looking strings."""

    def test_numeric_string_as_current_value(self):
        """Getter returns numeric string, should work as delimiter target."""
        result = []
        m_set_piece(lambda: "12345", lambda v: result.append(v), "2", 1, None, "NEW")
        assert result[0] == "NEW2345"

    def test_getter_returns_string_value(self):
        """Getter returns string value, setter receives modified string.

        In actual generated code, getters use str() wrapper to ensure
        numeric MUMPS values are converted to strings for m_set_piece.

        Note: "0" split by "0" gives ["", ""], so piece 1 = "".
        Setting piece 1 to "NEW" gives "NEW" + "0" + "" = "NEW0"
        """
        result = []
        m_set_piece(
            lambda: "0",  # Getter always returns string
            lambda v: result.append(v),
            "0",
            1,
            None,
            "NEW",
        )
        assert result[0] == "NEW0"
