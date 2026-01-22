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
        """NEW exclusive generates loop to NEW non-kept variables (§8.2.14).

        Spec 011 (T072): N (X) generates a for loop that NEWs all variables except X.
        """
        result = generate_python("TEST N (X) Q")
        assert "for _var_name in list(_scope.keys()):" in result
        assert "if _var_name not in" in result
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
        """Argumentless NEW generates loop with NewScopeManager (§8.2.14).

        N (with no arguments, followed by two spaces) NEWs all local variables.
        Note: N<space><space>Q is argumentless NEW then QUIT.
        """
        result = generate_python("TEST\n N  Q")
        # Uses NewScopeManager with loop to new_var all variables
        assert "for _var_name in list(_scope.keys()):" in result
        assert "_new_mgr.new_var(_var_name)" in result

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
