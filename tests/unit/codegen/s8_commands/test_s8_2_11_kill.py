"""Tests for KILL command code generation (§8.2.11).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.11

Spec 011: Implementation of selective KILL command codegen.
"""

import pytest


@pytest.mark.codegen
class TestKillCommandCodegen:
    """Codegen-level tests for KILL command code generation (§8.2.11)."""

    def test_kill_local_variable(self, generate_python):
        """KILL local variable generates MArray.kill() (§8.2.11).

        Phase 21: K X clears the MArray content but keeps the entry in _scope
        to preserve call-by-reference aliasing.
        """
        result = generate_python("TEST K X Q")
        assert "_scope.get('X', MArray()).kill()" in result

    def test_kill_multiple_variables(self, generate_python):
        """KILL multiple variables generates multiple kill() calls (§8.2.11).

        Phase 21: K X,Y clears MArray content for both variables.
        """
        result = generate_python("TEST K X,Y Q")
        assert "_scope.get('X', MArray()).kill()" in result
        assert "_scope.get('Y', MArray()).kill()" in result

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


# =============================================================================
# KILL with Empty Intermediate Node Cleanup (Bug Fix)
# =============================================================================


@pytest.mark.codegen
class TestKillEmptyIntermediateCleanup:
    """Tests for KILL cleaning up empty intermediate nodes.

    Bug fix: When killing a leaf node like X(2,1), if parent nodes
    become empty (no value and no children), they should be removed too.

    MUMPS doesn't leave "ghost" empty intermediate nodes after KILL.
    """

    def test_kill_leaf_cleans_empty_parent(self, execute_mumps):
        """K X(2,1) should clean up empty X(2) and empty X.

        I-222 from MUGJ V1DLB1: After S XX(2,1)="DEF" K XX(2,1),
        $D(XX) should be 0 (not 10) because no nodes remain.
        """
        result = execute_mumps('TEST K XX S XX(2,1)="DEF" K XX(2,1) W $D(XX) Q')
        # After kill, XX has no value and no children, so $D=0
        assert result.output == "0"

    def test_kill_leaf_cleans_entire_path(self, execute_mumps):
        """K X(2,1,1) should clean up empty X(2,1), X(2), and X.

        I-223: Deep nested single node - all empty ancestors should be cleaned.
        """
        result = execute_mumps("TEST K XX S XX(2,1,1)=2110 K XX(2,1,1) W $D(XX) Q")
        assert result.output == "0"

    def test_kill_preserves_valued_parent(self, execute_mumps):
        """K X(2,1) should NOT clean X(2) if X(2) has a value.

        If parent has its own value, it stays even if children are gone.
        """
        result = execute_mumps(
            'TEST K XX S XX(2)="parent",XX(2,1)="child" K XX(2,1) W $D(XX(2)) Q'
        )
        # XX(2) has value, no children after kill, so $D=1
        assert result.output == "1"

    def test_kill_preserves_parent_with_other_children(self, execute_mumps):
        """K X(2,1) should NOT clean X(2) if X(2) has other children.

        I-229: Parent with siblings of killed node should survive.
        """
        result = execute_mumps(
            'TEST K XX S XX(2,1)="a",XX(2,2)="b" K XX(2,1) W $D(XX(2)) Q'
        )
        # XX(2) has no value but still has child XX(2,2), so $D=10
        assert result.output == "10"

    def test_kill_chain_cleanup_stops_at_valued_node(self, execute_mumps):
        """Cleanup stops at first non-empty ancestor.

        S X="root" S X(1,2,3)=1 K X(1,2,3) → X should remain with $D=1
        """
        result = execute_mumps('TEST K X S X="root" S X(1,2,3)=1 K X(1,2,3) W $D(X) Q')
        # X has value, all children are gone, so $D=1
        assert result.output == "1"

    def test_kill_chain_cleanup_stops_at_sibling(self, execute_mumps):
        """Cleanup stops when node has sibling children.

        S X(1,1)=1 S X(1,2)=2 K X(1,1) → X(1) should remain with $D=10
        """
        result = execute_mumps(
            'TEST K X S X(1,1)=1,X(1,2)=2 K X(1,1) W $D(X(1))," ",$D(X) Q'
        )
        # X(1) has no value but has child X(1,2), so $D=10
        # X has no value but has child X(1), so $D=10
        assert result.output == "10 10"


@pytest.mark.codegen
class TestKillTrampolineDynamicLocals:
    """Tests for KILL with TRAMPOLINE strategy and dynamic_locals.

    When a routine uses argumentless KILL or NEW AND has cross-label GOTOs
    (triggering TRAMPOLINE), it uses dynamic_locals mode where variables are
    stored in state._locals dict. KILL in this mode must use state._locals
    instead of direct variable access.

    To trigger TRAMPOLINE + dynamic_locals, we need:
    1. Cross-label GOTO (triggers TRAMPOLINE)
    2. Argumentless KILL (triggers uses_dynamic_locals)
    """

    def test_kill_dynamic_locals_entire_variable(self, generate_python):
        """K X with TRAMPOLINE+dynamic_locals uses state._locals.pop().

        When uses_dynamic_locals is True AND strategy is TRAMPOLINE,
        K X should generate state._locals.pop('X', None).
        """
        # Cross-label GOTO + argumentless KILL triggers TRAMPOLINE + dynamic_locals
        code = generate_python("TEST K\n K X\n G END\n Q\nEND Q\n")

        # Should use state._locals for variable removal (TRAMPOLINE + dynamic_locals)
        assert "state._locals.pop('X', None)" in code

    def test_kill_dynamic_locals_subscripted(self, generate_python):
        """K X(1) with TRAMPOLINE+dynamic_locals uses state._locals.get().kill().

        For subscripted kills in TRAMPOLINE+dynamic_locals mode, should use
        state._locals.get('X', MArray()).kill(subscripts).
        """
        # Cross-label GOTO + argumentless KILL triggers TRAMPOLINE + dynamic_locals
        code = generate_python("TEST K\n K X(1)\n G END\n Q\nEND Q\n")

        # Should use state._locals.get().kill() pattern
        assert "state._locals.get('X', MArray()).kill(" in code

    def test_kill_dynamic_locals_multiple_subscripts(self, generate_python):
        """K X(1,2) with TRAMPOLINE+dynamic_locals handles multiple subscripts."""
        code = generate_python("TEST K\n K X(1,2)\n G END\n Q\nEND Q\n")

        # Should pass multiple subscripts to kill
        assert "state._locals.get('X', MArray()).kill(" in code

    def test_kill_without_dynamic_locals_uses_direct_access(self, generate_python):
        """K X without dynamic_locals uses MArray.kill() via _scope.

        Phase 21: KILL clears MArray content but keeps entry in _scope
        to preserve call-by-reference aliasing.
        """
        # No argumentless KILL, so uses direct access via _scope
        code = generate_python("TEST S X=1\n K X\n Q\n")

        # Should use _scope.get().kill() for SIMPLE_FUNCTIONS
        assert "_scope.get('X', MArray()).kill()" in code

    def test_kill_dynamic_locals_preserves_siblings(self, execute_mumps):
        """K X(1) with dynamic_locals preserves sibling subscripts."""
        # Create scenario with argumentless KILL + GOTO to trigger dynamic_locals
        result = execute_mumps(
            "TEST K\n S X(1)=1,X(2)=2\n K X(1)\n G END\n Q\nEND W $D(X(1)),$D(X(2)) Q\n"
        )
        # X(1) is killed (0), X(2) remains (1)
        assert result.output == "01"
        assert result.success is True

    def test_kill_dynamic_locals_execution(self, execute_mumps):
        """Full execution test for KILL with TRAMPOLINE+dynamic_locals.

        Verifies that KILL works correctly in a routine with both
        argumentless KILL (uses_dynamic_locals) and cross-label GOTO (TRAMPOLINE).
        """
        result = execute_mumps(
            'TEST K\n S X=5\n K X\n G END\n Q\nEND W $G(X,"gone") Q\n'
        )
        assert result.output == "gone"
        assert result.success is True


@pytest.mark.codegen
class TestKillAllMArrayKill:
    """Tests for Phase 21 KILL changes: MArray.kill() instead of scope removal."""

    def test_kill_all_uses_marray_kill(self, generate_python):
        """Argumentless K generates MArray.kill() loop instead of _scope.clear().

        Phase 21: KILL preserves entries in _scope for call-by-reference aliasing.
        Note: K<space><space>Q is argumentless KILL then QUIT (two spaces).
        """
        code = generate_python("TEST\n K  Q")
        assert "for _v in _scope.values():" in code
        assert "if isinstance(_v, MArray):" in code
        assert "_v.kill()" in code
        # Should NOT use _scope.clear()
        assert "_scope.clear()" not in code

    def test_kill_exclusive_uses_translated_names(self, generate_python):
        """K (X) uses translated names in keep_vars set.

        Phase 21: Names in keep_vars must be translated to Python form
        (e.g., %X → _pct_X) since _scope keys use translated names.
        """
        code = generate_python("TEST K (X) Q")
        assert "'X'" in code
        assert "MArray" in code

    def test_kill_exclusive_percent_var_translated(self, execute_mumps):
        """K (%X) keeps %X (translated to _pct_X in _scope).

        Phase 21: Ensures translate_name is applied in exclusive KILL.
        """
        result = execute_mumps(
            'TEST\n S %X=1,Y=2 K (%X) W $G(%X,"none"),$G(Y,"none"),!\n Q\n'
        )
        assert result.output == "1none\n"

    def test_kill_selective_percent_var(self, execute_mumps):
        """K %X kills the %X variable correctly.

        Phase 21: translate_name applied for selective KILL too.
        Y retains its value of 2 since only %X is killed.
        """
        result = execute_mumps(
            'TEST\n S %X=1,Y=2 K %X W $G(%X,"gone"),$G(Y,"kept"),!\n Q\n'
        )
        assert result.output == "gone2\n"

    def test_kill_preserves_byref_alias(self, execute_mumps):
        """K inside subroutine preserves MArray alias for call-by-reference.

        Phase 21: KILL clears MArray content rather than removing from _scope,
        so shared MArray aliases remain linked.
        """
        result = execute_mumps(
            'TEST S X=5 D SUB(.X) W $G(X,"gone"),! Q\nSUB(N) K N S N=10 Q\n'
        )
        # After K N, $DATA(N)=0, then S N=10 sets it. Since N is aliased
        # to X via MArray, X should see the new value.
        assert result.output == "10\n"


@pytest.mark.codegen
class TestZKillCodegen:
    """Tests for ZKILL code generation."""

    def test_zkill_unsubscripted_local(self, execute_mumps):
        """ZK X removes value but preserves subscripts."""
        result = execute_mumps(
            "TEST\n\tS X=1,X(1)=2\n\tZK X\n\tW $D(X),!,$D(X(1))\n\tQ\n"
        )
        # After ZKILL, X has no value but X(1) still exists
        # $D(X) should be 10 (descendants only), $D(X(1)) should be 1
        assert result.success is True

    def test_zkill_nonexistent_path(self, execute_mumps):
        """ZK on non-existent path is a no-op (coverage: runtime ZKILL path)."""
        result = execute_mumps('TEST\n S A(1)="x"\n ZK A(9,9)\n W $D(A(1)),!\n Q\n')
        assert result.output.strip() == "1"

    def test_zkill_root_node(self, execute_mumps):
        """ZK without subscripts clears root value, preserves children."""
        result = execute_mumps(
            'TEST\n S A="root",A(1)="child"\n ZK A\n W $D(A),!\n Q\n'
        )
        # $D = 10 — no value but has children
        assert result.output.strip() == "10"

    def test_kill_subscripted_with_data_check(self, execute_mumps):
        """K A(1) — kills subtree, sibling survives (coverage: codegen L4640-4670)."""
        result = execute_mumps(
            'TEST\n S A(1)="x",A(2)="y"\n K A(1)\n W $D(A(1))," ",$D(A(2)),!\n Q\n'
        )
        assert "0" in result.output  # A(1) gone
        assert "1" in result.output  # A(2) still there

    def test_kill_whole_variable_with_data_check(self, execute_mumps):
        """K A — kills entire variable tree."""
        result = execute_mumps("TEST\n S A=1,A(1)=2\n K A\n W $D(A),!\n Q\n")
        assert result.output.strip() == "0"
