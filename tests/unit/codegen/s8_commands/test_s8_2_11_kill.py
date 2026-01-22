"""Tests for KILL command code generation (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11

Spec 011: Implementation of selective KILL command codegen.
"""

import pytest


@pytest.mark.codegen
class TestKillCommandCodegen:
    """Codegen-level tests for KILL command code generation (§8.2.11)."""

    def test_kill_local_variable(self, generate_python):
        """KILL local variable generates _scope.pop() (§8.2.11).

        Spec 011 (T064): K X generates _scope.pop('X', None).
        """
        result = generate_python("TEST K X Q")
        assert "_scope.pop('X', None)" in result

    def test_kill_multiple_variables(self, generate_python):
        """KILL multiple variables generates multiple pops (§8.2.11).

        Spec 011 (T064): K X,Y generates pops for both variables.
        """
        result = generate_python("TEST K X,Y Q")
        assert "_scope.pop('X', None)" in result
        assert "_scope.pop('Y', None)" in result

    def test_kill_subscripted_variable(self, generate_python):
        """KILL subscripted variable generates .kill() call (§8.2.11).

        Spec 011 (T065): K A(1) generates _scope.get('A', MArray()).kill(1).
        """
        result = generate_python("TEST K A(1) Q")
        assert "_scope.get('A', MArray()).kill(" in result

    def test_kill_makes_variable_undefined(self, execute_mumps):
        """KILL makes variable undefined for $GET (§8.2.11).

        Spec 011: Acceptance scenario 1 - S X=5 K X W $G(X,"gone") → "gone"
        """
        result = execute_mumps('TEST\n S X=5 K X W $G(X,"gone"),!\n Q\n')
        assert result.output == "gone\n"

    def test_kill_multiple_makes_all_undefined(self, execute_mumps):
        """KILL multiple variables makes all undefined (§8.2.11).

        Spec 011: Acceptance scenario 2 - S X=1,Y=2 K X,Y W $G(X,"x"),$G(Y,"y") → "xy"
        """
        result = execute_mumps('TEST\n S X=1,Y=2 K X,Y W $G(X,"x"),$G(Y,"y"),!\n Q\n')
        assert result.output == "xy\n"

    def test_kill_subscript_preserves_siblings(self, execute_mumps):
        """KILL subscript only removes that node, not siblings (§8.2.11).

        Spec 011: Acceptance scenario 3 - S A(1)=1,A(2)=2 K A(1) → "k2"
        """
        result = execute_mumps(
            'TEST\n S A(1)=1,A(2)=2 K A(1) W $G(A(1),"k"),$G(A(2),"k"),!\n Q\n'
        )
        assert result.output == "k2\n"

    def test_kill_undefined_variable_noop(self, execute_mumps):
        """KILL of undefined variable should be a no-op (§8.2.11).

        Spec 011 (T066): KILL of undefined variable should not error.
        """
        result = execute_mumps('TEST\n K X W $G(X,"still gone"),!\n Q\n')
        assert result.output == "still gone\n"

    def test_kill_exclusive_generates_loop(self, generate_python):
        """KILL exclusive generates loop to KILL non-kept variables (§8.2.11).

        Spec 011 (T073): K (X) generates a for loop that KILLs all variables except X.
        """
        result = generate_python("TEST K (X) Q")
        assert "for _var_name in list(_scope.keys()):" in result
        assert "if _var_name not in" in result
        assert "'X'" in result

    def test_kill_exclusive_keeps_specified(self, execute_mumps):
        """KILL exclusive keeps specified variables, KILLs others (§8.2.11).

        Spec 011: Acceptance scenario - S X=1,Y=2,Z=3 K (X) W $G(X),$G(Y,"none"),$G(Z,"none") → "1nonenone"
        """
        result = execute_mumps(
            'TEST\n S X=1,Y=2,Z=3 K (X) W $G(X,"none"),$G(Y,"none"),$G(Z,"none"),!\n Q\n'
        )
        assert result.output == "1nonenone\n"

    def test_kill_exclusive_multiple_kept(self, execute_mumps):
        """KILL exclusive with multiple kept variables (§8.2.11).

        K (X,Y) keeps both X and Y, KILLs all others.
        """
        result = execute_mumps(
            'TEST\n S A=1,X=2,Y=3,Z=4 K (X,Y) W $G(A,"a"),$G(X,"x"),$G(Y,"y"),$G(Z,"z"),!\n Q\n'
        )
        # After K (X,Y), A and Z are undefined (KILLed), X and Y are kept
        assert result.output == "a23z\n"

    def test_kill_global(self, execute_mumps):
        """KILL ^GLOBAL deletes entire global tree (§8.2.11)."""
        result = execute_mumps("TEST S ^G(1)=1,^G(2)=2 K ^G W $D(^G),! Q")
        assert result.success
        assert result.output.rstrip() == "0"

    def test_kill_global_subscript(self, execute_mumps):
        """KILL ^GLOBAL(sub) deletes subtree (§8.2.11)."""
        result = execute_mumps(
            "TEST S ^G(1)=1,^G(2)=2 K ^G(1) W $D(^G(1)),$D(^G(2)),! Q"
        )
        assert result.success
        assert result.output.rstrip() == "01"

    def test_kill_global_preserves_siblings(self, execute_mumps):
        """KILL ^G(1) preserves ^G(2) and ^G root (§8.2.11)."""
        result = execute_mumps(
            'TEST S ^G="root",^G(1)=1,^G(2)=2 K ^G(1) W $G(^G),^G(2),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "root2"


# =============================================================================
# KILL Command Tests (consolidated from test_spec_009_kill.py)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec009
class TestKillLocalVariable:
    """Tests for KILL on local variables."""

    def test_scenario_1_kill_simple_variable(self, execute_mumps):
        """Scenario 1: K X kills simple variable.

        Given: S X=1 K X W $D(X) Q
        Then: Output is "0" (variable no longer exists)
        """
        result = execute_mumps("TEST S X=1 K X W $D(X) Q")
        assert result.output == "0"

    def test_scenario_2_kill_with_descendants(self, execute_mumps):
        """Scenario 2: K X(1) kills node and all descendants.

        Given: S X(1)=1 S X(1,2)=2 K X(1) W $D(X(1))," ",$D(X(1,2)) Q
        Then: Output is "0 0" (both X(1) and X(1,2) are gone)
        """
        result = execute_mumps(
            'TEST S X(1)=1 S X(1,2)=2 K X(1) W $D(X(1))," ",$D(X(1,2)) Q'
        )
        assert result.output == "0 0"

    def test_kill_preserves_sibling_nodes(self, execute_mumps):
        """K X(1) should not affect X(2) or X."""
        result = execute_mumps(
            'TEST S X=0 S X(1)=1 S X(2)=2 K X(1) W $D(X),"-",$D(X(1)),"-",$D(X(2)) Q'
        )
        # X still has value (1) and children (X(2)), so $D(X)=11
        # X(1) was killed, $D(X(1))=0
        # X(2) still exists, $D(X(2))=1
        assert result.output == "11-0-1"


@pytest.mark.codegen
@pytest.mark.spec009
class TestKillGlobalVariable:
    """Tests for KILL on global variables."""

    def test_scenario_3_kill_global_subscript(self, execute_mumps):
        """Scenario 3: K ^G(1) kills global node and descendants.

        Given: S ^G(1)=1 S ^G(1,2)=2 K ^G(1) W $D(^G(1)) Q
        Then: Output is "0"
        """
        result = execute_mumps("TEST S ^G(1)=1 S ^G(1,2)=2 K ^G(1) W $D(^G(1)) Q")
        assert result.output == "0"

    def test_scenario_4_kill_entire_global_tree(self, execute_mumps):
        """Scenario 4: K ^H kills entire global tree.

        Given: S ^H=1 S ^H(1)=2 K ^H W $D(^H) Q
        Then: Output is "0" (entire tree is gone)
        """
        result = execute_mumps("TEST S ^H=1 S ^H(1)=2 K ^H W $D(^H) Q")
        assert result.output == "0"

    def test_kill_global_preserves_siblings_spec009(self, execute_mumps):
        """K ^G(1) should not affect ^G(2) or ^G."""
        result = execute_mumps(
            'TEST S ^G=0 S ^G(1)=1 S ^G(2)=2 K ^G(1) W $D(^G),"-",$D(^G(1)),"-",$D(^G(2)) Q'
        )
        # ^G has value (1) and children (^G(2)), so $D(^G)=11
        # ^G(1) killed, $D=0
        # ^G(2) still exists, $D=1
        assert result.output == "11-0-1"


@pytest.mark.codegen
@pytest.mark.spec009
class TestKillEdgeCases:
    """Edge case tests for KILL command."""

    def test_kill_nonexistent_variable(self, execute_mumps):
        """K X on nonexistent variable should be no-op."""
        result = execute_mumps("TEST K X W $D(X) Q")
        assert result.output == "0"

    def test_kill_nonexistent_subscript(self, execute_mumps):
        """K X(1) when X(1) doesn't exist should be no-op."""
        result = execute_mumps("TEST S X=1 K X(1) W $D(X) Q")
        # X still has its value, no children
        assert result.output == "1"

    def test_kill_deep_subscript(self, execute_mumps):
        """K X(1,2,3) should kill only that subtree."""
        result = execute_mumps(
            'TEST S X(1,2,3)=1 S X(1,2,3,4)=2 S X(1,2)=0 K X(1,2,3) W $D(X(1,2)),"-",$D(X(1,2,3)) Q'
        )
        # X(1,2) has value (1), no children after kill (0), so $D=1
        # X(1,2,3) was killed, $D=0
        assert result.output == "1-0"

    def test_independent_test_from_tasks(self, execute_mumps):
        """Independent test from tasks.md.

        S X=1 S X(1)=2 K X(1) → X has value but X(1) is gone
        """
        result = execute_mumps('TEST S X=1 S X(1)=2 K X(1) W $D(X),"-",$D(X(1)) Q')
        # X has value (1), no children after kill, so $D=1
        # X(1) killed, $D=0
        assert result.output == "1-0"


@pytest.mark.codegen
@pytest.mark.spec009
class TestKillNakedReference:
    """Tests for KILL with naked global references."""

    def test_kill_naked_reference(self, execute_mumps):
        """KILL with naked reference resolves correctly.

        S ^G(1)=1,^(2)=2 K ^(1) W $D(^G(1)),$D(^G(2)) → "01"
        After S ^(2)=2, naked indicator is G with base subscripts ()
        So K ^(1) kills ^G(1)
        """
        result = execute_mumps("TEST S ^G(1)=1,^(2)=2 K ^(1) W $D(^G(1)),$D(^G(2)) Q")
        assert result.output == "01"

    def test_kill_naked_with_subscripts(self, execute_mumps):
        """KILL naked reference with multiple subscripts.

        S ^H(1,2)=1 - sets ^H(1,2)=1, naked indicator = H(1,2)
        S ^(3,4)=2 - replaces last subscript: ^H(1,3,4)=2, naked = H(1,3,4)
        K ^(3) - replaces last subscript: kills ^H(1,3,3) (doesn't exist)
        $D(^H(1,3)) = 10 (has descendants but no value)
        $D(^H(1,3,4)) = 1 (has value)
        Result: "101"
        """
        result = execute_mumps(
            "TEST S ^H(1,2)=1 S ^(3,4)=2 K ^(3) W $D(^H(1,3)),$D(^H(1,3,4)) Q"
        )
        assert result.output == "101"
