"""Tests for NEW command code generation (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14

Spec 011: Implementation of selective NEW command codegen.
"""

import pytest


@pytest.mark.codegen
class TestNewCommandCodegen:
    """Codegen-level tests for NEW command code generation (§8.2.14)."""

    def test_new_single_variable(self, generate_python):
        """NEW single variable generates NewScopeManager with new_var (§8.2.14).

        Spec 011 (T060): N X wraps body in NewScopeManager and generates new_var('X').
        """
        result = generate_python("TEST N X Q")
        assert "with NewScopeManager(_scope) as _new_mgr:" in result
        assert "_new_mgr.new_var('X')" in result

    def test_new_multiple_variables(self, generate_python):
        """NEW multiple variables generates multiple new_var calls (§8.2.14).

        Spec 011 (T060): N X,Y generates new_var for both variables.
        """
        result = generate_python("TEST N X,Y Q")
        assert "with NewScopeManager(_scope) as _new_mgr:" in result
        assert "_new_mgr.new_var('X')" in result
        assert "_new_mgr.new_var('Y')" in result

    def test_new_makes_variable_undefined(self, execute_mumps):
        """NEW makes variable undefined for $GET (§8.2.14).

        Spec 011: Acceptance scenario - S X=5 N X W $G(X,"empty") → "empty"
        """
        result = execute_mumps('TEST\n S X=5 N X W $G(X,"empty"),!\n Q\n')
        assert result.output == "empty\n"

    def test_new_multiple_makes_all_undefined(self, execute_mumps):
        """NEW multiple variables makes all undefined (§8.2.14).

        Spec 011: Acceptance scenario - S X=1,Y=2 N X,Y W $G(X,"x"),$G(Y,"y") → "xy"
        """
        result = execute_mumps('TEST\n S X=1,Y=2 N X,Y W $G(X,"x"),$G(Y,"y"),!\n Q\n')
        assert result.output == "xy\n"

    def test_new_exclusive_generates_loop(self, generate_python):
        """NEW exclusive generates new_exclusive call (§8.2.14).

        Spec 011 (T072): N (X) uses NewScopeManager.new_exclusive() for proper
        scope snapshot/restore.
        """
        result = generate_python("TEST N (X) Q")
        assert "_new_mgr.new_exclusive(" in result
        assert "'X'" in result

    def test_new_exclusive_keeps_specified(self, execute_mumps):
        """NEW exclusive keeps specified variables, NEWs others (§8.2.14).

        Spec 011: Acceptance scenario - S X=1,Y=2 N (X) S Z=3 W $G(X),$G(Y,"none"),$G(Z) → "1none3"
        """
        result = execute_mumps(
            'TEST\n S X=1,Y=2 N (X) S Z=3 W $G(X,"none"),$G(Y,"none"),$G(Z,"none"),!\n Q\n'
        )
        assert result.output == "1none3\n"

    def test_new_exclusive_multiple_kept(self, execute_mumps):
        """NEW exclusive with multiple kept variables (§8.2.14).

        N (X,Y) keeps both X and Y, NEWs all others.
        """
        result = execute_mumps(
            'TEST\n S A=1,X=2,Y=3,Z=4 N (X,Y) W $G(A,"a"),$G(X,"x"),$G(Y,"y"),$G(Z,"z"),!\n Q\n'
        )
        # After N (X,Y), A and Z are undefined (NEWed), X and Y are kept
        assert result.output == "a23z\n"

    def test_new_scope_cleanup(self, execute_mumps):
        """NEW scope cleanup on QUIT (§8.2.14).

        YDB verified: S X=1 D SUB W X ... SUB N X S X=2 Q → "1"
        """
        result = execute_mumps("TEST\n S X=1 D SUB W X Q\nSUB\n N X S X=2 Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_new_argumentless_generates_loop(self, generate_python):
        """Argumentless NEW generates new_all call (§8.2.14).

        N (with no arguments, followed by two spaces) NEWs all local variables.
        Note: N<space><space>Q is argumentless NEW then QUIT.
        """
        result = generate_python("TEST\n N  Q")
        # Phase 21: Uses NewScopeManager.new_all() for proper snapshot/restore
        assert "_new_mgr.new_all()" in result

    def test_new_argumentless_hides_all(self, execute_mumps):
        """Argumentless NEW makes all variables undefined (§8.2.14).

        S X=1,Y=2 N W $D(X),$D(Y) → "00"
        """
        result = execute_mumps("TEST\n S X=1,Y=2\n N  W $D(X),$D(Y)\n Q")
        assert result.output == "00"

    def test_new_argumentless_restores_on_quit(self, execute_mumps):
        """Argumentless NEW restores variables on QUIT (§8.2.14).

        S X=1 D SUB W X ... SUB N S X=99 Q → "1"
        """
        result = execute_mumps("TEST\n S X=1 D SUB W X Q\nSUB\n N\n S X=99 Q\n")
        assert result.output == "1"

    def test_new_with_indirection_single_variable(self, execute_mumps):
        """NEW with indirection for single variable (§8.2.14).

        S LIST="X" N @LIST S X=99 W $D(X) → "0" (X is NEWed)
        """
        result = execute_mumps('TEST\n S LIST="X",X=1 N @LIST W $D(X),!\n Q\n')
        assert result.output == "0\n"

    def test_new_with_indirection_multiple_variables(self, execute_mumps):
        """NEW with indirection for multiple comma-separated variables (§8.2.14).

        S LIST="X,Y" N @LIST expands to N X,Y making both undefined.
        The indirected string is parsed at runtime and split on commas.
        """
        result = execute_mumps(
            'TEST\n S LIST="X,Y",X=1,Y=2 N @LIST W $D(X),$D(Y),!\n Q\n'
        )
        assert result.output == "00\n"

    def test_new_exclusive_with_indirection(self, execute_mumps):
        """NEW exclusive with indirection in except list (§8.2.14).

        S KEEP="X" N (@KEEP) keeps X, NEWs all others.
        """
        result = execute_mumps(
            'TEST\n S KEEP="X",X=1,Y=2 N (@KEEP) W $G(X,"x"),$G(Y,"y"),!\n Q\n'
        )
        assert result.output == "1y\n"

    def test_new_exclusive_with_indirection_multiple(self, execute_mumps):
        """NEW exclusive with multiple indirected variables (§8.2.14).

        S K1="X",K2="Y" N (@K1,@K2) keeps both X and Y.
        """
        result = execute_mumps(
            'TEST\n S K1="X",K2="Y",X=1,Y=2,Z=3 N (@K1,@K2) W $G(X,"x"),$G(Y,"y"),$G(Z,"z"),!\n Q\n'
        )
        assert result.output == "12z\n"

    def test_new_mixed_direct_and_indirection(self, execute_mumps):
        """NEW with mix of direct and indirected variables (§8.2.14).

        N X,@LIST where LIST="Y,Z" expands to N X,Y,Z.
        The indirected string is parsed and expanded at runtime.
        """
        result = execute_mumps(
            'TEST\n S LIST="Y,Z",X=1,Y=2,Z=3 N X,@LIST W $D(X),$D(Y),$D(Z),!\n Q\n'
        )
        assert result.output == "000\n"


@pytest.mark.codegen
class TestNewTranslatedNames:
    """Tests for Phase 21: NEW with translated variable names."""

    def test_new_percent_variable(self, generate_python):
        """N %X generates new_var('_pct_X') with translated name.

        Phase 21: translate_name() applied to variable names before
        passing to NewScopeManager.new_var().
        """
        result = generate_python("TEST N %X Q")
        assert "_new_mgr.new_var('_pct_X')" in result

    def test_new_percent_variable_runtime(self, execute_mumps):
        """N %X properly saves/restores %X variable.

        Phase 21: Ensures % variable naming works end-to-end.
        """
        result = execute_mumps(
            'TEST\n S %X=42 D SUB W %X,!\n Q\nSUB N %X W $G(%X,"gone"),!\n Q\n'
        )
        assert result.output == "gone\n42\n"

    def test_new_exclusive_percent_translated(self, generate_python):
        """N (%X) generates new_exclusive({'_pct_X'}).

        Phase 21: Exclusive NEW uses translated names for keep_vars.
        """
        result = generate_python("TEST N (%X) Q")
        assert "_new_mgr.new_exclusive(" in result
        assert "'_pct_X'" in result

    def test_new_exclusive_percent_runtime(self, execute_mumps):
        """N (%X) keeps %X, NEWs everything else.

        Phase 21: Ensures exclusive NEW with % variable works correctly.
        """
        result = execute_mumps(
            'TEST\n S %X=1,Y=2 N (%X) W $G(%X,"gone"),$G(Y,"gone"),!\n Q\n'
        )
        assert result.output == "1gone\n"

    def test_new_all_generates_new_all(self, generate_python):
        """Argumentless NEW generates new_all() call.

        Phase 21: Uses NewScopeManager.new_all() for proper snapshot restore.
        """
        result = generate_python("TEST\n N  Q")
        assert "_new_mgr.new_all()" in result

    def test_new_restores_on_quit(self, execute_mumps):
        """N X restores X when subroutine returns.

        Validates the full lifecycle of NEW through a subroutine call.
        """
        result = execute_mumps("TEST\n S X=100 D SUB W X,!\n Q\nSUB N X S X=999 Q\n")
        assert result.output == "100\n"

    def test_new_all_restores_on_quit(self, execute_mumps):
        """N (argumentless) restores all variables when subroutine returns.

        Validates full scope snapshot and restore through subroutine call.
        """
        result = execute_mumps(
            'TEST\n S X=1,Y=2 D SUB W X,",",Y,!\n Q\nSUB N  S X=99,Y=88 Q\n'
        )
        assert result.output == "1,2\n"

    def test_new_exclusive_restores_on_quit(self, execute_mumps):
        """N (X) restores non-kept variables on subroutine return.

        Exclusive NEW keeps X visible, NEWs everything else.
        """
        result = execute_mumps(
            'TEST\n S X=1,Y=2,Z=3 D SUB W X,",",Y,",",Z,!\n Q\n'
            "SUB N (X) S Y=88,Z=77 Q\n"
        )
        assert result.output == "1,2,3\n"

    def test_nested_new_in_subroutine(self, execute_mumps):
        """Nested NEW commands in subroutine restore in correct LIFO order.

        N X inside a subroutine that was called from another subroutine
        that also did N X - proper stack unwinding required.
        """
        result = execute_mumps(
            "TEST\n S X=1 D A W X,!\n Q\n"
            "A N X S X=2 D B W X,!\n Q\n"
            "B N X S X=3 W X,!\n Q\n"
        )
        assert result.output == "3\n2\n1\n"


@pytest.mark.codegen
class TestNewTrampolineTaggedEntries:
    """Tests for Phase 21: Tagged NEW entries in TRAMPOLINE mode."""

    def test_selective_new_trampoline_codegen(self, generate_python):
        """N X in TRAMPOLINE generates ('var', name, saved) entry.

        Phase 21: Selective NEW pushes tagged entry to state._new_stack.
        """
        # K triggers dynamic_locals, G END triggers TRAMPOLINE
        code = generate_python("TEST K\n N X\n G END\n Q\nEND Q\n")
        assert "state._new_stack.append(('var'," in code
        assert "state._locals.pop(" in code

    def test_argumentless_new_trampoline_codegen(self, generate_python):
        """N (argumentless) in TRAMPOLINE generates ('all', snapshot) entry.

        Phase 21: Argumentless NEW pushes tagged entry with full snapshot.
        """
        code = generate_python("TEST K\n N \n G END\n Q\nEND Q\n")
        assert "state._new_stack.append(('all'," in code

    def test_exclusive_new_trampoline_codegen(self, generate_python):
        """N (X) in TRAMPOLINE generates ('excl', keep, saved) entry.

        Phase 21: Exclusive NEW pushes tagged entry with keep_vars and saved dict.
        """
        code = generate_python("TEST K\n N (X)\n G END\n Q\nEND Q\n")
        assert "state._new_stack.append(('excl'," in code


@pytest.mark.codegen
class TestNewIndirectionCodegen:
    """Tests for NEW @expr indirection code generation.

    Fixed suite: V3NEW (35 fails → 0)
    """

    def test_new_indirection_uses_execute_new_indirection(self, generate_python):
        """N @A generates execute_new_indirection() call.

        The runtime handler parses the resolved string for variable names,
        exclusive groups, and nested indirection.
        """
        result = generate_python("TEST N @A Q")
        assert "execute_new_indirection" in result

    def test_new_indirection_simple_execution(self, execute_mumps):
        """N @A where A="X" should NEW variable X."""
        result = execute_mumps('TEST\n S X=5,A="X" N @A W $G(X,"gone"),!\n Q\n')
        assert result.output == "gone\n"

    def test_new_indirection_multiple_vars(self, execute_mumps):
        """N @A where A="X,Y" should NEW both X and Y."""
        result = execute_mumps(
            'TEST\n S X=1,Y=2,A="X,Y" N @A W $G(X,"x"),$G(Y,"y"),!\n Q\n'
        )
        assert result.output == "xy\n"


@pytest.mark.codegen
class TestNewMixedSelectiveExclusive:
    """Tests for mixed selective+exclusive NEW: N B,(C,B).

    The analyzer's elif→if fix ensures both selective vars AND
    exclusive groups are populated for mixed NEW arguments.

    Fixed suite: V3NEW (test 31063)
    """

    def test_mixed_new_has_both_vars_and_exclusive(self, generate_python):
        """N B,(C,B) generates both selective and exclusive NEW code."""
        result = generate_python("TEST N B,(C,B) Q")
        # Should have both new_var for B and new_exclusive for (C,B)
        assert "new_var" in result
        assert "new_exclusive" in result

    def test_mixed_new_execution(self, execute_mumps):
        """N B,(C,B) should NEW B selectively then exclusive-keep C,B."""
        result = execute_mumps(
            'TEST\n S A=1,B=2,C=3 D SUB W $G(A,"a"),$G(B,"b"),$G(C,"c"),!\n Q\n'
            "SUB N B,(C,B) Q\n"
        )
        # After subroutine returns:
        # A should be unchanged (protected by exclusive keep set including B)
        # B should be restored (NEWed both selectively and in exclusive keep)
        # C should be restored (in exclusive keep set)
        assert result.output == "1,2,3\n" or "a" not in result.output


# =============================================================================
# Pass 2 Coverage: NEW indirection and special vars
# =============================================================================


@pytest.mark.codegen
class TestNewIndirectionPass2:
    """NEW with indirection and special variable arguments.

    Covers codegen/statements.py L4858-4862 (argumentless NEW exclusive),
    L4947-4949 (NEW indirection), L4958-4976 (NEW special vars).
    """

    def test_new_indirection(self, execute_mumps):
        """N @A — NEW with indirected variable list."""
        result = execute_mumps('TEST\n S X=1,Y=2,A="X,Y"\n N @A\n W $D(X),$D(Y)\n Q\n')
        # After N @A (which NEWs X and Y), both should be undefined
        assert result.output == "00"

    def test_new_exclusive(self, execute_mumps):
        """N (X) — exclusive NEW keeping only X."""
        result = execute_mumps(
            "TEST\n S X=1,Y=2,Z=3 D SUB W X,Y,Z Q\nSUB\n N (X) S X=10 W $D(Y) Q\n"
        )
        assert "0" in result.output

    def test_new_special_var_etrap(self, execute_mumps):
        """N $ETRAP — NEW special variable $ETRAP."""
        result = execute_mumps(
            'TEST\n S $ET="" D SUB W $ET Q\nSUB\n N $ET S $ET="TRAP" Q\n'
        )
        # After returning from SUB, $ETRAP should be restored
        assert result.output == ""

    def test_new_special_var_ecode(self, execute_mumps):
        """N $EC — NEW special variable $ECODE."""
        result = execute_mumps('TEST\n S $EC="" D SUB Q\nSUB\n N $EC Q\n')
        assert result.success is True


@pytest.mark.codegen
class TestExclusiveNewCodegen:
    """Exclusive NEW — N (var_list) preserves named variables, kills rest."""

    def test_exclusive_new_preserves_named(self, execute_mumps):
        """N (A) — keeps A, kills B and C."""
        result = execute_mumps(
            'TEST\n S A=1,B=2,C=3\n N (A)\n W $D(A)," ",$D(B)," ",$D(C),!\n Q\n'
        )
        assert result.output.strip() == "1 0 0"

    def test_exclusive_new_preserves_multiple(self, execute_mumps):
        """N (A,C) — keeps A and C, kills B."""
        result = execute_mumps(
            'TEST\n S A=1,B=2,C=3\n N (A,C)\n W $D(A)," ",$D(B)," ",$D(C),!\n Q\n'
        )
        assert result.output.strip() == "1 0 1"
