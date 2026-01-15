"""Tests for Extrinsic Functions code generation (§7.1.6).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6
Spec 010 Phase 4: Extrinsic functions with by-reference parameter support
"""

import pytest


@pytest.mark.codegen
class TestExtrinsicFunctionsCodegen:
    """Codegen-level tests for extrinsic functions code generation (§7.1.6)."""

    def test_extrinsic_function_call(self, generate_python):
        """Extrinsic function generates Python function call (§7.1.6).

        Spec 010 (T022): Internal extrinsic $$label generates _call_extrinsic call.
        """
        source = """TEST
 S X=$$ADD(3,4)
 Q X
ADD(A,B)
 Q A+B
"""
        code = generate_python(source)
        assert "_call_extrinsic(_rt, ADD" in code
        # Verify the generated code is syntactically valid
        compile(code, "<test>", "exec")

    def test_extrinsic_with_arguments(self, generate_python):
        """Extrinsic function arguments are passed correctly (§7.1.6)."""
        source = """TEST
 S X=$$CALC(1,2,3)
 Q X
CALC(A,B,C)
 Q A+B+C
"""
        code = generate_python(source)
        # Arguments should be passed to _call_extrinsic
        assert "_call_extrinsic(_rt, CALC, 1, 2, 3)" in code

    def test_external_routine_call(self, generate_python):
        """External routine generates module import and call (§7.1.6).

        Spec 010 (T023): $$label^routine generates import and module-prefixed call.
        """
        source = """TEST
 S X=$$ADD^math(3,5)
 Q X
"""
        code = generate_python(source)
        # Should import the module
        assert "import math" in code
        # Should call with module prefix
        assert "_call_extrinsic(_rt, math.ADD" in code

    def test_return_value_handling(self, generate_python):
        """Extrinsic return value is captured (§7.1.6).

        QUIT with expression in extrinsic returns the value.
        """
        source = """TEST
 S X=$$DOUBLE(5)
 Q X
DOUBLE(N)
 Q N*2
"""
        code = generate_python(source)
        # The SET should capture the extrinsic result
        assert "_scope.setdefault('X', MArray()).value = _call_extrinsic" in code


@pytest.mark.codegen
class TestExtrinsicByRefCodegen:
    """Spec 010 Phase 4: Tests for by-reference parameter passing in extrinsics."""

    def test_byref_parameter_generates_byref_list(self, generate_python):
        """By-reference arguments generate _byref parameter (T021).

        When .VAR syntax is used, the _call_extrinsic should receive
        _byref list with variable names for updating after call.
        """
        source = """TEST
 S A=5,B=10
 S X=$$DOUBLE(.A,.B)
 Q
DOUBLE(P1,P2)
 S P1=P1*2
 S P2=P2*2
 Q P1+P2
"""
        code = generate_python(source)
        # Should have _byref parameter with variable names
        assert "_byref=['A', 'B']" in code

    def test_byref_mixed_with_byvalue(self, generate_python):
        """Mixed by-ref and by-value args handled correctly (T021).

        Only by-ref args should be in _byref list, by-value args are None.
        """
        source = """TEST
 S A=5,B=10
 S X=$$CALC(A,.B,3)
 Q
CALC(P1,P2,P3)
 S P2=P2+P1+P3
 Q P2
"""
        code = generate_python(source)
        # _byref should have None for non-byref positions and name for byref
        assert "_byref=[None, 'B', None]" in code

    def test_byref_return_tuple_generated(self, generate_python):
        """Extrinsic with byref outputs returns tuple (T020).

        When a label modifies by-ref parameters and has a return value,
        it should return (value, *byref_outputs).
        """
        source = """TEST
 Q
DOUBLE(X)
 S X=X*2
 Q X
"""
        code = generate_python(source)
        # DOUBLE should return tuple since X is a byref output
        assert "return (" in code
        assert "DOUBLE" in code

    def test_byref_extrinsic_runtime_behavior(self, generate_python):
        """By-ref extrinsic updates caller's variables at runtime (T021).

        This is a full integration test: the callee modifies by-ref params
        and those changes are visible to the caller after the call.
        """
        source = """TEST
 S A=10,B=20
 S X=$$DOUBLE(.A,.B)
 Q A_B_X
DOUBLE(P1,P2)
 S P1=P1*2
 S P2=P2*2
 Q P1+P2
"""
        code = generate_python(source)
        namespace = {}
        exec(code, namespace)

        # Call the generated code
        runtime = namespace["MUMPSRuntime"]()
        result = namespace["TEST"](runtime)

        # A should be 20 (10*2), B should be 40 (20*2), X should be 60 (20+40)
        assert result == "204060"


@pytest.mark.codegen
class TestExternalRoutineCallsCodegen:
    """Codegen tests for cross-routine calls.

    External calls require module loading, caching, and shared
    runtime context for variable passing.

    Reference: §7.1.6
    """

    def test_module_import_generation(self, generate_python):
        """External call generates import statement.

        $$FUNC^ROUTINE generates: import routine
        """
        source = """TEST
 S X=$$CALC^mathlib(5)
 Q X
"""
        code = generate_python(source)
        assert "import mathlib" in code

    def test_external_with_scope_parameter(self, generate_python):
        """External extrinsic passes _scope for variable visibility.

        Spec 008 (T045): External calls pass _scope=_scope for
        cross-routine variable visibility.
        """
        source = """TEST
 S X=$$CALC^mathlib(5)
 Q X
"""
        code = generate_python(source)
        assert "_scope=_scope" in code

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
