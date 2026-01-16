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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW scope cleanup on QUIT")
    def test_new_scope_cleanup(self, generate_python):
        """NEW scope cleanup on QUIT (§8.2.14)."""
        pytest.fail("Stub - implement test")
