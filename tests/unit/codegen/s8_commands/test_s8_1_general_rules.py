"""Tests for Command General Rules code generation (§8.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.1
"""

import pytest


@pytest.mark.codegen
class TestCommandGeneralRulesCodegen:
    """Codegen-level tests for command general rules code generation (§8.1)."""

    def test_postcondition_codegen(self, generate_python):
        """Postconditions generate if statements (§8.1).

        Spec 011 Phase 8: Command-level postconditions wrap statement
        in `if m_truth(cond):` block.
        """
        source = "TEST S:1 X=1 Q"
        code = generate_python(source)
        # Postcondition should generate if m_truth(cond): wrapper
        assert "if m_truth(1):" in code
        # The SET assignment should be inside the conditional
        assert "_scope.setdefault('X', MArray()).value = 1" in code

    def test_postcondition_false_skips_statement(self, execute_mumps):
        """False postcondition skips statement execution (§8.1).

        Spec 011 Phase 8: S:0 X=1 should not set X.
        """
        source = 'TEST S:0 X=1 W $G(X,"none"),! Q'
        result = execute_mumps(source)
        assert result.output == "none\n"

    def test_postcondition_expression_evaluation(self, execute_mumps):
        """Postcondition expression is evaluated at runtime (§8.1).

        Spec 011 Phase 8: S:A>3 B=1 evaluates A>3 at runtime.
        """
        source = 'TEST S A=5 S:A>3 B=1 W $G(B,"none"),! Q'
        result = execute_mumps(source)
        assert result.output == "1\n"

    def test_postcondition_expression_false(self, execute_mumps):
        """Postcondition expression false skips statement (§8.1).

        Spec 011 Phase 8: When A=2, A>3 is false, so B is not set.
        """
        source = 'TEST S A=2 S:A>3 B=1 W $G(B,"none"),! Q'
        result = execute_mumps(source)
        assert result.output == "none\n"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: timeout codegen")
    def test_timeout_codegen(self, generate_python):
        """Timeouts generate timeout handling code (§8.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: command sequence")
    def test_command_sequence(self, generate_python):
        """Command sequences generate statement sequences (§8.1)."""
        pytest.fail("Stub - implement test")
