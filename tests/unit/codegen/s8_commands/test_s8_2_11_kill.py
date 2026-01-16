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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL exclusive")
    def test_kill_exclusive(self, generate_python):
        """KILL exclusive generates selective delete (§8.2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL global")
    def test_kill_global(self, generate_python):
        """KILL ^GLOBAL generates global delete (§8.2.11)."""
        pytest.fail("Stub - implement test")
