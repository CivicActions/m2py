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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW exclusive")
    def test_new_exclusive(self, generate_python):
        """NEW exclusive generates selective scope (§8.2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: NEW scope cleanup on QUIT")
    def test_new_scope_cleanup(self, generate_python):
        """NEW scope cleanup on QUIT (§8.2.14)."""
        pytest.fail("Stub - implement test")
