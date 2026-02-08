"""Unit tests for V1IDARG-related fixes.

Tests for indirection resolver and runtime fixes for:
- I-425: _to_mumps_bool using m_truth for proper MUMPS boolean semantics
- I-430: nested KILL indirection with comma-separated @ expressions
- I-442: SET indirection with function-valued targets and subscript evaluation
"""

from m2py.runtime import MUMPSRuntime, MArray
from m2py.core.scope import CurrentScope
from m2py.core.indirection import IndirectionResolver, IndirectionContext


class TestToMumpsBool:
    """Tests for _to_mumps_bool using proper MUMPS truth semantics."""

    def setup_method(self):
        """Set up runtime and resolver for each test."""
        self.rt = MUMPSRuntime()
        self.scope = {}
        self.cs = CurrentScope.from_generated_context(self.scope)
        self.resolver = IndirectionResolver(self.rt, self.cs)

    def test_numeric_string_starting_with_zero_is_false(self):
        """String '0.00E+2=1' should be FALSE (leading zero)."""
        # The string "0.00E+2=1" has numeric interpretation 0.00E+2 = 0
        result = self.resolver._to_mumps_bool("0.00E+2=1")
        assert result == 0

    def test_numeric_string_with_leading_digit_is_truthy(self):
        """String '2=2' should be TRUE (leading 2)."""
        result = self.resolver._to_mumps_bool("2=2")
        assert result == 1  # 2 is truthy

    def test_non_numeric_string_is_false(self):
        """String 'ABC' should be FALSE (starts with letter, numeric = 0)."""
        result = self.resolver._to_mumps_bool("ABC")
        assert result == 0

    def test_empty_string_is_false(self):
        """Empty string should be FALSE."""
        result = self.resolver._to_mumps_bool("")
        assert result == 0

    def test_none_is_false(self):
        """None should be FALSE."""
        result = self.resolver._to_mumps_bool(None)
        assert result == 0

    def test_zero_integer_is_false(self):
        """Integer 0 should be FALSE."""
        result = self.resolver._to_mumps_bool(0)
        assert result == 0

    def test_nonzero_integer_is_true(self):
        """Integer 5 should be TRUE."""
        result = self.resolver._to_mumps_bool(5)
        assert result == 1


class TestResolveToNameCommaList:
    """Tests for resolve_to_name preserving comma-separated argument lists."""

    def setup_method(self):
        """Set up runtime and resolver for each test."""
        self.rt = MUMPSRuntime()

    def test_resolve_preserves_comma_separated_at_expressions(self):
        """Z="@A(1),@B(1)" should NOT be resolved, returned as-is."""
        A = MArray()
        A[1] = "A(2)"
        B = MArray()
        B[1] = "B(2),B(3)"
        Z = MArray()
        Z.value = "@A(1),@B(1)"

        scope = {"A": A, "B": B, "Z": Z}
        cs = CurrentScope.from_generated_context(scope)
        resolver = IndirectionResolver(self.rt, cs)

        # With validate=False for KILL indirection patterns
        result = resolver.resolve_to_name("Z", levels=1, validate=False)
        # Should return the comma-separated list, not resolve the first @
        assert result == "@A(1),@B(1)"

    def test_resolve_single_at_expression_is_resolved(self):
        """Z="@A(1)" should be resolved to the target."""
        A = MArray()
        A[1] = "A(2)"
        Z = MArray()
        Z.value = "@A(1)"

        scope = {"A": A, "Z": Z}
        cs = CurrentScope.from_generated_context(scope)
        resolver = IndirectionResolver(self.rt, cs)

        result = resolver.resolve_to_name("Z", levels=1, validate=False)
        # Single @ should be resolved
        assert result == "A(2)"


class TestKillIndirectedNestedAt:
    """Tests for kill_indirected handling nested @ expressions."""

    def setup_method(self):
        """Set up runtime for each test."""
        self.rt = MUMPSRuntime()

    def test_kill_nested_at_expressions(self):
        """K @Z where Z="@A(1),@B(1)" should recursively resolve and kill."""
        A = MArray()
        A[1] = "A(2)"
        A[2] = 1

        B = MArray()
        B[1] = "B(2),B(3)"
        B[2] = 1
        B[(3, 3)] = 1

        Z = MArray()
        Z.value = "@A(1),@B(1)"

        scope = {"A": A, "B": B, "Z": Z}

        # Kill via indirection
        self.rt.kill_indirected("Z", scope, levels=1)

        # Check that targets were killed
        # A(2) should be killed (via @A(1) -> A(1)="A(2)")
        # MArray.get returns "" for missing keys, not None
        assert A.get((2,)) == "", "A(2) should be killed"

        # B(2) and B(3) should be killed (via @B(1) -> B(1)="B(2),B(3)")
        assert B.get((2,)) == "", "B(2) should be killed"
        # B(3,3) should also be killed (descendant of B(3))
        assert B.get((3, 3)) == "", "B(3,3) should be killed"

    def test_simple_kill_indirection(self):
        """K @A where A="B" should kill B."""
        A = MArray()
        A.value = "B"
        B = MArray()
        B.value = 1

        scope = {"A": A, "B": B}

        self.rt.kill_indirected("A", scope, levels=1)

        # B should be killed
        assert "B" not in scope


class TestSetIndirectedSubscriptEval:
    """Tests for set_indirected evaluating subscript variable references."""

    def setup_method(self):
        """Set up runtime for each test."""
        self.rt = MUMPSRuntime()

    def test_set_global_with_subscript_variable(self):
        """S with target "^V1A(I)" where I=1 should set ^V1A(1)."""
        idx = MArray()
        idx.value = 1

        scope = {"I": idx}
        self.rt.set_indirected("^V1A(I)", "test value", scope, levels=0)

        # Should have set ^V1A(1), not ^V1A(I)
        result = self.rt.globals.get("V1A", ("1",))
        assert result == "test value"

        # ^V1A(I) should NOT exist (globals.get returns None for missing)
        result_literal = self.rt.globals.get("V1A", ("I",))
        assert result_literal is None

    def test_set_global_with_multiple_subscript_variables(self):
        """S with target "^G(X,Y)" where X=1, Y=2 should set ^G(1,2)."""
        X = MArray()
        X.value = 1
        Y = MArray()
        Y.value = 2

        scope = {"X": X, "Y": Y}

        self.rt.set_indirected("^G(X,Y)", "test", scope, levels=0)

        # Should have set ^G(1,2)
        result = self.rt.globals.get("G", ("1", "2"))
        assert result == "test"

    def test_set_global_with_literal_subscript(self):
        """S with target "^G(1)" should work without variable resolution."""
        scope = {}

        self.rt.set_indirected("^G(1)", "test", scope, levels=0)

        # Should have set ^G(1)
        result = self.rt.globals.get("G", ("1",))
        assert result == "test"

    def test_set_local_via_indirection(self):
        """S @X=5 where X="A" should set A=5."""
        X = MArray()
        X.value = "A"
        A = MArray()

        scope = {"X": X, "A": A}

        # levels=1 means resolve X to get target "A"
        self.rt.set_indirected("X", "5", scope, levels=1)

        # Should have set A=5
        assert A.value == "5"


class TestI425FullPattern:
    """Integration test for I-425 full pattern."""

    def test_if_indirection_with_nested_subscripts(self):
        """I @A(1) where A(1)="A(@B,@B(2)),@B" with complex subscript chain."""
        rt = MUMPSRuntime()

        A = MArray()
        A[1] = "A(@B,@B(2)),@B"
        A[2, 3] = "0.00E+2=1"  # This evaluates to 0 (FALSE)

        B = MArray()
        B.value = "B(1)"
        B[1] = 2
        B[2] = "@B(3)"
        B[3] = "B(4)"
        B[4] = 3

        scope = {"A": A, "B": B}
        cs = CurrentScope.from_generated_context(scope)
        resolver = IndirectionResolver(rt, cs)

        # Full resolution with ARGUMENT context
        result = resolver.resolve(
            "A(1)",
            levels=1,
            context=IndirectionContext.ARGUMENT,
            treat_empty_as_truthy=True,
        )

        # A(1) = "A(@B,@B(2)),@B"
        # This is split: ["A(@B,@B(2))", "@B"]
        # A(@B,@B(2)) -> A(2,3) = "0.00E+2=1" -> 0 (FALSE)
        # @B -> B(1) -> 2 (TRUE)
        # FALSE AND TRUE = FALSE
        assert result == 0
