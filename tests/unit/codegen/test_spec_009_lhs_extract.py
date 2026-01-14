"""Tests for LHS $EXTRACT assignment (Spec 009 Phase 4 - User Story 2).

LHS $EXTRACT replaces character(s) at specified positions within a string
variable in-place, creating the variable if undefined and padding with
spaces if needed.

Acceptance Scenarios from spec.md:
1. S X="HELLO" S $E(X,1,2)="YO" W X → "YOLLO" (basic replacement)
2. S $E(Z,1,3)="ABC" W Z → "ABC" (Z undefined, creates variable)
3. S W="AB" S $E(W,5,6)="XY" W W → "AB  XY" (space padding)
4. S X="ABCDE" S $E(X,2)="X" W X → "AXCDE" (single position)
5. S X="ABC" S $E(X,1,5)="HELLO" W X → "HELLO" (replacement longer than range)

Note: Tests use W X without ! since format control (!) codegen is not in scope.
"""

import pytest


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSExtractBasic:
    """Tests for basic LHS $EXTRACT assignment."""

    def test_basic_character_replacement(self, execute_mumps):
        """Scenario 1: Replace first two characters of string.

        S X="HELLO" S $E(X,1,2)="YO" W X → "YOLLO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,1,2)="YO" W X Q')
        assert result.output == "YOLLO"

    def test_undefined_variable_creates_it(self, execute_mumps):
        """Scenario 2: LHS $EXTRACT on undefined variable creates it.

        S $E(Z,1,3)="ABC" W Z → "ABC"
        """
        result = execute_mumps('TEST S $E(Z,1,3)="ABC" W Z Q')
        assert result.output == "ABC"

    def test_space_padding(self, execute_mumps):
        """Scenario 3: Pad existing variable with spaces to reach position.

        S W="AB" S $E(W,5,6)="XY" W W → "AB  XY"
        """
        result = execute_mumps('TEST S W="AB" S $E(W,5,6)="XY" W W Q')
        assert result.output == "AB  XY"

    def test_single_position(self, execute_mumps):
        """Scenario 4: Single position replacement (no to_pos specified).

        S X="ABCDE" S $E(X,2)="X" W X → "AXCDE"
        """
        result = execute_mumps('TEST S X="ABCDE" S $E(X,2)="X" W X Q')
        assert result.output == "AXCDE"

    def test_replacement_longer_than_range(self, execute_mumps):
        """Scenario 5: Replacement string is longer than original range.

        S X="ABC" S $E(X,1,5)="HELLO" W X → "HELLO"
        """
        result = execute_mumps('TEST S X="ABC" S $E(X,1,5)="HELLO" W X Q')
        assert result.output == "HELLO"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSExtractEdgeCases:
    """Edge case tests for LHS $EXTRACT assignment."""

    def test_replacement_longer_than_original_range_middle(self, execute_mumps):
        """Replacement longer than range in middle of string expands it.

        S X="HELLO" S $E(X,2,3)="ABCD" W X → "HABCDLO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,2,3)="ABCD" W X Q')
        assert result.output == "HABCDLO"

    def test_replacement_shorter_than_range(self, execute_mumps):
        """Replacement shorter than range shrinks the string.

        S X="HELLO" S $E(X,2,4)="X" W X → "HXO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,2,4)="X" W X Q')
        assert result.output == "HXO"

    def test_same_length_replacement(self, execute_mumps):
        """Same length replacement keeps string length.

        S X="HELLO" S $E(X,2,3)="XX" W X → "HXXLO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,2,3)="XX" W X Q')
        assert result.output == "HXXLO"

    def test_empty_string_position_one(self, execute_mumps):
        """Set position 1 on empty string.

        S X="" S $E(X,1)="A" W X → "A"
        """
        result = execute_mumps('TEST S X="" S $E(X,1)="A" W X Q')
        assert result.output == "A"

    def test_replace_at_end(self, execute_mumps):
        """Replace characters at end of string.

        S X="HELLO" S $E(X,4,5)="XX" W X → "HELXX"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,4,5)="XX" W X Q')
        assert result.output == "HELXX"

    def test_extend_string_beyond_end(self, execute_mumps):
        """Extend string by setting position beyond end.

        S X="ABC" S $E(X,5)="X" W X → "ABC X"
        """
        result = execute_mumps('TEST S X="ABC" S $E(X,5)="X" W X Q')
        assert result.output == "ABC X"
