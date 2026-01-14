"""Tests for LHS $PIECE assignment (Spec 009 Phase 3 - User Story 1).

LHS $PIECE modifies a specific piece (delimiter-separated segment) of a
string variable in-place, creating the variable if undefined and padding
with delimiters if needed.

Acceptance Scenarios from spec.md:
1. S X="A^B^C" S $P(X,"^",2)="NEW" W X → "A^NEW^C" (basic replacement)
2. S $P(Y,"^",3)="C" W Y → "^^C" (Y undefined, pads with delimiters)
3. S X="A" S $P(X,"^",3)="C" W X → "A^^C" (pads to reach piece 3)
4. S X="A^B^C^D^E" S $P(X,"^",2,4)="X" W X → "A^X^E" (range replacement)
5. (Globals - tested after Phase 6)

Note: Tests use W X without ! since format control (!) codegen is not in scope.
"""

import pytest


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSPieceBasic:
    """Tests for basic LHS $PIECE assignment."""

    def test_basic_piece_replacement(self, execute_mumps):
        """Scenario 1: Replace second piece of delimited string.

        S X="A^B^C" S $P(X,"^",2)="NEW" W X → "A^NEW^C"
        """
        result = execute_mumps('TEST S X="A^B^C" S $P(X,"^",2)="NEW" W X Q')
        assert result.output == "A^NEW^C"

    def test_undefined_variable_with_padding(self, execute_mumps):
        """Scenario 2: LHS $PIECE on undefined variable pads with delimiters.

        S $P(Y,"^",3)="C" W Y → "^^C"
        """
        result = execute_mumps('TEST S $P(Y,"^",3)="C" W Y Q')
        assert result.output == "^^C"

    def test_existing_variable_needs_padding(self, execute_mumps):
        """Scenario 3: Pad existing variable to reach target piece.

        S X="A" S $P(X,"^",3)="C" W X → "A^^C"
        """
        result = execute_mumps('TEST S X="A" S $P(X,"^",3)="C" W X Q')
        assert result.output == "A^^C"

    def test_range_replacement(self, execute_mumps):
        """Scenario 4: Range replacement collapses multiple pieces.

        S X="A^B^C^D^E" S $P(X,"^",2,4)="X" W X → "A^X^E"
        """
        result = execute_mumps('TEST S X="A^B^C^D^E" S $P(X,"^",2,4)="X" W X Q')
        assert result.output == "A^X^E"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSPieceEdgeCases:
    """Edge case tests for LHS $PIECE assignment."""

    def test_piece_one_replacement(self, execute_mumps):
        """Replace first piece of string."""
        result = execute_mumps('TEST S X="A^B^C" S $P(X,"^",1)="NEW" W X Q')
        assert result.output == "NEW^B^C"

    def test_empty_string_piece_one(self, execute_mumps):
        """Set piece 1 on empty string."""
        result = execute_mumps('TEST S X="" S $P(X,"^",1)="A" W X Q')
        assert result.output == "A"

    def test_range_beyond_existing_pieces(self, execute_mumps):
        """Range replacement where end is beyond existing pieces."""
        result = execute_mumps('TEST S X="A^B" S $P(X,"^",2,5)="X" W X Q')
        assert result.output == "A^X"

    def test_range_starting_beyond_existing(self, execute_mumps):
        """Range replacement starting beyond existing pieces adds padding."""
        result = execute_mumps('TEST S X="A^B" S $P(X,"^",4,5)="X" W X Q')
        assert result.output == "A^B^^X"

    def test_different_delimiter(self, execute_mumps):
        """Use a different delimiter character."""
        result = execute_mumps('TEST S X="A:B:C" S $P(X,":",2)="NEW" W X Q')
        assert result.output == "A:NEW:C"

    def test_multi_char_delimiter(self, execute_mumps):
        """Use multi-character delimiter."""
        result = execute_mumps('TEST S X="A||B||C" S $P(X,"||",2)="NEW" W X Q')
        assert result.output == "A||NEW||C"
