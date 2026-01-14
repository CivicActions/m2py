"""Tests for Spec 009 User Story 8: KILL Command.

Tests the KILL command implementation for local and global variables.
KILL removes a node and all its descendants.

Acceptance Scenarios from spec.md:
1. S X=1 K X W $D(X) Q → "0" (simple variable, no children)
2. S X(1)=1 S X(1,2)=2 K X(1) W $D(X(1))," ",$D(X(1,2)) Q → "0 0" (kills descendants)
3. S ^G(1)=1 S ^G(1,2)=2 K ^G(1) W $D(^G(1)) Q → "0"
4. S ^H=1 S ^H(1)=2 K ^H W $D(^H) Q → "0" (kills entire tree)

Note: Tests use W X without ! since format control (!) codegen is not in scope.
"""

import pytest


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

    def test_kill_global_preserves_siblings(self, execute_mumps):
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
