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

    def test_timeout_codegen(self, generate_python, execute_mumps):
        """Timeouts generate timeout handling code (§8.1).

        Per Spec 009: Timeout arguments use m_read_timeout() for READ,
        m_lock_timeout() for LOCK, and direct timeout parameter for JOB.
        """
        # READ with timeout
        source = "TEST R X:3 W X Q"
        code = generate_python(source)

        # Should use _rt.read_line_timeout with timeout value
        assert "_rt.read_line_timeout" in code
        assert "3" in code  # timeout value present

        # LOCK with timeout is also working
        lock_source = 'TEST L +^A:2 W "locked" Q'
        lock_code = generate_python(lock_source)

        # Should have timeout parameter for lock
        assert "2" in lock_code  # timeout value

    def test_command_sequence(self, generate_python, execute_mumps):
        """Command sequences generate statement sequences (§8.1).

        Per §8.1: Multiple commands on same line execute left-to-right.
        Each command generates a separate Python statement.
        """
        source = "TEST S X=1 W X S X=2 W X Q"
        code = generate_python(source)

        # Should have multiple statements
        assert code.count("_scope.setdefault('X', MArray()).value") >= 2

        # Execute to verify sequence
        result = execute_mumps(source)
        assert result.output == "12"
        assert result.success is True
