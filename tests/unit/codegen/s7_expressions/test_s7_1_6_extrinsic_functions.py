"""Tests for Extrinsic Functions code generation (§7.1.6).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6
"""

import pytest


@pytest.mark.codegen
class TestExtrinsicFunctionsCodegen:
    """Codegen-level tests for extrinsic functions code generation (§7.1.6)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic function call")
    def test_extrinsic_function_call(self, generate_python):
        """Extrinsic function generates Python function call (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic with arguments")
    def test_extrinsic_with_arguments(self, generate_python):
        """Extrinsic function arguments are passed correctly (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: external routine call")
    def test_external_routine_call(self, generate_python):
        """External routine generates module import and call (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: return value handling")
    def test_return_value_handling(self, generate_python):
        """Extrinsic return value is captured (§7.1.6)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestExternalRoutineCallsCodegen:
    """Codegen tests for cross-routine calls.

    External calls require module loading, caching, and shared
    runtime context for variable passing.

    Reference: §7.1.6
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: module import generation")
    def test_module_import_generation(self, generate_python):
        """External call generates import statement.

        $$FUNC^ROUTINE generates: from routine import func
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: module caching")
    def test_module_caching(self, generate_python):
        """External modules are cached after first import.

        Multiple calls to same routine reuse cached module.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: cross-routine variable passing")
    def test_cross_routine_variable_passing(self, generate_python):
        """Variables visible across routine calls.

        Variables not NEWed in callee are visible to caller.
        Requires shared runtime context.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine name translation")
    def test_routine_name_translation(self, generate_python):
        """Routine names translated to valid module names.

        %ROUTINE becomes _pct_routine module.
        """
        pytest.fail("Stub - implement test")
