"""Tests for DO command code generation (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
"""

import pytest


@pytest.mark.codegen
class TestDoCommandCodegen:
    """Codegen-level tests for DO command code generation (§8.2.3)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO call codegen")
    def test_do_call_codegen(self, generate_python):
        """DO generates function call (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with args")
    def test_do_with_args(self, generate_python):
        """DO with arguments generates parameterized call (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO block codegen")
    def test_do_block_codegen(self, generate_python):
        """DO block generates indented block (§8.2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO external routine")
    def test_do_external_routine(self, generate_python):
        """DO external routine generates import and call (§8.2.3)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestScopeStrategyCodegen:
    """Codegen tests for variable scope strategies.

    Based on FunctionSignature.scope_strategy, different Python patterns
    are generated for handling variable visibility and side effects.

    Reference: §6.3, §8.2.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pure function codegen")
    def test_pure_function_codegen(self, generate_python):
        """PURE_FUNCTION generates simple def with return.

        No side effects, returns value: def f(args) -> T
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subroutine codegen")
    def test_subroutine_codegen(self, generate_python):
        """SUBROUTINE generates def returning None or dict.

        Side effects only, no return value.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: function with outputs codegen")
    def test_function_with_outputs_codegen(self, generate_python):
        """FUNCTION_WITH_OUTPUTS generates tuple return.

        Returns value plus modified by-ref parameters.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: requires runtime codegen")
    def test_requires_runtime_codegen(self, generate_python):
        """REQUIRES_RUNTIME generates runtime scope access.

        Indirection/XECUTE defeats static analysis.
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestByRefParameterCodegen:
    """Codegen tests for by-reference parameter handling.

    When caller uses .X, the callee can modify X. Generated code uses
    a return-tuple pattern to propagate modified values back.

    Reference: §6.3, §8.2.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: byref call generates tuple unpack")
    def test_byref_call_generates_tuple_unpack(self, generate_python):
        """By-reference call generates tuple unpacking at call site.

        D SWAP(.A,.B) generates: a, b = swap(a, b)
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: byref callee returns modified")
    def test_byref_callee_returns_modified(self, generate_python):
        """By-reference callee returns modified values.

        Callee returns tuple of byref_outputs values.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: mixed byref and value params")
    def test_mixed_byref_and_value_params(self, generate_python):
        """Mixed by-ref and by-value parameters handled correctly.

        D SUB(A,.B,C) - only B is by-reference.
        """
        pytest.fail("Stub - implement test")
