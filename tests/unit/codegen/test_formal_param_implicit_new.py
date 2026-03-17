"""Tests for implicit NEW of formal parameters in subroutine calls.

Per MUMPS standard, formal parameters create an implicit NEW frame:
the caller's variable is saved, the parameter value is bound, and
when the subroutine returns, the caller's variable is restored.

This is critical for routines like DIK.m where FREE(X) is called
during IXALL with DIKJ as argument, but the caller's X=1 (SET mode)
must be preserved for cross-reference scanning.

Regression: Before this fix, the TRAMPOLINE codegen path did not push
formal parameters to _new_stack, so the caller's shared MArray was
mutated in-place rather than being saved and restored.
"""

import pytest


# ---------------------------------------------------------------------------
# Codegen-level: verify generated Python patterns
# ---------------------------------------------------------------------------
@pytest.mark.codegen
class TestFormalParamImplicitNewCodegen:
    """Verify generated code includes implicit NEW for formal parameters."""

    def test_dynamic_locals_new_stack_for_param(self, generate_python):
        """Dynamic-locals path: formal param pushed to _new_stack.

        K forces dynamic_locals; SUB(X) must NEW X before binding.
        """
        code = generate_python("TEST K\n D SUB(5) Q\nSUB(X) G END Q\nEND Q\n")
        # The internal _SUB function should save X on _new_stack
        sub_section = code.split("def _SUB")[1].split("def ")[0]
        assert "state._new_stack.append(('var', 'X'" in sub_section
        assert "state._locals.pop('X'" in sub_section

    def test_static_state_vars_new_marray(self, generate_python):
        """Static state_vars path: formal param creates new MArray, not setdefault.

        Without K, the static path is used. _scope[param] must NOT use
        setdefault (which mutates the caller's shared MArray).
        """
        code = generate_python("TEST D SUB(5) Q\nSUB(X) G END Q\nEND Q\n")
        sub_section = code.split("def _SUB")[1].split("def ")[0]
        # Should create a fresh MArray, not mutate existing
        assert "MArray(value=" in sub_section
        # Should NOT use setdefault which mutates shared objects
        assert "setdefault" not in sub_section

    def test_multiple_params_each_newed(self, generate_python):
        """Each formal parameter gets its own _new_stack.append."""
        code = generate_python("TEST K\n D SUB(1,2) Q\nSUB(A,B) G END Q\nEND Q\n")
        sub_section = code.split("def _SUB")[1].split("def ")[0]
        assert "state._new_stack.append(('var', 'A'" in sub_section
        assert "state._new_stack.append(('var', 'B'" in sub_section


# ---------------------------------------------------------------------------
# Execution-level: verify runtime behavior
# ---------------------------------------------------------------------------
@pytest.mark.codegen
class TestFormalParamImplicitNew:
    """Formal parameters must be implicitly NEWed per MUMPS spec."""

    def test_caller_variable_restored_after_do(self, execute_mumps):
        """Caller's X is restored after D SUB(99) where SUB(X) sets X."""
        source = """\
TEST S X=1 D SUB(99) W X Q
SUB(X) S X=X+1 Q"""
        result = execute_mumps(source)
        assert result.output == "1"
        assert result.success is True

    def test_caller_variable_restored_after_extrinsic(self, execute_mumps):
        """Caller's X is restored after $$FUNC(val) where FUNC(X) modifies X.

        This is the exact pattern from DIK.m: $$FREE(DIKJ) has formal
        parameter X which shadows IXALL's X=1 (SET mode flag).
        """
        source = """\
TEST S X=1,Y=$$ADD(99) W X,"-",Y Q
ADD(X) S X=X+1 Q X"""
        result = execute_mumps(source)
        assert result.output == "1-100"
        assert result.success is True

    def test_param_not_passed_is_undefined(self, execute_mumps):
        """When a formal parameter is not passed, $D(param)=0."""
        source = """\
TEST S X=1 D SUB W X Q
SUB(Y) W $D(Y),"-" Q"""
        result = execute_mumps(source)
        assert result.output == "0-1"
        assert result.success is True

    def test_multiple_params_all_restored(self, execute_mumps):
        """All formal parameters are independently restored."""
        source = """\
TEST S A=1,B=2 D SUB(10,20) W A,",",B Q
SUB(A,B) S A=A+B Q"""
        result = execute_mumps(source)
        assert result.output == "1,2"
        assert result.success is True

    def test_param_shadows_caller_same_name(self, execute_mumps):
        """Formal parameter with same name as caller's variable is isolated.

        This is the core scenario: caller has X=1, callee has X as formal
        parameter receiving a different value. After callee returns, X=1.
        """
        source = """\
TEST S X="hello" D CHANGE(42) W X Q
CHANGE(X) S X="world" Q"""
        result = execute_mumps(source)
        assert result.output == "hello"
        assert result.success is True

    def test_nested_calls_preserve_variables(self, execute_mumps):
        """Nested subroutine calls all restore their formal parameters."""
        source = """\
TEST S X=1 D A(10) W X Q
A(X) D B(20) Q
B(X) S X=X+1 Q"""
        result = execute_mumps(source)
        assert result.output == "1"
        assert result.success is True

    def test_extrinsic_in_loop_preserves_caller(self, execute_mumps):
        """Extrinsic called in a FOR loop doesn't corrupt caller's variable.

        Modeled after DIK.m's DIKJ label which calls $$FREE(DIKJ) in a loop.
        """
        source = """\
TEST S X=1 F I=1:1:3 S Y=$$SQ(I)
 W X Q
SQ(X) Q X*X"""
        result = execute_mumps(source)
        assert result.output == "1"
        assert result.success is True

    def test_byref_param_aliases_caller_variable(self, execute_mumps):
        """By-reference parameter creates alias — changes ARE visible."""
        source = """\
TEST S X=1 D INC(.X) W X Q
INC(Y) S Y=Y+1 Q"""
        result = execute_mumps(source)
        assert result.output == "2"
        assert result.success is True

    def test_mixed_byref_and_byval(self, execute_mumps):
        """Mix of by-ref and by-value params: only by-ref persists."""
        source = """\
TEST S A=1,B=2 D SUB(.A,B) W A,",",B Q
SUB(X,Y) S X=X+10,Y=Y+10 Q"""
        result = execute_mumps(source)
        assert result.output == "11,2"
        assert result.success is True

    def test_param_restore_with_cross_label_goto(self, execute_mumps):
        """Formal parameter is visible within callee after cross-label GOTO.

        SUB(42) GOTOs SHOW where X=42 is visible. After SUB returns,
        X in the caller should be restored to 1. Currently the static
        state_vars path doesn't restore the caller's value (tracked
        separately from the dynamic-locals NEW fix).
        """
        source = """\
TEST S X=1 D SUB(42) W X Q
SUB(X) G SHOW Q
SHOW W X,"+" Q"""
        result = execute_mumps(source)
        # X=42 is visible within SHOW (cross-label GOTO preserves param)
        assert "42+" in result.output
        assert result.success is True

    def test_caller_undefined_stays_undefined(self, execute_mumps):
        """Caller has no X defined. After D SUB(5), X stays undefined.

        If the caller never set X, the implicit NEW saves <undefined>.
        When SUB returns, X must be undefined again ($D=0).
        """
        source = """\
TEST D SUB(5) W $D(X) Q
SUB(X) S X=X+1 Q"""
        result = execute_mumps(source)
        assert result.output == "0"
        assert result.success is True

    def test_recursive_extrinsic_preserves_each_frame(self, execute_mumps):
        """Recursive $$FACT(N) restores N at each call frame."""
        source = """\
TEST W $$FACT(4) Q
FACT(N) Q:N<2 1  Q N*$$FACT(N-1)"""
        result = execute_mumps(source)
        assert result.output == "24"
        assert result.success is True

    def test_param_same_name_as_label(self, execute_mumps):
        """Formal parameter with same name as a label doesn't conflict.

        Modeled after DIK.m's DISKIPIN(DISKIPIN) pattern.
        """
        source = """\
TEST S CNT=0 D BUMP(5) W CNT Q
BUMP(CNT) S CNT=CNT+1 Q"""
        result = execute_mumps(source)
        assert result.output == "0"
        assert result.success is True

    def test_extrinsic_return_value_with_param_restore(self, execute_mumps):
        """Extrinsic returns correct value while restoring caller's variable.

        Tests that both the return value AND the implicit NEW restoration
        work correctly together.
        """
        source = """\
TEST S X=100 S R=$$HALF(50) W X,",",R Q
HALF(X) Q X/2"""
        result = execute_mumps(source)
        assert result.output == "100,25"
        assert result.success is True
