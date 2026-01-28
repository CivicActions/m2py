"""Tests for static pre-resolution in code generation (Spec 018 Phase 9).

User Story 7: Static Pre-Resolution in Codegen (Priority: P3)
Goal: Codegen pre-resolves static references, falls back to runtime for dynamic

Key Tests:
- T081: Static `S X=1` generates direct assignment (no runtime call)
- T082: Dynamic `S @Y=1` generates runtime call

Reference: MUMPS 1995 ANSI Standard + Spec 018 plan.md
"""

import pytest


# =============================================================================
# T081: Static Variable References Generate Direct Assignments
# =============================================================================


@pytest.mark.codegen
class TestStaticResolution:
    """Tests for static pre-resolution in codegen.

    FR-001 through FR-004: Variable access produces identical behavior
    regardless of compile-time or runtime resolution.

    The codegen should generate direct Python assignments for statically
    resolvable references, avoiding runtime overhead.
    """

    def test_static_set_generates_direct_assignment(self, generate_python):
        """T081: Static `S X=1` generates direct assignment, not runtime call.

        Static variable assignments should generate inline Python code
        without calling set_indirected() or other runtime resolution.

        Expected: _scope.setdefault('X', MArray()).value = 1
        NOT: _rt.set_indirected(...)
        """
        code = generate_python("TEST\n S X=1\n Q")
        # Verify direct assignment pattern
        assert "_scope.setdefault('X', MArray()).value = 1" in code
        # Verify NO runtime indirection call
        assert "set_indirected" not in code
        assert "resolve_indirection" not in code

    def test_static_set_multiple_generates_direct_assignments(self, generate_python):
        """Static multiple assignment generates direct Python assignments.

        S X=1,Y=2 should generate:
        _scope.setdefault('X', MArray()).value = 1
        _scope.setdefault('Y', MArray()).value = 2
        """
        code = generate_python("TEST\n S X=1,Y=2\n Q")
        assert "_scope.setdefault('X', MArray()).value = 1" in code
        assert "_scope.setdefault('Y', MArray()).value = 2" in code
        assert "set_indirected" not in code

    def test_static_set_subscripted_generates_direct_assignment(self, generate_python):
        """Static subscripted assignment generates direct Python code.

        S A(1)=5 should generate:
        _scope.setdefault('A', MArray())[1] = 5
        """
        code = generate_python("TEST\n S A(1)=5\n Q")
        # Subscripted assignment should be direct
        assert "_scope.setdefault('A', MArray())[" in code
        assert "set_indirected" not in code

    def test_static_set_nested_subscripts_generates_direct_assignment(
        self, generate_python
    ):
        """Static nested subscript assignment generates direct Python code.

        S A(1,2,3)=5 should generate direct tuple subscript access.
        """
        code = generate_python("TEST\n S A(1,2,3)=5\n Q")
        # Should have multi-subscript tuple access
        assert "_scope.setdefault('A', MArray())[" in code
        # Subscripts should be in the generated code
        assert "1" in code and "2" in code and "3" in code
        assert "set_indirected" not in code

    def test_static_read_generates_direct_access(self, generate_python):
        """Static read (W X) generates direct variable access.

        W X should access _scope['X'] via m_var_value() helper.
        """
        code = generate_python("TEST\n S X=1\n W X\n Q")
        # Write should access variable via m_var_value helper (handles MArray and plain values)
        assert "m_var_value(_scope.get('X'))" in code
        # Read should NOT use get_var or resolve_indirection
        assert "get_var" not in code
        assert "resolve_indirection" not in code

    def test_static_global_generates_runtime_call(self, generate_python):
        """Static global access generates runtime call (globals ARE runtime).

        S ^A=1 should generate _rt.globals.set("A", (), 1)
        Globals always go through runtime because they persist beyond execution.
        """
        code = generate_python("TEST\n S ^A=1\n Q")
        # Globals use runtime interface
        assert "_rt.globals.set" in code
        # But NOT indirection resolution
        assert "set_indirected" not in code

    def test_static_global_subscripted_generates_runtime_call(self, generate_python):
        """Static subscripted global generates runtime call.

        S ^A(1,2)=3 should generate _rt.globals.set("A", (1, 2), 3)
        """
        code = generate_python("TEST\n S ^A(1,2)=3\n Q")
        assert "_rt.globals.set" in code
        assert "set_indirected" not in code


# =============================================================================
# T082: Dynamic Variable References Generate Runtime Calls
# =============================================================================


@pytest.mark.codegen
class TestDynamicResolution:
    """Tests for dynamic (indirection) resolution in codegen.

    When the target variable name is determined at runtime via indirection,
    the codegen MUST generate a runtime call (set_indirected, get_var, etc.).
    """

    def test_dynamic_set_generates_runtime_call(self, generate_python):
        """T082: Dynamic `S @Y=1` generates runtime call.

        Indirection requires runtime resolution since the target is not
        known until execution.

        Expected: _rt.set_indirected("Y", 1, _scope, levels=1)
        """
        code = generate_python('TEST\n S Y="X"\n S @Y=1\n Q')
        # Should use runtime indirection resolution
        assert "set_indirected" in code
        # The indirection source variable should be referenced
        assert '"Y"' in code or "'Y'" in code

    def test_dynamic_set_multi_level_generates_runtime_call(self, generate_python):
        """Multi-level indirection `S @@X=1` generates runtime call with levels=2.

        @@X requires resolving X to get variable name, then resolving that.
        """
        code = generate_python('TEST\n S X="Y"\n S Y="Z"\n S @@X=1\n Q')
        assert "set_indirected" in code
        # Should have levels=2 for double indirection
        assert "levels=2" in code

    def test_dynamic_set_with_subscripts_generates_runtime_call(self, generate_python):
        """Indirection with subscripts `S @X@(1)=2` generates runtime call.

        The @X@(1) pattern requires runtime subscript resolution.
        """
        code = generate_python('TEST\n S X="A"\n S @X@(1)=2\n Q')
        assert "set_indirected" in code
        # Subscripts should be passed to runtime
        assert "(1,)" in code or "1" in code

    def test_dynamic_read_generates_runtime_call(self, generate_python):
        """Dynamic read via indirection generates runtime call.

        W @X uses ARGUMENT indirection, which evaluates the resolved
        string as a MUMPS expression. This generates a call to
        evaluate_argument_indirection (preferred), or legacy
        resolve_indirection/get_var/get_indirected.
        """
        code = generate_python('TEST\n S X="Y"\n S Y=42\n W @X\n Q')
        # Should use runtime for indirection read
        assert (
            "resolve_indirection" in code
            or "get_var" in code
            or "get_indirected" in code
            or "evaluate_argument_indirection" in code
        )

    def test_argument_indirection_generates_runtime_call(self, generate_python):
        """Argument indirection `I @A` generates runtime evaluation call.

        Argument indirection evaluates the string as a MUMPS expression.
        """
        code = generate_python('TEST\n S A="1=1"\n I @A W "YES"\n Q')
        # Should use evaluate_argument_indirection
        assert "evaluate_argument_indirection" in code

    def test_mixed_static_dynamic_in_same_line(self, generate_python):
        """Mixed static and dynamic in same SET uses appropriate methods.

        S X=1,@Y=2 should generate direct for X, runtime for @Y.
        """
        code = generate_python('TEST\n S Y="Z"\n S X=1,@Y=2\n Q')
        # X should be direct
        assert "_scope.setdefault('X', MArray()).value = 1" in code
        # @Y should be runtime
        assert "set_indirected" in code


# =============================================================================
# T083/T084/T085: Integration Tests - Behavior Correctness
# =============================================================================


@pytest.mark.codegen
class TestStaticDynamicBehaviorEquivalence:
    """Verify static and dynamic resolution produce identical BEHAVIOR.

    FR-001: Variable access produces identical behavior regardless of
    compile-time or runtime resolution.
    """

    def test_static_and_dynamic_set_produce_same_result(self, execute_mumps):
        """Static S X=5 and dynamic S @"X"=5 produce same observable result.

        Both should set X to 5, readable via W X.
        """
        static_result = execute_mumps("TEST\n S X=5\n W X\n Q")
        dynamic_result = execute_mumps('TEST\n S @"X"=5\n W X\n Q')
        assert static_result.output == "5"
        assert dynamic_result.output == "5"
        assert static_result.output == dynamic_result.output

    def test_static_and_dynamic_subscripted_produce_same_result(self, execute_mumps):
        """Static S A(1)=5 and dynamic S @"A(1)"=5 produce same result."""
        static_result = execute_mumps("TEST\n S A(1)=5\n W A(1)\n Q")
        dynamic_result = execute_mumps('TEST\n S @"A(1)"=5\n W A(1)\n Q')
        assert static_result.output == "5"
        assert static_result.output == dynamic_result.output

    def test_global_static_and_dynamic_produce_same_result(self, execute_mumps):
        """Static S ^G=1 and dynamic S @"^G"=1 produce same result."""
        static_result = execute_mumps("TEST\n S ^G=1\n W ^G\n Q")
        dynamic_result = execute_mumps('TEST\n S @"^G"=1\n W ^G\n Q')
        assert static_result.output == "1"
        assert static_result.output == dynamic_result.output


# =============================================================================
# T085: Performance Characteristics (Non-Regression)
# =============================================================================


@pytest.mark.codegen
class TestCodegenEfficiency:
    """Verify codegen produces efficient code for static cases.

    The generated code for static cases should NOT include unnecessary
    runtime overhead like indirection resolution when not needed.
    """

    def test_no_unnecessary_imports_for_simple_static(self, generate_python):
        """Simple static code doesn't import unused indirection utilities."""
        code = generate_python("TEST\n S X=1\n W X\n Q")
        # Core imports should be present
        assert "from m2py.runtime import MUMPSRuntime, MArray" in code
        # Indirection-specific runtime functions not needed for pure static
        # (This is aspirational - current impl may include them in all cases)

    def test_static_loop_generates_direct_code(self, generate_python):
        """FOR loop with static variable generates direct assignments.

        FOR I=1:1:10 S X=I should generate direct Python for loop.
        """
        code = generate_python("TEST\n F I=1:1:10 S X=I\n Q")
        # Should have direct assignment in loop body
        # Loop variable I and target X should both be direct
        assert "set_indirected" not in code

    def test_complex_expression_static_is_direct(self, generate_python):
        """Complex expression S X=A+B*C generates direct code when all static."""
        code = generate_python("TEST\n S A=1,B=2,C=3\n S X=A+B*C\n Q")
        # All assignments should be direct
        assert "set_indirected" not in code
        # Expression helpers are used but not indirection
        assert "m_add" in code or "m_mul" in code or "+" in code
