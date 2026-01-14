"""Tests for naked global references (Spec 009 Phase 7 - User Story 5).

Naked global references use the "naked indicator" which tracks the base
(global name and all-but-last subscript) from the most recent global access.
^(subscripts) resolves to the base plus the new subscripts.

Acceptance Scenarios from spec.md:
1. S ^A(1,2)=1 S ^(3)=2 W ^A(1,3) → "2" (naked replaces last subscript)
2. S ^B(1,2,3)=1 S ^(4)=2 W ^B(1,2,4) → "2" (works with deeper nesting)
3. S ^C(1,2)=1 S ^(3,4)=2 W ^C(1,3,4) → "2" (multiple new subscripts)
4. S ^D(1)=1 W ^(1) → "1" (naked read)
5. S ^E(1,2)=1 S ^F(3,4)=2 S ^(5)=3 W ^F(3,5) → "3" (naked follows last global)

Note: Tests use W X without ! since format control (!) codegen is not in scope.
"""

import pytest


@pytest.mark.codegen
@pytest.mark.spec009
class TestNakedGlobalBasic:
    """Tests for basic naked global reference operations."""

    def test_naked_replaces_last_subscript(self, execute_mumps):
        """Scenario 1: Naked reference replaces last subscript.

        S ^A(1,2)=1 S ^(3)=2 W ^A(1,3) → "2"

        After ^A(1,2), naked indicator = ("A", ("1",))
        ^(3) resolves to ^A(1,3)
        """
        result = execute_mumps("TEST S ^A(1,2)=1 S ^(3)=2 W ^A(1,3) Q")
        assert result.output == "2"

    def test_naked_with_deeper_nesting(self, execute_mumps):
        """Scenario 2: Naked reference works with deeper nesting.

        S ^B(1,2,3)=1 S ^(4)=2 W ^B(1,2,4) → "2"

        After ^B(1,2,3), naked indicator = ("B", ("1", "2"))
        ^(4) resolves to ^B(1,2,4)
        """
        result = execute_mumps("TEST S ^B(1,2,3)=1 S ^(4)=2 W ^B(1,2,4) Q")
        assert result.output == "2"

    def test_naked_multiple_new_subscripts(self, execute_mumps):
        """Scenario 3: Naked reference with multiple new subscripts.

        S ^C(1,2)=1 S ^(3,4)=2 W ^C(1,3,4) → "2"

        After ^C(1,2), naked indicator = ("C", ("1",))
        ^(3,4) resolves to ^C(1,3,4)
        """
        result = execute_mumps("TEST S ^C(1,2)=1 S ^(3,4)=2 W ^C(1,3,4) Q")
        assert result.output == "2"

    def test_naked_read(self, execute_mumps):
        """Scenario 4: Naked reference for reading.

        S ^D(1)=1 W ^(1) → "1"

        After ^D(1), naked indicator = ("D", ())
        ^(1) resolves to ^D(1)
        """
        result = execute_mumps("TEST S ^D(1)=1 W ^(1) Q")
        assert result.output == "1"

    def test_naked_follows_last_global(self, execute_mumps):
        """Scenario 5: Naked follows most recently accessed global.

        S ^E(1,2)=1 S ^F(3,4)=2 S ^(5)=3 W ^F(3,5) → "3"

        ^E(1,2) sets indicator to ("E", ("1",))
        ^F(3,4)=2 sets indicator to ("F", ("3",))
        ^(5) resolves to ^F(3,5)
        """
        result = execute_mumps("TEST S ^E(1,2)=1 S ^F(3,4)=2 S ^(5)=3 W ^F(3,5) Q")
        assert result.output == "3"


@pytest.mark.codegen
@pytest.mark.spec009
class TestNakedGlobalEdgeCases:
    """Edge case tests for naked global references."""

    def test_naked_after_root_global(self, execute_mumps):
        """Naked after global with no subscripts."""
        # After ^G=1, indicator becomes None (no subscripts means naked is undefined)
        # But ^G(1)=2 sets indicator to ("G", ())
        result = execute_mumps("TEST S ^G(1)=1 S ^G=2 S ^G(1)=3 W ^(1) Q")
        # After ^G(1)=3, indicator = ("G", ()), ^(1) = ^G(1)
        assert result.output == "3"

    def test_naked_chain(self, execute_mumps):
        """Multiple naked references in sequence."""
        result = execute_mumps("TEST S ^H(1,2)=1 S ^(3)=2 S ^(4)=3 W ^H(1,4) Q")
        # After ^H(1,2), indicator = ("H", ("1",))
        # After ^(3), we're setting ^H(1,3), indicator = ("H", ("1",))
        # After ^(4), we're setting ^H(1,4), indicator = ("H", ("1",))
        assert result.output == "3"

    def test_naked_read_undefined(self, execute_mumps):
        """Naked read of undefined location returns empty string."""
        result = execute_mumps("TEST S ^I(1)=1 W ^(99) Q")
        # ^(99) = ^I(99) which is undefined
        assert result.output == ""

    def test_naked_with_string_subscripts(self, execute_mumps):
        """Naked reference with string subscripts."""
        result = execute_mumps('TEST S ^J("a","b")=1 S ^("c")=2 W ^J("a","c") Q')
        # After ^J("a","b"), indicator = ("J", ("a",))
        # ^("c") = ^J("a","c")
        assert result.output == "2"

    def test_naked_updates_after_read(self, execute_mumps):
        """Naked indicator updates after read operations too."""
        result = execute_mumps(
            "TEST S ^K(1,2)=1 S ^K(3,4)=2 W ^K(1,2) S ^(3)=99 W ^K(1,3) Q"
        )
        # After S ^K(1,2), indicator = ("K", ("1",))
        # After S ^K(3,4), indicator = ("K", ("3",))
        # W ^K(1,2) updates indicator to ("K", ("1",))
        # S ^(3) = S ^K(1,3) = 99
        assert result.output == "199"
